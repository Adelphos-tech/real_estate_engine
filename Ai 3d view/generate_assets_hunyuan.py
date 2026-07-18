#!/usr/bin/env python3
"""
Hunyuan3D-2 Asset Factory
=========================
Generate furniture/assets with Tencent Hunyuan3D-2 and save them as GLBs.
Room geometry (walls, floors, dimensions) is NOT touched by this script.
It only produces assets that the deterministic Blender renderer can load.

Modes:
  --from-prompt   Generate from a text prompt
  --from-image    Generate from a reference image

Example:
  python generate_assets_hunyuan.py --from-prompt \
      "modern beige fabric sofa, interior design, clean, low poly" \
      --output assets/library/sofa_modern_beige.glb
"""
import argparse
import base64
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).parent
CATALOG = ROOT / "asset_catalog.json"
REQUESTS_DIR = ROOT / "assets" / "requests"
LIBRARY_DIR = ROOT / "assets" / "library"
PREVIEWS_DIR = ROOT / "assets" / "previews"

# Default Hunyuan3D-2 API server endpoint. Change this if you run it elsewhere.
DEFAULT_API_URL = "http://localhost:8080"


def ensure_dirs():
    for d in (REQUESTS_DIR, LIBRARY_DIR, PREVIEWS_DIR):
        d.mkdir(parents=True, exist_ok=True)


def log_request(prompt_or_image, output_path, method, params):
    """Keep a persistent log of every AI asset request for reproducibility."""
    entry = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "method": method,
        "params": params,
        "output": str(output_path),
    }
    if prompt_or_image:
        entry["source"] = prompt_or_image if len(prompt_or_image) < 200 else prompt_or_image[:200] + "..."
    log_path = REQUESTS_DIR / f"{output_path.stem}.json"
    log_path.write_text(json.dumps(entry, indent=2))
    print(f"[log] saved request metadata to {log_path}")


def generate_via_local_api(prompt=None, image_path=None, api_url=DEFAULT_API_URL, turbo=False, texture=True):
    """Call a local Hunyuan3D-2 FastAPI server to produce a GLB."""
    import requests  # optional dependency, only needed in this path

    endpoint = f"{api_url}/generate"
    payload = {"turbo": turbo, "texture": texture}
    if image_path:
        with open(image_path, "rb") as f:
            payload["image"] = base64.b64encode(f.read()).decode("utf-8")
    if prompt:
        payload["prompt"] = prompt

    print(f"[api] POST {endpoint}")
    r = requests.post(endpoint, json=payload, timeout=600)
    r.raise_for_status()
    return r.content


def generate_via_native_pipeline(prompt=None, image_path=None, model_id="tencent/Hunyuan3D-2mini", turbo=False):
    """Run the Hunyuan3D-2 native PyTorch pipeline in this Python process."""
    try:
        from hy3dgen.shapegen import Hunyuan3DDiTFlowMatchingPipeline
    except ImportError as e:
        print("[error] Hunyuan3D-2 is not installed in this environment.")
        print("        Install with: pip install git+https://github.com/Tencent-Hunyuan/Hunyuan3D-2.git")
        raise e

    print(f"[native] loading shape model {model_id}...")
    pipeline = Hunyuan3DDiTFlowMatchingPipeline.from_pretrained(
        model_id,
        subfolder="hunyuan3d-dit-v2-mini-turbo" if turbo else "hunyuan3d-dit-v2-mini",
        variant="fp16",
    )

    if image_path:
        print(f"[native] generating shape from image: {image_path}")
        mesh = pipeline(image=str(image_path))[0]
    else:
        print(f"[native] generating shape from prompt: {prompt}")
        mesh = pipeline(text=prompt)[0]

    if texture:
        try:
            from hy3dgen.texgen import Hunyuan3DPaintPipeline
            print("[native] texturing mesh...")
            paint = Hunyuan3DPaintPipeline.from_pretrained(model_id)
            mesh = paint(mesh, image=str(image_path)) if image_path else paint(mesh, text=prompt)
        except Exception as e:
            print(f"[warn] texture generation failed, saving untextured mesh: {e}")

    return mesh


def normalize_mesh_to_meters(mesh, target_height=None):
    """Re-center mesh and scale so its longest horizontal dimension is in meters."""
    import trimesh
    if isinstance(mesh, (str, Path)):
        mesh = trimesh.load(str(mesh), force="mesh")

    bounds = mesh.bounds
    size = bounds[1] - bounds[0]

    # Center at origin
    center = (bounds[0] + bounds[1]) / 2
    mesh.apply_translation(-center)

    # Shift so base sits on z=0
    mesh.apply_translation([0, 0, -bounds[0][2] + center[2]])

    # Normalize to sane meters if model is huge/tiny (Hunyuan sometimes outputs in various units)
    longest_horiz = max(size[0], size[1])
    if longest_horiz < 0.01 or longest_horiz > 100:
        scale = 1.0 / longest_horiz if longest_horiz > 0 else 1.0
        mesh.apply_scale(scale)

    # Optional: force target height
    if target_height:
        current_h = mesh.bounds[1][2] - mesh.bounds[0][2]
        if current_h > 0:
            mesh.apply_scale(target_height / current_h)

    return mesh


def save_glb(mesh, output_path):
    """Export trimesh to GLB and preview OBJ fallback."""
    import trimesh
    if isinstance(mesh, bytes):
        output_path.write_bytes(mesh)
    else:
        mesh.export(str(output_path))
    print(f"[save] wrote {output_path}")


def register_in_catalog(asset_type, output_path, catalog_path=CATALOG):
    catalog = json.loads(catalog_path.read_text()) if catalog_path.exists() else {}
    rel = str(output_path.relative_to(ROOT))
    entry = catalog.setdefault(asset_type, {"default": None, "variants": []})
    if rel not in entry["variants"]:
        entry["variants"].append(rel)
    if entry.get("default") is None:
        entry["default"] = rel
    catalog_path.write_text(json.dumps(catalog, indent=2))
    print(f"[catalog] registered {asset_type} -> {rel}")


def main():
    parser = argparse.ArgumentParser(description="Generate furniture assets with Hunyuan3D-2")
    parser.add_argument("--from-prompt", type=str, help="Text prompt for generation")
    parser.add_argument("--from-image", type=str, help="Reference image path")
    parser.add_argument("--output", type=str, required=True, help="Output .glb path")
    parser.add_argument("--asset-type", type=str, required=True,
                        help="Furniture category, e.g. sofa, chair, bed")
    parser.add_argument("--mode", choices=["api", "native"], default="native",
                        help="Use local API server or native pipeline")
    parser.add_argument("--api-url", type=str, default=DEFAULT_API_URL)
    parser.add_argument("--turbo", action="store_true", help="Use faster/turbo model variant")
    parser.add_argument("--no-texture", action="store_true", help="Skip texture generation")
    parser.add_argument("--target-height", type=float, default=None,
                        help="Force final mesh height in meters (e.g. 0.85 for sofa seat)")
    args = parser.parse_args()

    ensure_dirs()
    output_path = Path(args.output)

    if not (args.from_prompt or args.from_image):
        print("[error] supply either --from-prompt or --from-image")
        sys.exit(1)

    prompt = args.from_prompt
    image_path = Path(args.from_image) if args.from_image else None
    texture = not args.no_texture

    log_request(prompt or str(image_path), output_path, args.mode, vars(args))

    if args.mode == "api":
        glb_bytes = generate_via_local_api(
            prompt=prompt, image_path=image_path, api_url=args.api_url, turbo=args.turbo, texture=texture
        )
        save_glb(glb_bytes, output_path)
    else:
        mesh = generate_via_native_pipeline(
            prompt=prompt, image_path=image_path, turbo=args.turbo
        )
        mesh = normalize_mesh_to_meters(mesh, target_height=args.target_height)
        save_glb(mesh, output_path)

    register_in_catalog(args.asset_type, output_path)

    print("[done] asset ready for deterministic renderer")


if __name__ == "__main__":
    main()
