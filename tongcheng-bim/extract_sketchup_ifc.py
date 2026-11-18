# -*- coding: utf-8 -*-
"""อ่าน IFC ที่ export จาก SketchUp (TONGCHENG-WH60X54_R1) -> data/sketchup_r1.json
SketchUp 2015 export ทุกชิ้นเป็น IfcBuildingElementProxy จึงจำแนกจากชื่อชิ้นส่วน (EX-RW-*, EX-BW-*)
ระบบพิกัด SketchUp: X = แนวกริด 1->11 (กริด 1 = 0), Y = ทิศเหนือ (กริด J = 0, กริด A = 54), Z = ระดับ ±0.00
แปลงเป็นพิกัดแบบของ model.py: x = X, y = 54 - Y
ใช้งาน: python3 extract_sketchup_ifc.py data/sketchup/TONGCHENG-WH60X54_R1.ifc
"""
import sys, json, re, math, collections
import ifcopenshell, ifcopenshell.geom as G, ifcopenshell.util.shape as US

src = sys.argv[1]
f = ifcopenshell.open(src)
s = G.settings(); s.set(s.USE_WORLD_COORDS, True)
fam = collections.defaultdict(list)
for e in f.by_type("IfcBuildingElementProxy"):
    sh = G.create_shape(s, e)
    v = sh.geometry.verts
    xs, ys, zs = v[0::3], v[1::3], v[2::3]
    try: vol = US.get_volume(sh.geometry)
    except Exception: vol = 0.0
    name = e.Name or ""
    m = re.search(r"(\d+)$", name)
    key = re.sub(r"[-_ ]?\d+$", "", name)
    fam[key].append(dict(name=name, n=int(m.group(1)) if m else 0, guid=e.GlobalId,
                         x0=min(xs), x1=max(xs), y0=54 - max(ys), y1=54 - min(ys), z0=min(zs), z1=max(zs), vol=vol))
for k in fam: fam[k].sort(key=lambda r: r["n"])
c = lambda r: ((r["x0"] + r["x1"]) / 2, (r["y0"] + r["y1"]) / 2)
out = {"source": src.split("/")[-1], "app": "SketchUp Pro 2015 (IFC2X3)", "families": {k: len(v) for k, v in fam.items()}}
# retaining wall (กำแพงกันดิน) along W-N-E boundary: path through wall piles
rw_p = [c(r) for r in fam["EX-RW-PILE"]]
L_rw = sum(math.dist(rw_p[i], rw_p[i + 1]) for i in range(len(rw_p) - 1))
wall, cap = fam["EX-RW-WALL"][0], fam["EX-RW-CAPBEAM"][0]
out["rw"] = dict(path=rw_p, length=L_rw,
                 wall=dict(t=round(wall["vol"] / (L_rw * (wall["z1"] - wall["z0"])), 3), z0=wall["z0"], z1=wall["z1"], vol=wall["vol"]),
                 cap=dict(b=round(cap["vol"] / (L_rw * (cap["z1"] - cap["z0"])), 3), z0=cap["z0"], z1=cap["z1"], vol=cap["vol"]),
                 piles=[dict(name=r["name"], c=c(r), a=r["x1"] - r["x0"], z0=r["z0"], z1=r["z1"]) for r in fam["EX-RW-PILE"]],
                 stay_piles=[dict(name=r["name"], c=c(r), a=r["x1"] - r["x0"], z0=r["z0"], z1=r["z1"]) for r in fam["EX-RW-STAYPILE"]],
                 stays=[dict(name=r["name"], c=c(r), z0=r["z0"], z1=r["z1"], vol=r["vol"], bx=r["x1"] - r["x0"], by=r["y1"] - r["y0"]) for r in fam["EX-RW-STAY"]],
                 footings=[dict(name=r["name"], c=c(r), z0=r["z0"], z1=r["z1"], vol=r["vol"], bx=r["x1"] - r["x0"], by=r["y1"] - r["y0"]) for r in fam["EX-RW-STAYFTG"]])
# boundary wall (กำแพงรั้ว) south side: path through posts
bw_p = [c(r) for r in fam["EX-BW-POST"]]
L_bw = sum(math.dist(bw_p[i], bw_p[i + 1]) for i in range(len(bw_p) - 1))
bw = {k: fam["EX-BW-" + k.upper()][0] for k in ("wall", "groundbeam", "lintel")}
out["bw"] = dict(path=bw_p, length=L_bw,
                 wall=dict(t=round(bw["wall"]["vol"] / (L_bw * (bw["wall"]["z1"] - bw["wall"]["z0"])), 3), z0=bw["wall"]["z0"], z1=bw["wall"]["z1"], vol=bw["wall"]["vol"]),
                 groundbeam=dict(b=round(bw["groundbeam"]["vol"] / (L_bw * 0.2), 3), z0=bw["groundbeam"]["z0"], z1=bw["groundbeam"]["z1"], vol=bw["groundbeam"]["vol"]),
                 lintel=dict(b=round(bw["lintel"]["vol"] / (L_bw * 0.2), 3), z0=bw["lintel"]["z0"], z1=bw["lintel"]["z1"], vol=bw["lintel"]["vol"]),
                 posts=[dict(name=r["name"], c=c(r), a=r["x1"] - r["x0"], z0=r["z0"], z1=r["z1"]) for r in fam["EX-BW-POST"]])
out["unmapped"] = [dict(name=r["name"], bbox=[r["x0"], r["y0"], r["z0"], r["x1"], r["y1"], r["z1"]], vol=r["vol"]) for r in fam.get("Object", [])]
json.dump(out, open("data/sketchup_r1.json", "w"), ensure_ascii=False, indent=0)
print(out["families"]); print("RW", round(L_rw, 2), out["rw"]["wall"], out["rw"]["cap"]); print("BW", round(L_bw, 2), out["bw"]["wall"], out["bw"]["groundbeam"])
