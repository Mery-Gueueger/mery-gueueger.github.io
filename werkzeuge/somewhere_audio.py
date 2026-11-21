"""Somewhere Only We Know in Gugge-Ablauf schneiden:
Einzählen + Takt 1–52, 33–46, 53–62 (mit Wiederholung) · 4 Takte Schlagzeug (Euphonium-Auftakt im 4.) · 41–48 ·
4 Takte Schlagzeug · 41–48 · 63 bis Schluss."""
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
EU = load("sowk/audio/Somewhere Only We Know - Euphonium.mp3")
rng = np.random.default_rng(7)
def env(n, dec): return np.exp(-np.arange(n) / (dec * SR))
def kick(v=1.0):
    n = smp(0.35); tt = np.arange(n) / SR; f = 45 + 75 * np.exp(-tt * 28)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.11) * 0.9 * v
def snare(v=1.0):
    n = smp(0.22); tt = np.arange(n) / SR
    noise = rng.standard_normal(n); noise = np.convolve(noise, [1, -0.85], "same")
    return (noise * env(n, 0.06) * 0.32 + np.sin(2 * np.pi * 190 * tt) * env(n, 0.04) * 0.35) * v
def hat(v=1.0):
    n = smp(0.06); noise = rng.standard_normal(n); noise = noise - np.convolve(noise, np.ones(4) / 4, "same")
    return noise * env(n, 0.015) * 0.16 * v
def tom(f, v=1.0):
    n = smp(0.3); tt = np.arange(n) / SR; ff = f * (1 + 0.3 * np.exp(-tt * 20))
    return np.sin(2 * np.pi * np.cumsum(ff) / SR) * env(n, 0.12) * 0.6 * v
def drums_clean():
    """4 Takte Schlagzeug ohne Bläser, nachgebaut nach dem Rhythmus der Aufnahme (Takte 37–40):
    Bassdrum auf 1, 2+, 3, 3+, Snare auf 2 und 4, Hi-Hat in Achteln, im 4. Takt ein Wirbel auf den Toms."""
    s16 = BL / 16; y = np.zeros(smp(4 * BL) + smp(0.5))
    def put(sig, pos):
        a = smp(pos); y[a:a + len(sig)] += sig[:len(y) - a]
    for b in range(4):
        base = b * BL
        kicks = [0, 7, 8, 10] + ([13] if b == 1 else [])
        if b == 3: kicks = [0, 7, 8, 10]
        for k in kicks: put(kick(1.7 if k in (0, 8) else 1.4), base + k * s16)  # Pauke (Bassdrum) kräftig
        for k in (4, 12):
            if not (b == 3 and k == 12): put(snare(), base + k * s16)
        for k in range(0, 16, 2):
            if not (b == 3 and k >= 11): put(hat(1.0 if k % 4 == 0 else 0.7), base + k * s16)
    base = 3 * BL
    for k, f in zip((11, 12, 13, 14, 15), (210, 180, 150, 120, 95)): put(tom(f), base + k * s16)
    put(snare(0.8), base + 12 * s16)
    # im letzten Takt vor dem Einsatz: Klick auf jeden Schlag, damit alle wissen, wann es losgeht
    for k in range(4):
        n = smp(0.05); tt = np.arange(n) / SR
        put(np.sin(2 * np.pi * (1760 if k == 0 else 1320) * tt) * env(n, 0.012) * 0.45, base + k * BL / 4)
    y = np.tanh(y[:smp(4 * BL)] * 1.1) / np.tanh(1.1)
    return np.stack([y, y], 1).astype(np.float32) * 0.9
DRUMS = drums_clean()
def drum_block(gd, ge):
    # 4 Takte nur Schlagzeug (sauber, ohne Bläser); im 4. Takt der Euphonium-Auftakt (letzter Schlag von Takt 40)
    y = DRUMS * gd
    if ge:
        a = t(39) + 0.75 * BL
        pick = ramp(EU[smp(a) - smp(0.01):smp(t(40))].copy(), 0.01, 0.02) * ge
        s0 = smp(3.75 * BL) - smp(0.01); y = y.copy(); y[s0:s0 + len(pick)] += pick[:len(y) - s0]
    return y
def build(item):
    pid, src = item
    x = load(src)
    gd, ge = {"drums": (1, 0), "tutti": (1, 1.8), "eup": (0.7, 1.8)}.get(pid, (0.7, 0))  # Euphonium-Auftakt kräftig
    D = drum_block(gd, ge)
    # bis und mit Takt 62 (Position 75), dann Schlagzeug
    parts = [seg(x, 0, t(76), 0, 0.05), D, seg(x, t(40), t(48)), D, seg(x, t(40), t(48)), seg(x, t(76), len(x) / SR, 0.012, 0.3)]  # zum Schluss ab Takt 63
    y = np.clip(np.concatenate(parts), -1, 1).astype(np.float32)
    out = OUT + f"sowk6-{pid}.mp3"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-", "-b:a", "96k", out], input=y.tobytes(), check=True)
    return pid, round(len(y) / SR, 2)
audio = json.loads(sys.argv[3])
with ThreadPoolExecutor(8) as ex:
    for r in ex.map(build, audio.items()): print(r)
print("erwartet mind.", round(off + 105 * BL, 2))
