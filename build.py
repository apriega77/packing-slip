#!/usr/bin/env python3
"""Build the static site into dist/.

Usage: python build.py
Reads content/, data/, templates/, static/ and pins/out/ (if present).
"""
import json
import re
import shutil
import sys
from datetime import date
from pathlib import Path

import markdown
import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

ROOT = Path(__file__).parent
DIST = ROOT / "dist"


def load(path):
    """Split a markdown file into (frontmatter dict, body text)."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}, text
    _, fm, body = text.split("---", 2)
    # Strip draft-only verification logs (<!-- sources ... -->) before rendering.
    body = re.sub(r"\n<!--\s*sources\b.*?-->\s*$", "", body.strip(), flags=re.DOTALL)
    return yaml.safe_load(fm) or {}, body.strip()


def render_markdown(body, links, warnings, source):
    html = markdown.markdown(
        body,
        extensions=["tables", "smarty"],
        extension_configs={"smarty": {"smart_dashes": False}},
    )
    used_affiliate = False

    def swap(match):
        nonlocal used_affiliate
        key = match.group(1)
        entry = links.get(key)
        if not entry:
            sys.exit(f"{source}: link key '{key}' is not in data/links.json")
        if entry.get("affiliate"):
            used_affiliate = True
            return f'href="{entry["url"]}" rel="sponsored nofollow noopener" target="_blank"'
        warnings.append(f"{source}: '{key}' has no affiliate link yet, using the official site")
        return f'href="{entry["url"]}" rel="noopener" target="_blank"'

    html = re.sub(r'href="aff:([a-z0-9_-]+)"', swap, html)
    html = html.replace(
        "<table>",
        '<div class="table-wrap" role="region" aria-label="Comparison table" tabindex="0"><table>',
    ).replace(
        "</table>", "</table></div>"
    )
    return html, used_affiliate


def fmt_date(value):
    if isinstance(value, date):
        return f"{value.day} {value.strftime('%B %Y')}"
    return str(value)


def main():
    site = json.loads((ROOT / "data/site.json").read_text())
    links = {
        k: v
        for k, v in json.loads((ROOT / "data/links.json").read_text()).items()
        if not k.startswith("_")
    }
    base_url = site["base_url"].rstrip("/")
    env = Environment(
        loader=FileSystemLoader(ROOT / "templates"),
        autoescape=select_autoescape(["html"]),
    )
    env.filters["nice_date"] = fmt_date
    warnings = []

    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir()
    shutil.copytree(ROOT / "static", DIST / "static")
    if (ROOT / "pins/out").exists():
        shutil.copytree(
            ROOT / "pins/out", DIST / "pins", ignore=shutil.ignore_patterns("*.csv")
        )

    posts = []
    for path in sorted((ROOT / "content/posts").glob("*.md")):
        meta, body = load(path)
        if meta.get("draft"):
            continue
        html, has_aff = render_markdown(body, links, warnings, path.name)
        posts.append(
            {**meta, "slug": path.stem, "html": html, "has_affiliate": has_aff,
             "url": f"{base_url}/{path.stem}/"}
        )
    posts.sort(key=lambda p: str(p.get("date", "")), reverse=True)

    pages = []
    for path in sorted((ROOT / "content/pages").glob("*.md")):
        meta, body = load(path)
        html, _ = render_markdown(body, links, warnings, path.name)
        pages.append({**meta, "slug": path.stem, "html": html,
                      "url": f"{base_url}/{path.stem}/"})

    def write(rel, template, **ctx):
        out = DIST / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        depth = len(Path(rel).parts) - 1
        ctx.setdefault("root", "../" * depth or "./")
        ctx.setdefault("current", "")
        ctx.update(site=site, year=date.today().year)
        out.write_text(env.get_template(template).render(**ctx), encoding="utf-8")

    write("index.html", "index.html", posts=posts, canonical=f"{base_url}/", current="home")
    # The 404 page is served at any depth, so its links must be absolute.
    write("404.html", "404.html", canonical="", root=f"{base_url}/")
    for post in posts:
        write(f"{post['slug']}/index.html", "post.html", post=post, canonical=post["url"])
    for page in pages:
        write(f"{page['slug']}/index.html", "page.html", page=page, canonical=page["url"],
              current=page["slug"])

    urls = [f"{base_url}/"] + [p["url"] for p in posts + pages]
    (DIST / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"  <url><loc>{u}</loc></url>\n" for u in urls)
        + "</urlset>\n"
    )
    (DIST / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {base_url}/sitemap.xml\n")

    print(f"Built {len(posts)} post(s), {len(pages)} page(s) into dist/")
    for w in sorted(set(warnings)):
        print("  note:", w)


if __name__ == "__main__":
    main()
