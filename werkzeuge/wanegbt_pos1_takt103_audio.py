"""We Are Never, Posaune 1: Takt 103 wie Takt 102 (ganze Note, Zug 1) in die Aufnahme einsetzen."""
import numpy as np, subprocess, sys
src, out = sys.argv[1], sys.argv[2]; SR = 44100
raw = subprocess.run(["ffmpeg", "-v", "error", "-i", src, "-f", "f32le", "-ac", "2", "-ar", str(SR), "-"], capture_output=True).stdout
x = np.frombuffer(raw, np.float32).reshape(-1, 2).copy()
off = 0.04 + 8 * 60 / 172; BL = 4 * 60 / 172
S = lambda a: int(round(a * SR)); t = lambda bar: off + (bar - 1) * BL
n = S(BL); seg = x[S(t(102)):S(t(102)) + n].copy()
e = np.ones(n); e[:S(0.004)] = np.linspace(0, 1, S(0.004)); f = S(0.03); e[-f:] = np.linspace(1, 0, f)
a = S(t(103)); x[a:a + n] += seg * e[:, None]
y = np.clip(x, -1, 1).astype(np.float32)
subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ac", "2", "-ar", str(SR), "-i", "-", "-b:a", "96k", out], input=y.tobytes(), check=True)
for bar in (101, 102, 103, 104):
    m = y[S(t(bar)):S(t(bar + 1)), 0]; print(bar, round(float(np.sqrt(np.mean(m ** 2))), 3))
