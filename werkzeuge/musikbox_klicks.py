"""Einzähl-Klicks am Anfang der Musikbox-Lieder entfernen: Anfang = erster Abschnitt mit ≥ 140 ms durchgehendem Klang."""
import numpy as np, subprocess, sys, os
def start(f):
    raw = subprocess.run(["ffmpeg","-v","error","-t","40","-i",f,"-f","f32le","-ac","1","-ar","22050","-"],capture_output=True).stdout
    x = np.frombuffer(raw,np.float32); w = 441
    r = np.sqrt(np.mean(x[:len(x)//w*w].reshape(-1,w)**2,1)); on = r > 0.01
    for i in range(len(on) - 7):  # 140 ms durchgehend Klang, davon mind. 2 kräftige Stellen (Klicks sind kürzer)
        if on[i:i + 7].all() and (r[i:i + 7] > 0.05).sum() >= 2: return max(0, i * 0.02 - 0.06)
    return 0.0
if __name__ == "__main__":
    for f in sys.argv[1:]: print(round(start(f), 2), os.path.basename(f))
