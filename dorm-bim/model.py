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
        p0 = (x, y_e, zroof(x, y_e) - 0.10)
        p1 = (x, y_t, zroof(x, y_t) - 0.10)
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
        p0 = (x_e, y, zroof(x_e, y) - 0.10)
        p1 = (x_t, y, zroof(x_t, y) - 0.10)
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


# =====================================================================
# งานสถาปัตย์ (แปลน A-01 ชั้น 1, A-02 ชั้น 2–5, แปลนห้องน้ำชั้น 1)
# กริดสถาปัตย์ A,B,C,D = กริดโครงสร้าง B,C,D,E
# =====================================================================
WALL_T = 0.10            # อิฐมวลเบา
PL_T = 0.015             # ฉาบแต่ละด้าน
ASSUMPTIONS += [
    'กริดสถาปัตย์ A,B,C,D ในแปลน A-01/A-02 ตรงกับกริดโครงสร้าง B,C,D,E',
    'ผนังอิฐมวลเบาหนา 0.10 ม. ฉาบด้านละ 0.015 ม. สูงจากพื้นถึงท้องคาน (คานลึก 0.50 หรือ 0.40)',
    'ขนาดประตู–หน้าต่างไม่มีตาราง: ประตูห้อง 0.90x2.00, ประตูระเบียง 0.80x2.00, ประตูห้องน้ำ 0.70x2.00, ช่องระแนงระเบียง 1.20x1.20 สูงจากพื้น 0.90, ช่องลมห้องน้ำ 0.40x0.40 สูงจากพื้น 1.80, ช่องหน้าร้าน 2.80x2.60',
    'ฉาบผนังห้องโถงบันไดชั้น 1 ผูกกับ A12; ฉาบใต้ท้องพื้น A12 = ใต้พื้นชั้น 2, A15 = ใต้พื้นชั้น 3–5 (เพดานชั้น 2–4)',
    'กระเบื้องพื้น A16/A17 แทนด้วยแผ่นหนา 0.02 ม. เต็มพื้นที่ใช้งานแต่ละชั้น (ห้อง ห้องน้ำ ระเบียง ทางเดิน)',
    'สุขภัณฑ์ A21 แทนด้วยกล่องโถส้วมและอ่างล้างหน้า ห้องน้ำละ 1 ชุด',
    'ยังไม่มีชิ้นส่วนของ A07/A08 (ระบบท่อ), A19/A20 (สี ฝ้า), A22/A23 เพราะไม่มีแบบระบบและเป็นงานผิว/งานทดสอบ',
    'ไม่ได้ขึ้นบันไดเหล็กภายนอกด้านกริด 10 (ไม่มีในแผน R3)',
]


def beam_soffit(f, kind):
    """ระดับท้องคานเหนือผนังของชั้น f; kind 'main' (คานลึก 0.50) / 'edge' (0.40)"""
    top = ROOF_BEAM if f == 5 else FL[f + 1] - SLAB_T
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


def add_wall(eid, floor, axis, fixed, a0, a1, z0, z1, task_wall, task_plaster, openings=(), name=None):
    if a1 - a0 < 0.05:
        return
    pcs = wall_pieces(a0, a1, z0, z1, list(openings))
    area = sum((b - a) * (d - c) for a, b, c, d in pcs)
    add(eid, 'ผนัง', floor, task_wall,
        dict(type='multi', parts=[rect_prism(axis, fixed, a, b, c, d, 0, WALL_T) for a, b, c, d in pcs]),
        name=name or f'ผนังก่อ {eid}', assumed=True, qty=dict(area=round(area, 3), length=round(a1 - a0, 3)))
    if task_plaster:
        parts = []
        for side in (-1, 1):
            off = side * (WALL_T / 2 + PL_T / 2)
            parts += [rect_prism(axis, fixed, a, b, c, d, off, PL_T) for a, b, c, d in pcs]
        add(eid + '-PL', 'งานฉาบ', floor, task_plaster, dict(type='multi', parts=parts),
            name=f'ฉาบ {eid}', assumed=True, qty=dict(area=round(2 * area, 3)))
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
    name='กระเบื้องพื้นห้องน้ำชั้น 1', assumed=True, qty=dict(area=round((GX[9] - GX[7] - 2 * cw) * (yC - yB - 2 * cd), 3)))

# ---------- ฉาบเสา ชั้น 1 และใต้ท้องพื้น ----------
for i in range(10):
    for r in COL_ROWS:
        w, d = COL_SEC[1]
        w2, d2 = w + 2 * PL_T, d + 2 * PL_T
        add(f'PL-C1-{i+1}{r}-F1', 'งานฉาบ', 1, 'A12',
            prism([(GX[i] - w2 / 2, GY[r] - d2 / 2), (GX[i] + w2 / 2, GY[r] - d2 / 2), (GX[i] + w2 / 2, GY[r] + d2 / 2), (GX[i] - w2 / 2, GY[r] + d2 / 2)],
                  FL[1], round(FL[2] - SLAB_T - FL[1], 3)),
            name=f'ฉาบเสา {i+1}/{r} ชั้น 1', assumed=True, qty=dict(area=round(2 * (w + d) * (FL[2] - SLAB_T - FL[1]), 3)))
for f, task in ((2, 'A12'), (3, 'A15'), (4, 'A15'), (5, 'A15')):
    add(f'PL-CEIL-F{f}', 'งานฉาบ', f - 1, task,
        prism([(x_min, GY['A']), (x_max, GY['A']), (x_max, GY['F']), (x_min, GY['F'])], FL[f] - SLAB_T - PL_T, PL_T),
        name=f'ฉาบใต้ท้องพื้นชั้น {f} (เพดานชั้น {f-1})', assumed=True,
        qty=dict(area=round((x_max - x_min) * (GY['F'] - GY['A']) - (sx1 - sx0) * (sy1 - sy0), 3)))
for f in (2, 3, 4, 5):
    add(f'TL-F{f}', 'กระเบื้อง', f, 'A16' if f < 5 else 'A17',
        dict(type='prism', poly=[[x_min, GY['A']], [x_max, GY['A']], [x_max, GY['F']], [x_min, GY['F']]], z0=FL[f], t=0.02,
             holes=[[[sx0, sy0], [sx1, sy0], [sx1, sy1], [sx0, sy1]]]),
        name=f'กันซึมและกระเบื้องพื้นชั้น {f}', assumed=True,
        qty=dict(area=round((x_max - x_min) * (GY['F'] - GY['A']) - (sx1 - sx0) * (sy1 - sy0), 3)))


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
