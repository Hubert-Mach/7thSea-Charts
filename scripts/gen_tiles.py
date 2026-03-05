#!/usr/bin/env python3
"""
gen_tiles.py - PNG tile generator for globe.html / 7th Sea Mappa Mundi

FAR:  8x4   tiles - each covers 45x45 degrees
NEAR: 72x36 tiles - each covers  5x5 degrees

Usage:
  python3 gen_tiles.py <map.png> [options]

Options:
  --out DIR   Output directory (default: ../tiles_png)

Requirements:
  pip install Pillow
"""

import sys
import os
import argparse
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("Missing Pillow library. Install with: pip install Pillow")
    sys.exit(1)

# Disable image size limit (default ~89 MPx is too small for large maps)
Image.MAX_IMAGE_PIXELS = None

# View configuration (must match VIEWS in globe.html)
VIEWS = {
    'far': {
        'cols': 8,
        'rows': 4,
        'desc': '45x45 degrees per tile',
    },
    'near': {
        'cols': 72,
        'rows': 36,
        'desc': '5x5 degrees per tile',
    },
}

DEFAULT_OUT_DIR = '../tiles_png'


def gen_tiles(src_path, out_dir=DEFAULT_OUT_DIR):

    src_path = Path(src_path)
    if not src_path.exists():
        print(f"Error: file '{src_path}' not found.")
        sys.exit(1)

    print(f"Loading: {src_path}")
    with Image.open(src_path) as img:
        src_img = img.convert('RGBA')
        src_w, src_h = src_img.size
    print(f"Source map size: {src_w}x{src_h} px")

    for view_name, cfg in VIEWS.items():
        cols = cfg['cols']
        rows = cfg['rows']

        tile_w = src_w // cols
        tile_h = src_h // rows

        target_w = tile_w * cols
        target_h = tile_h * rows

        if (target_w, target_h) != (src_w, src_h):
            print(f"  [{view_name}] Rescaling {src_w}x{src_h} -> {target_w}x{target_h}")
            scaled = src_img.resize((target_w, target_h), Image.LANCZOS)
        else:
            scaled = src_img.copy()

        tile_out_dir = Path(out_dir) / view_name
        tile_out_dir.mkdir(parents=True, exist_ok=True)

        total = rows * cols

        print(f"  [{view_name}] {rows}x{cols} = {total} tiles "
              f"({tile_w}x{tile_h} px) [{cfg['desc']}]")

        for row in range(rows):
            for col in range(cols):
                x0   = col * tile_w
                y0   = row * tile_h
                tile = scaled.crop((x0, y0, x0 + tile_w, y0 + tile_h))
                tile.save(tile_out_dir / f"{row}_{col}.png", 'PNG', optimize=True)

            done = (row + 1) * cols
            pct  = done * 100 // total
            bar  = '#' * (pct // 5) + '.' * (20 - pct // 5)
            print(f"\r    [{bar}] {pct:3d}% ({done}/{total})", end='', flush=True)

        print(f"\r  [{view_name}] OK {total} tiles -> {tile_out_dir}/          ")

    print("\nDone!")
    print("Run: python3 -m http.server 8000  ->  http://localhost:8000/globe.html")


if __name__ == '__main__':
    ap = argparse.ArgumentParser(
        description='PNG tile generator for globe.html'
    )
    ap.add_argument('map',
        help='Equirectangular PNG/JPG map (width = 2 x height)')
    ap.add_argument('--out', default=DEFAULT_OUT_DIR,
        help=f'Output directory (default: {DEFAULT_OUT_DIR})')

    args = ap.parse_args()
    gen_tiles(
        src_path = args.map,
        out_dir  = args.out,
    )
