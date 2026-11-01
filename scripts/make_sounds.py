"""Make the table's sound cues (Phase 10g, docs/phase10-plan.md 11.1).

    python scripts/make_sounds.py

Writes `clude_web/static/sounds/{tick,turn,refute,accent,door,passage}.wav`: short,
mono, 22.05 kHz, 16-bit cues. The generated cues use sines and seeded
noise; the door cue is shaped from the public-domain recording noted
below. Mechanical rather than musical, to fit "engraved, not
brass-plated": a relay's click, a desk bell, a card snapped down, a
struck plate. No music.

- `tick`: a move, or a suggestion nobody could disprove.
- `turn`: a decision has just become yours.
- `refute`: somebody disproved a suggestion.
- `accent`: an accusation, or the end of the game.
- `door`: a token going into a room through a door (2026-10-01): a
  real squeaky-door recording, trimmed and sped up to fit the board's
  swing, with its solid closing thud near the end.
  Source: LeonMire, “Squeaky door.ogg” (PDSounds record 505), public
  domain: https://commons.wikimedia.org/wiki/File:Squeaky_door.ogg
- `door-knock` and `door-soft` (2026-11-01): the door cue's two other
  voices. `static/sound.js` plays the file for the page's look: `door` for
  Gaslight dark, `door-knock` (one knuckle-rap on wood) for Developer, and
  `door-soft` (a muffled latch, wooden bars rising on the open and
  falling home on the shut) for Case-file light. Both are synthesized.
- `passage`: a token taking a secret passage: stone dragged aside, a
  hollow draught under it, and a low settle.

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
DOOR_SOURCE = Path(__file__).resolve().parent / "assets" / "door-source.wav"


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


def _resonator(freq: float, r: float):
    """A two-pole resonator: send it a sample, get the ringing back."""
    c = 2 * r * math.cos(2 * math.pi * freq / RATE)
    y1 = y2 = 0.0

    def step(x: float) -> float:
        nonlocal y1, y2
        y = x + c * y1 - r * r * y2
        y2, y1 = y1, y
        return y

    return step


def door(n: int) -> list:
    """The door-source excerpt, warmed and sped up slightly to fit a move.

    The 1.5-second source cut contains the hinge squeak and the real
    closing impact. A short, quiet echo adds a wooden twang; extra bass
    is mixed into the closing tail. Resampling places the impact near the
    end of the board's swing.
    """
    with wave.open(str(DOOR_SOURCE), "rb") as source:
        if (source.getnchannels(), source.getsampwidth(), source.getframerate()) != (1, 2, RATE):
            raise ValueError(f"unexpected door source format: {DOOR_SOURCE}")
        raw = source.readframes(source.getnframes())
    source_samples = [sample[0] / 32768.0 for sample in struct.iter_unpack("<h", raw)]
    last = len(source_samples) - 1
    if last < 1 or n < 2:
        raise ValueError("door source and cue must each contain at least two samples")
    scale = last / (n - 1)
    out = []
    for i in range(n):
        position = i * scale
        left = int(position)
        fraction = position - left
        right = min(left + 1, last)
        out.append(source_samples[left] * (1 - fraction) + source_samples[right] * fraction)
    fade_in = round(0.008 * RATE)
    for i in range(fade_in):
        out[i] *= i / fade_in
    # A faint 24 ms reflection lends the squeak some wood without making
    # the closing impact echo. A low shelf rises only around the thud.
    delay = round(0.024 * RATE)
    bass_alpha = 1 - math.exp(-2 * math.pi * 280 / RATE)
    bass = 0.0
    for i, sample in enumerate(out):
        t = i / RATE
        bass += bass_alpha * (sample - bass)
        if t < 0.78 and i >= delay:
            sample += 0.13 * out[i - delay]
        if t >= 0.82:
            sample += 0.65 * min(1.0, (t - 0.82) / 0.18) * bass
        out[i] = sample

    # The source has about 100 ms of low-level room noise after the hinge
    # has settled and before the closing impact. Keep a short 5 ms crossfade
    # at the join, then move the impact forward while retaining cue duration.
    gap_start = round(1.08 * RATE)
    gap_end = round(1.18 * RATE)
    crossfade = round(0.005 * RATE)
    if gap_end + crossfade < len(out):
        join = [
            out[gap_start - crossfade + i] * (1 - i / crossfade)
            + out[gap_end + i] * (i / crossfade)
            for i in range(crossfade)
        ]
        out = out[:gap_start - crossfade] + join + out[gap_end + crossfade:]
        out.extend([0.0] * (n - len(out)))
    return out


def knock(n: int) -> list:
    """One knuckle-rap on a wooden door, for the Developer look: a brief
    skin-on-grain contact over four fast-dying panel modes, with no
    hinge, no latch and no echo. Plain on purpose: Developer's board has
    no leaf to swing, so the cue is only a mark that a token came in."""
    noise = _noise(41)
    low = 0.0
    out = []
    for i in range(n):
        t = i / RATE
        low += 0.40 * (next(noise) - low)             # one-pole low-pass, about 1.8 kHz
        contact = low * math.exp(-t / 0.0022)
        body = (
            1.00 * _partial(t, 205, 0.040)
            + 0.85 * _partial(t, 388, 0.028, 0.4)
            + 0.55 * _partial(t, 640, 0.018, 1.0)
            + 0.28 * _partial(t, 1020, 0.010, 2.1)
        )
        out.append((0.9 * contact + body) * _attack(t, 0.0006))
    return out


def _bar(t: float, onset: float, freq: float, tau: float) -> float:
    """A struck wooden bar at `freq`, sounding from `onset`: a round
    fundamental with the 4th and 10th partials a marimba bar carries,
    which is what makes a pure tone read as wood."""
    u = t - onset
    if u < 0:
        return 0.0
    ring = (
        _partial(u, freq, tau)
        + 0.30 * _partial(u, 4 * freq, tau * 0.22)
        + 0.08 * _partial(u, 10 * freq, tau * 0.06)
    )
    return ring * _attack(u, 0.006)


def door_soft(n: int) -> list:
    """The Case-file light door: a soft open and a soft shut, tuned.

    Opening, a muffled latch and a breath of air, with wooden bars
    rising A3, E4, A4 (an open fifth and its octave) as the leaf swings
    clear. Shutting, a felt thud under bars falling D4, A3, D3, so the
    pair reads as a cadence from the dominant home to the tonic: an
    ending, not a slam. The close lands at 0.98 s, as the board's leaf
    (1.1 s swing, `--dur-door`) comes back to the frame."""
    noise = _noise(53)
    latch = breath = thud = 0.0
    phase = 0.0
    out = []
    close = 0.98
    for i in range(n):
        t = i / RATE
        x = next(noise)
        latch += 0.25 * (x - latch)                    # about 1 kHz
        breath += 0.06 * (x - breath)                  # a dark rush
        thud += 0.15 * (x - thud)
        opening = 0.30 * latch * math.exp(-t / 0.010)
        air = 0.0
        if t < 0.55:
            air = 0.085 * breath * math.sin(math.pi * t / 0.55) ** 2 * 6
        rising = (
            0.80 * _bar(t, 0.00, 220.0, 0.21)
            + 0.55 * _bar(t, 0.06, 329.63, 0.19)
            + 0.25 * _bar(t, 0.12, 440.0, 0.15)
        )
        shut = 0.0
        if t >= close:
            u = t - close
            phase += 2 * math.pi * (70 + 50 * math.exp(-u / 0.03)) / RATE    # a falling thump
            shut = (
                0.85 * math.sin(phase) * math.exp(-u / 0.07) * _attack(u, 0.003)
                + 0.35 * thud * math.exp(-u / 0.008)
                + 0.45 * _bar(t, close, 293.66, 0.22)
                + 0.60 * _bar(t, close + 0.05, 220.0, 0.22)
                + 0.70 * _bar(t, close + 0.10, 146.83, 0.24)
            )
        tail = 1.0
        end = n / RATE
        if t > end - 0.12:
            tail = 0.5 * (1 + math.cos(math.pi * (t - (end - 0.12)) / 0.12))
        out.append((opening + air + rising + shut) * _attack(t, 0.003) * tail)
    return out


def passage(n: int) -> list:
    """A secret passage: a stone slab dragged aside (filtered noise,
    grinding), a hollow draught beneath (a low tone wavering), swelling
    and dying away, and a soft settle at the end. Nothing like the door,
    so the two are told apart by ear."""
    noise = _noise(31)
    low = 0.0
    hollow = _resonator(210, 0.996)
    out = []
    for i in range(n):
        t = i / RATE
        x = next(noise)
        low += 0.08 * (x - low)                        # a dark noise
        swell = math.sin(math.pi * min(1.0, t / 0.95)) ** 2 if t < 0.95 else 0.0
        grind = low * (0.6 + 0.4 * math.sin(2 * math.pi * 11 * t)) * swell
        draught = 0.012 * hollow(low) * swell
        tone = 0.35 * math.sin(2 * math.pi * 73 * t + 0.6 * math.sin(2 * math.pi * 4.5 * t)) * swell
        settle = 0.0
        if t >= 0.92:
            u = t - 0.92
            settle = 0.7 * _partial(u, 82, 0.07) + 0.3 * x * math.exp(-u / 0.006)
        out.append((1.6 * grind + draught + tone + settle) * _attack(t, 0.02))
    return out


CUES = {
    "tick": (tick, 0.07, 0.45),
    "turn": (turn, 0.75, 0.40),
    "refute": (refute, 0.22, 0.50),
    "accent": (accent, 1.40, 0.55),
    "door": (door, 1.35, 0.52),
    "door-knock": (knock, 0.32, 0.55),
    "door-soft": (door_soft, 1.45, 0.26),
    "passage": (passage, 1.25, 0.50),
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
