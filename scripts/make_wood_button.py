"""Make the wooden question-mark button from the yellow one.

``clude_web/static/questionmark.png`` is a glossy yellow push button with
a cream bezel and a white "?". David wanted the same button, lit the
same way, made of wood (2026-09-29), as the link to the Wikiclude pages
in the header bar. This keeps every pixel's lighting and swaps its
material: each pixel's brightness, relative to the part it belongs to,
shades a procedural wood grain -- honey oak on the face, a darker
walnut on the bezel, a pale boxwood inlay for the "?" -- and the dark
outline stays dark, now a burnt groove. Alpha is the original's, less
its faint square shadow.

The pixels are read and written by a browser's canvas (Playwright),
since the project has no imaging library. Deterministic: the grain's
noise is a fixed hash, so the same source gives the same PNG.

    python scripts/make_wood_button.py
"""
from __future__ import annotations

import argparse
import base64
from pathlib import Path

STATIC = Path(__file__).resolve().parent.parent / "clude_web" / "static"
SOURCE = STATIC / "questionmark.png"
TARGET = STATIC / "questionmark-wood.png"

WOOD_JS = r"""
async (url) => {
  const img = new Image();
  img.src = url;
  await img.decode();
  const W = img.width, H = img.height;
  const canvas = document.createElement("canvas");
  canvas.width = W; canvas.height = H;
  const g = canvas.getContext("2d");
  g.drawImage(img, 0, 0);
  const frame = g.getImageData(0, 0, W, H);
  const d = frame.data;

  // Value noise from a fixed integer hash, summed over four octaves.
  const hash = (x, y) => {
    let h = (x * 374761393 + y * 668265263) | 0;
    h = Math.imul(h ^ (h >>> 13), 1274126177);
    return ((h ^ (h >>> 16)) >>> 0) / 4294967295;
  };
  const smooth = (t) => t * t * (3 - 2 * t);
  const noise = (x, y) => {
    const xi = Math.floor(x), yi = Math.floor(y);
    const xf = smooth(x - xi), yf = smooth(y - yi);
    const a = hash(xi, yi), b = hash(xi + 1, yi);
    const c = hash(xi, yi + 1), e = hash(xi + 1, yi + 1);
    return a + (b - a) * xf + (c - a) * yf + (a - b - c + e) * xf * yf;
  };
  const fbm = (x, y) => {
    let sum = 0, amp = 0.5, f = 1;
    for (let i = 0; i < 4; i++) { sum += amp * noise(x * f, y * f); f *= 2; amp /= 2; }
    return sum / 0.9375;
  };
  const clamp = (t) => Math.max(0, Math.min(1, t));
  const mix = (p, q, t) => [0, 1, 2].map((i) => p[i] + (q[i] - p[i]) * t);

  // One wood: light earlywood, dark latewood, the grain's angle, the
  // ring spacing and an offset so no two parts share a figure.
  const woods = {
    face:  { light: [214, 158, 92],  dark: [148, 92, 46],  angle: 0.12, rings: 0.50, seed: 11 },
    bezel: { light: [168, 110, 66],  dark: [92, 54, 30],   angle: 1.35, rings: 0.80, seed: 37 },
    inlay: { light: [246, 230, 192], dark: [222, 196, 150], angle: 0.45, rings: 0.95, seed: 73 },
  };
  const grain = (wood, x, y) => {
    const ca = Math.cos(wood.angle), sa = Math.sin(wood.angle);
    const u = x * ca + y * sa + wood.seed * 17, v = -x * sa + y * ca + wood.seed * 5;
    const warp = fbm(u / 40, v / 40) * 7;
    const ring = 0.5 + 0.5 * Math.sin((v + warp) * wood.rings + fbm(u / 12, v / 6) * 2);
    const fibre = fbm(u / 28, v * 0.9);
    return mix(wood.light, wood.dark, clamp(0.62 * Math.pow(ring, 3) + 0.38 * fibre));
  };

  // Each part's own brightness in the original: what "lit as usual" is,
  // so a pixel brighter than it is a highlight and darker a shadow.
  const REF_FACE = 205, REF_PALE = 240;
  const cx = (W - 1) / 2, cy = (H - 1) / 2, R = W / 2;
  const BEZEL = 0.8;  // the bezel's inner edge, as a fraction of the radius

  for (let y = 0; y < H; y++) {
    for (let x = 0; x < W; x++) {
      const i = (y * W + x) * 4;
      const r = d[i], gr = d[i + 1], b = d[i + 2];
      const hi = Math.max(r, gr, b), lo = Math.min(r, gr, b);
      const lum = 0.299 * r + 0.587 * gr + 0.114 * b;
      const sat = hi ? (hi - lo) / hi : 0;
      // How yellow: the face; the rest is the bezel or the inlay by radius.
      const yellow = clamp((sat - 0.35) / 0.25) * (r > b ? 1 : 0);
      const pale = Math.hypot(x - cx, y - cy) / R > BEZEL ? woods.bezel : woods.inlay;
      const base = mix(grain(pale, x, y), grain(woods.face, x, y), yellow);
      const shade = lum / (REF_PALE + (REF_FACE - REF_PALE) * yellow);
      let out;
      if (shade <= 1) {
        out = base.map((c) => c * shade);
      } else {
        const lift = clamp((shade - 1) * 2.5);
        out = base.map((c) => c + (255 - c) * lift);
      }
      d[i] = Math.round(out[0]); d[i + 1] = Math.round(out[1]); d[i + 2] = Math.round(out[2]);
      // The source's faint shadow (alpha under 10%) ends in a hard square
      // at the image's edge, visible on a dark bar: dropped.
      if (d[i + 3] < 24) d[i + 3] = 0;
    }
  }
  g.putImageData(frame, 0, 0);
  return canvas.toDataURL("image/png");
}
"""


def make(source: Path = SOURCE, target: Path = TARGET) -> int:
    """Write the wooden button; returns its size in bytes."""
    from playwright.sync_api import sync_playwright

    url = "data:image/png;base64," + base64.b64encode(source.read_bytes()).decode("ascii")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            data_url = browser.new_page().evaluate(WOOD_JS, url)
        finally:
            browser.close()
    png = base64.b64decode(data_url.split(",", 1)[1])
    target.write_bytes(png)
    return len(png)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--out", type=Path, default=TARGET)
    args = parser.parse_args()
    size = make(args.source, args.out)
    print(f"{args.out}: {size:,} bytes")


if __name__ == "__main__":
    main()
