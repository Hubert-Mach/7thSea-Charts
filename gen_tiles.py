#!/usr/bin/env python3
"""
gen_tiles.py — PNG tile generator for globe.html / 7th Sea Mappa Mundi
=======================================================================

Reads grid.json for all configuration — do not hardcode parameters here.
Place grid.json in the same directory as this script, or pass --grid.

Output layout
─────────────
  <out>/
    far/   0_0.png … 3_7.png
    near/  0_0.png … 35_71.png

grid.json is also copied to <out>/grid.json so compress_tiles.py and
globe.html can find it alongside the tiles.

Usage
─────
  python3 gen_tiles.py <map.png>
  python3 gen_tiles.py <map.png> --view far
  python3 gen_tiles.py <map.png> --view near
  python3 gen_tiles.py <map.png> --out ./tiles_png --grid ./grid.json

Requirements:  pip install Pillow
"""

import sys
import math
import json
import argparse
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("Missing Pillow library. Install with: pip install Pillow")
    sys.exit(1)

Image.MAX_IMAGE_PIXELS = None

DEFAULT_OUT_DIR  = '../tiles_png'
DEFAULT_GRID     = Path(__file__).parent / 'grid.json'
OVERLAP_SRC      = 2   # source-px overlap on each edge (anti-seam LANCZOS fix)


def load_grid(grid_path):
    path = Path(grid_path)
    if not path.exists():
        print(f"Error: grid.json not found at '{path}'")
        sys.exit(1)
    grid = json.loads(path.read_text())
    print(f"  [grid.json] tile_out={grid['tile_out']}, max_correction={grid['max_correction']}")
    for v, cfg in grid['views'].items():
        print(f"    {v}: {cfg['cols']}×{cfg['rows']}, lat_stretch={cfg['lat_stretch']}, seg={cfg['seg']}")
    return grid


def lat_correction(row, rows, max_correction):
    lat_mid = 90.0 - (row + 0.5) * (180.0 / rows)
    return min(1.0 / math.cos(math.radians(lat_mid)), max_correction)


def gen_view(norm_img, view_name, view_cfg, tile_out, max_correction, out_dir):
    cols        = view_cfg['cols']
    rows        = view_cfg['rows']
    lat_stretch = view_cfg['lat_stretch']

    src_w, src_h = norm_img.size
    tile_src_w   = src_w // cols
    tile_src_h   = src_h // rows
    scale_x      = tile_out / tile_src_w

    tile_out_dir = Path(out_dir) / view_name
    tile_out_dir.mkdir(parents=True, exist_ok=True)

    total = rows * cols
    print(f"  [{view_name}] {cols}×{rows} = {total} tiles  "
          f"(source {tile_src_w}×{tile_src_h}px → {tile_out}×H px"
          + (" lat-stretched" if lat_stretch else f", H={tile_out}") +
          f")  [{view_cfg['desc']}]")

    for row in range(rows):
        correction = lat_correction(row, rows, max_correction) if lat_stretch else 1.0
        out_h      = round(tile_out * correction)
        scale_y    = out_h / tile_src_h

        for col in range(cols):
            x0 = col * tile_src_w
            y0 = row * tile_src_h

            # Padded crop to avoid LANCZOS seam artifacts at tile edges
            cx0 = max(0,     x0 - OVERLAP_SRC)
            cy0 = max(0,     y0 - OVERLAP_SRC)
            cx1 = min(src_w, x0 + tile_src_w + OVERLAP_SRC)
            cy1 = min(src_h, y0 + tile_src_h + OVERLAP_SRC)

            tile = norm_img.crop((cx0, cy0, cx1, cy1))

            pad_w = round((cx1 - cx0) * scale_x)
            pad_h = round((cy1 - cy0) * scale_y)
            tile  = tile.resize((pad_w, pad_h), Image.LANCZOS)

            left = round((x0 - cx0) * scale_x)
            top  = round((y0 - cy0) * scale_y)
            tile = tile.crop((left, top, left + tile_out, top + out_h))

            tile.save(tile_out_dir / f"{row}_{col}.png", 'PNG', optimize=True)

        done = (row + 1) * cols
        pct  = done * 100 // total
        bar  = '#' * (pct // 5) + '.' * (20 - pct // 5)
        print(f"\r    [{bar}] {pct:3d}%  ({done}/{total})", end='', flush=True)

    print(f"\r  [{view_name}] Done — {total} tiles → {tile_out_dir}/          ")


def gen_tiles(src_path, grid_path, view='all', out_dir=DEFAULT_OUT_DIR):
    src_path = Path(src_path)
    if not src_path.exists():
        print(f"Error: '{src_path}' not found.")
        sys.exit(1)

    grid        = load_grid(grid_path)
    tile_out    = grid['tile_out']
    max_corr    = grid['max_correction']
    norm_w      = tile_out * grid['views']['far']['cols']   # e.g. 1024*8 = 8192
    norm_h      = tile_out * grid['views']['far']['rows']   # e.g. 1024*4 = 4096

    print(f"Loading: {src_path}")
    with Image.open(src_path) as img:
        src_img = img.convert('RGBA')
        src_w, src_h = src_img.size
    print(f"Source: {src_w}×{src_h} px")

    if (src_w, src_h) != (norm_w, norm_h):
        print(f"Rescaling to {norm_w}×{norm_h} px…")
        norm_img = src_img.resize((norm_w, norm_h), Image.LANCZOS)
    else:
        norm_img = src_img

    Path(out_dir).mkdir(parents=True, exist_ok=True)

    views_to_run = (list(grid['views'].items()) if view == 'all'
                    else [(view, grid['views'][view])])

    for view_name, view_cfg in views_to_run:
        gen_view(norm_img, view_name, view_cfg, tile_out, max_corr, out_dir)

    print("\nDone!")


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description='PNG tile generator for globe.html')
    ap.add_argument('map',
        help='Equirectangular PNG/JPG source map')
    ap.add_argument('--grid', default=DEFAULT_GRID, metavar='PATH',
        help=f'Path to grid.json (default: next to this script)')
    ap.add_argument('--view', choices=['far', 'near', 'all'], default='all',
        help="View to generate: 'far', 'near', or 'all' (default: all)")
    ap.add_argument('--out', default=DEFAULT_OUT_DIR,
        help=f'Output directory (default: {DEFAULT_OUT_DIR})')
    args = ap.parse_args()
    gen_tiles(src_path=args.map, grid_path=args.grid,
              view=args.view, out_dir=args.out)
