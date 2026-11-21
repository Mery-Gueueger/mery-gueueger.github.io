"""Ein Lied in daten/lieder.bin ersetzen, ohne alle anderen neu zu erzeugen.
Aufruf: GUGGE_PW=… python3 replace_song.py <lied.json> <alte_id> <audio-ordner> <repo>"""
import os, sys, json, base64, hashlib, unicodedata, secrets
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
song_path, old_id, aud_dir, repo = sys.argv[1:5]
pw = unicodedata.normalize("NFC", os.environ["GUGGE_PW"]).encode()
dd = os.path.join(repo, "daten"); meta = json.load(open(os.path.join(dd, "schluessel.json")))
key = hashlib.pbkdf2_hmac("sha256", pw, base64.b64decode(meta["salt"]), meta["iter"], 32); aes = AESGCM(key)
def enc(raw): iv = secrets.token_bytes(12); return iv + aes.encrypt(iv, raw, None)
def dec(b): return aes.decrypt(b[:12], b[12:], None)
name = lambda s: hashlib.sha256(key + s.encode()).hexdigest()[:16] + ".bin"
songs = json.loads(dec(open(os.path.join(dd, "lieder.bin"), "rb").read()))
new = json.load(open(song_path))[0]
idx = [i for i, s in enumerate(songs) if s["id"] == old_id][0]
old = songs[idx]
# alte Dateien entfernen
for pid in old["audio"]:
    f = os.path.join(dd, name(f"{old_id}-{pid}"))
    if os.path.exists(f): os.remove(f)
for pt in old["parts"]:
    for pg in pt.get("pages", []):
        f = os.path.join(dd, pg)
        if os.path.exists(f): os.remove(f)
# neue Aufnahmen
names = {}
for pid in new["audio"]:
    nm = name(f"{new['id']}-{pid}")
    open(os.path.join(dd, nm), "wb").write(enc(open(os.path.join(aud_dir, f"{new['id']}-{pid}.mp3"), "rb").read()))
    names[pid] = nm
new["audio"] = names
import pymupdf
for pt in new["parts"]:
    src = pt.pop("pdf", None)
    if not src: continue
    pages = []
    for i, pg in enumerate(pymupdf.open(src)):
        nm = name(f"{new['id']}-{pt['id']}-s{i + 1}")
        open(os.path.join(dd, nm), "wb").write(enc(pg.get_pixmap(dpi=170, colorspace=pymupdf.csGRAY).tobytes("png")))
        pages.append(nm)
    pt["pages"] = pages
songs[idx] = new
open(os.path.join(dd, "lieder.bin"), "wb").write(enc(json.dumps(songs, ensure_ascii=False).encode()))
print("ok", [s["id"] for s in songs])
