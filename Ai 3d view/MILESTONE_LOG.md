# Project Milestone Log — Ai 3D View

## Milestone 1: Deterministic Cycles Pipeline Fixed
**Date:** 2026-07-18
**Status:** ✅ Complete

### Summary
Replaced diffusion-based rendering with deterministic Blender 5.2 + Cycles pipeline. Fixed watertight wall geometry, eliminated HDRI leakage through internal doorways, corrected box scaling bug, rebalanced lighting, and rendered all 7 rooms at 4096×2048 / 128 samples.

### Key Changes
- `blender_photoreal_pano.py`: solid inward-facing wall boxes, scaled fill lights, reduced HDRI/sun intensity
- `add_box()`: fixed scaling bug (was producing half-size geometry)
- `render_all_photoreal.sh`: upgraded to 4096×2048 / 128 samples, temporarily restricted to `living_dining` for focused iteration
- `index.html`: cache-bust bumped to `?v=27`

### Outputs
- `unified_renders_8k/{living_dining,kitchen,bedroom,bathroom,study_maid,balcony,wc_laundry}_8k.png`
- All renders verified watertight with no outdoor leakage

---

## Milestone 2: Hunyuan3D-2 Asset Integration Scaffold
**Date:** 2026-07-18
**Status:** ✅ Complete — scaffold committed

### Summary
Added a scalable AI asset factory using **Hunyuan3D-2 (Tencent)**. Room geometry (walls/floors/dimensions) remains strictly JSON-driven. AI is used only to generate furniture GLBs offline, which the deterministic renderer loads at render time.

### Key Changes
- Created `assets/library/`, `assets/previews/`, `assets/requests/` directories
- Created `asset_catalog.json` mapping `furniture.type` to GLB variants
- Created `generate_assets_hunyuan.py` — Hunyuan3D-2 wrapper supporting:
  - Native PyTorch pipeline (`--mode native`)
  - Local FastAPI server (`--mode api`)
  - Text-prompt and image-to-3D generation
  - Automatic normalization to meters
  - Request logging to `assets/requests/`
- Modified `blender_photoreal_pano.py` `build_furniture()`:
  - Loads GLBs from catalog if present
  - Scales asset bounding box to match JSON `(w, d, h)` via empty transform — **geometry vertices untouched**
  - Falls back to colored box primitives when GLB missing
- Created `ASSET_INTEGRATION.md` with usage instructions

### Outputs
- `blender_photoreal_pano.py` updated with GLB import support
- `asset_catalog.json`
- `generate_assets_hunyuan.py`
- `ASSET_INTEGRATION.md`
- `assets/requests/`, `assets/library/`, `assets/previews/` directories

---

## Milestone 3: Remote GPU FastAPI Server for Asset Generation
**Date:** 2026-07-18
**Status:** 🚧 In Progress — server scaffold complete, awaiting deployment

### Summary
All heavy Hunyuan3D-2 inference now lives on a remote GPU server. The local Mac only sends text/image prompts and downloads GLBs. Room geometry remains untouched.

### Key Changes
- Created `server/hunyuan3d_api/` with:
  - `main.py` — FastAPI server with sync/async generation endpoints
  - `Dockerfile` — CUDA 12.1 + Hunyuan3D-2 + server deps
  - `docker-compose.yml` — single-command GPU deployment
  - `requirements.txt` — server Python deps
  - `README.md` — deployment and usage docs
  - `batch_generate.py` — client script to generate many assets at once
- Updated `generate_assets_hunyuan.py`:
  - Default mode switched to `--mode api`
  - Added `--async-mode` for long remote jobs
  - Reads `H3D_API_URL` env var for remote server URL
  - Uses `image_b64` field matching server API
- Added `assets/batch_prompts.json` — 20 furniture prompts ready for batch generation

### API Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | GPU status + config |
| GET | `/models` | Available model variants |
| POST | `/generate` | Sync generation, returns GLB |
| POST | `/generate/async` | Submit async job |
| GET | `/status/{job_id}` | Poll async job |
| GET | `/download/{job_id}` | Download completed GLB |

### How to Deploy Server
```bash
cd "/Users/apple/Desktop/Ai 3d view/server/hunyuan3d_api"
docker-compose up --build -d
```

### How to Generate Asset from Local Machine
```bash
cd "/Users/apple/Desktop/Ai 3d view"
export H3D_API_URL=http://your-gpu-server:8080
python3 generate_assets_hunyuan.py \
  --from-prompt "modern beige fabric sofa, apartment interior, clean" \
  --asset-type sofa \
  --output assets/library/sofa_modern_beige.glb \
  --mode api \
  --async-mode \
  --target-height 0.85
```

### Batch Generation
```bash
python3 server/hunyuan3d_api/batch_generate.py \
  --input assets/batch_prompts.json \
  --api-url http://your-gpu-server:8080 \
  --async-mode
```

### Outputs
- `server/hunyuan3d_api/` server package
- Updated `generate_assets_hunyuan.py`
- `assets/batch_prompts.json`

### Verification
- Server/client scripts pass Python syntax check.
- Local render still falls back to boxes when no assets present; geometry unchanged.

### Next Step
1. Deploy the Docker container on your GPU server.
2. Verify `/health` returns GPU available.
3. Generate first real asset (sofa) and re-render `living_dining`.
4. Iterate prompts/model until `living_dining` is photoreal.

### Notes
- The server loads models lazily on first `/generate` call, so the first request is slow (~minutes for model download to GPU).
- Async mode is recommended for all generations because shape+texture can take 1–5 minutes per asset.
- Geometry safety: server normalizes mesh to meters; local renderer only applies transform.
