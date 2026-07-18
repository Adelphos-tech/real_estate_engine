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
**Status:** 🚧 In Progress — scaffold complete, awaiting actual asset generation

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

### Verification
- Rendered `living_dining` with missing assets: renderer correctly fell back to boxes, geometry remained exact, no errors.
- Invalid placeholder GLB was rejected by Blender GLTF importer; fallback handled gracefully.

### Outputs
- `blender_photoreal_pano.py` updated with GLB import support
- `asset_catalog.json`
- `generate_assets_hunyuan.py`
- `ASSET_INTEGRATION.md`
- `assets/requests/`, `assets/library/`, `assets/previews/` directories

### Next Step
1. Install Hunyuan3D-2 or start its FastAPI server.
2. Generate first real asset: `assets/library/sofa_modern_beige.glb`.
3. Re-render `living_dining` to verify GLB placement matches JSON dimensions.
4. Iterate asset quality / prompts until `living_dining` looks photoreal.
5. Expand to remaining room types.

### Notes
- Hunyuan3D-2 native module (`hy3dgen`) is not yet installed in this environment.
- `render_all_photoreal.sh` is currently restricted to `living_dining` only for focused iteration.
