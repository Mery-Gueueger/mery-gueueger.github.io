"""Einzelne Takte einer Stimme in daten/lieder.bin ändern und optional eine neue Aufnahme dieser Stimme einsetzen.
Aufruf: GUGGE_PW=… python3 noten_korrektur.py LIED-ID STIMME TAKT "ABC" "Zug/Ventile,…" [neue.mp3 Kennung]
Beispiel (25.11.2026, Wunsch Posaune 1): wanegbt pos1 55 "A8 B2c2 B4" "4,2,4,2" pos1_neu.mp3 v2
Achtung: gen.py erzeugt die Noten neu aus den PDFs – solche Korrekturen danach nochmals ausführen."""
import os, sys, re, json, base64, hashlib, unicodedata, secrets
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."); dd = os.path.join(REPO, "daten")
sid, pid, bar, abc, fing = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4], sys.argv[5].split(",")
pw = unicodedata.normalize("NFC", os.environ["GUGGE_PW"]).encode(); meta = json.load(open(os.path.join(dd, "schluessel.json")))
key = hashlib.pbkdf2_hmac("sha256", pw, base64.b64decode(meta["salt"]), meta["iter"], 32); aes = AESGCM(key)
enc = lambda raw: (lambda iv: iv + aes.encrypt(iv, raw, None))(secrets.token_bytes(12))
dec = lambda b: aes.decrypt(b[:12], b[12:], None)
songs = json.loads(dec(open(os.path.join(dd, "lieder.bin"), "rb").read()))
song = [s for s in songs if s["id"] == sid][0]; part = [p for p in song["parts"] if p["id"] == pid][0]
head, body = part["abc"].split("\nK:", 1); kline, body = body.split("\n", 1)
bars = body.split("|")
count = lambda t: len(re.findall(r"[A-Ga-gz]", t)) - len(re.findall(r"z", t))  # Noten (ohne Pausen) = Einträge in fing
i = bar - 1; before = sum(count(b) for b in bars[:i]); old = bars[i]
print("alt:", old.strip(), part["fing"][before:before + count(old)])
assert count(" " + abc + " ") == len(fing), "Anzahl Noten und Zugangaben stimmt nicht"
bars[i] = " " + abc + " "
part["fing"] = part["fing"][:before] + fing + part["fing"][before + count(old):]
part["abc"] = head + "\nK:" + kline + "\n" + "|".join(bars)
print("neu:", abc, fing)
if len(sys.argv) > 6:
    mp3, tag = sys.argv[6], sys.argv[7]
    nm = hashlib.sha256(key + f"{sid}-{pid}-{tag}".encode()).hexdigest()[:16] + ".bin"
    open(os.path.join(dd, nm), "wb").write(enc(open(mp3, "rb").read()))
    oldf = song["audio"][pid]; song["audio"][pid] = nm
    if oldf != nm and os.path.exists(os.path.join(dd, oldf)): os.remove(os.path.join(dd, oldf))
    print("Aufnahme:", oldf, "→", nm)
open(os.path.join(dd, "lieder.bin"), "wb").write(enc(json.dumps(songs, ensure_ascii=False).encode()))
