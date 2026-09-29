"""Make the table's four sound cues (Phase 10g, docs/phase10-plan.md 11.1).

    python scripts/make_sounds.py

Writes `clude_web/static/sounds/{tick,turn,refute,accent}.wav`: short,
mono, 22.05 kHz, 16-bit, synthesised here from sines and a seeded noise
so the files are the same on every run and owe nothing to anyone's
sample library. Mechanical rather than musical, to fit "engraved, not
brass-plated": a relay's click, a desk bell, a card snapped down, a
struck plate. No music.

- `tick`: a move, or a suggestion nobody could disprove.
- `turn`: a decision has just become yours.
- `refute`: somebody disproved a suggestion.
- `accent`: an accusation, or the end of the game.

Standard library only. `tests/test_web.py` checks the committed files
are well-formed and short; rerun this after changing a recipe.
"""
from __future__ import annotations

import math
import struct
import wave
from pathlib import Path

RATE = 22050
OUT = Path(__file__).resolve().parents[1] / "clude_web" / "static" / "sounds"


def _noise(seed: int):
    """A deterministic white noise in [-1, 1] (a 32-bit LCG)."""
    state = seed & 0xFFFFFFFF
    while True:
        state = (1664525 * state + 1013904223) & 0xFFFFFFFF
        yield state / 0x7FFFFFFF - 1.0


def _partial(t: float, freq: float, tau: float, phase: float = 0.0) -> float:
    """One exponentially decaying sine at time `t` seconds."""
    return math.sin(2 * math.pi * freq * t + phase) * math.exp(-t / tau)


def _attack(t: float, rise: float) -> float:
    """A short linear fade-in, so no cue starts with a click of its own."""
    return min(1.0, t / rise) if rise > 0 else 1.0


def tick(n: int) -> list:
    """A relay's click: a 2 ms burst of noise over two damped sines."""
    noise = _noise(7)
    out = []
    for i in range(n):
        t = i / RATE
        burst = next(noise) * math.exp(-t / 0.0015)
        body = 0.8 * _partial(t, 2400, 0.008) + 0.6 * _partial(t, 1150, 0.016)
        out.append((0.7 * burst + body) * _attack(t, 0.0004))
    return out


def turn(n: int) -> list:
    """A desk bell: a struck partial and two inharmonic overtones."""
    out = []
    for i in range(n):
        t = i / RATE
        ring = (
            _partial(t, 1320, 0.42)
            + 0.45 * _partial(t, 1320 * 2.76, 0.16, 0.3)
            + 0.2 * _partial(t, 1320 * 5.4, 0.06, 1.1)
        )
        out.append(ring * _attack(t, 0.002))
    return out


def refute(n: int) -> list:
    """A card snapped onto the table: a band of noise and a low thump."""
    noise = _noise(11)
    low = high = previous = 0.0
    out = []
    for i in range(n):
        t = i / RATE
        x = next(noise)
        low += 0.35 * (x - low)                   # one-pole low-pass
        high = 0.85 * (high + low - previous)     # one-pole high-pass over it
        previous = low
        snap = high * math.exp(-t / 0.028)
        thump = 0.9 * _partial(t, 165, 0.055)
        out.append((1.4 * snap + thump) * _attack(t, 0.0015))
    return out


def accent(n: int) -> list:
    """A struck brass plate: a low note with slow inharmonic partials
    beating against each other, over a soft thud."""
    out = []
    for i in range(n):
        t = i / RATE
        plate = (
            _partial(t, 98, 0.9)
            + 0.6 * _partial(t, 98.6 * 2.52, 0.6, 0.4)
            + 0.4 * _partial(t, 98 * 4.1, 0.35, 0.9)
            + 0.25 * _partial(t, 98 * 6.3, 0.18, 1.7)
        )
        thud = 0.7 * _partial(t, 60, 0.05)
        out.append((plate + thud) * _attack(t, 0.004))
    return out


CUES = {
    "tick": (tick, 0.07, 0.45),
    "turn": (turn, 0.75, 0.40),
    "refute": (refute, 0.22, 0.50),
    "accent": (accent, 1.40, 0.55),
}
"""Cue -> (recipe, seconds, peak level). The peaks leave the loudest
cue at about -5 dBFS, and the volume control scales them all."""


def render(name: str) -> bytes:
    """One cue as 16-bit little-endian PCM, normalised to its peak and
    faded over its last 10 ms."""
    recipe, seconds, level = CUES[name]
    n = int(RATE * seconds)
    samples = recipe(n)
    peak = max(abs(s) for s in samples) or 1.0
    fade = int(RATE * 0.01)
    frames = bytearray()
    for i, s in enumerate(samples):
        gain = level / peak * min(1.0, (n - i) / fade)
        frames += struct.pack("<h", max(-32767, min(32767, round(s * gain * 32767))))
    return bytes(frames)


def main() -> int:
    """Write every cue and say how big each came out."""
    OUT.mkdir(parents=True, exist_ok=True)
    for name in CUES:
        path = OUT / f"{name}.wav"
        with wave.open(str(path), "wb") as out:
            out.setnchannels(1)
            out.setsampwidth(2)
            out.setframerate(RATE)
            out.writeframes(render(name))
        print(f"{path.relative_to(OUT.parents[2])}: {path.stat().st_size:,} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
