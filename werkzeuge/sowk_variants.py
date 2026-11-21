"""Somewhere Only We Know: Noten für alle Abläufe (Durchspielen, 1–6 Sprünge) erzeugen."""
import sys, json, copy
sys.path.insert(0, "/home/claude/work/omr")
import gen
base = [s for s in gen.SONGS if s["id"] == "sowk"][0]
S = [("S", k) for k in (1, 2, 3, 4)]
VARS = {"d": ("sowkd1", [(1, 52), (33, 46), (53, 67)])}
for n in range(1, 7):
    VARS[f"j{n}"] = ("sowk6" if n == 2 else f"sowkj{n}", [(1, 52), (33, 46), (53, 62)] + (S + [(41, 48)]) * n + [(63, 67)])
out = {}
for k, (aid, order) in VARS.items():
    s = copy.deepcopy(base); s["order"] = order; s["audio_id"] = aid
    gen.SONGS = [s]
    songs, rep = gen.run()
    out[k] = songs[0]
    print(k, aid, len(songs[0]["barnames"]))
json.dump(out, open("/home/claude/work/sowk_vars.json", "w"), ensure_ascii=False)
