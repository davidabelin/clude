"""Draw Wikiclude's method diagrams: clude_web/wiki/figures/*.svg.

    .venv\\Scripts\\python.exe scripts\\build_wiki_figures.py

The diagrams are the `DIAGRAMS` registry of
``docs/ux/diagrams/build_diagrams.py``, whose every fact is read from
the live modules. This script draws each with the vendored Mermaid
(``docs/ux/vendor/mermaid.min.js``) in a real browser under Playwright,
then strips everything Mermaid decided about colour and type: its
``<style>`` block and every inline ``style``. What is left is geometry
and class names, which ``clude_web/static/styles/wiki.css`` dresses from
the look's tokens, the way `clude_web.board_svg` and `clude_web.logo`
already emit uncoloured SVG. The result is committed: a maintainer runs
this after a diagram or the code behind it changes, and nothing ships
Mermaid to a reader (``docs/ux/vendor/README.md``).

Run it and then *look* at the wiki pages: a Mermaid syntax error draws a
small box rather than raising, so `build` refuses any diagram with no
nodes, but only eyes catch a diagram that is merely ugly.

Needs Playwright (``pip install playwright`` and ``python -m playwright
install chromium``), as ``clude_shots.py`` does.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "docs" / "ux" / "diagrams"))

import build_diagrams  # noqa: E402

from clude_web.wiki import figures  # noqa: E402

DIRECTION: dict = {"floor-then-method": "TD", "scarlett-update": "TD"}
"""Diagrams redrawn top-down for the wiki: left-to-right they are over
1,200 px wide, which no phone can show."""

CONFIG = """{
  startOnLoad: false, theme: "base", securityLevel: "loose",
  flowchart: { htmlLabels: false, useMaxWidth: false, curve: "basis",
               nodeSpacing: 26, rankSpacing: 34, padding: 10 },
  themeVariables: { fontFamily: "Inter, system-ui, sans-serif", fontSize: "14px" }
}"""
"""``htmlLabels: false`` makes every label SVG text rather than HTML in a
``foreignObject``, so the figure can sit inside a link and take its
type from the page."""


def source(key: str) -> str:
    """A diagram's Mermaid source, turned top-down if the wiki wants it so."""
    text = build_diagrams.DIAGRAMS[key][2]()
    if key in DIRECTION:
        text = re.sub(r"^flowchart \w+", f"flowchart {DIRECTION[key]}", text, count=1)
    return text


def undress(svg: str, key: str, label: str) -> str:
    """Mermaid's SVG without Mermaid's opinions.

    Drops the style block and every inline style, gives the root our
    classes and an accessible name, and prefixes every id with the
    diagram's key, so several diagrams can share one page.
    """
    svg = re.sub(r"<style>.*?</style>", "", svg, flags=re.S)
    svg = re.sub(r'\sstyle="[^"]*"', "", svg)
    root = f"mm-{key}"

    def reid(match):
        name = match.group(1)
        return f'id="{name}"' if name.startswith(root) else f'id="{root}-{name}"'

    svg = re.sub(r'id="([^"]+)"', reid, svg)
    head, rest = svg.split(">", 1)
    box = re.search(r'viewBox="([^"]+)"', head).group(1)
    width = round(float(box.split()[2]))
    height = round(float(box.split()[3]))
    safe = label.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;")
    # The one style we put back: a floor under the width, so that a
    # narrow page scrolls the diagram instead of shrinking its type
    # below three-quarters of its drawn size (wiki.css).
    head = (
        f'<svg class="fig fig-mermaid" id="{root}" viewBox="{box}" width="{width}" height="{height}" '
        f'style="min-width:{round(width * 0.75)}px" role="img" aria-label="{safe}" '
        f'xmlns="http://www.w3.org/2000/svg"'
    )
    return head + ">" + rest


def build(out_dir: Path = figures.FILES) -> list:
    """Draw every diagram; returns the paths written.

    Raises
    ------
    RuntimeError
        If Mermaid drew a diagram with no nodes (a syntax error).
    """
    from playwright.sync_api import sync_playwright

    out_dir.mkdir(parents=True, exist_ok=True)
    library = build_diagrams.VENDOR.read_text(encoding="utf-8")
    written = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        page.set_content("<!doctype html><meta charset='utf-8'><body></body>")
        page.add_script_tag(content=library)
        page.evaluate(f"mermaid.initialize({CONFIG})")
        for key in build_diagrams.DIAGRAMS:
            svg = page.evaluate(
                "async ([id, text]) => (await mermaid.render(id, text)).svg", [f"mm-{key}", source(key)]
            )
            if 'class="node' not in svg:
                raise RuntimeError(f"{key}: Mermaid drew no nodes; its source has a syntax error")
            title = figures.DIAGRAM_TEXT[key][0]
            path = out_dir / f"{key}.svg"
            path.write_text(undress(svg, key, title) + "\n", encoding="utf-8", newline="\n")
            written.append(path)
        browser.close()
    return written


def main() -> None:
    for path in build():
        print(f"wrote {path.relative_to(ROOT)}  ({path.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
