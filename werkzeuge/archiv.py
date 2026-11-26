"""Musikbox (alte Lieder, nur Tutti): Lied hinzufügen oder ersetzen.
Aufruf: GUGGE_PW=… python3 archiv.py DATEI.mp3 "Titel" ["Interpret"] ["2026,2025" = Jahre, in denen wir es gespielt haben]
Hängt 2 s Stille an (Pause bis zum nächsten Lied). Legt die Aufnahme verschlüsselt in daten/ ab und ergänzt daten/archiv.bin (Liste der Lieder)."""
import os, sys, re, json, base64, hashlib, unicodedata, secrets, subprocess, tempfile
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
dd = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "daten")
src, title = sys.argv[1], sys.argv[2]; sub = sys.argv[3] if len(sys.argv) > 3 else ""
years = [int(v) for v in sys.argv[4].split(",")] if len(sys.argv) > 4 and sys.argv[4] else None
pw = unicodedata.normalize("NFC", os.environ["GUGGE_PW"]).encode(); meta = json.load(open(os.path.join(dd, "schluessel.json")))
key = hashlib.pbkdf2_hmac("sha256", pw, base64.b64decode(meta["salt"]), meta["iter"], 32); aes = AESGCM(key)
enc = lambda raw: (lambda iv: iv + aes.encrypt(iv, raw, None))(secrets.token_bytes(12))
dec = lambda b: aes.decrypt(b[:12], b[12:], None)
ab = os.path.join(dd, "archiv.bin")
lst = json.loads(dec(open(ab, "rb").read())) if os.path.exists(ab) else []
slug = re.sub(r"[^a-z0-9]+", "-", unicodedata.normalize("NFKD", title.lower()).encode("ascii", "ignore").decode()).strip("-")
with tempfile.TemporaryDirectory() as td:
    out = os.path.join(td, "a.mp3")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-map", "0:a", "-map_metadata", "-1", "-af", "apad=pad_dur=2", "-ac", "2", "-ar", "44100", "-b:a", "128k", out], check=True)
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", out], capture_output=True, text=True).stdout)
    raw = open(out, "rb").read()
ver = hashlib.sha256(raw).hexdigest()[:8]  # neue Datei bei geänderter Aufnahme (Zwischenspeicher)
nm = hashlib.sha256(key + f"archiv-{slug}-{ver}".encode()).hexdigest()[:16] + ".bin"
open(os.path.join(dd, nm), "wb").write(enc(raw))
old = [x for x in lst if x["id"] == slug]
for x in old:
    if x["f"] != nm and os.path.exists(os.path.join(dd, x["f"])): os.remove(os.path.join(dd, x["f"]))
if years is None: years = old[0].get("y", []) if old else []
lst = [x for x in lst if x["id"] != slug] + [dict(id=slug, t=title, s=sub, f=nm, d=round(dur, 1), y=years)]
lst.sort(key=lambda x: (-min(x.get("y") or [0]), x["t"].lower()))  # nach dem ersten Jahr, neueste zuerst
open(ab, "wb").write(enc(json.dumps(lst, ensure_ascii=False).encode()))
print(len(lst), "Lieder:", ", ".join(x["t"] for x in lst))
