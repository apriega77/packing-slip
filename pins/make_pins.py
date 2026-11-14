#!/usr/bin/env python3
"""Generate Pinterest pin images (1000x1500) and a CSV from post frontmatter.

Usage: python pins/make_pins.py [--start YYYY-MM-DD] [--every DAYS]
Output: pins/out/<slug>-<n>.png and pins/out/pins.csv
"""
import argparse
import csv
import json
from datetime import date, timedelta
from pathlib import Path

import yaml
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).parent.parent
OUT = ROOT / "pins/out"
FONTS = ROOT / "pins/fonts"
W, H = 1000, 1500
BAND = 34  # airmail border thickness

INK = "#14233b"
PAPER = "#f1f5f6"
WHITE = "#ffffff"
RED = "#c9362c"
BLUE = "#1f4e9a"
MARIGOLD = "#f0b429"

STYLES = {
    "navy": {"bg": INK, "title": WHITE, "sub": "#c9d4e2", "rule": MARIGOLD},
    "paper": {"bg": PAPER, "title": INK, "sub": "#4a5a72", "rule": RED},
    "marigold": {"bg": MARIGOLD, "title": INK, "sub": INK, "rule": INK},
}


def display_font(size):
    font = ImageFont.truetype(str(FONTS / "Bricolage.ttf"), size)
    font.set_variation_by_axes([96, 800, 100])
    return font


def serif_font(size, weight=400):
    font = ImageFont.truetype(str(FONTS / "SourceSerif4.ttf"), size)
    # Axes order in SourceSerif4.ttf is [Weight, Optical Size].
    font.set_variation_by_axes([weight, min(60, max(8, size))])
    return font


def airmail_frame(img):
    """Draw diagonal red/white/blue stripes around the edge."""
    stripes = Image.new("RGB", (W, H), WHITE)
    d = ImageDraw.Draw(stripes)
    step = 120
    for i, x in enumerate(range(-H, W + H, step // 2)):
        color = RED if i % 2 == 0 else BLUE
        d.polygon([(x, H), (x + 34, H), (x + 34 + H, 0), (x + H, 0)], fill=color)
    mask = Image.new("L", (W, H), 255)
    ImageDraw.Draw(mask).rectangle([BAND, BAND, W - BAND, H - BAND], fill=0)
    img.paste(stripes, (0, 0), mask)


def wrap(draw, text, font, max_width):
    lines, line = [], ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if draw.textlength(trial, font=font) <= max_width:
            line = trial
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def fit_title(draw, text, max_width, max_height):
    for size in range(168, 60, -4):
        font = display_font(size)
        lines = wrap(draw, text, font, max_width)
        height = len(lines) * int(size * 1.04)
        widest = max(draw.textlength(l, font=font) for l in lines)
        if height <= max_height and widest <= max_width and len(lines) <= 7:
            return font, lines, int(size * 1.04)
    font = display_font(64)
    return font, wrap(draw, text, font, max_width), 67


def make_pin(title, style_name, site, path):
    style = STYLES.get(style_name, STYLES["navy"])
    img = Image.new("RGB", (W, H), style["bg"])
    draw = ImageDraw.Draw(img)
    airmail_frame(img)

    margin = BAND + 76
    inner = W - 2 * margin

    # Title block, set large and left aligned. Nothing sits above it.
    top = margin
    bottom_reserved = 250
    font, lines, leading = fit_title(draw, title, inner, H - top - margin - bottom_reserved)
    y = top
    for line in lines:
        draw.text((margin, y), line, font=font, fill=style["title"])
        y += leading

    # Footer: site name over a dashed slip line.
    foot_y = H - margin - 130
    x = margin
    while x < W - margin:
        draw.line([(x, foot_y), (min(x + 18, W - margin), foot_y)], fill=style["sub"], width=3)
        x += 32
    draw.text((margin, foot_y + 34), site["name"], font=display_font(54), fill=style["title"])
    draw.text((margin, foot_y + 104), site["tagline"], font=serif_font(36, weight=600), fill=style["sub"])

    img.save(path, optimize=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default=str(date.today() + timedelta(days=1)))
    ap.add_argument("--every", type=int, default=2, help="days between pins")
    args = ap.parse_args()

    site = json.loads((ROOT / "data/site.json").read_text())
    base = site["base_url"].rstrip("/")
    OUT.mkdir(parents=True, exist_ok=True)
    when = date.fromisoformat(args.start)
    rows = []

    for path in sorted((ROOT / "content/posts").glob("*.md")):
        _, fm, _ = path.read_text(encoding="utf-8").split("---", 2)
        meta = yaml.safe_load(fm)
        if meta.get("draft"):
            continue
        for n, pin in enumerate(meta.get("pins", []), start=1):
            name = f"{path.stem}-{n}.png"
            make_pin(pin["title"], pin.get("style", "navy"), site, OUT / name)
            rows.append({
                "Title": pin["title"],
                "Media URL": f"{base}/pins/{name}",
                "Pinterest board": site["pinterest_board"],
                "Description": pin["description"],
                "Link": f"{base}/{path.stem}/",
                "Publish date": when.isoformat(),
            })
            when += timedelta(days=args.every)

    with open(OUT / "pins.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Made {len(rows)} pin(s) in pins/out/")


if __name__ == "__main__":
    main()
