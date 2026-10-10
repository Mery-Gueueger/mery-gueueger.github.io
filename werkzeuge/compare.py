import sys; sys.path.insert(0, __file__.rsplit("/", 1)[0])
from build import build
def sig(bar):
    out = []
    for e in bar["ev"]:
        if e["t"] == "r": out.append(("r", e["dur"]))
        else: out.append((tuple(n["midi"] for n in e["notes"]), e["dur"], tuple(bool(n.get("tie")) for n in e["notes"])))
    # Pausen zusammenfassen
    m = []
    for x in out:
        if x[0] == "r" and m and m[-1][0] == "r": m[-1] = ("r", m[-1][1] + x[1])
        else: m.append(x)
    return m
score, n, idx, part, kind = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4], sys.argv[5]
A = build(score, kind, sel=(idx, n)); B = build(part, kind)
print("Takte Partitur", len(A["bars"]), "Stimme", len(B["bars"]), "Partitur falsche Länge", [(i+1, b["tot"]) for i, b in enumerate(A["bars"]) if b["tot"] != 16][:10])
diff = 0
for i, (a, b) in enumerate(zip(A["bars"], B["bars"])):
    if sig(a) != sig(b):
        diff += 1
        if diff <= 12: print("Takt", i + 1, "\n  P:", sig(a), "\n  S:", sig(b))
print("Unterschiede:", diff)
