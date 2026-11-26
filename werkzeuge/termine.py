"""Termine (Auftritte und Joker-Einsätze) verschlüsselt nach daten/termine.bin schreiben.
Aufruf: GUGGE_PW=… python3 termine.py termine.json
termine.json (nicht ins Repo, enthält Namen): {"hinweis": "...", "termine": [
  {"k": "auftritt", "d": "2027-01-08", "z": "23:00", "t": "Kappeobig", "wer": "Fasnachtsgesellschaft", "ort": "Muri", "info": ""},
  {"k": "einsatz", "d": "2026-10-20", "z": "19:00", "t": "Deko", "ort": "Schulhaus", "chef": "…", "leute": ["…"]} ]}"""
import os, sys, json, base64, hashlib, unicodedata, secrets
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
dd = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "daten")
pw = unicodedata.normalize("NFC", os.environ["GUGGE_PW"]).encode(); meta = json.load(open(os.path.join(dd, "schluessel.json")))
key = hashlib.pbkdf2_hmac("sha256", pw, base64.b64decode(meta["salt"]), meta["iter"], 32)
data = json.load(open(sys.argv[1]))
iv = secrets.token_bytes(12)
open(os.path.join(dd, "termine.bin"), "wb").write(iv + AESGCM(key).encrypt(iv, json.dumps(data, ensure_ascii=False).encode(), None))
print(len(data["termine"]), "Termine")
