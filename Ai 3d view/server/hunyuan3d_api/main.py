#!/usr/bin/env python3
"""
Hunyuan3D-2 FastAPI Asset Server
================================
Runs on a GPU server. Receives text/image prompts and returns GLB files.
The client (Blender renderer machine) does zero GPU work.

Endpoints:
  POST /generate       - synchronous generation, returns GLB
  POST /generate/async - submit async job, returns job_id
  GET  /status/{job_id}- poll async job status/result
  GET  /health         - health check + GPU info
  GET  /models         - list available model variants
"""
import base64
import io
import os
import tempfile
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

# Server configuration from env
HOST = os.getenv("H3D_HOST", "0.0.0.0")
PORT = int(os.getenv("H3D_PORT", "8080"))
DEFAULT_MODEL = os.getenv("H3D_MODEL", "tencent/Hunyuan3D-2mini")
DEFAULT_SUBFOLDER = os.getenv("H3D_SUBFOLDER", "hunyuan3d-dit-v2-mini")
USE_TEXTURE = os.getenv("H3D_TEXTURE", "true").lower() in ("1", "true", "yes")
OUTPUT_DIR = Path(os.getenv("H3D_OUTPUT_DIR", "./generated_assets"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# In-memory job store (replace with Redis/DB for multi-worker production)
JOBS = {}


class GenerationJob(BaseModel):
    job_id: str
    status: str  # pending, running, completed, failed
    created_at: float
    completed_at: Optional[float] = None
    output_path: Optional[str] = None
    error: Optional[str] = None
    prompt: Optional[str] = None
    texture: bool = True
    model: str = DEFAULT_MODEL
    subfolder: str = DEFAULT_SUBFOLDER


class GenerateRequest(BaseModel):
    prompt: Optional[str] = None
    image_b64: Optional[str] = None
    texture: bool = True
    turbo: bool = False
    target_height: Optional[float] = None
    model: str = DEFAULT_MODEL
    subfolder: str = DEFAULT_SUBFOLDER


# Lazy model loading
_pipeline = None
_texture_pipeline = None


def get_shape_pipeline(model: str, subfolder: str):
    global _pipeline
    if _pipeline is None:
        from hy3dgen.shapegen import Hunyuan3DDiTFlowMatchingPipeline
        print(f"[server] loading shape model {model}/{subfolder}...")
        _pipeline = Hunyuan3DDiTFlowMatchingPipeline.from_pretrained(
            model, subfolder=subfolder, variant="fp16"
        )
        print("[server] shape model ready")
    return _pipeline


def get_texture_pipeline(model: str):
    global _texture_pipeline
    if _texture_pipeline is None:
        try:
            from hy3dgen.texgen import Hunyuan3DPaintPipeline
            print(f"[server] loading texture model {model}...")
            _texture_pipeline = Hunyuan3DPaintPipeline.from_pretrained(model)
            print("[server] texture model ready")
        except Exception as e:
            print(f"[server] texture pipeline unavailable: {e}")
            _texture_pipeline = False
    return _texture_pipeline if _texture_pipeline else None


def decode_image(image_b64: str) -> bytes:
    try:
        return base64.b64decode(image_b64)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid base64 image: {e}")


def normalize_mesh(mesh, target_height: Optional[float] = None):
    """Re-center, floor-align, and optionally scale to target height."""
    import trimesh
    if isinstance(mesh, (str, Path)):
        mesh = trimesh.load(str(mesh), force="mesh")

    bounds = mesh.bounds
    size = bounds[1] - bounds[0]
    center = (bounds[0] + bounds[1]) / 2
    mesh.apply_translation(-center)
    mesh.apply_translation([0, 0, -bounds[0][2] + center[2]])

    longest_horiz = max(size[0], size[1])
    if longest_horiz < 0.01 or longest_horiz > 100:
        scale = 1.0 / longest_horiz if longest_horiz > 0 else 1.0
        mesh.apply_scale(scale)

    if target_height:
        current_h = mesh.bounds[1][2] - mesh.bounds[0][2]
        if current_h > 0:
            mesh.apply_scale(target_height / current_h)

    return mesh


def generate_glb(req: GenerateRequest, output_path: Path):
    """Blocking generation. Writes GLB to output_path."""
    import trimesh

    pipeline = get_shape_pipeline(req.model, req.subfolder)

    image_path = None
    if req.image_b64:
        img_bytes = decode_image(req.image_b64)
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(img_bytes)
            image_path = f.name

    if image_path:
        print(f"[server] generating from image -> {output_path.name}")
        mesh = pipeline(image=image_path)[0]
    elif req.prompt:
        print(f"[server] generating from prompt: {req.prompt[:80]}")
        mesh = pipeline(text=req.prompt)[0]
    else:
        raise ValueError("supply either prompt or image_b64")

    if req.texture:
        tex = get_texture_pipeline(req.model)
        if tex:
            try:
                mesh = tex(mesh, image=image_path) if image_path else tex(mesh, text=req.prompt)
            except Exception as e:
                print(f"[server] texture failed: {e}")

    if image_path and os.path.exists(image_path):
        os.unlink(image_path)

    mesh = normalize_mesh(mesh, target_height=req.target_height)
    mesh.export(str(output_path))
    print(f"[server] saved {output_path}")


def run_job(job_id: str, req: GenerateRequest):
    """Background worker."""
    JOBS[job_id].status = "running"
    output_path = OUTPUT_DIR / f"{job_id}.glb"
    try:
        generate_glb(req, output_path)
        JOBS[job_id].status = "completed"
        JOBS[job_id].output_path = str(output_path)
        JOBS[job_id].completed_at = time.time()
    except Exception as e:
        JOBS[job_id].status = "failed"
        JOBS[job_id].error = str(e)
        JOBS[job_id].completed_at = time.time()
        print(f"[server] job {job_id} failed: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"[server] output dir: {OUTPUT_DIR.resolve()}")
    print(f"[server] default model: {DEFAULT_MODEL}/{DEFAULT_SUBFOLDER}")
    print(f"[server] texture enabled: {USE_TEXTURE}")
    yield
    print("[server] shutting down")


app = FastAPI(title="Hunyuan3D-2 Asset Server", lifespan=lifespan)


@app.get("/health")
def health():
    try:
        import torch
        gpu = torch.cuda.is_available()
        gpu_name = torch.cuda.get_device_name(0) if gpu else None
    except Exception:
        gpu = False
        gpu_name = None
    return {
        "status": "ok",
        "gpu_available": gpu,
        "gpu_name": gpu_name,
        "default_model": DEFAULT_MODEL,
        "default_subfolder": DEFAULT_SUBFOLDER,
        "texture_enabled": USE_TEXTURE,
    }


@app.get("/models")
def models():
    return {
        "models": [
            {"id": "tencent/Hunyuan3D-2mini", "subfolder": "hunyuan3d-dit-v2-mini", "description": "Fast, lower VRAM"},
            {"id": "tencent/Hunyuan3D-2mini", "subfolder": "hunyuan3d-dit-v2-mini-turbo", "description": "Turbo fast"},
            {"id": "tencent/Hunyuan3D-2", "subfolder": "hunyuan3d-dit-v2", "description": "Full quality"},
            {"id": "tencent/Hunyuan3D-2mv", "subfolder": "hunyuan3d-dit-v2-mv", "description": "Multi-view"},
            {"id": "tencent/Hunyuan3D-2.1", "subfolder": "hunyuan3d-dit-v2-1", "description": "Latest v2.1"},
        ]
    }


@app.post("/generate")
def generate(req: GenerateRequest):
    """Synchronous generation. Returns GLB file."""
    job_id = str(uuid.uuid4())
    output_path = OUTPUT_DIR / f"{job_id}.glb"
    try:
        generate_glb(req, output_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return FileResponse(
        str(output_path),
        media_type="model/gltf-binary",
        filename=f"asset_{job_id}.glb",
    )


@app.post("/generate/async")
def generate_async(req: GenerateRequest, background_tasks: BackgroundTasks):
    """Submit async job. Returns job_id immediately."""
    job_id = str(uuid.uuid4())
    JOBS[job_id] = GenerationJob(
        job_id=job_id,
        status="pending",
        created_at=time.time(),
        prompt=req.prompt,
        texture=req.texture,
        model=req.model,
        subfolder=req.subfolder,
    )
    background_tasks.add_task(run_job, job_id, req)
    return {"job_id": job_id, "status": "pending"}


@app.get("/status/{job_id}")
def status(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    result = job.model_dump()
    if job.status == "completed" and job.output_path:
        result["download_url"] = f"/download/{job_id}"
    return result


@app.get("/download/{job_id}")
def download(job_id: str):
    job = JOBS.get(job_id)
    if not job or job.status != "completed" or not job.output_path:
        raise HTTPException(status_code=404, detail="result not ready")
    return FileResponse(
        job.output_path,
        media_type="model/gltf-binary",
        filename=f"asset_{job_id}.glb",
    )


if __name__ == "__main__":
    uvicorn.run(app, host=HOST, port=PORT, log_level="info")
