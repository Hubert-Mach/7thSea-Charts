#!/usr/bin/env python3
"""
gen_tiles.py - PNG tile generator for globe.html / 7th Sea Mappa Mundi

FAR:  8x4   tiles - each covers 45x45 degrees  (2048x2048 px output)
NEAR: 36x18 tiles - each covers 10x10 degrees   (2048x2048 px output, upscaled)

The source map is always rescaled to 4096x2048 before cutting.
All output tiles are 2048x2048 px regardless of view.

Usage:
  python3 gen_tiles.py <map.png> [options]

Options:
  --view VIEW  Which view to generate: 'far', 'near', or 'all' (default: all)
  --out DIR    Output directory (default: ../tiles_png)

Examples:
  python3 gen_tiles.py mapa.png --view far
  python3 gen_tiles.py mapa.png --view near
  python3 gen_tiles.py mapa.png

Requirements:
  pip install Pillow
"""

import sys
import argparse
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("Missing Pillow library. Install with: pip install Pillow")
    sys.exit(1)

Image.MAX_IMAGE_PIXELS = None

# Source map is always normalised to this before cutting
NORM_W = 4096
NORM_H = 2048

# All output tiles are this size
TILE_OUT = 2048

VIEWS = {
    'far': {
        'cols': 8,
        'rows': 4,
        'desc': '45x45 degrees per tile',
    },
    'near': {
        'cols': 36,
        'rows': 18,
        'desc': '10x10 degrees per tile',
    },
}

DEFAULT_OUT_DIR = '../tiles_png'


def gen_view(norm_img, view_name, cfg, out_dir):
    cols = cfg['cols']
    rows = cfg['rows']

    tile_w = NORM_W // cols   # raw tile size after cutting
    tile_h = NORM_H // rows

    tile_out_dir = Path(out_dir) / view_name
    tile_out_dir.mkdir(parents=True, exist_ok=True)

    total = rows * cols
    upscale = (tile_w != TILE_OUT or tile_h != TILE_OUT)

    # Overlap in source pixels added on each side before upscaling,
    # then cropped away after. Prevents seam artifacts from LANCZOS
    # interpolating edge pixels without knowledge of the neighbouring tile.
    OVERLAP = 2 if upscale else 0
    scale_factor = TILE_OUT / tile_w

    src_w, src_h = norm_img.size

    print(f"  [{view_name}] {cols}x{rows} = {total} tiles  "
          f"(cut {tile_w}x{tile_h} px → output {TILE_OUT}x{TILE_OUT} px"
          + (f", overlap={OVERLAP}px" if OVERLAP else "") +
          f")  [{cfg['desc']}]")

    for row in range(rows):
        for col in range(cols):
            x0 = col * tile_w
            y0 = row * tile_h

            if upscale:
                # Expand crop by OVERLAP on each side, clamped to image bounds
                cx0 = max(0, x0 - OVERLAP)
                cy0 = max(0, y0 - OVERLAP)
                cx1 = min(src_w, x0 + tile_w + OVERLAP)
                cy1 = min(src_h, y0 + tile_h + OVERLAP)

                tile = norm_img.crop((cx0, cy0, cx1, cy1))

                # Upscale padded crop proportionally
                tw = round((cx1 - cx0) * scale_factor)
                th = round((cy1 - cy0) * scale_factor)
                tile = tile.resize((tw, th), Image.LANCZOS)

                # Trim back to TILE_OUT by removing the overlap margin
                left = round((x0 - cx0) * scale_factor)
                top  = round((y0 - cy0) * scale_factor)
                tile = tile.crop((left, top, left + TILE_OUT, top + TILE_OUT))
            else:
                tile = norm_img.crop((x0, y0, x0 + tile_w, y0 + tile_h))

            tile.save(tile_out_dir / f"{row}_{col}.png", 'PNG', optimize=True)

        done = (row + 1) * cols
        pct  = done * 100 // total
        bar  = '#' * (pct // 5) + '.' * (20 - pct // 5)
        print(f"\r    [{bar}] {pct:3d}% ({done}/{total})", end='', flush=True)

    print(f"\r  [{view_name}] OK {total} tiles -> {tile_out_dir}/          ")


def gen_tiles(src_path, view='all', out_dir=DEFAULT_OUT_DIR):

    src_path = Path(src_path)
    if not src_path.exists():
        print(f"Error: file '{src_path}' not found.")
        sys.exit(1)

    print(f"Loading: {src_path}")
    with Image.open(src_path) as img:
        src_img = img.convert('RGBA')
        src_w, src_h = src_img.size
    print(f"Source map size: {src_w}x{src_h} px")

    # Always normalise to NORM_W x NORM_H
    if (src_w, src_h) != (NORM_W, NORM_H):
        print(f"Rescaling to {NORM_W}x{NORM_H} px...")
        norm_img = src_img.resize((NORM_W, NORM_H), Image.LANCZOS)
    else:
        norm_img = src_img

    views_to_run = list(VIEWS.items()) if view == 'all' else [(view, VIEWS[view])]

    for view_name, cfg in views_to_run:
        gen_view(norm_img, view_name, cfg, out_dir)

    print("\nDone!")
    print("Run: python3 -m http.server 8000  ->  http://localhost:8000/globe.html")


if __name__ == '__main__':
    ap = argparse.ArgumentParser(
        description='PNG tile generator for globe.html'
    )
    ap.add_argument('map',
        help='Equirectangular PNG/JPG map (approximately 2:1 aspect ratio)')
    ap.add_argument('--view', choices=['far', 'near', 'all'], default='all',
        help="Which view to generate: 'far', 'near', or 'all' (default: all)")
    ap.add_argument('--out', default=DEFAULT_OUT_DIR,
        help=f'Output directory (default: {DEFAULT_OUT_DIR})')

    args = ap.parse_args()
    gen_tiles(
        src_path = args.map,
        view     = args.view,
        out_dir  = args.out,
    )
