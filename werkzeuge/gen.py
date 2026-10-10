"""Erzeugt die Lieddaten (ABC + Griffe + Aufnahmen) für die App."""
import sys, json, os
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from build import build, abc_pitch, dur_str, NAMES
from extract import DIA

SRC = "/tmp/claude-0/-home-claude-mery-gueueger-github-io/f3f07ede-7612-5b84-8871-ed1e6a2a1a4a/scratchpad/songs2/"

SONGS = [
    dict(id="itd", title="In Too Deep", sub="Sum 41", qpm=116, key="C", offset=0.03 + 8 * 60 / 116,
         parts=[("trp1", "trp", "Trompete 1", "itd/scores/ms341 In Too Deep NUM - Bb Trumpet 1.pdf", "itd/audio/02 ms341 In Too Deep - Trumpet 1.mp3"),
                ("trp2", "trp", "Trompete 2", "itd/scores/ms341 In Too Deep NUM - Bb Trumpet 2.pdf", "itd/audio/03 ms341 In Too Deep - Trumpet 2.mp3"),
                ("pos1", "pos", "Posaune 1", "itd/scores/ms341 In Too Deep NUM - Bb Trombon 1.pdf", "itd/audio/04 ms341 In Too Deep - Trombon 1.mp3"),
                ("pos2", "pos", "Posaune 2", "itd/scores/ms341 In Too Deep NUM - Bb Trombon 2.pdf", "itd/audio/05 ms341 In Too Deep - Trombon 2.mp3"),
                ("eup", "eup", "Euphi", "itd/scores/ms341 In Too Deep NUM - Bb Euphonium.pdf", "itd/audio/06 ms341 In Too Deep - Euphonium.mp3"),
                ("sou", "sou", "Susi", "itd/scores/ms341 In Too Deep NUM - Bb Tuba.pdf", None)],
         tutti="itd/audio/01 ms341 In Too Deep - Tutti.mp3", drums="itd/audio/08 ms341 In Too Deep - Drums.mp3", marks={}),
    dict(id="wanegbt", title="We Are Never Ever Getting Back Together", sub="Taylor Swift", qpm=172, key="A", offset=0.04 + 8 * 60 / 172,
         parts=[("trp1", "trp", "Trompete 1", "wa/we-are-never-ever-getting-back-together-trompete-1.pdf", "wa/We Are Never Ever Getting Back Together-trompete-1.mp3"),
                ("trp2", "trp", "Trompete 2", "wa/we-are-never-ever-getting-back-together-trompete-2.pdf", "wa/We Are Never Ever Getting Back Together-trompete-2.mp3"),
                ("pos1", "pos", "Posaune 1", "wa/we-are-never-ever-getting-back-together-posaune-1.pdf", "wa/We Are Never Ever Getting Back Together-posaune-1.mp3"),
                ("pos2", "pos", "Posaune 2", "wa/we-are-never-ever-getting-back-together-posaune-2.pdf", "wa/We Are Never Ever Getting Back Together-posaune-2.mp3"),
                ("eup", "eup", "Euphi", "wa/we-are-never-ever-getting-back-together-euphonium.pdf", "wa/We Are Never Ever Getting Back Together-euphonium.mp3"),
                ("sou", "sou", "Susi", "wa/we-are-never-ever-getting-back-together-sousaphon.pdf", "wa/We Are Never Ever Getting Back Together-sousaphon.mp3")],
         tutti="wa/We Are Never Ever Getting Back-tutti.mp3", drums="wa/We Are Never Ever Getting Back Together-drms-all.mp3", marks={}),
    dict(id="sowk", title="Somewhere Only We Know", sub="Keane", qpm=86, key="G", offset=0.725 + 8 * 60 / 86,
         parts=[("trp1", "trp", "Trompete 1", None, "sowk/audio/Somewhere Only We Know - Trumpet 1.mp3"),
                ("trp2", "trp", "Trompete 2", None, "sowk/audio/Somewhere Only We Know - Trumpet 2.mp3"),
                ("pos1", "pos", "Posaune 1", "sowk/scores/Somewhere Only We Know NUM - Bb Trombon 1.pdf", "sowk/audio/Somewhere Only We Know - Trombon 1.mp3"),
                ("pos2", "pos", "Posaune 2", "sowk/scores/Somewhere Only We Know NUM - Bb Trombon 2.pdf", "sowk/audio/Somewhere Only We Know - Trombon 2.mp3"),
                ("eup", "eup", "Euphi", "sowk/scores/Somewhere Only We Know NUM - Bb Euphonium.pdf", "sowk/audio/Somewhere Only We Know - Euphonium.mp3"),
                ("sou", "sou", "Susi", None, "sowk/audio/Somewhere Only We Know - Tuba.mp3")],
         tutti="sowk/audio/Somewhere Only We Know - Tutti.mp3", drums="sowk/audio/Somewhere Only We Know - Drums.mp3",
         # Wiederholung Takt 33-52, 1. Klammer 47-52, 2. Klammer ab 53 (Taktindex 0-basiert)
         marks={32: dict(pre="|:"), 46: dict(volta="[1"), 51: dict(post=":|"), 52: dict(volta="[2")}),
]


def grace_abc(g, keysig, local):
    alt = g.get("acc", keysig.get(DIA[g["d"] % 7], 0))
    n = dict(d=g["d"], alt=alt)
    return abc_pitch(n, keysig, local)


def part_abc(model, song, title):
    marks = song["marks"]
    toks_all, fings = [], []
    for bi, bar in enumerate(model["bars"]):
        local = {}
        graces = sorted(bar.get("graces", []), key=lambda g: g["x"])
        toks = []
        for e in bar["ev"]:
            gs = [g for g in graces if g["x"] < e["x"]]
            graces = [g for g in graces if g["x"] >= e["x"]]
            pre = ("{" + "".join(grace_abc(g, bar["keysig"], local) for g in gs) + "}") if gs else ""
            if e["t"] == "r":
                toks.append(pre + "z" + dur_str(e["dur"]))
                continue
            ps = [abc_pitch(n, bar["keysig"], local) for n in e["notes"]]
            ties = [bool(n.get("tie")) for n in e["notes"]]
            if len(ps) == 1:
                tok = ps[0] + dur_str(e["dur"]) + ("-" if ties[0] else "")
            else:
                tok = "[" + "".join(p + ("-" if t else "") for p, t in zip(ps, ties)) + "]" + dur_str(e["dur"])
            toks.append(pre + tok)
            fings.append("/".join(e["fing"]))
        m = marks.get(bi, {})
        s = ""
        if m.get("pre"):
            s += m["pre"] + " "
        if m.get("volta"):
            s += m["volta"] + " "
        s += " ".join(toks)
        s += " " + m.get("post", "|")
        toks_all.append(s)
    body = " ".join(toks_all)
    # Anfang: "|:" direkt nach vorherigem "|" -> "|:" ersetzen
    body = body.replace("| |:", "|:").replace(":| [2", ":|[2").replace("| [1", "|[1").replace("| [2", "|[2")
    if body.endswith("|"):
        body = body[:-1] + "|]"
    head = ["X:1", f"T:{title}", "M:4/4", "L:1/16", f"Q:1/4={song['qpm']}", f"K:{song['key']}"]
    return "\n".join(head) + "\n" + body, fings


def run():
    out = []
    report = []
    for s in SONGS:
        song = dict(id=s["id"], title=s["title"], sub=s["sub"], qpm=s["qpm"], offset=round(s["offset"], 4), parts=[], audio={})
        for pid, instr, name, pdf, mp3 in s["parts"]:
            if mp3 and os.path.getsize(SRC + mp3) > 0:
                song["audio"][pid] = mp3
            if not pdf or not os.path.exists(SRC + pdf) or os.path.getsize(SRC + pdf) == 0:
                continue
            kind = "slide" if instr == "pos" else "valve"
            m = build(SRC + pdf, kind)
            bad = [(i + 1, b["tot"]) for i, b in enumerate(m["bars"]) if b["tot"] != 16]
            assert not bad, (pdf, bad)
            abc, fings = part_abc(m, s, s["title"])
            song["parts"].append(dict(id=pid, instr=instr, name=name, abc=abc, fing=fings, bars=len(m["bars"]), pdf=SRC + pdf))
            for x in m["issues"]:
                if x["pdf"] is not None:
                    report.append((s["title"], name, x))
        if s.get("tutti"):
            song["audio"]["tutti"] = s["tutti"]
        if s.get("drums") and os.path.getsize(SRC + s["drums"]) > 0:
            song["audio"]["drums"] = s["drums"]
        out.append(song)
    return out, report


if __name__ == "__main__":
    songs, report = run()
    json.dump(songs, open(sys.argv[1], "w"), ensure_ascii=False, indent=1)
    for s in songs:
        print(s["title"], [(p["id"], p["bars"], len(p["fing"])) for p in s["parts"]], list(s["audio"]))
    print("Abweichungen PDF:", report)
