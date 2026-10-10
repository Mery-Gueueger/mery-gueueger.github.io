"""Verschlüsselt Lieddaten und Aufnahmen für die App (AES-GCM, Schlüssel aus Passwort per PBKDF2).
Aufruf: python3 encrypt.py <songs.json> <audio-ordner> <repo-ordner>
Das Passwort kommt aus der Umgebungsvariable GUGGE_PW (nie ins Repo schreiben)."""
import os, sys, json, base64, hashlib, unicodedata, secrets
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

songs_path, aud_dir, repo = sys.argv[1:4]
pw = unicodedata.normalize("NFC", os.environ["GUGGE_PW"]).encode("utf-8")
data_dir = os.path.join(repo, "daten")
os.makedirs(data_dir, exist_ok=True)
kfile = os.path.join(data_dir, "schluessel.json")
if os.path.exists(kfile):
    meta = json.load(open(kfile))
    salt = base64.b64decode(meta["salt"])
else:
    salt = secrets.token_bytes(16)
    meta = {"v": 1, "salt": base64.b64encode(salt).decode(), "iter": 250000}
key = hashlib.pbkdf2_hmac("sha256", pw, salt, meta["iter"], 32)
aes = AESGCM(key)


def enc(raw):
    iv = secrets.token_bytes(12)
    return iv + aes.encrypt(iv, raw, None)


songs = json.load(open(songs_path))
# Dateinamen der Aufnahmen: zufällig wirkend, aber stabil (aus Schlüssel + Name abgeleitet)
for s in songs:
    names = {}
    for pid in list(s["audio"].keys()):
        src = os.path.join(aud_dir, f"{s['id']}-{pid}.mp3")
        nm = hashlib.sha256(key + f"{s['id']}-{pid}".encode()).hexdigest()[:16] + ".bin"
        if not os.path.exists(os.path.join(data_dir, nm)):  # vorhandene Aufnahmen nicht neu schreiben
            open(os.path.join(data_dir, nm), "wb").write(enc(open(src, "rb").read()))
        names[pid] = nm
    s["audio"] = names
open(os.path.join(data_dir, "lieder.bin"), "wb").write(enc(json.dumps(songs, ensure_ascii=False).encode("utf-8")))
json.dump(meta, open(kfile, "w"))
print("ok", len(songs), "Lieder")
