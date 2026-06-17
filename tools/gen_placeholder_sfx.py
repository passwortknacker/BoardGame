"""Generate tiny PROCEDURAL placeholder sound effects for the Godot demo.

These are throwaway 16-bit mono WAVs so the demo has audible feedback before real audio is sourced
(see godot/assets/ART_DIRECTION.md for the real audio plan). Godot imports .wav natively.

Run:  python tools/gen_placeholder_sfx.py
"""
from __future__ import annotations
import math
import os
import struct
import wave

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "godot", "assets", "audio", "sfx")
RATE = 22050


def _write(name: str, samples: list[float]) -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, name + ".wav")
    with wave.open(path, "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        frames = b"".join(struct.pack("<h", int(max(-1.0, min(1.0, s)) * 32000)) for s in samples)
        w.writeframes(frames)


def _env(i: int, n: int, attack=0.01, decay=0.5) -> float:
    """Simple attack/exponential-decay amplitude envelope."""
    t = i / RATE
    total = n / RATE
    a = min(1.0, t / attack) if attack > 0 else 1.0
    d = math.exp(-(t / (total * decay)))
    return a * d


def tone(freq, dur, vol=0.35, kind="sine", decay=0.5, glide=0.0):
    n = int(RATE * dur)
    out = []
    phase = 0.0
    for i in range(n):
        f = freq + glide * (i / n)
        phase += 2 * math.pi * f / RATE
        v = math.sin(phase) if kind == "sine" else (1.0 if math.sin(phase) > 0 else -1.0)
        out.append(v * vol * _env(i, n, decay=decay))
    return out


def noise(dur, vol=0.4, decay=0.3):
    import random
    rng = random.Random(7)
    n = int(RATE * dur)
    return [(rng.uniform(-1, 1)) * vol * _env(i, n, decay=decay) for i in range(n)]


def mix(*tracks):
    n = max(len(t) for t in tracks)
    out = [0.0] * n
    for t in tracks:
        for i, s in enumerate(t):
            out[i] += s
    return out


def main():
    _write("ui_click", tone(1200, 0.05, vol=0.3, kind="square", decay=0.25))
    _write("card_play", mix(noise(0.18, vol=0.25), tone(520, 0.18, vol=0.15, glide=300)))
    _write("hit", mix(tone(150, 0.18, vol=0.45, decay=0.35), noise(0.08, vol=0.15)))
    _write("boss_hit", tone(95, 0.28, vol=0.5, decay=0.45, glide=-40))
    _write("heal", mix(tone(660, 0.3, vol=0.22), tone(880, 0.3, vol=0.18, glide=120)))
    _write("victory", tone(523, 0.12) + tone(659, 0.12) + tone(784, 0.12) + tone(1047, 0.25))
    _write("defeat", tone(300, 0.5, vol=0.4, decay=0.6, glide=-180))
    names = sorted(f for f in os.listdir(OUT_DIR) if f.endswith(".wav"))
    print("wrote %d placeholder SFX to %s:" % (len(names), OUT_DIR))
    for f in names:
        print("   ", f)


if __name__ == "__main__":
    main()
