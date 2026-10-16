"""Forever Young in Gugge-Reihenfolge schneiden: Einzähler, Takt 75-82, Takt 1-74, Schlusstakt 75 als gehaltener Klang."""
import numpy as np, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
S = sys.argv[1]; SR = 44100
off = 0.022 + 8 * 60 / 130; BL = 4 * 60 / 130
t = lambda n: off + (n - 1) * BL
smp = lambda s: int(round(s * SR))
SRC = {'trp1': ('forever-young-trompete-1.mp3', False), 'trp2': ('forever-young-trompete-2.mp3', True), 'pos1': ('forever-young-posaune-1.mp3', True),
       'pos2': ('forever-young-posaune-2.mp3', False), 'eup': ('forever-young-euphonium.mp3', False), 'sou': ('forever-young-sousaphon.mp3', False),
       'tutti': ('forever-young-tutti.mp3', True), 'drums': ('forever-young-drums-all.mp3', False)}

def load(f):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", f, "-ac", "2", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32).reshape(-1, 2).copy()

def ramp(n, up):
    r = 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, n))
    return (r if up else r[::-1])[:, None]

def seg(x, a, b, fin=0.0, fout=0.0):
    y = x[smp(a):smp(a) + (smp(b) - smp(a))].copy()
    if fin: n = smp(fin); y[:n] *= ramp(n, True)
    if fout: n = smp(fout); y[-n:] *= ramp(n, False)
    return y

def hold_bar(x, freeze):
    """Schlusstakt: ab Taktanfang den ersten Klang über den ganzen Takt, gegen Schluss ausklingen."""
    a = t(75); L = smp(BL)
    if not freeze:
        y = x[smp(a):smp(a) + L].copy()
    else:
        c0, c1, xf = 0.20, 0.42, 0.07  # ruhiges Stück zwischen erstem und zweitem Schlag (ohne Klick)
        y = x[smp(a):smp(a + c1)].copy()
        chunk = x[smp(a + c0):smp(a + c1)]; n = smp(xf)
        while len(y) < L:
            # gleichmässig überblenden (gleiche Leistung)
            th = np.linspace(0, np.pi / 2, n)[:, None]
            y[-n:] = y[-n:] * np.cos(th) + chunk[:n] * np.sin(th)
            y = np.concatenate([y, chunk[n:]])
        y = y[:L]
    # Lautstärke: bis knapp zur Taktmitte voll, dann weich bis zum Taktende ausklingen
    k = np.ones(L); s0 = int(L * 0.45)
    k[s0:] = 0.5 + 0.5 * np.cos(np.linspace(0, np.pi, L - s0))
    return y * k[:, None]

def job(item):
    pid, (f, freeze) = item
    x = load(S + 'songs2/fy/' + f)
    parts = [seg(x, 0, off),
             seg(x, t(75), t(83), 0.015, 0.05),
             seg(x, t(1), t(75)),
             hold_bar(x, freeze),
             np.zeros((smp(0.6), 2), np.float32)]
    y = np.concatenate(parts).astype(np.float32)
    out = S + f'aud/fy5-{pid}.mp3'
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-", "-b:a", "96k", out], input=y.tobytes(), check=True)
    return pid, round(len(y) / SR, 3)

with ThreadPoolExecutor(8) as ex:
    for r in ex.map(job, SRC.items()): print(r)
print('erwartet', round(off + 83 * BL + 0.6, 3))
