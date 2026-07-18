# Hunyuan3D-2 Asset Integration Plan

## Principle: Geometry Is Untouchable
- **Walls, floors, ceilings, room dimensions** come only from `floor_plans/*.json`.
- **AI-generated assets** are restricted to furniture/objects placed inside rooms.
- The renderer loads GLBs at render time but **only applies transforms** (location, rotation, scale). Mesh vertices are never edited.

## Files Added / Modified
- `assets/library/` — cached GLB furniture assets
- `assets/previews/` — turntable preview renders of each asset
- `assets/requests/` — log of every AI generation request
- `asset_catalog.json` — maps `furniture.type` to available GLB variants
- `generate_assets_hunyuan.py` — Hunyuan3D-2 generation wrapper (API or native)
- `blender_photoreal_pano.py` — `build_furniture()` now loads GLBs from catalog, falls back to boxes
- `MILESTONE_LOG.md` — milestone log

## How to Generate an Asset

### Option A: Native pipeline (requires Hunyuan3D-2 install + GPU)
```bash
cd "/Users/apple/Desktop/Ai 3d view"
python3 generate_assets_hunyuan.py \
  --from-prompt "modern beige fabric sofa, clean interior design, low poly" \
  --asset-type sofa \
  --output assets/library/sofa_modern_beige.glb \
  --mode native \
  --target-height 0.85
```

### Option B: Local API server (recommended for scalable batch generation)
1. Start the Hunyuan3D-2 FastAPI server in a separate terminal:
   ```bash
   # inside Hunyuan3D-2 repo
   python api_server.py --host 0.0.0.0 --port 8080 --enable_tex
   ```
2. Generate:
   ```bash
   python3 generate_assets_hunyuan.py \
     --from-prompt "modern beige fabric sofa" \
     --asset-type sofa \
     --output assets/library/sofa_modern_beige.glb \
     --mode api \
     --target-height 0.85
   ```

## How the Renderer Uses Assets
`build_furniture()` in `blender_photoreal_pano.py`:
1. Reads `asset_catalog.json`.
2. For each furniture item, checks if its `type` has a `default` GLB.
3. If yes, imports the GLB and parents it to an empty at the JSON-specified `(x, y, z)` and `rotation`.
4. Scales the empty so the asset's bounding box matches the JSON `(w, d, h)` — **this only changes transform, not geometry**.
5. If no GLB exists, falls back to the old colored box primitive.

## Batch Generation Example
Create `assets/batch_prompts.json`:
```json
{
  "sofa": "modern beige fabric L-shaped sofa, apartment interior",
  "chair": "wooden dining chair, light oak",
  "coffee_table": "rectangular walnut coffee table",
  "tv": "flatscreen TV on stand",
  "dining_table": "rectangular wood dining table for 4",
  "bed": "queen size bed with white headboard",
  "bathtub": "white freestanding bathtub",
  "toilet": "white ceramic toilet",
  "fridge": "stainless steel double door refrigerator"
}
```
Then run the batch script (to be created once assets are needed).

## Next Step
1. Install Hunyuan3D-2 in a dedicated Python/conda environment or start the API server elsewhere.
2. Generate the first asset (`sofa_modern_beige.glb`).
3. Re-render `living_dining` to verify the GLB loads correctly and JSON dimensions remain exact.
