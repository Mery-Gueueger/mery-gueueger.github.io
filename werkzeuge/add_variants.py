"""Abläufe (Durchspielen, 1–6 Sprünge) zu Somewhere Only We Know in daten/lieder.bin hinzufügen."""
import os, sys, json, base64, hashlib, unicodedata, secrets
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
repo = sys.argv[1]; aud = sys.argv[2]
pw = unicodedata.normalize("NFC", os.environ["GUGGE_PW"]).encode()
dd = os.path.join(repo, "daten"); meta = json.load(open(os.path.join(dd, "schluessel.json")))
key = hashlib.pbkdf2_hmac("sha256", pw, base64.b64decode(meta["salt"]), meta["iter"], 32); aes = AESGCM(key)
def enc(raw): iv = secrets.token_bytes(12); return iv + aes.encrypt(iv, raw, None)
def dec(b): return aes.decrypt(b[:12], b[12:], None)
name = lambda s: hashlib.sha256(key + s.encode()).hexdigest()[:16] + ".bin"
songs = json.loads(dec(open(os.path.join(dd, "lieder.bin"), "rb").read()))
song = [s for s in songs if s["id"] == "sowk6"][0]
V = json.load(open("/home/claude/work/sowk_vars.json"))
# Kontrolle: j2 entspricht dem bisherigen Ablauf
assert V["j2"]["barnames"] == song["barnames"], "j2 weicht ab"
for a, b in zip(V["j2"]["parts"], song["parts"]): assert a["abc"] == b["abc"], a["id"]
labels = {"d": "Durchspielen"} | {f"j{n}": f"{n}× Sprung" for n in range(1, 7)}
out = []
for k, v in V.items():
    if k == "j2": audio = song["audio"]
    else:
        audio = {}
        for pid in v["audio"]:
            nm = name(f"{v['id']}-{pid}")
            open(os.path.join(dd, nm), "wb").write(enc(open(os.path.join(aud, f"{v['id']}-{pid}.mp3"), "rb").read()))
            audio[pid] = nm
    out.append(dict(key=k, label=labels[k], id=v["id"], barnames=v["barnames"], audio=audio,
                    parts=[dict(id=p["id"], abc=p["abc"], fing=p["fing"], bars=p["bars"]) for p in v["parts"]]))
song["variants"] = out; song["vdef"] = "j2"
song["voltas"] = {"47": "1.", "53": "2."}  # Klammern (erster Takt) für die Markierungen am Balken
open(os.path.join(dd, "lieder.bin"), "wb").write(enc(json.dumps(songs, ensure_ascii=False).encode()))
print("ok", [(o["key"], o["id"], len(o["barnames"])) for o in out])
