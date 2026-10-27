# -*- coding: utf-8 -*-
"""อ่านตำแหน่งเสาเข็ม ฐานราก และเสา จากไฟล์เวกเตอร์ S201 (Revit PDF export) -> data/s201_vector.json
ใช้งาน: python3 extract_s201.py <S201.pdf>
พิกัดแบบ (drawing): x = ไปทางกริด 11, y = ไปทางกริด J (ลงล่างกระดาษ) หน่วยเมตร จุดอ้างอิง กริด 1/A
"""
import sys, json, math, collections
import pymupdf as fitz

pg = fitz.open(sys.argv[1])[0]
W = pg.get_text("words")
lab = {w[4]: ((w[0]+w[2])/2, (w[1]+w[3])/2) for w in W[::-1] if w[4] in ("1", "11", "A") and w[0] < 900}
X0, Y0 = lab["1"][0], lab["A"][1]
SC = (lab["11"][0] - X0) / 60.0

segs = []
for d in pg.get_drawings():
    for it in d["items"]:
        if it[0] == "l":
            a, b = it[1], it[2]
            if abs(a.x-b.x)+abs(a.y-b.y) < 16: segs.append((a.x, a.y, b.x, b.y))
        elif it[0] == "re":
            r = it[1]; segs += [(r.x0, r.y0, r.x1, r.y0), (r.x1, r.y0, r.x1, r.y1), (r.x1, r.y1, r.x0, r.y1), (r.x0, r.y1, r.x0, r.y0)]
par = list(range(len(segs)))
def f(i):
    while par[i] != i: par[i] = par[par[i]]; i = par[i]
    return i
cell = collections.defaultdict(list)
for i, s in enumerate(segs):
    for (x, y) in ((s[0], s[1]), (s[2], s[3])):
        k = (round(x/0.5), round(y/0.5))
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for j in cell[(k[0]+dx, k[1]+dy)]:
                    sj = segs[j]
                    if min(abs(x-sj[0])+abs(y-sj[1]), abs(x-sj[2])+abs(y-sj[3])) < 0.25: par[f(i)] = f(j)
        cell[k].append(i)
G = collections.defaultdict(list)
for i in range(len(segs)): G[f(i)].append(i)
cls = collections.defaultdict(list)
for g in G.values():
    xs = [c for i in g for c in (segs[i][0], segs[i][2])]; ys = [c for i in g for c in (segs[i][1], segs[i][3])]
    w, h = (max(xs)-min(xs))/SC, (max(ys)-min(ys))/SC; n = len(g)
    x, y = round(((max(xs)+min(xs))/2-X0)/SC, 3), round(((max(ys)+min(ys))/2-Y0)/SC, 3)
    a, b = max(w, h), min(w, h)
    if n in (24, 48) and 0.19 < a < 0.28 and b > 0.19: k = "I26" if a >= 0.235 else "I22"
    elif n == 28 and 0.32 < a < 0.38: k = "I35"
    elif n == 8 and 0.58 < a < 0.68 and b > 0.58: k = "SQ60" if a < 0.63 else "SQ66"
    elif n == 8 and 1.45 < a < 1.55 and 0.58 < b < 0.63: k = "F2P_" + ("X" if w > h else "Y")
    elif n == 10 and 0.45 < a < 0.55 and 0.27 < b < 0.32: k = "C1_" + ("X" if w > h else "Y")
    elif n == 10 and 0.18 < a < 0.22: k = "C3"
    elif n == 10 and 0.45 < a < 0.55 and b > 0.45: k = "C2"
    else: continue
    if all(abs(x-q[0])+abs(y-q[1]) > 0.1 for q in cls[k]): cls[k].append([x, y])

near = lambda p, L, r: [q for q in L if math.hypot(p[0]-q[0], p[1]-q[1]) < r]
out = {"source": "S201 แปลนโครงสร้างฐานราก เสาตอม่อ (Issue 01/09/69)", "scale_pt_per_m": round(SC, 4),
       "F2P": [{"x": p[0], "y": p[1], "long": o} for o in "XY" for p in cls["F2P_" + o]],
       "C1": [{"x": p[0], "y": p[1], "long": o} for o in "XY" for p in cls["C1_" + o]],
       "C2": cls["C2"], "C3": cls["C3"], "I35": cls["I35"], "SQ66": cls["SQ66"]}
f2 = [(d["x"], d["y"]) for d in out["F2P"]]
f2p_piles = [q for p in f2 for q in near(p, cls["I26"], 1.0)]
out["I26_F2P"] = f2p_piles
out["F1A"] = [s for s in cls["SQ60"] if near(s, cls["I22"], 0.2)]
out["F1P1"] = [s for s in cls["SQ60"] if near(s, cls["I26"], 0.2)]
out["I22_road"] = [p for p in cls["I22"] if near(p, cls["SQ60"], 0.2)]
out["I22_TR"] = [p for p in cls["I22"] if not near(p, cls["SQ60"], 0.2)]
rest = [p for p in cls["I26"] if p not in f2p_piles]
out["I26_F1P1"] = [p for p in rest if near(p, out["F1P1"], 0.2)]
out["I26_SQ66"] = [p for p in rest if near(p, cls["SQ66"], 0.2)]
out["I26_tank"] = [p for p in rest if p not in out["I26_F1P1"] and p not in out["I26_SQ66"]]
json.dump(out, open("data/s201_vector.json", "w"), ensure_ascii=False, indent=0)
print({k: len(v) for k, v in out.items() if isinstance(v, list)})
