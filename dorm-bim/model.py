"""หอพักคนงาน 5 ชั้น อาคาร A — นิยามชิ้นส่วนโมเดล (แหล่งข้อมูลเดียวสำหรับ SketchUp / GLB / JSON)

แกน: x ตามกริด 1→10 (เมตร), y ตามกริด A→F (A = ด้านหน้า, y=0), z ระดับ (±0.00 = พื้นรอบอาคาร)
แหล่งแบบ: FOR CON (S101, S102, S910, S911), S001, S106, S107, A201, A203
ค่าที่ไม่มีในแบบใส่ไว้ใน ASSUMPTIONS และติด flag "assumed" ที่ชิ้นส่วน
"""
import json, math

# ---------- กริดและระดับ ----------
GX = [i * 3.5 for i in range(10)]                     # กริด 1..10
GY = {'A': 0.0, 'B': 1.65, 'C': 6.75, 'CX': 7.75, 'D': 8.75, 'E': 13.85, 'F': 15.5}
FL = {1: 0.30, 2: 3.50, 3: 6.70, 4: 9.90, 5: 13.10}    # ระดับพื้นสำเร็จ
ROOF_BEAM = 16.30
RIDGE = 20.00
FOOT_TOP = -0.30
SLAB_T = 0.10           # พื้นสำเร็จรูป 0.05 + topping 0.05 (S911 แบบ PS)
GS_T = 0.10             # พื้นชั้น 1 (GS)

# เสา C1 (S910): ชั้น 1–2 0.35x0.50, ชั้น 3 0.30x0.50, ชั้น 4–5 0.30x0.40
COL_SEC = {0: (0.35, 0.50), 1: (0.35, 0.50), 2: (0.35, 0.50), 3: (0.30, 0.50), 4: (0.30, 0.40), 5: (0.30, 0.40)}
COL_ROWS = ['B', 'C', 'D', 'E']

# คานซอย B5 (S102) ตำแหน่ง x
B5_X = [1.5, 5.5, 8.5, 12.5, 15.5, 19.5, 22.5, 26.5, 30.0]   # ตามระยะ 1.50/2.00 ในแปลน A-02 และผังคาน S-04
STAIR_BAY = (3, 4)      # ช่วงกริด 4–5 (index 3..4)
# บันไดหลัก (A-05): ชานพักในแถบยื่นด้านหน้า กว้าง 1.50, ช่วงบันไดละ 9 ลูกนอน x 0.30 = 2.70 จากแนว B, ลูกตั้ง 0.16 x 20
ST_RUN_Y1 = 1.65 + 2.70                        # ปลายช่วงบันไดฝั่งห้อง (ขอบช่องเปิด)

ASSUMPTIONS = [
    'แนวด้านยาวของเสา C1 (0.50) วางตามแกน y (ด้านสั้นอาคาร)',
    'หลังคาน = ระดับพื้นสำเร็จ − 0.10 ม. (ใต้พื้นสำเร็จรูป+topping)',
    'ไม่มีคาน คสล. หลังคา (ผู้ใช้ยกเลิก 9 พ.ย. 2569): ขื่อ/อะเสเหล็กวางบนหัวเสาและผนังชั้น 5 ที่ +16.30, ผนังชั้น 5 ก่อถึง +16.30',
    'หลังคาปั้นหยา: ผิวบนที่สัน +20.00 แนว CX, ท้องจันทันวางบนอะเส 2C125 (หลังอะเส +16.425) ได้ความลาด ≈24° ตาม S107, ชายคายื่นด้านยาว 1.195 ม. ด้านสกัด 1.33 ม.',
    'โครงหลังคาตาม S106/S107: ขื่อ/อะเส/สะพาน/ตะเข้/อกไก่/คานรับเสาดั้ง 2C125x50x20x3.2, เสารับจันทัน/เสารับอกไก่/ขื่อทางยาว 2C100x50x20x3.2, จันทัน/เหล็กทะแยง C100x50x20x3.2 ระยะจันทัน 0.875 ม.',
    '2C ขึ้นแบบประกบปากชนกันเป็นกล่อง (รอผู้ใช้ยืนยันว่าไม่ใช่ประกบหลัง); ไม่ได้ขึ้นแปสำเร็จรูปและเพลทรอยต่อ; น้ำหนักเหล็ก C125 6.13 กก./ม., C100 5.50 กก./ม.',
    'ขื่อด้านสั้นวางทุกกริด 2–9 บนคานหลังคา, เสารับจันทันที่แนว B, กลางช่วง B–C (2.55 ม.), C, D และฝั่ง E; คานรับเสาดั้งที่ +18.74 (2.44 ม. จาก +16.30)',
    'บันไดหลักตาม A-05: ช่วงกริด 4–5 ช่วงบันไดกว้าง 1.50 ช่องกลาง 0.40 ลูกนอน 0.30 x 9 ลูกตั้ง 0.16 x 20 ชานพักกว้าง 1.50 ในแถบยื่นด้านหน้า ที่ระดับพื้น +1.60; ท้องบันไดและชานพักหนา 0.12 ม. (สมมติ)',
    'คานบันได BST1/BST2/BST3 200x400 ตาม S-04: BST1 ขอบช่องเปิดระดับพื้น, BST2 (กริด 4,5) และ BST3 (ขอบนอก) ระดับชานพัก',
    'ระยะคานซอย B5 และผนังห้องน้ำปรับตามแปลน A-02/ผังคาน S-04 (เดิมใช้ S102)',
    'คานคอดิน: หลังคาน = +0.20 (ใต้พื้น GS 0.10 ม.)',
    'งานโครงสร้างทุกชิ้นที่ไม่มีในแผน R3 ถือว่าเสร็จก่อนวันเริ่มแผน 9 พ.ย. 2569 (กิจกรรม DONE)',
]

elements = []


def add(eid, cat, floor, task, geom, name=None, assumed=False, qty=None):
    elements.append(dict(id=eid, name=name or eid, category=cat, floor=floor, task=task,
                         assumed=assumed, geom=geom, qty=qty or {}))


def member(p0, p1, w, d):
    """ชิ้นส่วนแนวเส้น หน้าตัด w (กว้างแนวนอน) x d (ลึก/สูง) แกนอยู่กึ่งกลางหน้าตัด"""
    return dict(type='member', p0=[round(v, 4) for v in p0], p1=[round(v, 4) for v in p1], w=w, d=d)


def prism(poly, z0, t):
    return dict(type='prism', poly=[[round(x, 4), round(y, 4)] for x, y in poly], z0=round(z0, 4), t=t)


def plate(pts, t):
    """แผ่นระนาบ 3 มิติ (ผิวหลังคา) หนา t ตามแนวตั้งฉาก"""
    return dict(type='plate', pts=[[round(v, 4) for v in p] for p in pts], t=t)


def mlen(p0, p1):
    return math.dist(p0, p1)


# ---------- คานคอดิน (S101) ----------
for r in COL_ROWS:                      # GB2 250x500 แนวยาว
    for i in range(9):
        x0, x1 = GX[i], GX[i + 1]
        z = 0.20 - 0.25
        L = 3.5 - 0.35
        add(f'GB2-{r}{i+1}-{i+2}', 'คานคอดิน', 1, 'DONE',
            member((x0 + 0.175, GY[r], z), (x1 - 0.175, GY[r], z), 0.25, 0.50),
            qty=dict(length=L, concrete=round(L * 0.25 * 0.5, 4)))
for i in range(10):                     # GB1 250x400 แนวขวาง
    for a, b in (('B', 'C'), ('C', 'D'), ('D', 'E')):
        y0, y1 = GY[a] + 0.25, GY[b] - 0.25
        z = 0.20 - 0.20
        L = y1 - y0
        add(f'GB1-{i+1}-{a}{b}', 'คานคอดิน', 1, 'DONE',
            member((GX[i], y0, z), (GX[i], y1, z), 0.25, 0.40),
            qty=dict(length=round(L, 3), concrete=round(L * 0.25 * 0.4, 4)))

# ---------- เสา ----------
levels = [FOOT_TOP, FL[1], FL[2], FL[3], FL[4], FL[5], ROOF_BEAM]
for k in range(6):                      # k=0 ตอม่อ, 1..5 เสาชั้น 1..5
    z0, z1 = levels[k], levels[k + 1]
    w, d = COL_SEC[k]
    task = 'A01' if k == 5 else 'DONE'
    tag = 'ตอม่อ' if k == 0 else f'ชั้น {k}'
    for i in range(10):
        for r in COL_ROWS:
            add(f'C1-{i+1}{r}-{"ST" if k == 0 else "F%d" % k}', 'เสา', max(k, 1), task,
                prism([(GX[i] - w / 2, GY[r] - d / 2), (GX[i] + w / 2, GY[r] - d / 2),
                       (GX[i] + w / 2, GY[r] + d / 2), (GX[i] - w / 2, GY[r] + d / 2)], z0, round(z1 - z0, 3)),
                name=f'C1 {i+1}/{r} {tag}',
                qty=dict(height=round(z1 - z0, 3), concrete=round(w * d * (z1 - z0), 4)))


# ---------- คานชั้น 2–5 และคานหลังคา ----------
def beams_level(lv, top, task, floor, with_b5=True, assumed=False):
    sfx = f'L{lv}'
    for r in COL_ROWS:                  # B2 แนวยาว
        for i in range(9):
            c = top - 0.25
            L = 3.5 - COL_SEC[floor - 1][0]
            hw = COL_SEC[floor - 1][0] / 2
            add(f'B2-{r}{i+1}-{i+2}-{sfx}', 'คาน', floor, task,
                member((GX[i] + hw, GY[r], c), (GX[i + 1] - hw, GY[r], c), 0.25, 0.50),
                assumed=assumed, qty=dict(length=round(L, 3), concrete=round(L * 0.25 * 0.5, 4)))
    for i in range(10):                 # B1 แนวขวาง
        for a, b in (('B', 'C'), ('C', 'D'), ('D', 'E')):
            y0, y1 = GY[a] + 0.25, GY[b] - 0.25
            c = top - 0.25
            add(f'B1-{i+1}-{a}{b}-{sfx}', 'คาน', floor, task,
                member((GX[i], y0, c), (GX[i], y1, c), 0.25, 0.50), assumed=assumed,
                qty=dict(length=round(y1 - y0, 3), concrete=round((y1 - y0) * 0.25 * 0.5, 4)))
        for a, b in (('A', 'B'), ('E', 'F')):   # B3 ยื่น
            ya, yb = sorted((GY[a], GY[b]))
            y0 = ya + (0.10 if a == 'A' else 0.25)
            y1 = yb - (0.25 if a == 'A' else 0.10)
            c = top - 0.25
            add(f'B3-{i+1}-{a}{b}-{sfx}', 'คาน', floor, task,
                member((GX[i], y0, c), (GX[i], y1, c), 0.25, 0.50), assumed=assumed,
                qty=dict(length=round(y1 - y0, 3), concrete=round((y1 - y0) * 0.25 * 0.5, 4)))
    for r in ('A', 'F'):                # B4 ขอบ
        y = GY[r] + (0.10 if r == 'A' else -0.10)
        for i in range(9):
            c = top - 0.20
            L = 3.5 - 0.25
            add(f'B4-{r}{i+1}-{i+2}-{sfx}', 'คาน', floor, task,
                member((GX[i] + 0.125, y, c), (GX[i + 1] - 0.125, y, c), 0.20, 0.40), assumed=assumed,
                qty=dict(length=L, concrete=round(L * 0.2 * 0.4, 4)))
    if with_b5:
        for j, x in enumerate(B5_X):    # B5 ยื่นซอย
            for a, b in (('A', 'B'), ('E', 'F')):
                ya, yb = sorted((GY[a], GY[b]))
                y0, y1 = ya + 0.20, yb - 0.125
                if a == 'E':
                    y0, y1 = ya + 0.125, yb - 0.20
                c = top - 0.20
                add(f'B5-{j+1}-{a}{b}-{sfx}', 'คาน', floor, task,
                    member((x, y0, c), (x, y1, c), 0.15, 0.40), assumed=assumed,
                    qty=dict(length=round(y1 - y0, 3), concrete=round((y1 - y0) * 0.15 * 0.4, 4)))


for f in (2, 3, 4, 5):
    beams_level(f, FL[f] - SLAB_T, 'DONE', f)
# ช่วงชานพักบันได (กริด 4–5 แถบยื่นด้านหน้า) ไม่มีคานขอบ B4 และคานซอย B5 ระดับพื้น
_drop = {f'B4-A4-5-L{f}' for f in (2, 3, 4, 5)} | {f'B5-4-AB-L{f}' for f in (2, 3, 4, 5)}
elements[:] = [e for e in elements if e['id'] not in _drop]
# ไม่มีคาน คสล. หลังคา (ผู้ใช้ยกเลิก 9 พ.ย. 2569): โครงเหล็กหลังคาวางบนหัวเสาและผนังที่ +16.30

# ---------- พื้น ----------
x_min, x_max = GX[0] - 0.175, GX[-1] + 0.175
add('GS-F1', 'พื้น', 1, 'DONE', prism([(x_min, GY['B']), (x_max, GY['B']), (x_max, GY['E']), (x_min, GY['E'])],
                                       FL[1] - GS_T, GS_T),
    name='พื้นชั้น 1 (GS)', qty=dict(area=round((x_max - x_min) * (GY['E'] - GY['B']), 3)))
sx0, sx1 = GX[STAIR_BAY[0]] + 0.125, GX[STAIR_BAY[1]] - 0.125   # ผิวคาน B1 กริด 4/5
sy0, sy1 = GY['B'] + 0.125, ST_RUN_Y1                            # ช่องเปิดบันได
STRIP_Y1 = GY['B'] - 0.125                                       # แถบยื่นช่วงชานพัก (ไม่มีพื้นระดับชั้น)


def slab_pieces():
    """พื้นชั้น 2–5 เป็นสี่เหลี่ยมย่อย เว้นช่องบันไดและช่วงชานพัก"""
    return [(x_min, sx0, GY['A'], GY['F']), (sx1, x_max, GY['A'], GY['F']),
            (sx0, sx1, STRIP_Y1, sy0), (sx0, sx1, sy1, GY['F'])]


def pieces_geom(z0, t):
    return dict(type='multi', parts=[prism([(a, c), (b, c), (b, d), (a, d)], z0, t) for a, b, c, d in slab_pieces()])


SLAB_AREA = round(sum((b - a) * (d - c) for a, b, c, d in slab_pieces()), 3)
for f in (2, 3, 4, 5):
    add(f'PS-F{f}', 'พื้นสำเร็จรูป', f, 'DONE', pieces_geom(FL[f] - SLAB_T, 0.05),
        name=f'แผ่นพื้นสำเร็จรูปชั้น {f} หนา 0.05 (PS)', qty=dict(area=SLAB_AREA))
    add(f'TP-F{f}', 'พื้นทับหน้า', f, 'DONE', pieces_geom(FL[f] - 0.05, 0.05),
        name=f'คอนกรีตทับหน้า (Topping) ชั้น {f} หนา 0.05', qty=dict(area=SLAB_AREA, concrete=round(SLAB_AREA * 0.05, 3)))

# ---------- บันไดหลัก (A-05) ----------
ST_T = 0.12
RISER, TREAD, NSTEP = 0.16, 0.30, 9
FX0, FX1 = GX[3] + 0.05, GX[3] + 0.05 + 1.50       # ช่วงที่ 1 (ฝั่งกริด 4) ขึ้นไปทางด้านหน้า
GX0, GX1 = FX1 + 0.40, FX1 + 0.40 + 1.50           # ช่วงที่ 2 (ฝั่งกริด 5) กลับเข้าด้านใน
LY0, LY1 = GY['A'] + 0.15, GY['B']                 # ชานพัก
ASSUMPTIONS.append('บันไดหลักชั้น 4→5 ใช้รูปแบบเดียวกับชั้น 1→2 (A-05 แสดงชั้น 1–2)')


def flight(x0, x1, y_start, direction, z_start):
    """ช่วงบันได: ขั้นบันได (prism) + ท้องบันได (plate)"""
    parts = []
    for k in range(NSTEP):
        ya = y_start + direction * k * TREAD
        yb = ya + direction * TREAD
        top = z_start + (k + 1) * RISER
        parts.append(prism([(x0, min(ya, yb)), (x1, min(ya, yb)), (x1, max(ya, yb)), (x0, max(ya, yb))], top - RISER, RISER))
    y_end = y_start + direction * NSTEP * TREAD
    z_end = z_start + (NSTEP + 1) * RISER
    parts.append(plate([(x0, y_start, z_start), (x1, y_start, z_start), (x1, y_end, z_end - RISER), (x0, y_end, z_end - RISER)], ST_T))
    run_len = math.hypot(NSTEP * TREAD, NSTEP * RISER)
    conc = (x1 - x0) * (run_len * ST_T + NSTEP * 0.5 * TREAD * RISER)
    return dict(type='multi', parts=parts), round(conc, 3)


for f in (1, 2, 3, 4):
    z0 = FL[f]
    zm = z0 + 10 * RISER
    g, c = flight(FX0, FX1, ST_RUN_Y1, -1, z0)
    add(f'ST-F{f}-1', 'บันได', f, 'DONE', g, name=f'บันไดหลักชั้น {f}→{f+1} ช่วง 1 (ลูกตั้ง 1–10)',
        qty=dict(width=1.50, risers=10, treads=NSTEP, concrete=c))
    add(f'ST-F{f}-L', 'บันได', f, 'DONE', prism([(FX0, LY0), (GX1, LY0), (GX1, LY1), (FX0, LY1)], zm - ST_T, ST_T),
        name=f'ชานพักบันไดชั้น {f} (S2) ระดับ +{zm:.2f}', assumed=True,
        qty=dict(area=round((GX1 - FX0) * (LY1 - LY0), 3), concrete=round((GX1 - FX0) * (LY1 - LY0) * ST_T, 3)))
    g, c = flight(GX0, GX1, LY1, +1, zm)
    add(f'ST-F{f}-2', 'บันได', f, 'DONE', g, name=f'บันไดหลักชั้น {f}→{f+1} ช่วง 2 (ลูกตั้ง 11–20)',
        qty=dict(width=1.50, risers=10, treads=NSTEP, concrete=c))
    # คานชานพัก BST3 (ขอบนอก) และ BST2 (กริด 4, 5) ระดับชานพัก
    zc = zm - 0.20
    add(f'BST3-M{f}', 'คาน', f, 'DONE', member((GX[3] + 0.125, GY['A'] + 0.10, zc), (GX[4] - 0.125, GY['A'] + 0.10, zc), 0.20, 0.40),
        name=f'BST3 คานชานพักชั้น {f}', qty=dict(length=3.25, concrete=round(3.25 * 0.2 * 0.4, 4)))
    for k in (3, 4):
        add(f'BST2-{k+1}-M{f}', 'คาน', f, 'DONE', member((GX[k], GY['A'] + 0.20, zc), (GX[k], GY['B'] - 0.25, zc), 0.20, 0.40),
            name=f'BST2 คานชานพักกริด {k+1} ชั้น {f}', qty=dict(length=1.20, concrete=round(1.2 * 0.2 * 0.4, 4)))
for f in (2, 3, 4, 5):                             # BST1 ขอบช่องเปิดบันไดระดับพื้น
    c = FL[f] - SLAB_T - 0.20
    add(f'BST1-L{f}', 'คาน', f, 'DONE', member((sx0, ST_RUN_Y1 + 0.10, c), (sx1, ST_RUN_Y1 + 0.10, c), 0.20, 0.40),
        name=f'BST1 คานขอบช่องบันไดชั้น {f}', qty=dict(length=round(sx1 - sx0, 3), concrete=round((sx1 - sx0) * 0.08, 4)))

# ---------- หลังคา (S106 ผังโครงหลังคา, S107 รูปตัดด้านสั้น) ----------
# หน้าตัดเหล็ก (มอก. เหล็กรูปพรรณขึ้นรูปเย็น) h, b, c, t (ม.) และน้ำหนัก กก./ม. ต่อตัว
STEEL = {'C125': dict(h=0.125, b=0.05, c=0.02, t=0.0032, kg=6.13),
         'C100': dict(h=0.100, b=0.05, c=0.02, t=0.0032, kg=5.50)}
# ชั้นวัสดุใต้ผิวหลังคา (วัดจากผิวบนหลังคา zroof ลงมา)
SKIN_T, PURLIN_T = 0.03, 0.04            # แผ่นหลังคา, แปสำเร็จรูป (ไม่ได้ขึ้นแป)
RAF_TOP = SKIN_T + PURLIN_T              # หลังจันทัน
RAF_C = RAF_TOP + 0.05                   # แกนจันทัน C100
RAF_BOT = RAF_TOP + 0.10                 # ท้องจันทัน = หลังสะพานรับจันทัน / หลังตะเข้สัน
WP_Y = 0.10                              # แนวอะเสจากขอบคาน
OV_SIDE, OV_END = 1.195, 1.33
yc = GY['CX']
# ระนาบหลังคา: ท้องจันทันวางบนอะเส (หลังอะเส = +16.30 + 0.125) และผิวบนที่สันหลังคา = +20.00
slope = (RIDGE - (ROOF_BEAM + 0.125 + RAF_BOT)) / (yc - (GY['A'] + WP_Y))   # tan ≈ 24°
half = yc - GY['A']
run = half + OV_SIDE
z_eave = RIDGE - run * slope
ex0, ex1 = GX[0] - OV_END, GX[-1] + OV_END
ey0, ey1 = GY['A'] - OV_SIDE, GY['F'] + OV_SIDE
rx0, rx1 = ex0 + run, ex1 - run               # ปลายสันหลังคา (ตะเข้สัน 45° ในแปลน)


def zroof(x, y):
    dy = abs(y - yc)
    dx = max(rx0 - x, x - rx1, 0)
    return RIDGE - max(dy, dx) * slope


def steel(eid, p0, p1, sec, double, name, mark):
    """ชิ้นส่วนเหล็กรูปตัวซี: double=True คือ 2C ประกบปากชนกันเป็นกล่อง"""
    sp = STEEL[sec]
    g = member(p0, p1, 2 * sp['b'] if double else sp['b'], sp['h'])
    g['shape'] = '2C' if double else 'C'
    g['sec'] = {k: sp[k] for k in ('h', 'b', 'c', 't')}
    L = mlen(p0, p1)
    secname = f"{'2' if double else ''}{sec}x50x20x3.2"
    add(eid, 'โครงหลังคาเหล็ก', 5, 'A03.2', g, name=f'{mark} {name} {secname}',
        qty=dict(length=round(L, 3), section=secname, mark=mark,
                 weight_kg=round(L * sp['kg'] * (2 if double else 1), 2)))


ZB = ROOF_BEAM + 0.0625                       # แกนขื่อ/อะเส 2C125 วางบนหัวเสา/ผนัง +16.30
ZB_TOP = ROOF_BEAM + 0.125
ZA = ROOF_BEAM + 0.05                         # แกนขื่อทางยาว 2C100
Y_MID_N, Y_MID_S = GY['B'] + 2.55, GY['E'] - 2.55       # เสารับจันทันกลางช่วง (S107)
Y_HIP_N = yc - (rx0 - GX[1])                  # แนวสะพานช่วงตะเข้ (ตรงกับระยะ 550 ใน S106)
Y_HIP_S = yc + (rx0 - GX[1])
X_E0, X_E1 = GX[1], GX[8]                     # สะพานรับจันทันพรางด้านสกัด กริด 2 และ 9


def z_bridge(x, y):
    return zroof(x, y) - RAF_BOT - 0.0625     # แกนสะพาน 2C125 ใต้ท้องจันทัน


def bridge_bot(x, y):
    return zroof(x, y) - RAF_BOT - 0.125


# B อะเส รอบอาคาร
for k, (q0, q1) in enumerate((((GX[0], GY['A'] + WP_Y), (GX[-1], GY['A'] + WP_Y)),
                               ((GX[0], GY['F'] - WP_Y), (GX[-1], GY['F'] - WP_Y)),
                               ((GX[0] + WP_Y, GY['A'] + WP_Y), (GX[0] + WP_Y, GY['F'] - WP_Y)),
                               ((GX[-1] - WP_Y, GY['A'] + WP_Y), (GX[-1] - WP_Y, GY['F'] - WP_Y)))):
    steel(f'RF-WP{k+1}', (*q0, ZB), (*q1, ZB), 'C125', True, 'อะเส', 'B')
# B ขื่อด้านสั้น ทุกกริด 2–9 (วางบนคานหลังคาแนว y)
for gi in range(1, 9):
    x = GX[gi]
    steel(f'RF-TS{gi+1}', (x, GY['A'] + WP_Y, ZB), (x, GY['F'] - WP_Y, ZB), 'C125', True, f'ขื่อด้านสั้น กริด {gi+1}', 'B')
# A ขื่อทางยาว แนว B C D E
for r in COL_ROWS:
    steel(f'RF-TL-{r}', (GX[0] + WP_Y, GY[r], ZA), (GX[-1] - WP_Y, GY[r], ZA), 'C100', True, f'ขื่อทางยาว แนว {r}', 'A')

# C สะพานรับจันทัน (แนว x) ใต้จันทันด้านยาว
bridges = []                                  # (eid, y, x0, x1)
for r in ('B', 'C', 'D', 'E'):
    dy = abs(GY[r] - yc)
    bridges.append((f'RF-BR-{r}', GY[r], rx0 - dy, rx1 + dy))
bridges += [('RF-BR-MN', Y_MID_N, GX[2], GX[7]), ('RF-BR-MS', Y_MID_S, GX[2], GX[7]),
            ('RF-BR-HN1', Y_HIP_N, X_E0, GX[2]), ('RF-BR-HN2', Y_HIP_N, GX[7], X_E1),
            ('RF-BR-HS1', Y_HIP_S, X_E0, GX[2]), ('RF-BR-HS2', Y_HIP_S, GX[7], X_E1)]
for eid, y, x0, x1 in bridges:
    z = z_bridge((x0 + x1) / 2, y)
    steel(eid, (x0, y, z), (x1, y, z), 'C125', True, f'สะพานรับจันทัน y={y:.2f}', 'C')
# C สะพานรับจันทันพรางด้านสกัด (แนว y) กริด 2 และ 9
for k, x in enumerate((X_E0, X_E1)):
    z = z_bridge(x, yc)
    steel(f'RF-BR-END{k+1}', (x, Y_HIP_N, z), (x, Y_HIP_S, z), 'C125', True, f'สะพานรับจันทันพราง กริด {2 if k == 0 else 9}', 'C')

# D เสารับจันทัน 2C100 บนขื่อด้านสั้น
posts = []                                    # (x, y)
for gi in range(2, 8):
    for y in (GY['B'], Y_MID_N, GY['C'], GY['D'], Y_MID_S, GY['E']):
        posts.append((GX[gi], y))
for x in (X_E0, X_E1):
    for y in (GY['B'], Y_HIP_N, GY['C'], GY['D'], Y_HIP_S, GY['E']):
        posts.append((x, y))
for x in (GX[2], GX[7]):                      # ปลายสะพานช่วงตะเข้
    for y in (Y_HIP_N, Y_HIP_S):
        posts.append((x, y))
for n, (x, y) in enumerate(posts, 1):
    zt = bridge_bot(x, y)
    steel(f'RF-P{n:02d}', (x, y, ZB_TOP), (x, y, zt), 'C100', True, 'เสารับจันทัน', 'D')

# I เหล็กทะแยง C100 (S107): หัวเสาแนว B → โคนเสากลาง, หัวเสากลาง → โคนเสาแนว C (และฝั่ง E/D)
n = 0
for gi in range(2, 8):
    x = GX[gi]
    for ya, yb in ((GY['B'], Y_MID_N), (Y_MID_N, GY['C']), (GY['E'], Y_MID_S), (Y_MID_S, GY['D'])):
        n += 1
        steel(f'RF-DG{n:02d}', (x, ya, bridge_bot(x, ya) - 0.05), (x, yb, ZB_TOP + 0.05), 'C100', False, 'เหล็กทะแยง', 'I')

# E คานรับเสาดั้ง + F เสารับอกไก่ + G อกไก่
Z_E = ROOF_BEAM + 2.44
xs_king = [rx0] + [GX[i] for i in range(3, 7)] + [rx1]
for k, x in enumerate(xs_king, 1):
    steel(f'RF-KB{k}', (x, GY['C'], Z_E), (x, GY['D'], Z_E), 'C125', True, 'คานรับเสาดั้ง', 'E')
    steel(f'RF-KP{k}', (x, yc, Z_E + 0.0625), (x, yc, bridge_bot(x, yc)), 'C100', True, 'เสารับอกไก่', 'F')
    if x in (rx0, rx1):                       # เสารับคานรับเสาดั้งที่ปลายสัน ยืนบนขื่อทางยาว C/D
        for r in ('C', 'D'):
            steel(f'RF-KC{k}{r}', (x, GY[r], ZA + 0.05), (x, GY[r], Z_E - 0.0625), 'C100', True, 'เสารับคานรับเสาดั้ง', 'D')
zr = z_bridge(rx0, yc)
steel('RF-RIDGE', (rx0, yc, zr), (rx1, yc, zr), 'C125', True, 'อกไก่', 'G')

# C ตะเข้สัน: หลังตะเข้เสมอหลังจันทัน
for k, (cx, cy) in enumerate(((ex0, ey0), (ex1, ey0), (ex1, ey1), (ex0, ey1))):
    rx = rx0 if cx == ex0 else rx1
    q0 = (cx, cy, z_eave - RAF_TOP - 0.0625)
    q1 = (rx, yc, RIDGE - RAF_TOP - 0.0625)
    steel(f'RF-HIP{k+1}', q0, q1, 'C125', True, 'ตะเข้สัน', 'C')

# H จันทัน C100 @0.875 ด้านยาว (แนว y) และจันทันพรางด้านสกัด (แนว x)
xs = []
x = ex0 + 0.477
while x < ex1 - 0.2:
    xs.append(round(x, 3)); x += 0.875
n = 0
for x in xs:
    for side in (0, 1):
        y_e = ey0 if side == 0 else ey1
        if rx0 <= x <= rx1:
            y_t = yc
        else:
            d = (rx0 - x) if x < rx0 else (x - rx1)
            y_t = yc - d if side == 0 else yc + d
            if (side == 0 and y_t <= y_e) or (side == 1 and y_t >= y_e):
                continue
        n += 1
        steel(f'RF-RAF{n:03d}', (x, y_e, zroof(x, y_e) - RAF_C), (x, y_t, zroof(x, y_t) - RAF_C), 'C100', False, 'จันทัน', 'H')
ys = []
y = ey0 + 0.477
while y < ey1 - 0.2:
    ys.append(round(y, 3)); y += 0.875
for y in ys:
    for side in (0, 1):
        x_e = ex0 if side == 0 else ex1
        d = abs(y - yc)
        x_t = rx0 - d if side == 0 else rx1 + d
        if (side == 0 and x_t <= x_e + 0.05) or (side == 1 and x_t >= x_e - 0.05):
            continue
        n += 1
        steel(f'RF-RAF{n:03d}', (x_e, y, zroof(x_e, y) - RAF_C), (x_t, y, zroof(x_t, y) - RAF_C), 'C100', False, 'จันทันพราง', 'H')

# ผิวหลังคา + เชิงชาย (A03.3)
E = lambda x, y: (x, y, z_eave)
R0, R1 = (rx0, yc, RIDGE), (rx1, yc, RIDGE)
faces = {
    'RF-SKIN-A': [E(ex0, ey0), E(ex1, ey0), R1, R0],
    'RF-SKIN-F': [E(ex1, ey1), E(ex0, ey1), R0, R1],
    'RF-SKIN-1': [E(ex0, ey1), E(ex0, ey0), R0],
    'RF-SKIN-10': [E(ex1, ey0), E(ex1, ey1), R1],
}


def tri_area(p):
    import itertools
    a = 0
    for i in range(1, len(p) - 1):
        u = [p[i][k] - p[0][k] for k in range(3)]
        v = [p[i + 1][k] - p[0][k] for k in range(3)]
        c = [u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0]]
        a += math.sqrt(sum(t * t for t in c)) / 2
    return a


for k, pts in faces.items():
    add(k, 'หลังคา', 5, 'A03.3', plate(pts, 0.03), name='ผิวหลังคา', assumed=True,
        qty=dict(area=round(tri_area(pts), 3)))
for k, (p0, p1) in enumerate((((ex0, ey0), (ex1, ey0)), ((ex1, ey0), (ex1, ey1)),
                               ((ex1, ey1), (ex0, ey1)), ((ex0, ey1), (ex0, ey0)))):
    add(f'RF-FASCIA{k+1}', 'หลังคา', 5, 'A03.3', member((*p0, z_eave - 0.10), (*p1, z_eave - 0.10), 0.025, 0.20),
        name='เชิงชาย', assumed=True, qty=dict(length=round(math.dist(p0, p1), 3)))


# =====================================================================
# งานสถาปัตย์ (แปลน A-01 ชั้น 1, A-02 ชั้น 2–5, แปลนห้องน้ำชั้น 1)
# กริดสถาปัตย์ A,B,C,D = กริดโครงสร้าง B,C,D,E
# =====================================================================
WALL_T = 0.07            # บล็อก 3 รู 7x10x20 ซม. (ผู้ใช้กำหนด 9 พ.ย. 2569)
BLOCK_PER_M2 = round(1 / (0.20 + 0.01) / (0.10 + 0.01), 1)   # ก้อน/ตร.ม. รวมรอยต่อ 1 ซม.
PL_T = 0.015             # ฉาบแต่ละด้าน
ASSUMPTIONS += [
    'กริดสถาปัตย์ A,B,C,D ในแปลน A-01/A-02 ตรงกับกริดโครงสร้าง B,C,D,E',
    'เสาเอ็น/คานเอ็น คสล. กว้าง 0.10 ม. หนาเท่าบล็อก 0.07 ม.: เสาเอ็นข้างวงกบประตูหน้าต่างทุกช่อง, เสาเอ็นกลางผนังทึบที่ยาวเกิน 3.50 ม., คานเอ็นกลางความสูงผนังทุกผนัง, คานทับหลังและคานใต้วงกบยื่นเลยขอบช่องเปิดข้างละ 0.20 ม.',
    'ผนังบล็อก 3 รู 7x10x20 ซม. (หนา 0.07 ม.) ฉาบในและนอกด้านละ 0.015 ม. (ผู้ใช้กำหนด) จำนวนก้อนคิดรอยต่อ 1 ซม. สูงจากพื้นถึงท้องคาน (คานลึก 0.50 หรือ 0.40)',
    'ขนาดประตู–หน้าต่างไม่มีตาราง: ประตูห้อง 0.90x2.00, ประตูระเบียง 0.80x2.00, ประตูห้องน้ำ 0.70x2.00, ช่องระแนงระเบียง 1.20x1.20 สูงจากพื้น 0.90, ช่องลมห้องน้ำ 0.40x0.40 สูงจากพื้น 1.80, ช่องหน้าร้าน 2.80x2.60',
    'ฉาบเสาหนา 1 ซม. และท้องคาน/ข้างคานหนา 0.5 ซม. (ผู้ใช้กำหนด) ผูกกับงานฉาบของชั้นนั้น: ชั้น 1 = A12, ชั้น 2–3 = A09, ชั้น 4 = A10, ชั้น 5 (รวมคานหลังคา) = A11; ข้างคานคิดเต็มความลึกคาน',
    'ฉาบผนังห้องโถงบันไดชั้น 1 ผูกกับ A12; ฉาบใต้ท้องพื้น A12 = ใต้พื้นชั้น 2, A15 = ใต้พื้นชั้น 3–5 (เพดานชั้น 2–4)',
    'กระเบื้องพื้น A16/A17 แทนด้วยแผ่นหนา 0.02 ม. เต็มพื้นที่ใช้งานแต่ละชั้น (ห้อง ห้องน้ำ ระเบียง ทางเดิน)',
    'สุขภัณฑ์ A21 แทนด้วยกล่องโถส้วมและอ่างล้างหน้า ห้องน้ำละ 1 ชุด',
    'ยังไม่มีชิ้นส่วนของ A07/A08 (ระบบท่อ), A19/A20 (สี ฝ้า), A22/A23 เพราะไม่มีแบบระบบและเป็นงานผิว/งานทดสอบ',
    'ไม่ได้ขึ้นบันไดเหล็กภายนอกด้านกริด 10 (ไม่มีในแผน R3)',
]


def beam_soffit(f, kind):
    """ระดับท้องคานเหนือผนังของชั้น f; kind 'main' (คานลึก 0.50) / 'edge' (0.40)"""
    if f == 5:                      # ไม่มีคานหลังคา: ผนังชั้น 5 ก่อถึงใต้โครงเหล็กหลังคา +16.30
        return ROOF_BEAM
    top = FL[f + 1] - SLAB_T
    return top - (0.50 if kind == 'main' else 0.40)


def wall_pieces(a0, a1, z0, z1, openings):
    """แบ่งผนังรอบช่องเปิด openings: [(center, width, sill, height)] -> [(a0,a1,z0,z1)]"""
    pieces, cur = [], a0
    for c, w, sill, h in sorted(openings):
        o0, o1 = c - w / 2, c + w / 2
        if o0 > cur:
            pieces.append((cur, o0, z0, z1))
        if sill > 0:
            pieces.append((o0, o1, z0, z0 + sill))
        if z0 + sill + h < z1:
            pieces.append((o0, o1, z0 + sill + h, z1))
        cur = o1
    if cur < a1:
        pieces.append((cur, a1, z0, z1))
    return pieces


def rect_prism(axis, fixed, a0, a1, z0, z1, off, t):
    if axis == 'x':      # ผนังแนวแกน x ที่ y = fixed
        poly = [(a0, fixed + off - t / 2), (a1, fixed + off - t / 2), (a1, fixed + off + t / 2), (a0, fixed + off + t / 2)]
    else:                # ผนังแนวแกน y ที่ x = fixed
        poly = [(fixed + off - t / 2, a0), (fixed + off + t / 2, a0), (fixed + off + t / 2, a1), (fixed + off - t / 2, a1)]
    return prism(poly, z0, round(z1 - z0, 4))


TIE = 0.10               # เสาเอ็น/คานเอ็น กว้าง 0.10 x หนาเท่าผนัง
TIE_MAX = 3.50           # ผนังทึบยาวเกินนี้ใส่เสาเอ็นกลางผนัง
LINTEL_EXT = 0.20        # ทับหลัง/คานใต้วงกบยื่นเลยขอบช่องเปิดข้างละ


def tie_layout(a0, a1, z0, z1, openings):
    """คืน posts [(p0,p1)], beams [(x0,x1,zb0,zb1,kind)] ตามหลักผนังก่อ:
    เสาเอ็นข้างวงกบทุกช่อง, เสาเอ็นกลางช่วงผนังทึบที่ยาวเกิน 3.50 ม., คานเอ็นกลางความสูงผนัง,
    คานทับหลังเหนือช่องเปิด และคานใต้วงกบหน้าต่าง ยื่นเลยขอบข้างละ 0.20 ม."""
    posts = []
    for c, w, sill, h in openings:
        posts += [(c - w / 2 - TIE, c - w / 2), (c + w / 2, c + w / 2 + TIE)]
    # ช่วงผนังทึบระหว่างปลายผนัง/เสาเอ็น
    edges = sorted([(a0, a0)] + posts + [(a1, a1)])
    for (_, e0), (s1, _) in zip(edges, edges[1:]):
        L = s1 - e0
        if L > TIE_MAX:
            n = int(L // TIE_MAX)
            for k in range(1, n + 1):
                m = e0 + L * k / (n + 1)
                posts.append((m - TIE / 2, m + TIE / 2))
    posts = sorted((max(a0, p0), min(a1, p1)) for p0, p1 in posts)
    beams = []
    zm = z0 + (z1 - z0) / 2
    beams.append((a0, a1, zm - TIE / 2, zm + TIE / 2, 'คานเอ็นกลางผนัง'))
    for c, w, sill, h in openings:
        x0, x1 = max(a0, c - w / 2 - LINTEL_EXT), min(a1, c + w / 2 + LINTEL_EXT)
        zt = z0 + sill + h
        if zt + TIE <= z1 + 1e-6:
            beams.append((x0, x1, zt, zt + TIE, 'คานทับหลัง'))
        if sill > 0:
            beams.append((x0, x1, z0 + sill - TIE, z0 + sill, 'คานใต้วงกบ'))
    return posts, beams


def wall_cells(a0, a1, z0, z1, openings, posts, beams):
    xs = sorted({a0, a1} | {v for c, w, s, h in openings for v in (c - w / 2, c + w / 2)} |
                {v for p in posts for v in p} | {v for b in beams for v in b[:2]})
    zs = sorted({z0, z1} | {z0 + s for c, w, s, h in openings} | {z0 + s + h for c, w, s, h in openings} |
                {v for b in beams for v in b[2:4]})
    xs = [x for x in xs if a0 - 1e-9 <= x <= a1 + 1e-9]
    zs = [z for z in zs if z0 - 1e-9 <= z <= z1 + 1e-9]
    cells = {'mas': [], 'beam': {}}
    for xa, xb in zip(xs, xs[1:]):
        if xb - xa < 1e-4:
            continue
        xm = (xa + xb) / 2
        if any(p0 <= xm <= p1 for p0, p1 in posts):
            continue
        run = None
        for za, zb in zip(zs, zs[1:]):
            if zb - za < 1e-4:
                continue
            zm = (za + zb) / 2
            if any(abs(xm - c) < w / 2 and z0 + s < zm < z0 + s + h for c, w, s, h in openings):
                kind = None
            else:
                kind = next((k for k, b in enumerate(beams) if b[0] <= xm <= b[1] and b[2] <= zm <= b[3]), 'm')
            if kind == 'm':
                run = (xa, xb, run[2], zb) if run else (xa, xb, za, zb)
                continue
            if run:
                cells['mas'].append(run); run = None
            if kind is not None:
                cells['beam'].setdefault(kind, []).append((xa, xb, za, zb))
        if run:
            cells['mas'].append(run)
    return cells


def add_wall(eid, floor, axis, fixed, a0, a1, z0, z1, task_wall, task_plaster, openings=(), name=None):
    if a1 - a0 < 0.05:
        return
    openings = list(openings)
    pcs = wall_pieces(a0, a1, z0, z1, openings)
    posts, beams = tie_layout(a0, a1, z0, z1, openings)
    cells = wall_cells(a0, a1, z0, z1, openings, posts, beams)
    area = sum((b - a) * (d - c) for a, b, c, d in cells['mas'])
    add(eid, 'ผนัง', floor, task_wall,
        dict(type='multi', parts=[rect_prism(axis, fixed, a, b, c, d, 0, WALL_T) for a, b, c, d in cells['mas']]),
        name=name or f'ผนังก่อ {eid}', assumed=True,
        qty=dict(area=round(area, 3), length=round(a1 - a0, 3), blocks=round(area * BLOCK_PER_M2), material='บล็อก 3 รู 7x10x20'))
    for k, (p0, p1) in enumerate(posts):
        h = z1 - z0
        add(f'{eid}-TC{k+1}', 'เสาเอ็นคานเอ็น', floor, task_wall, rect_prism(axis, fixed, p0, p1, z0, z1, 0, WALL_T),
            name=f'เสาเอ็น {eid}', assumed=True,
            qty=dict(height=round(h, 3), concrete=round((p1 - p0) * WALL_T * h, 4), section='0.10x0.07'))
    for k, b in enumerate(beams):
        parts = cells['beam'].get(k, [])
        if not parts:
            continue
        L = sum(x1 - x0 for x0, x1, _, _ in parts)
        add(f'{eid}-TB{k+1}', 'เสาเอ็นคานเอ็น', floor, task_wall,
            dict(type='multi', parts=[rect_prism(axis, fixed, x0, x1, za, zb, 0, WALL_T) for x0, x1, za, zb in parts]),
            name=f'{b[4]} {eid}', assumed=True,
            qty=dict(length=round(L, 3), concrete=round(L * TIE * WALL_T, 4), section='0.10x0.07', kind=b[4]))
    if task_plaster:
        parts = []
        for side in (-1, 1):
            off = side * (WALL_T / 2 + PL_T / 2)
            parts += [rect_prism(axis, fixed, a, b, c, d, off, PL_T) for a, b, c, d in pcs]
        add(eid + '-PL', 'งานฉาบ', floor, task_plaster, dict(type='multi', parts=parts),
            name=f'ฉาบ {eid}', assumed=True, qty=dict(area=round(2 * sum((b - a) * (d - c) for a, b, c, d in pcs), 3)))
    for k, (c, w, sill, h) in enumerate(openings):
        kind = 'ประตู' if sill == 0 else 'หน้าต่าง/ช่องเปิด'
        add(f'{eid}-O{k+1}', 'ประตูหน้าต่าง', floor, 'A18',
            rect_prism(axis, fixed, c - w / 2, c + w / 2, z0 + sill, z0 + sill + h, 0, 0.04),
            name=f'{kind} {w:.2f}x{h:.2f} ใน {eid}', assumed=True, qty=dict(width=w, height=h, area=round(w * h, 3)))


def col_d(f):
    return COL_SEC[f][1] / 2


def col_w(f):
    return COL_SEC[f][0] / 2


def bay_split(i):
    """คืน (toilet_x0, toilet_x1, balcony_x0, balcony_x1) ของช่วงเสา i"""
    b5 = B5_X[i]
    if abs(b5 - GX[i] - 1.5) < 1e-6:
        return b5, GX[i + 1], GX[i], b5
    return GX[i], b5, b5, GX[i + 1]


plaster_task = {1: None, 2: 'A09', 3: 'A09', 4: 'A10', 5: 'A11'}
wall_task = {1: 'A04', 2: 'A04', 3: 'A04', 4: 'A05', 5: 'A06'}
yB, yC, yD, yE, yF = GY['B'], GY['C'], GY['D'], GY['E'], GY['F']

for f in (2, 3, 4, 5):
    z0 = FL[f]
    tw, tp = wall_task[f], plaster_task[f]
    cd, cw = col_d(f), col_w(f)
    for side in ('N', 'S'):           # N = ฝั่งกริด A–C (ด้านหน้า), S = ฝั่งกริด D–F
        if side == 'N':
            y_out, y_rm, y_cor = 0.0, yB, yC
        else:
            y_out, y_rm, y_cor = yF, yE, yD
        lo = lambda a, b: (min(a, b), max(a, b))
        for i in range(9):
            stair = side == 'N' and i == STAIR_BAY[0]
            x0, x1 = GX[i] + cw, GX[i + 1] - cw
            tx0, tx1, bx0, bx1 = bay_split(i)
            tag = f'F{f}-{side}{i+1}'
            # ผนังทางเดิน (ประตูห้อง)
            if not stair:
                add_wall(f'W-{tag}-COR', f, 'x', y_cor, x0, x1, z0, beam_soffit(f, 'main'), tw, tp,
                         [(GX[i] + 0.75, 0.90, 0.0, 2.00)], name=f'ผนังทางเดิน ชั้น {f} ห้อง {side}{i+1}')
                # ผนังห้อง–ระเบียง (ประตูระเบียง)
                add_wall(f'W-{tag}-BAL', f, 'x', y_rm, x0, x1, z0, beam_soffit(f, 'main'), tw, tp,
                         [((bx0 + bx1) / 2, 0.80, 0.0, 2.00)], name=f'ผนังห้องด้านระเบียง ชั้น {f} ห้อง {side}{i+1}')
                # ผนังข้างห้องน้ำ (แนว B5) ประตูห้องน้ำ
                ya, yb = lo(y_out, y_rm)
                add_wall(f'W-{tag}-WC', f, 'y', B5_X[i], ya + 0.10, yb - 0.125, z0, beam_soffit(f, 'edge'), tw, tp,
                         [((ya + yb) / 2, 0.70, 0.0, 2.00)], name=f'ผนังห้องน้ำ ชั้น {f} ห้อง {side}{i+1}')
                # ผนังนอกห้องน้ำ (ช่องลม) และผนังนอกระเบียง (ช่องระแนง)
                add_wall(f'W-{tag}-OWC', f, 'x', y_out + (0.10 if side == 'N' else -0.10),
                         tx0 + (WALL_T / 2), tx1 - (WALL_T / 2), z0, beam_soffit(f, 'edge'), tw, tp,
                         [((tx0 + tx1) / 2, 0.40, 1.80, 0.40)], name=f'ผนังนอกห้องน้ำ ชั้น {f} ห้อง {side}{i+1}')
                add_wall(f'W-{tag}-OBL', f, 'x', y_out + (0.10 if side == 'N' else -0.10),
                         bx0 + (WALL_T / 2), bx1 - (WALL_T / 2), z0, beam_soffit(f, 'edge'), tw, tp,
                         [((bx0 + bx1) / 2, 1.20, 0.90, 1.20)], name=f'ผนังนอกระเบียง ชั้น {f} ห้อง {side}{i+1}')
                # สุขภัณฑ์
                wy = (y_out + y_rm) / 2
                add(f'FX-{tag}-WC', 'สุขภัณฑ์', f, 'A21',
                    prism([((tx0 + tx1) / 2 - 0.2, wy - 0.35), ((tx0 + tx1) / 2 + 0.2, wy - 0.35),
                           ((tx0 + tx1) / 2 + 0.2, wy + 0.35), ((tx0 + tx1) / 2 - 0.2, wy + 0.35)], z0, 0.40),
                    name=f'โถส้วม ชั้น {f} ห้อง {side}{i+1}', assumed=True, qty=dict(count=1))
                bxs = tx0 + 0.35 if tx0 < bx0 else tx1 - 0.35
                add(f'FX-{tag}-LAV', 'สุขภัณฑ์', f, 'A21',
                    prism([(bxs - 0.25, wy - 0.20), (bxs + 0.25, wy - 0.20), (bxs + 0.25, wy + 0.20), (bxs - 0.25, wy + 0.20)],
                          z0 + 0.65, 0.20), name=f'อ่างล้างหน้า ชั้น {f} ห้อง {side}{i+1}', assumed=True, qty=dict(count=1))
            else:
                # โถงบันได: ผนังนอกแนว A มีหน้าต่าง
                add_wall(f'W-{tag}-OST', f, 'x', y_out + 0.10, GX[i] + cw, GX[i + 1] - cw, z0, beam_soffit(f, 'edge'), tw, tp,
                         [((GX[i] + GX[i + 1]) / 2, 1.00, 1.00, 1.20)], name=f'ผนังโถงบันได ชั้น {f}')
        # ผนังกั้นห้องตามกริด 1–10 (ช่วงห้อง + ช่วงระเบียง)
        for k in range(10):
            ya, yb = lo(y_rm, y_cor)
            add_wall(f'W-F{f}-{side}G{k+1}-RM', f, 'y', GX[k], ya + cd, yb - cd, z0, beam_soffit(f, 'main'), tw, tp,
                     name=f'ผนังกั้นห้องกริด {k+1} ชั้น {f} ฝั่ง {side}')
            ya, yb = lo(y_out, y_rm)
            add_wall(f'W-F{f}-{side}G{k+1}-BL', f, 'y', GX[k], ya + 0.10, yb - cd, z0, beam_soffit(f, 'main'), tw, tp,
                     name=f'ผนังกั้นระเบียงกริด {k+1} ชั้น {f} ฝั่ง {side}')

# ---------- ชั้น 1 ----------
z0 = FL[1]
cd, cw = col_d(1), col_w(1)
# โถงบันได (กริด 4–5) จากขอบนอกถึงแนว C
for k in (3, 4):
    add_wall(f'W-F1-ST-G{k+1}A', 1, 'y', GX[k], 0.10, yB - cd, z0, beam_soffit(1, 'main'), 'A04', 'A12', name=f'ผนังโถงบันไดชั้น 1 กริด {k+1} ช่วงยื่น')
    add_wall(f'W-F1-ST-G{k+1}B', 1, 'y', GX[k], yB + cd, yC - cd, z0, beam_soffit(1, 'main'), 'A04', 'A12', name=f'ผนังโถงบันไดชั้น 1 กริด {k+1}')
add_wall('W-F1-ST-OUT', 1, 'x', 0.10, GX[3] + cw, GX[4] - cw, z0, beam_soffit(1, 'edge'), 'A04', 'A12',
         [((GX[3] + GX[4]) / 2, 1.00, 1.00, 1.20)], name='ผนังนอกโถงบันไดชั้น 1')
# ร้านค้า 3 ห้อง (กริด 5–8) หน้าร้านแนว B ด้านหลังแนว C
for i in (4, 5, 6):
    add_wall(f'W-F1-SH{i-3}-FR', 1, 'x', yB, GX[i] + cw, GX[i + 1] - cw, z0, beam_soffit(1, 'main'), 'A04', 'A13',
             [((GX[i] + GX[i + 1]) / 2, 2.80, 0.0, 2.60)], name=f'ผนังหน้าร้าน {i-3}')
    add_wall(f'W-F1-SH{i-3}-BK', 1, 'x', yC, GX[i] + cw, GX[i + 1] - cw, z0, beam_soffit(1, 'main'), 'A04', 'A13',
             [(GX[i] + 0.75, 0.90, 0.0, 2.00)], name=f'ผนังหลังร้าน {i-3}')
for k in (5, 6, 7):
    add_wall(f'W-F1-SH-G{k+1}', 1, 'y', GX[k], yB + cd, yC - cd, z0, beam_soffit(1, 'main'), 'A04', 'A13', name=f'ผนังกั้นร้านกริด {k+1}')
# ห้องน้ำชาย–หญิง (กริด 8–10) A14 ทั้งก่อและฉาบ
for i in (7, 8):
    add_wall(f'W-F1-WC{i-6}-FR', 1, 'x', yB, GX[i] + cw, GX[i + 1] - cw, z0, beam_soffit(1, 'main'), 'A14', 'A14',
             [(GX[i] + 1.75, 0.90, 0.0, 2.00)], name=f'ผนังห้องน้ำชั้น 1 ห้อง {i-6} ด้านหน้า')
    add_wall(f'W-F1-WC{i-6}-BK', 1, 'x', yC, GX[i] + cw, GX[i + 1] - cw, z0, beam_soffit(1, 'main'), 'A14', 'A14',
             [(GX[i] + 1.75, 0.90, 0.0, 2.00)], name=f'ผนังห้องน้ำชั้น 1 ห้อง {i-6} ด้านหลัง')
    for j in range(3):   # ห้องส้วม 3 ห้อง กว้าง 1.20 ตามแบบห้องน้ำ
        x = GX[i] + 0.25 + 1.20 * (j + 1)
        if x < GX[i + 1] - 0.3:
            add_wall(f'W-F1-WC{i-6}-P{j+1}', 1, 'y', x, yB + cd, yB + cd + 1.80, z0, z0 + 2.10, 'A14', None,
                     name=f'ผนังกั้นห้องส้วม ชั้น 1 ห้อง {i-6}')
        add(f'FX-F1-WC{i-6}-{j+1}', 'สุขภัณฑ์', 1, 'A21',
            prism([(GX[i] + 0.25 + 1.2 * j + 0.4, yB + 0.6), (GX[i] + 0.25 + 1.2 * j + 0.8, yB + 0.6),
                   (GX[i] + 0.25 + 1.2 * j + 0.8, yB + 1.3), (GX[i] + 0.25 + 1.2 * j + 0.4, yB + 1.3)], z0, 0.40),
            name=f'โถส้วม ชั้น 1 ห้องน้ำ {i-6}', assumed=True, qty=dict(count=1))
for k in (8, 9):
    add_wall(f'W-F1-WC-G{k+1}', 1, 'y', GX[k], yB + cd, yC - cd, z0, beam_soffit(1, 'main'), 'A14', 'A14', name=f'ผนังห้องน้ำชั้น 1 กริด {k+1}')
add(f'TL-F1-WC', 'กระเบื้อง', 1, 'A14', prism([(GX[7] + cw, yB + cd), (GX[9] - cw, yB + cd), (GX[9] - cw, yC - cd), (GX[7] + cw, yC - cd)], z0, 0.02),
    name='กระเบื้องพื้นห้องน้ำชั้น 1 16x16 นิ้ว', assumed=True, qty=dict(area=round((GX[9] - GX[7] - 2 * cw) * (yC - yB - 2 * cd), 3), tile_size='16x16 นิ้ว', tile_model='ระบุภายหลัง', tiles=math.ceil((GX[9] - GX[7] - 2 * cw) * (yC - yB - 2 * cd) / 0.4064 ** 2)))

# ---------- ฉาบโครงสร้าง: เสา 1 ซม., ท้องคานและข้างคาน 0.5 ซม. (ผู้ใช้กำหนด) ----------
PL_COL, PL_BEAM = 0.010, 0.005
ceil_task = {1: 'A12', 2: 'A09', 3: 'A09', 4: 'A10', 5: 'A11'}   # งานฉาบของชั้นที่คาน/เสาอยู่
for e in [e for e in elements if e['category'] == 'เสา' and e['task'] in ('DONE', 'A01') and not e['id'].endswith('-ST')]:
    g = e['geom']
    xs = [p[0] for p in g['poly']]; ys = [p[1] for p in g['poly']]
    xa, xb, ya, yb = min(xs) - PL_COL, max(xs) + PL_COL, min(ys) - PL_COL, max(ys) + PL_COL
    f = e['floor']
    h = g['t']
    add(f'PL-{e["id"]}', 'งานฉาบ', f, ceil_task[f], prism([(xa, ya), (xb, ya), (xb, yb), (xa, yb)], g['z0'], h),
        name=f'ฉาบเสา {e["name"]} หนา 1 ซม.', assumed=True,
        qty=dict(area=round(2 * ((max(xs) - min(xs)) + (max(ys) - min(ys))) * h, 3), thickness=PL_COL))
for e in [e for e in elements if e['category'] == 'คาน']:
    g = e['geom']
    p0, p1 = g['p0'], g['p1']
    lv = e['id'].rsplit('-', 1)[1]          # L2..L5 / LR
    if lv.startswith('M'):                  # คานชานพักบันได
        f = int(lv[1:])
    else:
        f = 5 if lv == 'LR' else int(lv[1:]) - 1   # ชั้นที่คานเป็นเพดาน
    w, d = g['w'], g['d']
    horiz_x = abs(p1[0] - p0[0]) > abs(p1[1] - p0[1])
    parts = []
    for side in (-1, 1):
        off = side * (w / 2 + PL_BEAM / 2)
        q0 = [p0[0], p0[1] + off, p0[2]] if horiz_x else [p0[0] + off, p0[1], p0[2]]
        q1 = [p1[0], p1[1] + off, p1[2]] if horiz_x else [p1[0] + off, p1[1], p1[2]]
        parts.append(member(q0, q1, PL_BEAM, d))
    zb = p0[2] - d / 2 - PL_BEAM / 2
    parts.append(member([p0[0], p0[1], zb], [p1[0], p1[1], zb], w + 2 * PL_BEAM, PL_BEAM))
    L = math.dist(p0, p1)
    add(f'PL-{e["id"]}', 'งานฉาบ', f, ceil_task[f], dict(type='multi', parts=parts),
        name=f'ฉาบท้องคานและข้างคาน {e["id"]} หนา 0.5 ซม.', assumed=True,
        qty=dict(area=round(L * (w + 2 * d), 3), thickness=PL_BEAM))
for f, task in ((2, 'A12'), (3, 'A15'), (4, 'A15'), (5, 'A15')):
    add(f'PL-CEIL-F{f}', 'งานฉาบ', f - 1, task,
        pieces_geom(FL[f] - SLAB_T - PL_T, PL_T),
        name=f'ฉาบใต้ท้องพื้นชั้น {f} (เพดานชั้น {f-1})', assumed=True, qty=dict(area=SLAB_AREA))
TILE_ROOM = dict(size='60x60 ซม.', w=0.60, model='ระบุภายหลัง')
TILE_WC = dict(size='16x16 นิ้ว', w=0.4064, model='ระบุภายหลัง')
ASSUMPTIONS.append('กระเบื้องห้องพัก โถงทางเดิน ระเบียง และโถงบันได 60x60 ซม., ห้องน้ำ 16x16 นิ้ว (ผู้ใช้กำหนด รุ่นระบุภายหลัง); ระเบียงใช้ 60x60 รอผู้ใช้ยืนยัน; จำนวนแผ่นคิดสุทธิไม่รวมเผื่อเสีย')


def add_tile(eid, f, x0, x1, y0, y1, spec, name, z=None):
    x0, x1, y0, y1 = min(x0, x1), max(x0, x1), min(y0, y1), max(y0, y1)
    area = (x1 - x0) * (y1 - y0)
    add(eid, 'กระเบื้อง', f, 'A16' if f < 5 else 'A17',
        prism([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], FL[f] if z is None else z, 0.02), name=name, assumed=True,
        qty=dict(area=round(area, 3), tile_size=spec['size'], tile_model=spec['model'],
                 tiles=math.ceil(area / (spec['w'] ** 2))))


h = WALL_T / 2 + PL_T
for f in (2, 3, 4, 5):
    for side in ('N', 'S'):
        y_out, y_rm, y_cor = (0.0, yB, yC) if side == 'N' else (yF, yE, yD)
        o = 0.10 + h if side == 'N' else -(0.10 + h)
        for i in range(9):
            tx0, tx1, bx0, bx1 = bay_split(i)
            x0, x1 = GX[i] + h, GX[i + 1] - h
            if side == 'N' and i == STAIR_BAY[0]:
                continue
            ry0, ry1 = (y_rm + h, y_cor - h) if side == 'N' else (y_rm - h, y_cor + h)
            add_tile(f'TL-F{f}-{side}{i+1}-RM', f, x0, x1, ry0, ry1, TILE_ROOM, f'กระเบื้องห้องพัก ชั้น {f} ห้อง {side}{i+1}')
            wy0, wy1 = y_out + o, (y_rm - h if side == 'N' else y_rm + h)
            add_tile(f'TL-F{f}-{side}{i+1}-WC', f, max(tx0 + h, x0), min(tx1 - h, x1), wy0, wy1, TILE_WC, f'กระเบื้องห้องน้ำ ชั้น {f} ห้อง {side}{i+1}')
            add_tile(f'TL-F{f}-{side}{i+1}-BL', f, max(bx0 + h, x0), min(bx1 - h, x1), wy0, wy1, TILE_ROOM, f'กระเบื้องระเบียง ชั้น {f} ห้อง {side}{i+1}')
    add_tile(f'TL-F{f}-COR', f, x_min, x_max, yC + h, yD - h, TILE_ROOM, f'กระเบื้องโถงทางเดิน ชั้น {f}')

def summary():
    from collections import Counter
    return Counter((e['category'], e['task']) for e in elements)


if __name__ == '__main__':
    model = dict(project='หอพักคนงาน 5 ชั้น อาคาร A (ชัยเสรี หนองแค)', units='m', axes='x=กริด1→10, y=กริดA→F, z=ระดับ',
                 grid=dict(x={str(i + 1): v for i, v in enumerate(GX)}, y=GY), levels=dict(FL=FL, roof_beam=ROOF_BEAM, ridge=RIDGE),
                 assumptions=ASSUMPTIONS, elements=elements)
    json.dump(model, open('elements.json', 'w'), ensure_ascii=False)
    for k, v in sorted(summary().items()):
        print(k, v)
    print('total', len(elements), 'z_eave', round(z_eave, 3), 'ridge', rx0, rx1)
