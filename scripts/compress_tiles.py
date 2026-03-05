#!/usr/bin/env python3
"""
compress_tiles.py — Optymalizator kafli PNG dla aplikacji webowych
Konwertuje PNG → WebP (+ opcjonalnie zoptymowane PNG jako fallback)

Użycie:
    python compress_tiles.py [KATALOG_WEJŚCIOWY] [opcje]

Przykłady:
    python compress_tiles.py ./tiles
    python compress_tiles.py ./tiles --out ./tiles_compressed
    python compress_tiles.py ./tiles --webp-quality 80 --no-png-fallback
    python compress_tiles.py ./tiles --max-size 512

Wymagania:
    pip install Pillow
"""

import argparse
import sys
from pathlib import Path
from PIL import Image

# ── Konfiguracja domyślna ────────────────────────────────────────────────────
DEFAULT_WEBP_QUALITY  = 82   # 75-85 to sweet spot: świetna jakość, mały rozmiar
DEFAULT_PNG_COMPRESS  = 9    # 0-9, 9 = maksymalna kompresja (bezstratna)
DEFAULT_MAX_SIZE      = None # np. 512 — przeskaluje kafle powyżej tej szerokości/wysokości
# ─────────────────────────────────────────────────────────────────────────────


def format_size(bytes_: int) -> str:
    if bytes_ < 1024:
        return f"{bytes_} B"
    elif bytes_ < 1024 ** 2:
        return f"{bytes_ / 1024:.1f} KB"
    else:
        return f"{bytes_ / 1024**2:.2f} MB"


def compress_tile(
    src: Path,
    dst_dir: Path,
    webp_quality: int,
    png_compress: int,
    max_size: int | None,
    png_fallback: bool,
) -> dict:
    """Kompresuje jeden plik PNG. Zwraca słownik ze statystykami."""
    original_size = src.stat().st_size
    img = Image.open(src)

    # Opcjonalne przeskalowanie (zachowuje proporcje)
    if max_size and (img.width > max_size or img.height > max_size):
        img.thumbnail((max_size, max_size), Image.LANCZOS)
        resized = True
    else:
        resized = False

    # Konwersja trybu jeśli potrzeba (np. paletowy P → RGBA)
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGBA")

    results = {}

    # ── WebP ──────────────────────────────────────────────────────────────────
    webp_path = dst_dir / src.with_suffix(".webp").name
    img.save(
        webp_path,
        format="WEBP",
        quality=webp_quality,
        method=6,          # wolniejsza, ale lepsza kompresja
        lossless=False,
    )
    webp_size = webp_path.stat().st_size
    results["webp"] = {
        "path": webp_path,
        "size": webp_size,
        "saving_pct": (1 - webp_size / original_size) * 100,
    }

    # ── PNG fallback (bezstratny, tylko lepsza kompresja) ─────────────────────
    if png_fallback:
        png_path = dst_dir / src.name
        img.save(
            png_path,
            format="PNG",
            compress_level=png_compress,
            optimize=True,
        )
        png_size = png_path.stat().st_size
        results["png"] = {
            "path": png_path,
            "size": png_size,
            "saving_pct": (1 - png_size / original_size) * 100,
        }

    return {
        "src": src,
        "original_size": original_size,
        "resized": resized,
        "results": results,
    }


def run(args):
    src_dir  = Path(args.input_dir)
    dst_dir  = Path(args.out) if args.out else src_dir.parent / (src_dir.name + "_compressed")
    dst_dir.mkdir(parents=True, exist_ok=True)

    png_files = sorted(src_dir.glob("*.png"))
    if not png_files:
        print(f"❌  Nie znaleziono plików PNG w: {src_dir}")
        sys.exit(1)

    print(f"\n🗜  Kompresja {len(png_files)} kafli PNG")
    print(f"   Źródło : {src_dir}")
    print(f"   Cel    : {dst_dir}")
    print(f"   WebP quality : {args.webp_quality}  |  PNG compress : {args.png_compress}")
    if args.max_size:
        print(f"   Max rozmiar  : {args.max_size}px")
    print()

    total_original = 0
    total_webp     = 0
    total_png      = 0
    resized_count  = 0

    col_w = max(len(f.name) for f in png_files) + 2

    # Nagłówek tabeli
    header = f"{'Plik':<{col_w}} {'Oryginał':>10}  {'WebP':>10}  {'Oszczędność':>12}"
    if not args.no_png_fallback:
        header += f"  {'PNG opt':>10}  {'Oszczędność':>12}"
    print(header)
    print("─" * len(header))

    for png in png_files:
        stats = compress_tile(
            src         = png,
            dst_dir     = dst_dir,
            webp_quality= args.webp_quality,
            png_compress= args.png_compress,
            max_size    = args.max_size,
            png_fallback= not args.no_png_fallback,
        )

        orig = stats["original_size"]
        webp = stats["results"]["webp"]["size"]
        wpct = stats["results"]["webp"]["saving_pct"]

        total_original += orig
        total_webp     += webp
        if stats["resized"]:
            resized_count += 1

        line = (
            f"{png.name:<{col_w}} "
            f"{format_size(orig):>10}  "
            f"{format_size(webp):>10}  "
            f"{wpct:>+11.1f}%"
        )

        if not args.no_png_fallback:
            png_s = stats["results"]["png"]["size"]
            ppct  = stats["results"]["png"]["saving_pct"]
            total_png += png_s
            line += f"  {format_size(png_s):>10}  {ppct:>+11.1f}%"

        suffix = " 🔄" if stats["resized"] else ""
        print(line + suffix)

    # Podsumowanie
    print("─" * len(header))
    total_wpct = (1 - total_webp / total_original) * 100
    summary = (
        f"{'SUMA':<{col_w}} "
        f"{format_size(total_original):>10}  "
        f"{format_size(total_webp):>10}  "
        f"{total_wpct:>+11.1f}%"
    )
    if not args.no_png_fallback:
        total_ppct = (1 - total_png / total_original) * 100
        summary += f"  {format_size(total_png):>10}  {total_ppct:>+11.1f}%"
    print(summary)

    print(f"\n✅  Gotowe! Pliki zapisane w: {dst_dir.resolve()}")
    if resized_count:
        print(f"   🔄 {resized_count} kafli przeskalowanych do max {args.max_size}px")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Kompresuje kafle PNG do WebP (i opcjonalnie zoptymowanego PNG).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "input_dir",
        nargs="?",
        default=".",
        help="Katalog z plikami PNG",
    )
    parser.add_argument(
        "--out",
        metavar="DIR",
        help="Katalog wyjściowy (domyślnie: <input_dir>_compressed)",
    )
    parser.add_argument(
        "--webp-quality",
        type=int,
        default=DEFAULT_WEBP_QUALITY,
        metavar="1-100",
        help="Jakość WebP (75-85 = sweet spot jakość/rozmiar)",
    )
    parser.add_argument(
        "--png-compress",
        type=int,
        default=DEFAULT_PNG_COMPRESS,
        metavar="0-9",
        help="Poziom kompresji PNG fallback (9 = max, bezstratna)",
    )
    parser.add_argument(
        "--max-size",
        type=int,
        default=DEFAULT_MAX_SIZE,
        metavar="PX",
        help="Maksymalny wymiar kafla w pikselach (przeskalowuje jeśli większy)",
    )
    parser.add_argument(
        "--no-png-fallback",
        action="store_true",
        help="Generuj tylko WebP, bez zoptymowanego PNG",
    )
    args = parser.parse_args()
    run(args)


if __name__ == "__main__":
    main()
