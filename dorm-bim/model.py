"""หอพักคนงาน 5 ชั้น อาคาร A — นิยามชิ้นส่วนโมเดล (แหล่งข้อมูลเดียวสำหรับ SketchUp / GLB / JSON)

แกน: x ตามกริด 1→10 (เมตร), y ตามกริด A→F (A = ด้านหน้า, y=0), z ระดับ (±0.00 = พื้นรอบอาคาร)
แหล่งแบบ: FOR CON (S101, S102, S910, S911), S001, S106, S107, A201, A203
ค่าที่ไม่มีในแบบใส่ไว้ใน ASSUMPTIONS และติด flag "assumed" ที่ชิ้นส่วน
"""
import json, math, re

# ---------- กริดและระดับ ----------
GX = [i * 3.5 for i in range(10)]                     # กริด 1..10
GX11 = GX[-1] + 1.48                                  # กริด 11 สำหรับโครงสร้างบันไดหนีไฟ ห่างกริด 10 1.48 ม. (ผู้ใช้สั่ง 11 พ.ย. 2569)
GY = {'A': 0.0, 'B': 1.65, 'C': 6.75, 'CX': 7.75, 'D': 8.75, 'E': 13.85, 'F': 15.5}
FL = {1: 0.30, 2: 3.50, 3: 6.70, 4: 9.90, 5: 13.10}    # ระดับพื้นสำเร็จ
ROOF_BEAM = 16.30
RIDGE = 20.00
FOOT_TOP = -0.30
SLAB_T = 0.10           # พื้นสำเร็จรูป 0.05 + topping 0.05 (S911 แบบ PS)
GS_T = 0.10             # พื้นชั้น 1 (GS)
DROP = 0.075            # พื้นระเบียงหลังห้อง+ห้องน้ำ (แถบยื่น A–B, E–F) ต่ำกว่าห้องพัก/ทางเดิน (ผู้ใช้กำหนด 10 พ.ย. 2569)
S1_T = 0.10             # พื้นหล่อในที่ S1 ห้องน้ำ (S911 แบบขยายพื้น S1 หนา 100)
PLANK_W = 0.35          # แผ่นพื้นสำเร็จรูป 350x50 (S911)

# เสา C1 (S910 เดิม: ชั้น 1–2 0.35x0.50, ชั้น 3 0.30x0.50, ชั้น 4–5 0.30x0.40)
# ผู้ใช้สั่ง 11 พ.ย. 2569: เสาทุกชั้น 1–5 ขนาด 0.35x0.50 เท่ากันหมด
COL_SEC = {0: (0.35, 0.50), 1: (0.35, 0.50), 2: (0.35, 0.50), 3: (0.35, 0.50), 4: (0.35, 0.50), 5: (0.35, 0.50)}


def edge_dx(i, w, k=1):
    """คานบนกริด 1 และ 10 (ด้านข้างอาคาร): เลื่อนศูนย์คานออกนอกให้ผิวนอกคานเสมอผิวนอกเสา (ผู้ใช้สั่ง 11 พ.ย. 2569)"""
    off = COL_SEC[k][0] / 2 - w / 2
    return -off if i == 0 else (off if i == 9 else 0.0)
COL_ROWS = ['B', 'C', 'D', 'E']
# คาน B2 แนว C, D (ทางเดินหน้าห้อง): ผิวคานด้านทางเดินเสมอผิวเสา ผนังทางเดินอยู่ใต้คาน ฉาบเสา–คาน–ผนังแนวเดียวกัน (ผู้ใช้สั่ง 11 พ.ย. 2569)
B2_DY = {'B': 0.0, 'C': 0.125, 'D': -0.125, 'E': 0.0}

# คานซอย B5 (S102) ตำแหน่ง x
B5_X = [1.5, 5.5, 8.5, 12.5, 15.5, 19.5, 22.5, 26.5, 30.0]   # ตามระยะ 1.50/2.00 ในแปลน A-02 และผังคาน S-04
# ห้องแถวติดบันได (ฝั่ง N) กริด 5–9 (ห้อง N5–N8): สลับห้องน้ำ–ระเบียงในช่วงเสา ห้องน้ำ N5 ชิดบันได (ผู้ใช้สั่ง 10 พ.ย. 2569)
# แนวผนัง/คานซอย B5 ย้ายตามเป็นภาพกลับของเดิมในช่วงเสา (b5' = GX[i] + GX[i+1] - b5) ห้องริม N9 และฝั่ง S คงเดิม
B5_SWAP_N = (4, 5, 6, 7)


def b5x(i, side):
    """แนวผนัง/คานซอย B5 ของช่วงเสา i ฝั่ง side ('N' / 'S')"""
    if side == 'N' and i in B5_SWAP_N:
        return GX[i] + GX[i + 1] - B5_X[i]
    return B5_X[i]


STAIR_BAY = (3, 4)      # ช่วงกริด 4–5 (index 3..4)
# บันไดหลัก (A-05): ชานพักในแถบยื่นด้านหน้า กว้าง 1.50, ช่วงบันไดละ 9 ลูกนอน x 0.30 = 2.70 จากแนว B, ลูกตั้ง 0.16 x 20
ST_RUN_Y1 = 1.65 + 2.70                        # ปลายช่วงบันไดฝั่งห้อง (ขอบช่องเปิด)

ASSUMPTIONS = [
    'แนวด้านยาวของเสา C1 (0.50) วางตามแกน y (ด้านสั้นอาคาร)',
    'หลังคาน = ระดับพื้นสำเร็จ − 0.10 ม. (ใต้พื้นสำเร็จรูป+topping)',
    'ไม่มีคาน คสล. หลังคา (ผู้ใช้ยกเลิก 9 พ.ย. 2569): ขื่อ/อะเสเหล็กวางบนหัวเสาและผนังชั้น 5 ที่ +16.30, ผนังชั้น 5 ก่อถึง +16.30',
    'หลังคาปั้นหยา: ผิวบนที่สัน +20.00 แนว CX, ท้องจันทันวางบนอะเส 2C125 (หลังอะเส +16.425) ได้ความลาด ≈24° ตาม S107, ชายคายื่นด้านยาว 1.195 ม. ด้านสกัด 1.33 ม.',
    'โครงหลังคาตาม S106/S107: ขื่อ/อะเส/สะพาน/ตะเข้/อกไก่/คานรับเสาดั้ง 2C125x50x20x3.2, เสารับจันทัน/เสารับอกไก่/ขื่อทางยาว 2C100x50x20x3.2, จันทัน/เหล็กทะแยง C100x50x20x3.2 ระยะจันทัน 0.875 ม.',
    '2C ขึ้นแบบประกบปากชนกันเป็นกล่อง (รอผู้ใช้ยืนยันว่าไม่ใช่ประกบหลัง); ไม่ได้ขึ้นเพลทรอยต่อ; น้ำหนักเหล็ก C125 6.13 กก./ม., C100 5.50 กก./ม.',
    'ขื่อด้านสั้นวางทุกกริด 2–9 บนคานหลังคา, เสารับจันทันที่แนว B, กลางช่วง B–C (2.55 ม.), C, D และฝั่ง E; คานรับเสาดั้งที่ +18.74 (2.44 ม. จาก +16.30)',
    'บันไดหลักตาม A-05: ช่วงกริด 4–5 ช่วงบันไดกว้าง 1.50 ช่องกลาง 0.40 ลูกนอน 0.30 x 9 ลูกตั้ง 0.16 x 20 ชานพักกว้าง 1.50 ในแถบยื่นด้านหน้า ที่ระดับพื้น +1.60; ท้องบันไดหนา 0.12 ม. ชานพักหนา 0.16 ม. (สมมติ) บันไดแต่ละช่วงเป็น component ชิ้นตันรูปขั้นบันไดจริง',
    'คานบันได BST1/BST2/BST3 200x400 ตาม S-04: BST1 ขอบช่องเปิดระดับพื้น และขอบชานพักแนว B, BST2 (กริด 4,5) และ BST3 (ขอบนอก) ระดับชานพัก; ไม่มีคาน B2 แนว B ช่วงกริด 4–5 ชั้น 2–5 (ผู้ใช้แจ้ง)',
    'ระยะคานซอย B5 และผนังห้องน้ำปรับตามแปลน A-02/ผังคาน S-04 (เดิมใช้ S102)',
    'ประตูห้องน้ำ 0.70x1.80 เปิดจากห้องพัก (ผนังแนวห้อง–ระเบียง) ผนังห้องน้ำด้านระเบียงเป็นผนังทึบ (ผู้ใช้กำหนด)',
    'หน้าต่างห้องริมกริด 1 และ 10 ชั้น 2–5: W16 กว้าง 1.20 สูง 1.10 ขอบล่าง 0.90 วางกลางห้อง (ขนาดวัดจากรูปด้าน A203 มาตราส่วน 1:75 ไม่มีตารางหน้าต่าง)',
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
for r in COL_ROWS:                      # GB2 200x500 แนวยาว (ผู้ใช้กำหนด 11 พ.ย. 2569 เดิม 250x500)
    for i in range(9):
        x0, x1 = GX[i], GX[i + 1]
        z = 0.20 - 0.25
        L = 3.5 - 0.35
        add(f'GB2-{r}{i+1}-{i+2}', 'คานคอดิน', 1, 'DONE',
            member((x0 + 0.175, GY[r], z), (x1 - 0.175, GY[r], z), 0.20, 0.50),
            qty=dict(length=L, concrete=round(L * 0.20 * 0.5, 4)))
for i in range(10):                     # GB1 200x500 แนวขวาง (ผู้ใช้กำหนด 11 พ.ย. 2569 เดิม 250x400) หลังคานคงที่ +0.20
    for a, b in (('B', 'C'), ('C', 'D'), ('D', 'E')):
        y0, y1 = GY[a] + 0.25, GY[b] - 0.25
        z = 0.20 - 0.25
        L = y1 - y0
        xg = GX[i] + edge_dx(i, 0.20, 0)
        add(f'GB1-{i+1}-{a}{b}', 'คานคอดิน', 1, 'DONE',
            member((xg, y0, z), (xg, y1, z), 0.20, 0.50),
            qty=dict(length=round(L, 3), concrete=round(L * 0.20 * 0.5, 4)))

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

# ---------- ฐานบันไดหนีไฟ กริด 11 (ผู้ใช้สั่ง 11 พ.ย. 2569) ----------
# ตอม่อ F1 0.60x0.60x0.60 ที่ C/11, D/11 (ระดับเดียวกับตอม่อเดิม -0.30..+0.30) และคานคอดิน GB1 200x500 หลังคาน +0.20
# ต่อจากตอม่อ C1 กริด 10 แนว C, D มาชนตอม่อ F1 (ช่วงกริด 10–11)
for r in ('C', 'D'):
    add(f'F1-11{r}-ST', 'เสา', 1, 'DONE',
        prism([(GX11 - 0.30, GY[r] - 0.30), (GX11 + 0.30, GY[r] - 0.30), (GX11 + 0.30, GY[r] + 0.30), (GX11 - 0.30, GY[r] + 0.30)], FOOT_TOP, 0.60),
        name=f'ตอม่อ F1 0.60x0.60x0.60 กริด 11/{r} (บันไดหนีไฟ)', assumed=True, qty=dict(height=0.60, concrete=round(0.6 * 0.6 * 0.6, 4)))
    _x0, _x1 = GX[9] + COL_SEC[0][0] / 2, GX11 - 0.30
    add(f'GB1-10-11-{r}', 'คานคอดิน', 1, 'DONE', member((_x0, GY[r], 0.20 - 0.25), (_x1, GY[r], 0.20 - 0.25), 0.20, 0.50),
        name=f'GB1 กริด 10–11 แนว {r} (บันไดหนีไฟ)', assumed=True, qty=dict(length=round(_x1 - _x0, 3), concrete=round((_x1 - _x0) * 0.20 * 0.5, 4)))


# ---------- คานชั้น 2–5 และคานหลังคา ----------
def beams_level(lv, top, task, floor, with_b5=True, assumed=False, drop=0.0):
    """drop: ลดระดับหลังคานในแถบยื่น (B3, B4, B5) ใต้พื้นระเบียง/ห้องน้ำ"""
    sfx = f'L{lv}'
    for r in COL_ROWS:                  # B2 แนวยาว
        for i in range(9):
            c = top - 0.25
            L = 3.5 - COL_SEC[floor - 1][0]
            hw = COL_SEC[floor - 1][0] / 2
            add(f'B2-{r}{i+1}-{i+2}-{sfx}', 'คาน', floor, task,
                member((GX[i] + hw, GY[r] + B2_DY[r], c), (GX[i + 1] - hw, GY[r] + B2_DY[r], c), 0.25, 0.50),
                assumed=assumed, qty=dict(length=round(L, 3), concrete=round(L * 0.25 * 0.5, 4)))
    for i in range(10):                 # B1 แนวขวาง
        for a, b in (('B', 'C'), ('C', 'D'), ('D', 'E')):
            y0, y1 = GY[a] + 0.25, GY[b] - 0.25
            c = top - 0.25
            xb = GX[i] + edge_dx(i, 0.25, floor - 1)
            add(f'B1-{i+1}-{a}{b}-{sfx}', 'คาน', floor, task,
                member((xb, y0, c), (xb, y1, c), 0.25, 0.50), assumed=assumed,
                qty=dict(length=round(y1 - y0, 3), concrete=round((y1 - y0) * 0.25 * 0.5, 4)))
        for a, b in (('A', 'B'), ('E', 'F')):   # B3 ยื่น
            ya, yb = sorted((GY[a], GY[b]))
            # ปลายคาน B3 ด้านนอกเสมอขอบนอกคานริม B4 (แนวกริด A/F) (ผู้ใช้สั่ง 11 พ.ย. 2569)
            y0 = ya + (0.0 if a == 'A' else 0.25)
            y1 = yb - (0.25 if a == 'A' else 0.0)
            c = top - drop - 0.25
            xb = GX[i] + edge_dx(i, 0.25, floor - 1)
            add(f'B3-{i+1}-{a}{b}-{sfx}', 'คาน', floor, task,
                member((xb, y0, c), (xb, y1, c), 0.25, 0.50), assumed=assumed,
                qty=dict(length=round(y1 - y0, 3), concrete=round((y1 - y0) * 0.25 * 0.5, 4)))
    for r in ('A', 'F'):                # B4 ขอบ
        y = GY[r] + (0.10 if r == 'A' else -0.10)
        for i in range(9):
            c = top - drop - 0.20
            # ปลาย B4 ชนผิวข้างคาน B3 (B3 บนกริด 1, 10 เลื่อนออกนอกตาม edge_dx)
            bx0 = GX[i] + edge_dx(i, 0.25, floor - 1) + 0.125
            bx1 = GX[i + 1] + edge_dx(i + 1, 0.25, floor - 1) - 0.125
            L = round(bx1 - bx0, 4)
            add(f'B4-{r}{i+1}-{i+2}-{sfx}', 'คาน', floor, task,
                member((bx0, y, c), (bx1, y, c), 0.20, 0.40), assumed=assumed,
                qty=dict(length=L, concrete=round(L * 0.2 * 0.4, 4)))
    if with_b5:
        for j in range(len(B5_X)):    # B5 ยื่นซอย
            for a, b in (('A', 'B'), ('E', 'F')):
                x = b5x(j, 'N' if a == 'A' else 'S')
                ya, yb = sorted((GY[a], GY[b]))
                y0, y1 = ya + 0.20, yb - 0.125
                if a == 'E':
                    y0, y1 = ya + 0.125, yb - 0.20
                c = top - drop - 0.20
                add(f'B5-{j+1}-{a}{b}-{sfx}', 'คาน', floor, task,
                    member((x, y0, c), (x, y1, c), 0.15, 0.40), assumed=assumed,
                    qty=dict(length=round(y1 - y0, 3), concrete=round((y1 - y0) * 0.15 * 0.4, 4)))


for f in (2, 3, 4, 5):
    beams_level(f, FL[f] - SLAB_T, 'DONE', f, drop=DROP)
# ช่วงชานพักบันได (กริด 4–5 แถบยื่นด้านหน้า) ไม่มีคานขอบ B4 และคานซอย B5 ระดับพื้น
# และไม่มีคาน B2 แนว B ช่วงกริด 4–5 ระดับพื้น (ขวางทางเดินบนชานพัก) ใช้ BST1 ระดับชานพักแทน
_drop = {f'B4-A4-5-L{f}' for f in (2, 3, 4, 5)} | {f'B5-4-AB-L{f}' for f in (2, 3, 4, 5)} | {f'B2-B4-5-L{f}' for f in (2, 3, 4, 5)}
elements[:] = [e for e in elements if e['id'] not in _drop]
# ไม่มีคาน คสล. หลังคา (ผู้ใช้ยกเลิก 9 พ.ย. 2569): โครงเหล็กหลังคาวางบนหัวเสาและผนังที่ +16.30

# ---------- พื้น ----------
x_min, x_max = GX[0] - 0.175, GX[-1] + 0.175
# พื้นชั้น 1 หล่อในที่ หนา 0.10 เว้นหน้าเสา (ผู้ใช้สั่ง 11 พ.ย. 2569): เสาแนว B/E เป็นรอยบากที่ขอบพื้น เสาแนว C/D เป็นช่องในพื้น
_cw0, _cd0 = COL_SEC[0][0] / 2, COL_SEC[0][1] / 2


def _gs_edge(y, dy):
    """ขอบพื้นแนว y จาก x_min ไป x_max บากรอบเสา (ลึก dy เข้าในพื้น)"""
    pts = []
    for i in range(10):
        a, b = max(GX[i] - _cw0, x_min), min(GX[i] + _cw0, x_max)
        if a <= x_min + 1e-9:
            pts += [(x_min, y + dy), (b, y + dy), (b, y)]
        elif b >= x_max - 1e-9:
            pts += [(a, y), (a, y + dy), (x_max, y + dy)]
        else:
            pts += [(a, y), (a, y + dy), (b, y + dy), (b, y)]
    return pts


# เสาแนว C/D ที่กริด 1 และ 10 อยู่ชิดขอบพื้นด้านสกัด: เป็นรอยบากที่ขอบ ไม่ใช่ช่องใน
_xr, _xl = GX[-1] - _cw0, GX[0] + _cw0
_gs_right = [p for r in ('C', 'D') for p in ((x_max, GY[r] - _cd0), (_xr, GY[r] - _cd0), (_xr, GY[r] + _cd0), (x_max, GY[r] + _cd0))]
_gs_left = [p for r in ('D', 'C') for p in ((x_min, GY[r] + _cd0), (_xl, GY[r] + _cd0), (_xl, GY[r] - _cd0), (x_min, GY[r] - _cd0))]
_gs_poly = _gs_edge(GY['B'], _cd0) + _gs_right + _gs_edge(GY['E'], -_cd0)[::-1] + _gs_left
_gs_holes = [[(GX[i] - _cw0, GY[r] - _cd0), (GX[i] + _cw0, GY[r] - _cd0), (GX[i] + _cw0, GY[r] + _cd0), (GX[i] - _cw0, GY[r] + _cd0)]
             for i in range(1, 9) for r in ('C', 'D')]
_gs_geo = prism(_gs_poly, FL[1] - GS_T, GS_T)
_gs_geo['holes'] = [[[round(x, 4), round(y, 4)] for x, y in h] for h in _gs_holes]
_gs_area = (x_max - x_min) * (GY['E'] - GY['B']) - 20 * (2 * _cw0) * _cd0 - 20 * (2 * _cw0) * (2 * _cd0)   # หักรอยบากเสาขอบ 20 ต้น (ลึก cd) และช่องเสาใน 20 ต้น
add('GS-F1', 'พื้น', 1, 'DONE', _gs_geo,
    name='พื้นชั้น 1 หล่อในที่ หนา 0.10 (เว้นหน้าเสา)',
    qty=dict(area=round(_gs_area, 3), concrete=round(_gs_area * GS_T, 3), thickness=GS_T, type='พื้นหล่อในที่'))
sx0, sx1 = GX[STAIR_BAY[0]] + 0.125, GX[STAIR_BAY[1]] - 0.125   # ผิวคาน B1 กริด 4/5
sy0, sy1 = GY['B'] + 0.125, ST_RUN_Y1                            # ช่องเปิดบันได
STRIP_Y1 = GY['B'] - 0.125                                       # แถบยื่นช่วงชานพัก (ไม่มีพื้นระดับชั้น)


RM_EDGE = 0.05                                                   # ครึ่งผนัง 0.035 + ฉาบ 0.015
STRIP_N = GY['B'] - 0.125                                        # ขอบแถบยื่นด้านหน้า = ผิวคาน B2 แนว B
STRIP_S = GY['E'] + 0.125                                        # ขอบแถบยื่นด้านหลัง = ผิวคาน B2 แนว E


def _bx(i):
    """ขอบ x ของช่วงเสา i (ช่วงริมยื่นถึงขอบพื้น)"""
    return (x_min if i == 0 else GX[i]), (x_max if i == 8 else GX[i + 1])


def bay_split(i, side):
    """คืน (toilet_x0, toilet_x1, balcony_x0, balcony_x1) ของช่วงเสา i ฝั่ง side"""
    b5 = b5x(i, side)
    if abs(b5 - GX[i] - 1.5) < 1e-6:
        return b5, GX[i + 1], GX[i], b5
    return GX[i], b5, b5, GX[i + 1]


def slab_zones(f):
    """พื้นชั้น f แยกตามช่วงเสา: [(id_suffix, kind, rects, top)]
    kind: RM ห้องพัก/โถงบันได, COR ทางเดิน (แผ่นพื้น+ทับหน้า ผิวบน FL),
          BL ระเบียง (แผ่นพื้น+ทับหน้า), WC ห้องน้ำ (S1 หล่อในที่) ผิวบน FL - DROP"""
    z = []
    for i in range(9):
        xa, xb = _bx(i)
        clamp = lambda a, b: ((xa if a == GX[i] else a), (xb if b == GX[i + 1] else b))   # ช่วงริมยื่นถึงขอบพื้น
        for side in ('N', 'S'):
            tx0, tx1, bx0, bx1 = bay_split(i, side)
            # พื้นห้องพักวางทับหลังคาน B2 ถึงผิวผนังกั้นห้องน้ำ/ระเบียง (ขั้นลด 0.075 อยู่ที่แนวผนัง)
            ry = (GY['B'] - RM_EDGE, GY['C']) if side == 'N' else (GY['D'], GY['E'] + RM_EDGE)
            sy = (GY['A'], STRIP_N) if side == 'N' else (STRIP_S, GY['F'])
            if side == 'N' and i == STAIR_BAY[0]:     # โถงบันได: เว้นช่องบันได ไม่มีพื้นในแถบชานพัก
                r0 = STRIP_N                          # คงขอบเดิมของโถงบันได
                # ไม่มีแถบพื้นแนว B เหนือชานพัก (เดิมยื่นเข้าช่องบันได 0.25 ม. บังระยะหัวเหนือชานพัก, ผู้ใช้แจ้ง 10 พ.ย. 2569)
                rects = [(xa, sx0, r0, ry[1]), (sx1, xb, r0, ry[1]),
                         (sx0, sx1, sy1, ry[1])]
                z.append((f'{side}{i+1}-RM', 'RM', rects, FL[f]))
                continue
            z.append((f'{side}{i+1}-RM', 'RM', [(xa, xb, ry[0], ry[1])], FL[f]))
            t0, t1 = clamp(tx0, tx1)
            b0, b1 = clamp(bx0, bx1)
            z.append((f'{side}{i+1}-WC', 'WC', [(t0, t1, sy[0], sy[1])], FL[f] - DROP))
            z.append((f'{side}{i+1}-BL', 'BL', [(b0, b1, sy[0], sy[1])], FL[f] - DROP))
        z.append((f'COR{i+1}', 'COR', [(xa, xb, GY['C'], GY['D'])], FL[f]))
    return z


def rect_area(rects):
    return sum((b - a) * (d - c) for a, b, c, d in rects)


def rects_geom(rects, z0, t):
    parts = [prism([(a, c), (b, c), (b, d), (a, d)], z0, t) for a, b, c, d in rects if b - a > 1e-6 and d - c > 1e-6]
    return parts[0] if len(parts) == 1 else dict(type='multi', parts=parts)


def plank_qty(rects):
    """แผ่นพื้น 350 มม. พาดช่วงสั้นระหว่างคาน (ค่าสมมติ: แบบไม่ระบุทิศ): จำนวนแผ่น/ความยาว ต่อสี่เหลี่ยมย่อย"""
    n, runs = 0, []
    for a, b, c, d in rects:
        lx, ly = b - a, d - c
        span, width, dirn = (lx, ly, 'x') if lx <= ly else (ly, lx, 'y')
        k = math.ceil(round(width / PLANK_W, 6))
        n += k
        runs.append(f'{k} แผ่น ยาว {span:.2f} ม. พาดแนว {dirn}')
    return n, '; '.join(runs)


ASSUMPTIONS.append('แผ่นพื้นสำเร็จรูปท้องเรียบ 350x50 ทุกพื้นที่ (ห้องพัก โถงหน้าบันได ระเบียง ทางเดิน) พาดแนว x ทิศกริด 1→2 (ผู้ใช้สั่ง 11 พ.ย. 2569) ร่อง 3 มม. บากมุมชนเสา')
ASSUMPTIONS.append('พื้นระเบียงหลังห้องและห้องน้ำชั้น 2–5 ต่ำกว่าห้องพัก/ทางเดิน 0.075 ม.: หลังคาน B3/B4/B5 ในแถบยื่นลดลง 0.075 ม.; คาน B2 แนว B/E คงระดับเดิม พื้นห้องพักวางทับเต็มหลังคาน')

PLANK_BEAR = 0.05       # ระยะพาดแผ่นพื้นบนคาน 5 ซม. จากขอบคาน (ผู้ใช้สั่ง 11 พ.ย. 2569)
PLANK_EDGE_MAX = 0.025   # ช่องขนานคานจากการวางแผ่น ไม่เกิน 2.5 ซม. เททับหน้าปิด (ผู้ใช้สั่ง 11 พ.ย. 2569)
PLANK_GAP = 0.003       # ร่องระหว่างแผ่นพื้นสำเร็จรูป 3 มม. ทุกพื้นที่ (ผู้ใช้สั่ง 11 พ.ย. 2569 เดิม 5 มม.)


def planks_x(f, rects, top):
    """แผ่นพื้นสำเร็จรูปท้องเรียบกว้าง 0.35 หนา 0.05 พาดแนว x (ทิศกริด 1→2 ทุกแนว, ผู้ใช้สั่ง 11 พ.ย. 2569)
    วางเรียงแนว y เว้นร่อง 5 มม. แผ่นสุดท้ายตัดตามความกว้างที่เหลือ; ปลายแผ่นที่ชนเสาบากออกเสมอผิวเสา"""
    w, d = COL_SEC[f - 1]
    cols = [(GX[i] - w / 2, GX[i] + w / 2, GY[r] - d / 2, GY[r] + d / 2) for i in range(10) for r in COL_ROWS]
    if f == 5:                                   # เสา CX2 แนว A/F ตั้งบนหลังคานชั้น 5
        cols += [(GX[i] - 0.10, GX[i] + 0.10, ya_, yb_) for i in range(10) for ya_, yb_ in ((GY['A'], GY['A'] + 0.20), (GY['F'] - 0.20, GY['F']))]
    parts, n_cut, n_full, lens = [], 0, 0, []
    # คานรองรับปลายแผ่น (แนว y): B1/B3 บนกริด (กริด 1, 10 เลื่อนตาม edge_dx) กว้าง 0.25, B5 กว้าง 0.15
    sups = [(GX[i] + edge_dx(i, 0.25, f - 1), 0.125) for i in range(10)] + \
           [(b5x(j, sd), 0.075) for j in range(len(B5_X)) for sd in ('N', 'S')]

    def bear(xe, inward):
        """ปลายแผ่น: วางบนคานลึกจากขอบคาน PLANK_BEAR (ผู้ใช้สั่ง 11 พ.ย. 2569) inward=+1 ปลายซ้าย, -1 ปลายขวา"""
        c = [(abs(xc - xe), xc, hw) for xc, hw in sups if abs(xc - xe) <= hw + 0.011]
        if not c:
            return xe
        _, xc, hw = min(c)
        return xc + inward * hw - inward * PLANK_BEAR

    for x0, x1, y0, y1 in rects:
        if x1 - x0 < 0.30:                       # แถบแคบบนหลังคาน (ข้างช่องบันได) เทพร้อมคอนกรีตทับหน้า ไม่วางแผ่น
            continue
        x0, x1 = bear(x0, 1), bear(x1, -1)
        # ไม่วางแผ่นทับแนวคานแนว x (B2 แนวเสา, BST1 ขอบช่องบันได): เริ่ม/จบที่ผิวคาน (ผู้ใช้สั่ง 11 พ.ย. 2569)
        for lo_, hi_ in [(GY[r] + B2_DY[r] - 0.125, GY[r] + B2_DY[r] + 0.125) for r in COL_ROWS] + [(ST_RUN_Y1, ST_RUN_Y1 + 0.20)]:
            if lo_ - 1e-6 <= y0 < hi_ - 1e-6:
                y0 = hi_
            if lo_ + 1e-6 < y1 <= hi_ + 1e-6:
                y1 = lo_
        # ใช้เฉพาะแผ่นเต็มกว้าง 0.35 ม. ร่อง 3 มม. (ผู้ใช้สั่ง 11 พ.ย. 2569)
        # ช่องขนานคานเหลือได้ไม่เกิน PLANK_EDGE_MAX (เททับหน้าปิด); ถ้าเกิน เพิ่ม 1 แผ่นแล้ววางกึ่งกลาง ขอบแผ่นริมวางบนหลังคานเท่ากันสองข้าง
        k = int((y1 - y0 + PLANK_GAP) // (PLANK_W + PLANK_GAP) + 1e-9)
        left = (y1 - y0) - (k * PLANK_W + (k - 1) * PLANK_GAP)
        if left / 2 > PLANK_EDGE_MAX + 1e-6:          # วางกึ่งกลาง ช่องสองข้างเท่ากัน ข้างละ left/2
            k += 1
            left = (y1 - y0) - (k * PLANK_W + (k - 1) * PLANK_GAP)
        ys = [(y0 + left / 2 + j * (PLANK_W + PLANK_GAP), y0 + left / 2 + j * (PLANK_W + PLANK_GAP) + PLANK_W) for j in range(k)]
        for py0, py1 in ys:
            hit = [c for c in cols if min(py1, c[3]) - max(py0, c[2]) > 1e-6 and min(x1, c[1]) - max(x0, c[0]) > 1e-6]
            brk = sorted({py0, py1} | {v for c in hit for v in (c[2], c[3]) if py0 < v < py1})
            segs = []
            for a, b in zip(brk, brk[1:]):
                m = (a + b) / 2
                xm = (x0 + x1) / 2                   # เสาใกล้ปลายไหนบากปลายนั้น (รวมเสาที่อยู่ในช่วงปลายแผ่น เช่น CX2 ที่มุมอาคาร)
                xl = max([x0] + [c[1] for c in hit if c[2] < m < c[3] and (c[0] + c[1]) / 2 < xm])
                xr = min([x1] + [c[0] for c in hit if c[2] < m < c[3] and (c[0] + c[1]) / 2 >= xm])
                segs.append((a, b, xl, xr))
            if any(xr - xl < 0.02 for _, _, xl, xr in segs):
                segs = [sg for sg in segs if sg[3] - sg[2] >= 0.02]
                if not segs:
                    continue
            pts = []
            for a, b, xl, xr in segs:
                pts += [(xr, a), (xr, b)]
            for a, b, xl, xr in reversed(segs):
                pts += [(xl, b), (xl, a)]
            dd = []
            for p in pts:
                if not dd or abs(p[0] - dd[-1][0]) > 1e-6 or abs(p[1] - dd[-1][1]) > 1e-6:
                    dd.append(p)
            if len(dd) > 1 and abs(dd[0][0] - dd[-1][0]) < 1e-6 and abs(dd[0][1] - dd[-1][1]) < 1e-6:
                dd.pop()
            cl = []                                  # ตัดจุดกลางเส้นตรง
            for k, p in enumerate(dd):
                a_, c_ = dd[k - 1], dd[(k + 1) % len(dd)]
                if abs((p[0] - a_[0]) * (c_[1] - p[1]) - (p[1] - a_[1]) * (c_[0] - p[0])) > 1e-9:
                    cl.append(p)
            parts.append(prism(cl, top - SLAB_T, 0.05))
            notched = len(cl) > 4
            full = abs((py1 - py0) - PLANK_W) < 1e-6
            n_full += full
            n_cut += (notched or not full)
            lens.append(round(x1 - x0, 2))
    qc = dict(planks=len(parts), planks_full_width=n_full, planks_cut=n_cut, plank_size='กว้าง 0.35 หนา 0.05 ม. ท้องเรียบ',
              plank_length=max(lens) if lens else 0, gap_mm=round(PLANK_GAP * 1000),
              plank_layout=f'{len(parts)} แผ่น ยาว {"/".join(f"{v:.2f}" for v in sorted(set(lens)))} ม. พาดแนว x (กริด 1→2) (กว้างเต็ม {n_full}; ตัดกว้าง/บากชนเสา {n_cut})')
    return (parts[0] if len(parts) == 1 else dict(type='multi', parts=parts)), qc


def cor_planks(f, sfx, rect, top):
    """แผ่นพื้นสำเร็จรูปท้องเรียบกว้าง 0.35 หนา 0.05 พาดแนว y (C–D) วางเรียงแนว x เว้นร่อง 5 มม.
    แผ่นสุดท้ายของช่วงตัดตามความกว้างที่เหลือ; ส่วนที่ชนเสา (หน้าตัดเสาชั้นล่าง f-1) ตัดออกเสมอผิวเสา"""
    x0, x1, y0, y1 = rect
    w, d = COL_SEC[f - 1]
    cols = [(GX[i] - w / 2, GX[i] + w / 2, GY[r] - d / 2, GY[r] + d / 2) for i in range(10) for r in ('C', 'D')]
    last_bay = sfx == 'COR9'
    xs, x = [], x0
    while x < x1 - 1e-6:
        room = x1 - x - (0.0 if last_bay else PLANK_GAP)
        if room < 0.02:
            break
        pw = min(PLANK_W, room)
        xs.append((x, x + pw))
        x += pw + PLANK_GAP
    parts, n_cut, lens = [], 0, []
    for px0, px1 in xs:
        lo_pts, hi_pts = [(px0, y0), (px1, y0)], [(px1, y1), (px0, y1)]
        cut = pw_cut = abs((px1 - px0) - PLANK_W) > 1e-6
        for cx0, cx1, cy0, cy1 in cols:
            ox0, ox1 = max(px0, cx0), min(px1, cx1)
            if ox1 - ox0 < 1e-6:
                continue
            if cy0 < y0 < cy1:       # เสาแนว C: บากปลายด้าน y0
                yd, chain, fwd = cy1, lo_pts, True
            elif cy0 < y1 < cy1:     # เสาแนว D: บากปลายด้าน y1
                yd, chain, fwd = cy0, hi_pts, False
            else:
                continue
            cut = True
            ye = chain[0][1]
            a, b = (ox0, ox1) if fwd else (ox1, ox0)
            pts = [chain[0]]
            if (a > px0 + 1e-6) if fwd else (a < px1 - 1e-6):
                pts += [(a, ye)]
            else:
                pts = []
            pts += [(a, yd), (b, yd)]
            if (b < px1 - 1e-6) if fwd else (b > px0 + 1e-6):
                pts += [(b, ye), chain[-1]]
            chain[:] = pts
        poly = lo_pts + hi_pts
        dedup = [p for k, p in enumerate(poly) if k == 0 or (abs(p[0] - poly[k - 1][0]) > 1e-6 or abs(p[1] - poly[k - 1][1]) > 1e-6)]
        parts.append(prism(dedup, top - SLAB_T, 0.05))
        n_cut += cut
        lens.append(round(px1 - px0, 3))
    full = sum(1 for L in lens if abs(L - PLANK_W) < 1e-6)
    qc = dict(planks=len(parts), planks_full_width=full, planks_cut=n_cut, plank_size='กว้าง 0.35 หนา 0.05 ม. ท้องเรียบ',
              plank_length=round(y1 - y0, 3), gap_mm=round(PLANK_GAP * 1000),
              plank_layout=f'{len(parts)} แผ่น ยาว {y1 - y0:.2f} ม. พาดแนว y (กว้างเต็ม {full}, ตัดกว้าง {len(parts) - full}; บาก/ตัดชนเสา {n_cut})')
    return (parts[0] if len(parts) == 1 else dict(type='multi', parts=parts)), qc


SLAB_ZONES = {f: slab_zones(f) for f in (2, 3, 4, 5)}
for f in (2, 3, 4, 5):
    for sfx, kind, rects, top in SLAB_ZONES[f]:
        A = round(rect_area(rects), 3)
        where = {'RM': 'ห้องพัก' if not sfx.startswith('N4') else 'โถงบันได', 'COR': 'ทางเดิน', 'BL': 'ระเบียง', 'WC': 'ห้องน้ำ'}[kind]
        if kind in ('WC', 'BL'):   # ห้องน้ำและระเบียงหลังห้อง: พื้นเทในที่ S1 (ระเบียงผู้ใช้สั่ง 11 พ.ย. 2569)
            add(f'S1-F{f}-{sfx}', 'พื้น', f, 'DONE', rects_geom(rects, top - S1_T, S1_T),
                name=f'พื้นหล่อในที่ S1 หนา 0.10 {where} ชั้น {f} {sfx[:-3]} (ต่ำกว่าพื้นห้อง 0.075)',
                qty=dict(area=A, concrete=round(A * S1_T, 4), thickness=S1_T, top_level=round(top, 3)))
            continue
        # ห้องพัก โถงหน้าบันได ระเบียง ทางเดิน: แผ่นพื้นสำเร็จรูปท้องเรียบรายแผ่น พาดแนว x (กริด 1→2) ทุกแนว (ผู้ใช้สั่ง 11 พ.ย. 2569)
        geo, qc = planks_x(f, rects, top)
        lvl = '' if kind in ('RM', 'COR') else ' (ต่ำกว่าพื้นห้อง 0.075)'
        add(f'PS-F{f}-{sfx}', 'พื้นสำเร็จรูป', f, 'DONE', geo,
            name=f'แผ่นพื้นสำเร็จรูปท้องเรียบ 0.35 ม. {where} ชั้น {f} {sfx} (พาดแนวกริด 1→2 ร่อง 3 มม. บากมุมชนเสา){lvl}', assumed=True,
            qty=dict(area=A, top_level=round(top - 0.05, 3), **qc))
        add(f'TP-F{f}-{sfx}', 'พื้นทับหน้า', f, 'DONE', rects_geom(rects, top - 0.05, 0.05),
            name=f'คอนกรีตทับหน้า {where} ชั้น {f} {sfx} หนา 0.05{lvl}',
            qty=dict(area=A, concrete=round(A * 0.05, 4), top_level=round(top, 3)))

# ---------- บันไดหลัก (A-05) ----------
ST_T = 0.12
RISER, TREAD, NSTEP = 0.16, 0.30, 9
FX0, FX1 = GX[3] + 0.05, GX[3] + 0.05 + 1.50       # ช่วงที่ 1 (ฝั่งกริด 4) ขึ้นไปทางด้านหน้า
GX0, GX1 = FX1 + 0.40, FX1 + 0.40 + 1.50           # ช่วงที่ 2 (ฝั่งกริด 5) กลับเข้าด้านใน
LY0, LY1 = GY['A'] + 0.15, GY['B']                 # ชานพัก
ASSUMPTIONS.append('บันไดหลักชั้น 4→5 ใช้รูปแบบเดียวกับชั้น 1→2 (A-05 แสดงชั้น 1–2)')


LAND_T = RISER                                   # ชานพักหนาเท่าลูกตั้ง ให้ท้องชานพักต่อกับขั้นสุดท้าย


def flight(x0, x1, y_start, direction, z_start, z_base=None):
    """ช่วงบันไดเป็นชิ้นตันชิ้นเดียว: รูปตัดด้านข้าง (ขั้นบันไดจริง + ท้องบันไดหนา ST_T) ยืดตามแกน x"""
    d = direction
    zb = z_start if z_base is None else z_base                  # ระดับฐานช่วงบันได (ช่วง 2 ลงถึงท้องชานพัก)
    pts = [(y_start, zb), (y_start, z_start)] if zb < z_start else [(y_start, z_start)]
    for k in range(NSTEP):
        y = y_start + d * k * TREAD
        pts.append((y, z_start + (k + 1) * RISER))
        pts.append((y + d * TREAD, z_start + (k + 1) * RISER))
    y_top = y_start + d * NSTEP * TREAD
    # ลูกตั้งสุดท้ายคือขอบชานพัก/ขอบพื้นชั้นบน
    cos = TREAD / math.hypot(TREAD, RISER)
    dv = ST_T / cos                                              # ความหนาท้องบันไดแนวดิ่ง
    pts.append((y_top, z_start + NSTEP * RISER - dv))
    pts.append((y_start + d * (dv - (z_start - zb)) * TREAD / RISER, zb))
    poly = [[round(y, 4), round(z, 4)] for y, z in pts]
    area = abs(sum(poly[i][0] * poly[(i + 1) % len(poly)][1] - poly[(i + 1) % len(poly)][0] * poly[i][1] for i in range(len(poly)))) / 2
    return dict(type='xprofile', x0=round(x0, 4), x1=round(x1, 4), poly=poly, component='บันได คสล. กว้าง 1.50 ลูกตั้ง 0.16 ลูกนอน 0.30'), round(area * (x1 - x0), 3)


for f in (1, 2, 3, 4):
    z0 = FL[f]
    zm = z0 + 10 * RISER
    g, c = flight(FX0, FX1, ST_RUN_Y1, -1, z0)
    add(f'ST-F{f}-1', 'บันได', f, 'DONE', g, name=f'บันไดหลักชั้น {f}→{f+1} ช่วง 1 (ลูกตั้ง 1–10)',
        qty=dict(width=1.50, risers=10, treads=NSTEP, concrete=c))
    add(f'ST-F{f}-L', 'บันได', f, 'DONE', prism([(FX0, LY0), (GX1, LY0), (GX1, LY1), (FX0, LY1)], zm - ST_T, ST_T),
        name=f'ชานพักบันไดชั้น {f} (S2) ระดับ +{zm:.2f}', assumed=True,
        qty=dict(area=round((GX1 - FX0) * (LY1 - LY0), 3), concrete=round((GX1 - FX0) * (LY1 - LY0) * LAND_T, 3)))
    g, c = flight(GX0, GX1, LY1, +1, zm, zm - LAND_T)
    add(f'ST-F{f}-2', 'บันได', f, 'DONE', g, name=f'บันไดหลักชั้น {f}→{f+1} ช่วง 2 (ลูกตั้ง 11–20)',
        qty=dict(width=1.50, risers=10, treads=NSTEP, concrete=c))
    # คานชานพัก BST3 (ขอบนอก) และ BST2 (กริด 4, 5) ระดับชานพัก
    zc = zm - 0.20
    # ปลายชนผิวฉาบข้างคาน BST2 (เดิมเว้น 2.5 ซม. ตามเสา C1 ทำให้เป็นช่องแสง, ผู้ใช้แจ้ง 11 พ.ย. 2569)
    add(f'BST3-M{f}', 'คาน', f, 'DONE', member((GX[3] + 0.105, GY['A'] + 0.10, zc), (GX[4] - 0.105, GY['A'] + 0.10, zc), 0.20, 0.40),
        name=f'BST3 คานชานพักชั้น {f}', qty=dict(length=3.29, concrete=round(3.29 * 0.2 * 0.4, 4)))
    # BST1 แนว B เลื่อนไปทางแนว A 0.10 ให้ผิวคานเสมอขอบชานพัก ไม่โผล่เหนือขั้นบนสุดช่วง 1 (ผู้ใช้เลือก 11 พ.ย. 2569)
    add(f'BST1-B-M{f}', 'คาน', f, 'DONE', member((sx0, GY['B'] - 0.10, zc), (sx1, GY['B'] - 0.10, zc), 0.20, 0.40),
        name=f'BST1 คานขอบชานพักแนว B ชั้น {f}', qty=dict(length=round(sx1 - sx0, 3), concrete=round((sx1 - sx0) * 0.08, 4)))
    for k in (3, 4):
        add(f'BST2-{k+1}-M{f}', 'คาน', f, 'DONE', member((GX[k], GY['A'], zc), (GX[k], GY['B'] - 0.25, zc), 0.20, 0.40),   # ปลายนอกเสมอขอบนอก BST3 (แนว A) (ผู้ใช้สั่ง 11 พ.ย. 2569)
            name=f'BST2 คานชานพักกริด {k+1} ชั้น {f}', qty=dict(length=1.40, concrete=round(1.4 * 0.2 * 0.4, 4)))
# เสา CX 200x200 รับปลายคาน BST2 (กริด 4, 5 แนว A) (ผู้ใช้สั่ง 11 พ.ย. 2569): ต่อเป็นช่วงจากคานชานพักแต่ละชั้น
# ช่วงล่างสุดเริ่มระดับหัวตอม่อ (FOOT_TOP) เหมือนเสาอื่น; ช่วงบนสุดจบใต้ BST2 ชั้น 4 (ไม่มีชานพักชั้น 5)
_zms = [FL[f] + 10 * RISER for f in (1, 2, 3, 4)]
# ช่วงที่ผ่านระดับพื้นชั้น 2–4 แบ่งเป็นสองท่อนที่คาน B3 (คาน B3 ยาวต่อเนื่องถึงแนว A ตามที่แก้ไว้)
_b3z = {(e['id'].split('-')[1], e['id'].split('-')[3]): (e['geom']['p0'][2] - e['geom']['d'] / 2, e['geom']['p0'][2] + e['geom']['d'] / 2)
        for e in elements if re.match(r'^B3-\d+-AB-L\d$', e['id'])}
for k in (3, 4):
    for j, zm in enumerate(_zms):
        za = FOOT_TOP if j == 0 else _zms[j - 1]
        zb = zm - 0.40
        segs = [(za, zb, '')]
        b3 = _b3z.get((str(k + 1), f'L{j + 1}'))
        if j > 0 and b3 and za < b3[0] < zb:
            segs = [(za, b3[0], 'a'), (b3[1], zb, 'b')]
        for z0_, z1_, sx in segs:
            add(f'CX-{k+1}A-M{j+1}{sx}', 'เสา', j + 1, 'DONE',
                prism([(GX[k] - 0.10, GY['A']), (GX[k] + 0.10, GY['A']), (GX[k] + 0.10, GY['A'] + 0.20), (GX[k] - 0.10, GY['A'] + 0.20)], z0_, round(z1_ - z0_, 3)),
                name=f'CX 200x200 รับปลายคาน BST2 กริด {k+1} ใต้ชานพักชั้น {j+1}' + ({'a': ' ท่อนล่าง (ใต้คาน B3)', 'b': ' ท่อนบน (เหนือคาน B3)'}.get(sx, '')), assumed=True,
                qty=dict(height=round(z1_ - z0_, 3), concrete=round(0.04 * (z1_ - z0_), 4), section='0.20x0.20'))
# ช่วงต่อเพิ่ม (ผู้ใช้สั่ง 11 พ.ย. 2569): จากหลังคานชานพักชั้น 4 ขึ้นไปใต้คาน B3 ชั้น 5 (แนว A)
for k in (3, 4):
    z0_ = _zms[-1]
    z1_ = _b3z[(str(k + 1), 'L5')][0]
    add(f'CX-{k+1}A-M5', 'เสา', 4, 'DONE',
        prism([(GX[k] - 0.10, GY['A']), (GX[k] + 0.10, GY['A']), (GX[k] + 0.10, GY['A'] + 0.20), (GX[k] - 0.10, GY['A'] + 0.20)], z0_, round(z1_ - z0_, 3)),
        name=f'CX 200x200 กริด {k+1} จากชานพักชั้น 4 ถึงใต้คาน B3 ชั้น 5', assumed=True,
        qty=dict(height=round(z1_ - z0_, 3), concrete=round(0.04 * (z1_ - z0_), 4), section='0.20x0.20'))
# เสา CX2 200x200 ชั้น 5 แนว A และ F ทุกกริด 1–10 (ผู้ใช้สั่ง 11 พ.ย. 2569): รับโครงหลังคา ขึ้นถึงระดับเดียวกับเสาอาคาร (+16.30)
# ผิวนอกเสาเสมอแนวกริด A/F และขอบนอกคาน B4; ตั้งบนหลังคาน B3/B4 ชั้น 5 (แถบยื่นลดระดับ DROP)
_zcx2 = FL[5] - SLAB_T - DROP
for r, (ya_, yb_) in (('A', (GY['A'], GY['A'] + 0.20)), ('F', (GY['F'] - 0.20, GY['F']))):
    for i in range(10):
        add(f'CX2-{i+1}{r}-F5', 'เสา', 5, 'A01',
            prism([(GX[i] - 0.10, ya_), (GX[i] + 0.10, ya_), (GX[i] + 0.10, yb_), (GX[i] - 0.10, yb_)], _zcx2, round(ROOF_BEAM - _zcx2, 3)),
            name=f'CX2 200x200 ชั้น 5 กริด {i+1}/{r} รับโครงหลังคา', assumed=True,
            qty=dict(height=round(ROOF_BEAM - _zcx2, 3), concrete=round(0.04 * (ROOF_BEAM - _zcx2), 4), section='0.20x0.20'))
# คานรับแม่บันไดชั้น 1 เป็นคานคอดิน GB1 200x500 (เพิ่มจากแบบ ผู้ใช้สั่ง 11 พ.ย. 2569): ใต้ปลายล่างช่วงบันได 1
# พาดแนว x ระหว่างคานคอดิน GB1 กริด 4–5, ขอบหน้าคานเสมอลูกตั้งแรก (y = ST_RUN_Y1), หลังคานเสมอหลังคานคอดิน (+0.20) ใต้พื้น GS
_L = (GX[4] - 0.10) - (GX[3] + 0.10)
add('GB1-ST', 'คานคอดิน', 1, 'DONE', member((GX[3] + 0.10, ST_RUN_Y1 - 0.10, 0.20 - 0.25), (GX[4] - 0.10, ST_RUN_Y1 - 0.10, 0.20 - 0.25), 0.20, 0.50),
    name='GB1 คานรับแม่บันไดชั้น 1 (เพิ่มจากแบบ)', assumed=True, qty=dict(length=round(_L, 3), concrete=round(_L * 0.20 * 0.5, 4)))
for f in (2, 3, 4, 5):                             # BST1 ขอบช่องเปิดบันไดระดับพื้น
    c = FL[f] - SLAB_T - 0.20
    add(f'BST1-L{f}', 'คาน', f, 'DONE', member((sx0, ST_RUN_Y1 + 0.10, c), (sx1, ST_RUN_Y1 + 0.10, c), 0.20, 0.40),
        name=f'BST1 คานขอบช่องบันไดชั้น {f}', qty=dict(length=round(sx1 - sx0, 3), concrete=round((sx1 - sx0) * 0.08, 4)))

# ---------- ราวบันไดหลัก + ราวกันตกโถงบันไดชั้น 5 (ผู้ใช้กำหนด 10 พ.ย. 2569) ----------
# เหล็กทาสีดำ: แต่ละช่วงบันได (พื้น→ชานพัก, ชานพัก→พื้น) มีเสา 4 ต้น, ราวเหล็กกลม 3 แนว ราวบนสูง 1.20 จากลูกนอนที่ตั้งเสา
# ราวต่อเนื่องตามแนวช่องว่างระหว่างช่วงบันได 0.40 ม. ตั้งแต่ชั้น 1 ถึงชั้น 5 แล้วต่อเป็นราวกันตกขอบช่องบันไดชั้น 5
RAIL_H = (0.40, 0.80, 1.20)                   # ระดับราว 3 แนว จากลูกนอน/พื้นที่ตั้งเสา (ราวล่าง 2 แนวแบ่งเท่า: ค่าสมมติ)
RAIL_D = 0.038                                # ราวเหล็กกลม Ø 1-1/2" (ค่าสมมติ)
POST_W, POST_D = 0.025, 0.050                 # เสาเหล็กกล่อง 1"x2" (A-05)
POST_K = (0, 3, 5, 8)                         # ลูกนอนที่ตั้งเสา (ขั้นที่ 1, 4, 6, 9)
RX1, RX2 = FX1 - 0.05, GX0 + 0.05             # แนวเสาริมช่องว่างของช่วง 1 และช่วง 2
ASSUMPTIONS.append('ราวบันได: เสาเหล็กกล่อง 1"x2" ตาม A-05, ราวเหล็กกลม Ø 1-1/2" 3 แนวที่ 0.40/0.80/1.20 ม. จากลูกนอน (ผู้ใช้กำหนดราวบน 1.20 และจำนวน 4 เสา/3 ราว ต่อช่วง), ตั้งเสาห่างขอบช่วงบันไดด้านช่องว่าง 0.05 ม., ผูกกับกิจกรรม A18 เพราะแผนไม่มีรายการราวบันได')


def rail_pts():
    """จุดตั้งเสาต่อเนื่องจากชั้น 1 ถึงชั้น 5: [(floor, flight_tag, [(x, y, z_base), ...])]"""
    out = []
    for f in (1, 2, 3, 4):
        z0, zm = FL[f], FL[f] + 10 * RISER
        out.append((f, f'F{f}-1', [(RX1, ST_RUN_Y1 - k * TREAD - TREAD / 2, z0 + (k + 1) * RISER) for k in POST_K]))
        out.append((f, f'F{f}-2', [(RX2, LY1 + k * TREAD + TREAD / 2, zm + (k + 1) * RISER) for k in POST_K]))
    yg = ST_RUN_Y1 + 0.05                        # ราวกันตกชั้น 5 บนขอบพื้นริมช่องบันได
    xw = GX[3] + 0.035 + 0.015 + 0.03            # ชิดผิวฉาบผนังกริด 4 (ครึ่งบล็อก 0.035 + ฉาบ 0.015)
    out.append((5, 'F5-G', [(RX2, yg, FL[5]), ((RX2 + xw) / 2, yg, FL[5]), (xw, yg, FL[5])]))
    return out


def round_bar(p0, p1):
    return dict(type='member', p0=[round(v, 4) for v in p0], p1=[round(v, 4) for v in p1], w=RAIL_D, d=RAIL_D,
                shape='O', sec=dict(d=RAIL_D))


_runs = rail_pts()
_prev = None
for f, tag, pts in _runs:
    posts = [member((x, y, z), (x, y, z + RAIL_H[-1]), POST_W, POST_D) for x, y, z in pts]
    rails = []
    seq = ([_prev] if _prev else []) + pts       # เชื่อมจากเสาต้นสุดท้ายของช่วงก่อนหน้า (ราวต่อเนื่อง)
    for h in RAIL_H:
        for (xa, ya, za), (xb, yb, zb) in zip(seq, seq[1:]):
            rails.append(round_bar((xa, ya, za + h), (xb, yb, zb + h)))
    L = sum(math.dist(r['p0'], r['p1']) for r in rails)
    kind = 'ราวกันตกขอบช่องบันได' if tag.endswith('-G') else 'ราวบันได'
    add(f'RL-{tag}', 'ราวบันได', f, 'A18', dict(type='multi', parts=posts + rails),
        name=f'{kind} {tag} เหล็กทาสีดำ (เสา {len(posts)} ต้น ราวกลม 3 แนว สูง 1.20)', assumed=True,
        qty=dict(posts=len(posts), post_section='เหล็กกล่อง 1"x2"', post_length=round(len(posts) * RAIL_H[-1], 3),
                 rail_section='เหล็กกลม Ø 1-1/2"', rail_length=round(L, 3), finish='ทาสีกันสนิม + สีดำ'))
    _prev = pts[-1]


# ---------- หลังคา (S106 ผังโครงหลังคา, S107 รูปตัดด้านสั้น) ----------
# หน้าตัดเหล็ก (มอก. เหล็กรูปพรรณขึ้นรูปเย็น) h, b, c, t (ม.) และน้ำหนัก กก./ม. ต่อตัว
STEEL = {'C125': dict(h=0.125, b=0.05, c=0.02, t=0.0032, kg=6.13),
         'C100': dict(h=0.100, b=0.05, c=0.02, t=0.0032, kg=5.50)}
# ชั้นวัสดุใต้ผิวหลังคา (วัดจากผิวบนหลังคา zroof ลงมา)
SKIN_T, PURLIN_T = 0.03, 0.04            # แผ่นหลังคา, แปเหล็กกัลวาไนซ์ (สูง 0.04 ค่าสมมติ)
STACK_T = SKIN_T + PURLIN_T              # กระเบื้อง + แป วัดตั้งฉากกับลาดหลังคา
# RAF_TOP/RAF_C/RAF_BOT (ระยะดิ่งจากผิวหลังคา) คำนวณหลังได้ความลาด: ซ้อนชั้นตั้งฉากกับลาด (ผู้ใช้สั่ง 11 พ.ย. 2569)
WP_Y = 0.10                              # แนวอะเสจากขอบคาน
OV_SIDE, OV_END = 1.195, 1.33
yc = GY['CX']
# ระนาบหลังคา: ท้องจันทันวางบนอะเส (หลังอะเส = +16.30 + 0.125) และผิวบนที่สันหลังคา = +20.00
BASE_PL_T = 0.012                        # เพลทหัวเสา PL12x200x200 (ผู้ใช้กำหนด)
RB = ROOF_BEAM + BASE_PL_T               # ท้องโครงเหล็กหลังคา (บนเพลทหัวเสา)
# ความลาด: ท้องจันทัน (หน้าตัดตั้งฉากกับลาด) แตะหลังอะเสที่ขอบนอกอะเสพอดี และผิวบนที่สัน = RIDGE
slope = 0.45
for _ in range(60):
    slope = (RIDGE - (RB + 0.125) - (STACK_T + 0.10) * math.sqrt(1 + slope * slope)) / (yc - (GY['A'] + WP_Y - 0.05))
_SEC = math.sqrt(1 + slope * slope)
RAF_TOP = STACK_T * _SEC                 # หลังจันทัน (ระยะดิ่งใต้ผิวหลังคา) = ท้องแป
RAF_C = (STACK_T + 0.05) * _SEC          # แกนจันทัน C100
RAF_BOT = (STACK_T + 0.10) * _SEC        # ท้องจันทัน
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


def zface(face, x, y):
    """ผิวบนหลังคาแต่ละด้าน (ระนาบ) A/F ด้านยาว, 1/10 ด้านสกัด"""
    return {'A': RIDGE - (yc - y) * slope, 'F': RIDGE - (y - yc) * slope,
            '1': RIDGE - (rx0 - x) * slope, '10': RIDGE - (x - rx1) * slope}[face]


def _sub(a, b): return tuple(p - q for p, q in zip(a, b))
def _dot(a, b): return sum(p * q for p, q in zip(a, b))
def _unit(a):
    n = math.sqrt(_dot(a, a)); return tuple(p / n for p in a)
def _cross(a, b): return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def cut(pt, n):
    """ระนาบตัดปลายชิ้น (จุด, เวกเตอร์ตั้งฉาก) สำหรับ Profile Builder trim_to_plane"""
    return [round(v, 5) for v in (*pt, *_unit(n))]


def _on_plane(p0, p1, c):
    """จุดที่แกนชิ้น p0→p1 ตัดระนาบ c"""
    u = _sub(p1, p0); n = c[3:]; t = _dot(_sub(c[:3], p0), n) / _dot(u, n)
    return tuple(a + t * b for a, b in zip(p0, u))


def steel(eid, p0, p1, sec, double, name, mark, cuts=(None, None), segs=None):
    """ชิ้นส่วนเหล็กรูปตัวซี (สร้างด้วย Profile Builder): double=True คือ 2C ประกบปากชนกันเป็นกล่อง
    cuts = (ระนาบตัดปลายต้น, ระนาบตัดปลายท้าย) ตัด/ยืดปลายให้ผิวชนผิวชิ้นที่รองรับพอดี ไม่ทะลุกัน (ผู้ใช้สั่ง 11 พ.ย. 2569)
    segs = [(p0, p1, cuts), ...] ชิ้นที่แบ่งเป็นท่อน (เช่น ขื่อทางยาวตัดชนขื่อด้านสั้น)"""
    sp = STEEL[sec]
    parts, L = [], 0.0
    for a, b, (c0, c1) in (segs or [(p0, p1, cuts)]):
        q0 = _on_plane(a, b, c0) if c0 else a
        q1 = _on_plane(a, b, c1) if c1 else b
        g = member(q0, q1, 2 * sp['b'] if double else sp['b'], sp['h'])
        g['shape'] = '2C' if double else 'C'
        g['sec'] = {k: sp[k] for k in ('h', 'b', 'c', 't')}
        if c0 or c1:
            g['trim'] = [c0, c1]
        parts.append(g)
        L += mlen(q0, q1)
    secname = f"{'2' if double else ''}{sec}x50x20x3.2"
    add(eid, 'โครงหลังคาเหล็ก', 5, 'A03.2', parts[0] if len(parts) == 1 else dict(type='multi', parts=parts),
        name=f'{mark} {name} {secname}',
        qty=dict(length=round(L, 3), section=secname, mark=mark, pieces=len(parts),
                 weight_kg=round(L * sp['kg'] * (2 if double else 1), 2)))


ZB = RB + 0.0625                             # แกนขื่อ/อะเส 2C125 วางบนเพลทหัวเสา
ZB_TOP = RB + 0.125
ZA = RB + 0.05                               # แกนขื่อทางยาว 2C100
ZA_TOP = RB + 0.10
Y_MID_N, Y_MID_S = GY['B'] + 2.55, GY['E'] - 2.55       # เสารับจันทันกลางช่วง (S107)
Y_HIP_N = yc - (rx0 - GX[1])                  # แนวสะพานช่วงตะเข้ (ตรงกับระยะ 550 ใน S106)
Y_HIP_S = yc + (rx0 - GX[1])
X_E0, X_E1 = GX[1], GX[8]                     # สะพานรับจันทันพรางด้านสกัด กริด 2 และ 9
HB = 0.05                                     # ครึ่งความกว้าง 2C (กล่อง 100 มม.)
HIP_DROP = slope * HB / math.sqrt(2)          # ลดตะเข้ให้ขอบหลังตะเข้แตะระนาบหลังจันทันทั้งสองด้าน
XP, YP, ZP = (1, 0, 0), (0, 1, 0), (0, 0, 1)
FASCIA_T, FASCIA_H = 0.016, 0.23              # เชิงชาย DURAONE Fascia 23x300x1.6 ซม. (ผู้ใช้กำหนด 11 พ.ย. 2569) ผิวนอกอยู่บนแนวชายคา
FI = FASCIA_T                                 # ปลายจันทัน/ตะเข้ตัดชนผิวด้านในเชิงชาย

# ตะเข้สัน: มุมชายคา → ปลายสัน (แปลน 45°)
HIPS = {1: ((ex0, ey0), (rx0, yc), 'A'), 2: ((ex1, ey0), (rx1, yc), 'A'),
        3: ((ex1, ey1), (rx1, yc), 'F'), 4: ((ex0, ey1), (rx0, yc), 'F')}


def hip_frame(k):
    (cx, cy), (qx, qy), face = HIPS[k]
    d = _unit((qx - cx, qy - cy, 0))
    u = _unit((d[0], d[1], slope / math.sqrt(2)))
    s = _unit(_cross(u, ZP)); t = _unit(_cross(s, u))
    return (cx, cy), (qx, qy), face, d, u, s, t


def hip_top(k, x, y):
    """จุดบนแนวกึ่งกลางหลังตะเข้ (แปลน x,y อยู่บนแนวตะเข้)"""
    face = HIPS[k][2]
    return (x, y, zface(face, x, y) - RAF_TOP - HIP_DROP)


def hip_side(k, toward):
    """ระนาบผิวข้างตะเข้ k (ดิ่ง) ด้านที่หันเข้าหาจุด toward (x, y)"""
    (cx, cy), _, _, d, *_ = hip_frame(k)
    n = (d[1], -d[0], 0)
    if (toward[0] - cx) * n[0] + (toward[1] - cy) * n[1] < 0:
        n = (-n[0], -n[1], 0)
    return cut((cx + HB * n[0], cy + HB * n[1], 0), n)


def hip_bottom(k):
    """ระนาบท้องตะเข้ k"""
    (cx, cy), *_ , t = hip_frame(k)
    p = hip_top(k, cx, cy)
    return cut(tuple(a - 0.125 * b for a, b in zip(p, t)), t)


# B อะเส รอบอาคาร: แนว A/F ยาวต่อเนื่อง; แนวกริด 1/10 ตัดชนผิวด้านในอะเส A/F
YW0, YW1 = GY['A'] + WP_Y + HB, GY['F'] - WP_Y - HB     # ผิวด้านในอะเส A/F
for k, (q0, q1) in enumerate((((GX[0], GY['A'] + WP_Y), (GX[-1], GY['A'] + WP_Y)),
                               ((GX[0], GY['F'] - WP_Y), (GX[-1], GY['F'] - WP_Y)),
                               ((GX[0] + WP_Y, YW0), (GX[0] + WP_Y, YW1)),
                               ((GX[-1] - WP_Y, YW0), (GX[-1] - WP_Y, YW1)))):
    cs = (None, None)
    if k < 2:                                  # อะเส A/F ปลายตัดชนผิวข้างตะเข้ที่มุมอาคาร (ตะเข้ผ่านเหนือมุมอะเส)
        ha, hb_ = (1, 2) if k == 0 else (4, 3)
        cs = (hip_side(ha, (GX[4], q0[1])), hip_side(hb_, (GX[4], q0[1])))
    steel(f'RF-WP{k+1}', (*q0, ZB), (*q1, ZB), 'C125', True, 'อะเส', 'B', cuts=cs)
# B ขื่อด้านสั้น ทุกกริด 2–9 (วางบนคานหลังคาแนว y) ตัดชนผิวด้านในอะเส A/F
for gi in range(1, 9):
    x = GX[gi]
    steel(f'RF-TS{gi+1}', (x, YW0, ZB), (x, YW1, ZB), 'C125', True, f'ขื่อด้านสั้น กริด {gi+1}', 'B')
# A ขื่อทางยาว แนว B C D E: แบ่งท่อนระหว่างขื่อด้านสั้น ปลายชนผิวข้างขื่อ/อะเสกริด 1, 10
_tl_x = [GX[0] + WP_Y + HB] + [v for gi in range(1, 9) for v in (GX[gi] - HB, GX[gi] + HB)] + [GX[-1] - WP_Y - HB]
for r in COL_ROWS:
    segs = [((_tl_x[j], GY[r], ZA), (_tl_x[j + 1], GY[r], ZA), (None, None)) for j in range(0, len(_tl_x), 2)]
    steel(f'RF-TL-{r}', None, None, 'C100', True, f'ขื่อทางยาว แนว {r} ({len(segs)} ท่อน)', 'A', segs=segs)

# เพลทหัวเสา PL12x200x200 + J-BOLT M12 บนหัวเสา คสล. ชั้น 5 (ผู้ใช้กำหนด)
JB_N, JB_EMBED, JB_PROJ, JB_PITCH = 4, 0.30, 0.05, 0.14
for i in range(10):
    for r in COL_ROWS:
        x, y = GX[i], GY[r]
        add(f'RF-BP-{i+1}{r}', 'โครงหลังคาเหล็ก', 5, 'A03.2',
            prism([(x - 0.10, y - 0.10), (x + 0.10, y - 0.10), (x + 0.10, y + 0.10), (x - 0.10, y + 0.10)], ROOF_BEAM, BASE_PL_T),
            name=f'PL เพลทหัวเสา 12x200x200 มม. เสา {i+1}/{r}', qty=dict(count=1, mark='PL', weight_kg=round(0.2 * 0.2 * 0.012 * 7850, 2)))
        for k, (dx, dy) in enumerate(((-1, -1), (1, -1), (1, 1), (-1, 1))):
            bx, by = x + dx * JB_PITCH / 2, y + dy * JB_PITCH / 2
            add(f'RF-JB-{i+1}{r}-{k+1}', 'โครงหลังคาเหล็ก', 5, 'A03.2',
                member((bx, by, ROOF_BEAM - JB_EMBED), (bx, by, RB + JB_PROJ), 0.012, 0.012),
                name=f'J-BOLT M12 เสา {i+1}/{r}', assumed=True,
                qty=dict(count=1, mark='JB', length=round(JB_EMBED + BASE_PL_T + JB_PROJ, 3)))
ASSUMPTIONS.append('J-BOLT M12 ต่อเพลท 4 ตัว ระยะ 140 มม. ฝัง 0.30 ม. โผล่เหนือเพลท 0.05 ม. (รอผู้ใช้ยืนยัน); เพลทวางทุกหัวเสา แนว B–E กริด 1–10')


def bridge_top(face, x, y):
    """หลังสะพาน 2C125 แนวราบใต้จันทัน: แตะท้องจันทันที่ขอบด้านล่างลาดของสะพาน"""
    if face == 'A': y -= HB
    elif face == 'F': y += HB
    elif face == '1': x -= HB
    else: x += HB
    return zface(face, x, y) - RAF_BOT


# C สะพานรับจันทัน (แนว x) ใต้จันทันด้านยาว
BR_BOT = {}                                   # (x หรือ None, y) → ท้องสะพาน
def _bridge(eid, y, x0, x1, c0=None, c1=None):
    face = 'A' if y < yc else 'F'
    zt = bridge_top(face, 0, y)
    steel(eid, (x0, y, zt - 0.0625), (x1, y, zt - 0.0625), 'C125', True, f'สะพานรับจันทัน y={y:.2f}', 'C', cuts=(c0, c1))
    return zt - 0.125


for r in ('B', 'C', 'D', 'E'):
    y = GY[r]; dy = abs(y - yc)
    h0, h1 = (1, 2) if y < yc else (4, 3)
    BR_BOT[y] = _bridge(f'RF-BR-{r}', y, rx0 - dy, rx1 + dy, hip_side(h0, (rx0, y)), hip_side(h1, (rx0, y)))
BR_BOT[Y_MID_N] = _bridge('RF-BR-MN', Y_MID_N, GX[2] - HB, GX[7] + HB)
BR_BOT[Y_MID_S] = _bridge('RF-BR-MS', Y_MID_S, GX[2] - HB, GX[7] + HB)
# สะพานช่วงตะเข้: ปลายด้านสกัดอยู่บนแนวตะเข้ ตัดชนผิวข้างตะเข้
BR_BOT[Y_HIP_N] = _bridge('RF-BR-HN1', Y_HIP_N, X_E0, GX[2] + HB, hip_side(1, (GX[2], Y_HIP_N)))
_bridge('RF-BR-HN2', Y_HIP_N, GX[7] - HB, X_E1, None, hip_side(2, (GX[7], Y_HIP_N)))
BR_BOT[Y_HIP_S] = _bridge('RF-BR-HS1', Y_HIP_S, X_E0, GX[2] + HB, hip_side(4, (GX[2], Y_HIP_S)))
_bridge('RF-BR-HS2', Y_HIP_S, GX[7] - HB, X_E1, None, hip_side(3, (GX[7], Y_HIP_S)))
# C สะพานรับจันทันพรางด้านสกัด (แนว y) กริด 2 และ 9: ปลายตัดชนผิวข้างตะเข้
END_BOT = {}
for k, (x, face) in enumerate(((X_E0, '1'), (X_E1, '10'))):
    zt = bridge_top(face, x, yc)
    ha, hb_ = (1, 4) if face == '1' else (2, 3)
    steel(f'RF-BR-END{k+1}', (x, Y_HIP_N, zt - 0.0625), (x, Y_HIP_S, zt - 0.0625), 'C125', True,
          f'สะพานรับจันทันพราง กริด {2 if k == 0 else 9}', 'C', cuts=(hip_side(ha, (x, yc)), hip_side(hb_, (x, yc))))
    END_BOT[x] = zt - 0.125

# D เสารับจันทัน 2C100 บนขื่อด้านสั้น: หัวเสาแตะท้องสะพาน (เสาใต้แนวตะเข้: ตัดหัวเสาตามท้องตะเข้)
posts = []                                    # (x, y, หัวเสา z หรือ None, ระนาบตัดหัวเสา)
for gi in range(2, 8):
    for y in (GY['B'], Y_MID_N, GY['C'], GY['D'], Y_MID_S, GY['E']):
        posts.append((GX[gi], y, BR_BOT[y], None))
for x in (X_E0, X_E1):
    for y in (GY['B'], GY['E']):
        posts.append((x, y, BR_BOT[y], None))
    for y in (GY['C'], GY['D']):
        posts.append((x, y, END_BOT[x], None))
    for y in (Y_HIP_N, Y_HIP_S):              # เสาที่จุดตัดแนวตะเข้: หัวเสาราบที่ระดับท้องสะพานพราง (ต่ำกว่าท้องตะเข้)
        posts.append((x, y, END_BOT[x], None))
for x in (GX[2], GX[7]):                      # ปลายสะพานช่วงตะเข้
    for y in (Y_HIP_N, Y_HIP_S):
        posts.append((x, y, BR_BOT[y], None))
for n, (x, y, zt, ct) in enumerate(posts, 1):
    if ct:
        steel(f'RF-P{n:02d}', (x, y, ZB_TOP), (x, y, ZB_TOP + 1.0), 'C100', True, 'เสารับจันทัน (รับตะเข้)', 'D', cuts=(None, ct))
    else:
        steel(f'RF-P{n:02d}', (x, y, ZB_TOP), (x, y, zt), 'C100', True, 'เสารับจันทัน', 'D')

# I เหล็กทะแยง C100 (S107): หัวเสาแนว B → โคนเสากลาง, หัวเสากลาง → โคนเสาแนว C (และฝั่ง E/D)
# ปลายตัดดิ่งชนผิวข้างเสา; มุมบนแตะท้องสะพาน มุมล่างแตะหลังขื่อ (ไม่ทะลุ)
def diag_line(yu, z1, yl, z0, h):
    """แกนเหล็กทะแยงในระนาบ y-z: ขอบบนผ่าน (yu, z1) ขอบล่างผ่าน (yl, z0) หน้าตัดลึก h"""
    my, mz = (yu + yl) / 2, (z1 + z0) / 2
    Dy, Dz = yu - yl, z1 - z0
    L_ = math.hypot(Dy, Dz); a = math.asin(h / L_)
    for sg in (1, -1):
        ang = math.atan2(Dz, Dy) + sg * a
        uy, uz = math.cos(ang), math.sin(ang)
        ty, tz = -uz, uy                      # ตั้งฉากในระนาบ (หันขึ้น)
        if tz < 0: ty, tz = -ty, -tz
        if (yu - my) * ty + (z1 - mz) * tz > 0:
            return (my, mz), (uy, uz)
    raise ValueError


n = 0
for gi in range(2, 8):
    x = GX[gi]
    for ya, yb in ((GY['B'], Y_MID_N), (Y_MID_N, GY['C']), (GY['E'], Y_MID_S), (Y_MID_S, GY['D'])):
        n += 1
        sg = 1 if yb > ya else -1
        yu, yl = ya + sg * 0.05, yb - sg * 0.05
        (my, mz), (uy, uz) = diag_line(yu, BR_BOT[ya], yl, ZB_TOP, STEEL['C100']['h'])
        zl = lambda yy: mz + (yy - my) * uz / uy
        # เสารับจันทันที่อยู่ระหว่างช่วง (เสาปลายสะพานช่วงตะเข้): แบ่งเหล็กทะแยงเป็น 2 ท่อน ปลายชนผิวข้างเสา
        mid = sorted((py for px, py, *_ in posts if abs(px - x) < 1e-6 and min(yu, yl) < py < max(yu, yl)), key=lambda v: sg * v)
        ys_ = [yu] + [v for py in mid for v in (py - sg * 0.05, py + sg * 0.05)] + [yl]
        segs = [((x, ys_[j], zl(ys_[j])), (x, ys_[j + 1], zl(ys_[j + 1])), (cut((x, ys_[j], 0), YP), cut((x, ys_[j + 1], 0), YP)))
                for j in range(0, len(ys_), 2)]
        steel(f'RF-DG{n:02d}', None, None, 'C100', False, 'เหล็กทะแยง' + (f' ({len(segs)} ท่อน)' if len(segs) > 1 else ''), 'I', segs=segs)

# J คานค้ำแนวระดับ 2C100 ระหว่างเสารับจันทันที่อยู่ติดกัน (เสาปลายสะพานช่วงตะเข้ ↔ เสากลางช่วง) กริด 3, 8 (ผู้ใช้สั่ง 11 พ.ย. 2569)
# ปลายตัดชนผิวข้างเสา; ระดับกึ่งกลางความสูงเสาต้นที่เตี้ยกว่า (เสาใต้สะพานช่วงตะเข้)
n = 0
for x in (GX[2], GX[7]):
    for ya, yb in ((Y_MID_N, Y_HIP_N), (Y_MID_S, Y_HIP_S)):
        n += 1
        zc = (ZB_TOP + BR_BOT[yb]) / 2
        sg = 1 if yb > ya else -1
        steel(f'RF-PB{n}', (x, ya + sg * 0.05, zc), (x, yb - sg * 0.05, zc), 'C100', True, 'คานค้ำเสารับจันทัน', 'J')

# G อกไก่: ใต้ท้องจันทันที่สัน (แตะขอบท้องจันทันสองด้าน) ปลายเลยแกนเสารับอกไก่ปลายสัน 0.05
RIDGE_TOP = RIDGE - HB * slope - RAF_BOT
steel('RF-RIDGE', (rx0 - HB, yc, RIDGE_TOP - 0.0625), (rx1 + HB, yc, RIDGE_TOP - 0.0625), 'C125', True, 'อกไก่', 'G')

# E คานรับเสาดั้ง + F เสารับอกไก่
Z_E = ROOF_BEAM + 2.44
xs_king = [rx0] + [GX[i] for i in range(3, 7)] + [rx1]
for k, x in enumerate(xs_king, 1):
    on_posts = x in GX                         # มีเสารับจันทันแนว C/D ที่กริดนี้: ตัดปลายชนผิวข้างเสา
    y0, y1 = (GY['C'] + HB, GY['D'] - HB) if on_posts else (GY['C'], GY['D'])
    steel(f'RF-KB{k}', (x, y0, Z_E), (x, y1, Z_E), 'C125', True, 'คานรับเสาดั้ง', 'E')
    steel(f'RF-KP{k}', (x, yc, Z_E + 0.0625), (x, yc, RIDGE_TOP - 0.125), 'C100', True, 'เสารับอกไก่', 'F')
    if not on_posts:                           # เสารับคานรับเสาดั้งที่ปลายสัน ยืนบนขื่อทางยาว C/D
        for r in ('C', 'D'):
            steel(f'RF-KC{k}{r}', (x, GY[r], ZA_TOP), (x, GY[r], Z_E - 0.0625), 'C100', True, 'เสารับคานรับเสาดั้ง', 'D')

# C ตะเข้สัน: ขอบหลังตะเข้แตะระนาบหลังจันทัน; ปลายล่างตัดดิ่งตั้งฉาก (มุมไม่เลยแนวชายคา) ปลายบนตัดชนผิวข้างอกไก่
for k in (1, 2, 3, 4):
    (cx, cy), (qx, qy), face, d, u, s, t = hip_frame(k)
    off = 0.0625 * math.sqrt(1 + (slope / math.sqrt(2)) ** 2)
    a0, a1 = hip_top(k, cx, cy), hip_top(k, qx, qy)
    q0 = (a0[0], a0[1], a0[2] - off); q1 = (a1[0], a1[1], a1[2] - off)
    ins = HB + FI * math.sqrt(2)               # มุมตะเข้ไม่เลยผิวด้านในเชิงชาย
    c0 = cut((cx + ins * d[0], cy + ins * d[1], 0), (d[0], d[1], 0))
    c1 = cut((qx, yc - HB if qy - cy > 0 else yc + HB, 0), YP)
    steel(f'RF-HIP{k}', q0, q1, 'C125', True, 'ตะเข้สัน', 'C', cuts=(c0, c1))

# H จันทัน C100 @0.875 ด้านยาว (แนว y) และจันทันพรางด้านสกัด (แนว x)
# ปลายชายคาตัดดิ่ง, ปลายบนตัดดิ่งที่แนวสัน (ชนจันทันอีกด้าน) หรือชนผิวข้างตะเข้
xs = []
x = ex0 + 0.477
while x < ex1 - 0.2:
    xs.append(round(x, 3)); x += 0.875
n = 0
for x in xs:
    for side in (0, 1):
        y_e = ey0 if side == 0 else ey1
        face = 'A' if side == 0 else 'F'
        if rx0 <= x <= rx1:
            y_t, ct = yc, cut((x, yc, 0), YP)
        else:
            d = (rx0 - x) if x < rx0 else (x - rx1)
            y_t = yc - d if side == 0 else yc + d
            if (side == 0 and y_t <= y_e) or (side == 1 and y_t >= y_e):
                continue
            hk = {(0, 0): 1, (0, 1): 2, (1, 1): 3, (1, 0): 4}[(side, int(x > rx1))]
            ct = hip_side(hk, (x, y_e))
        n += 1
        steel(f'RF-RAF{n:03d}', (x, y_e, zface(face, x, y_e) - RAF_C), (x, y_t, zface(face, x, y_t) - RAF_C), 'C100', False,
              'จันทัน', 'H', cuts=(cut((x, y_e + (FI if side == 0 else -FI), 0), YP), ct))
ys = []
y = ey0 + 0.477
while y < ey1 - 0.2:
    ys.append(round(y, 3)); y += 0.875
for y in ys:
    for side in (0, 1):
        x_e = ex0 if side == 0 else ex1
        face = '1' if side == 0 else '10'
        d = abs(y - yc)
        x_t = rx0 - d if side == 0 else rx1 + d
        if (side == 0 and x_t <= x_e + 0.05) or (side == 1 and x_t >= x_e - 0.05):
            continue
        hk = {(0, 0): 1, (0, 1): 4, (1, 0): 2, (1, 1): 3}[(side, int(y > yc))]
        n += 1
        steel(f'RF-RAF{n:03d}', (x_e, y, zface(face, x_e, y) - RAF_C), (x_t, y, zface(face, x_t, y) - RAF_C), 'C100', False,
              'จันทันพราง', 'H', cuts=(cut((x_e + (FI if side == 0 else -FI), y, 0), XP), hip_side(hk, (x_e, y))))

# แปเหล็กกัลวาไนซ์ SCG บนจันทัน (A03.3) ตามคู่มือติดตั้งกระเบื้องคอนกรีต SCG:
# แปตัวแรกขอบบนห่างขอบนอกเชิงชาย 0.34 ม., แปคู่ที่สันห่างกัน 4–6 ซม. (ขอบนอก), แปที่เหลือแบ่งเท่ากัน 0.32–0.34 ม.
BAT_W = 0.05                                   # ความกว้างแป (ค่าสมมติ)
cosA = 1 / math.sqrt(1 + slope * slope)
L_SLOPE = run / cosA                           # ความยาวตามลาดจากขอบเชิงชายถึงสัน
U_FIRST, U_LAST = 0.34, L_SLOPE - 0.025        # ตำแหน่งขอบบนแปตัวแรก / ตัวบนสุด (แปคู่สันห่าง 5 ซม.)
BAT_N = next(n for n in range(1, 100) if (U_LAST - U_FIRST) / n <= 0.34)   # จำนวนช่องน้อยสุดที่ระยะ ≤ 0.34
BAT_SP = (U_LAST - U_FIRST) / BAT_N
BAT_MODEL = 'แปเหล็กกัลวาไนซ์ SCG หนา 0.55 มม. ยาว 4 ม./เส้น (ผู้ใช้เลือก 10 พ.ย. 2569)'
def _bat_pts(face, h):
    """ปลายแปสองข้างที่ระยะราบ h จากขอบเชิงชาย (ตัดชนแนวตะเข้สัน 45° ในแปลน)"""
    z = z_eave + h * slope - SKIN_T / cosA     # ใต้กระเบื้อง (กระเบื้องหนา SKIN_T ตั้งฉากกับลาด)
    return {'A': [(ex0 + h, ey0 + h, z), (ex1 - h, ey0 + h, z)],
            'F': [(ex1 - h, ey1 - h, z), (ex0 + h, ey1 - h, z)],
            '1': [(ex0 + h, ey1 - h, z), (ex0 + h, ey0 + h, z)],
            '10': [(ex1 - h, ey0 + h, z), (ex1 - h, ey1 - h, z)]}[face]


for k in range(BAT_N + 1):
    ut = U_FIRST + k * BAT_SP                  # ขอบบนแปตามลาด
    hb, ht = (ut - BAT_W) * cosA, ut * cosA
    for face in ('A', 'F', '1', '10'):
        b0, b1 = _bat_pts(face, hb)
        t1, t0 = _bat_pts(face, ht)[1], _bat_pts(face, ht)[0]
        lb, lt = math.dist(b0[:2], b1[:2]), math.dist(t0[:2], t1[:2])
        if lt < 0.05:
            continue
        add(f'RF-BAT-{face}-{k+1:02d}', 'โครงหลังคาเหล็ก', 5, 'A03.3', plate([b0, b1, t1, t0], PURLIN_T),
            name=f'แปเหล็กกัลวาไนซ์ แถว {k+1} ด้าน {face}', assumed=True,
            qty=dict(length=round((lb + lt) / 2, 3), model=BAT_MODEL, spacing=round(BAT_SP, 4)))
        elements[-1]['material'] = 'BIM-แปกัลวาไนซ์'   # สี/ผิวโลหะกัลวาไนซ์ (ผู้ใช้สั่ง 10 พ.ย. 2569); โครงเหล็กอื่นใช้สีกันสนิมแดง
ASSUMPTIONS.append('ประตูบานเลื่อน D2: คอมโพเนนต์อะลูมิเนียม 2 บานเลื่อน วงกบ 1.25x1.80 ลึก 0.10 ม. (เต็มความหนาผนังรวมฉาบ) หน้าวงกบ 4 ซม. ธรณีสูง 2 ซม. บานหนา 2.2 ซม. ทับกันกลาง 4 ซม. กระจกใส 6 มม. — ขนาดหน้าตัด/สีเป็นค่าสมมติ รอรุ่นจริง')
ASSUMPTIONS.append(f'แปเหล็กกัลวาไนซ์ SCG ตามคู่มือติดตั้งกระเบื้องคอนกรีต SCG (ผู้ใช้กำหนด 10 พ.ย. 2569): แปตัวแรก 0.34 ม. จากขอบเชิงชาย, แปคู่สันห่าง 5 ซม., ระยะแป {BAT_SP:.4f} ม. ({BAT_N + 1} แถว/ด้าน); แปหนา 0.55 มม. (ผู้ใช้เลือก) จันทันห่าง 0.875 ≤ 1.00 ม. ตามคู่มือ; หน้าตัดแปในโมเดลเป็นแผ่นตันกว้าง 0.05 หนา 0.04 ม. ขนานลาดหลังคา (ค่าสมมติ); ปลายแปตัดเฉียงชนแนวตะเข้สัน')

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
    add(k, 'หลังคา', 5, 'A03.3', plate(pts, 0.03), name='กระเบื้องหลังคาคอนกรีต SCG เพรสทีจ เอ็กซ์ชิลด์ สีดีพ ฟอร์เรสท์', assumed=True,
        qty=dict(area=round(tri_area(pts), 3), model='SCG เพรสทีจ เอ็กซ์ชิลด์ สีดีพ ฟอร์เรสท์ (กระเบื้องหลังคาคอนกรีต)'))
for k, (p0, p1) in enumerate((((ex0, ey0), (ex1, ey0)), ((ex1, ey0), (ex1, ey1)),
                               ((ex1, ey1), (ex0, ey1)), ((ex0, ey1), (ex0, ey0)))):
    # ผิวนอกบนแนวชายคา หลังเชิงชายแตะท้องกระเบื้องที่ขอบ ต่อมุมตัดองศา (45°) สร้างด้วย Profile Builder
    _P = [(ex0, ey0), (ex1, ey0), (ex1, ey1), (ex0, ey1)]
    dv = _unit((p1[0] - p0[0], p1[1] - p0[1], 0)); n_in = (-dv[1], dv[0], 0)
    zc = z_eave - SKIN_T * _SEC - FASCIA_H / 2
    a0 = (p0[0] + n_in[0] * FASCIA_T / 2, p0[1] + n_in[1] * FASCIA_T / 2, zc)
    a1 = (p1[0] + n_in[0] * FASCIA_T / 2, p1[1] + n_in[1] * FASCIA_T / 2, zc)
    def _miter(c, d_in, d_out):
        b = _unit((d_out[0] - d_in[0], d_out[1] - d_in[1], 0))
        return cut((c[0], c[1], 0), (b[1], -b[0], 0))
    dprev = _unit((p0[0] - _P[(k - 1) % 4][0], p0[1] - _P[(k - 1) % 4][1], 0))
    dnext = _unit((_P[(k + 2) % 4][0] - p1[0], _P[(k + 2) % 4][1] - p1[1], 0))
    fg = member(a0, a1, FASCIA_T, FASCIA_H); fg['pb'] = True
    fg['trim'] = [_miter(p0, dprev, dv), _miter(p1, dv, dnext)]
    add(f'RF-FASCIA{k+1}', 'หลังคา', 5, 'A03.3', fg,
        name='เชิงชาย DURAONE Fascia 23x300x1.6 ซม. สีซีเมนต์', assumed=True,
        qty=dict(length=round(math.dist(p0, p1), 3), model='DURAONE Fascia 23x300x1.6 ซม. สีซีเมนต์ (ผู้ใช้กำหนด 11 พ.ย. 2569)',
                 pieces_3m=math.ceil(round(math.dist(p0, p1) / 3.0, 6))))
    elements[-1]['material'] = 'BIM-เชิงชายสีซีเมนต์'


# =====================================================================
# งานสถาปัตย์ (แปลน A-01 ชั้น 1, A-02 ชั้น 2–5, แปลนห้องน้ำชั้น 1)
# กริดสถาปัตย์ A,B,C,D = กริดโครงสร้าง B,C,D,E
# =====================================================================
WALL_T = 0.07            # บล็อก 3 รู 7x10x20 ซม. (ผู้ใช้กำหนด 9 พ.ย. 2569)
BLOCK_PER_M2 = round(1 / (0.20 + 0.01) / (0.10 + 0.01), 1)   # ก้อน/ตร.ม. รวมรอยต่อ 1 ซม.
PL_T = 0.015             # ฉาบแต่ละด้าน
# ผนังก่อรอบอาคาร: ผิวนอกบล็อกเสมอขอบนอกคาน/เสา ให้ฉาบภายนอกต่อเนื่องเป็นผืนเดียว (ผู้ใช้สั่ง 11 พ.ย. 2569)
OUT_C = WALL_T / 2       # ศูนย์ผนังนอกแนว A/F ห่างแนวกริด (ผิวนอกเสมอขอบนอกคาน B4 ที่แนวกริด)


def gw(x):
    """ศูนย์ผนังบนแนวกริด x: กริด 1 และ 10 (ผนังริมอาคาร) เลื่อนออกนอกให้ผิวนอกเสมอผิวนอกเสา/คาน"""
    if abs(x - GX[0]) < 1e-6:
        return GX[0] - (COL_SEC[1][0] / 2 - WALL_T / 2)
    if abs(x - GX[9]) < 1e-6:
        return GX[9] + (COL_SEC[1][0] / 2 - WALL_T / 2)
    return x


def ox(t, sgn):
    """ปลายผนังนอกแนว A/F ที่กริด t: กริดริม (1, 10) ยาวถึงมุมนอกอาคาร, กริดใน ชนผิวผนังกริด"""
    if abs(t - GX[0]) < 1e-6 or abs(t - GX[9]) < 1e-6:
        return gw(t) - sgn * WALL_T / 2
    return t + sgn * WALL_T / 2
ASSUMPTIONS += [
    'กริดสถาปัตย์ A,B,C,D ในแปลน A-01/A-02 ตรงกับกริดโครงสร้าง B,C,D,E',
    'เสาเอ็น/คานเอ็น คสล. กว้าง 0.10 ม. หนาเท่าบล็อก 0.07 ม.: เสาเอ็นข้างวงกบประตูหน้าต่างทุกช่อง, เสาเอ็นกลางผนังทึบที่ยาวเกิน 3.50 ม., คานเอ็นกลางความสูงผนังทุกผนัง, คานทับหลังและคานใต้วงกบยาวชนเสาเอ็นข้างช่องพอดี (ช่องเปิดกว้างไม่เกิน 1 ม. เสาเอ็นข้างช่องตั้งบนคานใต้วงกบ)',
    'ผนังบล็อก 3 รู 7x10x20 ซม. (หนา 0.07 ม.) ฉาบในและนอกด้านละ 0.015 ม. (ผู้ใช้กำหนด) จำนวนก้อนคิดรอยต่อ 1 ซม. สูงจากพื้นถึงท้องคาน (คานลึก 0.50 หรือ 0.40)',
    'ขนาดประตู–หน้าต่างไม่มีตาราง: ประตูห้อง 0.90x2.00, ประตูระเบียง 0.80x2.00, ประตูห้องน้ำ 0.70x2.00, ช่องระแนงระเบียง 1.20x1.20 สูงจากพื้น 0.90, ช่องลมห้องน้ำ 0.40x0.40 สูงจากพื้น 1.80, ช่องหน้าร้าน 2.80x2.60',
    'ฉาบเสาหนา 1 ซม. และท้องคาน/ข้างคานหนา 0.5 ซม. (ผู้ใช้กำหนด) ผูกกับงานฉาบของชั้นนั้น: ชั้น 1 = A12, ชั้น 2–3 = A09, ชั้น 4 = A10, ชั้น 5 (รวมคานหลังคา) = A11; ข้างคานคิดเต็มความลึกคาน',
    'ฉาบผนังห้องโถงบันไดชั้น 1 ผูกกับ A12; ฉาบใต้ท้องพื้น A12 = ใต้พื้นชั้น 2, A15 = ใต้พื้นชั้น 3–5 (เพดานชั้น 2–4)',
    'กระเบื้องพื้น A16/A17 แทนด้วยแผ่นหนา 0.02 ม. เต็มพื้นที่ใช้งานแต่ละชั้น (ห้อง ห้องน้ำ ระเบียง ทางเดิน)',
    'สุขภัณฑ์ A21 แทนด้วยกล่องโถส้วมและอ่างล้างหน้า ห้องน้ำละ 1 ชุด',
    'ยังไม่มีชิ้นส่วนของ A07/A08 (ระบบท่อ), A19/A20 (สี ฝ้า), A22/A23 เพราะไม่มีแบบระบบและเป็นงานผิว/งานทดสอบ',
    'ไม่ได้ขึ้นบันไดเหล็กภายนอกด้านกริด 10 (ไม่มีในแผน R3)',
]


def beam_soffit(f, kind, strip=False):
    """ระดับท้องคานเหนือผนังของชั้น f; kind 'main' (คานลึก 0.50) / 'edge' (0.40)
    strip=True: ผนังในแถบยื่น (ระเบียง/ห้องน้ำ) ใต้คาน B3/B4/B5 ที่ลดระดับ DROP"""
    if f == 5:                      # ไม่มีคานหลังคา: ผนังชั้น 5 ก่อถึงใต้โครงเหล็กหลังคา +16.30
        return ROOF_BEAM
    top = FL[f + 1] - SLAB_T - (DROP if strip else 0.0)
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
SMALL_WIN = 1.00         # หน้าต่างกว้างไม่เกินนี้: เสาเอ็นข้างช่องเริ่มจากคานใต้วงกบ
LINTEL_EXT = TIE         # ทับหลัง/คานใต้วงกบสิ้นสุดชนผิวนอกเสาเอ็นข้างช่องพอดี ไม่ยื่นเลย (ผู้ใช้กำหนด 10 พ.ย. 2569)


def tie_layout(a0, a1, z0, z1, openings):
    """คืน posts [(p0,p1)], beams [(x0,x1,zb0,zb1,kind)] ตามหลักผนังก่อ:
    เสาเอ็นข้างวงกบทุกช่อง, เสาเอ็นกลางช่วงผนังทึบที่ยาวเกิน 3.50 ม., คานเอ็นกลางความสูงผนัง,
    คานทับหลังเหนือช่องเปิด และคานใต้วงกบหน้าต่าง ยาวชนเสาเอ็นข้างช่องพอดี"""
    posts = []          # (p0, p1, zb, zt)
    full = []           # เสาเอ็นเต็มความสูง ใช้แบ่งช่วงผนังทึบ
    for c, w, sill, h in openings:
        pp = [(c - w / 2 - TIE, c - w / 2), (c + w / 2, c + w / 2 + TIE)]
        if sill > 0 and w <= SMALL_WIN + 1e-9:
            # หน้าต่าง/บานกระทุ้งกว้างไม่เกิน 1 ม.: เสาเอ็นข้างช่องตั้งบนคานใต้วงกบ ขึ้นถึงใต้คาน (ผู้ใช้กำหนด 10 พ.ย. 2569)
            posts += [(p0, p1, z0 + sill, z1) for p0, p1 in pp]
        else:
            posts += [(p0, p1, z0, z1) for p0, p1 in pp]
            full += pp
    # ช่วงผนังทึบระหว่างปลายผนัง/เสาเอ็นเต็มความสูง
    edges = sorted([(a0, a0)] + full + [(a1, a1)])
    for (_, e0), (s1, _) in zip(edges, edges[1:]):
        L = s1 - e0
        if L > TIE_MAX:
            n = int(L // TIE_MAX)
            for k in range(1, n + 1):
                m = e0 + L * k / (n + 1)
                zt = z1
                for c, w, sill, h in openings:      # เสาเอ็นกลางที่ตรงใต้ช่องเปิด สิ้นสุดใต้คานใต้วงกบ
                    if abs(m - c) < w / 2 + TIE / 2:
                        zt = min(zt, z0 + sill - TIE)
                if zt - z0 > 0.05:
                    posts.append((m - TIE / 2, m + TIE / 2, z0, zt))
    posts = sorted((max(a0, p0), min(a1, p1), zb, zt) for p0, p1, zb, zt in posts)
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
                {v for p in posts for v in p[:2]} | {v for b in beams for v in b[:2]})
    zs = sorted({z0, z1} | {z0 + s for c, w, s, h in openings} | {z0 + s + h for c, w, s, h in openings} |
                {v for b in beams for v in b[2:4]} | {v for p in posts for v in p[2:4]})
    xs = [x for x in xs if a0 - 1e-9 <= x <= a1 + 1e-9]
    zs = [z for z in zs if z0 - 1e-9 <= z <= z1 + 1e-9]
    cells = {'mas': [], 'beam': {}}
    for xa, xb in zip(xs, xs[1:]):
        if xb - xa < 1e-4:
            continue
        xm = (xa + xb) / 2
        run = None
        for za, zb in zip(zs, zs[1:]):
            if zb - za < 1e-4:
                continue
            zm = (za + zb) / 2
            if any(p0 <= xm <= p1 and pb <= zm <= pt for p0, p1, pb, pt in posts):
                kind = None
            elif any(abs(xm - c) < w / 2 and z0 + s < zm < z0 + s + h for c, w, s, h in openings):
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
    if cells['mas']:                   # ผนังที่เหลือแต่เสาเอ็นข้างช่องเปิด (เช่น หน้าร้าน) ไม่มีงานก่อ
        add(eid, 'ผนัง', floor, task_wall,
            dict(type='multi', parts=[rect_prism(axis, fixed, a, b, c, d, 0, WALL_T) for a, b, c, d in cells['mas']]),
            name=name or f'ผนังก่อ {eid}', assumed=True,
            qty=dict(area=round(area, 3), length=round(a1 - a0, 3), blocks=round(area * BLOCK_PER_M2), material='บล็อก 3 รู 7x10x20'))
    for k, (p0, p1, pb, pt) in enumerate(posts):
        h = pt - pb
        add(f'{eid}-TC{k+1}', 'เสาเอ็นคานเอ็น', floor, task_wall, rect_prism(axis, fixed, p0, p1, pb, pt, 0, WALL_T),
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


plaster_task = {1: None, 2: 'A09', 3: 'A09', 4: 'A10', 5: 'A11'}


def cor_wall_y(side, f):
    """แนวกึ่งกลางผนังทางเดิน: ผิวบล็อกด้านทางเดินเสมอผิวเสาด้านทางเดิน"""
    if side == 'N':
        return GY['C'] + col_d(f) - WALL_T / 2
    return GY['D'] - col_d(f) + WALL_T / 2
wall_task = {1: 'A04', 2: 'A04', 3: 'A04', 4: 'A05', 5: 'A06'}
D2_W = 1.25                 # ประตูบานเลื่อนออกระเบียง D2 (A106)
D2_H = 1.80                 # ความสูงประตูด้านหลังคงไว้ 1.80 ม. (ผู้ใช้กำหนด 10 พ.ย. 2569)
SH_W, SH_D = 0.475, 0.65    # ช่องชาร์ฟห้องน้ำ ขนาดนอก (แนว x จากผิวผนังกริด, แนว y จากผิวผนังห้อง) ตาม A106
W1_MODEL = 'KPA หน้าต่างบานกระจกซ้อน อะลูมิเนียม 60x40 ซม. สีขาว (HomePro 1310766)'


def wc_geo(i, side, f):
    """ตำแหน่งอ้างอิงห้องน้ำห้องพักตาม A106: xc แนวกริดฝั่งเสา, dr ทิศเข้าห้องน้ำ, xg ผิวผนังกริด,
    s ทิศจากผนังนอกเข้าห้อง (แกน y), yo ผิวในผนังนอก, yr ผิวผนังห้อง, d2/d3 ศูนย์กลางประตู"""
    tx0, tx1, bx0, bx1 = bay_split(i, side)
    b5 = b5x(i, side)
    xc, dr = (tx1, -1) if abs(tx0 - b5) < 1e-6 else (tx0, 1)
    s = 1 if side == 'N' else -1
    y_out, y_rm = (0.0, GY['B']) if side == 'N' else (GY['F'], GY['E'])
    xb = GX[i] if xc == GX[i + 1] else GX[i + 1]          # กริดฝั่งระเบียง
    cwf = col_w(f)
    face_b5 = b5 + dr * (WALL_T / 2)                       # ผิวผนัง B5 ด้านระเบียง (จาก B5 ห้องน้ำอยู่ทิศ -dr ระเบียงอยู่ทิศ +dr)
    face_col = xb - dr * cwf                               # ผิวเสาฝั่งระเบียง
    return dict(xc=xc, dr=dr, s=s, xg=gw(xc) + dr * (WALL_T / 2 + PL_T),
                yo=y_out + s * (OUT_C + WALL_T / 2 + PL_T), yr=y_rm - s * (WALL_T / 2 + PL_T),
                d3=b5 - dr * 0.55, d2=(face_b5 + face_col) / 2)
yB, yC, yD, yE, yF = GY['B'], GY['C'], GY['D'], GY['E'], GY['F']

for f in (2, 3, 4, 5):
    z0 = FL[f]
    zs = FL[f] - DROP                  # พื้นระเบียง/ห้องน้ำ (แถบยื่น)
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
            tx0, tx1, bx0, bx1 = bay_split(i, side)
            tag = f'F{f}-{side}{i+1}'
            # ผนังทางเดิน (ประตูห้อง)
            if not stair:
                # ผิวก่อด้านทางเดินเสมอขอบเสา (ผู้ใช้แจ้ง 10 พ.ย. 2569); คาน B2 แนว C/D เลื่อนมาเสมอผิวเสา ผนังจึงก่อถึงใต้ท้องคาน (11 พ.ย. 2569)
                add_wall(f'W-{tag}-COR', f, 'x', cor_wall_y(side, f), x0, x1, z0, beam_soffit(f, 'main'), tw, tp,
                         [(GX[i] + 0.75, 0.90, 0.0, 2.00)], name=f'ผนังทางเดิน ชั้น {f} ห้อง {side}{i+1}')
                # ---- ผังห้องน้ำ/ระเบียงตามแบบ A106 (ผู้ใช้ส่ง 10 พ.ย. 2569) ----
                # คงแนวผนัง B5 เดิม (ตรงคานซอย B5 ตาม S-04); xc = แนวกริดฝั่งเสาของห้องน้ำ, dr = ทิศจากกริดเข้าห้องน้ำ
                g = wc_geo(i, side, f)
                # ผนังห้อง–ระเบียง: ประตูบานเลื่อน D2 1.25x1.80 ออกระเบียง, ประตูห้องน้ำ D3 0.70x1.80 ชิดผนังระเบียง
                add_wall(f'W-{tag}-BAL', f, 'x', y_rm, x0, x1, z0, beam_soffit(f, 'main'), tw, tp,
                         [(g['d2'], D2_W, 0.0, D2_H), (g['d3'], 0.70, 0.0, 1.80)],
                         name=f'ผนังห้องด้านระเบียง/ห้องน้ำ ชั้น {f} ห้อง {side}{i+1} (ประตูบานเลื่อน D2 1.25x1.80, ประตูห้องน้ำ D3 0.70x1.80)')
                elements[-2]['name'] = f'ประตูบานเลื่อน D2 1.25x1.80 ออกระเบียง ใน W-{tag}-BAL'
                # ผนังข้างห้องน้ำ (แนว B5) ประตูห้องน้ำ
                ya, yb = lo(y_out, y_rm)
                # ผนังกั้นห้องน้ำกับระเบียง (แนว B5) ผนังทึบ: เข้าห้องน้ำจากในห้องพัก (ผู้ใช้แจ้ง 10 พ.ย. 2569)
                # ปลายผนังถึงผิวนอกแนว A/F ไม่เหลือร่องระหว่างผนังนอก 2 ช่วง (ผู้ใช้สั่ง 11 พ.ย. 2569); ฉาบผนังนี้ตัดออกช่วงความหนาผนังนอก (ด้านล่าง)
                wa, wb = (ya, yb - 0.125) if side == 'N' else (ya + 0.125, yb)
                add_wall(f'W-{tag}-WC', f, 'y', b5x(i, side), wa, wb, zs, beam_soffit(f, 'edge', True), tw, tp,
                         name=f'ผนังห้องน้ำด้านระเบียง ชั้น {f} ห้อง {side}{i+1}')
                # ผนังนอกห้องน้ำ: หน้าต่าง W1 KPA 0.60x0.40 ขอบล่าง 1.80 ชิดเสา (ศูนย์กลางห่างกริด 0.47 ตาม A106)
                add_wall(f'W-{tag}-OWC', f, 'x', y_out + (OUT_C if side == 'N' else -OUT_C),
                         ox(tx0, 1), ox(tx1, -1), zs, beam_soffit(f, 'edge', True), tw, tp,
                         [(g['xc'] + g['dr'] * 0.47, 0.60, 1.80, 0.40)], name=f'ผนังนอกห้องน้ำ ชั้น {f} ห้อง {side}{i+1}')
                elements[-1].update(name=f'หน้าต่าง W1 0.60x0.40 ใน W-{tag}-OWC')
                elements[-1]['qty'].update(type='หน้าต่างบานกระจกซ้อน อะลูมิเนียม', model=W1_MODEL)
                add_wall(f'W-{tag}-OBL', f, 'x', y_out + (OUT_C if side == 'N' else -OUT_C),
                         ox(bx0, 1), ox(bx1, -1), zs, beam_soffit(f, 'edge', True), tw, tp,
                         [((bx0 + bx1) / 2, 1.20, 0.90, 1.20)], name=f'ผนังนอกระเบียง ชั้น {f} ห้อง {side}{i+1}')
                # ช่องชาร์ฟท่อแนวดิ่งมุมห้องน้ำชิดเสาฝั่งแนวห้อง (A106 ขนาดนอก 0.475x0.65) ผนังบล็อก 2 ด้าน ก่อถึงใต้พื้นชั้นบน
                zt = (FL[f + 1] - DROP - S1_T) if f < 5 else beam_soffit(f, 'edge', True)
                add_wall(f'W-{tag}-SH1', f, 'y', g['xg'] + g['dr'] * (SH_W - WALL_T / 2), *lo(g['yr'], g['yr'] - g['s'] * SH_D), zs, zt, tw, tp,
                         name=f'ผนังช่องชาร์ฟห้องน้ำ ชั้น {f} ห้อง {side}{i+1} ด้านข้าง')
                add_wall(f'W-{tag}-SH2', f, 'x', g['yr'] - g['s'] * (SH_D - WALL_T / 2), *lo(g['xg'], g['xg'] + g['dr'] * (SH_W - WALL_T)), zs, zt, tw, tp,
                         name=f'ผนังช่องชาร์ฟห้องน้ำ ชั้น {f} ห้อง {side}{i+1} ด้านหน้า')
                # สุขภัณฑ์: โถส้วมหลังชิดผนังกริดที่มุมผนังนอก, อ่างล้างหน้าติดผนังชาร์ฟ (A106)
                wx0, wx1 = g['xg'], g['xg'] + g['dr'] * 0.70
                wyc = g['yo'] + g['s'] * 0.40
                add(f'FX-{tag}-WC', 'สุขภัณฑ์', f, 'A21',
                    prism([(wx0, wyc - 0.20), (wx1, wyc - 0.20), (wx1, wyc + 0.20), (wx0, wyc + 0.20)], zs + 0.02, 0.40),   # วางบนผิวกระเบื้อง
                    name=f'โถส้วม ชั้น {f} ห้อง {side}{i+1}', assumed=True, qty=dict(count=1))
                lx0 = g['xg'] + g['dr'] * (SH_W + PL_T)
                lx1 = lx0 + g['dr'] * 0.45
                lyc = g['yo'] + g['s'] * 1.13
                add(f'FX-{tag}-LAV', 'สุขภัณฑ์', f, 'A21',
                    prism([(lx0, lyc - 0.25), (lx1, lyc - 0.25), (lx1, lyc + 0.25), (lx0, lyc + 0.25)],
                          zs + 0.65, 0.20), name=f'อ่างล้างหน้า ชั้น {f} ห้อง {side}{i+1}', assumed=True, qty=dict(count=1))
            # โถงบันได: ผนังนอกแนว A สร้างแยกตามช่วงชานพัก (ด้านล่าง)
        # ผนังกั้นห้องตามกริด 1–10 (ช่วงห้อง + ช่วงระเบียง)
        for k in range(10):
            ya, yb = lo(y_rm, y_cor)
            # ห้องริม (กริด 1, 10): หน้าต่าง W16 1.20x1.10 ขอบล่าง 0.90 กลางห้อง (ผู้ใช้แจ้ง, ขนาดวัดจากรูปด้าน A203)
            win = [((ya + yb) / 2, 1.20, 0.90, 1.10)] if k in (0, 9) else []
            add_wall(f'W-F{f}-{side}G{k+1}-RM', f, 'y', gw(GX[k]), ya + cd, yb - cd, z0, beam_soffit(f, 'main'), tw, tp, win,
                     name=f'ผนังกั้นห้องกริด {k+1} ชั้น {f} ฝั่ง {side}' + (' (ผนังริม มีหน้าต่าง)' if win else ''))
            ya, yb = lo(y_out, y_rm)
            # ฝั่ง N เสาอยู่ที่ yb (แนว B), ฝั่ง S เสาอยู่ที่ ya (แนว E): เว้นระยะเสาด้านที่ชนเสา (เดิมฝั่ง S ล้ำเข้าเนื้อเสา, ผู้ใช้แจ้ง 10 พ.ย. 2569)
            # กริดริม (1, 10): เริ่มที่ผิวในผนังนอกแนว A/F (ผนังนอกวิ่งผ่านถึงมุมอาคาร); กริดใน: ชนศูนย์ผนังนอก
            # กริดใน: ปลายผนังถึงผิวนอกแนว A/F ไม่เหลือร่อง (ผู้ใช้สั่ง 11 พ.ย. 2569)
            eo = WALL_T if k in (0, 9) else 0.0
            ba, bb = (ya + eo, yb - cd) if side == 'N' else (ya + cd, yb - eo)
            add_wall(f'W-F{f}-{side}G{k+1}-BL', f, 'y', gw(GX[k]), ba, bb, zs, beam_soffit(f, 'main', True), tw, tp,
                     name=f'ผนังกั้นระเบียงกริด {k+1} ชั้น {f} ฝั่ง {side}')

# ผนังปลายทางเดินด้านขวา (กริด 10 ระหว่างเสาแนว C–D) ชั้น 2–5: ก่ออิฐฉาบปูน
# (เดิมเป็นหน้าต่างบานเกล็ด 1.20x1.10; ผู้ใช้เปลี่ยนเป็นประตูหนีไฟ D33 ตามแบบ A102 10 พ.ย. 2569)
for f in (2, 3, 4, 5):
    cd = col_d(f)
    # ผู้ใช้แจ้ง 10 พ.ย. 2569 (ตามแบบ A102): ประตู D33 ออกบันไดหนีไฟภายนอก ประตูเหล็กทนไฟ Professional Door FD1G 86.4x204.8 ซม. สีเทา
    # เปิดซ้าย ผลักออกด้านนอก; ศูนย์กลางช่องวัดจากแบบ A102 ห่างแนว C 1.27 ม. (ไปทางแนว D)
    add_wall(f'W-F{f}-COR-G10', f, 'y', gw(GX[9]), yC + cd, yD - cd, FL[f], beam_soffit(f, 'main'), wall_task[f], plaster_task[f],
             [(yC + 1.27, 0.864, 0.0, 2.048)], name=f'ผนังปลายทางเดินกริด 10 ชั้น {f} (ประตูหนีไฟ D33 0.864x2.048)')
    elements[-1]['name'] = f'ประตูเหล็กทนไฟ D33 0.864x2.048 ใน W-F{f}-COR-G10'
    elements[-1]['qty'].update(type='ประตูเหล็กทนไฟ ออกบันไดหนีไฟ', model='Professional Door FD1G 86.4x204.8 ซม. สีเทา (เปิดซ้าย ผลักออกด้านนอก) MegaHome 1308235', swing='เปิดซ้าย ผลักออกด้านนอก')

# ผนังปลายทางเดินด้านซ้าย (กริด 1 ระหว่างเสาแนว C–D) ชั้น 2–5: ก่ออิฐฉาบปูน + หน้าต่างบานเกล็ด
# ขนาดและชนิดเดียวกับหน้าต่างห้องริม W3 (1.20x1.10 ขอบล่าง 0.90) วางกลางทางเดิน (ผู้ใช้กำหนด 10 พ.ย. 2569)
for f in (2, 3, 4, 5):
    cd = col_d(f)
    add_wall(f'W-F{f}-COR-G1', f, 'y', gw(GX[0]), yC + cd, yD - cd, FL[f], beam_soffit(f, 'main'), wall_task[f], plaster_task[f],
             [((yC + yD) / 2, 1.20, 0.90, 1.10)], name=f'ผนังปลายทางเดินกริด 1 ชั้น {f} (หน้าต่างบานเกล็ด 1.20x1.10)')
    elements[-1]['name'] = f'หน้าต่างบานเกล็ด 1.20x1.10 ปลายทางเดิน ใน W-F{f}-COR-G1'
    elements[-1]['qty'].update(type='หน้าต่างบานเกล็ด (ขนาดและชนิดเดียวกับหน้าต่างห้องริม W3)')

# ---------- ชั้น 1 ----------
z0 = FL[1]
cd, cw = col_d(1), col_w(1)
# โถงบันได (กริด 4–5) จากขอบนอกถึงแนว C
for k in (3, 4):
    add_wall(f'W-F1-ST-G{k+1}A', 1, 'y', GX[k], OUT_C, yB - cd, z0, beam_soffit(1, 'main', True), 'A04', 'A12', name=f'ผนังโถงบันไดชั้น 1 กริด {k+1} ช่วงยื่น')
    add_wall(f'W-F1-ST-G{k+1}B', 1, 'y', GX[k], yB + cd, yC - cd, z0, beam_soffit(1, 'main'), 'A04', 'A12', name=f'ผนังโถงบันไดชั้น 1 กริด {k+1}')
# ผนังนอกโถงบันไดแนว A (หลังชานพัก): ก่อระหว่างคาน BST3 ของชานพักแต่ละชั้น
# หน้าต่างบานกระทุ้ง 1.20x0.60 ขอบล่างสูง 1.50 จากพื้นชานพัก (ผู้ใช้กำหนด 10 พ.ย. 2569)
_zm = [FL[f] + 10 * RISER for f in (1, 2, 3, 4)]          # ระดับพื้นชานพัก
_segs = [(FL[1], _zm[0] - 0.40, 1, None)]                   # ใต้ชานพักแรก
for k in range(4):
    top = _zm[k + 1] - 0.40 if k < 3 else ROOF_BEAM
    _segs.append((_zm[k], top, k + 1, _zm[k]))
for n, (za, zb, f, zland) in enumerate(_segs):
    fl = max(ff for ff in FL if FL[ff] <= za + 1e-6)
    tw = wall_task[fl]
    tp = 'A12' if fl == 1 else plaster_task[fl]
    win = [((GX[3] + GX[4]) / 2, 1.20, 1.50, 0.60)] if zland is not None else []
    # ก่อชนผิวฉาบเสา CX 200x200 ที่แนว A กริด 4/5 (เดิมเว้นตามเสา C1 ทำให้มีช่องแสงข้างเสา, ผู้ใช้แจ้ง 11 พ.ย. 2569); ช่วงคาน B3 ตัดรอบคานด้านล่าง
    add_wall(f'W-ST-OUT-{n}', fl, 'x', OUT_C, GX[3] + 0.10 + 0.010, GX[4] - 0.10 - 0.010, za, zb, tw, tp, win,
             name=f'ผนังนอกโถงบันได ช่วง {n}' + (f' หน้าต่างบานกระทุ้ง 1.20x0.60 (ชานพัก +{zland:.2f})' if win else ''))
ASSUMPTIONS.append('ผนังนอกโถงบันไดแนว A ก่อระหว่างคาน BST3 ชานพัก; ช่วงบนสุดก่อจากชานพักชั้น 4 ถึง +16.30; หน้าต่างบานกระทุ้ง 1.20x0.60 สูง 1.50 จากพื้นชานพัก')
# ร้านค้า 3 ห้อง (กริด 5–8) หน้าร้านแนว B ด้านหลังแนว C
for i in (4, 5, 6):
    # หน้าร้านอยู่ด้านใต้ถุน (แนว C) ประตูม้วน, ด้านหลัง (แนว B) ประตู 0.90 (ผู้ใช้แจ้ง 10 พ.ย. 2569)
    add_wall(f'W-F1-SH{i-3}-FR', 1, 'x', yC, GX[i] + cw, GX[i + 1] - cw, z0, beam_soffit(1, 'main'), 'A04', 'A13',
             [((GX[i] + GX[i + 1]) / 2, 3.00, 0.0, beam_soffit(1, 'main') - z0)], name=f'ผนังหน้าร้าน {i-3} (แนว C ด้านใต้ถุน) ช่องประตูม้วน 3.00 ม. สูงถึงใต้คาน')
    add_wall(f'W-F1-SH{i-3}-BK', 1, 'x', yB, GX[i] + cw, GX[i + 1] - cw, z0, beam_soffit(1, 'main'), 'A04', 'A13',
             [(GX[i] + 0.75, 0.90, 0.0, 2.00)], name=f'ผนังหลังร้าน {i-3} (แนว B) ประตู 0.90')
for k in (5, 6, 7):
    add_wall(f'W-F1-SH-G{k+1}', 1, 'y', GX[k], yB + cd, yC - cd, z0, beam_soffit(1, 'main'), 'A04', 'A13', name=f'ผนังกั้นร้านกริด {k+1}')
# ห้องน้ำชาย (กริด 8–9) / หญิง (กริด 9–10) ชั้น 1 ตามแบบ A901 (ผู้ใช้ส่ง 10 พ.ย. 2569) A14 ทั้งก่อและฉาบ
# ระยะวัดจากแบบ A901 (1:25) อ้างอิงแนว B; ทางเข้าแนว C เป็นช่องโล่งไม่มีบานชิดเสาด้านขวา, ผนังกั้นกลางห้องมีประตู 0.80
F1_WC_MW = yB + 3.50                     # ผนังกั้นกลางห้อง (ห้องส้วม/โถปัสสาวะ ด้าน B, อ่างล้างมือรวม ด้าน C)
F1_PART_H = 2.10                         # ผนังกั้นห้องส้วมสูง 2.10 (สมมติ)
UR_MODEL = 'กะรัต K-17392X (ฟลัชวาล์ว K-11702X-CP) ขอบบนสูง 0.61'
US_MODEL = 'NASCO NU-961-WA สีขาว เซรามิก 15x29.2x61.5 ซม. (HomePro 1122510)'
_zmw = FL[2] - SLAB_T                    # ผนังกั้นกลางห้องก่อถึงใต้ท้องพื้นชั้น 2 (ไม่มีคานแนวนี้)
_hw = WALL_T / 2
_fx = lambda eid, name, x0, x1, y0, y1, za, t, **q: add(eid, 'สุขภัณฑ์', 1, 'A21',
                                                         prism([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], za, t),
                                                         name=name, assumed=True, qty=dict(count=1, **q))
for i in (7, 8):
    n = i - 6
    room = 'ห้องน้ำชาย' if i == 7 else 'ห้องน้ำหญิง'
    xl, xr = gw(GX[i]) + _hw, gw(GX[i + 1]) - _hw                  # แนวผิวกลางผนังกริดซ้าย/ขวา (ผนังชนกัน)
    fl, fr = GX[i] + _hw + PL_T, GX[i + 1] - _hw - PL_T    # ผิวฉาบผนังกริด
    # หน้าต่างระบายอากาศ W1 0.60x0.40 ขอบล่าง 1.80 เหมือนห้องน้ำห้องพัก ห้องละ 2 จุด (ผู้ใช้สั่ง 10 พ.ย. 2569)
    # ตำแหน่ง: กึ่งกลางช่วงผนังแต่ละฝั่งของผนังหน้าห้องส้วม (ฝั่งห้องส้วม 1 จุด ฝั่งที่ล้างมือ 1 จุด)
    _xf = GX[i] + (1.79 if i == 7 else 1.80)
    _a0, _a1 = GX[i] + cw, GX[i + 1] - cw
    add_wall(f'W-F1-WC{n}-FR', 1, 'x', yB, _a0, _a1, z0, beam_soffit(1, 'main'), 'A14', 'A14',
             [((_a0 + _xf) / 2, 0.60, 1.80, 0.40), ((_xf + _a1) / 2, 0.60, 1.80, 0.40)],
             name=f'ผนัง{room}ชั้น 1 ด้านหลังอาคาร (แนว B) หน้าต่าง W1 0.60x0.40 x2')
    for _e in elements[-2:]:
        if _e['id'].startswith(f'W-F1-WC{n}-FR-O'):
            _e.update(name=f"หน้าต่าง W1 0.60x0.40 ระบายอากาศ ใน W-F1-WC{n}-FR")
            _e['qty'].update(type='หน้าต่างบานกระจกซ้อน อะลูมิเนียม', model=W1_MODEL)
    # แนว C: ผนังจากเสาซ้ายยาว 2.20 (ชาย) / 2.35 (หญิง) ที่เหลือเป็นช่องทางเข้าโล่งถึงเสาขวา (A901)
    add_wall(f'W-F1-WC{n}-BK', 1, 'x', yC, GX[i] + cw, GX[i] + 0.15 + (2.20 if i == 7 else 2.35), z0, beam_soffit(1, 'main'), 'A14', 'A14',
             name=f'ผนัง{room}ชั้น 1 ด้านใต้ถุน (แนว C) ช่องทางเข้าโล่ง ไม่มีบาน')
    # ผนังกั้นกลางห้อง ประตู 0.80x2.00 ชิดผนังกริด 9
    add_wall(f'W-F1-WC{n}-MW', 1, 'x', F1_WC_MW, xl, xr, z0, _zmw, 'A14', 'A14',
             [((27.33 if i == 7 else 28.65), 0.80, 0.0, 2.00)], name=f'ผนังกั้นกลาง{room}ชั้น 1 ประตู 0.80x2.00')
    if i == 7:   # ชาย: ห้องส้วม 2 ห้องชิดผนังกริด 8, โถปัสสาวะ 3 โถ บนผนังกั้นกลาง
        xf = GX[i] + 1.79
        add_wall(f'W-F1-WC{n}-CF', 1, 'y', xf, yB + _hw, yB + 2.25 + _hw, z0, z0 + F1_PART_H, 'A14', 'A14',
                 [(yB + 0.49, 0.70, 0.0, 2.00), (yB + 1.70, 0.70, 0.0, 2.00)], name=f'ผนังหน้าห้องส้วม{room}ชั้น 1 ประตู 0.70x2.00 x2')
        for j, yp in enumerate((yB + 1.06, yB + 2.25)):
            add_wall(f'W-F1-WC{n}-P{j+1}', 1, 'x', yp, xl, xf - _hw, z0, z0 + F1_PART_H, 'A14', 'A14', name=f'ผนังกั้นห้องส้วม{room}ชั้น 1')
        for j, yc in enumerate((yB + 0.43, yB + 1.655)):
            _fx(f'FX-F1-WC{n}-{j+1}', f'โถส้วม {room}ชั้น 1 ห้อง {j+1}', fl + 0.13, fl + 0.84, yc - 0.20, yc + 0.20, z0 + 0.02, 0.40)
        yw = F1_WC_MW - _hw - PL_T                          # ผิวผนังกั้นกลางด้านห้องส้วม
        for j, xc_ in enumerate((GX[i] + 0.34, GX[i] + 1.14, GX[i] + 1.94)):
            _fx(f'FX-F1-WC{n}-UR{j+1}', f'โถปัสสาวะชาย {room}ชั้น 1 ตัวที่ {j+1}', xc_ - 0.148, xc_ + 0.148, yw - 0.306, yw, z0 + 0.18, 0.43, model=UR_MODEL)
        for j, xc_ in enumerate((GX[i] + 0.74, GX[i] + 1.54, GX[i] + 2.26)):
            _fx(f'FX-F1-WC{n}-US{j+1}', f'แผงกั้นโถปัสสาวะ {room}ชั้น 1 ตัวที่ {j+1}', xc_ - 0.075, xc_ + 0.075, yw - 0.292, yw, z0 + 0.45, 0.615, model=US_MODEL)
        lav_x = (fr - 0.45, fr)
        tr_x = (fl, fl + 2.135)
    else:        # หญิง: ห้องส้วม 3 ห้องชิดผนังกริด 10
        xf = GX[i] + 1.80
        add_wall(f'W-F1-WC{n}-CF', 1, 'y', xf, yB + _hw, F1_WC_MW - _hw, z0, z0 + F1_PART_H, 'A14', 'A14',
                 [(yB + 0.437, 0.70, 0.0, 2.00), (yB + 1.70, 0.70, 0.0, 2.00), (yB + 2.95, 0.70, 0.0, 2.00)],
                 name=f'ผนังหน้าห้องส้วม{room}ชั้น 1 ประตู 0.70x2.00 x3')
        for j, yp in enumerate((yB + 1.11, yB + 2.31)):
            add_wall(f'W-F1-WC{n}-P{j+1}', 1, 'x', yp, xf + _hw, xr, z0, z0 + F1_PART_H, 'A14', 'A14', name=f'ผนังกั้นห้องส้วม{room}ชั้น 1')
        for j, yc in enumerate((yB + 0.46, yB + 1.71, yB + 2.91)):
            _fx(f'FX-F1-WC{n}-{j+1}', f'โถส้วม {room}ชั้น 1 ห้อง {j+1}', fr - 0.84, fr - 0.11, yc - 0.20, yc + 0.20, z0 + 0.02, 0.40)
        lav_x = (fl, fl + 0.45)
        tr_x = (fr - 2.135, fr)
    # อ่างล้างหน้า K1225 2 อ่าง ติดผนังกริด 9
    for j, yc in enumerate((yB + 0.53, yB + 1.33)):
        _fx(f'FX-F1-WC{n}-LAV{j+1}', f'อ่างล้างหน้า {room}ชั้น 1 ตัวที่ {j+1}', lav_x[0], lav_x[1], yc - 0.25, yc + 0.25, z0 + 0.65, 0.20)
    # อ่างล้างมือรวม ก่ออิฐปูกระเบื้อง ยาว 2.135 ลึก 0.545 ขอบสูง 0.60 มี 3 ก๊อก (แอ่งลึก 0.15 สมมติ)
    ty0 = F1_WC_MW + _hw + PL_T
    ty1 = ty0 + 0.545
    rim = 0.075
    parts = [prism([(tr_x[0], ty0), (tr_x[1], ty0), (tr_x[1], ty1), (tr_x[0], ty1)], z0, 0.45)]
    for (ax0, ax1, ay0, ay1) in ((tr_x[0], tr_x[1], ty0, ty0 + rim), (tr_x[0], tr_x[1], ty1 - rim, ty1),
                                 (tr_x[0], tr_x[0] + rim, ty0 + rim, ty1 - rim), (tr_x[1] - rim, tr_x[1], ty0 + rim, ty1 - rim)):
        parts.append(prism([(ax0, ay0), (ax1, ay0), (ax1, ay1), (ax0, ay1)], z0 + 0.45, 0.15))
    add(f'FX-F1-WC{n}-TR', 'สุขภัณฑ์', 1, 'A21', dict(type='multi', parts=parts),
        name=f'อ่างล้างมือรวม ก่ออิฐปูกระเบื้อง {room}ชั้น 1 (2.135x0.545 สูง 0.60, 3 ก๊อก)', assumed=True,
        qty=dict(count=1, length=2.135, depth=0.545, height=0.60, taps=3, type='อ่างล้างมือรวม ก่ออิฐปูกระเบื้อง'))
for k in (8, 9):
    add_wall(f'W-F1-WC-G{k+1}', 1, 'y', gw(GX[k]), yB + cd, yC - cd, z0, beam_soffit(1, 'main'), 'A14', 'A14', name=f'ผนังห้องน้ำชั้น 1 กริด {k+1}')
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
    _cz = SLAB_ZONES[f]
    _parts = [rects_geom([r], top - (S1_T if k == 'WC' else SLAB_T) - PL_T, PL_T) for _, k, rs, top in _cz for r in rs
              if r[1] - r[0] > 1e-6 and r[3] - r[2] > 1e-6]
    add(f'PL-CEIL-F{f}', 'งานฉาบ', f - 1, task, dict(type='multi', parts=_parts),
        name=f'ฉาบใต้ท้องพื้นชั้น {f} (เพดานชั้น {f-1})', assumed=True,
        qty=dict(area=round(sum(rect_area(rs) for _, _, rs, _ in _cz), 3)))
TILE_ROOM = dict(size='60x60 ซม.', w=0.60, model='ระบุภายหลัง')
# ห้องน้ำ: กระเบื้องลายเทา 16x16 นิ้ว ยาแนว 3 มม. (ผู้ใช้กำหนด 10 พ.ย. 2569, รุ่นตามรูปที่ผู้ใช้ส่ง)
TILE_WC = dict(size='16x16 นิ้ว', w=0.4064, model='ลายเทา 16x16 นิ้ว (ตามรูปผู้ใช้)', joint=0.003, material='กระเบื้องห้องน้ำ ลายเทา 16x16 ยาแนว 3 มม.')
ASSUMPTIONS.append('กระเบื้องห้องพัก โถงทางเดิน ระเบียง และโถงบันได 60x60 ซม., ห้องน้ำ 16x16 นิ้ว (ผู้ใช้กำหนด รุ่นระบุภายหลัง); จำนวนแผ่นคิดสุทธิไม่รวมเผื่อเสีย')


# กระเบื้องห้องพักและโถงทางเดิน: Tara รุ่นเจด้าไวท์ 60x60 ซม. ยาแนว 3 มม. (ผู้ใช้กำหนด 10 พ.ย. 2569)
TILE_TARA = dict(size='60x60 ซม.', w=0.60, model='Tara เจด้าไวท์ 60x60 ซม.', joint=0.003)
TILE_MAT = 'Tara เจด้าไวท์ 60x60 ยาแนว 3 มม.'
# ห้องพัก: Tara รุ่นเจเลนวูด 60x60 ซม. (ผู้ใช้กำหนด 10 พ.ย. 2569) ยาแนว 3 มม. และแนวการปูเหมือนทางเดิน
TILE_TARA_WOOD = dict(size='60x60 ซม.', w=0.60, model='Tara เจเลนวูด 60x60 ซม.', joint=0.003, material='Tara เจเลนวูด 60x60 ยาแนว 3 มม.')
ASSUMPTIONS.append('แนวกระเบื้อง Tara (ห้องพักเจเลนวูด, ทางเดินเจด้าไวท์; ยาแนว 3 มม. ของเจเลนวูดใช้ตามเจด้าไวท์): แนวยาวขวางอาคาร (y) เริ่มจากร่องยาแนวที่กึ่งกลางทางเดิน (แนว CX) ออกไปหาหลังห้องตามที่ผู้ใช้กำหนด; แนวตามยาวอาคาร (x) ผมกำหนดให้ร่องยาแนวอยู่กึ่งกลางห้อง และกึ่งกลางอาคารสำหรับทางเดิน (ค่าสมมติ)')


def tile_layout(x0, x1, y0, y1, ox, oy, pitch):
    """นับแผ่นเต็ม/แผ่นตัด เมื่อร่องยาแนวอยู่ที่ ox + k*pitch, oy + k*pitch"""
    def cells(a0, a1, o):
        k0, k1 = math.floor((a0 - o) / pitch + 1e-9), math.ceil((a1 - o) / pitch - 1e-9)
        out = []
        for k in range(k0, k1):
            c0, c1 = o + k * pitch, o + (k + 1) * pitch
            out.append(c0 >= a0 - 1e-6 and c1 <= a1 + 1e-6)
        return out
    cx, cy = cells(x0, x1, ox), cells(y0, y1, oy)
    full = sum(1 for a in cx for b in cy if a and b)
    return full, len(cx) * len(cy) - full


def add_tile(eid, f, x0, x1, y0, y1, spec, name, z=None, origin=None):
    x0, x1, y0, y1 = min(x0, x1), max(x0, x1), min(y0, y1), max(y0, y1)
    area = (x1 - x0) * (y1 - y0)
    qty = dict(area=round(area, 3), tile_size=spec['size'], tile_model=spec['model'],
               tiles=math.ceil(area / (spec['w'] ** 2)))
    extra = {}
    if origin is not None:
        pitch = spec['w'] + spec['joint']
        full, cut = tile_layout(x0, x1, y0, y1, origin[0], origin[1], pitch)
        qty.update(tiles=full + cut, tiles_full=full, tiles_cut=cut, joint_mm=round(spec['joint'] * 1000, 1))
        extra = dict(material=spec.get('material', TILE_MAT), pitch=round(pitch, 4), origin=[round(origin[0], 4), round(origin[1], 4)])
    add(eid, 'กระเบื้อง', f, 'A16' if f < 5 else 'A17',
        prism([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], FL[f] if z is None else z, 0.02), name=name, assumed=True, qty=qty)
    if extra:
        elements[-1]['finish'] = extra


def _rects_minus(rects, bx0, bx1, by0, by1):
    out = []
    for x0, x1, y0, y1 in rects:
        if min(x1, bx1) - max(x0, bx0) <= 1e-6 or min(y1, by1) - max(y0, by0) <= 1e-6:
            out.append((x0, x1, y0, y1)); continue
        if x0 < bx0 - 1e-6: out.append((x0, bx0, y0, y1))
        if x1 > bx1 + 1e-6: out.append((bx1, x1, y0, y1))
        xa, xb = max(x0, bx0), min(x1, bx1)
        if y0 < by0 - 1e-6: out.append((xa, xb, y0, by0))
        if y1 > by1 + 1e-6: out.append((xa, xb, by1, y1))
    return out


def tile_cut_box(e, bx0, bx1, by0, by1, spec):
    """ตัดพื้นที่กล่อง (แนวแกน) ออกจากกระเบื้อง e (prism หรือ multi ของสี่เหลี่ยม) และนับแผ่นใหม่"""
    bx0, bx1, by0, by1 = min(bx0, bx1), max(bx0, bx1), min(by0, by1), max(by0, by1)
    g = e['geom']
    parts = g['parts'] if g['type'] == 'multi' else [g]
    z, t = parts[0]['z0'], parts[0]['t']
    rects = []
    for pt in parts:
        xs = [q[0] for q in pt['poly']]; ys = [q[1] for q in pt['poly']]
        rects.append((min(xs), max(xs), min(ys), max(ys)))
    rects = [r for r in _rects_minus(rects, bx0, bx1, by0, by1) if r[1] - r[0] > 1e-4 and r[3] - r[2] > 1e-4]
    ps = [prism([(a, c), (b, c), (b, d), (a, d)], z, t) for a, b, c, d in rects]
    e['geom'] = ps[0] if len(ps) == 1 else dict(type='multi', parts=ps)
    area = sum((b - a) * (d - c) for a, b, c, d in rects)
    q = e['qty']
    q['area'] = round(area, 3)
    if 'finish' in e:
        ox, oy = e['finish']['origin']
        cells = set()
        pitch = e['finish']['pitch']
        for a, b, c, d in rects:          # นับช่องแผ่นที่ถูกปู (แผ่นเต็ม = อยู่ในชิ้นใดชิ้นหนึ่งทั้งแผ่น)
            for kx in range(math.floor((a - ox) / pitch + 1e-9), math.ceil((b - ox) / pitch - 1e-9)):
                for ky in range(math.floor((c - oy) / pitch + 1e-9), math.ceil((d - oy) / pitch - 1e-9)):
                    c0, c1, r0, r1 = ox + kx * pitch, ox + (kx + 1) * pitch, oy + ky * pitch, oy + (ky + 1) * pitch
                    full = c0 >= a - 1e-6 and c1 <= b + 1e-6 and r0 >= c - 1e-6 and r1 <= d + 1e-6
                    cells.add((kx, ky, full))
        fulls = {(kx, ky) for kx, ky, fu in cells if fu}
        allc = {(kx, ky) for kx, ky, fu in cells}
        q.update(tiles=len(allc), tiles_full=len(fulls), tiles_cut=len(allc) - len(fulls))
    else:
        q['tiles'] = math.ceil(area / spec['w'] ** 2)


h = WALL_T / 2 + PL_T
for f in (2, 3, 4, 5):
    for side in ('N', 'S'):
        y_out, y_rm, y_cor = (0.0, yB, yC) if side == 'N' else (yF, yE, yD)
        o = OUT_C + h if side == 'N' else -(OUT_C + h)
        for i in range(9):
            tx0, tx1, bx0, bx1 = bay_split(i, side)
            x0, x1 = gw(GX[i]) + h, gw(GX[i + 1]) - h
            if side == 'N' and i == STAIR_BAY[0]:
                # โถงหน้าบันไดปูเจด้าไวท์เหมือนโถงทางเดิน (ผู้ใช้แจ้ง 10 พ.ย. 2569) แนวร่องต่อเนื่องกับทางเดิน
                add_tile(f'TL-F{f}-ST-HALL', f, x0, x1, sy1, yC + col_d(f) + PL_T, TILE_TARA, f'กระเบื้องโถงหน้าบันได ชั้น {f} Tara เจด้าไวท์ 60x60',
                         origin=((GX[0] + GX[-1]) / 2, GY['CX']))
                continue
            yw = cor_wall_y(side, f)
            ry0, ry1 = (y_rm + h, yw - h) if side == 'N' else (y_rm - h, yw + h)
            add_tile(f'TL-F{f}-{side}{i+1}-RM', f, x0, x1, ry0, ry1, TILE_TARA_WOOD, f'กระเบื้องห้องพัก ชั้น {f} ห้อง {side}{i+1} Tara เจเลนวูด 60x60',
                     origin=((GX[i] + GX[i + 1]) / 2, GY['CX']))
            wy0, wy1 = y_out + o, (y_rm - h if side == 'N' else y_rm + h)
            add_tile(f'TL-F{f}-{side}{i+1}-WC', f, max(gw(tx0) + h, x0), min(gw(tx1) - h, x1), wy0, wy1, TILE_WC, f'กระเบื้องห้องน้ำ ชั้น {f} ห้อง {side}{i+1} ลายเทา 16x16 นิ้ว', z=FL[f] - DROP,
                     origin=((max(gw(tx0) + h, x0) + min(gw(tx1) - h, x1)) / 2, (wy0 + wy1) / 2))
            # ช่องชาร์ฟ (A106): ตัดกระเบื้องห้องน้ำออกตามขนาดนอกช่องชาร์ฟรวมฉาบ
            g = wc_geo(i, side, f)
            tile_cut_box(elements[-1], g['xg'], g['xg'] + g['dr'] * (SH_W + PL_T), g['yr'], g['yr'] - g['s'] * (SH_D + PL_T), TILE_WC)
            # เจเลนวูดปูตั้งแต่แนวประตูหน้าห้องถึงแนวหลังระเบียง (ผู้ใช้กำหนด 10 พ.ย. 2569) แนวร่องต่อเนื่องจากห้องพัก
            add_tile(f'TL-F{f}-{side}{i+1}-BL', f, max(gw(bx0) + h, x0), min(gw(bx1) - h, x1), wy0, wy1, TILE_TARA_WOOD, f'กระเบื้องระเบียง ชั้น {f} ห้อง {side}{i+1} Tara เจเลนวูด 60x60', z=FL[f] - DROP,
                     origin=((GX[i] + GX[i + 1]) / 2, GY['CX']))
            # ใต้ช่องประตู (ความหนาผนัง+ฉาบ 0.10): เดิมกระเบื้องหยุดที่ผิวฉาบ เห็นผิวพื้นทับหน้าโผล่ (ผู้ใช้แจ้ง 10 พ.ย. 2569)
            # ปูเจเลนวูดต่อจากห้องพักผ่านช่องประตู ที่ระดับพื้นห้อง FL (ฝั่งระเบียง/ห้องน้ำลดระดับที่ผิวผนัง)
            for k, (cx, w, yy) in enumerate((((GX[i] + 0.75), 0.90, yw), (g['d2'], D2_W, y_rm), (g['d3'], 0.70, y_rm))):
                add_tile(f'TL-F{f}-{side}{i+1}-TH{k+1}', f, cx - w / 2, cx + w / 2, yy - h, yy + h, TILE_TARA_WOOD,
                         f'กระเบื้องใต้ช่อง{("ประตูหน้าห้อง", "ประตูระเบียง", "ประตูห้องน้ำ")[k]} ชั้น {f} ห้อง {side}{i+1} Tara เจเลนวูด 60x60',
                         origin=((GX[i] + GX[i + 1]) / 2, GY['CX']))
    # เริ่มที่ผิวฉาบผนังปลายทางเดินกริด 1 (เพิ่ม 10 พ.ย. 2569)
    add_tile(f'TL-F{f}-COR', f, gw(GX[0]) + WALL_T / 2 + PL_T, gw(GX[9]) - WALL_T / 2 - PL_T, yC + col_d(f) + PL_T, yD - col_d(f) - PL_T, TILE_TARA, f'กระเบื้องโถงทางเดิน ชั้น {f} Tara เจด้าไวท์ 60x60',
             origin=((GX[0] + GX[-1]) / 2, GY['CX']))
# ห้องน้ำรวมชั้น 1: กระเบื้องลายเทา 16x16 นิ้ว ยาแนว 3 มม. (แทนรายการเดิมที่ยังไม่ระบุรุ่น)
_cw1, _cd1 = col_w(1), col_d(1)
elements[:] = [e for e in elements if e['id'] != 'TL-F1-WC']
_wx0, _wx1, _wy0, _wy1 = GX[7] + _cw1, GX[9] - _cw1, yB + _cd1, yC - _cd1
add_tile('TL-F1-WC', 1, _wx0, _wx1, _wy0, _wy1, TILE_WC, 'กระเบื้องพื้นห้องน้ำชั้น 1 ลายเทา 16x16 นิ้ว', origin=((_wx0 + _wx1) / 2, (_wy0 + _wy1) / 2))
elements[-1]['task'] = 'A14'
# ผังใหม่ A901: ตัดกระเบื้องใต้ผนังกั้นภายใน (ก่อ/เอ็น/ฉาบ) และใต้อ่างล้างมือรวม
_tl1 = elements[-1]
for e in [e for e in elements if re.match(r'^(W-F1-WC\d-(MW|CF|P\d)|W-F1-WC-G9|FX-F1-WC\d-TR)', e['id']) and not re.search(r'-O\d+$', e['id'])]:
    gg = e['geom']
    for pt in (gg['parts'] if gg['type'] == 'multi' else [gg]):
        if pt['type'] == 'prism' and pt['z0'] <= FL[1] + 0.02:
            xs = [q[0] for q in pt['poly']]; ys = [q[1] for q in pt['poly']]
            tile_cut_box(_tl1, min(xs), max(xs), min(ys), max(ys), TILE_WC)
# ---------- งานไฟฟ้าแสงสว่างในห้องพัก (ผู้ใช้กำหนด 10 พ.ย. 2569) ----------
# ส่วนที่ไม่ผูกกับผังห้องน้ำ: ตู้คอนซูมเมอร์เหนือประตูเข้า, สวิตช์+เต้ารับข้างประตูเข้า (ฝั่งมือจับ ห่างวงกบ 0.15),
# โคมรางตัวยู T8 1x18 กลางห้อง และท่อ PVC ขาว Ø1/2" เดินลอยบนผนังชิดใต้คาน มี junction box ทุกจุดแยกท่อ
# วงจรหลังห้อง (สวิตช์ 2 ตัวหน้าห้องน้ำ เต้ารับคู่มุมห้อง โคมห้องน้ำ/หลังห้อง) ต่อจากโคมกลางห้อง
EL_PIPE = 0.018                  # ท่อ PVC 1/2" ขนาดโตนอก 18 มม.
EL_BOX = (0.12, 0.075, 0.045)    # บล็อกลอย 2x4 นิ้ว วางนอน (กว้าง, สูง, ลึก)
EL_CU = (0.25, 0.22, 0.10)       # ตู้คอนซูมเมอร์ RACER เมน+4 ช่อง (ขนาดประมาณจากรูป)
EL_JB = (0.08, 0.04)             # junction box กลม Ø0.08 ลึก 0.04 (ค่าสมมติ)
EL_LAMP = (0.63, 0.07, 0.05)     # โคมรางตัวยู T8 1x18 (ยาว, กว้าง, สูง)
EL_SW_Z, EL_CU_Z = 1.20, 2.10    # ความสูงสวิตช์ / ขอบล่างตู้ จากพื้น (ผู้ใช้กำหนด)
EL_SO_Z = 0.30                   # ความสูงเต้ารับ (ผู้ใช้กำหนด)
EL_WL = (0.30, 0.08, 0.08)       # โคมติดผนังห้องน้ำ/หลังห้อง (ยาว, ยื่น, สูง) ค่าสมมติ รอรุ่น
CEIL5 = 2.60                     # ฝ้าชั้น 5 สูงจากพื้น (ผู้ใช้กำหนด)
ASSUMPTIONS.append('วงจรหลังห้อง: สวิตช์ 2 ตัวอยู่กึ่งกลางผนังกลางระหว่าง D3 กับ D2; เต้ารับคู่บนผนังกั้นห้องฝั่ง D2 ถัดผิวเสา 0.15 ม.; ท่อแยกจากโคมกลางห้องไปตามท้องพื้นถึงผนังห้อง–ระเบียง ลอดผนังที่แนว B5 ไปโคมห้องน้ำ/หลังห้อง (ตำแหน่งตีความจากคำสั่งผู้ใช้); โคมติดผนัง 0.30x0.08x0.08 ม. ยังไม่ระบุรุ่น')
ASSUMPTIONS.append('งานไฟฟ้าห้องพัก: ท่อ PVC Ø1/2" เดินลอยบนผนังที่ระดับใต้ท้องคาน 0.03 ม. (ชั้น 5 เหนือฝ้า +0.05), ลอดใต้คานแล้วขึ้นข้างคานไปตามท้องพื้นถึงโคมกลางห้อง; ขนาดบล็อก 2x4 นิ้ว ตู้ 0.25x0.22x0.10 และ junction box Ø0.08 เป็นค่าสมมติ; ฝั่งมือจับประตูตรวจจากบานประตูในโมเดล (ฝั่ง +x ของช่องประตูทุกห้อง)')


def el_pipe(p0, p1):
    return dict(type='member', p0=[round(v, 4) for v in p0], p1=[round(v, 4) for v in p1], w=EL_PIPE, d=EL_PIPE,
                shape='O', sec=dict(d=EL_PIPE))


def el_box_on_x_wall(xc, yface, dn, zc, w, h, dpt):
    """กล่องติดผนังแนวแกน x (ผิวผนังที่ y = yface) ยื่นเข้าห้องทิศ dn"""
    y0, y1 = sorted((yface, yface + dn * dpt))
    return prism([(xc - w / 2, y0), (xc + w / 2, y0), (xc + w / 2, y1), (xc - w / 2, y1)], zc - h / 2, h)


def el_add(eid, f, geom, name, qty):
    add(eid, 'ไฟฟ้า', f, 'A21', geom, name=name, assumed=True, qty=qty)


for f in (2, 3, 4, 5):
    for side in ('N', 'S'):
        dn = -1 if side == 'N' else 1                       # ทิศจากผนังทางเดินเข้าห้อง
        for i in range(9):
            if side == 'N' and i == STAIR_BAY[0]:
                continue
            tag = f'F{f}-{side}{i+1}'
            room = f'ชั้น {f} ห้อง {side}{i+1}'
            yface = cor_wall_y(side, f) + dn * (WALL_T / 2 + PL_T)       # ผิวฉาบผนังทางเดินด้านในห้อง
            yp = yface + dn * (EL_PIPE / 2 + 0.003)                      # แนวศูนย์ท่อบนผนัง
            fl = FL[f]
            if f < 5:
                zr = beam_soffit(f, 'main') - 0.03                       # ชิดใต้ท้องคาน
                ceil = FL[f + 1] - SLAB_T - PL_T                         # ผิวฉาบใต้ท้องพื้น
            else:
                ceil = fl + CEIL5
                zr = ceil + 0.05                                         # ชั้น 5 เดินเหนือฝ้าทีบาร์
            x_cu = GX[i] + 0.75                                          # กึ่งกลางประตูเข้า
            x_sw = GX[i] + 1.20 + 0.15 + EL_BOX[0] / 2                   # ฝั่งมือจับ (+x) ห่างวงกบ 0.15
            x_l = (GX[i] + GX[i + 1]) / 2
            y_rmface = (yB if side == 'N' else yE) - dn * (WALL_T / 2 + PL_T)
            y_l = (y_rmface + yface) / 2
            cu_top = fl + EL_CU_Z + EL_CU[1]
            el_add(f'EL-{tag}-CU', f, el_box_on_x_wall(x_cu, yface, dn, fl + EL_CU_Z + EL_CU[1] / 2, *EL_CU),
                   f'ตู้คอนซูมเมอร์ 4 วงจร เหนือประตูเข้า {room}', dict(count=1, model='RACER เมน+4 ช่อง', bottom=EL_CU_Z))
            el_add(f'EL-{tag}-SW1', f, el_box_on_x_wall(x_sw, yface, dn, fl + EL_SW_Z, *EL_BOX),
                   f'สวิตช์ไฟ+เต้ารับ ข้างประตูเข้า {room}', dict(count=1, box='บล็อกลอย 2x4 นิ้ว', height=EL_SW_Z))
            ly0, ly1 = y_l - EL_LAMP[1] / 2, y_l + EL_LAMP[1] / 2
            el_add(f'EL-{tag}-LP1', f, prism([(x_l - EL_LAMP[0] / 2, ly0), (x_l + EL_LAMP[0] / 2, ly0), (x_l + EL_LAMP[0] / 2, ly1), (x_l - EL_LAMP[0] / 2, ly1)],
                                             ceil - EL_LAMP[2], EL_LAMP[2]),
                   f'โคมรางตัวยู T8 1x18W กลางห้อง {room}', dict(count=1, model='T8 1x18 หลอดเดี่ยว'))
            for k, xj in ((1, x_cu), (2, x_sw)):
                el_add(f'EL-{tag}-JB{k}', f, el_pipe((xj, yface, zr), (xj, yface + dn * EL_JB[1], zr)) | dict(w=EL_JB[0], d=EL_JB[0], sec=dict(d=EL_JB[0])),
                       f'Junction box {k} {room}', dict(count=1, size='Ø0.08'))
            # ท่อ: ตู้→JB1 (ขึ้น), JB1→JB2 (ตามผนัง), JB2→สวิตช์ (ลง), JB2→โคมกลางห้อง
            yb = (yC + B2_DY['C'] - 0.125 - 0.03) if side == 'N' else (yD + B2_DY['D'] + 0.125 + 0.03)  # พ้นผิวคานแนว C/D ด้านในห้อง
            runs = [((x_cu, yp, cu_top), (x_cu, yp, zr)), ((x_cu, yp, zr), (x_sw, yp, zr)),
                    ((x_sw, yp, zr), (x_sw, yp, fl + EL_SW_Z + EL_BOX[1] / 2)), ((x_sw, yp, zr), (x_l, yp, zr))]
            ye = y_l - dn * EL_LAMP[1] / 2
            if f < 5:
                zc = ceil - EL_PIPE / 2
                runs += [((x_l, yp, zr), (x_l, yb, zr)), ((x_l, yb, zr), (x_l, yb, zc)), ((x_l, yb, zc), (x_l, ye, zc))]
            else:
                runs += [((x_l, yp, zr), (x_l, y_l, zr)), ((x_l, y_l, zr), (x_l, y_l, ceil))]
            L = sum(math.dist(a, b) for a, b in runs)
            el_add(f'EL-{tag}-CD1', f, dict(type='multi', parts=[el_pipe(a, b) for a, b in runs]),
                   f'ท่อร้อยสาย PVC ขาว Ø1/2" ตู้–สวิตช์–โคมกลางห้อง {room}', dict(length=round(L, 3), size='PVC 1/2"'))
            # --- วงจรหลังห้อง (ผู้ใช้กำหนด 10 พ.ย. 2569) ---
            # สวิตช์ 2 ตัวในกล่องเดียว ที่ผนังกลางระหว่างประตูห้องน้ำ D3 กับประตูบานเลื่อน D2 (หน้าห้องน้ำ) สูง 1.20
            # เต้ารับคู่ 1 กล่อง มุมห้องก่อนออกระเบียง (ผนังกั้นห้องฝั่ง D2 ถัดจากเสา) สูง 0.30
            # โคมห้องน้ำ: ผนังกั้นห้องน้ำ–ระเบียง (B5) ฝั่งห้องน้ำ สูง 2.40 / โคมหลังห้อง: ผนังเดียวกัน ฝั่งระเบียง สูง 2.50
            g = wc_geo(i, side, f)
            sr, dr, b5, xb = g['s'], g['dr'], b5x(i, side), (GX[i] if g['xc'] == GX[i + 1] else GX[i + 1])
            y_bal = yB if side == 'N' else yE                                   # แนวผนังห้อง–ระเบียง/ห้องน้ำ
            off = EL_PIPE / 2 + 0.003
            wf = WALL_T / 2 + PL_T
            yq = y_bal + sr * (wf + off)                                         # แนวท่อบนผิวผนังด้านห้อง
            x_s2 = ((g['d3'] + dr * 0.35) + (g['d2'] - dr * D2_W / 2)) / 2      # กึ่งกลางผนังกลางระหว่าง D3 กับ D2
            el_add(f'EL-{tag}-SW2', f, el_box_on_x_wall(x_s2, y_bal + sr * wf, sr, fl + EL_SW_Z, *EL_BOX),
                   f'สวิตช์ 2 ตัวในกล่องเดียว (โคมห้องน้ำ + โคมหลังห้อง) หน้าห้องน้ำ {room}',
                   dict(count=1, box='บล็อกลอย 2x4 นิ้ว', gang=2, height=EL_SW_Z))
            x_pw = gw(xb) - dr * wf                                                  # ผิวผนังกั้นห้องฝั่ง D2
            cwf, cdf = col_w(f), col_d(f)
            COL_PL = 0.01                                                        # ฉาบเสา 1 ซม.
            y_so = y_bal + sr * (cdf + 0.15 + EL_BOX[0] / 2)                     # ถัดผิวเสา 0.15
            y0, y1 = y_so - EL_BOX[0] / 2, y_so + EL_BOX[0] / 2
            xa, xz = sorted((x_pw, x_pw - dr * EL_BOX[2]))
            el_add(f'EL-{tag}-SO1', f, prism([(xa, y0), (xz, y0), (xz, y1), (xa, y1)], fl + EL_SO_Z - EL_BOX[1] / 2, EL_BOX[1]),
                   f'เต้ารับคู่ 1 กล่อง มุมห้องก่อนออกระเบียง {room}', dict(count=1, box='บล็อกลอย 2x4 นิ้ว', outlets=2, height=EL_SO_Z))
            zs_ = fl - DROP
            y_lw = (g['yo'] + g['yr']) / 2                                       # กึ่งกลางผนัง B5 ในแถบห้องน้ำ/ระเบียง
            lamps = ((3, -1, 2.40, 'โคมห้องน้ำ ผนังกั้นห้องน้ำ–ระเบียง ฝั่งห้องน้ำ'), (4, 1, 2.50, 'โคมหลังห้อง ผนังกั้นห้องน้ำ–ระเบียง ฝั่งระเบียง'))
            for k, sgn, hz, nm in lamps:
                xf = b5 + sgn * dr * wf
                xa, xz = sorted((xf, xf + sgn * dr * EL_WL[1]))
                el_add(f'EL-{tag}-LP{k - 1}', f, prism([(xa, y_lw - EL_WL[0] / 2), (xz, y_lw - EL_WL[0] / 2), (xz, y_lw + EL_WL[0] / 2), (xa, y_lw + EL_WL[0] / 2)],
                                                       zs_ + hz - EL_WL[2] / 2, EL_WL[2]),
                       f'{nm} สูง {hz:.2f} {room}', dict(count=1, model='ยังไม่ระบุรุ่น', height=hz))
            el_add(f'EL-{tag}-JB3', f, el_pipe((x_s2, y_bal + sr * wf, zr - 0.02), (x_s2, y_bal + sr * (wf + EL_JB[1]), zr - 0.02)) | dict(w=EL_JB[0], d=EL_JB[0], sec=dict(d=EL_JB[0])),
                   f'Junction box 3 เหนือสวิตช์หน้าห้องน้ำ {room}', dict(count=1, size='Ø0.08'))
            # ท่อ: โคมกลางห้อง → ตามท้องพื้น/เหนือฝ้า ถึงผนังห้อง–ระเบียง → JB3 → สวิตช์ 2 ตัว / เต้ารับคู่ / โคมห้องน้ำ / โคมหลังห้อง
            if f < 5:
                yb2 = y_bal + sr * (0.125 + 0.03)                                # พ้นผิวคานแนว B/E ด้านในห้อง
                r2 = [((x_l, y_l + dn * EL_LAMP[1] / 2, zc), (x_l, yb2, zc)), ((x_l, yb2, zc), (x_l, yb2, zr)), ((x_l, yb2, zr), (x_l, yq, zr))]
            else:
                r2 = [((x_l, y_l, zr), (x_l, yq, zr))]
            r2 += [((x_l, yq, zr), (x_s2, yq, zr)),                                                   # ตามผนังถึง JB3
                   ((x_s2, yq, zr), (x_s2, yq, fl + EL_SW_Z + EL_BOX[1] / 2))]                         # ลงสวิตช์ 2 ตัว
            xcp = xb - dr * (cwf + COL_PL + off)                                 # อ้อมผิวฉาบเสาฝั่ง D2
            ycp = y_bal + sr * (cdf + COL_PL + off)
            xpp = x_pw - dr * off
            r2 += [((x_s2, yq, zr), (xcp, yq, zr)), ((xcp, yq, zr), (xcp, ycp, zr)), ((xcp, ycp, zr), (xpp, ycp, zr)),
                   ((xpp, ycp, zr), (xpp, y_so, zr)), ((xpp, y_so, zr), (xpp, y_so, fl + EL_SO_Z + EL_BOX[1] / 2))]
            for k, sgn, hz, nm in lamps:                                         # ลอดผนังที่แนว B5 แล้วตามผิวผนัง B5 ถึงโคม
                xl_ = b5 + sgn * dr * (wf + off)                                 # แนวท่อบนผิวผนัง B5
                xpen = b5 + sgn * dr * 0.08                                      # จุดลอดผนัง พ้นเสาเอ็นข้างแนว B5
                yw = y_bal - sr * (wf + off)
                r2 += [((x_s2, yq, zr), (xpen, yq, zr)), ((xpen, yq, zr), (xpen, yw, zr)), ((xpen, yw, zr), (xl_, yw, zr)), ((xl_, yw, zr), (xl_, y_lw, zr)),
                       ((xl_, y_lw, zr), (xl_, y_lw, zs_ + hz + EL_WL[2] / 2))]
            r2 = [(a, b) for a, b in r2 if math.dist(a, b) > 1e-3]
            L2 = sum(math.dist(a, b) for a, b in r2)
            el_add(f'EL-{tag}-CD2', f, dict(type='multi', parts=[el_pipe(a, b) for a, b in r2]),
                   f'ท่อร้อยสาย PVC ขาว Ø1/2" วงจรหลังห้อง (สวิตช์หน้าห้องน้ำ เต้ารับคู่ โคมห้องน้ำ โคมหลังห้อง) {room}', dict(length=round(L2, 3), size='PVC 1/2"'))

# บานประตูห้องพัก: ใช้คอมโพเนนต์ door2.dxf ที่ผู้ใช้ใส่ในโมเดล (ขนาดช่อง 0.90x2.00) แทนแผ่นตัวแทน
# ระเบียงหลังห้อง: ผนังนอกเป็นช่องเปิดโล่ง ไม่มีบานหน้าต่าง; ประตูห้องพัก→ระเบียงเป็นบานเลื่อน (ผู้ใช้แจ้ง 10 พ.ย. 2569)
elements[:] = [e for e in elements if not re.match(r'^W-F[2-5]-[NS]\d-OBL-O1$', e['id'])]
for e in elements:
    if re.match(r'^W-F[2-5]-[NS]\d-OBL$', e['id']):
        e['name'] = e['name'] + ' (ช่องเปิดโล่ง 1.20x1.20 ไม่มีบาน)'
    if re.match(r'^W-F[2-5]-[NS]\d-BAL-O1$', e['id']):
        e['name'] = e['name'].replace('ประตู 0.80x2.00', 'ประตูบานเลื่อน 0.80x2.00')
        e['qty']['type'] = 'บานเลื่อน'
        # คอมโพเนนต์ประตูบานเลื่อนอะลูมิเนียม 2 บาน (สร้างใน build_sketchup.rb) วงกบเต็มช่อง 1.25x1.80 ลึกเท่าผนังรวมฉาบ 0.10
        e['component'] = 'ประตูบานเลื่อน D2 1.25x1.80'
        e['component_fit'] = 'opening'
        e['component_spec'] = dict(w=D2_W, h=D2_H, d=round(WALL_T + 2 * PL_T, 3), frame=0.04, sill=0.02, sash_t=0.022, overlap=0.04)
for e in elements:
    if e['id'].startswith('W-F') and e['id'].endswith('-COR-O1'):
        e['component'] = 'door2.dxf'
    # ประตูห้องน้ำ: ตัวอย่างชั่วคราวของผู้ใช้ ย่อ/ขยายให้พอดีช่อง 0.70x1.80 (จะเปลี่ยนเป็นรุ่นจริงภายหลัง)
    if re.match(r'^W-F[2-5]-[NS]\d-BAL-O2$', e['id']):
        e['component'] = 'ประตูห้องน้ำ 0.70x1.80 (ตัวอย่างชั่วคราว)'
        e['component_fit'] = 'opening'
    # ประตูม้วนร้านค้า (แนว C ด้านใต้ถุน): ระยะระหว่างราง 3.00, กล่องม้วนสูง 0.75 ชนท้องพื้นชั้น 2
    # ติดตั้งด้านในร้าน: ด้านรางของคอมโพเนนต์ชิดผิวคาน B2 ด้านในร้าน (y = C - 0.125) กล่องยื่นเข้าในร้าน
    if re.match(r'^W-F1-SH\d-FR-O1$', e['id']):
        e['component'] = 'ประตูม้วน 3.00x2.60'
        e['component_mount'] = dict(back_y=round(GY['C'] + B2_DY['C'] - 0.125, 4), box_dir=-1, box_top=round(FL[2] - SLAB_T, 3))


def summary():
    from collections import Counter
    return Counter((e['category'], e['task']) for e in elements)


def mirror_y(g):
    """กลับแกน y (y' = F − y) ให้มุมมองด้านบนใน SketchUp ตรงกับแปลน (กริด 1 ซ้าย, กริด A ด้านบน)"""
    Y = GY['F']
    t = g['type']
    if t == 'multi':
        for q in g['parts']:
            mirror_y(q)
    elif t == 'member':
        for k in ('p0', 'p1'):
            g[k][1] = round(Y - g[k][1], 4)
        if g.get('shape') == 'POLY':             # หน้าตัดไม่สมมาตร: กลับทิศ chain ให้ด้านหน้าหน้าตัดยังหันทิศเดิมหลังกลับแกน y
            g['p0'], g['p1'] = g['p1'], g['p0']
        for c in g.get('trim') or []:
            if c:
                c[1], c[4] = round(Y - c[1], 5), round(-c[4], 5) + 0.0
    elif t == 'prism':
        g['poly'] = [[x, round(Y - y, 4)] for x, y in g['poly']][::-1]
        if g.get('holes'):
            g['holes'] = [[[x, round(Y - y, 4)] for x, y in h][::-1] for h in g['holes']]
    elif t == 'plate':
        g['pts'] = [[x, round(Y - y, 4), z] for x, y, z in g['pts']][::-1]
    elif t == 'xprofile':
        g['poly'] = [[round(Y - y, 4), z] for y, z in g['poly']][::-1]


# ---------- ตัดงานก่อ/เอ็น/ฉาบผนัง ที่ล้ำเข้าเนื้อเสา (ผู้ใช้แจ้ง 10 พ.ย. 2569) ----------
# เช่น ผนังแถบระเบียงชั้น 4 ฐานผนังอยู่ต่ำกว่า FL4 0.075 (พื้นลดระดับ) ชนหัวเสาชั้น 3 ที่ใหญ่กว่าเสาชั้น 4
def _box(g):
    xs = [q[0] for q in g['poly']]; ys = [q[1] for q in g['poly']]
    return [min(xs), max(xs), min(ys), max(ys), g['z0'], g['z0'] + g['t']]


def _vol(b):
    return (b[1] - b[0]) * (b[3] - b[2]) * (b[5] - b[4])


def _sub_box(r, c):
    """r - c (กล่องแนวแกน) คืนรายการกล่องที่เหลือ"""
    if not all(min(r[2 * k + 1], c[2 * k + 1]) - max(r[2 * k], c[2 * k]) > 1e-6 for k in range(3)):
        return [r]
    out, cur = [], list(r)
    for k in range(3):
        a, b = 2 * k, 2 * k + 1
        if cur[a] < c[a] - 1e-6:
            piece = list(cur); piece[b] = c[a]; out.append(piece); cur[a] = c[a]
        if cur[b] > c[b] + 1e-6:
            piece = list(cur); piece[a] = c[b]; out.append(piece); cur[b] = c[b]
    return out


def _clip_geom(g, cols):
    parts = g['parts'] if g['type'] == 'multi' else [g]
    if any(pt['type'] != 'prism' or len(pt['poly']) != 4 for pt in parts):
        return None, 0.0
    boxes, removed = [], 0.0
    for pt in parts:
        b0 = _box(pt)
        bs = [b0]
        for c in cols:
            bs = [nb for b in bs for nb in _sub_box(b, c)]
        removed += _vol(b0) - sum(_vol(b) for b in bs)
        boxes += bs
    if removed <= 1e-9:
        return None, 0.0
    ps = [prism([(b[0], b[2]), (b[1], b[2]), (b[1], b[3]), (b[0], b[3])], b[4], round(b[5] - b[4], 4)) for b in boxes]
    return (ps[0] if len(ps) == 1 else dict(type='multi', parts=ps)), removed


_cols = [_box(e['geom']) for e in elements if e['category'] == 'เสา' and e['geom']['type'] == 'prism']
_BST2_END = []
# ปลายคาน BST2 ที่ยืดถึงแนว A (ช่วง A..A+0.20 รวมฉาบคาน): ผนังนอกห้องน้ำที่ก่อผ่านระดับชานพักเว้นช่องรอบปลายคาน (ผู้ใช้เลือก 11 พ.ย. 2569)
for e in elements:
    if e['id'].startswith('BST2-'):
        g = e['geom']; x, z = g['p0'][0], g['p0'][2]
        hw = g['w'] / 2 + PL_BEAM
        _BST2_END.append([x - hw, x + hw, GY['A'], GY['A'] + 0.20, z - g['d'] / 2 - PL_BEAM, z + g['d'] / 2])
# คาน B3 ที่แนวกริด 4/5 (รวมฉาบคาน): ผนังนอกโถงบันไดแนว A ที่ก่อชนเสา CX ตัดรอบปลายคาน (ผู้ใช้แจ้ง 11 พ.ย. 2569)
_B3_ST = []
for e in elements:
    if re.match(r'^B3-[45]-AB-L\d$', e['id']):
        g = e['geom']; x, z = g['p0'][0], g['p0'][2]
        hw = g['w'] / 2 + PL_BEAM
        _B3_ST.append([x - hw, x + hw, GY['A'], GY['B'], z - g['d'] / 2 - PL_BEAM, z + g['d'] / 2])
# ฉาบผนังกั้นที่ก่อถึงผิวนอกแนว A/F: ตัดช่วงที่อยู่ในความหนาผนังนอก (ผนังนอกก่อชนผิวผนังกั้น)
_OUTER_BAND = [[-1, 33, GY['A'] - 0.1, GY['A'] + WALL_T, -1, 20], [-1, 33, GY['F'] - WALL_T, GY['F'] + 0.1, -1, 20]]
CLIPPED = []
for e in elements:
    if not (e['category'] in ('ผนัง', 'เสาเอ็นคานเอ็น') or (e['category'] == 'งานฉาบ' and e['id'].startswith('W-'))):
        continue
    extra = _BST2_END if '-OWC' in e['id'] else []                                        # เฉพาะผนังนอกห้องน้ำที่ปลาย BST2
    if e['id'].startswith('W-ST-OUT'):
        extra = _B3_ST
    if e['category'] == 'งานฉาบ' and re.match(r'^W-F\d-([NS]\d-WC|[NS]G[2-9]-BL)-PL$', e['id']):
        extra = _OUTER_BAND
    ng, rem = _clip_geom(e['geom'], _cols + extra)
    if ng is None:
        continue
    e['geom'] = ng
    CLIPPED.append(e['id'])
    q = e.get('qty') or {}
    if e['category'] == 'ผนัง' and 'area' in q:
        q['area'] = round(q['area'] - rem / WALL_T, 3); q['blocks'] = round(q['area'] * BLOCK_PER_M2)
    elif e['category'] == 'งานฉาบ' and 'area' in q:
        q['area'] = round(q['area'] - rem / PL_T, 3)
    elif 'concrete' in q:
        q['concrete'] = round(q['concrete'] - rem, 4)


# ---------- รุ่นสุขภัณฑ์ (ผู้ใช้แจ้ง 10 พ.ย. 2569) ----------
for e in elements:
    if e['category'] == 'สุขภัณฑ์' and e['name'].startswith('โถส้วม'):
        e['qty']['model'] = 'กะรัต K2760 หรือเทียบเท่า'
    elif e['category'] == 'สุขภัณฑ์' and e['name'].startswith('อ่างล้างหน้า'):
        e['qty']['model'] = 'กะรัต K1225'


# กระเบื้องห้องน้ำ N3/N5 ชั้น 2–4 ตัดรอบเสา CX (รวมฉาบเสา 1 ซม.)
for e in elements:
    m_ = re.match(r'^TL-F([234])-N([35])-WC$', e['id'])
    if m_:
        xk = GX[3] if m_.group(2) == '3' else GX[4]
        tile_cut_box(e, xk - 0.10 - PL_COL, xk + 0.10 + PL_COL, GY['A'], GY['A'] + 0.20 + PL_COL, TILE_WC)

# กระเบื้องแถบยื่นชั้น 5 (ห้องน้ำ/ระเบียง) ตัดรอบเสา CX2 (รวมฉาบเสา 1 ซม.)
for e in elements:
    m_ = re.match(r'^TL-F5-([NS])\d-(WC|BL)$', e['id'])
    if not m_:
        continue
    spec = TILE_WC if m_.group(2) == 'WC' else TILE_TARA_WOOD
    ya_, yb_ = (GY['A'], GY['A'] + 0.20 + PL_COL) if m_.group(1) == 'N' else (GY['F'] - 0.20 - PL_COL, GY['F'])
    for i in range(10):
        tile_cut_box(e, GX[i] - 0.10 - PL_COL, GX[i] + 0.10 + PL_COL, ya_, yb_, spec)

# ---------- งานผิวบันได (ผู้ใช้สั่ง 11 พ.ย. 2569) ----------
# ลูกนอน + ลูกตั้ง: ปูนกาว + กระเบื้อง Tara เจด้าไวท์ (ชนิดเดียวกับโถงหน้าห้อง) หนารวม 0.02 เท่ากระเบื้องพื้น
# ชานพัก: กระเบื้องชนิดเดียวกัน; จมูกบันได PVC MAC DF38-20G1 สีเทาเข้ม 3.8x1.5x200 ซม. ฝังที่ขอบทุกขั้น (รวมขอบชานพัก/ขอบพื้นชั้นบน)
ST_TILE_T = 0.02
NOSE_W, NOSE_H, NOSE_L = 0.038, 0.015, 2.00
# หน้าตัดจมูกบันได (มม., x = 0 ด้านใน → 38 ด้านหน้า, y = 0 ผิวบน ↓ -15) ตามรูปที่ผู้ใช้ส่ง; ความหนาแผ่น 3 มม. ขาหน้า 2.5 มม. ครีบยึด 2x5 มม. เป็นค่าสมมติ (ไม่ขึ้นร่องกันลื่น)
NOSE_POLY = [(0, 0), (38, 0), (38, -15), (33, -15), (33, -13), (35.5, -13), (35.5, -3), (20, -3), (20, -8), (18, -8), (18, -3), (0, -3)]
_np_area = abs(sum(NOSE_POLY[i - 1][0] * NOSE_POLY[i][1] - NOSE_POLY[i][0] * NOSE_POLY[i - 1][1] for i in range(len(NOSE_POLY)))) / 2 / 1e6
ST_TILE_MAT = 'Tara เจด้าไวท์ 60x60 ยาแนว 3 มม.'


def _strip_tiles(w, h, n, spec=TILE_TARA):
    """จำนวนแผ่น 60x60 ที่ตัดเป็นแถบกว้าง w x สูง h จำนวน n แถบ (ตัดแถบตามยาวแผ่น)"""
    pitch = spec['w']
    per_tile = max(1, int((pitch + 1e-9) // (h + 0.003)))         # แถบต่อแผ่น (เผื่อรอยตัด 3 มม.)
    pieces = n * math.ceil(round(w / (pitch + spec['joint']), 6))  # ชิ้นตามความกว้างบันได
    return pieces, math.ceil(pieces / per_tile)


for f in (1, 2, 3, 4):
    z0 = FL[f]
    zm = z0 + 10 * RISER
    for fl_id, (x0, x1, y_start, d, zs) in (('1', (FX0, FX1, ST_RUN_Y1, -1, z0)), ('2', (GX0, GX1, LY1, +1, zm))):
        base = (z0 + (ST_TILE_T if f >= 2 else 0.0)) if fl_id == '1' else zm + ST_TILE_T   # ผิวที่ลูกตั้งแรกตั้งอยู่
        treads, risers, noses = [], [], []
        for k in range(10):
            yk = y_start + d * k * TREAD                  # ผิวคอนกรีตลูกตั้ง k
            top = zs + (k + 1) * RISER + ST_TILE_T       # ผิวกระเบื้องลูกนอน k (k = 9 คือผิวชานพัก/พื้นชั้นบน)
            yf = yk - d * ST_TILE_T                      # หน้ากระเบื้องลูกตั้ง = หน้าจมูกบันได
            zb = base if k == 0 else zs + k * RISER + ST_TILE_T
            risers.append(prism([(x0, min(yf, yk)), (x1, min(yf, yk)), (x1, max(yf, yk)), (x0, max(yf, yk))], zb, round(top - NOSE_H - zb, 4)))
            # จมูกบันได: แกนที่กึ่งกลางกรอบหน้าตัด ทิศ chain = d*x ให้ด้านหน้า (x หน้าตัด +) หันลงบันได
            yc_ = yf + d * NOSE_W / 2
            pa, pb_ = ((x0, yc_, top - NOSE_H / 2), (x1, yc_, top - NOSE_H / 2)) if d > 0 else ((x1, yc_, top - NOSE_H / 2), (x0, yc_, top - NOSE_H / 2))
            ng = member(pa, pb_, NOSE_W, NOSE_H)
            ng['shape'] = 'POLY'; ng['poly2d'] = [[round(a / 1000, 4), round(b / 1000, 4)] for a, b in NOSE_POLY]
            noses.append(ng)
            if k < 9:
                ya, yb = yf + d * NOSE_W, yk + d * TREAD
                treads.append(prism([(x0, min(ya, yb)), (x1, min(ya, yb)), (x1, max(ya, yb)), (x0, max(ya, yb))], top - ST_TILE_T, ST_TILE_T))
        W = x1 - x0
        tr_d = TREAD - (NOSE_W - ST_TILE_T)
        pcs, nt = _strip_tiles(W, tr_d, 9)
        add(f'TL-ST-F{f}-{fl_id}-T', 'กระเบื้อง', f, 'A16', dict(type='multi', parts=treads),
            name=f'ปูนกาว+กระเบื้องลูกนอน บันไดชั้น {f}→{f+1} ช่วง {fl_id} Tara เจด้าไวท์ 60x60 (ชนิดเดียวกับโถงหน้าห้อง)', assumed=True,
            qty=dict(area=round(W * tr_d * 9, 3), treads=9, tread_tile_depth=round(tr_d, 3), pieces=pcs, tiles=nt,
                     tile_model=TILE_TARA['model'], thickness=ST_TILE_T, note='ปูนกาว + กระเบื้อง หนารวม 0.02 ม.'))
        elements[-1]['material'] = 'BIM-กระเบื้องบันได'
        rh = [p['t'] for p in risers]
        pcs, nt = _strip_tiles(W, max(rh), 10)
        add(f'TL-ST-F{f}-{fl_id}-R', 'กระเบื้อง', f, 'A16', dict(type='multi', parts=risers),
            name=f'ปูนกาว+กระเบื้องลูกตั้ง บันไดชั้น {f}→{f+1} ช่วง {fl_id} Tara เจด้าไวท์ 60x60', assumed=True,
            qty=dict(area=round(W * sum(rh), 3), risers=10, riser_tile_height=round(rh[1], 3), first_riser_tile_height=round(rh[0], 3),
                     pieces=pcs, tiles=nt, tile_model=TILE_TARA['model'], thickness=ST_TILE_T))
        elements[-1]['material'] = 'BIM-กระเบื้องบันได'
        add(f'NS-ST-F{f}-{fl_id}', 'จมูกบันได', f, 'A16', dict(type='multi', parts=noses),
            name=f'จมูกบันได PVC MAC DF38-20G1 สีเทาเข้ม 3.8x1.5 ซม. บันไดชั้น {f}→{f+1} ช่วง {fl_id} (10 ขอบ)', assumed=True,
            qty=dict(count=10, length=round(10 * W, 3), bars_2m=10 * math.ceil(round(W / NOSE_L, 6)),
                     model='MAC PVC Stair Nosing DF38-20G1 Dark Gray 3.8x200x1.5 ซม. (ผู้ใช้กำหนด 11 พ.ย. 2569)'))
        elements[-1]['material'] = 'BIM-จมูกบันไดเทาเข้ม'
    # ชานพัก: กระเบื้องชนิดเดียวกับทางเดินหน้าห้อง แนวร่องต่อเนื่องจากทางเดิน (ผู้ใช้สั่ง 11 พ.ย. 2569) เว้นแถบจมูกบันไดขอบชานพัก (ช่วง 1)
    add_tile(f'TL-ST-F{f}-L', f, FX0, GX1, LY0, LY1, TILE_TARA, f'ปูนกาว+กระเบื้องชานพักบันไดชั้น {f} Tara เจด้าไวท์ 60x60 (ชนิดและแนวร่องต่อเนื่องจากทางเดินหน้าห้อง)',
             z=zm, origin=((GX[0] + GX[-1]) / 2, GY['CX']))
    elements[-1]['task'] = 'A16'
    tile_cut_box(elements[-1], FX0, FX1, LY1 - (NOSE_W - ST_TILE_T), LY1 + 1, TILE_TARA)
    # ฉาบผิวข้างคาน BST1 ขอบช่องบันได (ด้านบันได) หยุดใต้กระเบื้องลูกตั้งขั้นสุดท้ายของช่วง 2 (กระเบื้องปูทับแทนฉาบ)
    plb = next((e for e in elements if e['id'] == f'PL-BST1-L{f+1}'), None)
    if plb:
        z_cut = zm + 9 * RISER + ST_TILE_T
        for q in plb['geom']['parts']:
            if q['w'] < 0.01 and q['p0'][1] < ST_RUN_Y1:
                zb_, zt_ = q['p0'][2] - q['d'] / 2, q['p0'][2] + q['d'] / 2
                if zt_ > z_cut:
                    q['d'] = round(z_cut - zb_, 4)
                    q['p0'][2] = q['p1'][2] = round((zb_ + z_cut) / 2, 4)
    # ฉาบผิวข้างคาน BST1 แนว B ด้านช่วง 1 (ผิวคานเสมอลูกตั้งขั้นสุดท้าย): หยุดใต้กระเบื้องลูกตั้งขั้นสุดท้ายช่วง 1
    plb = next((e for e in elements if e['id'] == f'PL-BST1-B-M{f}'), None)
    if plb:
        z_cut = z0 + 9 * RISER + ST_TILE_T
        for q in plb['geom']['parts']:
            if q['w'] < 0.01 and q['p0'][1] > LY1 - 1e-6:
                zb_, zt_ = q['p0'][2] - q['d'] / 2, q['p0'][2] + q['d'] / 2
                if zt_ > z_cut:
                    q['d'] = round(z_cut - zb_, 4)
                    q['p0'][2] = q['p1'][2] = round((zb_ + z_cut) / 2, 4)
    # ขอบพื้นชั้นบนที่ปลายช่วง 2: ตัดกระเบื้องโถงหน้าบันไดเว้นแถบจมูกบันได
    hall = next((e for e in elements if e['id'] == f'TL-F{f+1}-ST-HALL'), None)
    if hall:
        tile_cut_box(hall, GX0, GX1, ST_RUN_Y1 - ST_TILE_T, ST_RUN_Y1 - ST_TILE_T + NOSE_W, TILE_TARA)
ASSUMPTIONS.append('บันได: ปูนกาว+กระเบื้องหนารวม 0.02 ม. (เท่ากระเบื้องพื้น) ลูกตั้งตั้งบนกระเบื้องลูกนอน, จมูกบันไดหน้าเสมอผิวกระเบื้องลูกตั้ง ผิวบนเสมอกระเบื้องลูกนอน; ชั้น 1 ไม่มีกระเบื้องพื้นที่ต้นบันได ลูกตั้งแรกจึงสูงกว่าขั้นอื่น 0.02 ม.')

# ---------- งานเทคอนกรีตพื้น: เติมเต็มช่อง + ตัดหลบเสา/คาน (ผู้ใช้สั่ง 11 พ.ย. 2569) ----------
# topping เทเต็มชั้นแผ่นพื้นด้วย: ช่องขนานคาน (<= 2.5 ซม.) หลังคานที่แผ่นพาด (เลยระยะพาด 5 ซม.) ร่องแผ่น 3 มม. แถบแคบ
# ผิวล่างคอนกรีตเติมเสมอท้องแผ่น/หลังคาน ขอบเสมอผิวคาน; หักเนื้อเสา คาน แผ่นพื้น ออก ไม่ให้ solid ซ้อนกัน
def _solid_boxes(g):
    t = g['type']
    if t == 'multi':
        for q in g['parts']:
            yield from _solid_boxes(q)
    elif t == 'prism':
        xs = [p[0] for p in g['poly']]; ys = [p[1] for p in g['poly']]
        yield (min(xs), max(xs), min(ys), max(ys), g['z0'], g['z0'] + g['t'])
    elif t == 'member':
        p0, p1, w, d = g['p0'], g['p1'], g['w'], g['d']
        if abs(p0[2] - p1[2]) > 1e-6:
            return
        if abs(p0[1] - p1[1]) < 1e-6:
            yield (min(p0[0], p1[0]), max(p0[0], p1[0]), p0[1] - w / 2, p0[1] + w / 2, p0[2] - d / 2, p0[2] + d / 2)
        elif abs(p0[0] - p1[0]) < 1e-6:
            yield (p0[0] - w / 2, p0[0] + w / 2, min(p0[1], p1[1]), max(p0[1], p1[1]), p0[2] - d / 2, p0[2] + d / 2)


_POUR_SOLIDS = [b for e in elements if e['category'] in ('เสา', 'คาน', 'พื้นสำเร็จรูป') for b in _solid_boxes(e['geom'])]


def pour_geom(rects, z0, z1):
    """คอนกรีตเทในกรอบ rects ช่วง z0..z1 หักเนื้อเสา/คาน/แผ่นพื้น แบ่งชั้นตามระดับ z ของชิ้นที่ตัด คืน (geom, [(z0,t,area)])"""
    bx = [b for b in _POUR_SOLIDS if b[5] > z0 + 1e-6 and b[4] < z1 - 1e-6 and
          any(min(b[1], x1) - max(b[0], x0) > 1e-6 and min(b[3], y1) - max(b[2], y0) > 1e-6 for x0, x1, y0, y1 in rects)]
    zs = sorted({round(z0, 4), round(z1, 4)} | {round(v, 4) for b in bx for v in (b[4], b[5]) if z0 + 1e-6 < v < z1 - 1e-6})
    bands = []
    for za, zb in zip(zs, zs[1:]):
        rs = list(rects)
        for b in bx:
            if b[4] <= za + 1e-6 and b[5] >= zb - 1e-6:
                rs = _rects_minus(rs, b[0], b[1], b[2], b[3])
        rs = sorted((round(a, 4), round(c, 4), round(d_, 4), round(f_, 4)) for a, c, d_, f_ in rs if c - a > 1e-6 and f_ - d_ > 1e-6)
        if bands and bands[-1][2] == rs:
            bands[-1][1] = zb
        else:
            bands.append([za, zb, rs])
    parts = [prism([(a, c), (b, c), (b, d_), (a, d_)], za, round(zb - za, 4)) for za, zb, rs in bands for a, b, c, d_ in rs]
    return (parts[0] if len(parts) == 1 else dict(type='multi', parts=parts)), [(za, zb - za, rect_area(rs)) for za, zb, rs in bands]


for f in (2, 3, 4, 5):
    for sfx, kind, rects, top in SLAB_ZONES[f]:
        sid = f'S1-F{f}-{sfx}' if kind in ('WC', 'BL') else f'TP-F{f}-{sfx}'
        e = next(x for x in elements if x['id'] == sid)
        geo, bands = pour_geom(rects, top - SLAB_T, top) if kind not in ('WC', 'BL') else pour_geom(rects, top - S1_T, top)
        e['geom'] = geo
        vol = sum(t * a for _, t, a in bands)
        e['qty']['concrete'] = round(vol, 4)
        if sid.startswith('TP'):
            vt = sum(t * a for z, t, a in bands if z >= top - 0.05 - 1e-6)
            e['qty']['concrete_topping'] = round(vt, 4)
            e['qty']['concrete_fill'] = round(vol - vt, 4)
            e['name'] += ' + เติมช่องแผ่นพื้น/หลังคาน (หักเสา/คาน)'
        else:
            e['name'] += ' (หักเสา/คาน)'

# ---------- ปิดผิวฉาบภายนอกให้ต่อเนื่อง (ผู้ใช้สั่ง 11 พ.ย. 2569) ----------
# ผิวโครงสร้าง/งานก่อที่อยู่บนระนาบผิวนอกอาคาร (แนว A, F, กริด 1, 10) แต่ยังไม่มีงานฉาบปิด เช่น ขอบพื้นหล่อในที่/ทับหน้า,
# ปลายคานที่ชนผิวนอก, ปลายผนังกั้นและปลายผนังนอกที่มุมอาคาร: เพิ่มแผ่นฉาบปิดเฉพาะส่วนที่ยังเปิด (ไม่ทับฉาบเดิม)
# หนาตามชนิดผิว: ผนัง/พื้น 1.5 ซม., เสา 1 ซม., คาน 0.5 ซม.; ตั้งแต่ระดับพื้นชั้น 1 ขึ้นไป
def _aabb(p):
    t = p['type']
    if t == 'prism':
        return _box(p)
    if t == 'member':
        a, b = p['p0'], p['p1']
        if p.get('shape') or p.get('pb'):
            return None
        w, d = p['w'] / 2, p['d'] / 2
        if abs(a[0] - b[0]) < 1e-6 and abs(a[1] - b[1]) < 1e-6:
            return [a[0] - w, a[0] + w, a[1] - d, a[1] + d, min(a[2], b[2]), max(a[2], b[2])]
        if abs(a[2] - b[2]) > 1e-6:
            return None
        if abs(a[0] - b[0]) < 1e-6:
            return [a[0] - w, a[0] + w, min(a[1], b[1]), max(a[1], b[1]), a[2] - d, a[2] + d]
        if abs(a[1] - b[1]) < 1e-6:
            return [min(a[0], b[0]), max(a[0], b[0]), a[1] - w, a[1] + w, a[2] - d, a[2] + d]
    return None


_EXT_SKIP = ('ไฟฟ้า', 'ประตูหน้าต่าง', 'ราวบันได', 'สุขภัณฑ์', 'โครงหลังคาเหล็ก', 'หลังคา', 'จมูกบันได', 'กระเบื้อง', 'บันได')
_ext_boxes = []
for e in elements:
    if e['category'] in _EXT_SKIP:
        continue
    for p in (e['geom']['parts'] if e['geom']['type'] == 'multi' else [e['geom']]):
        b = _aabb(p)
        if b:
            _ext_boxes.append((b, e['category']))
_X_OUT0, _X_OUT1 = GX[0] - COL_SEC[1][0] / 2, GX[-1] + COL_SEC[1][0] / 2
_EXT_FACES = [('A', 1, GY['A'], -1), ('F', 1, GY['F'], 1), ('G1', 0, _X_OUT0, -1), ('G10', 0, _X_OUT1, 1)]
_EXT_T = {'คาน': PL_BEAM, 'เสา': PL_COL}
EXT_PATCH = {}
for fname, ax, P, s_ in _EXT_FACES:
    lo_, hi_ = (2, 3) if ax == 1 else (0, 1)
    u0_, u1_ = (0, 1) if ax == 1 else (2, 3)
    on_face = lambda b: (b[lo_] if s_ < 0 else -b[hi_]) <= (P if s_ < 0 else -P) + 0.002 and ((b[hi_] - P) if s_ < 0 else (P - b[lo_])) > 0.002
    covers = [(b[u0_], b[u1_], b[4], b[5]) for b, c in _ext_boxes if c == 'งานฉาบ'
              and ((b[lo_] < P - 0.0005) if s_ < 0 else (b[hi_] > P + 0.0005)) and ((b[hi_] > P - 0.03) if s_ < 0 else (b[lo_] < P + 0.03))]
    solids = [((b[u0_], b[u1_], max(b[4], FL[1]), b[5]), c) for b, c in _ext_boxes if c != 'งานฉาบ' and on_face(b) and b[5] > FL[1] + 1e-6]
    solids.sort(key=lambda t: -_EXT_T.get(t[1], PL_T))
    done = []
    for r, c in solids:
        rs = [r]
        for cv in covers + done:
            rs = _rects_minus(rs, *cv)
        rs = [q for q in rs if q[1] - q[0] > 0.002 and q[3] - q[2] > 0.002]
        done += rs
        for q in rs:
            zc = (q[2] + q[3]) / 2
            f = max(ff for ff in FL if FL[ff] <= zc + 1e-6)
            EXT_PATCH.setdefault((fname, f), []).append((q, _EXT_T.get(c, PL_T), c))
for (fname, f), lst in sorted(EXT_PATCH.items()):
    ax, P, s_ = next((a, p, s) for n, a, p, s in _EXT_FACES if n == fname)
    parts, area = [], 0.0
    for (a0, a1, z0, z1), t, c in lst:
        o0, o1 = (P - t, P) if s_ < 0 else (P, P + t)
        poly = [(a0, o0), (a1, o0), (a1, o1), (a0, o1)] if ax == 1 else [(o0, a0), (o1, a0), (o1, a1), (o0, a1)]
        parts.append(prism(poly, round(z0, 4), round(z1 - z0, 4)))
        area += (a1 - a0) * (z1 - z0)
    add(f'PL-EXT-{fname}-F{f}', 'งานฉาบ', f, 'A12' if f == 1 else plaster_task[f],
        parts[0] if len(parts) == 1 else dict(type='multi', parts=parts),
        name=f'ฉาบปิดผิวภายนอกด้าน {fname} ชั้น {f} (ขอบพื้น ปลายคาน ปลายผนัง ที่ยังไม่มีฉาบ)', assumed=True,
        qty=dict(area=round(area, 3), pieces=len(parts)))
ASSUMPTIONS.append('ฉาบปิดผิวภายนอกเพิ่ม (PL-EXT-*): ขอบพื้น ปลายคาน ปลายผนังที่อยู่บนระนาบผิวนอกอาคารแต่ยังไม่มีฉาบ หนา ผนัง/พื้น 1.5 ซม. เสา 1 ซม. คาน 0.5 ซม.')

# ---------- สีคานตามเบอร์คาน (ผู้ใช้เลือก 11 พ.ย. 2569) ----------
for e in elements:
    if e['category'] == 'คาน':
        e['material'] = 'BIM-คาน-' + e['id'].split('-')[0]
    # คอนกรีตเททับหน้า (topping) และพื้นหล่อในที่ (S1 ห้องน้ำ/ระเบียง, GS ชั้น 1) ใช้คอนกรีตชนิดเดียวกัน (ผู้ใช้สั่ง 11 พ.ย. 2569)
    if e['category'] in ('พื้นทับหน้า', 'พื้น'):
        e['material'] = 'BIM-คอนกรีตเทพื้น'

ASSUMPTIONS.append('พิกัดใน elements.json กลับแกน y แล้ว: กริด A อยู่ที่ y = 15.50, กริด F ที่ y = 0 (มุมมองด้านบนตรงกับแปลน)')

if __name__ == '__main__':
    for e in elements:
        mirror_y(e['geom'])
        if 'finish' in e:
            e['finish']['origin'][1] = round(GY['F'] - e['finish']['origin'][1], 4)
        if 'component_mount' in e:
            e['component_mount']['back_y'] = round(GY['F'] - e['component_mount']['back_y'], 4)
            e['component_mount']['box_dir'] = -e['component_mount'].get('box_dir', 1)
    GYM = {k: round(GY['F'] - v, 4) for k, v in GY.items()}
    model = dict(project='หอพักคนงาน 5 ชั้น อาคาร A (ชัยเสรี หนองแค)', units='m', axes='x=กริด1→10, y=กริดF(0)→A(15.5), z=ระดับ',
                 grid=dict(x={**{str(i + 1): v for i, v in enumerate(GX)}, '11': GX11}, y=GYM), levels=dict(FL=FL, roof_beam=ROOF_BEAM, ridge=RIDGE),
                 assumptions=ASSUMPTIONS, elements=elements)
    json.dump(model, open('elements.json', 'w'), ensure_ascii=False)
    for k, v in sorted(summary().items()):
        print(k, v)
    print('total', len(elements), 'z_eave', round(z_eave, 3), 'ridge', rx0, rx1)
