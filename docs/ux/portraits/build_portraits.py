"""Build the portraits' contact sheet: docs/ux/portraits/index.html.

    .venv\\Scripts\\python.exe docs\\ux\\portraits\\build_portraits.py

The six busts of `clude_web/wiki/portraits.py`, on a light and a dark
panel, painted by the real rules: the ``.fig`` rules of wiki.css and the
suspect colours of engraved.css's light and dark tokens, inlined so the
page opens from disk in any browser.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

from clude_core.domain import SUSPECTS  # noqa: E402
from clude_web.wiki import figures  # noqa: E402

STYLES = ROOT / "clude_web" / "static" / "styles"


def _suspect_tokens(css: str) -> tuple:
    """engraved.css's light and dark suspect colours, as two blocks."""
    blocks = re.findall(r"((?:\s*--suspect-[a-z]+(?:-ink)?:\s*#[0-9A-Fa-f]{6};\s*)+)", css)
    lines = [re.findall(r"--suspect-[a-z]+(?:-ink)?:\s*#[0-9A-Fa-f]{6};", b) for b in blocks]
    full = [ln for ln in lines if len(ln) >= 12]
    return " ".join(full[0]), " ".join(full[1])


def build() -> Path:
    wiki = (STYLES / "wiki.css").read_text(encoding="utf-8")
    fig_rules = "\n".join(line for line in wiki.splitlines() if line.startswith(".fig .pt-") or line.startswith(".fig .s-"))
    light, dark = _suspect_tokens((STYLES / "engraved.css").read_text(encoding="utf-8"))
    cards = []
    for suspect in SUSPECTS:
        fig = figures.figure(f"portrait-{suspect.lower()}")
        cards.append(f'<figure>{fig.svg}<figcaption>{fig.title}</figcaption></figure>')
    row = "".join(cards)
    page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Portraits: contact sheet</title>
<style>
body {{ margin: 0; padding: 28px; background: #2b282c; color: #d9d3c7; font: 14px/1.5 Inter, system-ui, sans-serif; }}
h1 {{ font: 600 24px/1.2 Georgia, serif; color: #f0c67e; margin: 0 0 6px; }}
p {{ color: #a9a090; max-width: 62em; }}
.panel {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(190px, 1fr)); gap: 18px; padding: 20px; margin: 0 0 28px; border-radius: 3px; }}
.light {{ background: #F5F0E4; color: #22201a; {light} }}
.dark {{ background: #1B181C; color: #EDE6D8; {dark} }}
figure {{ margin: 0; text-align: center; }}
svg {{ width: 100%; height: auto; }}
figcaption {{ font-size: 13px; margin-top: 4px; }}
{fig_rules}
</style></head><body>
<h1>The six, sketched</h1>
<p>Cartoon busts for the character articles' infoboxes (Wikiclude, Phase 12 N7). Clothes take each suspect's
colour from the look; skin, hair and props keep one palette in light and dark. Drawn by
<code>clude_web/wiki/portraits.py</code>; this page by <code>docs/ux/portraits/build_portraits.py</code>.</p>
<h2>Case-file light</h2><div class="panel light">{row}</div>
<h2>Gaslight dark</h2><div class="panel dark">{row}</div>
</body></html>
"""
    out = HERE / "index.html"
    out.write_text(page, encoding="utf-8")
    return out


if __name__ == "__main__":
    print(f"wrote {build()}")
