# -*- coding: utf-8 -*-
"""
แบบจำลอง BIM (LOD 200-300) งานก่อสร้างอาคารโกดังและงานบริเวณ
บริษัท ตงเฉิน อีเล็คทริค เคเบิ้ล แอนด์ไวร์ จำกัด  (Project No. WEC-TC-6901)

แหล่งข้อมูล (Google Drive: TONGCHENG/แบบประกอบเพื่อประเมินราคา):
  S201   แปลนโครงสร้างฐานราก เสาตอม่อ (1:200)
  S201-B ปริมาณงานโครงสร้างฐานราก (ตาราง Revit S2, S1.1)
  S202   แปลนโครงสร้างคาน พื้น ชั้นที่ 1 (ตาราง S3, S4.1, S6.1)
  A101   ผังส่วนประกอบอาคารใหม่ (1:200)
  A202   รูปด้านหน้า 01 / รูปด้านซ้าย 02 (1:150)
และ BOQ: 00_BOQ_Preconstruction.xlsx, 01_BOQ_งานหลัก.xlsx

ระบบพิกัด: x = แนวกริด 1->11 (0..60 ม.), y = แนวกริด A->J (0..54 ม.), z = ระดับ (±0.00 = ระดับถนนรอบอาคาร)
ทุกชิ้นส่วนมี: หมวด WBS, อ้างอิงรายการ BOQ, กิจกรรม 4D, แหล่งที่มา (จากแบบ / สมมติ)
"""
import math, json, os

GX = [6.0 * i for i in range(11)]          # grid 1..11
GY = [6.0 * i for i in range(10)]          # grid A..J
GXN = [str(i + 1) for i in range(11)]
GYN = list("ABCDEFGHIJ")
BW, BD = 60.0, 54.0

# ---------------- levels (A202 / S202) ----------------
LV = {
    "ref_road": -1.50,   # ระดับถนนอ้างอิง (ถนนสาธารณะ)
    "road": 0.00,        # ระดับถนนรอบอาคาร
    "ffl": 0.50,         # ระดับพื้นชั้นที่ 1
    "mezz": 3.30,        # ระดับพื้นชั้นลอย
    "col_top_rc": 4.50,  # ระดับหัวเสาคอนกรีต
    "eave": 9.00,        # ระดับหัวเสารับหลังคา
    "ridge": 14.10,      # ระดับสันหลังคา
    "jack": 15.25,       # ระดับสัน JACKROOF
    # --- ระดับฐานราก (รอยืนยันจากแบบขยาย) ---
    "f2p_bot": -1.20,    # ท้องฐาน F2P (หลังฐาน -0.40 จากความยาวเสา C1 4.90 ม. ในตาราง S4.1)
    "drop_bot": 0.10,    # ท้อง Drop panel F1P (ชิดท้องพื้น S1 +0.30)
    "f1a_bot": -0.45,    # ท้องฐาน F1A (ชิดท้องพื้นถนน S2 -0.15)
    "f1p1_bot": -1.00,   # ท้องฐาน F1P-1
    "tank_bot": -2.85,   # ท้องถังเก็บน้ำใต้ดิน BF (S202)
}
PILE_LEN = 22.0          # I22-22 / I26-22 / I35-22 -> 22 ม. (ความยาวจริงยืนยันจากผลเจาะสำรวจดิน P3)
EXIST_GROUND = 0.00      # ดินเดิม = ระดับถนนรอบอาคาร ±0.00 (ผู้ว่าจ้างยืนยัน 27/10/69); -1.50 คือถนนสาธารณะ
FILL_T = 0.30            # ความหนาดินถมสำหรับคิด BOQ (ผู้ว่าจ้างกำหนด)
FILL_AREA = (-2.0, -2.0, BW + 2.0, BD + 2.0)   # พื้นที่อาคาร + ระยะเผื่อ 2 ม. = 64 x 58 ม. (ฐานเดียวกับ BOQ เดิม)

# site boundary digitised from A101 (approx. +/-0.5 m)
SITE = [(-12.50, -15.80), (0.88, -14.64), (62.04, -9.33), (68.29, -4.52), (75.19, 66.25), (-5.75, 58.12),
        (-5.89, 57.04), (-8.33, 38.64), (-9.38, 26.77), (-12.32, -6.44), (-12.51, -8.74)]   # แนวเขตจากเวกเตอร์ S202

# auxiliary footprints (digitised from A101/S202)
TANK = (-11.38, -13.34, 0.74, -6.71)          # ถังเก็บน้ำใต้ดิน x0,y0,x1,y1  TF -2.60 BF -2.85
TRANS = (62.90, -8.44, 66.90, -5.89)          # ฐานหม้อแปลง
TOILET = (-7.365, 18.007, -4.962, 26.011)         # อาคารห้องน้ำ 4x8
CHEM = (-4.015, 0.0, 0.0, 6.012)             # Chemical Drum Storage Room 21.84 m2
MDB = (54.07, 0.0, 60.0, 3.0)              # MDB ROOM 17.79 m2
ROOMS = (41.2, 0.0, 54.07, 4.0)            # ห้องประกอบแนวกริด A (รอแบบสถาปัตย์)
MEZZ = (0.0, 0.0, 18.0, 17.0)              # ชั้นลอย F8 306 m2
RAMP_N = (24.0, -3.19, 30.0, 0.0)           # ทางลาดขนส่ง (DN) ด้านเหนือ
RAMP_S = (36.0, 54.0, 42.0, 57.5)          # ทางลาดขนส่ง (DN) ด้านใต้
SITE_OFFICE = (2.0, -7.75, 10.0, -4.75)     # สำนักงานสนาม 3x8 (สมมติตำแหน่ง)
STORE = (11.0, -7.75, 23.0, -4.75)           # โรงเก็บวัสดุ (สมมติตำแหน่ง)
TEMP_WC = (33.0, -7.25, 36.0, -5.25)         # ห้องน้ำชั่วคราว

# ---------------- small vector helpers ----------------
def sub(a, b): return (a[0]-b[0], a[1]-b[1], a[2]-b[2])
def add(a, b): return (a[0]+b[0], a[1]+b[1], a[2]+b[2])
def mul(a, s): return (a[0]*s, a[1]*s, a[2]*s)
def dot(a, b): return a[0]*b[0]+a[1]*b[1]+a[2]*b[2]
def cross(a, b): return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])
def norm(a):
    l = math.sqrt(dot(a, a)); return (a[0]/l, a[1]/l, a[2]/l)
def length(a): return math.sqrt(dot(a, a))

X, Y, Z = (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)


def poly_area(p):
    return abs(sum(p[i][0]*p[(i+1) % len(p)][1]-p[(i+1) % len(p)][0]*p[i][1] for i in range(len(p))))/2


def poly_perim(p):
    return sum(math.dist(p[i], p[(i+1) % len(p)]) for i in range(len(p)))


def in_poly(pt, poly):
    x, y = pt; c = False
    for i in range(len(poly)):
        x1, y1 = poly[i]; x2, y2 = poly[(i+1) % len(poly)]
        if (y1 > y) != (y2 > y) and x < (x2-x1)*(y-y1)/(y2-y1)+x1:
            c = not c
    return c


def dist_to_poly_edge(pt, poly):
    best = 1e9
    for i in range(len(poly)):
        a, b = poly[i], poly[(i+1) % len(poly)]
        ax, ay = b[0]-a[0], b[1]-a[1]
        t = max(0, min(1, ((pt[0]-a[0])*ax+(pt[1]-a[1])*ay)/(ax*ax+ay*ay)))
        best = min(best, math.dist(pt, (a[0]+t*ax, a[1]+t*ay)))
    return best


def offset_rect_poly(poly, d):
    """inset convex polygon by d (positive = inward)."""
    n = len(poly); lines = []
    # orientation
    s = sum(poly[i][0]*poly[(i+1) % n][1]-poly[(i+1) % n][0]*poly[i][1] for i in range(n))
    sign = 1 if s > 0 else -1
    for i in range(n):
        a, b = poly[i], poly[(i+1) % n]
        dx, dy = b[0]-a[0], b[1]-a[1]; L = math.hypot(dx, dy)
        nx, ny = -dy/L*sign, dx/L*sign
        lines.append(((a[0]+nx*d, a[1]+ny*d), (dx, dy)))
    out = []
    for i in range(n):
        (p1, d1), (p2, d2) = lines[i-1], lines[i]
        den = d1[0]*d2[1]-d1[1]*d2[0]
        t = ((p2[0]-p1[0])*d2[1]-(p2[1]-p1[1])*d2[0])/den
        out.append((p1[0]+d1[0]*t, p1[1]+d1[1]*t))
    return out



# ---------------- perimeter walls (shared by model + BOQ) ----------------
WALL_T, WALL_TOP, TIE_Z, COL_W = 0.15, 4.35, 2.60, 0.30
DOOR_BAYS = {"A": [(24.0, 30.0)], "J": [(36.0, 42.0)]}          # ประตูม้วน 6.00 ม. (เต็มช่วงเสา)
D1_DOORS = {"1": [29.44], "11": [11.39]}                        # ประตู D1 กว้าง 1.00 ม. สูง 2.10 ม. (A101)


def wall_bays():
    out = []
    for name, fixed, axis, n in [("A", 0.0, "x", 10), ("J", BD, "x", 10), ("1", 0.0, "y", 9), ("11", BW, "y", 9)]:
        bays, masonry, stiff = [], [], []
        for i in range(n):
            a0, a1 = 6.0*i, 6.0*(i+1)
            if any(abs(a0-d0) < 0.01 for d0, _ in DOOR_BAYS.get(name, [])): continue
            s0, s1 = a0 + COL_W/2, a1 - COL_W/2
            P = (lambda t: (t, fixed)) if axis == "x" else (lambda t: (fixed, t))
            bays.append((P(s0), P(s1)))
            doors = [d for d in D1_DOORS.get(name, []) if a0 < d < a1]
            if doors:
                for d in doors:
                    stiff += [P(d-0.55), P(d+0.55)]
                    masonry += [(P(s0), P(d-0.5)), (P(d+0.5), P(s1))]
            else:
                stiff.append(P((a0+a1)/2)); masonry.append((P(s0), P(s1)))
        out.append(dict(name=f"ผนังแนวกริด {name}", grid=name, bays=bays, masonry=masonry, stiff=stiff,
                        doors=len(D1_DOORS.get(name, [])), roll=len(DOOR_BAYS.get(name, []))))
    return out

# =====================================================================
#  ELEMENT REGISTRY
# =====================================================================
ELEMENTS = []


def box(cat, ifc, name, mark, center, ex, ey, ez, a, b, h, task, boq, src="แบบ", wbs=None, pre=None, extra=None, remove_task=None):
    """oriented box. a,b,h = sizes along ex,ey,ez. center = geometric centre."""
    e = dict(kind="box", cat=cat, ifc=ifc, pre=pre, name=name, mark=mark,
             c=center, ex=norm(ex), ey=norm(ey), ez=norm(ez), a=a, b=b, h=h,
             task=task, boq=boq, src=src, wbs=wbs or boq.split(" ")[0], extra=extra or {},
             remove_task=remove_task)
    ELEMENTS.append(e)
    return e


def vbox(cat, ifc, name, mark, x0, y0, x1, y1, z0, z1, task, boq, **kw):
    """axis-aligned box from plan rectangle and levels."""
    return box(cat, ifc, name, mark, ((x0+x1)/2, (y0+y1)/2, (z0+z1)/2), X, Y, Z,
               abs(x1-x0), abs(y1-y0), abs(z1-z0), task, boq, **kw)


def member(cat, ifc, name, mark, p0, p1, w, d, task, boq, up=Z, **kw):
    """linear member from p0 to p1, section w (horizontal-ish) x d (in 'up' plane)."""
    v = sub(p1, p0); L = length(v); ez = norm(v)
    upv = up if abs(dot(norm(up), ez)) < 0.99 else X
    ex = norm(cross(upv, ez))          # section width direction
    ey = cross(ez, ex)                 # section depth direction
    c = mul(add(p0, p1), 0.5)
    return box(cat, ifc, name, mark, c, ex, ey, ez, w, d, L, task, boq, **kw)


def prism(cat, ifc, name, mark, origin, ex, ey, ez, outer, holes, h, task, boq, src="แบบ", pre=None, extra=None, remove_task=None):
    e = dict(kind="prism", cat=cat, ifc=ifc, pre=pre, name=name, mark=mark, o=origin,
             ex=norm(ex), ey=norm(ey), ez=norm(ez), outer=outer, holes=holes, h=h,
             task=task, boq=boq, src=src, wbs=boq.split(" ")[0], extra=extra or {}, remove_task=remove_task)
    ELEMENTS.append(e)
    return e


def plan_prism(cat, ifc, name, mark, outer, holes, z0, z1, task, boq, **kw):
    return prism(cat, ifc, name, mark, (0, 0, z0), X, Y, Z, outer, holes, z1-z0, task, boq, **kw)


def rect(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


# =====================================================================
#  BUILD
# =====================================================================
def build():
    ELEMENTS.clear()
    bldg = rect(0, 0, BW, BD)

    # ---------------- 0 Site / Preconstruction ----------------
    plan_prism("site", "IfcGeographicElement", "ผิวดินเดิม ±0.00", "EG",
               SITE, [], EXIST_GROUND-0.30, EXIST_GROUND, "P2", "P2.1 ถางป่า/เคลียร์พื้นที่",
               src="ผู้ว่าจ้างยืนยัน", pre="TERRAIN")
    # fill: outside building to -0.25 (under road slab + sand), inside building to +0.10
    plan_prism("earth", "IfcEarthworksFill", "ดินถมบดอัด หนา 0.30 ม. (อาคาร + เผื่อ 2 ม.)", "FILL",
               rect(*FILL_AREA), [], EXIST_GROUND, EXIST_GROUND + FILL_T, "M13", "1.3.1 ถมดินปรับระดับ", src="ผู้ว่าจ้างกำหนด 0.30 ม.")

    # ---------------- temporary facilities ----------------
    fence = offset_rect_poly(SITE, 0.3)
    for i in range(len(fence)):
        p0, p1 = fence[i], fence[(i+1) % len(fence)]
        member("temp", "IfcBuildingElementProxy", "รั้วชั่วคราวเมทัลชีท สูง 2.00 ม.", "TF",
               (p0[0], p0[1], -0.25), (p1[0], p1[1], -0.25), 0.05, 2.0, "M11", "1.2.1 รั้วชั่วคราว",
               up=Z, src="สมมติ", remove_task="M52")
    for r, nm, hh, item in [(SITE_OFFICE, "สำนักงานสนาม 3.00x8.00 ม. (ด้านเหนือ ระหว่างแถวเข็มถนน)", 2.8, "1.2.3 สำนักงานสนาม"),
                            (STORE, "โรงเก็บวัสดุและเครื่องมือ 3.00x12.00 ม. (ด้านเหนือ)", 3.2, "1.2.4 โรงเก็บวัสดุ"),
                            (TEMP_WC, "ห้องน้ำชั่วคราว 2 ห้อง (ด้านเหนือ)", 2.4, "1.2.5 ห้องน้ำชั่วคราว")]:
        vbox("temp", "IfcBuildingElementProxy", nm, "TMP", r[0], r[1], r[2], r[3], -0.25, -0.25+hh,
             "M11", item, src="สมมติ", remove_task="M52")

    # ---------------- 2.1 Piles / 2.2 footings : positions read from S201 vectors (data/s201_vector.json) ----------------
    V = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "s201_vector.json"), encoding="utf-8"))
    POS = "แบบ S201 (ตำแหน่ง) / ระดับรอยืนยัน"

    def pile(x, y, top, size, mark, desc, task, boq, src=POS, grp="pile_b"):
        flange = size/1000.0
        vbox(grp, "IfcPile", desc, mark, x-flange/2, y-flange/2, x+flange/2, y+flange/2,
             top-PILE_LEN, top, task, boq, src=src, pre="DRIVEN",
             extra={"ขนาด": f"I-{size}x{size} มม.", "ความยาว (ม.)": PILE_LEN, "ระดับหัวเข็ม": round(top, 2),
                    "ระดับปลายเข็ม": round(top-PILE_LEN, 2), "พิกัดแบบ x,y": f"{x:.3f}, {y:.3f}"})

    def tag(x, y):
        gx = min(range(11), key=lambda i: abs(GX[i]-x)); gy = min(range(10), key=lambda j: abs(GY[j]-y))
        return f"{GXN[gx]}/{GYN[gy]}" if abs(GX[gx]-x) < 0.2 and abs(GY[gy]-y) < 0.2 else f"x{x:.2f} y{y:.2f}"

    # I35-22 under floor + F1P drop panel (360)
    for x, y in V["I35"]:
        pile(x, y, LV["drop_bot"]+0.05, 350, "I35-22", "เสาเข็ม I-350x350 รับพื้นโรงงาน", "M21A", "2.1.2 เสาเข็มใต้พื้น")
        vbox("found", "IfcFooting", "Drop panel F1P 1.00x1.00x0.20", "F1P", x-0.5, y-0.5, x+0.5, y+0.5,
             LV["drop_bot"], LV["drop_bot"]+0.20, "M24", "2.2.2 Drop panel F1P", pre="PILE_CAP", src=POS)
    # F2P 46 footings, 2 x I26-22 each (pile positions from drawing)
    for d in V["F2P"]:
        x, y = d["x"], d["y"]
        a_, b_ = (1.5, 0.6) if d["long"] == "X" else (0.6, 1.5)
        vbox("found", "IfcFooting", f"ฐานราก F2P 0.60x1.50x0.80 @ {tag(x, y)}", "F2P", x-a_/2, y-b_/2, x+a_/2, y+b_/2,
             LV["f2p_bot"], LV["f2p_bot"]+0.80, "M22", "2.2.1 ฐานราก F2P", pre="PILE_CAP", src=POS)
    for x, y in V["I26_F2P"]:
        pile(x, y, LV["f2p_bot"]+0.05, 260, "I26-22", "เสาเข็ม I-260x260 รับฐานราก F2P (หนวดกุ้ง 4-DB12-2.5 ม.)", "M21A", "2.1.1 เสาเข็มฐานราก")
    # C1 45 + C2 1 (S201) : RC columns from top of footing to +4.50
    for d in V["C1"]:
        x, y = d["x"], d["y"]
        ca, cb = (0.50, 0.30) if d["long"] == "X" else (0.30, 0.50)
        vbox("rc", "IfcColumn", f"เสา คสล. C1 0.30x0.50 @ {tag(x, y)}", "C1", x-ca/2, y-cb/2, x+ca/2, y+cb/2,
             LV["f2p_bot"]+0.80, LV["col_top_rc"], "M23", "2.3.1 เสา คสล. C1", pre="COLUMN", src=POS)
    for x, y in V["C2"]:
        vbox("rc", "IfcColumn", f"เสา คสล. C2 0.50x0.50 @ {tag(x, y)}", "C2", x-0.25, y-0.25, x+0.25, y+0.25,
             LV["f2p_bot"]+0.80, LV["col_top_rc"], "M23", "2.3.2 เสา คสล. C2", pre="COLUMN", src=POS)
    for d in V["C1"] + [{"x": p[0], "y": p[1]} for p in V["C2"]]:
        x, y = d["x"], d["y"]
        vbox("steel", "IfcColumn", f"เสาเหล็ก H250x175x44.1 kg/m @ {tag(x, y)}", "SC1", x-0.0875, y-0.125, x+0.0875, y+0.125,
             LV["col_top_rc"], LV["eave"], "M31", "2.5.1 เสาเหล็ก", pre="COLUMN", extra={"น้ำหนัก (กก./ม.)": 44.1})
    # F1P-1 single-pile footings (11) + I26
    for x, y in V["F1P1"]:
        vbox("found", "IfcFooting", f"ฐานราก F1P-1 0.60x0.60x0.60 @ {tag(x, y)}", "F1P-1", x-0.3, y-0.3, x+0.3, y+0.3,
             LV["f1p1_bot"], LV["f1p1_bot"]+0.60, "M44", "2.2.3 ฐาน F1P-1", pre="PILE_CAP", src=POS)
    for x, y in V["I26_F1P1"]:
        pile(x, y, LV["f1p1_bot"]+0.05, 260, "I26-22", "เสาเข็ม I-260x260 อาคารประกอบ (F1P-1)", "M21B", "2.1.3 เสาเข็มอาคารประกอบ", grp="pile_a")
    for x, y in V["C3"]:
        vbox("rc", "IfcColumn", "เสา คสล. C3 0.20x0.20", "C3", x-0.1, y-0.1, x+0.1, y+0.1, LV["f1p1_bot"]+0.60, 3.0,
             "M44", "2.3.3 เสา คสล. C3", pre="COLUMN", src=POS)
    # I26 underground tank (17), cut-off lowered
    for x, y in V["I26_tank"]:
        pile(x, y, LV["tank_bot"]+0.05, 260, "I26", "เสาเข็ม I-260x260 รับถังใต้ดิน (ลดระดับ 1 ม.)", "M21B", "2.1.4 เสาเข็มถังใต้ดิน", grp="pile_a")
    # I22-TR transformer (6)
    for x, y in V["I22_TR"]:
        pile(x, y, -0.40, 220, "I22-TR", "เสาเข็ม I-220x220 รับฐานหม้อแปลง", "M21B", "4.3.1 เข็มฐานหม้อแปลง", grp="pile_a")
    # I22-22 road piles + F1A (232 on plan)
    for x, y in V["I22_road"]:
        pile(x, y, LV["f1a_bot"]+0.05, 220, "I22-22", "เสาเข็ม I-220x220 รับพื้นถนนรอบอาคาร", "M21C", "4.1.1 เข็มพื้นถนน", grp="pile_r")
    for x, y in V["F1A"]:
        vbox("ext", "IfcFooting", "ฐาน F1A 0.60x0.60x0.30 รับพื้นถนน", "F1A", x-0.3, y-0.3, x+0.3, y+0.3,
             LV["f1a_bot"], LV["f1a_bot"]+0.30, "M41", "4.1.2 ฐาน F1A", pre="PILE_CAP", src=POS)
    # 0.66 m pads with I26 along south/east boundary (function unknown)
    for x, y in V["SQ66"]:
        vbox("found", "IfcFooting", "ฐาน 0.66x0.66 แนวเขตที่ดิน (ไม่ทราบหน้าที่)", "SQ66", x-0.33, y-0.33, x+0.33, y+0.33,
             -0.45, -0.15, "M41", "4.6.1 ฐาน 0.66 แนวเขต", pre="PILE_CAP", src="แบบ S201 (ตำแหน่ง) / หน้าที่+ระดับรอยืนยัน")
    for x, y in V["I26_SQ66"]:
        pile(x, y, -0.40, 260, "I26-B", "เสาเข็ม I-260x260 ใต้ฐาน 0.66 แนวเขตที่ดิน", "M21B", "4.6.1 ฐาน 0.66 แนวเขต", src="แบบ S201 (ตำแหน่ง) / หน้าที่+ระดับรอยืนยัน", grp="pile_a")

    # ---------------- 2.3 grade beams B1 (perimeter + grid 6) top +0.50 ----------------
    B1 = [((0, 0), (BW, 0)), ((0, BD), (BW, BD)), ((0, 0), (0, BD)), ((BW, 0), (BW, BD)), ((30, 0), (30, BD))]
    for (p0, p1) in B1:
        for k in range(int(length((p1[0]-p0[0], p1[1]-p0[1], 0))/6)):
            a = (p0[0]+(p1[0]-p0[0])*k/ (length((p1[0]-p0[0], p1[1]-p0[1], 0))/6), p0[1]+(p1[1]-p0[1])*k/(length((p1[0]-p0[0], p1[1]-p0[1], 0))/6))
            n = length((p1[0]-p0[0], p1[1]-p0[1], 0))/6
            b = (p0[0]+(p1[0]-p0[0])*(k+1)/n, p0[1]+(p1[1]-p0[1])*(k+1)/n)
            member("rc", "IfcBeam", "คานคอดิน B1 0.20x0.60", "B1", (a[0], a[1], 0.20), (b[0], b[1], 0.20),
                   0.20, 0.60, "M24", "2.3.1 คานคอดิน คสล.", pre="BEAM")
    # B3 0.20x0.40 annex beams
    for r, z in [(TOILET, LV["ffl"]-0.20), (CHEM, -0.20)]:   # S3: B3 ระดับพื้นชั้น 1 (ห้องน้ำ 23.30 ม.) / ระดับถนน (ห้องสารเคมี 17.15 ม.)
        pts = rect(*r)
        for i in range(4):
            p0, p1 = pts[i], pts[(i+1) % 4]
            if r is CHEM and p0[0] == 0 and p1[0] == 0: continue
            member("rc", "IfcBeam", "คาน B3 0.20x0.40", "B3", (p0[0], p0[1], z), (p1[0], p1[1], z), 0.2, 0.4,
                   "M44", "2.3.5 คาน B3", pre="BEAM", src="แบบ S202 (ตำแหน่ง+ระดับ)")
    member("rc", "IfcBeam", "คาน B3 0.20x0.40", "B3", (CHEM[0], 3.006, -0.20), (0.0, 3.006, -0.20), 0.2, 0.4,
           "M44", "2.3.5 คาน B3", pre="BEAM", src="แบบ S202 (ตำแหน่ง+ระดับ)")

    # ---------------- slabs ----------------
    vbox("slab", "IfcSlab", "พื้น S1 คสล. หนา 0.20 ม. วางบนเสาเข็ม (TOP +0.50)", "S1", 0, 0, BW, BD, 0.30, 0.50,
         "M25", "2.3.2 พื้นชั้นล่าง คสล.", pre="FLOOR", extra={"ผิว": "ขัดมันผสม Floor Hardener (3.3.1)"})
    holes = [bldg, rect(*TANK), rect(*TRANS), rect(*TOILET), rect(*CHEM), rect(*RAMP_N), rect(*RAMP_S)]
    road_outer = offset_rect_poly(SITE, 0.6)
    plan_prism("ext", "IfcSlab", "พื้นถนนรอบอาคาร S2 คสล. หนา 0.15 ม. (TOP ±0.00)", "S2", road_outer, holes,
               -0.15, 0.0, "M42", "4.1 งานพื้นถนนรอบอาคาร S2", pre="BASESLAB")
    vbox("ext", "IfcSlab", "ฐานหม้อแปลง SF02 หนา 0.25", "SF02", *TRANS, -0.25, 0.10, "M45", "4.3 ฐานหม้อแปลง", pre="BASESLAB", src="สมมติขนาด")
    vbox("slab", "IfcSlab", "พื้นอาคารห้องน้ำ AF01 หนา 0.10 (TOP +0.50)", "AF01", *TOILET, LV["ffl"]-0.10, LV["ffl"], "M44", "2.4.2 พื้น AF01", pre="FLOOR", src="แบบ S202/S6.1")
    vbox("slab", "IfcSlab", "พื้นห้องเก็บสารเคมี AF01 หนา 0.10 (TOP ±0.00)", "AF01", *CHEM, -0.10, 0.0, "M44", "2.4.2 พื้น AF01", pre="FLOOR", src="แบบ S202/S6.1")
    for r, nm in [(RAMP_N, "ทางลาดขนส่งด้านเหนือ (DN)"), (RAMP_S, "ทางลาดขนส่งด้านใต้ (DN)")]:
        y_in = r[3] if r[3] <= 0.01 else r[1]
        y_out = r[1] if r[3] <= 0.01 else r[3]
        p0 = ((r[0]+r[2])/2, y_in, 0.40); p1 = ((r[0]+r[2])/2, y_out, -0.05)
        member("ext", "IfcRamp", nm + " กว้าง 6.00 ม.", "RAMP", p0, p1, r[2]-r[0], 0.20, "M43", "4.2 ทางลาดขนส่ง", up=Z, pre="STRAIGHT_RUN_RAMP", src="แบบ (ขนาดวัดจากผัง)")

    # underground tank: base, walls, top slab
    x0, y0, x1, y1 = TANK
    vbox("ext", "IfcSlab", "ถังเก็บน้ำใต้ดิน - พื้น หนา 0.25 (BF -2.85)", "UGT", x0, y0, x1, y1, -2.85, -2.60, "M26", "4.4 ถังเก็บน้ำใต้ดิน", pre="BASESLAB", src="แบบ (ขนาดวัดจากผัง)")
    for (a0, b0, a1, b1) in [(x0, y0, x1, y0+0.25), (x0, y1-0.25, x1, y1), (x0, y0, x0+0.25, y1), (x1-0.25, y0, x1, y1)]:
        vbox("ext", "IfcWall", "ถังเก็บน้ำใต้ดิน - ผนัง คสล. หนา 0.25", "UGT", a0, b0, a1, b1, -2.60, -0.15, "M26", "4.4 ถังเก็บน้ำใต้ดิน", src="สมมติ")
    vbox("ext", "IfcSlab", "ถังเก็บน้ำใต้ดิน - ฝา หนา 0.15", "UGT", x0, y0, x1, y1, -0.15, 0.0, "M26", "4.4 ถังเก็บน้ำใต้ดิน", pre="ROOF", src="สมมติ")

    # drain channel along site boundary
    drain = offset_rect_poly(SITE, 1.2)
    for i in range(len(drain)):
        p0, p1 = drain[i], drain[(i+1) % len(drain)]
        member("ext", "IfcPipeSegment", "รางระบายน้ำ คสล. พร้อมฝาปิด 0.40x0.50", "DR", (p0[0], p0[1], -0.25), (p1[0], p1[1], -0.25),
               0.40, 0.50, "M46", "4.5 รางระบายน้ำพร้อมฝาปิด", up=Z, pre="GUTTER", src="แบบ (แนวโดยประมาณ)")

    # ---------------- mezzanine F8 ----------------
    for i in range(6):
        for j in range(6):
            x, y = 3.0*(i+1), 3.0*(j+1) - (0.5 if j == 5 else 0)
            x = min(x, MEZZ[2]-0.15); y = min(y, MEZZ[3]-0.15)
            vbox("steel", "IfcColumn", "เสาชั้นลอย H250x250x66.5 kg/m", "MC", x-0.125, y-0.125, x+0.125, y+0.125,
                 LV["ffl"], LV["mezz"], "M35", "3.6 ชั้นลอย (โครงเหล็ก)", pre="COLUMN", extra={"น้ำหนัก (กก./ม.)": 66.5})
    for k in range(7):
        y = min(3.0*k, MEZZ[3])
        member("steel", "IfcBeam", "คานชั้นลอย H200x100 (สมมติ)", "MB", (MEZZ[0], y, 3.17), (MEZZ[2], y, 3.17), 0.10, 0.20,
               "M35", "3.6 ชั้นลอย (โครงเหล็ก)", pre="BEAM", src="สมมติ")
    for k in range(7):
        x = 3.0*k
        member("steel", "IfcBeam", "คานชั้นลอย H200x100 (สมมติ)", "MB", (x, MEZZ[1], 3.17), (x, MEZZ[3], 3.17), 0.10, 0.20,
               "M35", "3.6 ชั้นลอย (โครงเหล็ก)", pre="BEAM", src="สมมติ")
    vbox("slab", "IfcSlab", "พื้นชั้นลอย F8 (TOP +3.30)", "F8", *MEZZ, 3.27, 3.30, "M35", "3.6 ชั้นลอย (พื้น)", pre="FLOOR")
    member("steel", "IfcStair", "บันไดชั้นลอย กว้าง 1.40 ม.", "ST", (5.8, 17.2, 0.5), (1.6, 17.2, 3.3), 1.4, 0.15,
           "M35", "3.6 ชั้นลอย (บันได)", up=Z, src="แบบ (ตำแหน่ง DN)")

    # ---------------- steel roof ----------------
    E_TOP, R_TOP = 10.00, 13.95          # top chord at eave / ridge
    E_BOT, R_BOT = LV["eave"], 11.00     # bottom chord at eave / ridge
    def ztop(x): return E_TOP + (R_TOP-E_TOP)*(1-abs(x-30)/30)
    def zbot(x): return E_BOT + (R_BOT-E_BOT)*(1-abs(x-30)/30)
    for j, y in enumerate(GY):
        for (xa, xb) in [(0.0, 30.0), (30.0, 60.0)]:
            member("steel", "IfcMember", f"โครงถัก (Truss) แนว {GYN[j]} - คอร์ดบน 2C-150x65x20x3.2", "TR-TC",
                   (xa, y, ztop(xa)), (xb, y, ztop(xb)), 0.13, 0.15, "M32", "2.4.1 โครงสร้างเหล็ก (โครงถัก)", up=Z, pre="CHORD", src="แบบ (หน้าตัดสมมติ)", extra={"น้ำหนัก (กก./ม.)": 15.0})
            member("steel", "IfcMember", f"โครงถัก (Truss) แนว {GYN[j]} - คอร์ดล่าง 2C-150x65x20x3.2", "TR-BC",
                   (xa, y, zbot(xa)), (xb, y, zbot(xb)), 0.13, 0.15, "M32", "2.4.1 โครงสร้างเหล็ก (โครงถัก)", up=Z, pre="CHORD", src="แบบ (หน้าตัดสมมติ)", extra={"น้ำหนัก (กก./ม.)": 15.0})
            n = 20
            for k in range(n+1):
                x = xa + (xb-xa)*k/n
                member("steel", "IfcMember", f"โครงถัก แนว {GYN[j]} - ค้ำตั้ง C-100x50x20x2.3", "TR-W",
                       (x, y, zbot(x)), (x, y, ztop(x)), 0.05, 0.10, "M32", "2.4.1 โครงสร้างเหล็ก (โครงถัก)", up=X, pre="WEB", src="สมมติ", extra={"น้ำหนัก (กก./ม.)": 4.06})
                if k < n:
                    x2 = xa + (xb-xa)*(k+1)/n
                    pa, pb = ((x, y, zbot(x)), (x2, y, ztop(x2))) if k % 2 == 0 else ((x, y, ztop(x)), (x2, y, zbot(x2)))
                    member("steel", "IfcMember", f"โครงถัก แนว {GYN[j]} - ค้ำทแยง C-100x50x20x2.3", "TR-W",
                           pa, pb, 0.05, 0.10, "M32", "2.4.1 โครงสร้างเหล็ก (โครงถัก)", up=Z, pre="WEB", src="สมมติ", extra={"น้ำหนัก (กก./ม.)": 4.06})
    # purlins C-125x50x20x3.2 @ ~1.2 m along slope, continuous along y
    for side in (0, 1):
        for k in range(26):
            x = (k*1.2 + 0.3) if side == 0 else (60 - k*1.2 - 0.3)
            if abs(x-30) < 0.4: continue
            z = ztop(x) + 0.10
            member("steel", "IfcMember", "แป C-125x50x20x3.2", "PL", (x, -0.3, z), (x, BD+0.3, z), 0.05, 0.125,
                   "M33", "2.4.1 โครงสร้างเหล็ก (แป)", up=Z, pre="PURLIN", src="สมมติ", extra={"น้ำหนัก (กก./ม.)": 6.13})
    # roof X-bracing RB 12 mm, end bays
    for (ya, yb) in [(0, 6), (48, 54)]:
        for i in range(10):
            xa, xb = 6.0*i, 6.0*(i+1)
            for (p, q) in [((xa, ya), (xb, yb)), ((xa, yb), (xb, ya))]:
                member("steel", "IfcMember", "ค้ำยันหลังคา RB12 + Turnbuckle", "BR", (p[0], p[1], ztop(p[0])-0.08), (q[0], q[1], ztop(q[0])-0.08),
                       0.012, 0.012, "M32", "2.4.1 โครงสร้างเหล็ก (ค้ำยัน)", up=Z, pre="BRACE", src="สมมติ", extra={"น้ำหนัก (กก./ม.)": 0.888})
    # wall girts C-125 on walls +5.2 .. eave
    for zg in (5.30, 6.80, 8.30):
        for (p0, p1) in [((0, 0), (BW, 0)), ((0, BD), (BW, BD)), ((0, 0), (0, BD)), ((BW, 0), (BW, BD))]:
            member("steel", "IfcMember", "แปผนัง (Girt) C-125x50x20x3.2", "GT", (p0[0], p0[1], zg), (p1[0], p1[1], zg), 0.125, 0.05,
                   "M33", "2.4.1 โครงสร้างเหล็ก (แปผนัง)", up=Z, pre="STUD", src="สมมติ", extra={"น้ำหนัก (กก./ม.)": 6.13})

    # roof sheets (two slopes)
    for side in (0, 1):
        xa, xb = (-0.6, 30.0) if side == 0 else (30.0, 60.6)
        za, zb = ztop(max(xa, 0)) + 0.2 - (0.08 if side == 0 else 0), ztop(min(xb, 60)) + 0.2
        if side == 1: za, zb = ztop(30)+0.2, ztop(60)+0.2-0.08
        pa, pb = (xa, 0, za), (xb, 0, zb)
        v = sub(pb, pa); L = length(v); ex = norm(v)
        ez = norm(cross(ex, Y)) if side == 1 else norm(cross(ex, Y))
        if ez[2] < 0: ez = mul(ez, -1)
        c = (xa+(xb-xa)/2, BD/2, (za+zb)/2)
        box("roof", "IfcCovering", "หลังคาเมทัลชีท หนา 0.47 มม. + ฉนวน PU 25 มม.", "RF", c, ex, Y, ez, L, BD+1.0, 0.05,
            "M34", "3.1 หลังคาและผนังภายนอก (มุงหลังคา)", pre="ROOFING", src="สมมติสเปค")
    # jackroof
    vbox("roof", "IfcCovering", "Jack roof กว้าง 6.00 ม. (สัน +15.25)", "JR", 27.0, 6.0, 33.0, 48.0, LV["jack"]-0.05, LV["jack"],
         "M34", "3.1 หลังคาและผนังภายนอก (Jack roof)", pre="ROOFING")
    for x in (27.0, 33.0):
        vbox("roof", "IfcCovering", "ช่องระบายอากาศ Jack roof (ตะแกรง)", "JR-L", x-0.03, 6.0, x+0.03, 48.0, ztop(x)+0.2, LV["jack"]-0.05,
             "M34", "3.1 หลังคาและผนังภายนอก (Jack roof)", pre="CLADDING")
    # gutters & downpipes
    for x in (-0.6, 60.6):
        vbox("roof", "IfcPipeSegment", "รางน้ำฝนเหล็กอาบสังกะสี 0.30x0.30", "GU", x-0.15, -0.5, x+0.15, BD+0.5, 9.75, 10.05,
             "M34", "3.1 หลังคาและผนังภายนอก (รางน้ำ)", pre="GUTTER", src="สมมติ")
        for y in (3.0, 15.0, 27.0, 39.0, 51.0):
            vbox("roof", "IfcPipeSegment", "ท่อระบายน้ำฝน PVC Ø4\"", "DP", x-0.05, y-0.05, x+0.05, y+0.05, 0.0, 9.75,
                 "M34", "3.1 หลังคาและผนังภายนอก (ท่อน้ำฝน)", pre="RIGIDSEGMENT", src="สมมติ")

    # ---------------- walls ----------------
    # ผนังก่อ +0.50 ถึง +4.35 (ต่ำกว่าหัวเสา 15 ซม.) + คานทับหลัง +4.35..+4.50, เสาเอ็นกลางช่วง/ข้างวงกบ, คานเอ็นระดับหลังประตู
    for w in wall_bays():
        for seg in w["masonry"]:
            (ax0, ay0), (ax1, ay1) = seg
            vbox("wall", "IfcWall", f"ผนังก่ออิฐมวลเบา หนา 0.15 +0.50 ถึง +4.35 ({w['name']})", "W1",
                 min(ax0, ax1)-(WALL_T/2 if ax0 == ax1 else 0), min(ay0, ay1)-(WALL_T/2 if ay0 == ay1 else 0),
                 max(ax0, ax1)+(WALL_T/2 if ax0 == ax1 else 0), max(ay0, ay1)+(WALL_T/2 if ay0 == ay1 else 0),
                 LV["ffl"], WALL_TOP, "M36", "3.2.1 ผนังก่ออิฐ", pre="SOLIDWALL", src="ผู้ว่าจ้างกำหนดระดับ / A202")
        for (p, q) in w["bays"]:
            member("wall", "IfcBeam", "คานทับหลัง คสล. 0.15x0.15 ม. +4.35..+4.50", "LB", (p[0], p[1], WALL_TOP+0.075), (q[0], q[1], WALL_TOP+0.075),
                   WALL_T, 0.15, "M36", "3.2.3 คานทับหลัง", pre="LINTEL", src="ผู้ว่าจ้างกำหนดระดับ")
            member("wall", "IfcBeam", "คานเอ็น คสล. 0.15x0.10 ม. ระดับหลังประตู +2.60", "TB", (p[0], p[1], TIE_Z+0.05), (q[0], q[1], TIE_Z+0.05),
                   WALL_T, 0.10, "M36", "3.2.4 คานเอ็น", pre="BEAM", src="สมมติตามมาตรฐานผนังก่อ (สูง > 3 ม.)")
        for (x_, y_) in w["stiff"]:
            hx, hy = (0.05, 0.075) if w["grid"] in ("A", "J") else (0.075, 0.05)
            vbox("wall", "IfcColumn", "เสาเอ็น คสล. 0.15x0.10 ม. +0.50 ถึง +4.35", "SC", x_-hx, y_-hy, x_+hx, y_+hy,
                 LV["ffl"], WALL_TOP, "M36", "3.2.5 เสาเอ็น", pre="COLUMN", src="สมมติ: กลางช่วงเสา 6 ม. และข้างวงกบ")
    for (x0_, y0_, x1_, y1_) in [(0, 0, BW, 0), (0, BD, BW, BD), (0, 0, 0, BD), (BW, 0, BW, BD)]:
        horiz = y0_ == y1_
        # metal sheet cladding +5.20 -> eave / gable
        o = (-0.12 if x0_ == 0 and not horiz else (0.12 if x0_ == BW and not horiz else 0))
        oy = (-0.12 if horiz and y0_ == 0 else (0.12 if horiz and y0_ == BD else 0))
        if horiz:
            outline = [(0, 5.20), (60, 5.20), (60, ztop(60)+0.2), (30, ztop(30)+0.2), (0, ztop(0)+0.2)]
            prism("wall", "IfcCovering", "ผนังเมทัลชีท (ด้านจั่ว) +5.20 ถึงหลังคา", "W2", (0, y0_+oy, 0), X, Z, (0.0, -1.0, 0.0), outline, [], 0.03,
                  "M37", "3.1 หลังคาและผนังภายนอก (ผนังเมทัลชีท)", pre="CLADDING", src="แบบ A202")
        else:
            vbox("wall", "IfcCovering", "ผนังเมทัลชีท (ด้านชายคา) +5.20 ถึง +10.00", "W2", x0_+o-0.015, -0.1, x0_+o+0.015, BD+0.1, 5.20, ztop(x0_)+0.2,
                 "M37", "3.1 หลังคาและผนังภายนอก (ผนังเมทัลชีท)", pre="CLADDING", src="แบบ A202")
    # loading doors
    vbox("door", "IfcDoor", "ประตูม้วนเหล็ก 6.00x4.00 ม. (ทางลาดเหนือ)", "RD1", 24.0, -0.06, 30.0, 0.06, LV["ffl"], 4.50, "M38", "3.4 ประตูม้วน/ประตูเลื่อนขนส่ง", src="สมมติขนาด")
    vbox("door", "IfcDoor", "ประตูม้วนเหล็ก 6.00x4.00 ม. (ทางลาดใต้)", "RD2", 36.0, BD-0.06, 42.0, BD+0.06, LV["ffl"], 4.50, "M38", "3.4 ประตูม้วน/ประตูเลื่อนขนส่ง", src="สมมติขนาด")
    # personnel doors from A101 tags (sizes await door schedule)
    for (dx_, dy_, ax, mk) in [(0.0, 29.44, "Y", "D1"), (60.0, 11.39, "Y", "D1"), (42.59, 4.0, "X", "D2"), (48.61, 4.0, "X", "D2"), (54.55, 3.0, "X", "D1")]:
        w_ = 1.8 if mk == "D2" else 1.0
        a0, a1 = (dx_-0.08, dx_+0.08) if ax == "Y" else (dx_-w_/2, dx_+w_/2)
        b0, b1 = (dy_-w_/2, dy_+w_/2) if ax == "Y" else (dy_-0.08, dy_+0.08)
        vbox("door", "IfcDoor", f"ประตู {mk} (ตำแหน่งจาก A101 ขนาดรอตารางประตู)", mk, a0, b0, a1, b1, LV["ffl"], LV["ffl"]+2.10,
             "M38", "3.4.2 ประตู D1/D2/D4", src="แบบ A101 (ตำแหน่ง) / ขนาดสมมติ")

    # ---------------- rooms / annex architecture ----------------
    def room(r, name, mark, z0, z1, task, boq, src):
        x0, y0, x1, y1 = r
        for (a0, b0, a1, b1) in [(x0, y0, x1, y0+0.1), (x0, y1-0.1, x1, y1), (x0, y0, x0+0.1, y1), (x1-0.1, y0, x1, y1)]:
            vbox("annex", "IfcWall", f"{name} - ผนังก่ออิฐ", mark, a0, b0, a1, b1, z0, z1, task, boq, pre="PARTITIONING", src=src)
        vbox("annex", "IfcSlab", f"{name} - หลังคา/ฝ้า", mark, x0, y0, x1, y1, z1, z1+0.1, task, boq, pre="ROOF", src=src)
    room(TOILET, "อาคารห้องน้ำ", "WC", LV["ffl"], 3.0, "M44", "3.6 สถาปัตยกรรมอาคารประกอบ", "สมมติตำแหน่ง/ขนาดจาก A101")
    room(CHEM, "ห้องเก็บสารเคมี (Chemical Drum Storage) 21.84 ตร.ม.", "CHEM", 0.0, 3.3, "M44", "3.6 สถาปัตยกรรมอาคารประกอบ", "แบบ A101")
    room(MDB, "ห้อง MDB 17.79 ตร.ม.", "MDB", 0.5, 3.3, "M39", "3.6 สถาปัตยกรรมอาคารประกอบ", "แบบ A101")
    room(ROOMS, "ห้องประกอบแนวกริด A (รอแบบ)", "RM", 0.5, 3.3, "M39", "3.6 สถาปัตยกรรมอาคารประกอบ", "สมมติ (A101)")
    vbox("ext", "IfcSlab", "พื้นทางเท้า/ลานหน้าห้องเก็บสารเคมี AF01", "AF01", -3.64, 6.0, 0.0, 10.6, -0.10, 0.0, "M42", "4.1 งานพื้นถนนรอบอาคาร", pre="BASESLAB", src="สมมติตำแหน่ง")
    return ELEMENTS


# =====================================================================
#  4D SCHEDULE (CPM forward pass, working days Mon-Sat, Thai holidays)
# =====================================================================
import datetime as dt
HOLIDAYS = {dt.date(2026, 12, 5), dt.date(2026, 12, 10), dt.date(2026, 12, 31), dt.date(2027, 1, 1), dt.date(2027, 1, 2),
            dt.date(2027, 2, 22), dt.date(2027, 4, 6), dt.date(2027, 4, 13), dt.date(2027, 4, 14), dt.date(2027, 4, 15),
            dt.date(2027, 5, 1), dt.date(2027, 5, 20), dt.date(2027, 6, 3), dt.date(2027, 7, 28)}


def is_work(d): return d.weekday() != 6 and d not in HOLIDAYS


def add_wd(d, n):
    """finish date of a task that starts on d and lasts n working days."""
    while not is_work(d): d += dt.timedelta(days=1)
    k = 1
    while k < n:
        d += dt.timedelta(days=1)
        if is_work(d): k += 1
    return d


def next_wd(d):
    d += dt.timedelta(days=1)
    while not is_work(d): d += dt.timedelta(days=1)
    return d


# id, WBS, name, duration (working days), predecessors [(id, type, lag)], crew note
TASKS = [
    ("P0", "P", "ยื่นราคา/อนุมัติจ้างงาน Preconstruction", 10, [], "ยื่น 5 พ.ย. 69 เข้างานภายใน 2 สัปดาห์", "milestone-ish"),
    ("P1", "P1", "สำรวจแนวเขตที่ดินและระดับเดิม (Topographic)", 4, [("P0", "FS", 0)], "ทีมสำรวจ 3 คน + กล้อง Total Station", ""),
    ("P3", "P3", "เจาะสำรวจดิน 3 หลุม x 30 ม. (SPT)", 7, [("P0", "FS", 0)], "รถเจาะ Wash boring 1 ชุด", ""),
    ("P2", "P2", "ถางป่า ขุดตอ ลอกหน้าดิน 0.20 ม. ระบายน้ำขัง", 15, [("P1", "SS", 2)], "รถขุด 1 คัน + รถบรรทุก 3 คัน", ""),
    ("P4", "P3", "ทดสอบห้องปฏิบัติการ + รายงานผลสำรวจดิน", 14, [("P3", "FS", 0)], "วิศวกรธรณีเทคนิค", ""),
    ("P5", "P1", "สำรวจระดับหลังเคลียร์ (OGL) + ตารางดินถม", 2, [("P2", "FS", 0)], "ทีมสำรวจ", ""),
    ("M0", "1", "เซ็นสัญญางานหลัก / ส่ง Master schedule / Shop drawing", 6, [("P4", "FS", 0), ("P5", "FS", 0)], "ยื่นราคางานหลัก 15 พ.ย. 69", ""),
    ("M11", "1.2", "Mobilization: รั้ว สำนักงานสนาม โรงเก็บ ไฟฟ้า-ประปาชั่วคราว", 8, [("M0", "SS", 2)], "ช่างไม้/เหล็ก 8 คน", ""),
    ("M12", "1.1", "วางผังอาคาร กริด 1-11/A-J ตั้งหมุด BM ±0.00", 3, [("M0", "FS", 0)], "ทีมสำรวจ", ""),
    ("M13", "1.3", "ถมดินบดอัดหนา 0.30 ม. (1,114 ลบ.ม.) + ลานทำงานปั้นจั่น", 6, [("M12", "SS", 1)], "รถเกลี่ย/รถบด/รถบรรทุก 6 คัน ~ 250 ลบ.ม./วัน + ทดสอบ FDT 16 จุด", ""),
    ("M21A", "2.1", "ตอกเข็มอาคาร: I35 ใต้พื้น 360 + I26 ฐาน F2P 92 (2 ปั้นจั่น)", 25, [("M13", "FS", 0)], "ปั้นจั่น 2 ชุด x ~9 ต้น/วัน (เข็ม 22 ม. ต่อ 2 ท่อน)", ""),
    ("M21B", "2.1", "ตอกเข็มอาคารประกอบ/อื่นๆ: F1P-1 11, ถังใต้ดิน 17, หม้อแปลง 6, ฐานแนวเขต 16", 6, [("M21A", "FS", 0)], "ปั้นจั่น 1 ชุด", ""),
    ("M21C", "4.1", "ตอกเข็มพื้นถนนรอบอาคาร I22 249 ต้น (2 ปั้นจั่น)", 14, [("M21A", "FS", 0)], "ปั้นจั่น 2 ชุด x ~9 ต้น/วัน", ""),
    ("M21T", "1.4", "Dynamic Load Test 2 ต้น", 2, [("M21A", "SS", 10)], "หน่วยงานทดสอบ", ""),
    ("M22", "2.2", "ขุดดิน ตัดหัวเข็ม ฐานราก F2P/F1P-1", 18, [("M21A", "SS", 8)], "ทีมโครงสร้าง A 15 คน", ""),
    ("M23", "2.2", "เสาตอม่อ/เสา คสล. C1 0.30x0.50 ถึง +4.50", 18, [("M22", "SS", 6)], "ทีมโครงสร้าง A", ""),
    ("M24", "2.3", "คานคอดิน B1 + Drop panel F1P 360 จุด + ทรายรองพื้น", 20, [("M22", "SS", 10)], "ทีมโครงสร้าง B 15 คน", ""),
    ("M26", "4.4", "ถังเก็บน้ำใต้ดิน คสล.", 20, [("M21B", "FS", 0)], "ทีมโครงสร้าง C 8 คน", ""),
    ("M30", "2.4", "ผลิตโครงเหล็ก (โรงงาน) เสา/โครงถัก/แป", 30, [("M0", "FS", 10)], "โรงงานผู้รับเหมาช่วง ~95 ตัน", ""),
    ("M31", "2.4", "ติดตั้งเสาเหล็ก H250x175 บนหัวเสา คสล.", 8, [("M23", "FS", 5), ("M30", "SS", 15)], "รถเครน 25 ตัน + ทีมเหล็ก 10 คน", ""),
    ("M32", "2.4", "ยกติดตั้งโครงถัก 20 ชุด + ค้ำยัน", 16, [("M31", "SS", 3)], "รถเครน 2 คัน", ""),
    ("M33", "2.4", "ติดตั้งแปหลังคา/แปผนัง", 10, [("M32", "SS", 6)], "ทีมเหล็ก", ""),
    ("M34", "3.1", "มุงหลังคาเมทัลชีท + ฉนวน + Jack roof + รางน้ำ", 18, [("M33", "SS", 4)], "ทีมหลังคา 12 คน", ""),
    ("M25", "2.3", "เทพื้น S1 (6 โซน) + Floor hardener ใต้หลังคา", 24, [("M24", "FS", 0), ("M34", "SS", 8)], "ทีมพื้น + ปั๊มคอนกรีต ~640 ลบ.ม.", ""),
    ("M36", "3.2", "ผนังก่ออิฐ/ฉาบ ถึง +4.50", 22, [("M25", "SS", 8)], "ช่างปูน 12 คน", ""),
    ("M37", "3.1", "ผนังเมทัลชีท +5.20 ถึงหลังคา/จั่ว", 12, [("M33", "FS", 0)], "ทีมหลังคา", ""),
    ("M35", "3.6", "ชั้นลอย F8 (โครงเหล็ก พื้น บันได)", 14, [("M25", "SS", 10)], "ทีมเหล็ก", ""),
    ("M39", "3.6", "ห้อง MDB / ห้องประกอบ แนวกริด A", 18, [("M36", "SS", 5)], "ช่างปูน/ไม้", ""),
    ("M44", "2.5", "อาคารประกอบ: ฐาน F1P-1 เสา คาน ห้องน้ำ / ห้องเก็บสารเคมี", 25, [("M22", "FS", 0), ("M21B", "FS", 0)], "ทีมอาคารประกอบ 8 คน", ""),
    ("M38", "3.4", "ประตูม้วน ประตู-หน้าต่าง ทาสี", 12, [("M36", "FS", 0)], "ผู้รับเหมาช่วง", ""),
    ("M41", "4.1", "ฐาน F1A 249 จุด รับพื้นถนน", 12, [("M21C", "FS", 0)], "ทีมโครงสร้าง C", ""),
    ("M46", "4.5", "รางระบายน้ำ คสล. พร้อมฝาปิด", 15, [("M41", "SS", 4)], "ทีมภายนอก", ""),
    ("M45", "4.3", "ฐานหม้อแปลง", 6, [("M21B", "FS", 3)], "ทีมภายนอก", ""),
    ("M42", "4.1", "พื้นถนนรอบอาคาร S2 2,440 ตร.ม.", 20, [("M41", "FS", 0), ("M34", "FS", 0)], "ทีมพื้น ~366 ลบ.ม.", ""),
    ("M43", "4.2", "ทางลาดขนส่ง 2 จุด", 6, [("M42", "SS", 6), ("M25", "FS", 0)], "ทีมพื้น", ""),
    ("M51", "1.5", "ทดสอบระบบ ตรวจรับ แก้ไขงาน (Punch list)", 8, [("M38", "FS", 0), ("M42", "FS", 0), ("M39", "FS", 0), ("M35", "FS", 0), ("M44", "FS", 0), ("M43", "FS", 0), ("M46", "FS", 0), ("M37", "FS", 0), ("M45", "FS", 0), ("M26", "FS", 0)], "ทีมบริหารโครงการ", ""),
    ("M52", "1.5", "รื้อสิ่งชั่วคราวด้านเหนือ เทพื้นถนนส่วนใต้สิ่งชั่วคราว ทำความสะอาด ส่งมอบ + As-built", 8, [("M51", "FS", 0)], "", ""),
]

PROJECT_START = dt.date(2026, 11, 5)   # ยื่นราคา Preconstruction


def schedule():
    """CPM on working-day indices (Mon-Sat excl. Thai holidays)."""
    days = []
    d = PROJECT_START
    while len(days) < 400:
        if is_work(d): days.append(d)
        d += dt.timedelta(days=1)
    out = {}
    for (tid, wbs, name, dur, preds, crew, _) in TASKS:
        es = 0
        for (p, typ, lag) in preds:
            es = max(es, out[p]["es"] + lag if typ == "SS" else out[p]["ef"] + 1 + lag)
        out[tid] = dict(id=tid, wbs=wbs, name=name, dur=dur, preds=preds, crew=crew, es=es, ef=es + dur - 1)
    end = max(t["ef"] for t in out.values())
    succ = {k: [] for k in out}
    for k, t in out.items():
        for (p, typ, lag) in t["preds"]: succ[p].append((k, typ, lag))
    for tid in [t[0] for t in TASKS][::-1]:
        t = out[tid]; lf = end
        for (s, typ, lag) in succ[tid]:
            ls_s = out[s]["lf"] - out[s]["dur"] + 1
            lf = min(lf, ls_s - 1 - lag if typ == "FS" else ls_s - lag + t["dur"] - 1)
        t["lf"] = lf
        t["float"] = lf - t["ef"]
        t["critical"] = t["float"] <= 0
    for t in out.values():
        t["start"], t["finish"] = days[t["es"]], days[t["ef"]]
    return out
