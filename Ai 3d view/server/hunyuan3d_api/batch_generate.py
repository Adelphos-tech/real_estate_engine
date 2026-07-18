#!/usr/bin/env python3
"""
Batch asset generator client.
Reads a JSON file of furniture prompts and generates all assets from the remote GPU server.

Example batch file (assets/batch_prompts.json):
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

Usage:
  python batch_generate.py \
    --input assets/batch_prompts.json \
    --api-url http://your-gpu-server:8080 \
    --async-mode
"""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from generate_assets_hunyuan import generate_via_api, register_in_catalog


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=str, default="assets/batch_prompts.json")
    parser.add_argument("--api-url", type=str, default="http://localhost:8080")
    parser.add_argument("--async-mode", action="store_true")
    parser.add_argument("--turbo", action="store_true")
    parser.add_argument("--no-texture", action="store_true")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"[error] batch file not found: {input_path}")
        sys.exit(1)

    prompts = json.loads(input_path.read_text())
    print(f"[batch] {len(prompts)} assets to generate")

    for asset_type, prompt in prompts.items():
        output_path = Path("assets/library") / f"{asset_type}_01.glb"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        print(f"\n[batch] generating {asset_type}: {prompt[:60]}...")
        try:
            glb_bytes = generate_via_api(
                prompt=prompt,
                api_url=args.api_url,
                turbo=args.turbo,
                texture=not args.no_texture,
                async_mode=args.async_mode,
            )
            output_path.write_bytes(glb_bytes)
            register_in_catalog(asset_type, output_path)
            print(f"[batch] saved {output_path}")
        except Exception as e:
            print(f"[batch] FAILED {asset_type}: {e}")

    print("\n[batch] done")


if __name__ == "__main__":
    main()
