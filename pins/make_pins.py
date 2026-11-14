#!/usr/bin/env python3
"""Generate Pinterest pin images (1000x1500), CSV, and RSS 2.0 feed from post frontmatter.

Usage: python pins/make_pins.py [--start YYYY-MM-DD] [--every DAYS] [--today YYYY-MM-DD]
Output: pins/out/<slug>-<n>.png, pins/out/pins.csv, and pins/out/feed.xml
"""
import argparse
import csv
import json
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta, timezone
from email.utils import format_datetime
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


def rfc822(day):
    """Format a date as an RFC 822 UTC timestamp matching the 01:00 UTC build."""
    return format_datetime(
        datetime(day.year, day.month, day.day, 1, 0, 0, tzinfo=timezone.utc)
    )


def write_feed(site, base, items, today, path):
    """Write an RSS 2.0 feed of due pins for Pinterest Auto-publish."""
    rss = ET.Element("rss", version="2.0")
    channel = ET.SubElement(rss, "channel")
    ET.SubElement(channel, "title").text = site["name"]
    ET.SubElement(channel, "link").text = f"{base}/"
    ET.SubElement(channel, "description").text = site["description"]
    ET.SubElement(channel, "language").text = "en"
    ET.SubElement(channel, "lastBuildDate").text = rfc822(today)

    for item in items:
        el = ET.SubElement(channel, "item")
        ET.SubElement(el, "title").text = item["title"]
        ET.SubElement(el, "description").text = item["description"]
        ET.SubElement(el, "link").text = item["link"]
        guid = ET.SubElement(el, "guid", isPermaLink="false")
        guid.text = item["guid"]
        ET.SubElement(el, "pubDate").text = rfc822(item["pub_date"])
        ET.SubElement(
            el,
            "enclosure",
            url=item["media_url"],
            type="image/png",
            length=str(item["length"]),
        )

    ET.indent(rss, space="  ")
    ET.ElementTree(rss).write(path, encoding="utf-8", xml_declaration=True)


def main():
    site = json.loads((ROOT / "data/site.json").read_text())
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--start",
        default=site.get("pin_start") or str(date.today() + timedelta(days=1)),
    )
    ap.add_argument(
        "--every",
        type=int,
        default=site.get("pin_every", 2),
        help="days between pins",
    )
    ap.add_argument(
        "--today",
        default=str(date.today()),
        help="override today's date (YYYY-MM-DD) for feed drip testing",
    )
    args = ap.parse_args()

    base = site["base_url"].rstrip("/")
    OUT.mkdir(parents=True, exist_ok=True)
    when = date.fromisoformat(args.start)
    today = date.fromisoformat(args.today)
    rows = []
    feed_items = []

    for path in sorted((ROOT / "content/posts").glob("*.md")):
        _, fm, _ = path.read_text(encoding="utf-8").split("---", 2)
        meta = yaml.safe_load(fm)
        if meta.get("draft"):
            continue
        held = bool(meta.get("pin_hold"))
        article_url = f"{base}/{path.stem}/"
        for n, pin in enumerate(meta.get("pins", []), start=1):
            name = f"{path.stem}-{n}.png"
            png_path = OUT / name
            make_pin(pin["title"], pin.get("style", "navy"), site, png_path)
            media_url = f"{base}/pins/{name}"
            rows.append({
                "Title": pin["title"],
                "Media URL": media_url,
                "Pinterest board": site["pinterest_board"],
                "Description": pin["description"],
                "Link": article_url,
                "Publish date": when.isoformat(),
            })
            if not held and when <= today:
                feed_items.append({
                    "title": pin["title"],
                    "description": pin["description"],
                    "link": article_url,
                    "media_url": media_url,
                    "length": png_path.stat().st_size,
                    "guid": f"{path.stem}-{n}",
                    "pub_date": when,
                })
            when += timedelta(days=args.every)

    if rows:
        with open(OUT / "pins.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
    write_feed(site, base, feed_items, today, OUT / "feed.xml")
    print(f"Made {len(rows)} pin(s), {len(feed_items)} feed item(s) in pins/out/")


if __name__ == "__main__":
    main()
