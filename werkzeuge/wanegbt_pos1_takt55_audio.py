"""We Are Never, Posaune 1: Takt 55 neu (Halbe A, Achtel B, Achtel c#, Viertel B – Zug 4 2 4 2) in die Aufnahme einsetzen."""
import numpy as np, subprocess, sys
src, out = sys.argv[1], sys.argv[2]
SR = 44100
raw = subprocess.run(["ffmpeg", "-v", "error", "-i", src, "-f", "f32le", "-ac", "2", "-ar", str(SR), "-"], capture_output=True).stdout
x = np.frombuffer(raw, np.float32).reshape(-1, 2).copy()
off = 0.04 + 8 * 60 / 172; BL = 4 * 60 / 172; B = BL / 4
t = lambda bar, beat=0: off + (bar - 1) * BL + beat * B
S = lambda a: int(round(a * SR))
def cut(a, dur):  # Ausschnitt ab Sekunde a
    return x[S(a):S(a) + S(dur)].copy()
def shift(seg, semis, dur):  # Tonhöhe per Umrechnen der Abtastrate
    r = 2 ** (semis / 12); n = S(dur); idx = np.arange(n) * r
    return np.stack([np.interp(idx, np.arange(len(seg)), seg[:, c]) for c in (0, 1)], 1)
def env(seg, fin=0.006, fout=0.05):
    n = len(seg); e = np.ones(n); a = S(fin); b = S(fout)
    e[:a] = np.linspace(0, 1, a); e[n - b:] = np.linspace(1, 0, b); return seg * e[:, None]
rms = lambda s: float(np.sqrt(np.mean(s ** 2)) + 1e-9)
ref = rms(cut(t(55, 0.3), 3 * B))  # Lautstärke des bisherigen Tons
G = cut(t(4, 0), 4 * B)            # Takt 4: ganze Note A (Zug 4)
notes = []
half = env(cut(t(4, 0), 1.9 * B), 0.004, 0.08)                  # Halbe A
e1 = env(cut(t(11, 2.0), 0.47 * B), 0.004, 0.03)                # Takt 11: Achtel B (Zug 2)
e2 = env(cut(t(11, 2.5), 0.47 * B), 0.012, 0.03)                # Takt 11: c# (Zug 4), erste Achtel davon
q = env(shift(cut(t(4, 0.2), 2 * B), 2, 0.92 * B), 0.012, 0.06)  # Viertel B: A einen Ganzton höher
parts = [(0, half), (2, e1), (2.5, e2), (3, q)]
a0, a1 = S(t(55)), S(t(56))
fade = S(0.015)
newbar = np.zeros((a1 - a0 + fade, 2))
for beat, seg in parts:
    seg = seg * (ref / rms(seg))
    p = S(beat * B); n = min(len(seg), len(newbar) - p); newbar[p:p + n] += seg[:n]
y = x.copy()
# alter Ton weg: kurzes Ausblenden vor Takt 55, neuer Takt, nahtlos in Takt 56
ramp = np.linspace(1, 0, fade)[:, None]
y[a0 - fade:a0] *= ramp
y[a0:a1] = newbar[: a1 - a0]
y[a1:a1 + fade] = y[a1:a1 + fade] + newbar[a1 - a0:]
y = np.clip(y, -1, 1).astype(np.float32)
subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ac", "2", "-ar", str(SR), "-i", "-", "-b:a", "96k", out], input=y.tobytes(), check=True)
# Kontrolle: Tonhöhen der neuen Noten
for beat, d in [(0.3, 1.2), (2.05, 0.35), (2.55, 0.35), (3.1, 0.6)]:
    m = y[S(t(55, beat)):S(t(55, beat + d)), 0]; ac = np.correlate(m, m, "full")[len(m) - 1:]; lo, hi = SR // 500, SR // 60
    print(beat, round(SR / (lo + np.argmax(ac[lo:hi])), 1))
