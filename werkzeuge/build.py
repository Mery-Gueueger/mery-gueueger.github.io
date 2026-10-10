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


def build(path, kind="valve", meter16=16, sel=None):
    systems = analyze(path)
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
            else:
                c["dur"] = base_dur(c)
        bar["ev"] = out
    # Bindebögen (je Ton zum nächsten Ereignis)
    seq = [(bi, e) for bi, bar in enumerate(bars) for e in bar["ev"]]
    for i in range(len(seq) - 1):
        bi, a = seq[i]; bj, b = seq[i + 1]
        if a["t"] != "c" or b["t"] != "c":
            continue
        sa = systems[bars[bi]["sys"]]
        for n in a["notes"]:
            m = [x for x in b["notes"] if x["midi"] == n["midi"]]
            if not m:
                continue
            u = sa["half"] / 2.3
            if bars[bi]["sys"] == bars[bj]["sys"]:
                ok = any(n["x"] - 2 * u <= c["x0"] <= n["x"] + 14 * u and m[0]["x"] - 6 * u <= c["x1"] <= m[0]["x"] + 14 * u and abs((c["y0"] + c["y1"]) / 2 - n["y"]) < 14 * u for c in sa["curves"])
            else:
                ok = any(n["x"] - 2 * u <= c["x0"] <= n["x"] + 14 * u and c["x1"] > sa["x1"] - 30 * u and abs((c["y0"] + c["y1"]) / 2 - n["y"]) < 14 * u for c in sa["curves"])
            if ok:
                n["tie"] = True
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
