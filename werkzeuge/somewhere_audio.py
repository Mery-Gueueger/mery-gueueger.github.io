"""Somewhere Only We Know in Gugge-Ablauf schneiden:
Einzählen + Takt 1–52, 33–46, 53–61 (mit Wiederholung) · 4 Takte Schlagzeug (Euphonium-Auftakt im 4.) · 41–48 ·
4 Takte Schlagzeug · 41–48 · 62 bis Schluss."""
import numpy as np, subprocess, json, sys
from concurrent.futures import ThreadPoolExecutor
SRC = sys.argv[1]; OUT = sys.argv[2]; SR = 44100
off = 0.725 + 8 * 60 / 86; BL = 4 * 60 / 86
t = lambda p: off + p * BL               # p = Position in der Aufnahme (Takte, mit Wiederholung gezählt)
smp = lambda s: int(round(s * SR))
def load(f):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", SRC + f, "-ac", "2", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32).reshape(-1, 2).copy()
def ramp(y, fin=0.0, fout=0.0):
    if fin: n = smp(fin); y[:n] *= np.linspace(0, 1, n)[:, None]
    if fout: n = smp(fout); y[-n:] *= np.linspace(1, 0, n)[:, None]
    return y
def seg(x, a, b, fin=0.012, fout=0.04): return ramp(x[smp(a):smp(b)].copy(), fin, fout)
DR = load("sowk/audio/Somewhere Only We Know - Drums.mp3")
EU = load("sowk/audio/Somewhere Only We Know - Euphonium.mp3")
def drum_block(gd, ge):
    # Schlagzeug-Takte 37–40 (endet mit dem Wirbel in Takt 41), im 4. Takt der Euphonium-Auftakt (letzter Schlag von Takt 40)
    y = seg(DR, t(36), t(40), 0.012, 0.03) * gd
    a = t(39) + 0.75 * BL
    pick = ramp(EU[smp(a) - smp(0.01):smp(t(40))].copy(), 0.01, 0.02) * ge
    s0 = smp(3.75 * BL) - smp(0.01); y[s0:s0 + len(pick)] += pick[:len(y) - s0]
    return y
def build(item):
    pid, src = item
    x = load(src)
    gd, ge = {"drums": (1, 0), "tutti": (1, 1), "eup": (0.6, 1)}.get(pid, (0.6, 0.45))
    D = drum_block(gd, ge)
    parts = [seg(x, 0, t(75), 0, 0.05), D, seg(x, t(40), t(48)), D, seg(x, t(40), t(48)), seg(x, t(75), len(x) / SR, 0.012, 0.3)]
    y = np.clip(np.concatenate(parts), -1, 1).astype(np.float32)
    out = OUT + f"sowk2-{pid}.mp3"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-", "-b:a", "96k", out], input=y.tobytes(), check=True)
    return pid, round(len(y) / SR, 2)
audio = json.loads(sys.argv[3])
with ThreadPoolExecutor(8) as ex:
    for r in ex.map(build, audio.items()): print(r)
print("erwartet mind.", round(off + 105 * BL, 2))
