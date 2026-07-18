#!/bin/bash
# Render all apartment rooms with deterministic Cycles photorealistic renderer
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
BLENDER="/Applications/Blender.app/Contents/MacOS/Blender"
SCRIPT="$ROOT/blender_photoreal_pano.py"
FP_DIR="$ROOT/floor_plans"
OUT_DIR="$ROOT/unified_renders_8k"

WIDTH=4096
HEIGHT=2048
SAMPLES=128

mkdir -p "$OUT_DIR"

echo "=========================================="
echo "  Photoreal Cycles Render — All Rooms"
echo "  Resolution: ${WIDTH}x${HEIGHT}  Samples: $SAMPLES"
echo "=========================================="

# Focused iteration: render only living_dining until it is perfect
for room in living_dining; do
  echo ""
  echo "[render] $room..."
  "$BLENDER" -b -P "$SCRIPT" -- \
    --floor-plans "$FP_DIR" \
    --output-dir "$OUT_DIR" \
    --room "$room" \
    --width "$WIDTH" \
    --height "$HEIGHT" \
    --samples "$SAMPLES" 2>&1 | grep -E "^\[|Saved:|Error|error" || true
done

echo ""
echo "=========================================="
echo "  All renders complete"
echo "  Output: $OUT_DIR"
echo "=========================================="
ls -la "$OUT_DIR"/*_8k.png
