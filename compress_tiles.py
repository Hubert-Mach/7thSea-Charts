#!/usr/bin/env python3
"""
compress_tiles.py — PNG → WebP converter for globe.html tiles
==============================================================

For FAR tiles:
  Squeezes each 1024px tile back to tile_out×tile_out (reversing lat-stretch)
  and saves as a single WebP.

For NEAR tiles (when grid.json has subtile_size < tile_out):
  Squeezes to tile_out×tile_out, then splits each tile into an NxN grid of
  subtile_size×subtile_size WebP files.
  e.g. tile_out=1024, subtile_size=256 → 4×4 = 16 sub-tiles per tile
  Output files: <row*N+sr>_<col*N+sc>.webp

grid.json is expected next to this script.

Usage
─────
  python3 compress_tiles.py <tiles_png/far>   --out <tiles/far>
  python3 compress_tiles.py <tiles_png/near>  --out <tiles/near>
  python3 compress_tiles.py <tiles_png/near>  --out <tiles/near> --webp-quality 85

Requirements:  pip install Pillow
"""

import argparse
import sys
import json
import re
from pathlib import Path
from PIL import Image

DEFAULT_WEBP_QUALITY = 82
DEFAULT_PNG_COMPRESS = 9


def format_size(n):
    if n < 1024:       return f"{n} B"
    if n < 1024 ** 2:  return f"{n/1024:.1f} KB"
    return f"{n/1024**2:.2f} MB"


def load_grid(src_dir):
    """Load grid.json from next to this script."""
    candidate = Path(__file__).parent / 'grid.json'
    if not candidate.exists():
        print("   ⚠️  grid.json not found — no lat correction, assuming tile_out=1024, no split")
        return 1024, [], 1024, 0
    grid      = json.loads(candidate.read_text())
    tile_out  = grid['tile_out']
    view_name = src_dir.name
    view_cfg  = grid['views'].get(view_name, {})
    corrections = (view_cfg.get('row_corrections', [])
                   if view_cfg.get('lat_stretch') else [])

    # Subtiling only applies to NEAR (lat_stretch=True).
    # FAR tiles are not split — they are served at tile_out size.
    if view_cfg.get('lat_stretch', False):
        subtile = grid.get('subtile_size', tile_out)
    else:
        subtile = tile_out

    split = tile_out // subtile
    print(f"   grid.json : view={view_name}, tile_out={tile_out}, "
          f"lat_stretch={view_cfg.get('lat_stretch', False)}, "
          f"{view_cfg.get('cols','?')}×{view_cfg.get('rows','?')} tiles")
    if split > 1:
        sub_cols = view_cfg.get('cols', 0) * split
        sub_rows = view_cfg.get('rows', 0) * split
        print(f"   subtiling : {tile_out}px → {split}×{split} × {subtile}px  "
              f"({sub_cols}×{sub_rows} = {sub_cols*sub_rows} output tiles)")

    # Count polar-skipped rows (only relevant for lat_stretch views)
    skipped_rows = 0
    polar_cap = grid.get('polar_lat_cap')
    if view_cfg.get('lat_stretch', False) and polar_cap is not None:
        rows = view_cfg.get('rows', 0)
        cols = view_cfg.get('cols', 0)
        for r in range(rows):
            deg_per_row = 180.0 / rows
            lat_top = 90.0 - r * deg_per_row
            lat_bot = 90.0 - (r + 1) * deg_per_row
            if lat_bot >= polar_cap or lat_top <= -polar_cap:
                skipped_rows += 1
        if skipped_rows:
            skipped_tiles = skipped_rows * cols * split * split
            print(f"   polar skip: {skipped_rows} rows ({skipped_tiles} sub-tiles not generated, cap={polar_cap}°)")

    return tile_out, corrections, subtile, skipped_rows


def row_from_name(name):
    m = re.match(r'^(\d+)_\d+\.png$', name)
    return int(m.group(1)) if m else None

def col_from_name(name):
    m = re.match(r'^\d+_(\d+)\.png$', name)
    return int(m.group(1)) if m else None


def process_tile(src, dst_dir, tile_out, subtile_size, row_corrections,
                 webp_quality, png_compress, png_fallback):
    """
    Process one source PNG tile:
    1. Squeeze to tile_out×tile_out (reversing lat-stretch if needed)
    2. If subtile_size < tile_out, split into (tile_out/subtile_size)² sub-tiles
    3. Save each sub-tile as WebP (and optionally PNG)
    Returns total bytes written.
    """
    original_size = src.stat().st_size
    img = Image.open(src)

    row = row_from_name(src.name)
    col = col_from_name(src.name)

    # Squeeze back to square (reverse lat-stretch)
    if img.width != tile_out or img.height != tile_out:
        img = img.resize((tile_out, tile_out), Image.LANCZOS)

    if img.mode not in ('RGB', 'RGBA'):
        img = img.convert('RGBA')

    split        = tile_out // subtile_size
    total_webp   = 0
    total_png    = 0
    sub_count    = 0

    for sr in range(split):
        for sc in range(split):
            x0, y0 = sc * subtile_size, sr * subtile_size
            sub    = img.crop((x0, y0, x0 + subtile_size, y0 + subtile_size))

            # Global row/col in the sub-tile grid
            out_row = row * split + sr
            out_col = col * split + sc

            webp_path = dst_dir / f"{out_row}_{out_col}.webp"
            sub.save(webp_path, format='WEBP', quality=webp_quality,
                     method=6, lossless=False)
            total_webp += webp_path.stat().st_size

            if png_fallback:
                png_path = dst_dir / f"{out_row}_{out_col}.png"
                sub.save(png_path, format='PNG',
                         compress_level=png_compress, optimize=True)
                total_png += png_path.stat().st_size

            sub_count += 1

    return {
        'original':   original_size,
        'total_webp': total_webp,
        'total_png':  total_png,
        'sub_count':  sub_count,
    }


def run(args):
    src_dir = Path(args.input_dir)
    dst_dir = Path(args.out) if args.out else src_dir.parent / (src_dir.name + '_compressed')
    dst_dir.mkdir(parents=True, exist_ok=True)

    tile_out, row_corrections, subtile_size, skipped_rows = load_grid(src_dir)
    split = tile_out // subtile_size

    png_files = sorted(src_dir.glob('*.png'))
    if not png_files:
        print(f"❌  No PNG files in: {src_dir}")
        sys.exit(1)

    out_count = len(png_files) * split * split
    print(f"\n🗜  Compressing {len(png_files)} source tiles → {out_count} output tiles")
    print(f"   Source : {src_dir}")
    print(f"   Output : {dst_dir}")
    print(f"   WebP quality: {args.webp_quality}  |  Split: {split}×{split}"
          f"  ({tile_out}px → {subtile_size}px)")
    print()

    grand_orig = grand_webp = grand_png = 0

    for i, png in enumerate(png_files):
        s = process_tile(png, dst_dir, tile_out, subtile_size, row_corrections,
                         args.webp_quality, args.png_compress, args.png_fallback)
        grand_orig += s['original']
        grand_webp += s['total_webp']
        grand_png  += s['total_png']

        pct = (i + 1) * 100 // len(png_files)
        bar = '#' * (pct // 5) + '.' * (20 - pct // 5)
        print(f"\r  [{bar}] {pct:3d}%  ({i+1}/{len(png_files)})  "
              f"{png.name} → {s['sub_count']} sub-tiles  "
              f"({format_size(s['original'])} → {format_size(s['total_webp'])})",
              end='', flush=True)

    print(f"\n\n✅  Done → {dst_dir.resolve()}")
    print(f"   Source  : {format_size(grand_orig)}  ({len(png_files)} tiles)")
    print(f"   WebP out: {format_size(grand_webp)}  ({out_count} tiles, "
          f"{(1-grand_webp/grand_orig)*100:+.1f}%)")
    if args.png_fallback:
        print(f"   PNG out : {format_size(grand_png)}  "
              f"({(1-grand_png/grand_orig)*100:+.1f}%)")
    print()


def main():
    ap = argparse.ArgumentParser(
        description='Compress PNG tiles → WebP, with optional sub-tile splitting.',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    ap.add_argument('input_dir', nargs='?', default='.',
        help='Directory with PNG tiles (grid.json must be next to this script)')
    ap.add_argument('--out', metavar='DIR',
        help='Output directory (default: <input_dir>_compressed)')
    ap.add_argument('--webp-quality', type=int, default=DEFAULT_WEBP_QUALITY,
        metavar='1-100')
    ap.add_argument('--png-compress', type=int, default=DEFAULT_PNG_COMPRESS,
        metavar='0-9')
    ap.add_argument('--png-fallback', action='store_true',
        help='Also generate optimised PNG alongside WebP')
    main_args = ap.parse_args()
    run(main_args)


if __name__ == '__main__':
    main()
