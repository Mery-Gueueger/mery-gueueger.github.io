"""Liest Noten aus Sibelius/Finale-PDFs (Musikschrift als Text-Glyphen) aus.
Ausgabe: JSON mit Systemen, Takten, Ereignissen (Noten/Pausen), Ventilzahlen."""
import pymupdf, sys, json, re

MUSIC_FONTS = ("OpusStd", "Maestro", "OpusSpecialStd", "Opus")
HEADS = {"œ": "q", "˙": "h", "w": "w"}
RESTS = {"Œ": 4, "Ó": 8, "∑": 16, "‰": 2, "≈": 1}
ACC = {"#": 1, "b": -1, "n": 0}
DIA = "CDEFGAB"


def dia_to_name(d):  # diatonic index: 0 = C0
    return DIA[d % 7], d // 7


def load(path):
    doc = pymupdf.open(path)
    pages = []
    for pi, p in enumerate(doc):
        glyphs, texts = [], []
        for b in p.get_text("rawdict")["blocks"]:
            for l in b.get("lines", []):
                for s in l["spans"]:
                    for c in s["chars"]:
                        if c["c"] == " ":
                            continue
                        g = dict(c=c["c"], x=c["origin"][0], y=c["origin"][1], size=s["size"], font=s["font"],
                                 x1=c["bbox"][2], y0=c["bbox"][1], y1=c["bbox"][3])
                        (glyphs if s["font"].startswith(MUSIC_FONTS) else texts).append(g)
        lines, fills, curves = [], [], []
        for dr in p.get_drawings():
            kinds = "".join(i[0] for i in dr["items"])
            r = dr["rect"]
            if "c" in kinds:
                curves.append(dict(x0=r.x0, y0=r.y0, x1=r.x1, y1=r.y1, items=dr["items"]))
            elif dr["type"] in ("f", "fs") and kinds.replace("l", "") in ("", "re", "qu") or (dr["type"] in ("f", "fs") and ("re" in kinds or "qu" in kinds)):
                fills.append(dict(x0=r.x0, y0=r.y0, x1=r.x1, y1=r.y1, items=dr["items"]))
            else:
                for it in dr["items"]:
                    if it[0] == "l":
                        a, b2 = it[1], it[2]
                        lines.append(dict(x0=a.x, y0=a.y, x1=b2.x, y1=b2.y, w=dr.get("width") or 0))
                    elif it[0] == "re":
                        rr = it[1]
                        fills.append(dict(x0=rr.x0, y0=rr.y0, x1=rr.x1, y1=rr.y1, items=[]))
        pages.append(dict(glyphs=glyphs, texts=texts, lines=lines, fills=fills, curves=curves, width=p.rect.width))
    return pages


def yslice(f, x):
    verts = []
    for it in f["items"]:
        if it[0] == "l":
            if not verts:
                verts.append((it[1].x, it[1].y))
            verts.append((it[2].x, it[2].y))
        elif it[0] == "qu":
            q = it[1]; verts += [(q.ul.x, q.ul.y), (q.ur.x, q.ur.y), (q.lr.x, q.lr.y), (q.ll.x, q.ll.y)]
    if len(verts) < 3:
        return (f["y0"], f["y1"])
    ys = []
    n = len(verts)
    for k in range(n):
        x1, y1 = verts[k]; x2, y2 = verts[(k + 1) % n]
        if abs(x2 - x1) < 1e-6:
            if abs(x1 - x) < 0.6:
                ys += [y1, y2]
            continue
        if min(x1, x2) - 0.3 <= x <= max(x1, x2) + 0.3:
            t = min(max((x - x1) / (x2 - x1), 0), 1)
            ys.append(y1 + t * (y2 - y1))
    return (min(ys), max(ys)) if ys else None


def staves(pg):
    hs = [l for l in pg["lines"] if abs(l["y0"] - l["y1"]) < 0.3 and abs(l["x1"] - l["x0"]) > 200]
    ys = sorted(set(round(l["y0"], 1) for l in hs))
    out, i = [], 0
    while i + 4 < len(ys):
        grp = ys[i:i + 5]
        gaps = [grp[k + 1] - grp[k] for k in range(4)]
        if max(gaps) - min(gaps) < 0.6 and 1.5 < gaps[0] < 12:
            xs = [l for l in hs if abs(l["y0"] - grp[0]) < 0.3]
            out.append(dict(top=grp[0], bot=grp[4], half=(grp[4] - grp[0]) / 8,
                            x0=min(l["x0"] for l in xs), x1=max(l["x1"] for l in xs)))
            i += 5
        else:
            i += 1
    return out


def analyze(path, clef_override=None):
    pages = load(path)
    systems = []
    for pi, pg in enumerate(pages):
        STS = staves(pg)
        def mine(st, y):
            c = (st["top"] + st["bot"]) / 2
            return all(abs(y - c) <= abs(y - (o["top"] + o["bot"]) / 2) + 0.01 for o in STS)
        for st in STS:
            top, bot, half = st["top"], st["bot"], st["half"]
            sp = 2 * half
            lo, hi = top - 7 * sp, bot + 7 * sp
            G = [g for g in pg["glyphs"] if lo <= g["y"] <= hi and st["x0"] - 5 <= g["x"] <= st["x1"] + 5 and mine(st, g["y"])]
            # nach oben/unten zu nahe System-Nachbarn begrenzen: nur Glyphen, deren y näher an diesem System liegt
            # Taktstriche
            HG = [g for g in G if g["c"] in HEADS]
            near_head = lambda x: any(g["x"] - 1.5 <= x <= g["x1"] + 1.5 for g in HG)
            vls = [l["w"] for l in pg["lines"] if abs(l["x0"] - l["x1"]) < 0.3 and 1.8 * sp < abs(l["y1"] - l["y0"]) < 9 * sp]
            import collections as _c
            STEMW = _c.Counter(round(w, 2) for w in vls).most_common(1)[0][0] if vls else 0.4
            bars = sorted(set(round(l["x0"], 1) for l in pg["lines"]
                              if abs(l["x0"] - l["x1"]) < 0.3 and ((abs(min(l["y0"], l["y1"]) - top) < 1 and abs(max(l["y0"], l["y1"]) - bot) < 1 and (l["w"] > STEMW + 0.1 or not near_head(l["x0"])))
                                  or (min(l["y0"], l["y1"]) <= top + 0.5 and max(l["y0"], l["y1"]) >= bot - 0.5 and abs(l["y1"] - l["y0"]) > (bot - top) + 4
                                      and (not near_head(l["x0"]) or abs(l["y1"] - l["y0"]) > 2.5 * (bot - top))))))
            thick = [f for f in pg["fills"] if f["y0"] <= top + 1.5 and f["y1"] >= bot - 1.5 and (f["x1"] - f["x0"]) < 6 and st["x0"] + 5 < f["x0"] <= st["x1"] + 1]
            bars = sorted(set(bars + [round((f["x0"] + f["x1"]) / 2, 1) for f in thick]))
            # zusammenfassen (Doppelstriche)
            bx = []
            for b in bars:
                if bx and b - bx[-1][-1] < 12:
                    bx[-1].append(b)
                else:
                    bx.append([b])
            barxs = [(min(b), max(b), len(b)) for b in bx]
            # Schlüssel
            clefg = sorted([g for g in G if g["c"] in "&V?" and g["size"] > 3.0 * sp], key=lambda g: g["x"])
            clef = clefg[0]["c"] if clefg else "&"
            if clef_override:
                clef = clef_override
            refd = {"&": 4 * 7 + 4, "V": 4 * 7 + 4, "?": 3 * 7 + 3}[clef]  # G4 (V: wie Violinschlüssel gelesen), F3
            refy = {"&": bot - sp, "V": bot - sp, "?": top + sp}[clef]
            # Tonart: Vorzeichen vor dem ersten Notenkopf/Pause/Taktart, direkt nach dem Schlüssel
            heads = sorted([g for g in G if g["c"] in HEADS and g["size"] > 1.5 * sp], key=lambda g: g["x"])
            restg = sorted([g for g in G if g["c"] in RESTS and g["size"] > 3.0 * sp], key=lambda g: g["x"])
            firstx = min([g["x"] for g in heads + restg] + [st["x1"]])
            for f in pg["fills"]:
                if abs((f["y0"] + f["y1"]) / 2 - (top + bot) / 2) < 2 and (f["x1"] - f["x0"]) > 20 and 2 < (f["y1"] - f["y0"]) < 3 * sp and st["x0"] < f["x0"] < st["x1"]:
                    firstx = min(firstx, f["x0"])
            for l in pg["lines"]:
                if abs(l["y0"] - l["y1"]) < 0.3 and abs(l["y0"] - (top + bot) / 2) < 1.5 and l["w"] > 1.5 and abs(l["x1"] - l["x0"]) > 20 and st["x0"] < l["x0"] < st["x1"]:
                    firstx = min(firstx, min(l["x0"], l["x1"]))
            tsig = [g for g in G if g["c"].isdigit() and g["size"] > 3.4 * sp and g["x"] < firstx and abs(g["y"] - (top + bot) / 2) < sp * 2.5]
            if tsig:
                firstx = min(firstx, min(g["x"] for g in tsig))
            clefx = clefg[0]["x1"] if clefg else st["x0"]
            keyacc = [g for g in G if g["c"] in "#b" and clefx - 1 <= g["x"] < firstx]
            keysig = {}
            for g in keyacc:
                d = refd + round((refy - g["y"]) / half)
                keysig[DIA[d % 7]] = ACC[g["c"]]
            ts = None
            if tsig:
                t = sorted(tsig, key=lambda g: g["y"])
                ts = (t[0]["c"], t[-1]["c"]) if len(t) >= 2 else (t[0]["c"],)
            # Halse
            stems = [l for l in pg["lines"] if abs(l["x0"] - l["x1"]) < 0.3 and 1.8 * sp < abs(l["y1"] - l["y0"]) < 9 * sp
                     and lo <= min(l["y0"], l["y1"]) and max(l["y0"], l["y1"]) <= hi and l["w"] < 0.7]
            beams = [f for f in pg["fills"] if (f["x1"] - f["x0"]) > 0.6 * sp and 0.3 * sp < (f["y1"] - f["y0"]) < 7 * sp
                     and lo <= f["y0"] and f["y1"] <= hi and not (abs(f["y0"] - top) < 1.5 and abs(f["y1"] - bot) < 1.5)]
            events = []
            for g in heads:
                if g["x"] < firstx - 1 and False:
                    continue
                d = refd + round((refy - g["y"]) / half)
                hw = g["x1"] - g["x"]
                kind = HEADS[g["c"]]
                ev = dict(t="n", x=g["x"], y=g["y"], d=d, head=kind, hw=hw, small=g["size"] < 3.0 * sp)
                # Hals suchen
                cand = [s for s in stems if (abs(s["x0"] - g["x"]) < 0.26 * sp or (g["x"] + hw - 0.48 * sp) < s["x0"] < (g["x"] + hw + 0.26 * sp))
                        and min(s["y0"], s["y1"]) - 2 <= g["y"] <= max(s["y0"], s["y1"]) + 2]
                nb = 0
                if cand:
                    s = cand[0]
                    ya, yb = min(s["y0"], s["y1"]), max(s["y0"], s["y1"])
                    far = ya if abs(yb - g["y"]) < abs(ya - g["y"]) else yb
                    up = far < g["y"]
                    ev["stem"] = dict(x=s["x0"], far=far, up=up)
                    for bm in beams:
                        if bm["x0"] - 1.0 <= s["x0"] <= bm["x1"] + 1.0:
                            sl = yslice(bm, min(max(s["x0"], bm["x0"]), bm["x1"]))
                            if not sl:
                                continue
                            ymin, ymax = sl
                            if up and far - 1.5 <= ymin <= far + 2.6 * sp and ymax < g["y"] - 2:
                                nb += 1
                            elif (not up) and far - 2.6 * sp <= ymax <= far + 1.5 and ymin > g["y"] + 2:
                                nb += 1
                ev["beams"] = nb
                events.append(ev)
            for g in restg:
                events.append(dict(t="r", x=g["x"], y=g["y"], dur=RESTS[g["c"]], c=g["c"]))
            # Fähnchen
            for g in G:
                if g["c"] in "JjKkrR" and g["size"] > 1.5 * sp:
                    # zugehörige Note: Hals-x gleich
                    best = None
                    for ev in events:
                        if ev["t"] == "n" and "stem" in ev and abs(ev["stem"]["x"] - g["x"]) < 0.45 * sp:
                            best = ev
                    if best:
                        best["flag"] = 2 if g["c"] in "KkrR" else 1
                    else:
                        # Pause mit Fähnchen? (z.B. ‰ zusammengesetzt) -> Hinweis
                        pass
            # Punkte
            dots0 = [g for g in G if g["c"] in ("™", ".", "k") and g["font"].startswith(MUSIC_FONTS)]
            rep = []
            for g in dots0:
                for o in dots0:
                    if o is not g and abs(o["x"] - g["x"]) < 0.6 and abs(abs(o["y"] - g["y"]) - sp) < 1.2 and abs((o["y"] + g["y"]) / 2 - (top + bot) / 2) < 1.5:
                        rep.append(g)
            dots = [g for g in dots0 if g not in rep]
            repeats = []
            for g in rep:
                bxl = [b for b in barxs]
                near = min(bxl, key=lambda b: min(abs(b[0] - g["x"]), abs(b[1] - g["x"]))) if bxl else None
                kind = "end" if near and g["x"] < near[0] else "start"
                if not any(abs(r["x"] - g["x"]) < 1 for r in repeats):
                    repeats.append(dict(x=g["x"], kind=kind))
            for g in dots:
                best, bd = None, 99
                for ev in events:
                    dx = g["x"] - ev["x"]
                    if 0.85 * sp < dx < 3.5 * sp and abs(g["y"] - ev["y"]) <= half * 1.6 + 0.5:
                        if dx < bd:
                            best, bd = ev, dx
                if best is not None:
                    best["dot"] = best.get("dot", 0) + 1
            # Versetzungszeichen
            for g in G:
                if g["c"] in ACC and g["x"] >= firstx - 0.5:
                    best, bd = None, 99
                    for ev in events:
                        if ev["t"] != "n":
                            continue
                        dx = ev["x"] - g["x"]
                        dd = refd + round((refy - g["y"]) / half)
                        if 0.4 * sp < dx < 3.5 * sp and dd == ev["d"] and dx < bd:
                            best, bd = ev, dx
                    if best is not None:
                        best["acc"] = ACC[g["c"]]
            # Triolen-Ziffern (kleine 3 in Musikschrift)
            tup = [g for g in G if g["c"] in "3" and g["size"] < 16 and g["x"] > firstx]
            # Mehrtaktpausen
            mm = []
            for l in pg["lines"]:
                if abs(l["y0"] - l["y1"]) < 0.3 and abs(l["y0"] - (top + bot) / 2) < 1.5 and l["w"] > 1.5 and abs(l["x1"] - l["x0"]) > 20:
                    x0, x1 = min(l["x0"], l["x1"]), max(l["x0"], l["x1"])
                    num = [g for g in G if g["c"].isdigit() and x0 - 5 <= g["x"] <= x1 and g["y"] < top]
                    n = int("".join(c["c"] for c in sorted(num, key=lambda c: c["x"]))) if num else 1
                    mm.append(dict(x0=x0, x1=x1, n=n))
            for f in pg["fills"]:
                if abs((f["y0"] + f["y1"]) / 2 - (top + bot) / 2) < 2 and (f["x1"] - f["x0"]) > 20 and 2 < (f["y1"] - f["y0"]) < 3 * sp and st["x0"] < f["x0"] < st["x1"]:
                    num = [g for g in G if g["c"].isdigit() and f["x0"] - 5 <= g["x"] <= f["x1"] and g["y"] < top]
                    n = int("".join(c["c"] for c in sorted(num, key=lambda c: c["x"]))) if num else 1
                    mm.append(dict(x0=f["x0"], x1=f["x1"], n=n))
            # Ventilzahlen (Text über/unter dem System)
            eqs = [t for t in pg["texts"] if t["c"] == "="]
            vt = [t for t in pg["texts"] if t["c"].isdigit() and not any(abs(t["y"] - q["y"]) < 1 and 0 < t["x"] - q["x"] < 30 for q in eqs) and t["font"].startswith(("Tahoma-Bold", "Times-Roman"))
                  and ((t["font"].startswith("Tahoma") and top - 10 * sp <= t["y"] <= top) or (t["font"].startswith("Times") and bot + sp <= t["y"] <= bot + 10 * sp))
                  and st["x0"] <= t["x"] <= st["x1"]]
            ul = [l for l in pg["lines"] if abs(l["y0"] - l["y1"]) < 0.3 and abs(l["x1"] - l["x0"]) > 3 and l["w"] < 1.0]
            for t in vt:
                cx = (t["x"] + t["x1"]) / 2
                t["ul"] = None
                for k, l in enumerate(ul):
                    if min(l["x0"], l["x1"]) - 0.5 <= cx <= max(l["x0"], l["x1"]) + 0.5 and t["y"] - 0.5 <= l["y0"] <= t["y"] + 4:
                        t["ul"] = (round(l["x0"], 1), round(l["y0"], 1))
                        break
            # Bögen
            cur = [c for c in pg["curves"] if lo <= c["y0"] and c["y1"] <= hi and (c["x1"] - c["x0"]) > 4]
            systems.append(dict(page=pi, top=top, bot=bot, half=half, x0=st["x0"], x1=st["x1"], clef=clef,
                                keysig=keysig, ts=ts, bars=barxs, events=sorted(events, key=lambda e: e["x"]),
                                tup=[(g["x"], g["y"]) for g in tup], mm=mm, repeats=repeats, valves=vt,
                                curves=[dict(x0=c["x0"], y0=c["y0"], x1=c["x1"], y1=c["y1"]) for c in cur], firstx=firstx))
    return systems


if __name__ == "__main__":
    s = analyze(sys.argv[1])
    json.dump(s, open(sys.argv[2], "w"), indent=0, default=str)
    for i, sy in enumerate(s):
        print(i, sy["page"], round(sy["top"]), sy["clef"], sy["keysig"], sy["ts"], len(sy["events"]), "bars", [round(b[0]) for b in sy["bars"]], "mm", sy["mm"], "tup", len(sy["tup"]))
