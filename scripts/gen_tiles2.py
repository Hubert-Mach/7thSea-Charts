#!/usr/bin/env python3
"""
gen_tiles.py - Generator kafelkow PNG dla globe.html / 7th Sea Mappa Mundi

FAR:  8x4   kafelki - kazdy pokrywa 45x45 stopni  (siatka co 15 stopni)
NEAR: 72x36 kafelki - kazdy pokrywa  5x5 stopni   (siatka co  5 stopni)

Uzycie:
  python3 gen_tiles.py <mapa.png> [opcje]

Opcje:
  --no-grid            Wylacz siatke i etykiety
  --grid-color R G B   Kolor linii siatki (domyslnie 255 255 255)
  --grid-alpha A       Przezroczystosc linii 0-255 (domyslnie 120)
  --line-width W       Grubosc linii w px (domyslnie 1)
  --font-size S        Rozmiar czcionki (domyslnie auto)

Wymagania:
  pip install Pillow
"""

import sys
import os
import math
import argparse
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("Brak biblioteki Pillow. Zainstaluj: pip install Pillow")
    sys.exit(1)

# Wylacz limit rozmiaru obrazu (domyslnie ~89 MPx - za malo dla duzych map)
Image.MAX_IMAGE_PIXELS = None

# Konfiguracja widokow (zgodna z VIEWS w globe.html)
VIEWS = {
    'far': {
        'cols': 8,
        'rows': 4,
        'grid_step': 15,
        'desc': '45x45 stopni na kafelek',
    },
    'near': {
        'cols': 72,
        'rows': 36,
        'grid_step': 5,
        'desc': '5x5 stopni na kafelek',
    },
}

GRID_COLOR   = (255, 255, 255)
GRID_ALPHA   = 120
LINE_WIDTH   = 1
LABEL_MARGIN = 3


def fmt_lat(deg):
    hemi = 'N' if deg >= 0 else 'S'
    val  = abs(deg)
    s    = f"{val:.1f}" if val != int(val) else f"{int(val)}"
    return f"{s}'{hemi}"


def fmt_lon(deg):
    deg  = ((deg + 180) % 360 + 360) % 360 - 180
    hemi = 'E' if deg >= 0 else 'W'
    val  = abs(deg)
    s    = f"{val:.1f}" if val != int(val) else f"{int(val)}"
    return f"{s}'{hemi}"


def get_font(size):
    candidates = [
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
        '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf',
        '/usr/share/fonts/truetype/freefont/FreeSansBold.ttf',
        '/System/Library/Fonts/Helvetica.ttc',
        '/Library/Fonts/Arial Bold.ttf',
        'C:/Windows/Fonts/arialbd.ttf',
        'C:/Windows/Fonts/arial.ttf',
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
    return ImageFont.load_default()


def draw_grid_on_tile(draw, tile_w, tile_h,
                      lon0, lon1, lat0, lat1,
                      grid_step, grid_color, grid_alpha, line_width, font):
    gc = grid_color + (grid_alpha,)

    def lon_to_x(lon):
        return (lon - lon0) / (lon1 - lon0) * tile_w

    def lat_to_y(lat):
        return (lat0 - lat) / (lat0 - lat1) * tile_h

    # Poludniki
    first_lon = math.ceil(lon0 / grid_step) * grid_step
    lon = first_lon
    while lon <= lon1 + 1e-9:
        if lon0 + 1e-9 < lon < lon1 - 1e-9:
            x = lon_to_x(lon)
            draw.line([(x, 0), (x, tile_h)], fill=gc, width=line_width)
        lon += grid_step

    # Rownolegniki
    first_lat = math.floor(lat0 / grid_step) * grid_step
    lat = first_lat
    while lat >= lat1 - 1e-9:
        if lat1 + 1e-9 < lat < lat0 - 1e-9:
            y = lat_to_y(lat)
            draw.line([(0, y), (tile_w, y)], fill=gc, width=line_width)
        lat -= grid_step

    # Etykiety naroznikow wylaczone - nazwy plikow wystarczaja


def gen_tiles(src_path, draw_grid=True,
              grid_color=GRID_COLOR, grid_alpha=GRID_ALPHA,
              line_width=LINE_WIDTH, font_size=None):

    src_path = Path(src_path)
    if not src_path.exists():
        print(f"Blad: plik '{src_path}' nie istnieje.")
        sys.exit(1)

    print(f"Wczytywanie: {src_path}")
    with Image.open(src_path) as img:
        src_img = img.convert('RGBA')
        src_w, src_h = src_img.size
    print(f"Rozmiar mapy zrodlowej: {src_w}x{src_h} px")

    for view_name, cfg in VIEWS.items():
        cols      = cfg['cols']
        rows      = cfg['rows']
        grid_step = cfg['grid_step']

        tile_w = src_w // cols
        tile_h = src_h // rows

        target_w = tile_w * cols
        target_h = tile_h * rows

        if (target_w, target_h) != (src_w, src_h):
            print(f"  [{view_name}] Skalowanie {src_w}x{src_h} -> {target_w}x{target_h}")
            scaled = src_img.resize((target_w, target_h), Image.LANCZOS)
        else:
            scaled = src_img.copy()

        fs   = font_size or max(7, min(13, tile_w // 12))
        font = get_font(fs)

        out_dir = Path('tiles') / view_name
        out_dir.mkdir(parents=True, exist_ok=True)

        total       = rows * cols
        lon_per_col = 360.0 / cols
        lat_per_row = 180.0 / rows

        print(f"  [{view_name}] {rows}x{cols} = {total} kafelkow "
              f"({tile_w}x{tile_h} px, siatka co {grid_step} stopni) [{cfg['desc']}]")

        for row in range(rows):
            for col in range(cols):
                x0   = col * tile_w
                y0   = row * tile_h
                tile = scaled.crop((x0, y0, x0 + tile_w, y0 + tile_h))

                if draw_grid:
                    lon0 = -180.0 + col * lon_per_col
                    lon1 = lon0 + lon_per_col
                    lat0 =  90.0 - row * lat_per_row
                    lat1 = lat0 - lat_per_row

                    overlay = Image.new('RGBA', (tile_w, tile_h), (0, 0, 0, 0))
                    drw     = ImageDraw.Draw(overlay)
                    draw_grid_on_tile(
                        drw, tile_w, tile_h,
                        lon0, lon1, lat0, lat1,
                        grid_step, grid_color, grid_alpha, line_width, font
                    )
                    tile = Image.alpha_composite(tile, overlay)

                tile.save(out_dir / f"{row}_{col}.png", 'PNG', optimize=True)

            done = (row + 1) * cols
            pct  = done * 100 // total
            bar  = '#' * (pct // 5) + '.' * (20 - pct // 5)
            print(f"\r    [{bar}] {pct:3d}% ({done}/{total})", end='', flush=True)

        print(f"\r  [{view_name}] OK {total} kafelkow -> {out_dir}/          ")

    print("\nGotowe!")
    print("Uruchom: python3 -m http.server 8000  ->  http://localhost:8000/globe.html")


if __name__ == '__main__':
    ap = argparse.ArgumentParser(
        description='Generator kafelkow PNG z siatka geograficzna dla globe.html'
    )
    ap.add_argument('map',
        help='Mapa equirectangular PNG/JPG (szerokosc = 2 x wysokosc)')
    ap.add_argument('--no-grid', action='store_true',
        help='Wylacz siatke i etykiety naroznikow')
    ap.add_argument('--grid-color', nargs=3, type=int, metavar=('R','G','B'),
        default=list(GRID_COLOR),
        help='Kolor linii RGB (domyslnie 255 255 255)')
    ap.add_argument('--grid-alpha', type=int, default=GRID_ALPHA,
        help='Przezroczystosc linii 0-255 (domyslnie 120)')
    ap.add_argument('--line-width', type=int, default=LINE_WIDTH,
        help='Grubosc linii w px (domyslnie 1)')
    ap.add_argument('--font-size', type=int, default=None,
        help='Rozmiar czcionki etykiet (domyslnie auto)')

    args = ap.parse_args()
    gen_tiles(
        src_path   = args.map,
        draw_grid  = not args.no_grid,
        grid_color = tuple(args.grid_color),
        grid_alpha = args.grid_alpha,
        line_width = args.line_width,
        font_size  = args.font_size,
    )
