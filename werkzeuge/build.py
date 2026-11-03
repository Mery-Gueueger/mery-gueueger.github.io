"""Baut aus einer Stimmen-PDF ein Modell (Takte, Ereignisse, Akkorde, Bindebögen, Griffe) und ABC-Text."""
import sys, json
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from extract import analyze, DIA

STEP = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
VALVE = {48: "0", 49: "123", 50: "13", 51: "23", 52: "12", 53: "1", 54: "123", 55: "13", 56: "23", 57: "12", 58: "1", 59: "2",
         60: "0", 61: "123", 62: "13", 63: "23", 64: "12", 65: "1", 66: "2", 67: "0", 68: "23", 69: "12", 70: "1", 71: "2",
         72: "0", 73: "12", 74: "1", 75: "2", 76: "0", 77: "1", 78: "2", 79: "0", 80: "23", 81: "12", 82: "1", 83: "2", 84: "0"}
SLIDE = {40: "7", 41: "6", 42: "5", 43: "4", 44: "3", 45: "2", 46: "1", 47: "7", 48: "6", 49: "5", 50: "4", 51: "3", 52: "2", 53: "1",
         54: "5", 55: "4", 56: "3", 57: "2", 58: "1", 59: "4", 60: "3", 61: "2", 62: "1", 63: "3", 64: "2", 65: "1", 66: "3", 67: "2",
         68: "3", 69: "2", 70: "1"}
WSLIDE = {k + 14: v for k, v in SLIDE.items()}
NAMES = ["C", "Cis", "D", "Es", "E", "F", "Fis", "G", "Gis", "A", "B", "H"]


def midi_of(d, alt):
    return 12 * (d // 7 + 1) + STEP[DIA[d % 7]] + alt


def base_dur(ev):
    if ev["t"] == "r":
        b = ev["dur"]
    else:
        b = {"w": 16, "h": 8, "q": 4}[ev["head"]]
        if ev["head"] == "q":
            n = max(ev.get("beams", 0), ev.get("flag", 0))
            b = 4 / (2 ** n)
    dt = ev.get("dot", 0)
    return b * (1.5 if dt == 1 else 1.75 if dt == 2 else 1)


def fing_rows(sy):
    """Ventil-/Zugzahlen als Zeilen-Token; übereinanderliegende Token zu Spalten zusammenfassen."""
    vt = sorted(sy["valves"], key=lambda t: (round(t["y"]), t["x"]))
    toks = []
    for t in vt:
        last = toks[-1] if toks else None
        if last and t.get("ul") and t["ul"] == last["ul"] and abs(t["y"] - last["y"]) < 1:
            last["s"] += t["c"]; last["xe"] = t["x1"]
        else:
            toks.append(dict(s=t["c"], x=t["x"], xe=t["x1"], y=t["y"], ul=t.get("ul")))
    cols = []
    for t in sorted(toks, key=lambda t: (t["x"] + t["xe"]) / 2):
        cx = (t["x"] + t["xe"]) / 2
        for c in cols:
            if abs(c["cx"] - cx) < 5 and all(abs(r["y"] - t["y"]) > 3 for r in c["rows"]):
                c["rows"].append(t); break
        else:
            cols.append(dict(cx=cx, rows=[t]))
    for c in cols:
        c["rows"].sort(key=lambda r: r["y"])
        c["rows"] = [r["s"] for r in c["rows"]]
    return cols


def norm_f(s):
    s = "".join(sorted(set(s)))
    if s != "0" and "0" in s:
        s = s.replace("0", "")
    return s


def tuplets(path, systems, bars, allsys=None):
    """Triolen: kursive 3 mit Klammer; die Ereignisse unter der Klammer dauern 2/3 ihres geschriebenen Werts."""
    import pymupdf
    doc = pymupdf.open(path)
    marks = {}
    for pi, pg in enumerate(doc):
        threes = []
        for b in pg.get_text("dict")["blocks"]:
            for l in b.get("lines", []):
                for sp in l["spans"]:
                    if sp["text"].strip() == "3" and "Italic" in sp["font"]:
                        x0, y0, x1, y1 = sp["bbox"]; threes.append((x0, x1, (y0 + y1) / 2))
        if not threes:
            continue
        segs = [(min(it[1].x, it[2].x), max(it[1].x, it[2].x), (it[1].y + it[2].y) / 2) for dr in pg.get_drawings() for it in dr["items"]
                if it[0] == "l" and abs(it[1].x - it[2].x) > 2 and abs(it[1].y - it[2].y) < abs(it[1].x - it[2].x) * 0.3]
        marks[pi] = (threes, segs)
    gid = 0
    for si, sy in enumerate(systems):
        if sy["page"] not in marks:
            continue
        threes, segs = marks[sy["page"]]
        evs = [(bar, e) for bar in bars if bar["sys"] == si and not bar.get("mm") for e in bar["ev"]]
        for x0, x1, yc in threes:
            # zu diesem System gehörig? (knapp über oder unter den Notenlinien; nächstes System gewinnt)
            dist = 0 if sy["top"] - 30 <= yc <= sy["bot"] + 30 else 99
            if dist or min(abs(yc - (o["top"] + o["bot"]) / 2) for o in (allsys or systems) if o["page"] == sy["page"]) < abs(yc - (sy["top"] + sy["bot"]) / 2) - 1:
                continue
            left = [s for s in segs if abs(s[2] - yc) < 5 and -1 < x0 - s[1] < 6]
            right = [s for s in segs if abs(s[2] - yc) < 5 and -1 < s[0] - x1 < 6]
            if left and right:
                a, b = min(s[0] for s in left) - 2, max(s[1] for s in right) + 2
                mem = [(bar, e) for bar, e in evs if a <= e["x"] + e.get("hw", 0) / 2 <= b]
            else:
                cx = (x0 + x1) / 2
                mem = sorted(evs, key=lambda be: abs(be[1]["x"] + be[1].get("hw", 0) / 2 - cx))[:3]
                mem.sort(key=lambda be: be[1]["x"])
            if not mem:
                continue
            gid += 1
            for k, (bar, e) in enumerate(mem):
                if "tup" in e:
                    continue
                e["wdur"] = e["dur"]; e["dur"] = e["dur"] * 2 / 3; e["tup"] = gid
                e["tupn"] = len(mem) if k == 0 else 0


def build(path, kind="valve", meter16=16, sel=None):
    systems = analyze(path); allsys = systems
    if sel:
        systems = [s for k, s in enumerate(systems) if k % sel[1] == sel[0]]
    bars, keysig = [], {}
    for si, sy in enumerate(systems):
        if sy["keysig"] or si == 0:
            keysig = sy["keysig"] or keysig
        bx = [b[0] for b in sy["bars"]]
        edges = [sy["firstx"] - 3] + [b for b in bx if b > sy["firstx"]]
        for k in range(len(edges) - 1):
            a, b = edges[k], edges[k + 1]
            evs = [e for e in sy["events"] if a <= e["x"] < b and not e.get("small")]
            graces = [e for e in sy["events"] if a <= e["x"] < b and e.get("small")]
            mm = [m for m in sy["mm"] if a <= m["x0"] < b]
            if mm and not evs:
                for _ in range(mm[0]["n"]):
                    bars.append(dict(sys=si, ev=[dict(t="r", dur=meter16, x=a)], mm=True, keysig=dict(keysig), x0=a, x1=b))
                continue
            if len(evs) == 1 and evs[0]["t"] == "r" and evs[0].get("c") in ("Ó", "∑"):
                evs[0]["dur"] = meter16
            bars.append(dict(sys=si, ev=evs, keysig=dict(keysig), x0=a, x1=b, graces=graces))
    # Tonhöhen
    for bar in bars:
        local = {}
        for e in sorted(bar["ev"], key=lambda e: e["x"]):
            if e["t"] != "n":
                continue
            if "acc" in e:
                local[e["d"]] = e["acc"]
            e["alt"] = local.get(e["d"], bar["keysig"].get(DIA[e["d"] % 7], 0))
            e["midi"] = midi_of(e["d"], e["alt"])
    # Akkorde bilden
    for bar in bars:
        out = []
        evs = sorted(bar["ev"], key=lambda e: e["x"])
        for e in evs:
            if e["t"] == "n" and out and out[-1]["t"] == "c":
                c = out[-1]; f = c["notes"][0]
                same_stem = "stem" in e and "stem" in f and abs(e["stem"]["x"] - f["stem"]["x"]) < 0.8
                whole = e["head"] == "w" and f["head"] == "w" and abs(e["x"] - f["x"]) < e["hw"] + 1.5
                whole = whole or (e["head"] == f["head"] and abs(e["x"] - f["x"]) < 1.0 and "stem" not in e)
                if same_stem or whole:
                    c["notes"].append(e)
                    c["x"] = min(c["x"], e["x"])
                    for k in ("beams", "flag", "dot"):
                        if k in e and k not in f:
                            f[k] = e[k]
                    continue
            if e["t"] == "n":
                out.append(dict(t="c", notes=[e], x=e["x"], hw=e["hw"]))
            else:
                out.append(e)
        for c in out:
            if c["t"] == "c":
                c["notes"].sort(key=lambda n: -n["midi"])  # oben zuerst
                c["dur"] = base_dur(c["notes"][0])
                ups = {n["stem"]["up"] for n in c["notes"] if "stem" in n}
                if len(ups) > 1:  # zwei Stimmen (Hals oben und unten): kürzere Note bestimmt den Schritt
                    c["dur"] = min(base_dur(n) for n in c["notes"])
            else:
                c["dur"] = base_dur(c)
        # Akkord ohne erkannten Hals (z.B. Balken unten) im zu langen Takt: als Achtel lesen, wenn es dann aufgeht
        tot = sum(e["dur"] for e in out)
        if not bar.get("mm") and tot > meter16:
            for c in out:
                if c["t"] == "c" and c["dur"] == 4 and all("stem" not in n for n in c["notes"]) and abs(tot - 2 - meter16) < 1e-6:
                    c["dur"] = 2; break
        # Zweite Stimme: Pause genau unter/über einer Note gehört zur anderen Stimme (nur wenn der Takt sonst zu lang wäre)
        if not bar.get("mm") and sum(e["dur"] for e in out) > meter16:
            notes_x = [c["x"] for c in out if c["t"] == "c"]
            out = [e for e in out if e["t"] != "r" or not any(abs(e["x"] - x) < 1.0 for x in notes_x)]
        bar["ev"] = out
    tuplets(path, systems, bars, allsys)
    # Bindebögen (je Ton zum nächsten Ereignis)
    seq = [(bi, e) for bi, bar in enumerate(bars) for e in bar["ev"]]
    for i in range(len(seq) - 1):
        bi, a = seq[i]; bj, b = seq[i + 1]
        if a["t"] != "c" or b["t"] != "c":
            continue
        sa = systems[bars[bi]["sys"]]
        for n in a["notes"]:
            m = [x for x in b["notes"] if x["midi"] == n["midi"]]
            carry = False
            if not m and bi != bj:
                # über den Taktstrich gebundene Note behält ihr Vorzeichen (z.B. B gebunden in den nächsten Takt)
                m = [x for x in b["notes"] if x["d"] == n["d"] and "acc" not in x]
                carry = bool(m)
            if not m:
                continue
            u = sa["half"] / 2.3
            if bars[bi]["sys"] == bars[bj]["sys"]:
                ok = any(n["x"] - 2 * u <= c["x0"] <= n["x"] + 14 * u and m[0]["x"] - 6 * u <= c["x1"] <= m[0]["x"] + 14 * u and abs((c["y0"] + c["y1"]) / 2 - n["y"]) < 14 * u for c in sa["curves"])
            else:
                ok = any(n["x"] - 2 * u <= c["x0"] <= n["x"] + 14 * u and c["x1"] > sa["x1"] - 30 * u and abs((c["y0"] + c["y1"]) / 2 - n["y"]) < 14 * u for c in sa["curves"])
            if ok:
                n["tie"] = True
                if carry:
                    m[0]["alt"] = n["alt"]; m[0]["midi"] = n["midi"]
    # Fortsetzungen von Bindebögen markieren
    prev_tied = set()
    for bar in bars:
        for e in bar["ev"]:
            if e["t"] != "c":
                prev_tied = set()
                continue
            for n in e["notes"]:
                n["cont"] = n["midi"] in prev_tied
            e["cont"] = all(n["cont"] for n in e["notes"])
            prev_tied = set(n["midi"] for n in e["notes"] if n.get("tie"))
    # Griffe aus der PDF zuordnen (Zeilen von oben = Töne von oben, nur neu angespielte Töne)
    fmap = WSLIDE if kind == "slide" else VALVE
    unmatched = []
    for si, sy in enumerate(systems):
        chords = [e for bar in bars if bar["sys"] == si and not bar.get("mm") for e in bar["ev"] if e["t"] == "c"]
        for col in fing_rows(sy):
            if not chords:
                break
            c = min(chords, key=lambda c: abs(col["cx"] - (c["x"] + c["hw"] / 2)))
            if abs(col["cx"] - (c["x"] + c["hw"] / 2)) < 8 and "pdfrows" not in c:
                fresh = [n for n in c["notes"] if not n["cont"]] or c["notes"]
                rows = col["rows"]
                if len(rows) == len(c["notes"]) and len(fresh) != len(rows):
                    fresh = c["notes"]
                if len(fresh) == 1:
                    rows = ["".join(rows)]
                c["pdfrows"] = rows
                if len(rows) > len(fresh) > 1:
                    # Griffe untereinander geschrieben (1 über 2 = 1+2): Zeilen so gruppieren, dass sie zu den Tönen passen
                    import itertools
                    best = None
                    for cut in itertools.combinations(range(1, len(rows)), len(fresh) - 1):
                        idx = (0,) + cut + (len(rows),)
                        grp = ["".join(rows[idx[i]:idx[i + 1]]) for i in range(len(fresh))]
                        score = sum(norm_f(g) == fmap.get(n["midi"]) for g, n in zip(grp, fresh))
                        if best is None or score > best[0]:
                            best = (score, grp)
                    if best and best[0] == len(fresh):
                        rows = best[1]
                if len(rows) == len(fresh):
                    for n, r in zip(fresh, rows):
                        n["pdf"] = norm_f(r)
                else:
                    unmatched.append((si, round(col["cx"]), "Akkord/Zeilen", rows, [n["midi"] for n in fresh]))
            else:
                unmatched.append((si, round(col["cx"]), "Zahl ohne Note", col["rows"]))
    issues = []
    for bi, bar in enumerate(bars):
        bar["tot"] = sum(e["dur"] for e in bar["ev"])
        for e in bar["ev"]:
            if e["t"] != "c":
                continue
            fl = []
            for n in e["notes"]:
                calc = fmap.get(n["midi"], "?")
                nm = NAMES[n["midi"] % 12] + str(n["midi"] // 12 - 1)
                if n["cont"] and "pdf" not in n:
                    n["fing"] = ""
                elif "pdf" in n:
                    n["fing"] = n["pdf"]
                    if n["pdf"] != calc:
                        issues.append(dict(bar=bi + 1, note=nm, pdf=n["pdf"], calc=calc))
                else:
                    n["fing"] = calc
                    issues.append(dict(bar=bi + 1, note=nm, pdf=None, calc=calc))
                if n["fing"]:
                    fl.append(n["fing"])
            e["fing"] = fl
    return dict(systems=systems, bars=bars, issues=issues, unmatched=unmatched)


def abc_pitch(n, keysig, local):
    d, alt = n["d"], n["alt"]
    L, o = DIA[d % 7], d // 7
    exp = local.get(d, keysig.get(L, 0))
    acc = ""
    if alt != exp:
        acc = {1: "^", -1: "_", 0: "="}[alt]
        local[d] = alt
    return acc + (L.lower() + "'" * (o - 5) if o >= 5 else L + "," * (4 - o))


def dur_str(d):
    if d == 1:
        return ""
    if d == int(d):
        return str(int(d))
    # halbe Sechzehntel kommen nicht vor; Punktierungen ergeben ganze Zahlen in 1/16
    return f"{d:g}"


def to_abc(model, keyname, title="", meter="4/4", per_line=4, marks=None):
    """marks: dict Taktindex(0-basiert) -> {'pre': '|:', 'post': ':|', 'volta': '1'}"""
    marks = marks or {}
    head = [f"X:1", f"T:{title}", f"M:{meter}", "L:1/16", f"K:{keyname}"]
    out, fings = [], []
    line = ""
    for bi, bar in enumerate(model["bars"]):
        local = {}
        toks = []
        for e in bar["ev"]:
            if e["t"] == "r":
                toks.append("z" + dur_str(e["dur"]))
                continue
            ps = []
            for n in e["notes"]:
                ps.append(abc_pitch(n, bar["keysig"], local) + ("-" if n.get("tie") else ""))
            if len(ps) == 1:
                tok = ps[0].rstrip("-") + dur_str(e["dur"]) + ("-" if ps[0].endswith("-") else "")
            else:
                tok = "[" + "".join(ps) + "]" + dur_str(e["dur"])
            toks.append(tok)
            fings.append("/".join(e["fing"]))
        m = marks.get(bi, {})
        pre = m.get("pre", "")
        if m.get("volta"):
            pre += ("[" if not pre else "") + m["volta"] + " "
        line += (pre + " " if pre and not pre.endswith(" ") else pre) + " ".join(toks) + " " + m.get("post", "|") + " "
        if (bi + 1) % per_line == 0:
            out.append(line.strip()); line = ""
    if line:
        out.append(line.strip())
    abc = "\n".join(head + out)
    if abc.endswith("|"):
        abc = abc[:-1] + "|]"
    return abc, fings


if __name__ == "__main__":
    m = build(sys.argv[1], kind=sys.argv[2] if len(sys.argv) > 2 else "valve")
    bad = [(i + 1, b["tot"]) for i, b in enumerate(m["bars"]) if b["tot"] != 16]
    print("Takte:", len(m["bars"]), "falsche Länge:", bad)
    print("Abweichungen:", [x for x in m["issues"] if x["pdf"] is not None])
    print("ohne PDF-Zahl:", [x for x in m["issues"] if x["pdf"] is None][:40])
    print("unzugeordnet:", m["unmatched"])
