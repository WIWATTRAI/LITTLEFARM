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
B5_X = [1.5, 5.5, 8.5, 12.25, 16.0, 19.0, 23.0, 26.0, 30.0]
STAIR_BAY = (3, 4)      # ช่วงกริด 4–5 (index 3..4) ระหว่าง B–C

ASSUMPTIONS = [
    'แนวด้านยาวของเสา C1 (0.50) วางตามแกน y (ด้านสั้นอาคาร)',
    'หลังคาน = ระดับพื้นสำเร็จ − 0.10 ม. (ใต้พื้นสำเร็จรูป+topping)',
    'คานหลังคา +16.30 วางตามผังคานชั้น 2–5 (ไม่รวม B5) เพราะไม่มีผังคานหลังคา',
    'คานหลังคา +16.30 ผูกกับกิจกรรม A01 (เสาชั้น 5) เพราะแผนไม่มีรายการคานหลังคาแยก',
    'หลังคาปั้นหยา: ระนาบผ่าน +16.30 ที่แนว A/F และสันที่ +20.00 แนว CX, ชายคายื่นด้านยาว 1.195 ม. ด้านสกัด 1.33 ม.',
    'โครงถักหลังคาที่กริด 3–8, จันทัน C100x50 ระยะ 0.875 ม., หน้าตัดเหล็ก 2C แทนด้วยกล่องขนาดภายนอก',
    'บันไดภายในช่วงกริด 4–5 ระหว่าง B–C สองช่วงต่อชั้น แทนด้วยแผ่นพื้นลาดหนา 0.15 ม.',
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
            L = 3.5 - COL_SEC[min(floor, 5)][0]
            if lv != 'R' and r == 'C' and i == STAIR_BAY[0]:
                pass
            add(f'B2-{r}{i+1}-{i+2}-{sfx}', 'คาน', floor, task,
                member((GX[i] + 0.15, GY[r], c), (GX[i + 1] - 0.15, GY[r], c), 0.25, 0.50),
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
beams_level('R', ROOF_BEAM, 'A01', 5, with_b5=False, assumed=True)

# ---------- พื้น ----------
x_min, x_max = GX[0] - 0.175, GX[-1] + 0.175
add('GS-F1', 'พื้น', 1, 'DONE', prism([(x_min, GY['B']), (x_max, GY['B']), (x_max, GY['E']), (x_min, GY['E'])],
                                       FL[1] - GS_T, GS_T),
    name='พื้นชั้น 1 (GS)', qty=dict(area=round((x_max - x_min) * (GY['E'] - GY['B']), 3)))
sx0, sx1 = GX[STAIR_BAY[0]] + 0.125, GX[STAIR_BAY[1]] - 0.125
sy0, sy1 = GY['B'] + 0.125, GY['C'] - 0.125
for f in (2, 3, 4, 5):
    poly = [(x_min, GY['A']), (x_max, GY['A']), (x_max, GY['F']), (x_min, GY['F']), (x_min, GY['A'])]
    # รูเปิดบันได: แบ่งพื้นเป็นสองแผ่นรอบช่องบันได
    outer = [(x_min, GY['A']), (x_max, GY['A']), (x_max, GY['F']), (x_min, GY['F'])]
    area = (x_max - x_min) * (GY['F'] - GY['A']) - (sx1 - sx0) * (sy1 - sy0)
    add(f'PS-F{f}', 'พื้น', f, 'DONE',
        dict(type='prism', poly=[[round(a, 4), round(b, 4)] for a, b in outer], z0=FL[f] - SLAB_T, t=SLAB_T,
             holes=[[[sx0, sy0], [sx1, sy0], [sx1, sy1], [sx0, sy1]]]),
        name=f'พื้นชั้น {f} (PS)', qty=dict(area=round(area, 3)))

# ---------- บันได (2 ช่วงต่อชั้น) ----------
for f in (1, 2, 3, 4):
    z0, z1 = FL[f], FL[f + 1]
    zm = (z0 + z1) / 2
    xw = (sx1 - sx0) / 2
    land_y = sy0 + 1.30          # ชานพักฝั่ง B
    run_y0, run_y1 = land_y, sy1 - 0.0
    t = 0.15
    # ช่วงที่ 1: ขึ้นจากฝั่ง C ไปฝั่ง B (ซีกซ้าย)
    add(f'ST-F{f}-1', 'บันได', f, 'DONE',
        plate([(sx0, run_y1, z0), (sx0 + xw, run_y1, z0), (sx0 + xw, run_y0, zm), (sx0, run_y0, zm)], t),
        assumed=True, name=f'บันไดชั้น {f}→{f+1} ช่วง 1')
    add(f'ST-F{f}-L', 'บันได', f, 'DONE',
        prism([(sx0, sy0), (sx1, sy0), (sx1, land_y), (sx0, land_y)], zm - t, t),
        assumed=True, name=f'ชานพักชั้น {f}')
    add(f'ST-F{f}-2', 'บันได', f, 'DONE',
        plate([(sx0 + xw, run_y0, zm), (sx1, run_y0, zm), (sx1, run_y1, z1), (sx0 + xw, run_y1, z1)], t),
        assumed=True, name=f'บันไดชั้น {f}→{f+1} ช่วง 2')

# ---------- หลังคา ----------
OV_SIDE, OV_END = 1.195, 1.33
yc = GY['CX']
half = yc - GY['A']
slope = (RIDGE - ROOF_BEAM) / half            # tan
run = half + OV_SIDE
z_eave = RIDGE - run * slope
ex0, ex1 = GX[0] - OV_END, GX[-1] + OV_END
ey0, ey1 = GY['A'] - OV_SIDE, GY['F'] + OV_SIDE
rx0, rx1 = ex0 + run, ex1 - run               # ปลายสันหลังคา


def zroof(x, y):
    dy = abs(y - yc)
    dx = max(rx0 - x, x - rx1, 0)
    return RIDGE - max(dy, dx) * slope


# โครงถักที่กริด 3..8 (index 2..7)
TR_TOP = (0.125, 0.10)   # 2C125x50 (กว้าง 0.10 ลึก 0.125)
for gi in range(2, 8):
    x = GX[gi]
    zb = ROOF_BEAM + 0.0625
    yb0, ye0 = GY['B'], GY['E']
    pts = []
    add(f'TR{gi+1}-BC', 'โครงหลังคาเหล็ก', 5, 'A03.2', member((x, yb0, zb), (x, ye0, zb), 0.10, 0.125),
        name=f'โครงถักกริด {gi+1} ขื่อ', assumed=True, qty=dict(length=round(ye0 - yb0, 3), section='2C125x50x20x3.2'))
    for side, (ya, yb) in enumerate(((GY['B'], yc), (GY['E'], yc))):
        za = zroof(x, ya) - 0.10
        zt = RIDGE - 0.10
        add(f'TR{gi+1}-TC{side+1}', 'โครงหลังคาเหล็ก', 5, 'A03.2', member((x, ya, za), (x, yb, zt), 0.10, 0.125),
            name=f'โครงถักกริด {gi+1} จันทันเอก', assumed=True,
            qty=dict(length=round(mlen((x, ya, za), (x, yb, zt)), 3), section='2C125x50x20x3.2'))
    for k, y in enumerate((GY['B'] + 2.55, GY['C'], yc, GY['D'], GY['E'] - 2.55)):
        zt = zroof(x, y) - 0.15
        add(f'TR{gi+1}-V{k+1}', 'โครงหลังคาเหล็ก', 5, 'A03.2', member((x, y, zb + 0.06), (x, y, zt), 0.10, 0.10),
            name=f'โครงถักกริด {gi+1} เสาตั้ง', assumed=True,
            qty=dict(length=round(zt - zb, 3), section='2C100x50x20x3.2'))
    for k, (ya, yb) in enumerate(((GY['B'] + 2.55, GY['C']), (GY['E'] - 2.55, GY['D']))):
        p0 = (x, ya, zb + 0.06)
        p1 = (x, yb, zroof(x, yb) - 0.15)
        add(f'TR{gi+1}-D{k+1}', 'โครงหลังคาเหล็ก', 5, 'A03.2', member(p0, p1, 0.10, 0.10),
            name=f'โครงถักกริด {gi+1} ค้ำยัน', assumed=True, qty=dict(length=round(mlen(p0, p1), 3), section='2C100x50x20x3.2'))

# อกไก่ ตะเฆ่สัน อะเส
zr = RIDGE - 0.10
add('RF-RIDGE', 'โครงหลังคาเหล็ก', 5, 'A03.2', member((rx0, yc, zr), (rx1, yc, zr), 0.10, 0.125),
    name='อกไก่', assumed=True, qty=dict(length=round(rx1 - rx0, 3), section='2C125x50x20x3.2'))
for k, (cx, cy) in enumerate(((ex0, ey0), (ex1, ey0), (ex1, ey1), (ex0, ey1))):
    rx = rx0 if cx == ex0 else rx1
    p0, p1 = (cx, cy, z_eave - 0.10), (rx, yc, zr)
    add(f'RF-HIP{k+1}', 'โครงหลังคาเหล็ก', 5, 'A03.2', member(p0, p1, 0.10, 0.125),
        name='ตะเฆ่สัน', assumed=True, qty=dict(length=round(mlen(p0, p1), 3), section='2C125x50x20x3.2'))
za = ROOF_BEAM + 0.0625
for k, (p0, p1) in enumerate((((GX[0], GY['A'] + 0.1), (GX[-1], GY['A'] + 0.1)),
                               ((GX[0], GY['F'] - 0.1), (GX[-1], GY['F'] - 0.1)),
                               ((GX[0], GY['A'] + 0.1), (GX[0], GY['F'] - 0.1)),
                               ((GX[-1], GY['A'] + 0.1), (GX[-1], GY['F'] - 0.1)))):
    add(f'RF-WP{k+1}', 'โครงหลังคาเหล็ก', 5, 'A03.2', member((*p0, za), (*p1, za), 0.10, 0.125),
        name='อะเส', assumed=True, qty=dict(length=round(math.dist(p0, p1), 3), section='2C125x50x20x3.2'))

# จันทัน C100x50 @0.875 บนระนาบด้านยาว (แนว y) และด้านสกัด (แนว x)
xs = []
x = ex0 + 0.477
while x < ex1 - 0.2:
    xs.append(round(x, 3)); x += 0.875
n = 0
for x in xs:
    for side in (0, 1):
        y_e = ey0 if side == 0 else ey1
        # จุดบน: ชนสันหรือชนตะเฆ่
        if rx0 <= x <= rx1:
            y_t = yc
        else:
            d = (rx0 - x) if x < rx0 else (x - rx1)
            y_t = yc - d if side == 0 else yc + d
            if (side == 0 and y_t <= y_e) or (side == 1 and y_t >= y_e):
                continue
        p0 = (x, y_e, zroof(x, y_e) - 0.08)
        p1 = (x, y_t, zroof(x, y_t) - 0.08)
        n += 1
        add(f'RF-RAF{n:03d}', 'โครงหลังคาเหล็ก', 5, 'A03.2', member(p0, p1, 0.05, 0.10),
            name='จันทัน C100x50', assumed=True, qty=dict(length=round(mlen(p0, p1), 3), section='C100x50x20x3.2'))
ys = []
y = ey0 + 0.477
while y < ey1 - 0.2:
    ys.append(round(y, 3)); y += 0.875
for y in ys:
    for side in (0, 1):
        x_e = ex0 if side == 0 else ex1
        d = abs(y - yc)
        x_t = (rx0 - (run - d) + 0) if False else None
        # ตะเฆ่: |y-yc| = dx  -> x = rx0 - (yc_dist) ... จุดชนตะเฆ่ที่ dx == dy
        x_t = rx0 - d if side == 0 else rx1 + d
        if (side == 0 and x_t <= x_e + 0.05) or (side == 1 and x_t >= x_e - 0.05):
            continue
        p0 = (x_e, y, zroof(x_e, y) - 0.08)
        p1 = (x_t, y, zroof(x_t, y) - 0.08)
        n += 1
        add(f'RF-RAF{n:03d}', 'โครงหลังคาเหล็ก', 5, 'A03.2', member(p0, p1, 0.05, 0.10),
            name='จันทัน C100x50 (ด้านสกัด)', assumed=True, qty=dict(length=round(mlen(p0, p1), 3), section='C100x50x20x3.2'))

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
