# Hunyuan3D-2 Remote Asset Server

GPU-powered FastAPI server that generates furniture/assets from text or image prompts and returns GLB files.

## Deploy on GPU Server

### Option A: Docker Compose (recommended)

```bash
cd /path/to/server/hunyuan3d_api
docker-compose up --build -d
```

Requirements on host:
- NVIDIA GPU + driver
- Docker + NVIDIA Container Toolkit (`nvidia-docker2`)

### Option B: Manual Install

```bash
# 1. Python environment (conda recommended)
conda create -n hunyuan3d python=3.10 -y
conda activate hunyuan3d

# 2. PyTorch with CUDA
pip install torch==2.4.0 torchvision --index-url https://download.pytorch.org/whl/cu121

# 3. Hunyuan3D-2
git clone https://github.com/Tencent-Hunyuan/Hunyuan3D-2.git
cd Hunyuan3D-2
pip install -r requirements.txt
pip install -e .
cd hy3dgen/texgen/custom_rasterizer && python setup.py install
cd ../../differentiable_renderer && python setup.py install
cd /path/to/server/hunyuan3d_api

# 4. Server dependencies
pip install -r requirements.txt

# 5. Run
python main.py
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `H3D_HOST` | `0.0.0.0` | Bind host |
| `H3D_PORT` | `8080` | Bind port |
| `H3D_MODEL` | `tencent/Hunyuan3D-2mini` | Default model repo |
| `H3D_SUBFOLDER` | `hunyuan3d-dit-v2-mini` | Default model subfolder |
| `H3D_TEXTURE` | `true` | Enable texture generation |
| `H3D_OUTPUT_DIR` | `./generated_assets` | Where GLBs are stored |

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | GPU status + config |
| GET | `/models` | Available model variants |
| POST | `/generate` | Sync generation, returns GLB |
| POST | `/generate/async` | Submit async job |
| GET | `/status/{job_id}` | Poll async job |
| GET | `/download/{job_id}` | Download completed GLB |

## Example Request

```bash
curl -X POST http://your-gpu-server:8080/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "modern beige fabric sofa, apartment interior, clean",
    "texture": true,
    "target_height": 0.85,
    "model": "tencent/Hunyuan3D-2mini",
    "subfolder": "hunyuan3d-dit-v2-mini"
  }' \
  -o sofa_modern_beige.glb
```

## Client (Local Blender Machine)

Use `generate_assets_hunyuan.py` in the project root:

```bash
cd "/Users/apple/Desktop/Ai 3d view"
python3 generate_assets_hunyuan.py \
  --from-prompt "modern beige fabric sofa" \
  --asset-type sofa \
  --output assets/library/sofa_modern_beige.glb \
  --mode api \
  --api-url http://your-gpu-server:8080 \
  --target-height 0.85
```

The renderer then loads the saved GLB and places it using only the JSON transform.
