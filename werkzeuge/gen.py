"""Erzeugt die Lieddaten (ABC + Griffe + Aufnahmen) für die App."""
import sys, json, os
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from build import build, abc_pitch, dur_str, NAMES, VALVE, WSLIDE
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
    dict(id="fy", title="Forever Young", sub="Alphaville, Ava Max, David Guetta", qpm=130, key="Bb", offset=0.022 + 8 * 60 / 130,
         parts=[("trp1", "trp", "Trompete 1", "fy/forever-young-trompete-1-v3.pdf", "fy/forever-young-trompete-1.mp3"),
                ("trp2", "trp", "Trompete 2", "fy/forever-young-trompete-2-v3.pdf", "fy/forever-young-trompete-2.mp3"),
                ("pos1", "pos", "Posaune 1", "fy/forever-young-posaune-1.pdf", "fy/forever-young-posaune-1.mp3"),
                ("pos2", "pos", "Posaune 2", "fy/forever-young-posaune-2.pdf", "fy/forever-young-posaune-2.mp3"),
                ("eup", "eup", "Euphi", "fy/forever-young-euphonium.pdf", "fy/forever-young-euphonium.mp3"),
                ("sou", "sou", "Susi", "fy/forever-young-sousaphon-v3.pdf", "fy/forever-young-sousaphon.mp3")],
         tutti="fy/forever-young-tutti.mp3", drums="fy/forever-young-drums-all.mp3", marks={},
         # So spielt die Gugge es: zuerst Takt 75 bis 82 (83 fällt weg), dann von vorne bis und mit Takt 75
         order=[(75, 82), (1, 75)], hold_last=True, audio_id="fy5"),
    dict(id="italo", title="Italo Disco", sub="The Kolors", qpm=123, key="D", offset=0.022 + 8 * 60 / 123,
         parts=[("trp1", "trp", "Trompete 1", "id/italodisco-trompete-1-v2.pdf", "id/italo-disco-trompete-1-v2.mp3"),
                ("trp2", "trp", "Trompete 2", "id/italodisco-trompete-2-v2.pdf", "id/italo-disco-trompete-2-v2.mp3"),
                ("pos1", "pos", "Posaune 1", "id/italodisco-posaune-1-v2.pdf", "id/italo-disco-posaune-1-v2.mp3"),
                ("pos2", "pos", "Posaune 2", "id/italodisco-posaune-2-v2.pdf", "id/italo-disco-posaune-2-v2.mp3"),
                ("eup1", "eup", "Euphi 1", "id/italodisco-euphonium-1-v2.pdf", "id/italo-disco-euphonium-1-v2.mp3"),
                ("eup2", "eup", "Euphi 2", "id/italodisco-euphonium-v2-2.pdf", "id/italo-disco-euphonium-v2-2.mp3"),
                ("sou", "sou", "Susi", "id/italodisco-sousaphon-v2.pdf", "id/italo-disco-sousaphon-v2.mp3")],
         tutti="id/italo-disco-tutti-v2.mp3", drums="id/italo-disco-drums-all-v2.mp3", marks={}),
    dict(id="maneater", title="Maneater", sub="Nelly Furtado", qpm=130, key="C", offset=0.022 + 12 * 60 / 130,
         parts=[("trp1", "trp", "Trompete 1", "me/maneater-trompete-1.pdf", "me/maneater-trompete-1.mp3"),
                ("trp2", "trp", "Trompete 2", "me/maneater-trompete-2.pdf", "me/maneater-trompete-2.mp3"),
                ("pos1", "pos", "Posaune 1", "me/maneater-posaune-1.pdf", "me/maneater-posaune-1.mp3"),
                ("pos2", "pos", "Posaune 2", "me/maneater-posaune-2.pdf", "me/maneater-posaune-2.mp3"),
                ("eup", "eup", "Euphi", "me/maneater-euphonium.pdf", "me/maneater-euphonium.mp3"),
                ("sou", "sou", "Susi", "me/maneater-sousaphon.pdf", "me/maneater-sousaphon.mp3")],
         tutti="me/maneater-tutti.mp3", drums="me/maneater-drums-all.mp3", marks={}),
    dict(id="wlto", title="When Love Takes Over", sub="David Guetta", qpm=130, key="Eb", offset=0.022 + 8 * 60 / 130,
         parts=[("trp1", "trp", "Trompete 1", "wl/when-love-takes-over-trompete-1.pdf", "wl/when-love-takes-over-trompete-1.mp3"),
                ("trp2", "trp", "Trompete 2", "wl/when-love-takes-over-trompete-2.pdf", "wl/when-love-takes-over-trompete-2.mp3"),
                ("pos1", "pos", "Posaune 1", "wl/when-love-takes-over-posaune-1.pdf", "wl/when-love-takes-over-posaune-1.mp3"),
                ("pos2", "pos", "Posaune 2", "wl/when-love-takes-over-posaune-2.pdf", "wl/when-love-takes-over-posaune-2.mp3"),
                ("eup", "eup", "Euphi", "wl/when-love-takes-over-euphonium.pdf", "wl/when-love-takes-over-euphonium.mp3"),
                ("trp3", "trp", "Euphi 2 / Trompete 3", "wl/when-love-takes-over-euphonium-2-trp-3.pdf", None, dict(sub="Eigene Aufnahme gibt es keine")),
                ("sou", "sou", "Susi", "wl/when-love-takes-over-sousaphon-v2.pdf", "wl/when-love-takes-over-sousaphon.mp3"),
                ("sou0", "sou", "Susi (andere Fassung)", "wl/when-love-takes-over-sousaphon.pdf", None,
                 dict(sub="Ältere Fassung ohne eigene Aufnahme. Griffe von der App berechnet", calc=True))],
         tutti="wl/when-love-takes-over-tutti.mp3", drums=None, marks={}),
]


def grace_abc(g, keysig, local):
    alt = g.get("acc", keysig.get(DIA[g["d"] % 7], 0))
    n = dict(d=g["d"], alt=alt)
    return abc_pitch(n, keysig, local)


def reorder(model, order, kind, hold_last=False):
    """Takte in neuer Reihenfolge; Haltebögen an den Schnittstellen lösen, dort Griffe neu setzen."""
    import copy
    fmap = WSLIDE if kind == "slide" else VALVE
    src = [i for a, b in order for i in range(a - 1, b)]
    bars = [copy.deepcopy(model["bars"][i]) for i in src]
    for k, bar in enumerate(bars):
        chords = [e for e in bar["ev"] if e["t"] == "c"]
        # Anfang eines Abschnitts: gebundene Töne werden hier neu angespielt
        if (k == 0 or src[k - 1] != src[k] - 1) and bar["ev"] and bar["ev"][0]["t"] == "c":
            e = bar["ev"][0]
            for n in e["notes"]:
                if n.get("cont"):
                    n["cont"] = False; n["fing"] = n.get("pdf") or fmap.get(n["midi"], "?")
            e["cont"] = False
            e["fing"] = [n["fing"] for n in e["notes"] if n.get("fing")]
        # Ende eines Abschnitts: kein Haltebogen ins Leere
        if (k == len(bars) - 1 or src[k + 1] != src[k] + 1) and chords and chords[-1] is bar["ev"][-1]:
            for n in chords[-1]["notes"]:
                n["tie"] = False
    if hold_last:  # Schlusstakt: nur den ersten Ton (oder die Pause) über den ganzen Takt halten
        last = bars[-1]; e = last["ev"][0]; e["dur"] = 16
        if e["t"] == "c":
            for n in e["notes"]:
                n["tie"] = False
        last["ev"] = [e]; last["graces"] = []; last["tot"] = 16
    m = dict(model); m["bars"] = bars
    return m, [i + 1 for i in src]


def part_abc(model, song, title, barnames=None):
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
        if barnames and bi > 0 and barnames[bi] != barnames[bi - 1] + 1:
            s += f"[I:setbarnb {barnames[bi]}] "
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
    if barnames and barnames[0] != 1:
        head.append(f"%%setbarnb {barnames[0]}")
    return "\n".join(head) + "\n" + body, fings


def run():
    out = []
    report = []
    for s in SONGS:
        song = dict(id=s.get("audio_id", s["id"]), title=s["title"], sub=s["sub"], qpm=s["qpm"], offset=round(s["offset"], 4), parts=[], audio={})
        for pt in s["parts"]:
            pid, instr, name, pdf, mp3 = pt[:5]; opt = pt[5] if len(pt) > 5 else {}
            if mp3 and os.path.getsize(SRC + mp3) > 0:
                song["audio"][pid] = mp3
            if not pdf or not os.path.exists(SRC + pdf) or os.path.getsize(SRC + pdf) == 0:
                continue
            kind = "slide" if instr == "pos" else "valve"
            m = build(SRC + pdf, kind)
            if opt.get("calc"):  # gedruckte Zahlen passen nicht zum Instrument: Griffe aus der Tonhöhe
                fmap = WSLIDE if kind == "slide" else VALVE
                m["issues"] = []
                for bar in m["bars"]:
                    for e in bar["ev"]:
                        if e["t"] == "c":
                            for n in e["notes"]:
                                n["fing"] = "" if n["cont"] else fmap.get(n["midi"], "?")
                            e["fing"] = [n["fing"] for n in e["notes"] if n["fing"]]
            bad = [(i + 1, b["tot"]) for i, b in enumerate(m["bars"]) if b["tot"] != 16]
            assert not bad, (pdf, bad)
            names = None
            if s.get("order"):
                m, names = reorder(m, s["order"], kind, s.get("hold_last", False))
                song["barnames"] = names
            abc, fings = part_abc(m, s, s["title"], names)
            if s.get("hold_last"):  # Fermate auf dem gehaltenen Schlusston
                i = abc.rstrip().rfind("| ") + 2
                abc = abc[:i] + "!fermata!" + abc[i:]
            song["parts"].append(dict(id=pid, instr=instr, name=name, abc=abc, fing=fings, bars=len(m["bars"]), pdf=SRC + pdf, **({"sub": opt["sub"]} if opt.get("sub") else {})))
            for x in m["issues"]:
                if x["pdf"] is not None:
                    report.append((s["title"], name, x))
        if s.get("tutti"):
            song["audio"]["tutti"] = s["tutti"]
        if s.get("drums") and os.path.exists(SRC + s["drums"]) and os.path.getsize(SRC + s["drums"]) > 0:
            song["audio"]["drums"] = s["drums"]
        out.append(song)
    return out, report


if __name__ == "__main__":
    songs, report = run()
    json.dump(songs, open(sys.argv[1], "w"), ensure_ascii=False, indent=1)
    for s in songs:
        print(s["title"], [(p["id"], p["bars"], len(p["fing"])) for p in s["parts"]], list(s["audio"]))
    print("Abweichungen PDF:", report)
