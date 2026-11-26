"""หอพักคนงาน 5 ชั้น อาคาร A — นิยามชิ้นส่วนโมเดล (แหล่งข้อมูลเดียวสำหรับ SketchUp / GLB / JSON)

แกน: x ตามกริด 1→10 (เมตร), y ตามกริด A→F (A = ด้านหน้า, y=0), z ระดับ (±0.00 = พื้นรอบอาคาร)
แหล่งแบบ: FOR CON (S101, S102, S910, S911), S001, S106, S107, A201, A203
ค่าที่ไม่มีในแบบใส่ไว้ใน ASSUMPTIONS และติด flag "assumed" ที่ชิ้นส่วน
"""
import collections, json, math, re

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
# ตอม่อ F1 0.60x0.60x0.60 ที่ C/11, D/11 หลังตอม่ออยู่ใต้ท้องคาน GB1 (-0.30) (ผู้ใช้แจ้ง)
# คานคอดิน GB1 200x500 หลังคาน +0.20: แนว C, D จากตอม่อ C1 กริด 10 ถึงผิวนอกคานกริด 11 และแนวกริด 11 ระหว่าง C–D
_GB_Z = 0.20 - 0.25
for r in ('C', 'D'):
    add(f'F1-11{r}-ST', 'เสา', 1, 'DONE',
        prism([(GX11 - 0.30, GY[r] - 0.30), (GX11 + 0.30, GY[r] - 0.30), (GX11 + 0.30, GY[r] + 0.30), (GX11 - 0.30, GY[r] + 0.30)], FOOT_TOP - 0.60, 0.60),
        name=f'ตอม่อ F1 0.60x0.60x0.60 กริด 11/{r} (บันไดหนีไฟ) หลังตอม่อใต้คาน GB1', assumed=True, qty=dict(height=0.60, concrete=round(0.6 * 0.6 * 0.6, 4)))
    _x0, _x1 = GX[9] + COL_SEC[0][0] / 2, GX11 + 0.10
    add(f'GB1-10-11-{r}', 'คานคอดิน', 1, 'DONE', member((_x0, GY[r], _GB_Z), (_x1, GY[r], _GB_Z), 0.20, 0.50),
        name=f'GB1 กริด 10–11 แนว {r} (บันไดหนีไฟ)', assumed=True, qty=dict(length=round(_x1 - _x0, 3), concrete=round((_x1 - _x0) * 0.20 * 0.5, 4)))
_y0, _y1 = GY['C'] + 0.10, GY['D'] - 0.10
add('GB1-11-CD', 'คานคอดิน', 1, 'DONE', member((GX11, _y0, _GB_Z), (GX11, _y1, _GB_Z), 0.20, 0.50),
    name='GB1 กริด 11 แนว C–D (บันไดหนีไฟ)', assumed=True, qty=dict(length=round(_y1 - _y0, 3), concrete=round((_y1 - _y0) * 0.20 * 0.5, 4)))
# ตอม่อ F1 ปลายบันไดหนีไฟ ห่างแนว C 3.25 ม. ไปทางแนว B (ผู้ใช้สั่ง 11 พ.ย. 2569): ใต้คาน GB1 กริด 10 (B–C) เดิม และกริด 11
# พร้อมคาน GB1 กริด 11 จากคานแนว C ถึงปลายตอม่อ (หลังตอม่อใต้ท้องคาน -0.30)
FS_YM = GY['C'] - 3.25
for k, xc in (('10', GX[9]), ('11', GX11)):
    add(f'F1-{k}M-ST', 'เสา', 1, 'DONE',
        prism([(xc - 0.30, FS_YM - 0.30), (xc + 0.30, FS_YM - 0.30), (xc + 0.30, FS_YM + 0.30), (xc - 0.30, FS_YM + 0.30)], FOOT_TOP - 0.60, 0.60),
        name=f'ตอม่อ F1 0.60x0.60x0.60 กริด {k} ห่างแนว C 3.25 ม. ไปทาง B (บันไดหนีไฟ) หลังตอม่อใต้คาน GB1', assumed=True,
        qty=dict(height=0.60, concrete=round(0.6 * 0.6 * 0.6, 4)))
_y0, _y1 = GY['C'] - 0.10, FS_YM + 0.10
add('GB1-11-CM', 'คานคอดิน', 1, 'DONE', member((GX11, _y0, _GB_Z), (GX11, _y1, _GB_Z), 0.20, 0.50),
    name='GB1 กริด 11 จากแนว C ถึงคานขวางปลายบันไดหนีไฟ', assumed=True, qty=dict(length=round(_y0 - _y1, 3), concrete=round((_y0 - _y1) * 0.20 * 0.5, 4)))
# คาน GB1 ขวางระหว่างตอม่อปลายบันได กริด 10–11 (ผู้ใช้สั่ง 11 พ.ย. 2569): จากผิวนอกคาน GB1 กริด 10 ถึงผิวนอกคานกริด 11
_x0, _x1 = GX[9] + COL_SEC[0][0] / 2, GX11 + 0.10
add('GB1-10-11-M', 'คานคอดิน', 1, 'DONE', member((_x0, FS_YM, _GB_Z), (_x1, FS_YM, _GB_Z), 0.20, 0.50),
    name='GB1 กริด 10–11 ปลายบันไดหนีไฟ (ห่างแนว C 3.25 ม.)', assumed=True, qty=dict(length=round(_x1 - _x0, 3), concrete=round((_x1 - _x0) * 0.20 * 0.5, 4)))

# ---------- เสาเหล็กบันไดหนีไฟ C/11, D/11 (ผู้ใช้สั่ง 11 พ.ย. 2569) ขึ้นด้วย Profile Builder ----------
# H 175x175x11x16 ยาวท่อนละ 6 ม. รอยต่อเว้น 3 มม. (งานเชื่อม) แผ่นประกับ PL8x120x120 ที่เอวทั้งสองด้าน
# เพลทฐาน PL20x200x200 บนหลังคาน GB1 (+0.20), สลัก M16x200 จำนวน 4 ตัว ระยะ 75x130 (เดิม 125x125, ปรับให้ขันน็อตได้)
# แนวเอวขนานแกน x (ปีกหันเข้าหาอาคาร/ออกนอก) (ผมกำหนด)
SC_D, SC_B, SC_TW, SC_TF = 0.175, 0.175, 0.011, 0.016
_hd, _hb, _hw, _ti = SC_D / 2, SC_B / 2, SC_TW / 2, SC_D / 2 - SC_TF
SC_POLY = [(-_hd, -_hb), (-_ti, -_hb), (-_ti, -_hw), (_ti, -_hw), (_ti, -_hb), (_hd, -_hb),
           (_hd, _hb), (_ti, _hb), (_ti, _hw), (-_ti, _hw), (-_ti, _hb), (-_hd, _hb)]
BOLT_POLY = [(0.008 * math.cos(2 * math.pi * k / 16), 0.008 * math.sin(2 * math.pi * k / 16)) for k in range(16)]
WASHER_POLY = [(0.015 * math.cos(2 * math.pi * k / 16), 0.015 * math.sin(2 * math.pi * k / 16)) for k in range(16)]
NUT_POLY = [(0.012 / math.cos(math.pi / 6) * math.cos(math.pi / 3 * k), 0.012 / math.cos(math.pi / 6) * math.sin(math.pi / 3 * k)) for k in range(6)]
AB_DX, AB_DY, AB_WT, AB_NT = 0.0375, 0.065, 0.003, 0.013
SC_BASE = 0.20                       # หลังคาน GB1
SC_TOP = FL[5] + 1.50                # ปลายบนท่อนสุดท้ายเหนือระดับพื้นชั้น 5 1.50 ม. (ผู้ใช้สั่ง)
SC_LEN, SC_GAP = 6.0, 0.003


def _floor_at(z):
    return max([1] + [f for f in FL if FL[f] <= z + 1e-6])


# เสาที่ 11/M (แนวคานขวางปลายบันได ห่างแนว C 3.25 ม.) ขนาดเดียวกัน (ผู้ใช้สั่ง 11 พ.ย. 2569)
# เสาที่ 10/M บนหลังคาน GB1-10-11-M ผิวปีกเสาห่างผิวฉาบนอกกริด 10 (ผนัง 1.5 ซม.) 10 มม. (ผู้ใช้สั่ง 11 พ.ย. 2569)
SC_X10M = GX[9] + COL_SEC[1][0] / 2 + 0.015 + 0.010 + SC_D / 2
_SC_SET = [('11C', GX11, GY['C'], 'C/11'), ('11D', GX11, GY['D'], 'D/11'), ('11M', GX11, FS_YM, '11 ห่างแนว C 3.25 ม.'),
           ('10M', SC_X10M, FS_YM, '10 ห่างแนว C 3.25 ม. (ผิวเสาห่างผิวฉาบ 10 มม.)')]
for tag, cx, cy, lab in _SC_SET:
    sq = lambda hx, hy, z0, t: prism([(cx - hx, cy - hy), (cx + hx, cy - hy), (cx + hx, cy + hy), (cx - hx, cy + hy)], z0, t)
    add(f'SC-{tag}-BP', 'เสา', 1, 'DONE', sq(0.10, 0.10, SC_BASE, 0.020),
        name=f'เพลทฐานเสาเหล็ก PL20x200x200 กริด {lab}', assumed=True, qty=dict(count=1, size='PL20x200x200', weight_kg=round(0.2 * 0.2 * 0.02 * 7850, 2)))
    elements[-1]['material'] = 'BIM-เหล็กโครงสร้าง'
    # ระยะสลักใหม่ (ผู้ใช้สั่ง 11 พ.ย. 2569: เดิม 125x125 ชิดปีกเสา ขันน็อตไม่ได้): อยู่ในช่องระหว่างปีกเสาสองข้างเอว
    # x ±0.0375 (ห่างผิวในปีก 34 มม.), y ±0.065 (ห่างผิวเอว 59.5 มม., ห่างขอบเพลท 35 มม.) => ระยะ 75x130
    # ชุดสลัก: แกน M16 + แหวน M16 (OD30 หนา 3 มม.) + น็อตหกเหลี่ยม M16 (ปากประแจ 24 หนา 13 มม.) บนเพลทฐาน
    for k, (dx, dy) in enumerate(((-1, -1), (1, -1), (1, 1), (-1, 1))):
        bx, by = cx + dx * AB_DX, cy + dy * AB_DY
        g = member((bx, by, SC_BASE + 0.06 - 0.20), (bx, by, SC_BASE + 0.06), 0.016, 0.016)
        g['shape'] = 'POLY'; g['poly2d'] = [[round(a, 5), round(b, 5)] for a, b in BOLT_POLY]
        zp = SC_BASE + 0.020
        wsh = member((bx, by, zp), (bx, by, zp + AB_WT), 0.030, 0.030)
        wsh['shape'] = 'POLY'; wsh['poly2d'] = [[round(a, 5), round(b, 5)] for a, b in WASHER_POLY]
        nut = member((bx, by, zp + AB_WT), (bx, by, zp + AB_WT + AB_NT), 0.028, 0.028)
        nut['shape'] = 'POLY'; nut['poly2d'] = [[round(a, 5), round(b, 5)] for a, b in NUT_POLY]
        add(f'SC-{tag}-AB{k+1}', 'เสา', 1, 'DONE', dict(type='multi', parts=[g, wsh, nut]),
            name=f'สลักยึดเสา M16x200 พร้อมแหวนและน็อต กริด {lab}', assumed=True,
            qty=dict(count=1, size='M16x200', washer='M16 OD30x3', nut='M16 hex 24x13'))
        elements[-1]['material'] = 'BIM-สลักเหล็ก'
    z, n, joints = SC_BASE + 0.020, 0, []
    while z < SC_TOP - 1e-6:
        n += 1
        z1 = min(z + SC_LEN, SC_TOP)
        g = member((cx, cy, z), (cx, cy, z1), SC_B, SC_D)
        g['shape'] = 'POLY'; g['poly2d'] = [[round(a, 5), round(b, 5)] for a, b in SC_POLY]
        add(f'SC-{tag}-{n}', 'เสา', _floor_at(z), 'DONE', g,
            name=f'เสาเหล็ก H175x175x11x16 กริด {lab} ท่อน {n} ยาว {z1 - z:.3f} ม.', assumed=True,
            qty=dict(length=round(z1 - z, 3), section='H175x175x11x16'))
        elements[-1]['material'] = 'BIM-เหล็กโครงสร้าง'
        if z1 < SC_TOP - 1e-6:
            joints.append(z1 + SC_GAP / 2)
        z = z1 + SC_GAP
    for j, zj in enumerate(joints):
        for side, sy in (('L', -1), ('R', 1)):
            y0 = cy + sy * _hw
            y1 = y0 + sy * 0.008
            add(f'SC-{tag}-SP{j+1}{side}', 'เสา', _floor_at(zj), 'DONE',
                prism([(cx - 0.06, min(y0, y1)), (cx + 0.06, min(y0, y1)), (cx + 0.06, max(y0, y1)), (cx - 0.06, max(y0, y1))], round(zj - 0.06, 4), 0.12),
                name=f'แผ่นประกับรอยต่อเสาเหล็ก PL8x120x120 กริด {lab} รอยต่อ {j+1}', assumed=True,
                qty=dict(count=1, size='PL8x120x120', weight_kg=round(0.12 * 0.12 * 0.008 * 7850, 2)))
            elements[-1]['material'] = 'BIM-เหล็กโครงสร้าง'


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
        if j == 0:          # เสา CX ใต้ชานพักชั้น 1 ไม่มีจริง (ผู้ใช้แจ้ง 11 พ.ย. 2569: เข้าใจผิด ลบออก)
            continue
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


def tie_layout(a0, a1, z0, z1, openings, mid_at_sill=False):
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
    _sills = [sill for c, w, sill, h in openings if sill > 0]
    if mid_at_sill and _sills:
        # ยกคานเอ็นกลางผนังขึ้นไปอยู่ระดับใต้วงกบหน้าต่าง ใช้แทนคานใต้วงกบ (ผู้ใช้สั่ง 23 พ.ย. 2569 ผนังหลังห้องน้ำ)
        zs_ = z0 + min(_sills)
        beams.append((a0, a1, zs_ - TIE, zs_, 'คานเอ็นกลางผนัง (ระดับใต้วงกบหน้าต่าง)'))
    else:
        beams.append((a0, a1, zm - TIE / 2, zm + TIE / 2, 'คานเอ็นกลางผนัง'))
    for c, w, sill, h in openings:
        x0, x1 = max(a0, c - w / 2 - LINTEL_EXT), min(a1, c + w / 2 + LINTEL_EXT)
        zt = z0 + sill + h
        if zt + TIE <= z1 + 1e-6:
            beams.append((x0, x1, zt, zt + TIE, 'คานทับหลัง'))
        if sill > 0 and not mid_at_sill:
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


def add_wall(eid, floor, axis, fixed, a0, a1, z0, z1, task_wall, task_plaster, openings=(), name=None, mid_at_sill=False):
    if a1 - a0 < 0.05:
        return
    openings = list(openings)
    pcs = wall_pieces(a0, a1, z0, z1, openings)
    posts, beams = tie_layout(a0, a1, z0, z1, openings, mid_at_sill)
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
WC_CEIL = 2.50                # ฝ้าทีบาร์ห้องน้ำสูงจากผิวกระเบื้อง (ผู้ใช้กำหนด 12 พ.ย. 2569)
SV_W, SV_H, SV_SILL, SV_C, SV_FW = 0.40, 0.80, 1.60, 0.357, 0.03   # ช่อง service ผนังชาร์ฟ: กว้าง สูง ขอบล่างจากผิวกระเบื้อง ศูนย์จากผิวฉาบผนังห้อง วงกบไม้กว้าง (ผู้ใช้กำหนด 12 พ.ย. 2569; วงกบ 3 ซม. ผมกำหนด)
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
                # ช่วงปลายผนัง B5 ใต้คานแนว B/E ก่อต่อจนชนผนังหลังห้อง (เดิมหยุดที่ผิวคาน เหลือช่องว่าง 9 ซม.) (ผู้ใช้แจ้ง 12 พ.ย. 2569)
                # ก่อถึงใต้ท้องคานหลัก ฉาบ 2 ด้านจบที่ผิวฉาบผนังหลังห้อง
                xa_, xb_ = (yb - 0.125, y_rm - WALL_T / 2) if side == 'N' else (y_rm + WALL_T / 2, ya + 0.125)
                add_wall(f'W-{tag}-WCX', f, 'y', b5x(i, side), xa_, xb_, zs, beam_soffit(f, 'main'), tw, tp,
                         name=f'ผนังห้องน้ำด้านระเบียง ช่วงต่อชนผนังหลังห้อง ชั้น {f} ห้อง {side}{i+1}')
                _yr = y_rm - (WALL_T / 2 + PL_T) if side == 'N' else y_rm + (WALL_T / 2 + PL_T)
                for _e in elements[-3:]:
                    if _e['id'] == f'W-{tag}-WCX-PL':
                        for _p in _e['geom']['parts']:
                            _p['poly'] = [[q[0], min(q[1], _yr) if side == 'N' else max(q[1], _yr)] for q in _p['poly']]
                        _e['qty']['area'] = round(_e['qty']['area'] * (abs(_yr - (xa_ if side == 'N' else xb_)) / abs(xb_ - xa_)), 3)
                # ผนังนอกห้องน้ำ: หน้าต่าง W1 KPA 0.60x0.40 ขอบล่าง 1.80 ชิดเสา (ศูนย์กลางห่างกริด 0.47 ตาม A106)
                add_wall(f'W-{tag}-OWC', f, 'x', y_out + (OUT_C if side == 'N' else -OUT_C),
                         ox(tx0, 1), ox(tx1, -1), zs, beam_soffit(f, 'edge', True), tw, tp,
                         [(g['xc'] + g['dr'] * 0.47, 0.60, 1.80, 0.40)], name=f'ผนังนอกห้องน้ำ ชั้น {f} ห้อง {side}{i+1}', mid_at_sill=True)
                elements[-1].update(name=f'หน้าต่าง W1 0.60x0.40 ใน W-{tag}-OWC')
                elements[-1]['qty'].update(type='หน้าต่างบานกระจกซ้อน อะลูมิเนียม', model=W1_MODEL)
                add_wall(f'W-{tag}-OBL', f, 'x', y_out + (OUT_C if side == 'N' else -OUT_C),
                         ox(bx0, 1), ox(bx1, -1), zs, beam_soffit(f, 'edge', True), tw, tp,
                         [((bx0 + bx1) / 2, 1.20, 0.90, 1.20)], name=f'ผนังนอกระเบียง ชั้น {f} ห้อง {side}{i+1}')
                # ช่องชาร์ฟท่อแนวดิ่งมุมห้องน้ำชิดเสาฝั่งแนวห้อง (A106 ขนาดนอก 0.475x0.65) ผนังบล็อก 2 ด้าน ก่อถึงใต้พื้นชั้นบน
                # ก่อผนังชาร์ฟสูงกว่าฝ้าทีบาร์ห้องน้ำ 0.20 (ฝ้าสูง 2.50 จากผิวกระเบื้อง) ไม่ก่อถึงท้องพื้น (ผู้ใช้สั่ง 12 พ.ย. 2569)
                zt = zs + 0.02 + WC_CEIL + 0.20
                # ก่อชนผิวบล็อกผนังห้อง/ผนังกริด (เดิมหยุดที่ผิวฉาบ) (ตรวจ 12 พ.ย. 2569)
                # ช่อง service 0.40x0.80 เข้าช่องชาร์ฟ ที่ผนัง SH1 ด้านห้องน้ำ ตามกรอบตัวอย่างผู้ใช้ (ศูนย์ห่างผิวฉาบผนังห้อง 0.357)
                # ขอบล่าง 1.60 ขอบบน 2.40 จากผิวกระเบื้อง (ใต้ฝ้า 0.10) วงกบไม้ + บานไม้บานพับ (ผู้ใช้สั่ง 12 พ.ย. 2569)
                sv_c, sv_sill = g['yr'] - g['s'] * SV_C, 0.02 + SV_SILL
                x_sh1 = g['xg'] + g['dr'] * (SH_W - WALL_T / 2)
                add_wall(f'W-{tag}-SH1', f, 'y', x_sh1, *lo(g['yr'] + g['s'] * PL_T, g['yr'] - g['s'] * SH_D), zs, zt, tw, tp,
                         [(sv_c, SV_W, sv_sill, SV_H)], name=f'ผนังช่องชาร์ฟห้องน้ำ ชั้น {f} ห้อง {side}{i+1} ด้านข้าง (ช่อง service {SV_W:.2f}x{SV_H:.2f})')
                _ov = next(e for e in elements if e['id'] == f'W-{tag}-SH1-O1')
                ya_, yb_ = sv_c - SV_W / 2, sv_c + SV_W / 2
                o0_, o1_ = zs + sv_sill, zs + sv_sill + SV_H
                dr_ = g['dr']
                _ov.update(name=f'บานเปิดช่อง service ไม้ บานพับ {SV_W - 2 * SV_FW:.2f}x{SV_H - 2 * SV_FW:.2f} ผนังชาร์ฟ ชั้น {f} ห้อง {side}{i+1}',
                           geom=rect_prism('y', x_sh1, ya_ + SV_FW, yb_ - SV_FW, o0_ + SV_FW, o1_ - SV_FW, dr_ * (WALL_T / 2 + PL_T - 0.01), 0.02))
                _ov['qty'] = dict(count=1, width=round(SV_W - 2 * SV_FW, 3), height=round(SV_H - 2 * SV_FW, 3), type='บานไม้เปิด บานพับ 2 ตัว', opening=f'{SV_W:.2f}x{SV_H:.2f}')
                fd, fo = WALL_T + PL_T, dr_ * (PL_T / 2)                          # วงกบลึกจากผิวบล็อกด้านในช่องถึงผิวฉาบด้านห้องน้ำ
                hz = dr_ * (WALL_T / 2 + PL_T + 0.003)
                add(f'W-{tag}-SH1-SVF', 'ประตูหน้าต่าง', f, 'A18', dict(type='multi', parts=[
                    rect_prism('y', x_sh1, ya_, ya_ + SV_FW, o0_, o1_, fo, fd), rect_prism('y', x_sh1, yb_ - SV_FW, yb_, o0_, o1_, fo, fd),
                    rect_prism('y', x_sh1, ya_ + SV_FW, yb_ - SV_FW, o1_ - SV_FW, o1_, fo, fd), rect_prism('y', x_sh1, ya_ + SV_FW, yb_ - SV_FW, o0_, o0_ + SV_FW, fo, fd),
                    rect_prism('y', x_sh1, ya_ + SV_FW - 0.006, ya_ + SV_FW + 0.006, o0_ + 0.12, o0_ + 0.18, hz, 0.006),
                    rect_prism('y', x_sh1, ya_ + SV_FW - 0.006, ya_ + SV_FW + 0.006, o1_ - 0.18, o1_ - 0.12, hz, 0.006)]),
                    name=f'วงกบไม้ช่อง service {SV_W:.2f}x{SV_H:.2f} + บานพับ 2 ตัว ผนังชาร์ฟ ชั้น {f} ห้อง {side}{i+1}', assumed=True,
                    qty=dict(count=1, frame_length=round(2 * SV_H + 2 * (SV_W - 2 * SV_FW), 3), frame_section=f'{SV_FW:.2f}x{fd:.3f}', hinges=2))
                add_wall(f'W-{tag}-SH2', f, 'x', g['yr'] - g['s'] * (SH_D - WALL_T / 2), *lo(g['xg'] - g['dr'] * PL_T, g['xg'] + g['dr'] * (SH_W - WALL_T)), zs, zt, tw, tp,
                         name=f'ผนังช่องชาร์ฟห้องน้ำ ชั้น {f} ห้อง {side}{i+1} ด้านหน้า')
                # ฉาบผนังชาร์ฟเฉพาะด้านในห้องน้ำ ผิวด้านในช่องชาร์ฟไม่ฉาบ (ผู้ใช้สั่ง 12 พ.ย. 2569)
                for sid, ax, wc_dir in (('SH1', 0, g['dr']), ('SH2', 1, -g['s'])):
                    pe = next(e for e in elements if e['id'] == f'W-{tag}-{sid}-PL')
                    wall = next(e for e in elements if e['id'] == f'W-{tag}-{sid}')
                    wcen = (min(p[ax] for p in wall['geom']['parts'][0]['poly']) + max(p[ax] for p in wall['geom']['parts'][0]['poly'])) / 2
                    pe['geom']['parts'] = [p for p in pe['geom']['parts']
                                           if (sum(q[ax] for q in p['poly']) / len(p['poly']) - wcen) * wc_dir > 0]
                    # ฉาบด้านห้องน้ำ: SH1 เริ่มที่ผิวฉาบผนังห้อง, SH2 เริ่มที่ผิวฉาบผนังกริดและเลยไปปิดหัวผนัง SH1 ถึงผิวฉาบ SH1 (มุมต่อเนื่อง) (12 พ.ย. 2569)
                    rng = lo(g['yr'], g['yr'] - g['s'] * SH_D) if sid == 'SH1' else lo(g['xg'], g['xg'] + g['dr'] * (SH_W + PL_T))
                    for p_ in pe['geom']['parts']:
                        p_['poly'] = [[min(max(q[0], rng[0]), rng[1]) if ax == 1 else q[0], min(max(q[1], rng[0]), rng[1]) if ax == 0 else q[1]] for q in p_['poly']]
                        if ax == 1:
                            xs_ = [q[0] for q in p_['poly']]
                            p_['poly'] = [[rng[0] if q[0] == min(xs_) else rng[1], q[1]] for q in p_['poly']]
                    pe['qty']['area'] = round(sum((max(q[1 - ax] for q in p_['poly']) - min(q[1 - ax] for q in p_['poly'])) * p_['t'] for p_ in pe['geom']['parts']), 3)
                    pe['name'] = f'ฉาบ W-{tag}-{sid} (เฉพาะด้านในห้องน้ำ)'
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
    # ผนังช่วงยื่นกริด 4 ชั้น 1 ไม่มีจริง (ผู้ใช้แจ้ง 11 พ.ย. 2569: เข้าใจผิด ลบออก)
    if k != 3:
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
    if n == 0:              # ผนังนอกโถงบันไดใต้ชานพักชั้น 1 ไม่มีจริง (ผู้ใช้แจ้ง 11 พ.ย. 2569: เข้าใจผิด ลบออก)
        continue
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
             [(GX[i] + 0.75, 0.90, 0.0, 2.00), (GX[i] + 2.00, 1.20, 1.00, 1.00)],
             name=f'ผนังหลังร้าน {i-3} (แนว B) ประตู 0.90 + หน้าต่างบานเลื่อนคู่ 1.20x1.00')
    # หน้าต่างบานเลื่อนคู่ กว้าง 1.20 ข้างประตูหลัง เว้นเสาเอ็น 0.20 จากวงกบประตู (ผู้ใช้สั่ง 23 พ.ย. 2569)
    # แก้ 23 พ.ย. 2569 (ผู้ใช้): สูง 1.00 หัวหน้าต่างระดับเดียวกับหัวประตู 2.00 → ขอบล่าง 1.00 จากพื้น
    elements[-1]['name'] = f'หน้าต่างบานเลื่อนคู่ 1.20x1.00 ใน W-F1-SH{i-3}-BK'
    elements[-1]['qty'].update(type='หน้าต่างบานเลื่อนคู่', sill=1.00)
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
             # ผู้ใช้สั่ง 23 พ.ย. 2569: เหลือห้องละ 1 บาน เก็บบานฝั่งอ่างล้างหน้า (ช่วงผนังด้านกริด 9)
             [((_xf + _a1) / 2 if i == 7 else (_a0 + _xf) / 2, 0.60, 1.80, 0.40)],
             name=f'ผนัง{room}ชั้น 1 ด้านหลังอาคาร (แนว B) หน้าต่าง W1 0.60x0.40')
    for _e in elements[-2:]:
        if _e['id'].startswith(f'W-F1-WC{n}-FR-O'):
            _e.update(name=f"หน้าต่าง W1 0.60x0.40 ระบายอากาศ ใน W-F1-WC{n}-FR")
            _e['qty'].update(type='หน้าต่างบานกระจกซ้อน อะลูมิเนียม', model=W1_MODEL)
    # แนว C: ผนังจากเสาซ้ายยาว 2.20 (ชาย) / 2.35 (หญิง) ที่เหลือเป็นช่องทางเข้าโล่งถึงเสาขวา (A901)
    add_wall(f'W-F1-WC{n}-BK', 1, 'x', yC, GX[i] + cw, GX[i] + 0.15 + (2.20 if i == 7 else 2.35), z0, beam_soffit(1, 'main'), 'A14', 'A14',
             [((GX[i] + cw + GX[i] + 0.15 + (2.20 if i == 7 else 2.35)) / 2, 0.60, 1.80, 0.40)],
             name=f'ผนัง{room}ชั้น 1 ด้านใต้ถุน (แนว C) ช่องทางเข้าโล่ง ไม่มีบาน + หน้าต่าง W1 0.60x0.40')
    # ผู้ใช้สั่ง 23 พ.ย. 2569: เพิ่มบานเกล็ด W1 แนวผนังทางเข้า ให้อากาศถ่ายเทกับบานแนว B (กึ่งกลางผนังทึบ ขอบล่าง 1.80 เท่าบานแนว B)
    for _e in elements[-2:]:
        if _e['id'].startswith(f'W-F1-WC{n}-BK-O'):
            _e.update(name=f"หน้าต่าง W1 0.60x0.40 ระบายอากาศ ใน W-F1-WC{n}-BK")
            _e['qty'].update(type='หน้าต่างบานกระจกซ้อน อะลูมิเนียม', model=W1_MODEL)
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
for e in [e for e in elements if e['category'] == 'เสา' and e['task'] in ('DONE', 'A01') and not e['id'].endswith('-ST') and not e['id'].startswith('SC-')]:
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
EL_PIPE = 0.020                  # ท่อร้อยสาย PVC ขาว 20 มม. (ผู้ใช้ส่งรูปข้อต่อ 20 มม. 12 พ.ย. 2569)
EL_BOX = (0.12, 0.075, 0.045)    # บล็อกลอย 2x4 นิ้ว วางนอน (กว้าง, สูง, ลึก)
EL_CU = (0.25, 0.22, 0.10)       # ตู้คอนซูมเมอร์ RACER เมน+4 ช่อง (ขนาดประมาณจากรูป)
EL_JB = (0.08, 0.04)             # junction box กลม Ø0.08 ลึก 0.04 (ค่าสมมติ)
EL_LAMP = (0.63, 0.07, 0.05)     # โคมรางตัวยู T8 1x18 (ยาว, กว้าง, สูง)
EL_SW_Z, EL_CU_Z = 1.20, 2.10    # ความสูงสวิตช์ / ขอบล่างตู้ จากพื้น (ผู้ใช้กำหนด)
EL_SO_Z = 0.30                   # ความสูงเต้ารับ (ผู้ใช้กำหนด)
EL_WL = (0.30, 0.08, 0.08)       # โคมติดผนังห้องน้ำ/หลังห้อง (ยาว, ยื่น, สูง) ค่าสมมติ รอรุ่น
BEND_R, SOCK = 0.06, 0.02               # งอโค้ง: รัศมีแนวศูนย์ 60 มม. ปากสวม 20 มม. (ค่าสมมติจากรูป)
JB_SQ = (0.10, 0.10, 0.05)              # กล่องพักสาย 4x4 นิ้ว (กว้าง, สูง, ลึก)
JB_DROP = 0.17                   # ลดระดับ JB1/JB2 ผนังหน้าห้องจากแนวท่อใต้คาน ให้ท่อออกบนกล่องแล้วหักเข้าห้องด้วยงอโค้งได้ (ผู้ใช้สั่ง 12 พ.ย. 2569)
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
            x_cu = GX[i] + col_w(f) + 0.01 + EL_CU[0] / 2                # ชิดผิวฉาบเสาหน้าห้องฝั่งประตู (เดิมกึ่งกลางประตู) (ผู้ใช้สั่ง 12 พ.ย. 2569)
            x_sw = GX[i] + 1.20 + 0.15 + EL_BOX[0] / 2                   # ฝั่งมือจับ (+x) ห่างวงกบ 0.15
            x_l = (GX[i] + GX[i + 1]) / 2
            y_rmface = (yB if side == 'N' else yE) - dn * (WALL_T / 2 + PL_T)
            y_l = (y_rmface + yface) / 2
            # แนวท่อ (ผู้ใช้สั่ง 12 พ.ย. 2569): JB1/JB2 ผนังหน้าห้องลดระดับลง ท่อออกบนกล่องตรงขึ้นแล้วหักเข้าห้อง;
            # ท่อเพดานแนวตรงจาก JB2 (เหนือสวิตช์) ถึงผนังหลังห้อง มี JB4 บนเพดานก่อนถึงแนวโคม แยกท่อไฟแสงสว่างเข้าโคมด้านใกล้แนวท่อด้านเดียว
            x_ln = x_sw
            zj = zr - JB_DROP if f < 5 else zr                                  # ศูนย์กล่อง JB1/JB2 (ชั้น 5 กล่องอยู่เหนือฝ้า)
            zh = zr if f < 5 else zr + JB_DROP                                   # แนวท่อแนวนอนออกจากหน้าห้อง
            x_bq = x_ln + JB_SQ[0] / 2 + BEND_R + SOCK                           # แนวท่อแยกเข้าโคม (ใกล้ปลายโคมด้านแนวท่อ)
            y4 = y_l - dn * (0.13 if f < 5 else 0.0)                             # JB4: ชั้น 2–4 ก่อนถึงแนวโคม, ชั้น 5 เหนือฝ้าตรงแนวโคม
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
                el_add(f'EL-{tag}-JB{k}', f, el_pipe((xj, yface, zj), (xj, yface + dn * EL_JB[1], zj)) | dict(w=EL_JB[0], d=EL_JB[0], sec=dict(d=EL_JB[0])),
                       f'Junction box {k} {room}', dict(count=1, size='Ø0.08'))
            if f < 5:
                zc = ceil - EL_PIPE / 2
                j4z0 = ceil - JB_SQ[2]                                           # กล่องติดท้องพื้น
            else:
                j4z0 = zh - JB_SQ[2] / 2                                         # กล่องเหนือฝ้า
            el_add(f'EL-{tag}-JB4', f, prism([(x_ln - JB_SQ[0] / 2, y4 - JB_SQ[1] / 2), (x_ln + JB_SQ[0] / 2, y4 - JB_SQ[1] / 2), (x_ln + JB_SQ[0] / 2, y4 + JB_SQ[1] / 2),
                                              (x_ln - JB_SQ[0] / 2, y4 + JB_SQ[1] / 2)], j4z0, JB_SQ[2]),
                   f'กล่องพักสายสี่เหลี่ยม 4x4 นิ้ว (junction box) บนเพดาน แยกท่อเข้าโคมกลางห้อง {room}',
                   dict(count=1, size='4x4 นิ้ว 0.10x0.10x0.05', type='กล่องพักสาย PVC ขาว สี่เหลี่ยม'))
            # ท่อ: ตู้→JB1 (ขึ้น), JB1→JB2 (ตามผนัง), JB2→สวิตช์ (ลง), JB2→โคมกลางห้อง
            yb = (yC + B2_DY['C'] - 0.125 - 0.03) if side == 'N' else (yD + B2_DY['D'] + 0.125 + 0.03)  # พ้นผิวคานแนว C/D ด้านในห้อง
            runs = [((x_cu, yp, cu_top), (x_cu, yp, zj)), ((x_cu, yp, zj), (x_sw, yp, zj)),
                    ((x_sw, yp, zj), (x_sw, yp, fl + EL_SW_Z + EL_BOX[1] / 2)), ((x_sw, yp, zj), (x_ln, yp, zh))]
            if f < 5:
                runs += [((x_ln, yp, zh), (x_ln, yb, zh)), ((x_ln, yb, zh), (x_ln, yb, zc)), ((x_ln, yb, zc), (x_ln, y4, zc)),
                         ((x_ln, y4, zc), (x_bq, y4, zc)), ((x_bq, y4, zc), (x_bq, y_l - dn * EL_LAMP[1] / 2, zc))]       # JB4 -> ด้านข้างโคมใกล้ปลาย
            else:
                runs += [((x_ln, yp, zh), (x_ln, y4, zh)), ((x_ln, y4, zh), (x_bq, y4, zh)), ((x_bq, y4, zh), (x_bq, y4, ceil))]  # JB4 -> ลงหลังโคม
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
            # เต้ารับคู่ย้ายมาติดผิวเสาด้านหน้า (หันเข้าห้อง) ชิดมุมเสาฝั่ง D2 ห่าง 0.02 ลดระยะท่อและข้อต่อ (ผู้ใช้สั่ง 12 พ.ย. 2569; เดิมอยู่ผนังกั้นห้องถัดเสา)
            # ข้างเสาฝั่ง D2 มีผนังเหลือ 1 ซม. ถึงขอบประตู D2 จึงติดผิวเสาด้านหน้า
            x_so = xb - dr * (cwf + COL_PL) + dr * (EL_BOX[0] / 2 + 0.02)
            y_cf = y_bal + sr * (cdf + COL_PL)                                   # ผิวฉาบเสาด้านหน้า (ด้านห้อง)
            el_add(f'EL-{tag}-SO1', f, el_box_on_x_wall(x_so, y_cf, sr, fl + EL_SO_Z, *EL_BOX),
                   f'เต้ารับคู่ 1 กล่อง ผิวเสาหลังห้องฝั่งประตูระเบียง {room}', dict(count=1, box='บล็อกลอย 2x4 นิ้ว', outlets=2, height=EL_SO_Z))
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
                r2 = [((x_ln, y4, zc), (x_ln, yb2, zc)), ((x_ln, yb2, zc), (x_ln, yb2, zr)), ((x_ln, yb2, zr), (x_ln, yq, zr))]
            else:
                r2 = [((x_ln, y4, zh), (x_ln, yq, zh)), ((x_ln, yq, zh), (x_ln, yq, zr))]
            r2 += [((x_ln, yq, zr), (x_s2, yq, zr)),                                                   # ตามผนังถึง JB3
                   ((x_s2, yq, zr), (x_s2, yq, fl + EL_SW_Z + EL_BOX[1] / 2))]                         # ลงสวิตช์ 2 ตัว
            xcp = xb - dr * (cwf + COL_PL + off)                                 # อ้อมผิวฉาบเสาฝั่ง D2
            ycp = y_bal + sr * (cdf + COL_PL + off)
            r2 += [((x_s2, yq, zr), (xcp, yq, zr)), ((xcp, yq, zr), (xcp, ycp, zr)), ((xcp, ycp, zr), (x_so, ycp, zr)),
                   ((x_so, ycp, zr), (x_so, ycp, fl + EL_SO_Z + EL_BOX[1] / 2))]
            for k, sgn, hz, nm in lamps:                                         # ลอดผนังที่แนว B5 แล้วตามผิวผนัง B5 ถึงโคม
                xl_ = b5 + sgn * dr * (wf + off)                                 # แนวท่อบนผิวผนัง B5
                xpen = xl_                                                       # จุดลอดผนังแนวเดียวกับท่อบนผิวผนัง B5 (พ้นเสาเอ็น 0.05) ไม่หักหลบ 18 มม. (12 พ.ย. 2569)
                yw = y_bal - sr * (wf + off)
                r2 += [((x_s2, yq, zr), (xpen, yq, zr)), ((xpen, yq, zr), (xpen, yw, zr)), ((xpen, yw, zr), (xl_, yw, zr)), ((xl_, yw, zr), (xl_, y_lw, zr)),
                       ((xl_, y_lw, zr), (xl_, y_lw, zs_ + hz + EL_WL[2] / 2))]
            r2 = [(a, b) for a, b in r2 if math.dist(a, b) > 1e-3]
            L2 = sum(math.dist(a, b) for a, b in r2)
            el_add(f'EL-{tag}-CD2', f, dict(type='multi', parts=[el_pipe(a, b) for a, b in r2]),
                   f'ท่อร้อยสาย PVC ขาว Ø1/2" วงจรหลังห้อง (สวิตช์หน้าห้องน้ำ เต้ารับคู่ โคมห้องน้ำ โคมหลังห้อง) {room}', dict(length=round(L2, 3), size='PVC 1/2"'))

# ---------- ท่อร้อยสาย/ข้อต่อ/กล่องพักสาย (ผู้ใช้สั่ง 12 พ.ย. 2569) ----------
# กล่องพักสายสี่เหลี่ยมตามท้องตลาด 4x4 นิ้ว (0.10x0.10 ลึก 0.05) แทนกล่องกลม; ท่อกลมขึ้นด้วย Profile Builder
# ข้อต่อตามรูปผู้ใช้ (ข้อต่อ PVC ขาว 20 มม.): หักมุม 90 องศาใช้งอโค้ง (ถ้าระยะไม่พอใช้งอสั้น), จุดแยกใช้สามทางมีฝา,
# ท่อเข้ากล่องใช้ข้อต่อเข้ากล่อง, ท่อยาวเกิน 4 ม. ใส่ข้อต่อตรงทุก 4 ม. (ความยาวท่อต่อเส้น)
CD_OD, CD_T = EL_PIPE, 0.0012            # ท่อ 20 มม. หนา 1.2 มม. (ค่าสมมติ)
FT_OD, FT_T = 0.0245, 0.00225           # ตัวข้อต่อ (สวมนอกท่อ) โตนอก 24.5 มม.
SHORT_L, TEE_L, CON_L, CPL_L, STICK = 0.03, 0.035, 0.03, 0.045, 4.0
def _cd_poly(od, t, n=24):
    r, ri = od / 2, od / 2 - t
    return ([[round(r * math.cos(2 * math.pi * k / n), 5), round(r * math.sin(2 * math.pi * k / n), 5)] for k in range(n)],
            [[round(ri * math.cos(2 * math.pi * k / n), 5), round(ri * math.sin(2 * math.pi * k / n), 5)] for k in range(n)])


_CD_PIPE = _cd_poly(CD_OD, CD_T)
_CD_FIT = _cd_poly(FT_OD, FT_T)
_CD_NUT = _cd_poly(0.030, 0.00475)


def _cd_mem(path, prof):
    path = [tuple(round(v, 4) for v in p) for p in path]
    g = member(path[0], path[-1], prof[0][0][0] * 2, prof[0][0][0] * 2)
    g['shape'] = 'POLY'; g['poly2d'], g['hole2d'] = prof
    if len(path) > 2:
        g['path'] = [list(p) for p in path]
    return g


def _v(a, b, t=1.0):
    return tuple(x + t * y for x, y in zip(a, b))


def _conduit(segs, boxes, obst=()):
    """segs: [(p, q)] แนวแกน; boxes: [(x0,y0,z0,x1,y1,z1, kind, mount_axis, mount_val)]
    คืน (parts, qty) ท่อ+ข้อต่อ"""
    R4 = lambda p: tuple(round(v, 4) for v in p)
    segs = [(R4(a), R4(b)) for a, b in segs if math.dist(a, b) > 1e-4]
    pts = set(p for s_ in segs for p in s_)

    def ax_of(a, b):
        return [k for k in range(3) if abs(a[k] - b[k]) > 1e-6][0]
    edges = set()
    for a, b in segs:
        k = ax_of(a, b)
        lo_, hi_ = sorted((a[k], b[k]))
        on = sorted([p for p in pts if all(abs(p[j] - a[j]) < 1e-4 for j in range(3) if j != k) and lo_ - 1e-6 <= p[k] <= hi_ + 1e-6], key=lambda p: p[k])
        for p, q in zip(on, on[1:]):
            if math.dist(p, q) > 1e-4:
                edges.add(tuple(sorted((p, q))))
    # ตัดส่วนที่อยู่ในกล่อง
    ends = {}                                                    # จุดปลายที่ผิวกล่อง -> (kind, ผ่านผิวยึดผนัง?)
    out = []
    for a, b in edges:
        k = ax_of(a, b)
        pieces = [(a, b)]
        for bx in boxes:
            lo, hi = bx[0:3], bx[3:6]
            nxt = []
            for p, q in pieces:
                if all(lo[j] + 1e-6 < p[j] < hi[j] - 1e-6 for j in range(3) if j != k):
                    s0, s1 = sorted((p[k], q[k])); p0_, q0_ = (p, q) if p[k] <= q[k] else (q, p)
                    if s1 <= lo[k] + 1e-6 or s0 >= hi[k] - 1e-6:
                        nxt.append((p, q)); continue
                    # ออกทางผิวหลังกล่องที่ติดผนัง = ลอดเข้าผนัง (ไม่ใส่ข้อต่อเข้ากล่อง); ออกทางผิวหน้า/ข้าง = ใส่ข้อต่อเข้ากล่อง
                    mnt = lambda v: bx[7] == k and (bx[8] is None and bx[6] == 'LP' or bx[8] is not None and abs(v - bx[8]) < 1e-6)
                    if s0 < lo[k]:
                        e_ = tuple(lo[k] if j == k else p0_[j] for j in range(3)); nxt.append((p0_, e_))
                        ends[R4(e_)] = (bx[6], mnt(lo[k]))
                    if s1 > hi[k]:
                        e_ = tuple(hi[k] if j == k else p0_[j] for j in range(3)); nxt.append((e_, q0_))
                        ends[R4(e_)] = (bx[6], mnt(hi[k]))
                else:
                    nxt.append((p, q))
            pieces = nxt
        out += [(R4(p), R4(q)) for p, q in pieces if math.dist(p, q) > 1e-4]
    adj = collections.defaultdict(list)
    for p, q in out:
        adj[p].append(q); adj[q].append(p)
    unit = lambda a, b: tuple((y - x) / math.dist(a, b) for x, y in zip(a, b))
    colin = lambda u, v: abs(sum(x * y for x, y in zip(u, v)) + 1) < 1e-6
    # ชนิดโหนด
    node = {}
    for p, ns in adj.items():
        us = [unit(p, q) for q in ns]
        if len(ns) == 1:
            if p not in ends:                                    # ปลายท่อที่ชนผิวกล่องพอดี (ไม่ได้ถูกตัด)
                k = ax_of(p, ns[0])
                for bx in boxes:
                    if all(bx[j] - 1e-4 <= p[j] <= bx[j + 3] + 1e-4 for j in range(3)):
                        ends[p] = (bx[6], bx[7] == k and (bx[8] is None and bx[6] == 'LP' or bx[8] is not None and abs(p[k] - bx[8]) < 1e-4)); break
            node[p] = ('box', ends.get(p)) if p in ends else ('end', None)
        elif len(ns) == 2:
            node[p] = ('pass', None) if colin(us[0], us[1]) else ('bend', us)
        elif len(ns) == 3:
            run = [(i, j) for i in range(3) for j in range(i + 1, 3) if colin(us[i], us[j])]
            node[p] = ('tee', (us, run[0] if run else None))
        else:
            node[p] = ('cross', us)
    # แนวท่อตรงต่อเนื่อง (ผ่านโหนด pass)
    seen, runs = set(), []
    for p, q in out:
        if (p, q) in seen or (q, p) in seen:
            continue
        chain = [p, q]; seen.add((p, q))
        for di in (0, 1):
            while True:
                end, prev = (chain[-1], chain[-2]) if di == 0 else (chain[0], chain[1])
                if node[end][0] != 'pass':
                    break
                nx = [n for n in adj[end] if n != prev][0]
                seen.add((end, nx))
                if di == 0: chain.append(nx)
                else: chain.insert(0, nx)
        runs.append((chain[0], chain[-1]))
    ext = lambda t: {'bend': BEND_R + SOCK, 'short': SHORT_L, 'tee': TEE_L}.get(t, 0.0)
    kind = {p: ('bend' if v[0] == 'bend' else v[0]) for p, v in node.items()}
    # งอโค้งที่แนวโค้งตัดเข้าผิวเสา (อ้อมมุมเสา) -> ใช้งอสั้นแทน (ตรวจ 12 พ.ย. 2569)
    for p, v in node.items():
        if v[0] != 'bend':
            continue
        ua, ub = v[1]
        c = _v(_v(p, ua, BEND_R), ub, BEND_R)
        arc = [tuple(cc - BEND_R * (math.cos(th) * b_ + math.sin(th) * a_) for cc, a_, b_ in zip(c, ua, ub))
               for th in (math.pi / 2 * k_ / 16 for k_ in range(17))]
        rr = FT_OD / 2
        if any(all(ob[j] - rr < q[j] < ob[j + 3] + rr for j in range(3)) for q in arc for ob in obst):
            kind[p] = 'short'
    for _ in range(6):                                           # ระยะไม่พอสำหรับงอโค้ง -> งอสั้น
        ch = False
        for a, b in runs:
            if ext(kind[a]) + ext(kind[b]) > math.dist(a, b) + 1e-6:
                for p in (a, b):
                    if kind[p] == 'bend':
                        kind[p] = 'short'; ch = True
        if not ch:
            break
    trim = {'bend': BEND_R, 'short': 0.012, 'tee': 0.015}
    parts, cnt = [], collections.Counter()
    plen = 0.0
    pipe_runs = []
    for a, b in runs:
        u = unit(a, b); L = math.dist(a, b)
        ta, tb = trim.get(kind[a], 0.0), trim.get(kind[b], 0.0)
        if L - ta - tb < 0.005:
            cnt['tight'] += 1; ta = tb = 0.0
        pa, pb = _v(a, u, ta), _v(b, u, -tb)
        Lp = math.dist(pa, pb)
        # ท่อยาวเกิน 4 ม.: ท่อนละ 4 ม. ต่อด้วยข้อต่อตรง
        n = max(1, math.ceil(Lp / STICK - 1e-9))
        parts.append(_cd_mem([pa, pb], _CD_PIPE)); plen += Lp
        isbox = lambda p: kind[p] == 'box' and node[p][1] is not None and node[p][1][0] in ('JB', 'SW', 'SO', 'CU')
        pipe_runs.append((pa, pb, u, isbox(a), isbox(b)))
        for k_ in range(1, n):
            c = _v(pa, u, k_ * STICK)
            parts.append(_cd_mem([_v(c, u, -CPL_L / 2), _v(c, u, CPL_L / 2)], _CD_FIT)); cnt['coupling'] += 1
        cnt['pieces'] += n
        for p, d in ((a, u), (b, tuple(-x for x in u))):
            if kind[p] == 'box' and node[p][1] and node[p][1][0] in ('JB', 'SW', 'SO', 'CU') and not node[p][1][1]:
                parts.append(_cd_mem([p, _v(p, d, CON_L)], _CD_FIT))
                parts.append(_cd_mem([p, _v(p, d, 0.006)], _CD_NUT)); cnt['connector'] += 1
    for p, t in kind.items():
        if t in ('bend', 'short'):
            ua, ub = node[p][1]
            if t == 'bend':
                c = _v(_v(p, ua, BEND_R), ub, BEND_R)
                arc = []
                for k_ in range(9):
                    th = math.pi / 2 * k_ / 8
                    arc.append(tuple(cc - BEND_R * (math.cos(th) * b_ + math.sin(th) * a_) for cc, a_, b_ in zip(c, ua, ub)))
                path = [_v(p, ua, BEND_R + SOCK)] + arc + [_v(p, ub, BEND_R + SOCK)]
                parts.append(_cd_mem(path, _CD_FIT)); cnt['bend'] += 1
            else:
                parts.append(_cd_mem([_v(p, ua, SHORT_L), p, _v(p, ub, SHORT_L)], _CD_FIT)); cnt['short'] += 1
        elif t == 'tee':
            us, run = node[p][1]
            if run is None:
                cnt['odd_tee'] += 1; continue
            i, j = run; br = [k_ for k_ in range(3) if k_ not in run][0]
            arm = lambda k_: min(TEE_L, min(math.dist(p, q) for q in adj[p] if math.dist(unit(p, q), us[k_]) < 1e-6))
            parts.append(_cd_mem([_v(p, us[i], arm(i)), _v(p, us[j], arm(j))], _CD_FIT))
            parts.append(_cd_mem([p, _v(p, us[br], arm(br))], _CD_FIT))
            g = member(_v(p, us[i], 0.022), _v(p, us[j], 0.022), 0.032, 0.032); g['pb'] = True      # ตัวสามทางมีฝา
            g['p0'] = [round(v, 4) for v in g['p0']]; g['p1'] = [round(v, 4) for v in g['p1']]
            parts.append(g); cnt['tee'] += 1
        elif t == 'cross':
            cnt['cross'] += 1
    cnt['_runs'] = pipe_runs
    qty = dict(length=round(plen, 3), size='PVC ขาว 20 มม.', pipe_pieces=cnt['pieces'], sticks_4m=math.ceil(plen / STICK), bend_90=cnt['bend'], short_elbow=cnt['short'],
               tee_cover=cnt['tee'], coupling=cnt['coupling'], box_connector=cnt['connector'])
    return parts, qty, cnt


_CD_WARN = collections.Counter()
_COL_OBST = collections.defaultdict(list)                   # ผิวฉาบเสาแต่ละชั้น (กรอบ) สำหรับตรวจงอโค้งชนมุมเสา
for e in elements:
    if e['category'] == 'งานฉาบ' and re.match(r'^PL-C\d', e['id']) and e['geom']['type'] == 'prism':
        g = e['geom']; xs = [q[0] for q in g['poly']]; ys = [q[1] for q in g['poly']]
        _COL_OBST[e['floor']].append((min(xs), min(ys), g['z0'], max(xs), max(ys), g['z0'] + g['t']))
_CD_RUNS = {}
_E = {e['id']: e for e in elements}
for e in list(elements):
    m_ = re.match(r'^EL-(F\d-[NS]\d)-JB\d$', e['id'])
    if m_ and e['geom']['type'] == 'member':                                                       # กล่องกลม -> กล่องสี่เหลี่ยม 4x4 นิ้ว
        g = e['geom']; p0, p1 = g['p0'], g['p1']
        dn_ = 1 if p1[1] > p0[1] else -1
        e['geom'] = el_box_on_x_wall(p0[0], p0[1], dn_, p0[2], *JB_SQ)
        e['name'] = e['name'].replace('Junction box', 'กล่องพักสายสี่เหลี่ยม 4x4 นิ้ว (junction box)')
        e['qty'] = dict(count=1, size='4x4 นิ้ว 0.10x0.10x0.05', type='กล่องพักสาย PVC ขาว สี่เหลี่ยม')
_WALLBB = collections.defaultdict(list)                   # ชั้น -> กรอบผนัง/ฉาบผนัง (หาผิวหลังกล่องที่ติดผนัง)
for e in elements:
    if e['category'] in ('ผนัง', 'งานฉาบ') and e['id'].startswith('W-'):
        for p in (e['geom']['parts'] if e['geom']['type'] == 'multi' else [e['geom']]):
            if p['type'] == 'prism':
                xs = [q[0] for q in p['poly']]; ys = [q[1] for q in p['poly']]
                _WALLBB[e['floor']].append((min(xs), min(ys), p['z0'], max(xs), max(ys), p['z0'] + p['t']))


def _seg_dist(q, a, b):
    ab = [b[i] - a[i] for i in range(3)]; L2 = sum(v * v for v in ab)
    t = 0.0 if L2 < 1e-12 else max(0.0, min(1.0, sum((q[i] - a[i]) * ab[i] for i in range(3)) / L2))
    return math.dist(q, [a[i] + t * ab[i] for i in range(3)])


def _cd_qty(parts):
    """นับปริมาณจากชิ้นท่อ/ข้อต่อ"""
    pipes = [p for p in parts if p.get('w') == CD_OD and not p.get('path')]
    plen = sum(math.dist(p['p0'], p['p1']) for p in pipes)
    fit = [p for p in parts if p.get('w') == FT_OD and not p.get('path')]
    return dict(length=round(plen, 3), size='PVC ขาว 20 มม.', pipe_pieces=sum(max(1, math.ceil(math.dist(p['p0'], p['p1']) / STICK - 1e-9)) for p in pipes),
                sticks_4m=math.ceil(plen / STICK), bend_90=sum(1 for p in parts if p.get('path') and len(p['path']) > 3),
                short_elbow=sum(1 for p in parts if p.get('path') and len(p['path']) == 3), tee_cover=sum(1 for p in parts if p.get('pb')),
                coupling=sum(1 for p in fit if abs(math.dist(p['p0'], p['p1']) - CPL_L) < 1e-4),
                box_connector=sum(1 for p in parts if p.get('w') and abs(p['w'] - 0.030) < 1e-6 and not p.get('pb')))


_CD_GROUPS = collections.defaultdict(list)
for e in elements:
    m_ = re.match(r'^EL-(F\d-[NS]\d)-CD\d$', e['id'])
    if m_:
        _CD_GROUPS[m_.group(1)].append(e)
for tag_, els in _CD_GROUPS.items():                       # ท่อวงจรในห้องเดียวกันคิดรวม (จุดแยกสามทางระหว่าง CD1/CD2) แล้วแบ่งชิ้นคืนตามแนวเดิม
    boxes = []
    for k_, kd in (('JB1', 'JB'), ('JB2', 'JB'), ('JB3', 'JB'), ('JB4', 'JB'), ('SW1', 'SW'), ('SW2', 'SW'), ('SO1', 'SO'), ('CU', 'CU'), ('LP1', 'LP'), ('LP2', 'LP'), ('LP3', 'LP')):
        b_ = _E.get(f'EL-{tag_}-{k_}')
        if not b_:
            continue
        g = b_['geom']; xs = [q[0] for q in g['poly']]; ys = [q[1] for q in g['poly']]
        bb_ = (min(xs), min(ys), g['z0'], max(xs), max(ys), g['z0'] + g['t'])
        # ผิวที่ยึดผนัง = ด้านความลึกกล่อง (แกนแนวนอนที่สั้นกว่า) ฝั่งที่ชนผนัง: ท่อที่ออกทางผิวนี้คือลอดเข้าผนัง ไม่ใส่ข้อต่อเข้ากล่อง
        mount_ax = 0 if (bb_[3] - bb_[0]) < (bb_[4] - bb_[1]) else 1
        mount_v = None
        if kd != 'LP':
            zc_ = (bb_[2] + bb_[5]) / 2
            for v_, dv in ((bb_[mount_ax], -0.005), (bb_[mount_ax + 3], 0.005)):
                q_ = [(bb_[0] + bb_[3]) / 2, (bb_[1] + bb_[4]) / 2, zc_]; q_[mount_ax] = v_ + dv
                if any(all(w[j] <= q_[j] <= w[j + 3] for j in range(3)) for w in _WALLBB[els[0]['floor']]):
                    mount_v = v_
        boxes.append(bb_ + (kd, mount_ax, mount_v))
    own = {e['id']: [(p['p0'], p['p1']) for p in e['geom']['parts']] for e in els}
    segs = [sg for e in els for sg in own[e['id']]]
    parts, qty, cnt = _conduit(segs, boxes, _COL_OBST[els[0]['floor']])
    def owner(pt):
        d = {k: min(_seg_dist(pt, a, b) for a, b in v) for k, v in own.items()}
        return min(sorted(d), key=lambda k: d[k] - (1e-3 if k.endswith('CD1') else 0.0))
    def refpt(p):
        if p.get('path'):
            return p['path'][len(p['path']) // 2]
        return [(a + b) / 2 for a, b in zip(p['p0'], p['p1'])]
    split = collections.defaultdict(list)
    for p in parts:
        split[owner(refpt(p))].append(p)
    runs_ = collections.defaultdict(list)
    for r_ in cnt['_runs']:
        runs_[owner([(a + b) / 2 for a, b in zip(r_[0], r_[1])])].append(r_)
    for e in els:
        e['geom'] = dict(type='multi', parts=split[e['id']])
        e['qty'] = _cd_qty(split[e['id']])
        e['name'] = e['name'].replace('PVC ขาว Ø1/2"', 'PVC ขาว 20 มม. (Profile Builder) พร้อมข้อต่อ')
        _CD_RUNS[e['id']] = runs_[e['id']]
    _CD_WARN.update({k: v for k, v in cnt.items() if k in ('tight', 'odd_tee', 'cross')})
# ก้ามปูยึดท่อ (ผู้ใช้สั่ง 12 พ.ย. 2569): ตัวแรกห่างกล่องไม่เกิน 1 ม. (วาง 0.30), ระยะระหว่างตัวไม่เกิน 3 ม.;
# ท่อตรงทุกช่วงที่ยาวตั้งแต่ 0.25 ม. มีอย่างน้อย 1 ตัว; แผ่นฐานติดผิวผนัง/ท้องพื้นที่ใกล้ท่อที่สุด (ถ้าไม่มีผิวใกล้ เช่น เหนือฝ้าชั้น 5 มีแต่แถบรัด)
CLIP_FROM_BOX, CLIP_MAX, CLIP_W = 0.30, 3.0, 0.015
_SURF = collections.defaultdict(list)                     # ชั้น -> กรอบผิวฉาบ/ผนัง
for e in elements:
    if e['category'] in ('งานฉาบ', 'ผนัง', 'เสาเอ็นคานเอ็น') or e['id'].startswith('PL-'):
        for p in (e['geom']['parts'] if e['geom']['type'] == 'multi' else [e['geom']]):
            if p['type'] == 'prism':
                xs = [q[0] for q in p['poly']]; ys = [q[1] for q in p['poly']]
                _SURF[e['floor']].append((min(xs), min(ys), p['z0'], max(xs), max(ys), p['z0'] + p['t']))
            elif p['type'] == 'member' and abs(p['p0'][2] - p['p1'][2]) < 1e-6 and 'shape' not in p:   # ฉาบคาน (ชิ้นแนวนอนตามแกน)
                a0, a1 = p['p0'], p['p1']
                ka = 0 if abs(a0[0] - a1[0]) > 1e-6 else 1
                lo = [min(a0[0], a1[0]), min(a0[1], a1[1]), a0[2] - p['d'] / 2]
                hi = [max(a0[0], a1[0]), max(a0[1], a1[1]), a0[2] + p['d'] / 2]
                lo[1 - ka] -= p['w'] / 2; hi[1 - ka] += p['w'] / 2
                _SURF[e['floor']].append(tuple(lo + hi))
_SURF[6] = []


def _clip_mount(P, k, fl):
    best = None
    for bb in _SURF.get(fl, []) + _SURF.get(fl + 1, []):
        for j in range(3):
            if j == k:
                continue
            o = [x for x in range(3) if x not in (j,)]
            if not all(bb[x] - 1e-4 <= P[x] <= bb[x + 3] + 1e-4 for x in o):
                continue
            for sg in (1, -1):
                face = bb[j] if sg > 0 else bb[j + 3]
                dd = (face - P[j]) * sg
                if 0.008 <= dd <= 0.045 and (best is None or dd < best[0]):          # ห่างผิวเกินปกติ: แผ่นฐานหนาขึ้นเป็นแท่นรอง
                    best = (dd, j, sg, face)
    return best


for eid, runs in list(_CD_RUNS.items()):
    src = next(e for e in elements if e['id'] == eid)
    fl = src['floor']
    parts, n_cl = [], 0
    for pa, pb, u, ba, bb_ in runs:
        L = math.dist(pa, pb)
        ts = []
        if ba: ts.append(min(CLIP_FROM_BOX, L / 2))
        if bb_: ts.append(max(L - CLIP_FROM_BOX, L / 2))
        ts = sorted(set(round(t, 4) for t in ts))
        if not ts and L >= 0.25:
            ts = [L / 2]
        if ts:                                                # เติมให้ห่างไม่เกิน 3 ม. (รวมจากปลายท่อ)
            full = [0.0] + ts + [L]
            ts2 = []
            for t0, t1 in zip(full, full[1:]):
                nadd = math.ceil((t1 - t0) / CLIP_MAX - 1e-9) - 1
                ts2 += [t0 + (t1 - t0) * q / (nadd + 1) for q in range(1, nadd + 1)]
            ts = sorted(ts + ts2)
        k = [x for x in range(3) if abs(u[x]) > 0.5][0]
        for t in ts:
            P = _v(pa, u, t)
            parts.append(dict(type='member', p0=[round(v, 4) for v in _v(P, u, -CLIP_W / 2)], p1=[round(v, 4) for v in _v(P, u, CLIP_W / 2)],
                              w=0.027, d=0.027, shape='O', sec=dict(d=0.027)))          # แถบรัดท่อ
            mt = _clip_mount(P, k, fl)
            if mt:                                            # แผ่นฐานก้ามปู 0.04 x 0.015 หนา 3 มม. บนผิวยึด
                dd, j, sg, face = mt
                lo_, hi_ = [0.0] * 3, [0.0] * 3
                third = [x for x in range(3) if x not in (k, j)][0]
                lo_[k], hi_[k] = P[k] - CLIP_W / 2, P[k] + CLIP_W / 2
                lo_[third], hi_[third] = P[third] - 0.02, P[third] + 0.02
                lo_[j], hi_[j] = sorted((face, face - sg * max(0.003, dd - 0.0135)))
                parts.append(dict(type='prism', poly=[[round(lo_[0], 4), round(lo_[1], 4)], [round(hi_[0], 4), round(lo_[1], 4)], [round(hi_[0], 4), round(hi_[1], 4)], [round(lo_[0], 4), round(hi_[1], 4)]],
                                  z0=round(lo_[2], 4), t=round(hi_[2] - lo_[2], 4)))
            n_cl += 1
    if parts:
        add(eid + '-CL', 'ไฟฟ้า', fl, 'A21', dict(type='multi', parts=parts),
            name=f'ก้ามปูยึดท่อร้อยสาย 20 มม. ({eid})', assumed=True, qty=dict(count=n_cl, size='20 มม.', type='ก้ามปู PVC ขาว'))
ASSUMPTIONS.append('ท่อร้อยสาย: PVC ขาว 20 มม. หนา 1.2 มม.; ข้อต่อโตนอก 24.5 มม.; งอโค้งรัศมี 60 มม. ปากสวม 20 มม.; งอสั้นขา 30 มม.; สามทางมีฝา; ข้อต่อเข้ากล่องยาว 30 มม.; กล่องพักสาย 4x4 นิ้ว 0.10x0.10x0.05 (ขนาดประมาณจากสินค้าทั่วไป)')

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
        if g.get('path'):                        # แนว chain หลายจุด (ข้อต่องอ/งอสั้น) ต้องกลับแกน y ด้วย (แก้ 12 พ.ย. 2569: เดิมไม่กลับ ข้อต่อไปอยู่ผิดตำแหน่ง)
            g['path'] = [[q[0], round(Y - q[1], 4), q[2]] for q in g['path']]
        if g.get('shape') == 'POLY':             # หน้าตัดไม่สมมาตร: กลับทิศ chain ให้ด้านหน้าหน้าตัดยังหันทิศเดิมหลังกลับแกน y
            g['p0'], g['p1'] = g['p1'], g['p0']
            if g.get('path'):
                g['path'] = g['path'][::-1]
            if g.get('trim'):
                g['trim'] = g['trim'][::-1]
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
# ห้องน้ำห้องพัก ชั้น 2–5: เปลี่ยนรุ่น (ผู้ใช้แจ้ง 24 พ.ย. 2569) ห้องน้ำรวมชั้น 1 คงเดิม
for e in elements:
    if e['category'] == 'สุขภัณฑ์' and re.match(r'^FX-F[2-5]-[NS]\d-WC$', e['id']):
        e['qty']['model'] = 'COTTO C13970 สุขภัณฑ์ 2 ชิ้น 6 ลิตร สีขาว'
    elif e['category'] == 'สุขภัณฑ์' and re.match(r'^FX-F[2-5]-[NS]\d-LAV$', e['id']):
        e['qty']['model'] = 'COTTO C002 อ่างล้างหน้าแขวน 51.5x35x20 ซม. สีขาว'


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

# ---------- เพลทฝังผิวเสา C/10 รับ END PLATE คานชานพักบันไดหนีไฟ (ผู้ใช้สั่ง 11 พ.ย. 2569) ----------
# PL12x150x300 ฝังเสมอผิวนอกเสา C1 10/C ด้านกริด 11 ทุกชั้นที่มีชานพัก (2–5) กึ่งกลางเพลทที่กึ่งกลางคาน H200 (หลังคาน FL - 0.10)
# เหล็กเดือย 6-DB16 เชื่อมหลังเพลท ยาว 0.15 เข้าเนื้อเสา งอปลายลง 0.05 (ทิศงอผมกำหนด); ฉาบเสาเว้นช่องเพลท
EP_BOLT16 = [[round(0.008 * math.cos(2 * math.pi * k / 16), 5), round(0.008 * math.sin(2 * math.pi * k / 16), 5)] for k in range(16)]
_xf = GX[9] + COL_SEC[1][0] / 2                     # ผิวนอกเสากริด 10
for f in (2, 3, 4, 5):
    zc = FL[f] - 0.10 - 0.10
    yc = GY['C']
    add(f'SC-EP-10C-F{f}', 'เสา', f - 1, 'DONE',
        prism([(_xf - 0.012, yc - 0.075), (_xf, yc - 0.075), (_xf, yc + 0.075), (_xf - 0.012, yc + 0.075)], round(zc - 0.15, 4), 0.30),
        name=f'เพลทฝังผิวเสา C/10 PL12x150x300 รับ END PLATE คานชานพักชั้น {f}', assumed=True,
        qty=dict(count=1, size='PL12x150x300', weight_kg=round(0.15 * 0.30 * 0.012 * 7850, 2)))
    elements[-1]['material'] = 'BIM-เหล็กโครงสร้าง'
    parts = []
    for dy in (-0.045, 0.045):
        for dz in (-0.10, 0.0, 0.10):
            y, z = yc + dy, zc + dz
            a = member((_xf - 0.012, y, z), (_xf - 0.012 - 0.15 + 0.008, y, z), 0.016, 0.016)
            b = member((_xf - 0.012 - 0.15, y, z + 0.008), (_xf - 0.012 - 0.15, y, z - 0.05), 0.016, 0.016)
            for g in (a, b):
                g['shape'] = 'POLY'; g['poly2d'] = EP_BOLT16
            parts += [a, b]
    add(f'SC-EP-10C-F{f}-DW', 'เสา', f - 1, 'DONE', dict(type='multi', parts=parts),
        name=f'เหล็กเดือย 6-DB16 ยาว 0.15 งอปลาย 0.05 หลังเพลทฝังเสา C/10 ชั้น {f}', assumed=True,
        qty=dict(count=6, size='DB16', length_each=0.20, weight_kg=round(6 * 0.20 * 1.578, 2)))
    elements[-1]['material'] = 'BIM-สลักเหล็ก'
    # ฉาบเสา C/10 ที่ช่วงชั้นนี้: เว้นช่องหน้าเพลท
    pe = next(e for e in elements if e['id'] == f'PL-C1-10C-F{f - 1}')
    ng, rem = _clip_geom(pe['geom'], [[_xf - 0.001, _xf + PL_COL + 0.001, yc - 0.075, yc + 0.075, zc - 0.15, zc + 0.15]])
    if ng is not None:
        pe['geom'] = ng
        pe['qty']['area'] = round(pe['qty']['area'] - 0.15 * 0.30, 3)

# ---------- เพลทฝังคาน B1 กริด 10 แนวเสา 10/M (ผู้ใช้สั่ง 11 พ.ย. 2569) ----------
# รูปแบบเดียวกับเพลทเสา C/10: PL12x150x300 + เดือย 6-DB16 ระดับเดียวกัน (กึ่งกลาง FL - 0.20) ชั้น 2–5
# ฝังเสมอผิวนอกคาน B1-10-BC (และขอบพื้นเหนือคาน) ที่แนวเสา 10/M ไว้เป็นจุดยึดเสาภายหลัง; ฉาบคานเว้นช่องเพลท
for f in (2, 3, 4, 5):
    zc = FL[f] - 0.10 - 0.10
    yc = FS_YM
    add(f'SC-EP-10M-F{f}', 'เสา', f - 1, 'DONE',
        prism([(_xf - 0.012, yc - 0.075), (_xf, yc - 0.075), (_xf, yc + 0.075), (_xf - 0.012, yc + 0.075)], round(zc - 0.15, 4), 0.30),
        name=f'เพลทฝังผิวคาน B1 กริด 10 แนวเสา 10/M PL12x150x300 จุดยึดเสาเหล็กชั้น {f}', assumed=True,
        qty=dict(count=1, size='PL12x150x300', weight_kg=round(0.15 * 0.30 * 0.012 * 7850, 2)))
    elements[-1]['material'] = 'BIM-เหล็กโครงสร้าง'
    parts = []
    for dy in (-0.045, 0.045):
        for dz in (-0.10, 0.0, 0.10):
            y, z = yc + dy, zc + dz
            a = member((_xf - 0.012, y, z), (_xf - 0.012 - 0.15 + 0.008, y, z), 0.016, 0.016)
            b = member((_xf - 0.012 - 0.15, y, z + 0.008), (_xf - 0.012 - 0.15, y, z - 0.05), 0.016, 0.016)
            for g in (a, b):
                g['shape'] = 'POLY'; g['poly2d'] = EP_BOLT16
            parts += [a, b]
    add(f'SC-EP-10M-F{f}-DW', 'เสา', f - 1, 'DONE', dict(type='multi', parts=parts),
        name=f'เหล็กเดือย 6-DB16 ยาว 0.15 งอปลาย 0.05 หลังเพลทฝังคาน B1 กริด 10 แนวเสา 10/M ชั้น {f}', assumed=True,
        qty=dict(count=6, size='DB16', length_each=0.20, weight_kg=round(6 * 0.20 * 1.578, 2)))
    elements[-1]['material'] = 'BIM-สลักเหล็ก'
    # ฉาบคาน (ชิ้นผิวนอก) แยกเป็น 3 ชิ้น เว้นช่องหน้าเพลท
    pe = next(e for e in elements if e['id'] == f'PL-B1-10-BC-L{f}')
    po = next(p for p in pe['geom']['parts'] if p['type'] == 'member' and abs(p['p0'][0] - _xf - p['w'] / 2) < 1e-6)
    i = pe['geom']['parts'].index(po)
    px, pc, pd, pw = po['p0'][0], po['p0'][2], po['d'], po['w']
    ya, yb = sorted((po['p0'][1], po['p1'][1]))
    zb, zt = pc - pd / 2, pc + pd / 2
    zh = zc - 0.15
    new = [member((px, ya, pc), (px, yc - 0.075, pc), pw, pd), member((px, yc + 0.075, pc), (px, yb, pc), pw, pd),
           member((px, yc - 0.075, (zb + zh) / 2), (px, yc + 0.075, (zb + zh) / 2), pw, round(zh - zb, 4))]
    pe['geom']['parts'][i:i + 1] = new
    pe['qty']['area'] = round(pe['qty']['area'] - 0.15 * (zt - zh), 3)

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
    if e['category'] in _EXT_SKIP or (e['id'].startswith('SC-') and not e['id'].startswith('SC-EP-')) or e['id'].endswith('-DW'):
        continue
    for p in (e['geom']['parts'] if e['geom']['type'] == 'multi' else [e['geom']]):
        b = _aabb(p)
        if b:
            # เพลทฝังผิวเสา (SC-EP) ไม่ฉาบ: นับเป็นผิวปิดแล้ว (เหมือนงานฉาบ) ไม่เติมฉาบทับ
            if e['id'].startswith('SC-EP-'):
                b = [b[0] - 0.002, b[1] + 0.002, b[2] - 0.002, b[3] + 0.002, b[4], b[5]]
            _ext_boxes.append((b, 'งานฉาบ' if e['id'].startswith('SC-EP-') else e['category']))
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

# ---------- คานรับชานพักบันไดหนีไฟ แนว C/10–C/11 และ D/10–D/11 ชั้น 2–5 (ผู้ใช้สั่ง 11 พ.ย. 2569) ----------
# เหล็ก H200x100x7x11 (อ่านจาก "H100X2007*11" ที่ผู้ใช้ให้) ขึ้นด้วย Profile Builder, หลังคานต่ำกว่าระดับพื้นโถงทางเดิน 0.10 (FL - 0.10)
# ปลายกริด 10: แนว C ชนหน้าเพลทฝัง SC-EP-10C (ผิวคอนกรีตเสา), แนว D ชนผิวฉาบเสา D/10 (ยังไม่มีเพลทฝัง); ปลายกริด 11: ชนผิวปีกเสา SC-11C/D
LB_D, LB_B, LB_TW, LB_TF = 0.200, 0.100, 0.007, 0.011
_a, _b, _w, _t = LB_D / 2, LB_B / 2, LB_TW / 2, LB_D / 2 - LB_TF
LB_POLY = [(-_b, -_a), (_b, -_a), (_b, -_t), (_w, -_t), (_w, _t), (_b, _t), (_b, _a), (-_b, _a), (-_b, _t), (-_w, _t), (-_w, -_t), (-_b, -_t)]
for r in ('C', 'D'):
    x0 = _xf if r == 'C' else _xf + PL_COL
    x1 = GX11 - SC_D / 2
    for f in (2, 3, 4, 5):
        zc = FL[f] - 0.10 - LB_D / 2
        g = member((x0, GY[r], zc), (x1, GY[r], zc), LB_B, LB_D)
        g['shape'] = 'POLY'; g['poly2d'] = [[round(a, 5), round(b, 5)] for a, b in LB_POLY]
        add(f'SC-LB-{r}-F{f}', 'คาน', f, 'DONE', g,
            name=f'คานเหล็กรับชานพักบันไดหนีไฟ H200x100x7x11 แนว {r}/10–{r}/11 ชั้น {f}', assumed=True,
            qty=dict(length=round(x1 - x0, 3), section='H200x100x7x11', weight_kg=round((x1 - x0) * (2 * LB_B * LB_TF + (LB_D - 2 * LB_TF) * LB_TW) * 7850, 2)))
        elements[-1]['material'] = 'BIM-เหล็กโครงสร้าง'

# ---------- บันไดเหล็กหนีไฟ (ผู้ใช้สั่ง 11 พ.ย. 2569) ----------
# บันไดพับกลับ 2 ช่วงต่อชั้น ระหว่างชานพักชั้น (แนว C–D บนคาน SC-LB) กับชานพักกลาง (ติดแนวเสา 10/M, 11/M)
# แม่บันไดเหล็กรางน้ำ C200x100 (tw 7.5, tf 11 มม. ผมสมมติ) หันหน้าเรียบเข้าหาขั้น ขั้นเหล็กลาย 4 มม. พับรูป Z เชื่อมชนหน้าเรียบ
# ผิวชานพัก = เหล็กลาย 4 มม. บนโครงที่หลังคาน FL-0.10 (ผู้ใช้เลือก) => ระดับเหยียบ FL-0.096
# โครงชานพัก: กระทงหลักเหล็กกล่อง 125x75x3.2 ซอยด้วย 100x50x3.2 @0.40 (ผู้ใช้กำหนด)
ST_T = 0.004
SG_H, SG_B, SG_TW, SG_TF = 0.200, 0.100, 0.0075, 0.011
FS_X0, FS_X1 = _xf + 0.025, GX11 - SC_D / 2                        # ปลายปีกแม่บันไดฝั่งอาคาร (ห่างผิวฉาบ 10 มม.) / ผิวปีกเสากริด 11 ด้านใน
# แม่บันไดหันหน้าเรียบ (หลังเอว) เข้าหาขั้น ปีกออกนอก (ผู้ใช้สั่ง 11 พ.ย. 2569): ตัวนอกหน้าเรียบเสมอผิวปีกเสากริด 11 ด้านใน
# ปลายชนขอบปีกเสา; ฝั่งอาคารปลายปีกห่างผิวฉาบ 10 มม.; 2 ตัวกลางชนปลายปีกกันเป็นชิ้นเดียว (ผู้ใช้เลือก)
_xm = (FS_X0 + SG_B + FS_X1) / 2                                    # แนวชนปลายปีกแม่บันไดตัวกลาง
LANE_IN, LANE_OUT = (FS_X0 + SG_B, _xm - SG_B), (_xm + SG_B, FS_X1)   # ช่วงระหว่างหน้าเรียบแม่บันได (ความยาวขั้น)
FS_YT = GY['C'] - 0.05                                              # ขอบชานพักชั้น (ผิวปีกคาน SC-LB แนว C)
FS_YL0 = FS_YM + SC_B / 2                                           # ขอบปีกเสา 10/M, 11/M (แม่บันไดขอบหลังชานพักกลางชนเสา)
FS_YC = GY['C'] - SC_B / 2                                          # ขอบปีกเสา C/11 (ปลายแม่บันไดตัวนอกชน)
# ลูกตั้ง 20 ซม. (16 ลูกต่อชั้น ช่วงละ 8) ลูกนอน 27.5 ซม. (ผู้ใช้สั่งลองออกแบบ 11 พ.ย. 2569)
EP_T = 0.010                                                        # แผ่นปิดปลายแม่บันได PL10 (ผมกำหนด)
FS_N = 16                                                           # ลูกตั้งต่อชั้น (2 ช่วง ช่วงละ 8)
FS_G = 0.275                                                        # ลูกนอน
FS_YL1 = FS_YL0 + 0.90                                              # ขอบหน้าชานพักครึ่งชั้น: ยาว 0.90 จากขอบปีกเสา (ผู้ใช้สั่ง 11 พ.ย. 2569, เดิม ~1.19)
FS_YS = FS_YL1 + (FS_N // 2 - 1) * FS_G                             # จมูกขั้นแรก/ลูกตั้งสุดท้ายฝั่งชานพักชั้น; ช่วง FS_YS..FS_YT เป็นแนวราบระดับชั้น
LT = {f: FL[f] - 0.10 + ST_T for f in FL}


def _box_poly(w, d, t):
    o = [(-w / 2, -d / 2), (w / 2, -d / 2), (w / 2, d / 2), (-w / 2, d / 2)]
    i = [(-w / 2 + t, -d / 2 + t), (w / 2 - t, -d / 2 + t), (w / 2 - t, d / 2 - t), (-w / 2 + t, d / 2 - t)]
    return [[round(a, 5), round(b, 5)] for a, b in o], [[round(a, 5), round(b, 5)] for a, b in i]


def _box(p0, p1, w, d, t=0.0032):
    g = member(p0, p1, w, d)
    g['shape'] = 'POLY'; g['poly2d'], g['hole2d'] = _box_poly(w, d, t)
    return g


def _chan_poly(k):
    h, b, tw, tf = SG_H / 2, SG_B, SG_TW, SG_TF
    p = [(0, -h), (b, -h), (b, -h + tf), (tw, -h + tf), (tw, h - tf), (b, h - tf), (b, h), (0, h)]
    return [[round(k * a, 5), round(c, 5)] for a, c in p]


def _steel_add(eid, cat, f, g, name, qty):
    add(eid, cat, f, 'DONE', g, name=name, assumed=True, qty=qty)
    elements[-1]['material'] = 'BIM-เหล็กโครงสร้าง'


def _miter(pa, ua, pb, ub):
    """ระนาบตัดต่อมุมระหว่างแกน a (ทิศ ua เข้ามุม) กับแกน b (ทิศ ub ออกจากมุม) ในระนาบ y-z"""
    # จุดตัดแกน: pa + t ua = pb + s ub (ใช้ y, z)
    det = ua[1] * (-ub[2]) - ua[2] * (-ub[1])
    t = ((pb[1] - pa[1]) * (-ub[2]) - (pb[2] - pa[2]) * (-ub[1])) / det
    p = tuple(c + t * d for c, d in zip(pa, ua))
    return cut(p, _unit(tuple(x + y for x, y in zip(ua, ub))))


def _chan(q0, q1, k, trim):
    g = member(q0, q1, SG_B, SG_H)
    g['shape'] = 'POLY'; g['poly2d'] = _chan_poly(k)
    g['trim'] = [list(trim[0]), list(trim[1])]
    return g


def _isect(l1, l2):
    """จุดตัดเส้น (p, u) สองเส้นในระนาบ y-z"""
    (p, u), (q, v) = l1, l2
    det = u[1] * (-v[2]) - u[2] * (-v[1])
    t = ((q[1] - p[1]) * (-v[2]) - (q[2] - p[2]) * (-v[1])) / det
    return tuple(c + t * d for c, d in zip(p, u))


def _chan_path(xf, dg, lines, c_start, c_end):
    """แม่บันไดต่อเนื่องหลายช่วง (ราบ/ลาด) ในระนาบ y-z ที่ x = xf (หน้าเรียบ) ปีกชี้ทาง x = dg
    lines: [(จุด, ทิศ)] เรียงตามทิศเดินของชิ้น; ต่อมุมด้วยระนาบแบ่งครึ่งมุม"""
    lines = [((xf, p[1], p[2]), u) for p, u in lines]
    pts, cuts = [], [c_start]
    p0, u0 = lines[0]
    pts.append(_on_plane(p0, tuple(a + b for a, b in zip(p0, u0)), c_start))
    for (p, u), (q, v) in zip(lines, lines[1:]):
        k = _isect((p, u), (q, v))
        pts.append(k); cuts.append(cut(k, _unit(tuple(a + b for a, b in zip(u, v)))))
    pn, un = lines[-1]
    pts.append(_on_plane(pn, tuple(a + b for a, b in zip(pn, un)), c_end)); cuts.append(c_end)
    parts = []
    for i, (p, u) in enumerate(lines):
        sx = 1 if u[1] > 0 else -1                                  # แกน a ของหน้าตัด (u x z) = +x เมื่อเดินทาง +y
        parts.append(_chan(pts[i], pts[i + 1], dg * sx, (cuts[i], cuts[i + 1])))
    return parts


for f in (1, 2, 3, 4):
    z0 = LT[f]
    R = (LT[f + 1] - z0) / FS_N
    zm = z0 + R * (FS_N // 2)
    z1 = LT[f + 1]
    L = math.hypot(FS_G, R); cth = FS_G / L
    off = 0.010 + SG_TF - SG_H / 2                                  # แกนแม่บันไดจากเส้นจมูกขั้น (ตั้งฉากแนวลาด)
    dz = (0.010 + SG_TF) / cth - SG_H / 2                           # แกนช่วงราบใต้ระดับเหยียบ (หลังเสมอแนวช่วงลาดที่มุม)
    zh = zm + dz
    zf0 = z0 + dz if f > 1 else SC_BASE + SG_H / 2                  # ชั้น 1: ช่วงราบนั่งบนหลังคาน GB1 (+0.20)
    zf1 = z1 + dz
    uA = (0.0, -FS_G / L, R / L); nA_ = (0.0, R / L, FS_G / L)
    uB = (0.0, FS_G / L, R / L); nB_ = (0.0, -R / L, FS_G / L)
    sA = ((0, FS_YS + nA_[1] * off, z0 + R + nA_[2] * off), uA)    # ช่วงลาด A (ขึ้นทาง -y) จมูกขั้นแรกที่ FS_YS
    sB = ((0, FS_YL1 + nB_[1] * off, zm + R + nB_[2] * off), uB)   # ช่วงลาด B (ขึ้นทาง +y) จมูกขั้นแรกที่ FS_YL1
    hF0m = ((0, 0, zf0), (0.0, -1.0, 0.0)); hF1p = ((0, 0, zf1), (0.0, 1.0, 0.0))
    hMm = ((0, 0, zh), (0.0, -1.0, 0.0)); hMp = ((0, 0, zh), (0.0, 1.0, 0.0))
    zhl = zm - ST_T - SG_H / 2                                      # ตัวกลาง: ช่วงราบใต้ชานพัก หลังเสมอใต้เหล็กลาย (ไม่โผล่เหนือผิวชานพัก)
    hLm = ((0, 0, zhl), (0.0, -1.0, 0.0)); hLp = ((0, 0, zhl), (0.0, 1.0, 0.0))
    xo, xb_ = LANE_OUT[1], LANE_IN[0]
    yL = FS_YL0 + SG_B
    pl_y = lambda y, n: cut((0, y, 0), (0, n, 0))
    # ตัวริม (ชิ้นเดียว): A ขวา [ราบระดับชั้น -> ลาด -> ราบชานพัก] ชนขอบปีกเสา C/11 และ 11/M, ขอบหลัง, ด้านอาคาร [ราบชานพัก -> ลาด -> ราบระดับชั้นบน]
    parts = _chan_path(xo, 1, [hF0m, sA, hMm], pl_y(FS_YC - (0.0125 if f == 1 else 0.0), 1), pl_y(FS_YL0, -1))
    parts.append(_chan((xo, yL, zh), (xb_, yL, zh), -1, (cut((xo, 0, 0), (1, 0, 0)), cut((xb_, 0, 0), (-1, 0, 0)))))
    parts += _chan_path(xb_, -1, [hMp, sB, hF1p], pl_y(FS_YL0, -1), pl_y(FS_YT, 1))
    Lt = sum(mlen(p['p0'], p['p1']) for p in parts)
    _steel_add(f'FS-SG-F{f}-U', 'บันได', f, dict(type='multi', parts=parts),
               f'แม่บันไดหนีไฟตัวริม เหล็กรางน้ำ C200x100x7.5x11 ชั้น {f}→{f+1} ต่อเนื่องรอบชานพักครึ่งชั้น ปลายเป็นช่วงราบ เชื่อมเป็นชิ้นเดียว',
               dict(length=round(Lt, 3), section='C200x100x7.5x11', weight_kg=round(Lt * 27.7, 1)))
    # ตัวกลาง (ชิ้นเดียว ชนปลายปีกกัน): A ซ้าย [ราบระดับชั้น -> ลาด -> ราบใต้ชานพัก]; B ขวา [ราบใต้ชานพัก -> ลาด -> ราบระดับชั้นบน]
    # ช่วงราบใต้ชานพักวิ่งลอดขอบหน้าชานพักไปชนหน้าแม่บันไดขอบหลัง (y = yL) รับเหล็กลายชานพักโดยตรง
    parts = _chan_path(LANE_OUT[0], -1, [hF0m, sA, hLm], pl_y(GY['C'] + 0.10 if f == 1 else FS_YT, 1), pl_y(yL, -1))
    pB = _chan_path(LANE_IN[1], 1, [sB, hF1p], pl_y(FS_YL1 + EP_T, -1), pl_y(FS_YT, 1))   # ช่วง B ปลายล่างตัดตั้งที่ขอบหน้าชานพัก (ผู้ใช้เลือก 11 พ.ย. 2569)
    parts += pB
    Lt = sum(mlen(p['p0'], p['p1']) for p in parts)
    _steel_add(f'FS-SG-F{f}-M', 'บันได', f, dict(type='multi', parts=parts),
               f'แม่บันไดหนีไฟตัวกลาง เหล็กรางน้ำ C200x100x7.5x11 ชั้น {f}→{f+1} 2 ช่วงชนปลายปีกกัน ปลายเป็นช่วงราบ เชื่อมเป็นชิ้นเดียว',
               dict(length=round(Lt, 3), section='C200x100x7.5x11', weight_kg=round(Lt * 27.7, 1)))
    # ขั้นเหล็กลาย 4 มม. พับ Z เชื่อมชนหน้าเรียบแม่บันได
    t = ST_T
    zp = [(0, -0.03), (t, -0.03), (t, -t), (FS_G, -t), (FS_G, 0.03), (FS_G - t, 0.03), (FS_G - t, 0), (0, 0)]
    for fl, lane, sgn, yb, zb in (('A', LANE_OUT, -1, FS_YS, z0), ('B', LANE_IN, 1, FS_YL1, zm)):
        xa, xb = lane
        if sgn > 0:
            xa, xb = xb, xa
        tp = []
        for k in range(1, FS_N // 2):
            yf, zt = yb + sgn * (k - 1) * FS_G, zb + k * R
            g = member((xa, yf, zt), (xb, yf, zt), abs(xb - xa), 0.06)
            g['shape'] = 'POLY'; g['poly2d'] = [[round(a, 5), round(c, 5)] for a, c in zp]
            tp.append(g)
        _steel_add(f'FS-TR-F{f}-{fl}', 'บันได', f, dict(type='multi', parts=tp),
                   f'ขั้นบันไดหนีไฟ เหล็กลาย 4 มม. พับ Z ชั้น {f}→{f+1} ช่วง {fl} {len(tp)} ขั้น (ลูกตั้ง {R*1000:.1f} ลูกนอน {FS_G*1000:.0f} มม.)',
                   dict(count=len(tp), riser=round(R, 4), going=round(FS_G, 4), width=round(abs(xb - xa), 3), thickness=ST_T))
    # ชานพักกลาง: เหล็กลายระหว่างหน้าเรียบแม่บันไดตัวริม บนโครงกล่อง (ขอบหน้า 125x75 ซอย 100x50 @0.40)
    zt = zm - ST_T
    X0, X1 = xb_, xo
    _steel_add(f'FS-ML-F{f}', 'บันได', f,
               prism([(X0, yL), (X1, yL), (X1, FS_YL1), (X0, FS_YL1)], zt, ST_T),
               f'ชานพักกลางบันไดหนีไฟ เหล็กลาย 4 มม. ชั้น {f}→{f+1}', dict(area=round((X1 - X0) * (FS_YL1 - yL), 3), thickness=ST_T))
    zc1, zc2 = zt - 0.0625, zt - 0.05
    fr = [_box((a, FS_YL1 - 0.0375, zc1), (b, FS_YL1 - 0.0375, zc1), 0.075, 0.125)
          for a, b in ((X0, LANE_IN[1] + SG_B), (LANE_OUT[0], X1))]  # ขอบหน้าแบ่ง 2 ท่อน ชนแม่บันไดตัวกลางช่วง A ที่ลอดใต้
    x = X0 + 0.40
    while x < X1 - 0.20:
        fr.append(_box((x, yL, zc2), (x, FS_YL1 - 0.075, zc2), 0.050, 0.100))
        x += 0.40
    _steel_add(f'FS-MLF-F{f}', 'บันได', f, dict(type='multi', parts=fr),
               f'โครงชานพักกลาง เหล็กกล่อง 125x75x3.2 ขอบหน้า (2 ท่อน ชนแม่บันไดตัวกลางช่วง A) ซอย 100x50x3.2 @0.40 ชั้น {f}→{f+1} (ขอบข้าง/หลังคือแม่บันได)', dict(pieces=len(fr)))
    # แผ่นปิดปลายแม่บันไดตัวกลางช่วง B: PL10 เต็มกว้างปีก เชื่อมปลายตัดตั้ง ลงมาเชื่อมหน้ากล่องขอบหน้าชานพักเต็มความสูงกล่อง
    q = pB[0]['p0']
    ztop = q[2] + SG_H / 2 / cth
    _steel_add(f'FS-SGP-F{f}', 'บันได', f,
               prism([(LANE_IN[1], FS_YL1), (LANE_IN[1] + SG_B, FS_YL1), (LANE_IN[1] + SG_B, FS_YL1 + EP_T), (LANE_IN[1], FS_YL1 + EP_T)], zc1 - 0.0625, ztop - (zc1 - 0.0625)),
               f'แผ่นปิดปลายแม่บันไดตัวกลางช่วง B PL{EP_T*1000:.0f} เชื่อมรับที่กล่องขอบหน้าชานพักกลาง ชั้น {f}→{f+1}',
               dict(width=SG_B, height=round(ztop - zc1 + 0.0625, 3), thickness=EP_T))
    # คานรับพื้นชานพักครึ่งชั้น แนวเสา 10/M–11/M (ห่างแนว C 3.25 ม.) H200x100x7x11 ขนาดเดียวกับคานรับชานพักชั้น (ผู้ใช้สั่ง 11 พ.ย. 2569)
    # หลังคานเสมอใต้เหล็กลาย (zm - 0.004) ปลายชนผิวปีกเสาด้านใน; ขอบปีกคานชนปลายปีกแม่บันไดขอบหลังชานพัก (เชื่อมรับ)
    bx0, bx1 = SC_X10M + SC_D / 2, GX11 - SC_D / 2
    by = FS_YL0 - LB_B / 2
    bz = zm - ST_T - LB_D / 2
    g = member((bx0, by, bz), (bx1, by, bz), LB_B, LB_D)
    g['shape'] = 'POLY'; g['poly2d'] = [[round(a, 5), round(c, 5)] for a, c in LB_POLY]
    _steel_add(f'SC-LB-M-F{f}', 'คาน', f, g,
               f'คานเหล็กรับพื้นชานพักครึ่งชั้น H200x100x7x11 แนวเสา 10/M–11/M ชั้น {f}→{f+1}',
               dict(length=round(bx1 - bx0, 3), section='H200x100x7x11', weight_kg=round((bx1 - bx0) * (2 * LB_B * LB_TF + (LB_D - 2 * LB_TF) * LB_TW) * 7850, 2)))

# ส่วนต่อชานพักชั้น (ช่วงราบปลายแม่บันได FS_YS..ขอบคาน SC-LB แนว C) เหล็กลายเชื่อมระหว่างหน้าเรียบแม่บันได (ผู้ใช้สั่ง 11 พ.ย. 2569)
# ชั้น 2–4 ทั้ง 2 ช่วง; ชั้น 5 เฉพาะช่วงขาขึ้นมาถึง (ช่วงใน) เพราะช่วงนอกไม่มีบันไดต่อขึ้น
for f in (2, 3, 4, 5):
    zt = FL[f] - 0.10
    lanes = (LANE_IN, LANE_OUT) if f < 5 else (LANE_IN,)
    ps = [prism([(a, FS_YS), (b, FS_YS), (b, FS_YT), (a, FS_YT)], zt, ST_T) for a, b in lanes]
    _steel_add(f'FS-LDX-F{f}', 'บันได', f, ps[0] if len(ps) == 1 else dict(type='multi', parts=ps),
               f'ส่วนต่อชานพักชั้น {f} บันไดหนีไฟ เหล็กลาย 4 มม. (ช่วงราบปลายแม่บันได)', dict(area=round(sum((b - a) * (FS_YT - FS_YS) for a, b in lanes), 3), thickness=ST_T))
# ชานพักชั้น 2–5 แนว C–D: เหล็กลายบนโครงกล่องระหว่างคาน SC-LB
for f in (2, 3, 4, 5):
    zt = FL[f] - 0.10
    ya, yb = GY['C'] - 0.05, GY['D'] + 0.05
    _steel_add(f'FS-LD-F{f}', 'บันได', f,
               prism([(FS_X0, ya), (FS_X1, ya), (FS_X1, yb), (FS_X0, yb)], zt, ST_T),
               f'ชานพักชั้น {f} บันไดหนีไฟ เหล็กลาย 4 มม. แนว C–D', dict(area=round((FS_X1 - FS_X0) * (yb - ya), 3), thickness=ST_T))
    y0, y1 = GY['C'] + 0.05, GY['D'] - 0.05
    zc1, zc2 = zt - 0.0625, zt - 0.05
    fr = [_box((FS_X0 + 0.0375, y0, zc1), (FS_X0 + 0.0375, y1, zc1), 0.075, 0.125),
          _box((FS_X1 - 0.0375, y0, zc1), (FS_X1 - 0.0375, y1, zc1), 0.075, 0.125)]
    y = GY['C'] + 0.40
    while y < GY['D'] - 0.20:
        fr.append(_box((FS_X0 + 0.075, y, zc2), (FS_X1 - 0.075, y, zc2), 0.050, 0.100))
        y += 0.40
    _steel_add(f'FS-LDF-F{f}', 'บันได', f, dict(type='multi', parts=fr),
               f'โครงชานพักชั้น {f} เหล็กกล่อง 125x75x3.2 ซอย 100x50x3.2 @0.40', dict(pieces=len(fr)))
# ---------- ราวจับบันไดหนีไฟ (ผู้ใช้สั่ง 11 พ.ย. 2569) ----------
# ท่อเหล็กดำ หนา 2.3 มม. ทาสีน้ำเงิน ขึ้นด้วย Profile Builder: เสาและราวบนสุด 1.5" (OD 48.6), ราวกลาง 1" (OD 34.0)
# (ผมกำหนด) ราวบนสูง 0.90 จากแนวจมูกขั้น/ผิวชานพัก, ราวกลาง 2 เส้นที่ 0.30 และ 0.60, เสาตั้งบนปีกบนแม่บันได (ห่างผิวหลังเอว 30 มม.)
# ทุกด้านของแต่ละช่วงบันได และขอบเปิดของชานพัก; ระยะเสาไม่เกิน 1.20 ม.
P15, P10, PT = 0.0486, 0.0340, 0.0023


def _pipe_poly(od, t, n=24):
    r, ri = od / 2, od / 2 - t
    o = [[round(r * math.cos(2 * math.pi * k / n), 5), round(r * math.sin(2 * math.pi * k / n), 5)] for k in range(n)]
    i = [[round(ri * math.cos(2 * math.pi * k / n), 5), round(ri * math.sin(2 * math.pi * k / n), 5)] for k in range(n)]
    return o, i


def _pipe(p0, p1, od):
    g = member(p0, p1, od, od)
    g['shape'] = 'POLY'; g['poly2d'], g['hole2d'] = _pipe_poly(od, PT)
    return g


def _rail_set(eid, f, name, posts, top_of):
    """posts: [(x, y, z_base)], top_of(x, y) -> ระดับผิวอ้างอิง (จมูกขั้น/ผิวชานพัก) ณ ตำแหน่งนั้น"""
    parts, l15, l10 = [], 0.0, 0.0
    tops = [(x, y, top_of(x, y)) for x, y, _ in posts]
    for (x, y, zb), (_, _, zr) in zip(posts, tops):
        parts.append(_pipe((x, y, zb), (x, y, zr + 0.90), P15)); l15 += zr + 0.90 - zb
    for h, od in ((0.90, P15), (0.60, P10), (0.30, P10)):
        for (xa, ya, za), (xb, yb, zb) in zip(tops, tops[1:]):
            d = math.hypot(xb - xa, yb - ya); ux, uy = (xb - xa) / d, (yb - ya) / d
            e0 = P15 / 2 if h < 0.90 else 0.0                       # ราวกลางชนผิวเสา, ราวบนต่อเนื่องผ่านหัวเสา
            sl = (zb - za) / d
            q0 = (xa + ux * e0, ya + uy * e0, za + h + sl * e0)
            q1 = (xb - ux * e0, yb - uy * e0, zb + h - sl * e0)
            parts.append(_pipe(q0, q1, od))
            if od == P15:
                l15 += mlen(q0, q1)
            else:
                l10 += mlen(q0, q1)
    add(eid, 'ราวบันได', f, 'DONE', dict(type='multi', parts=parts), name=name, assumed=True,
        qty={'pipe_1.5in_m': round(l15, 3), 'pipe_1in_m': round(l10, 3), 'posts': len(posts), 'spec': 'ท่อเหล็กดำหนา 2.3 มม. ทาสีน้ำเงิน'})
    elements[-1]['material'] = 'BIM-เหล็กโครงสร้าง'


def _spaced(a, b, maxs=1.20):
    n = max(1, math.ceil(abs(b - a) / maxs - 1e-9))
    return [a + (b - a) * k / n for k in range(n + 1)]


_FL_TOP = 0.010 + SG_TF                                            # ปีกบนแม่บันไดเหนือแนวจมูกขั้น (ตั้งฉากแนวลาด)
for f in (1, 2, 3, 4):
    z0 = LT[f]; R = (LT[f + 1] - z0) / FS_N; zm = z0 + R * (FS_N // 2)
    cth = FS_G / math.hypot(FS_G, R)
    for fl, lane, sgn, yb, zb, ye in (('A', LANE_OUT, -1, FS_YT, z0, FS_YL1), ('B', LANE_IN, 1, FS_YL1, zm, FS_YT)):
        y1st = FS_YS if fl == 'A' else FS_YL1                       # จมูกขั้นแรกของช่วง
        lo, hi = (z0, zm) if fl == 'A' else (zm, LT[f + 1])
        nose = lambda x, y, y1st=y1st, zb=zb, sgn=sgn, R=R, lo=lo, hi=hi: min(hi, max(lo, zb + R + sgn * (y - y1st) * R / FS_G))
        for side, xw, dirx in (('L', lane[0], 1), ('R', lane[1], -1)):
            if fl == 'A' and side == 'R':
                continue                                            # ราวด้านกริด 11 รวมกับราวชานพักกลางเป็นชุดเดียว (ด้านล่าง)
            xp = xw - dirx * SG_B / 2                               # เสาตั้งกลางปีกบนแม่บันได (ปีกออกนอก)
            ys = _spaced(yb + sgn * 0.08, ye - sgn * 0.08)
            posts = [(xp, y, nose(xp, y) + _FL_TOP / cth) for y in ys]
            _rail_set(f'FS-HR-F{f}-{fl}-{side}', f, f'ราวจับบันไดหนีไฟ ชั้น {f}→{f+1} ช่วง {fl} ด้าน{"ซ้าย" if side == "L" else "ขวา"} ท่อเหล็กดำ 1.5"/1"', posts, nose)
    # ชานพักกลาง: ขอบหลัง (แนวเสา M, ระหว่างเสา 10/M กับขอบนอก) และขอบนอกด้านกริด 11
    # ราวด้านนอกชุดเดียวต่อเนื่องจากเสา C/11 -> ช่วงบันได A -> ขอบชานพักกลางด้านกริด 11 -> ขอบหลัง ถึงเสา 10/M (ผู้ใช้สั่ง 11 พ.ย. 2569)
    # เสาตั้งกลางปีกบนแม่บันได; เสาที่ขอบชานพัก (y = FS_YL1) ใช้ร่วมกัน ราวบนต่อระดับพอดี (แนวจมูกขั้น = ผิวชานพักที่ขอบ)
    xi, yi = FS_X1 + SG_B / 2, FS_YL0 + SG_B / 2
    nA = lambda x, y, z0=z0, R=R, zm=zm: min(zm, max(z0, z0 + R + (FS_YS - y) * R / FS_G))   # ราบระดับชั้น -> ลาด A -> ราบชานพัก
    pts = [(xi, y) for y in _spaced(FS_YT - 0.08, FS_YL1)] + [(xi, y) for y in _spaced(FS_YL1, yi)][1:] + [(x, yi) for x in _spaced(xi, FS_X0 + SG_B / 2)][1:]
    _rail_set(f'FS-HR-F{f}-O', f, f'ราวจับบันไดหนีไฟด้านนอก ชั้น {f}→{f+1} ชุดเดียวจากเสา C/11 ผ่านชานพักครึ่งชั้นถึงเสา 10/M ท่อเหล็กดำ 1.5"/1"',
              [(x, y, nA(x, y) + (0.010 + SG_TF) / cth) for x, y in pts], nA)
for f in (2, 3, 4, 5):
    zl = LT[f]
    xi = FS_X1 - 0.03
    y0, y1 = GY['C'] + SC_B / 2 + 0.03, GY['D'] + 0.05 - 0.03
    pts = [(xi, y) for y in _spaced(y0, y1)] + [(x, y1) for x in _spaced(xi, FS_X0 + 0.03)][1:]
    if f == 5:                                                      # ชั้นบนสุด: ขอบด้านแนว C เหนือช่วงบันไดขาขึ้น (ไม่มีช่วงต่อขึ้น)
        yc = GY['C'] - 0.05 + 0.03
        pts = [(x, yc) for x in _spaced(_xm + 0.03, xi)] + [(xi, y) for y in _spaced(yc, y1)][1:] + [(x, y1) for x in _spaced(xi, FS_X0 + 0.03)][1:]
    _rail_set(f'FS-HR-LD-F{f}', f, f'ราวกันตกชานพักชั้น {f} บันไดหนีไฟ ท่อเหล็กดำ 1.5"/1"', [(x, y, zl) for x, y in pts], lambda x, y, zl=zl: zl)
ASSUMPTIONS.append('ราวบันไดหนีไฟ: สูง 0.90 ราวกลาง 0.30/0.60 เสาห่างไม่เกิน 1.20 ม. (ผมกำหนด); ท่อเหล็กดำหนา 2.3 มม. เสา/ราวบน 1.5" อื่นๆ 1" (ผู้ใช้กำหนด)')

# เหล็กลาย (ขั้นบันได, ผิวชานพัก) ใช้วัสดุเหล็กลายจากคลังวัสดุ SketchUp (Patterns/Checker Plate) (ผู้ใช้สั่ง 11 พ.ย. 2569)
for e in elements:
    if re.match(r'^FS-(TR|ML|LD|LDX)-', e['id']):
        e['material'] = '[Checker Plate]'
ASSUMPTIONS.append('บันไดหนีไฟ: แม่บันได C200x100 ใช้ tw 7.5 tf 11 มม. (ผู้ใช้ไม่ระบุความหนา); 16 ลูกตั้งต่อชั้น (20 ซม.) ลูกนอน 27.5 ซม.; ผิวชานพักเหล็กลาย FL-0.096')

# ช่องชาร์ฟห้องน้ำ: ตัดฉาบผิวเสา ข้างคาน และท้องคานส่วนที่อยู่ภายในช่องชาร์ฟออก ผิวในช่องไม่ฉาบ (ผู้ใช้สั่ง 12 พ.ย. 2569)
def _shaft_boxes():
    out = []
    for f in (2, 3, 4, 5):
        zs = FL[f] - DROP
        zt = (FL[f + 1] - DROP - S1_T) if f < 5 else beam_soffit(f, 'edge', True)
        for side in ('N', 'S'):
            for i in range(9):
                if side == 'N' and i == STAIR_BAY[0]:
                    continue
                g = wc_geo(i, side, f)
                xa, xb = sorted((g['xg'], g['xg'] + g['dr'] * (SH_W - WALL_T)))
                ya, yb = sorted((g['yr'], g['yr'] - g['s'] * (SH_D - WALL_T)))
                out.append((f'F{f}-{side}{i+1}', xa, xb, ya, yb, zs, zt))
    return out


def _iv_minus(a0, a1, b0, b1):
    """ช่วง [a0,a1] ลบช่วง [b0,b1]"""
    r = []
    if b0 > a0 + 1e-6:
        r.append((a0, min(a1, b0)))
    if b1 < a1 - 1e-6:
        r.append((max(a0, b1), a1))
    return [q for q in r if q[1] - q[0] > 1e-6]


def _rect_minus_boxes(r, boxes):
    """สี่เหลี่ยม r (x0,x1,y0,y1) ลบกล่อง boxes [(x0,x1,y0,y1)] คืนรายการรูปปิดทวนเข็ม (แตกเป็นช่องตาราง แล้วไล่ขอบรวม)"""
    X = sorted({r[0], r[1], *[min(max(v, r[0]), r[1]) for b in boxes for v in b[:2]]})
    Y = sorted({r[2], r[3], *[min(max(v, r[2]), r[3]) for b in boxes for v in b[2:4]]})
    keep = set()
    for i in range(len(X) - 1):
        for j in range(len(Y) - 1):
            cx, cy = (X[i] + X[i + 1]) / 2, (Y[j] + Y[j + 1]) / 2
            if not any(b[0] < cx < b[1] and b[2] < cy < b[3] for b in boxes):
                keep.add((i, j))
    edges = {}                                       # ขอบทวนเข็มของแต่ละช่อง ตัดขอบที่ใช้ร่วมกันออก
    for i, j in keep:
        for p, q in (((i, j), (i + 1, j)), ((i + 1, j), (i + 1, j + 1)), ((i + 1, j + 1), (i, j + 1)), ((i, j + 1), (i, j))):
            if (q, p) in edges:
                del edges[(q, p)]
            else:
                edges[(p, q)] = True
    nxt = {}
    for p, q in edges:
        nxt.setdefault(p, []).append(q)
    loops = []
    while nxt:
        s = next(iter(nxt)); loop = [s]; p = s
        while True:
            q = nxt[p].pop()
            if not nxt[p]:
                del nxt[p]
            if q == s:
                break
            loop.append(q); p = q
        pts = [(X[i], Y[j]) for i, j in loop]
        pts = [pts[k] for k in range(len(pts))                      # ตัดจุดกลางแนวตรง
               if not ((pts[k - 1][0] == pts[k][0] == pts[(k + 1) % len(pts)][0]) or (pts[k - 1][1] == pts[k][1] == pts[(k + 1) % len(pts)][1]))]
        loops.append(pts)
    return loops


def _cut_plaster_boxes(e, boxes):
    """ตัดชิ้นฉาบของ e ส่วนที่อยู่ในกล่อง boxes [(tag,x0,x1,y0,y1,z0,z1)] คืน (พื้นที่ฉาบที่ตัดออก ม.2, tags ที่ตัด)"""
    g = e['geom']
    parts = g['parts'] if g['type'] == 'multi' else [g]
    removed, tags = 0.0, set()
    for box in boxes:                                # คาน: ชิ้นฉาบเป็น member ตัดทีละกล่อง (ชิ้นที่เหลือยังเป็น member)
        _, X0, X1, Y0, Y1, Z0, Z1 = box
        new = []
        for p in parts:
            if p['type'] == 'member' and not p.get('shape') and not p.get('trim'):
                a, b = p['p0'], p['p1']
                ax = 0 if abs(a[1] - b[1]) < 1e-6 and abs(a[2] - b[2]) < 1e-6 else (1 if abs(a[0] - b[0]) < 1e-6 and abs(a[2] - b[2]) < 1e-6 else None)
                if ax is not None:
                    cx = 1 - ax
                    L0, L1 = sorted((a[ax], b[ax]))
                    c, zc, w, d = a[cx], a[2], p['w'], p['d']
                    BL = (X0, X1) if ax == 0 else (Y0, Y1)
                    BC = (Y0, Y1) if ax == 0 else (X0, X1)
                    if L1 > BL[0] + 1e-6 and L0 < BL[1] - 1e-6 and c + w / 2 > BC[0] + 1e-6 and c - w / 2 < BC[1] - 1e-6 \
                            and zc + d / 2 > Z0 + 1e-6 and zc - d / 2 < Z1 - 1e-6:
                        tags.add(box[0])
                        def seg(l0, l1, cc, ww, p=p, a=a, ax=ax, cx=cx):
                            q0, q1 = list(a), list(a)
                            q0[ax], q1[ax] = round(l0, 4), round(l1, 4)
                            q0[cx] = q1[cx] = round(cc, 4)
                            return dict(p, p0=q0, p1=q1, w=round(ww, 4))
                        for l0, l1 in _iv_minus(L0, L1, *BL):
                            new.append(seg(l0, l1, c, w))
                        la, lb = max(L0, BL[0]), min(L1, BL[1])
                        keep = _iv_minus(c - w / 2, c + w / 2, *BC)
                        for c0, c1 in keep:
                            new.append(seg(la, lb, (c0 + c1) / 2, c1 - c0))
                        # ข้างคาน (แผ่นตั้ง) ตัดทั้งแผ่น; ท้องคาน (แผ่นนอน) ตัดเฉพาะความกว้างส่วนที่อยู่ในช่อง
                        removed += (lb - la) * (d if d > w else (w - sum(c1 - c0 for c0, c1 in keep)))
                        continue
            new.append(p)
        parts = new
    new = []
    for p in parts:                                  # เสา: ชิ้นฉาบเป็น prism สี่เหลี่ยม ตัดทุกกล่องพร้อมกัน แยกเป็นช่วงระดับ z
        if p['type'] == 'prism' and len(p['poly']) == 4 and not p.get('holes'):
            xs = [q[0] for q in p['poly']]; ys = [q[1] for q in p['poly']]
            r = (min(xs), max(xs), min(ys), max(ys))
            z0, z1 = p['z0'], p['z0'] + p['t']
            hb = [bx for bx in boxes if r[1] > bx[1] + 1e-6 and r[0] < bx[2] - 1e-6 and r[3] > bx[3] + 1e-6 and r[2] < bx[4] - 1e-6
                  and z1 > bx[5] + 1e-6 and z0 < bx[6] - 1e-6]
            if hb:
                zz = sorted({z0, z1, *[min(max(v, z0), z1) for bx in hb for v in bx[5:7]]})
                bands = []
                for za, zb in zip(zz, zz[1:]):
                    act = tuple(sorted(bx[1:5] for bx in hb if bx[5] < (za + zb) / 2 < bx[6]))
                    if bands and bands[-1][2] == act:
                        bands[-1][1] = zb
                    else:
                        bands.append([za, zb, act])
                for za, zb, act in bands:
                    if not act:
                        new.append(dict(p, z0=round(za, 4), t=round(zb - za, 4)))
                        continue
                    for poly in _rect_minus_boxes(r, act):
                        new.append(dict(type='prism', poly=[[round(x, 4), round(y, 4)] for x, y in poly], z0=round(za, 4), t=round(zb - za, 4)))
                    for bx in act:                   # ผิวฉาบรอบเสาส่วนที่อยู่ในช่อง (2 ด้านที่หันเข้าช่อง)
                        removed += ((min(r[1], bx[1]) - max(r[0], bx[0])) + (min(r[3], bx[3]) - max(r[2], bx[2]))) * (zb - za)
                tags.update(bx[0] for bx in hb)
                continue
        new.append(p)
    if tags:
        e['geom'] = new[0] if len(new) == 1 else dict(type='multi', parts=new)
    return removed, tags


_SHAFT_BOXES = _shaft_boxes()
for _e in elements:
    if _e['category'] != 'งานฉาบ' or not re.match(r'^PL-(C\d|B)', _e['id']):
        continue
    _rm, _tags = _cut_plaster_boxes(_e, _SHAFT_BOXES)
    if _tags:
        _e['qty']['area'] = round(max(0.0, _e['qty']['area'] - _rm), 3)
        _e['shaft_cut'] = sorted(_tags)
# ผนังห้องน้ำ (ผนังช่องชาร์ฟ SH1/SH2, ผนังนอก OWC, ผนัง B5 ช่วงต่อ WCX) พร้อมเสาเอ็น/คานเอ็น/ฉาบ: ตัดส่วนที่ชนคาน เสา พื้น ออก (ตรวจ 12 พ.ย. 2569)
# และตัดฉาบผนังห้อง/ผนังกริดช่วงที่ผนังช่องชาร์ฟก่อชนเข้าไป
def _bb3(p):
    if p['type'] == 'prism':
        xs = [q[0] for q in p['poly']]; ys = [q[1] for q in p['poly']]
        return (min(xs), min(ys), p['z0'], max(xs), max(ys), p['z0'] + p['t'])
    if p['type'] == 'member' and 'p0' in p and not p.get('shape') and not p.get('path'):
        a, b = p['p0'], p['p1']; w, d = p.get('w', 0), p.get('d', 0)
        if abs(a[1] - b[1]) < 1e-6 and abs(a[2] - b[2]) < 1e-6:
            return (min(a[0], b[0]), a[1] - w / 2, a[2] - d / 2, max(a[0], b[0]), a[1] + w / 2, a[2] + d / 2)
        if abs(a[0] - b[0]) < 1e-6 and abs(a[2] - b[2]) < 1e-6:
            return (a[0] - w / 2, min(a[1], b[1]), a[2] - d / 2, a[0] + w / 2, max(a[1], b[1]), a[2] + d / 2)
        if abs(a[0] - b[0]) < 1e-6 and abs(a[1] - b[1]) < 1e-6:
            return (a[0] - w / 2, a[1] - d / 2, min(a[2], b[2]), a[0] + w / 2, a[1] + d / 2, max(a[2], b[2]))
    return None


def _box3_minus(b, c):
    """กล่อง b ลบกล่อง c (x0,y0,z0,x1,y1,z1) คืนรายการกล่อง"""
    if not all(min(b[j + 3], c[j + 3]) - max(b[j], c[j]) > 1e-6 for j in range(3)):
        return [b]
    out, cur = [], list(b)
    for j in range(3):
        if c[j] > cur[j] + 1e-6:
            q = list(cur); q[j + 3] = c[j]; out.append(tuple(q)); cur[j] = c[j]
        if c[j + 3] < cur[j + 3] - 1e-6:
            q = list(cur); q[j] = c[j + 3]; out.append(tuple(q)); cur[j + 3] = c[j + 3]
    return out


def _vol(b):
    return (b[3] - b[0]) * (b[4] - b[1]) * (b[5] - b[2])


def _cut_elem_boxes(e, cut):
    """ตัดชิ้น prism สี่เหลี่ยมของ e ด้วยกล่อง cut คืนสัดส่วนปริมาตรที่เหลือ (None = ไม่ชน)"""
    g = e['geom']
    parts = g['parts'] if g['type'] == 'multi' else [g]
    new, v0, v1, hit = [], 0.0, 0.0, False
    for p in parts:
        b = _bb3(p) if p['type'] == 'prism' and len(p['poly']) == 4 else None
        if b is None:
            new.append(p); continue
        v0 += _vol(b)
        hs = [c for c in cut if all(min(b[j + 3], c[j + 3]) - max(b[j], c[j]) > 0.002 for j in range(3))]
        if not hs:
            new.append(p); v1 += _vol(b); continue
        hit = True
        pcs = [b]
        for c in hs:
            pcs = [r for q in pcs for r in _box3_minus(q, c)]
        for q in pcs:
            if min(q[3] - q[0], q[4] - q[1], q[5] - q[2]) < 1e-4:
                continue
            new.append(dict(type='prism', poly=[[round(q[0], 4), round(q[1], 4)], [round(q[3], 4), round(q[1], 4)], [round(q[3], 4), round(q[4], 4)], [round(q[0], 4), round(q[4], 4)]],
                            z0=round(q[2], 4), t=round(q[5] - q[2], 4)))
            v1 += _vol(q)
    if not hit:
        return None
    e['geom'] = new[0] if len(new) == 1 else dict(type='multi', parts=new)
    return v1 / v0 if v0 else 1.0


_STR_BOX = collections.defaultdict(list)                  # ชั้น -> กรอบคาน/เสา/พื้น
for _e in elements:
    if _e['category'] in ('คาน', 'เสา', 'พื้น', 'พื้นสำเร็จรูป', 'พื้นทับหน้า'):
        for _p in (_e['geom']['parts'] if _e['geom']['type'] == 'multi' else [_e['geom']]):
            _b = _bb3(_p)
            if _b:
                for _f in (_e['floor'] - 1, _e['floor'], _e['floor'] + 1):
                    _STR_BOX[_f].append(_b)
_WC_FIX = collections.Counter()
_SH_MAS = collections.defaultdict(list)
for _e in elements:
    _m = re.match(r'^W-F(\d)-[NS]\d-(SH1|SH2|OWC|WCX)(-PL|-TB\d+|-TC\d+)?$', _e['id'])
    if not _m:
        continue
    if _m.group(2) in ('SH1', 'SH2') and _m.group(3) in (None, '-TB1', '-TB2', '-TC1', '-TC2') and not (_m.group(3) or '').startswith('-PL'):
        _SH_MAS[_e['floor']] += [b for b in (_bb3(p) for p in (_e['geom']['parts'] if _e['geom']['type'] == 'multi' else [_e['geom']])) if b]
    _r = _cut_elem_boxes(_e, _STR_BOX[_e['floor']])
    if _r is not None:
        _q = _e['qty']
        for _k in ('area', 'concrete'):
            if _k in _q:
                _q[_k] = round(_q[_k] * _r, 4 if _k == 'concrete' else 3)
        if 'blocks' in _q:
            _q['blocks'] = round(_q['area'] * BLOCK_PER_M2)
        _WC_FIX[_m.group(2) + (_m.group(3) or '')] += 1
for _e in elements:                                          # ฉาบผนังห้อง/ผนังกริดช่วงหัวผนังช่องชาร์ฟ
    if _e['category'] == 'งานฉาบ' and re.match(r'^W-F\d-', _e['id']) and not re.match(r'^W-F\d-[NS]\d-SH\d-PL$', _e['id']):
        _r = _cut_elem_boxes(_e, _SH_MAS[_e['floor']])
        if _r is not None:
            _e['qty']['area'] = round(_e['qty']['area'] * _r, 3)
            _WC_FIX['wallPL:' + re.sub(r'F\d-|\d', '', _e['id'])] += 1
ASSUMPTIONS.append('ผนังห้องน้ำ/ช่องชาร์ฟ: ตัดผนังก่อ เสาเอ็น คานเอ็น และฉาบ ส่วนที่ชนคาน เสา พื้น ออก; ผนังช่องชาร์ฟก่อชนผิวบล็อกผนังห้องและผนังกริด; ฉาบด้านห้องน้ำปิดหัวผนังที่มุมช่องชาร์ฟต่อเนื่อง (12 พ.ย. 2569)')

ASSUMPTIONS.append('ช่องชาร์ฟห้องน้ำ: ไม่ฉาบผิวเสา ข้างคาน และท้องคานส่วนที่อยู่ภายในช่องชาร์ฟ (ผู้ใช้สั่ง 12 พ.ย. 2569)')

# ---- ห้องน้ำชั้น 1: งานฉาบไม่ซ้อนเนื้อผนังที่มาชน และฉาบปิดผิวก่อที่โผล่ (วงกบ หัวผนัง ปลายผนัง ท้องทับหลัง) (ผู้ใช้สั่ง 17 พ.ย. 2569) ----
_F1WC_RX = r'^W-F1-(WC|SH-G8)'
_F1Z = (GX[7] - 0.6, yB - 0.6, GX[9] + 0.6, yC + 0.6)


def _f1_base(i):
    return re.sub(r'-(PL|TB\d+|TC\d+)$', '', i)


def _box_mid(b):
    return [(b[k] + b[k + 3]) / 2 for k in range(3)]


_f1_els = [e for e in elements if re.match(_F1WC_RX, e['id']) and e['category'] in ('ผนัง', 'เสาเอ็นคานเอ็น', 'งานฉาบ')]
_f1_mas = [(_f1_base(e['id']), b) for e in _f1_els if e['category'] != 'งานฉาบ'
           for p in (e['geom']['parts'] if e['geom']['type'] == 'multi' else [e['geom']]) for b in [_bb3(p)] if b]
# 1) ฉาบของผนังหนึ่งที่ทะลุเข้าเนื้อก่อของผนังที่มาชน: ตัดออก
_F1_FIX = collections.Counter()
for _e in [e for e in _f1_els if e['category'] == 'งานฉาบ']:
    _bs = _f1_base(_e['id'])
    _r = _cut_elem_boxes(_e, [b for k, b in _f1_mas if k != _bs])
    if _r is not None:
        _e['qty']['area'] = round(_e['qty']['area'] * _r, 3); _F1_FIX['cut_mas'] += 1
# 2) ฉาบสองผนังซ้อนกันที่มุม: ตัดจากชิ้นที่ส่วนซ้อนอยู่ปลายชิ้น (ผนังที่มาชน) ให้ฉาบผนังหลักต่อเนื่อง
_f1_pl = [e for e in _f1_els if e['category'] == 'งานฉาบ']
for _e in _f1_pl:
    _bs = _f1_base(_e['id'])
    _others = [b for o in _f1_pl if _f1_base(o['id']) != _bs for p in (o['geom']['parts'] if o['geom']['type'] == 'multi' else [o['geom']]) for b in [_bb3(p)] if b]
    _cuts = []
    for p in (_e['geom']['parts'] if _e['geom']['type'] == 'multi' else [_e['geom']]):
        b = _bb3(p)
        if not b:
            continue
        ax = 0 if b[3] - b[0] >= b[4] - b[1] else 1      # แกนยาวของชิ้นฉาบ
        for c in _others:
            if all(min(b[j + 3], c[j + 3]) - max(b[j], c[j]) > 0.001 for j in range(3)):
                lo, hi = max(b[ax], c[ax]), min(b[ax + 3], c[ax + 3])
                if lo <= b[ax] + 0.002 or hi >= b[ax + 3] - 0.002:   # ซ้อนที่ปลายชิ้น
                    cl = (c[ax + 3] - c[ax]) >= (b[ax + 3] - b[ax]) - 1e-6
                    if not cl:
                        _cuts.append(c)
    if _cuts:
        _r = _cut_elem_boxes(_e, _cuts)
        if _r is not None:
            _e['qty']['area'] = round(_e['qty']['area'] * _r, 3); _F1_FIX['cut_pl'] += 1
# 3) ผิวก่อที่ยังโผล่: เพิ่มฉาบ 1.5 ซม. ปิดผิว (ขยายเลยขอบเท่าความหนาฉาบให้ชนฉาบด้านข้าง) แล้วหักส่วนที่ชนของแข็งอื่น
_f1_sol = []
for _e in elements:
    if _e['category'] in ('ไฟฟ้า', 'สุขาภิบาล', 'ประตูหน้าต่าง'):
        continue
    for p in (_e['geom']['parts'] if _e['geom']['type'] == 'multi' else [_e['geom']]):
        b = _bb3(p)
        if b and b[0] < _F1Z[2] and b[3] > _F1Z[0] and b[1] < _F1Z[3] and b[4] > _F1Z[1] and b[2] < 4.0 and b[5] > 0.0:
            _f1_sol.append(b)


def _f1_in(pt):
    return any(all(b[k] - 1e-4 <= pt[k] <= b[k + 3] + 1e-4 for k in range(3)) for b in _f1_sol)


_f1_pl_by = {e['id']: e for e in _f1_pl}
for _e in [e for e in _f1_els if e['category'] != 'งานฉาบ']:
    _pe = _f1_pl_by.get(_f1_base(_e['id']) + '-PL')
    if _pe is None:
        continue
    for p in (_e['geom']['parts'] if _e['geom']['type'] == 'multi' else [_e['geom']]):
        b = _bb3(p)
        if not b:
            continue
        for ax in (0, 1, 2):
            for sg in (0, 1):
                if ax == 2 and sg == 0 and b[2] <= FL[1] + 0.05:
                    continue
                v = b[ax + 3 * sg] + (0.003 if sg else -0.003)
                o = [k for k in (0, 1, 2) if k != ax]
                bad = 0
                for s in range(1, 6):
                    for t in range(1, 6):
                        pt = [0.0, 0.0, 0.0]; pt[ax] = v
                        pt[o[0]] = b[o[0]] + (b[o[0] + 3] - b[o[0]]) * s / 6
                        pt[o[1]] = b[o[1]] + (b[o[1] + 3] - b[o[1]]) * t / 6
                        bad += not _f1_in(pt)
                if not bad:
                    continue
                nb = list(b)
                if sg:
                    nb[ax], nb[ax + 3] = b[ax + 3], b[ax + 3] + PL_T
                else:
                    nb[ax], nb[ax + 3] = b[ax] - PL_T, b[ax]
                for k in o:
                    nb[k] -= PL_T; nb[k + 3] += PL_T
                nb[2] = max(nb[2], FL[1])
                pcs = [tuple(nb)]
                for c in _f1_sol:
                    pcs = [r for q in pcs for r in _box3_minus(q, c)]
                pcs = [q for q in pcs if min(q[3] - q[0], q[4] - q[1], q[5] - q[2]) > 0.002]
                if not pcs:
                    continue
                g = _pe['geom']
                if g['type'] != 'multi':
                    _pe['geom'] = g = dict(type='multi', parts=[g])
                for q in pcs:
                    g['parts'].append(dict(type='prism', poly=[[round(q[0], 4), round(q[1], 4)], [round(q[3], 4), round(q[1], 4)], [round(q[3], 4), round(q[4], 4)], [round(q[0], 4), round(q[4], 4)]],
                                           z0=round(q[2], 4), t=round(q[5] - q[2], 4)))
                    _f1_sol.append(q)
                    ar = sorted([q[3] - q[0], q[4] - q[1], q[5] - q[2]])
                    _pe['qty']['area'] = round(_pe['qty']['area'] + ar[1] * ar[2], 3)
                _F1_FIX['add_face'] += 1
ASSUMPTIONS.append('ห้องน้ำชั้น 1: ตัดฉาบที่ซ้อนเข้าเนื้อผนังที่มาชน ฉาบผนังหลักวิ่งต่อเนื่องที่มุม; ฉาบปิดวงกบประตู/ช่องเปิด ปลายผนัง และหัวผนังกั้นห้องส้วม หนา 1.5 ซม. (17 พ.ย. 2569)')

# ---- สุขภัณฑ์จากไฟล์ตัวอย่าง แทนกล่องตัวแทน (ผู้ใช้สั่ง 17 พ.ย. 2569) ----
# ไฟล์ใน O:\\My Drive\\Work2027\\CSR-หนองแค\\แบบสำหรับขึ้นโมเดล: ชักโครกจาก "สำหรับอ่านข้อมูลสร้างชิ้นงาน...ระบบท่อและสุขาภิบาล.skp",
# อ่างล้างหน้าตั้งพื้นพร้อมก๊อกจาก "HAND WASH BASIN.skp", โถปัสสาวะตั้งพื้นพร้อมแผงกั้นจาก "URINE-โถปัสสาวะ.skp"
FIX_DEFS = {'โถส้วม': ('สุขภัณฑ์ ชักโครก (ไฟล์ตัวอย่าง)', 'xmin'),
            'อ่างล้างหน้า': ('สุขภัณฑ์ อ่างล้างหน้าตั้งพื้น+ก๊อก (ไฟล์ตัวอย่าง)', 'xmin'),
            'โถปัสสาวะ': ('สุขภัณฑ์ โถปัสสาวะ+แผงกั้น (ไฟล์ตัวอย่าง)', 'ymin')}
_fx_wall = collections.defaultdict(list)
for _e in elements:
    if _e['category'] in ('ผนัง', 'งานฉาบ', 'เสา', 'เสาเอ็นคานเอ็น'):
        for p in (_e['geom']['parts'] if _e['geom']['type'] == 'multi' else [_e['geom']]):
            b = _bb3(p)
            if b:
                _fx_wall[_e['floor']].append(b)
_FX_N = collections.Counter()
for _e in elements:
    if _e['category'] != 'สุขภัณฑ์' or _e['geom']['type'] != 'prism':
        continue
    _k = next((k for k in FIX_DEFS if _e['name'].startswith(k)), None)
    if not _k:
        continue
    b = _bb3(_e['geom']); f = _e['floor']
    zf = FL[1] + 0.02 if f == 1 else FL[f] - DROP + 0.02          # ผิวกระเบื้องพื้นห้องน้ำ
    zm = b[2] + 0.05
    cands = []
    mid = [(b[0] + b[3]) / 2, (b[1] + b[4]) / 2]
    for ax in (0, 1):
        for sg in (0, 1):
            # ระยะจากผิวกล่องถึงผิวผนัง/ฉาบ/เสาที่ใกล้ที่สุดในทิศนั้น (ไม่เกิน 0.30) วางชิดผิวผนังจริง
            o = 1 - ax
            best = None
            for w in _fx_wall[f]:
                if not (w[o] - 1e-4 <= mid[o] <= w[o + 3] + 1e-4 and w[2] - 1e-4 <= zm <= w[5] + 1e-4):
                    continue
                dist = (w[ax] - b[ax + 3]) if sg else (b[ax] - w[ax + 3])
                if -0.006 <= dist <= 0.30 and (best is None or dist < best):
                    best = dist
            if best is not None:
                cands.append((ax, sg, b[ax + 3] + max(best, 0) if sg else b[ax] - max(best, 0), best))
    cands.sort(key=lambda c: c[3])
    if _k == 'โถส้วม':
        la = 0 if b[3] - b[0] >= b[4] - b[1] else 1
        cands = [c for c in cands if c[0] == la] or cands
    if not cands:
        _FX_N['no_wall'] += 1
        continue
    ax, sg, v, _dist = cands[0]
    pt = [(b[0] + b[3]) / 2, (b[1] + b[4]) / 2, zf]; pt[ax] = v
    d = [0, 0]; d[ax] = -1 if sg else 1
    _e['component_place'] = dict(def_=FIX_DEFS[_k][0], back=FIX_DEFS[_k][1], pt=[round(q, 4) for q in pt], dir=d)
    _e['component_place']['def'] = _e['component_place'].pop('def_')
    _FX_N[_k] += 1
ASSUMPTIONS.append('สุขภัณฑ์: ใช้คอมโพเนนต์จากไฟล์ตัวอย่างของผู้ใช้ (ชักโครก, อ่างล้างหน้าตั้งพื้นพร้อมก๊อก, โถปัสสาวะตั้งพื้นพร้อมแผงกั้น) วางชิดผนังด้านหลังกึ่งกลางกล่องเดิม ฐานที่ผิวกระเบื้อง; กล่องเดิมคงไว้เป็นข้อมูลปริมาณ (17 พ.ย. 2569)')

# ---- ระบบท่อน้ำเสียแนวดิ่งในช่องชาร์ฟห้องน้ำ (ผู้ใช้สั่ง 16 พ.ย. 2569) ----
# PVC ชั้น 8.5 ต่อช่องชาร์ฟ: ท่อส้วม 4" ท่อน้ำทิ้ง 3" ท่ออากาศ 2" (ผู้ใช้เลือก)
# ช่องเปิดพื้นห้องน้ำ 0.30x0.40 เว้นไว้ตอนเทพื้น ชิดข้างคานแนว B/E ทะลุตรงกันทุกชั้น (ผู้ใช้สั่ง); ด้าน 0.30 ชิดผิวในผนังชาร์ฟ SH1 (ผมกำหนด)
# ปลายล่างลงตามข้างเสาถึงระดับดิน 0.00 หยุดรอต่อถังบำบัด (ผู้ใช้: ถังกำลังออกแบบ); ปลายบนจบเหนือฝ้าชั้น 5 0.30 (ผู้ใช้: จบเหนือฝ้า, ระยะ 0.30 ผมกำหนด)
SAN_OPEN = (0.30, 0.40)
SAN_PIPES = [('VENT', 'ท่ออากาศ 2"', 0.060, 0.0023), ('WASTE', 'ท่อน้ำทิ้ง 3"', 0.089, 0.0032), ('SOIL', 'ท่อส้วม 4"', 0.114, 0.0041)]   # OD, ความหนา (ชั้น 8.5 ค่าประมาณ)
SAN_GAP, SAN_EDGE = 0.025, 0.03
SAN_Z0, SAN_Z1 = 0.0, FL[5] + CEIL5 + 0.30
# ตำแหน่งท่อดิ่งแบบใหม่ (ระยะจากผิวในผนังชาร์ฟ SH1 แนว x, จากผิวข้างคาน B/E แนว y) — ทำแนว N3 ก่อน ตรวจผ่านแล้วใช้กับแนวอื่น
SAN_NEWPOS = {('N', 2): {'SOIL': (0.235, 0.315), 'WASTE': (0.050, 0.325), 'VENT': (0.205, 0.090)}}   # เว้นช่อง 8 ซม. ระหว่างท่อน้ำทิ้งกับท่อส้วมให้ท่ออากาศใต้พื้นลอด


def _circ(r, n=24):
    return [[round(r * math.cos(2 * math.pi * k / n), 5), round(r * math.sin(2 * math.pi * k / n), 5)] for k in range(n)]


_SAN_OPEN_BOX = collections.defaultdict(list)              # ชั้น -> กล่องช่องเปิดพื้น
for side in ('N', 'S'):
    for i in range(9):
        if side == 'N' and i == STAIR_BAY[0]:
            continue
        g = wc_geo(i, side, 2)
        y_rm = GY['B'] if side == 'N' else GY['E']
        xi = g['xg'] + g['dr'] * (SH_W - WALL_T)           # ผิวในผนังชาร์ฟ SH1
        yf = y_rm - g['s'] * 0.125                         # ผิวข้างคานแนว B/E ด้านห้องน้ำ
        xa, xb = sorted((xi, xi - g['dr'] * SAN_OPEN[0]))
        ya, yb = sorted((yf, yf - g['s'] * SAN_OPEN[1]))
        for f in (2, 3, 4, 5):
            zt = FL[f] - DROP
            _SAN_OPEN_BOX[f].append((xa, ya, zt - S1_T - PL_T - 0.01, xb, yb, zt + 0.03))
        xc = xi - g['dr'] * SAN_OPEN[0] / 2
        off = SAN_EDGE
        for key, nm, od, t in SAN_PIPES:
            off += od / 2
            yc = yf - g['s'] * off
            off += od / 2 + SAN_GAP
            if True:                                         # จัดตำแหน่งใหม่ (ผู้ใช้สั่ง 23 พ.ย. 2569): ส้วมฝั่งชักโครก น้ำทิ้งฝั่งอ่าง อากาศฝั่งคาน B2; ทุกห้อง N+S (ผู้ใช้เลือก 24 พ.ย. 2569)
                _dx, _dy = SAN_NEWPOS[('N', 2)][key]
                xc, yc = xi - g['dr'] * _dx, yf - g['s'] * _dy
            L = SAN_Z1 - SAN_Z0
            m = member((xc, yc, SAN_Z0), (xc, yc, SAN_Z1), od, od)
            m.update(shape='POLY', poly2d=_circ(od / 2), hole2d=_circ(od / 2 - t))
            add(f'PB-{side}{i+1}-{key}', 'สุขาภิบาล', 2, 'A07', m,
                name=f'{nm} PVC ชั้น 8.5 แนวดิ่งในช่องชาร์ฟห้องน้ำ ห้อง {side}{i+1} ชั้น 2–5 (ดิน 0.00 ถึงเหนือฝ้าชั้น 5 0.30)', assumed=True,
                qty=dict(length=round(L, 3), size=nm, od_mm=round(od * 1000), sticks_4m=math.ceil(L / 4.0), coupling=math.ceil(L / 4.0) - 1, cls='8.5'))
# เจาะช่องพื้น S1 กระเบื้อง และฉาบใต้ท้องพื้นตามกล่องช่องเปิด
for _e in elements:
    _m = re.match(r'^(S1|TL)-F(\d)-[NS]\d-WC$', _e['id']) or re.match(r'^PL-CEIL-F(\d)$', _e['id'])
    if not _m:
        continue
    _f = int(_m.group(_m.lastindex))
    _r = _cut_elem_boxes(_e, _SAN_OPEN_BOX[_f])
    if _r is not None:
        _q = _e['qty']
        for _k in ('area', 'concrete'):
            if _k in _q:
                _q[_k] = round(_q[_k] * _r, 4 if _k == 'concrete' else 3)
ASSUMPTIONS.append('ท่อน้ำเสียแนวดิ่งในช่องชาร์ฟ: PVC ชั้น 8.5 ท่อส้วม 4" (OD 114) ท่อน้ำทิ้ง 3" (OD 89) ท่ออากาศ 2" (OD 60) เรียงในช่องเปิดพื้น 0.30x0.40 ชิดข้างคานแนว B/E ทุกชั้น; ปลายล่างระดับดิน 0.00 รอต่อถังบำบัด ปลายบนเหนือฝ้าชั้น 5 0.30; ความหนาท่อเป็นค่าประมาณ (16 พ.ย. 2569)')

# ---- ถังบำบัดน้ำเสียสำเร็จรูป (ผู้ใช้สั่ง 23 พ.ย. 2569) ----
# DOS COMPACT 3000 ลิตร สีเทา ST-01/GY-3000L (HomePro 1137962): กว้าง 182 ลึก 182 สูง 193 ซม. — รูปทรงกระบอกตั้ง (ผมสมมติ หน้าสินค้าไม่ระบุ)
# แนวศูนย์กลางถังห่างกริด A ออกนอกอาคาร 5.00 ม.; ถังในกลุ่มห่างกันศูนย์กลาง 2.30 ม. กึ่งกลางกลุ่มตามโซน (ผู้ใช้ยืนยัน); ฝาถังเสมอดิน ±0.00
SEP_D, SEP_H, SEP_Y = 1.82, 1.93, GY['A'] - 5.00
SEP_TANKS = [('Z1-1', 4.10, 'โซน 1 ห้อง N1–N3 ชั้น 2–5 (12 ห้อง)'), ('Z1-2', 6.40, 'โซน 1 ห้อง N1–N3 ชั้น 2–5 (12 ห้อง)'),
             ('Z2-1', 22.20, 'โซน 2 ห้อง N5–N9 ชั้น 2–5 (20 ห้อง)'), ('Z2-2', 24.50, 'โซน 2 ห้อง N5–N9 ชั้น 2–5 (20 ห้อง)'),
             ('Z2-3', 26.80, 'โซน 2 ห้อง N5–N9 ชั้น 2–5 (20 ห้อง)'), ('Z3-1', GX11, 'โซน 3 ห้องน้ำชาย-หญิง ชั้น 1')]
for _k, _x, _z in SEP_TANKS:
    m = member((_x, SEP_Y, -SEP_H), (_x, SEP_Y, 0.0), SEP_D, SEP_D)
    m.update(shape='POLY', poly2d=_circ(SEP_D / 2, 32))
    add(f'SEP-{_k}', 'สุขาภิบาล', 1, 'A07', m,
        name=f'ถังบำบัดน้ำเสีย DOS COMPACT 3000 ลิตร สีเทา (ST-01/GY-3000L) {_z}', assumed=True,
        qty=dict(type='ถังบำบัดน้ำเสียสำเร็จรูป', model='DOS COMPACT ST-01/GY-3000L', capacity_l=3000,
                 dia=SEP_D, height=SEP_H, weight_kg=123, top=0.0, bottom=-SEP_H))
    elements[-1]['material'] = 'BIM-ถังบำบัด DOS เทา'
ASSUMPTIONS.append('ถังบำบัดน้ำเสีย: DOS COMPACT 3000 ลิตร 6 ใบ (โซน 1: 2, โซน 2: 3, โซน 3: 1) ทรงกระบอกตั้ง ø1.82 สูง 1.93 ม. (ขนาดจาก HomePro, รูปทรงสมมติ) แนวศูนย์กลางห่างกริด A ออกนอกอาคาร 5.00 ม. ศูนย์กลางถังห่างกัน 2.30 ม. ฝาถังเสมอดิน ±0.00 (23 พ.ย. 2569)')

# ---- ท่อระบายน้ำเสียจากโคนท่อแนวดิ่ง → บ่อพัก → ถังบำบัด → ท่อทิ้งรอต่อบ่อพักโครงการ (ผู้ใช้ยืนยันแนวท่อ 23 พ.ย. 2569) ----
# ข้อต่อ/บ่อพักใช้คอมโพเนนต์จากไฟล์ตัวอย่าง (PVC-EB-45-*, PVC-YR-*, MH); ท่อ PVC ชั้น 8.5 สร้างเป็นชิ้นงานเอง
# คู่มือ DOS: ท่อเข้าถัง 1:50, ท่อออก 1:100, ท่อออกต่ำกว่าท่อเข้า ≥ 15 ซม.; ระยะ A (ท่อเข้าต่ำจากปากถัง) ไม่มีในคู่มือ → สมมติ 0.40 ม.
SD_OD = {50: 0.060, 80: 0.089, 100: 0.114, 150: 0.165, 200: 0.216}
SD_T = {50: 0.0023, 80: 0.0032, 100: 0.0041, 150: 0.0060, 200: 0.0078}      # ชั้น 8.5 ค่าประมาณ
SD_DEF = {('EB45', 80): ('PVC-EB-45-80', 0.021, 0.021), ('EB45', 100): ('PVC-EB-45-100', 0.025, 0.025), ('EB45', 150): ('PVC-EB-45-150', 0.038, 0.038)}
# วาย: (คอมโพเนนต์, ระยะก้นปากออก(+x), ระยะก้นปากเข้า(-x), ระยะก้นปากแยก(ทิศ -0.71,0.71))
SD_Y = {(100, 80): ('PVC-YR-100x80', 0.015, 0.114, 0.127), (150, 100): ('PVC-YR-150x100', 0.000, 0.160, 0.178)}
SD_A, SD_DROP_TANK, SD_COVER_Z = 0.40, 0.15, -0.45
SD_NECK = (0.60, 0.80)          # คอถัง: ช่องใน ø0.60 นอก ø0.80 (สมมติ)
_sd_n = collections.Counter()


def _v(a, b):
    return [b[i] - a[i] for i in range(3)]


def _unit(v):
    L = math.sqrt(sum(c * c for c in v))
    return [c / L for c in v]


def _pt(p, d, s):
    return [p[i] + d[i] * s for i in range(3)]


def _cross(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]


def _frame(X, P2, l2):
    """แกนคอมโพเนนต์: แกน x ท้องถิ่น = X (โลก), ทิศปากที่ 2 ท้องถิ่น l2 = (lx, ly) ชี้ไปทาง P2 (โลก)"""
    X = _unit(X)
    a = l2[0]
    Y = [(P2[i] - a * X[i]) for i in range(3)]
    d = sum(Y[i] * X[i] for i in range(3))
    Y = _unit([Y[i] - d * X[i] for i in range(3)])
    return X, Y


def sd_pipe(pref, p, q, size, nm, zone, solid=False):
    _sd_n[pref] += 1
    eid = f'{pref}-P{_sd_n[pref]:02d}'
    od = SD_OD[size]
    m = member(p, q, od, od)
    m.update(shape='POLY', poly2d=_circ(od / 2))
    if not solid:
        m['hole2d'] = _circ(od / 2 - SD_T[size])
    L = math.dist(p, q)
    add(eid, 'สุขาภิบาล', 1, 'A07', m, name=f'{nm} ø{size} PVC ชั้น 8.5 ({zone})', assumed=True,
        qty=dict(length=round(L, 3), size=f'ø{size}', od_mm=round(od * 1000), cls='8.5',
                 slope=round(abs(q[2] - p[2]) / max(math.hypot(q[0] - p[0], q[1] - p[1]), 1e-6), 4)))
    return eid


def sd_fit(pref, kind, dname, origin, X, Y, nm, zone, anchor='origin', size=None):
    _sd_n[pref + kind] += 1
    eid = f'{pref}-{kind}{_sd_n[pref + kind]:02d}'
    o = [round(c, 4) for c in origin]
    add(eid, 'สุขาภิบาล', 1, 'A07', member(o, [o[0], o[1], o[2] + 0.01], 0.05, 0.05),
        name=f'{nm} ({zone}) คอมโพเนนต์ไฟล์ตัวอย่าง {dname}', assumed=True, qty=dict(type=nm, model=dname, size=size))
    elements[-1]['fitting'] = dict(def_=dname, origin=o, x=[round(c, 5) for c in X], y=[round(c, 5) for c in Y], anchor=anchor)
    elements[-1]['fitting']['def'] = elements[-1]['fitting'].pop('def_')
    return eid


def sd_route(pref, pts, size, nm, zone, start_port=0.0, end_port=0.0):
    """เส้นท่อผ่านจุด pts: ข้องอ 45° ทุกจุดหักมุม (ท่อเริ่มที่ระยะ start_port จาก pts[0] ตามแนว, จบก่อน pts[-1] ระยะ end_port)"""
    dname, d1, d2 = SD_DEF[('EB45', size)]
    cur = _pt(pts[0], _unit(_v(pts[0], pts[1])), start_port)
    for i in range(1, len(pts) - 1):
        a = _unit(_v(pts[i - 1], pts[i])); b = _unit(_v(pts[i], pts[i + 1]))
        ang = math.degrees(math.acos(max(-1, min(1, sum(a[k] * b[k] for k in range(3))))))
        assert 30 < ang < 60, (pref, i, ang)
        X, Y = _frame([-c for c in a], b, (-0.7071, 0.7071))
        sd_fit(pref, 'EB', dname, pts[i], X, Y, f'ข้องอ 45° ø{size}', zone, size=f'ø{size}')
        sd_pipe(pref, cur, _pt(pts[i], a, -d1), size, nm, zone)
        cur = _pt(pts[i], b, d2)
    a = _unit(_v(pts[-2], pts[-1]))
    sd_pipe(pref, cur, _pt(pts[-1], a, -end_port), size, nm, zone)


def sd_y(pref, key, origin, flow, branch_from, zone):
    """วายลดที่ origin: ทางออกไปทิศ flow, ปากแยกชี้ไปทาง branch_from (ทิศจากวายไปหาท่อแยก) — คืนจุดก้นปาก (ออก, เข้า, แยก)"""
    dname, do, di, db = SD_Y[key]
    X, Y = _frame(flow, branch_from, (-0.7071, 0.7071))
    sd_fit(pref, 'Y', dname, origin, X, Y, f'วายลด {key[0]}x{key[1]}', zone, size=f'{key[0]}x{key[1]}')
    br = [-0.7071 * X[i] + 0.7071 * Y[i] for i in range(3)]
    return _pt(origin, X, do), _pt(origin, X, -di), _pt(origin, br, db)


def sd_cap(pref, p, d, size, zone):
    """ฝาปิดปลายท่อ/ช่องล้าง (ไฟล์ตัวอย่างไม่มีชิ้นนี้ — ทำขึ้นเอง)"""
    _sd_n[pref + 'CAP'] += 1
    od = SD_OD[size] + 0.012
    m = member(p, _pt(p, d, 0.03), od, od)
    m.update(shape='POLY', poly2d=_circ(od / 2))
    add(f'{pref}-CAP{_sd_n[pref + "CAP"]:02d}', 'สุขาภิบาล', 1, 'A07', m, name=f'ฝาปิดช่องล้าง/ปลายท่อ ø{size} ({zone}) ทำเอง ไม่มีในไฟล์ตัวอย่าง',
        assumed=True, qty=dict(type='ฝาปิดปลายท่อ (ปลั๊ก)', size=f'ø{size}'))


def sd_cleanout(pref, p_elbow, run_dir, size, zone, z_top=0.03):
    """ช่องล้างต้นสาย: ข้องอ 45° ที่ p_elbow ยกขึ้นถอยหลังทิศ run_dir ไปถึงระดับ z_top แล้วปิดฝา"""
    h = z_top - p_elbow[2]
    top = [p_elbow[0] - run_dir[0] * h, p_elbow[1] - run_dir[1] * h, z_top]
    return top


SD_HY = -0.60 + 0.0          # ท่อรวมใต้ระเบียง ห่างกริด A เข้าอาคาร 0.60 (ก่อนกลับแกน y = +0.60)
SD_HY = GY['A'] + 0.60
SD_MHY = SEP_Y + SEP_D / 2 + 1.00 + 0.40      # บ่อพัก 0.80x0.80 ห่างหน้าถัง 1.00
SD_MAINY = SEP_Y - SEP_D / 2 - 0.59           # ท่อทิ้งรวมหลังแนวถัง
_stk = {}
for _e in elements:
    _m = re.match(r'^PB-N(\d)-(SOIL|WASTE)$', _e['id'])
    if _m:
        _stk[(int(_m.group(1)), _m.group(2))] = _e


def sd_stack_base(pref, n, hx, z_h_of, zone):
    """โคนท่อแนวดิ่งห้อง N{n}: น้ำทิ้ง 3" เข้าท่อส้วม 4" ด้วยวายลด 100x80 (แนวดิ่ง), ท่อส้วมลงดินด้วยข้องอ 45° 2 ตัว
    แล้วเดินแนวทแยง 45° ในแปลนเข้าวายลด 150x100 บนท่อรวม — คืน (x วายบนท่อรวม, ฟังก์ชันสร้างท่อแยกเมื่อรู้ระดับ)"""
    es, ew = _stk[(n, 'SOIL')], _stk[(n, 'WASTE')]
    xs, ys = es['geom']['p0'][0], es['geom']['p0'][1]
    xw, yw = ew['geom']['p0'][0], ew['geom']['p0'][1]
    _hw = math.hypot(xw - xs, yw - ys)
    _ux, _uy = (xw - xs) / _hw, (yw - ys) / _hw     # ทิศในแปลนจากท่อส้วมไปท่อน้ำทิ้ง
    zY = -0.15
    up = [0, 0, 1]
    # วายลด 100x80 แนวดิ่ง: ทางออกลง (-z), ปากแยกชี้ขึ้นเฉียงไปทางท่อน้ำทิ้ง
    o_out, o_in, o_br = sd_y(pref, (100, 80), [xs, ys, zY], [0, 0, -1], [_ux * 0.7071, _uy * 0.7071, 0.7071], zone)
    brd = _unit(_v([xs, ys, zY], o_br))
    s = math.hypot(xw - o_br[0], yw - o_br[1]) / math.hypot(brd[0], brd[1])
    E = _pt(o_br, brd, s)
    X, Y = _frame(up, [-c for c in brd], (-0.7071, 0.7071))
    sd_fit(pref, 'EB', 'PVC-EB-45-80', E, X, Y, 'ข้องอ 45° ø80', zone, size='ø80')
    sd_pipe(pref, _pt(E, brd, -0.021), o_br, 80, 'ท่อน้ำทิ้ง', zone)
    # ตัดปลายล่างท่อแนวดิ่งให้จบที่ปากข้อต่อ
    for _e2, _zb in ((ew, E[2] + 0.021), (es, o_in[2])):
        _g = _e2['geom']
        _lo = 'p0' if _g['p0'][2] < _g['p1'][2] else 'p1'
        _g[_lo][2] = round(_zb, 4)
    for _e2 in (es, ew):
        g = _e2['geom']; L = abs(g['p0'][2] - g['p1'][2]); _e2['qty']['length'] = round(L, 3)
    # ข้องอ 45° 2 ตัว: ลงดิ่ง → เอียง 45° → แนวราบทิศ ds (ทแยงในแปลน)
    ds = [0.7071 * hx, -0.7071 if SD_HY < ys else 0.7071, 0]
    Lb = 0.12
    t = abs(ys - 0.5 * Lb - SD_HY) / 0.7071
    xY = xs + (0.5 * Lb + 0.7071 * t) * hx
    zYh = z_h_of(xY)
    zO2 = zYh + 0.02 * t
    O2 = [xs + 0.5 * Lb * hx, ys + 0.5 * Lb * ds[1] / 0.7071, zO2]
    O1 = [xs, ys, zO2 + 0.7071 * Lb]
    Yo = [xY, SD_HY, zYh]
    pts = [o_out, O1, O2, Yo]
    return dict(x=xY, pts=pts, ds=ds, Yo=Yo)


def sd_zone_header(pref, zone, hx, stacks, x_turn, x_mh_in, z0):
    """ท่อรวม ø150 ใต้ระเบียงทิศ hx → ข้องอ 45° 2 ตัวเลี้ยวออกนอกอาคาร → เข้าบ่อพักที่ x_mh_in; คืนระดับที่ผนังบ่อพัก"""
    xs_first = min(_stk[(n, 'SOIL')]['geom']['p0'][0] for n in stacks) if hx > 0 else max(_stk[(n, 'SOIL')]['geom']['p0'][0] for n in stacks)
    bases = {}
    # ตำแหน่งวายบนท่อรวม (ไม่ขึ้นกับระดับ)
    for n in stacks:
        xs = _stk[(n, 'SOIL')]['geom']['p0'][0]
        bases[n] = xs + (0.06 + 0.7071 * abs(_stk[(n, 'SOIL')]['geom']['p0'][1] - 0.06 - SD_HY) / 0.7071) * hx
    x_co = min(bases.values()) - 0.50 if hx > 0 else max(bases.values()) + 0.50
    zf = lambda x: z0 - 0.01 * abs(x - x_co)
    # ช่องล้างต้นสาย
    pco = [x_co, SD_HY, z0]
    top = sd_cleanout(pref, pco, [hx, 0, 0], 150, zone)
    seq = sorted(stacks, key=lambda n: bases[n] * hx)
    # จุดเลี้ยว
    p_t1 = [x_turn, SD_HY, zf(x_turn)]
    p_t2 = [x_mh_in, SD_HY - abs(x_mh_in - x_turn), zf(x_turn) - 0.01 * abs(x_mh_in - x_turn) * 1.4142]
    y_face = SD_MHY + 0.40 * (1 if SD_HY > SD_MHY else -1)
    L3 = abs(p_t2[1] - y_face)
    p_mh = [x_mh_in, y_face - 0.05 * (1 if SD_HY > SD_MHY else -1), p_t2[2] - 0.01 * L3]
    # ช่องล้าง: ท่อตั้งเอียง + ข้องอ
    dname, d1, d2 = SD_DEF[('EB45', 150)]
    dirup = _unit(_v(pco, top))
    X, Y = _frame(dirup, [hx, 0, 0], (-0.7071, 0.7071))
    sd_fit(pref, 'EB', dname, pco, X, Y, 'ข้องอ 45° ø150 (ช่องล้างต้นสาย)', zone, size='ø150')
    sd_pipe(pref, _pt(pco, dirup, d1), top, 150, 'ท่อช่องล้าง', zone)
    sd_cap(pref, top, dirup, 150, zone)
    cur = _pt(pco, [hx, 0, 0], d2)
    for n in seq:
        info = sd_stack_base(pref, n, hx, zf, zone)
        Yo = info['Yo']
        o_out, o_in, o_br = sd_y(pref, (150, 100), Yo, _unit([hx, 0, -0.01]), [-info['ds'][0], -info['ds'][1], 0.02], zone)
        sd_pipe(pref, cur, o_in, 150, 'ท่อรวม', zone)
        # ท่อแยกจากโคนท่อส้วม
        p = info['pts']
        sd_route(pref, [p[0], p[1], p[2], o_br], 100, 'ท่อส้วม+น้ำทิ้ง', zone, start_port=0.0, end_port=0.0)
        cur = o_out
    sd_route(pref, [cur, p_t1, p_t2, p_mh], 150, 'ท่อรวม', zone)
    return p_mh[2]


SD_MH = {}
SD_TANK_IN = {}


def sd_mh(pref, zone, x, z_in_min):
    o = [x, SD_MHY, -0.40]
    sd_fit(pref, 'MH', 'MH', o, [1, 0, 0], [0, 1, 0], 'บ่อพัก 0.80x0.80 ลึก 0.80', zone, anchor='center', size='0.80x0.80x0.80')
    SD_MH[pref] = (x, z_in_min - 0.05)
    return z_in_min - 0.05


def sd_mh_to_tank(pref, zone, xm, zm, xt):
    """ท่อ ø100 ลาด 1:50 จากบ่อพักเข้าถัง: ตรงถ้าอยู่แนวเดียวกัน ไม่งั้นออกด้านข้างบ่อ + ข้องอ 45° 2 ตัว"""
    sgn = 1 if SD_MHY > SEP_Y else -1
    y_face_t = SEP_Y + sgn * SEP_D / 2
    if abs(xt - xm) < 0.01:
        p0 = [xm, SD_MHY - sgn * 0.40, zm]
        p1 = [xt, y_face_t - sgn * 0.02, zm - 0.02 * abs(p0[1] - y_face_t)]
        sd_pipe(pref, p0, p1, 100, 'ท่อเข้าถัง', zone)
        return p1[2]
    sx = 1 if xt > xm else -1
    p0 = [xm + sx * 0.40, SD_MHY, zm]
    jog = 0.30
    pa = [xt - sx * jog, SD_MHY, None]
    pb = [xt, SD_MHY - sgn * jog, None]
    pc = [xt, y_face_t - sgn * 0.02, None]
    L = 0
    pts = [p0, pa, pb, pc]
    for i in range(1, 4):
        L += math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1])
        pts[i][2] = zm - 0.02 * L
    sd_route(pref, pts, 100, 'ท่อเข้าถัง', zone)
    return pc[2]


# ระดับเริ่มท่อรวม (กลางท่อ) −0.45: ดินกลบหลังท่อ ≥ 0.30
_z1w = sd_zone_header('SD-Z1W', 'โซน 1 ฝั่งกริด 1', +1, [1, 2], 4.75, 5.05, SD_COVER_Z)
_z1e = sd_zone_header('SD-Z1E', 'โซน 1 ฝั่งกริด 4', -1, [3], 5.75, 5.45, SD_COVER_Z)
_z2w = sd_zone_header('SD-Z2W', 'โซน 2 ฝั่งกริด 5', +1, [5, 6, 7], 24.00, 24.30, SD_COVER_Z)
_z2e = sd_zone_header('SD-Z2E', 'โซน 2 ฝั่งกริด 10', -1, [8, 9], 25.00, 24.70, SD_COVER_Z)
_zm1 = sd_mh('SD-Z1', 'โซน 1', 5.25, min(_z1w, _z1e))
_zm2 = sd_mh('SD-Z2', 'โซน 2', 24.50, min(_z2w, _z2e))
for _k, _xt, _z in SEP_TANKS:
    if _k.startswith('Z1'):
        SD_TANK_IN[_k] = sd_mh_to_tank('SD-Z1', 'โซน 1', 5.25, _zm1, _xt)
    elif _k.startswith('Z2'):
        SD_TANK_IN[_k] = sd_mh_to_tank('SD-Z2', 'โซน 2', 24.50, _zm2, _xt)

# โซน 3: ท่อรวม ø150 จากใต้พื้นห้องน้ำชั้น 1 → ท่อปลอก ø200 ผ่านคานคอดิน GB2-B9-10 → ลดระดับด้วยข้องอ 45° 2 ตัว → เข้าถังที่กริด 11 (ลาด 1:50)
_x3, _y3s, _z3s = 29.20, GY["B"] + 1.85, -0.05          # ใต้ทางเดินห้องน้ำหญิง ระหว่างอ่างล้างมือกับผนังห้องส้วม
_yb0, _yb1 = GY['B'] - 0.10, GY['B'] + 0.10          # ความกว้างคาน GB2 0.20 กลางแนว B
_co3 = [_x3, _y3s, _z3s]
_top3 = [_x3, _y3s + (0.33 - _z3s), FL[1] + 0.03 - 0.30 + 0.30]     # ช่องล้างโผล่ผิวพื้นชั้น 1
_top3 = [_x3, _y3s + (FL[1] - _z3s), FL[1]]
_dup = _unit(_v(_co3, _top3))
X, Y = _frame(_dup, [0, -1, 0], (-0.7071, 0.7071))
sd_fit('SD-Z3', 'EB', 'PVC-EB-45-150', _co3, X, Y, 'ข้องอ 45° ø150 (ช่องล้างต้นสาย ใต้พื้นห้องน้ำ)', 'โซน 3', size='ø150')
sd_pipe('SD-Z3', _pt(_co3, _dup, 0.038), _top3, 150, 'ท่อช่องล้าง', 'โซน 3')
sd_cap('SD-Z3', _top3, _dup, 150, 'โซน 3')
_yd = _yb0 - 0.35                                     # เริ่มลดระดับหลังพ้นคาน
_zd = SD_COVER_Z
_xt3 = GX11
_yt3f = SEP_Y + SEP_D / 2
_pA = [_x3, _yd, _z3s - 0.02 * (_y3s - _yd)]
_pB = [_x3, _yd - 0.40, None]
_pB[2] = _pA[2] - 0.40 - 0.0
_yE = _yt3f + 0.40
_yC = _yE + (_xt3 - _x3)
_pts3 = [[_x3, _y3s - 0.038, _z3s], _pA, _pB, [_x3, _yC, None], [_xt3, _yE, None], [_xt3, _yt3f - 0.02, None]]
_L = 0
for _i in range(3, 6):
    _L += math.hypot(_pts3[_i][0] - _pts3[_i - 1][0], _pts3[_i][1] - _pts3[_i - 1][1])
    _pts3[_i][2] = _pB[2] - 0.02 * _L
sd_route('SD-Z3', _pts3, 150, 'ท่อรวม', 'โซน 3')
SD_TANK_IN['Z3-1'] = _pts3[-1][2]
# ท่อปลอก ø200 ในคาน GB2
_zs = _z3s - 0.02 * (_y3s - GY['B'])
_m = member([_x3, _yb0, _zs], [_x3, _yb1, _zs], SD_OD[200], SD_OD[200])
_m.update(shape='POLY', poly2d=_circ(SD_OD[200] / 2), hole2d=_circ(SD_OD[200] / 2 - SD_T[200]))
add('SD-Z3-SLV1', 'สุขาภิบาล', 1, 'A07', _m, name='ท่อปลอก PVC ø200 ฝังคานคอดิน GB2-B9-10 สำหรับท่อ ø150 (โซน 3)', assumed=True,
    qty=dict(type='ท่อปลอก', size='ø200', length=0.20))

# ปรับระดับถัง: ท่อเข้าที่ระยะ A ต่ำจากปากถัง; ท่ออากาศ ø50 จากปากถังขึ้นเหนือดิน 0.30 (รอแนวต่อขึ้นสูงกว่าอาคาร)
SD_TANK_OUT = {}
for _e in elements:
    _m = re.match(r'^SEP-(Z\d-\d)$', _e['id'])
    if not _m:
        continue
    _k = _m.group(1)
    _top = round(SD_TANK_IN[_k] + SD_A, 3)
    g = _e['geom']
    g['p0'][2], g['p1'][2] = _top, round(_top - SEP_H, 3)
    _e['qty'].update(top=_top, bottom=round(_top - SEP_H, 3), inlet_z=round(SD_TANK_IN[_k], 3), outlet_z=round(SD_TANK_IN[_k] - SD_DROP_TANK, 3),
                     neck=round(-_top, 3))
    SD_TANK_OUT[_k] = (g['p0'][0], SD_TANK_IN[_k] - SD_DROP_TANK)
    # คอถังก่ออิฐฉาบเรียบ จากปากถังขึ้นถึงผิวดิน ±0.00 + ฝาถัง (ผู้ใช้สั่ง 23 พ.ย. 2569; ช่องฝา ø0.60 ผนังคอ 0.10 สมมติ คู่มือ: คอถังไม่เกิน 0.50)
    _xc = g['p0'][0]
    _mn = member([_xc, SEP_Y, _top], [_xc, SEP_Y, -0.03], SD_NECK[1], SD_NECK[1])
    _mn.update(shape='POLY', poly2d=_circ(SD_NECK[1] / 2, 32), hole2d=_circ(SD_NECK[0] / 2, 32))
    add(f'SEP-{_k}-NECK', 'สุขาภิบาล', 1, 'A07', _mn, name=f'คอถังก่ออิฐฉาบเรียบ ช่อง ø{SD_NECK[0]:.2f} สูง {(-0.03 - _top):.2f} ม. ถัง {_k}', assumed=True,
        qty=dict(type='คอถังก่ออิฐฉาบเรียบ', height=round(-0.03 - _top, 3), inner_dia=SD_NECK[0], outer_dia=SD_NECK[1]))
    elements[-1]['material'] = 'BIM-คอถังก่ออิฐฉาบ'
    _ml = member([_xc, SEP_Y, -0.03], [_xc, SEP_Y, 0.0], SD_NECK[1], SD_NECK[1])
    _ml.update(shape='POLY', poly2d=_circ(SD_NECK[1] / 2, 32))
    add(f'SEP-{_k}-LID', 'สุขาภิบาล', 1, 'A07', _ml, name=f'ฝาถังพร้อมกรอบ เสมอผิวดิน ถัง {_k} (ขนาดสมมติ)', assumed=True, qty=dict(type='ฝาถังบำบัด', dia=SD_NECK[1]))
    elements[-1]['material'] = 'BIM-ถังบำบัด DOS เทา'

# ท่อทิ้งรวม ø150 หลังแนวถัง ลาด 1:100 ไปทางกริด 11 (บ่อพักโครงการเฟสถัดไป ห่าง ~50 ม.) ปิดปลายรอ
_ys = SD_MAINY
_xs0 = min(x for x, _ in SD_TANK_OUT.values()) - 0.20
_xend = GX11 + 1.00
_zmain0 = min(z + 0.01 * ((x + 0.40) - _xs0) for x, z in SD_TANK_OUT.values()) - 0.05
_zmf = lambda x: _zmain0 - 0.01 * (x - _xs0)
_pco = [_xs0, _ys, _zmain0]
_top = sd_cleanout('SD-OUT', _pco, [1, 0, 0], 150, 'ท่อทิ้งรวม')
_dup = _unit(_v(_pco, _top))
X, Y = _frame(_dup, [1, 0, 0], (-0.7071, 0.7071))
sd_fit('SD-OUT', 'EB', 'PVC-EB-45-150', _pco, X, Y, 'ข้องอ 45° ø150 (ช่องล้างต้นสาย)', 'ท่อทิ้งรวม', size='ø150')
sd_pipe('SD-OUT', _pt(_pco, _dup, 0.038), _top, 150, 'ท่อช่องล้าง', 'ท่อทิ้งรวม')
sd_cap('SD-OUT', _top, _dup, 150, 'ท่อทิ้งรวม')
_cur = _pt(_pco, [1, 0, 0], 0.038)
for _k in sorted(SD_TANK_OUT, key=lambda k: SD_TANK_OUT[k][0]):
    _xt, _zo = SD_TANK_OUT[_k]
    _Yo = [_xt + 0.40, _ys, _zmf(_xt + 0.40)]
    _o_out, _o_in, _o_br = sd_y('SD-OUT', (150, 100), _Yo, _unit([1, 0, -0.01]), [-0.7071, 0.7071, 0.0], 'ท่อทิ้งรวม')
    sd_pipe('SD-OUT', _cur, _o_in, 150, 'ท่อทิ้งรวม', 'ท่อทิ้งรวม')
    _p0 = [_xt, SEP_Y - SEP_D / 2 + 0.02, _zo]
    _p1 = [_xt, SEP_Y - SEP_D / 2 - 0.19, _zo - 0.01 * 0.21]
    sd_route(f'SD-{_k}', [_p0, _p1, _o_br], 100, 'ท่อออกจากถัง', f'ถัง {_k}')
    _cur = _o_out
_pend = [_xend, _ys, _zmf(_xend)]
sd_pipe('SD-OUT', _cur, _pend, 150, 'ท่อทิ้งรวม (ปิดปลายรอต่อบ่อพักโครงการ)', 'ท่อทิ้งรวม')
sd_cap('SD-OUT', _pend, [1, 0, 0], 150, 'ท่อทิ้งรวม')
# ท่ออากาศถังบำบัดเข้าท่ออากาศอาคาร: ยกเลิก (ผู้ใช้สั่ง 23 พ.ย. 2569)
# ---- ระบบท่อห้องน้ำแนว N3 ชั้น 2–5 (ผู้ใช้สั่ง 23 พ.ย. 2569; ทำแนว N3 ก่อน ตรวจผ่านแล้วใช้กับแนวอื่น) ----
# พิกัดในบล็อกนี้เขียนเป็นพิกัด elements.json (กลับแกน y แล้ว) แล้วแปลงกลับก่อนเก็บ (_J / _JV) เพื่อให้ตรงกับแปลน
# ท่อน้ำเสีย: ชักโครก → ข้อต่อกันซึม SCG 4" สีฟ้าในพื้น → ข้องอ 90° → ท่อ 4" ใต้พื้นลาด 1:50 → สามทาง TY-100 บนท่อส้วม
#            อ่างล้างหน้า → P-trap 2" → ทะลุผนังชาร์ฟ SH1 ที่ +0.45 → สามทางลด TYR-80x55 บนท่อน้ำทิ้ง
#            ฟลอร์เดรน PVC มุมข้างชักโครก (ระหว่างชักโครกกับผนังชาร์ฟ SH2) → ข้องอ 90° → ท่อ 3" ใต้พื้นลาด 1:50 → TY-80 บนท่อน้ำทิ้ง
# ท่ออากาศย่อย: ทุกชั้น ท่อส้วม (TYR-100x55 ที่ +1.10) และท่อน้ำทิ้ง (TYR-80x55 ที่ +1.25) → ท่อ 2" → สามทาง TEE-55 บนท่ออากาศ
# ตัวยึด: ทุกชั้นใต้พื้น เหล็กฉาก L50x50x5 2 ตัว (ขวางแนว x ยึดข้างคาน B3-4-AB, แนว y ยึดข้างคาน B2) + ห่วงรัดท่อ
_YM = GY['F']


def _J(p):
    return [p[0], round(_YM - p[1], 4), p[2]]


def _JV(v):
    return [v[0], -v[1], v[2]]


def n3_fit(eid, dname, o, X, Y, nm, size):
    """คอมโพเนนต์ข้อต่อจากไฟล์ตัวอย่าง วางด้วยแกน X, Y (พิกัด json)"""
    oo = [round(c, 4) for c in _J(o)]
    add(eid, 'สุขาภิบาล', 1, 'A07', member(oo, [oo[0], oo[1], oo[2] + 0.01], 0.05, 0.05),
        name=f'{nm} คอมโพเนนต์ไฟล์ตัวอย่าง {dname}', assumed=True, qty=dict(type=nm, model=dname, size=size))
    elements[-1]['fitting'] = {'def': dname, 'origin': oo, 'x': [round(c, 5) for c in _JV(X)], 'y': [round(c, 5) for c in _JV(Y)], 'anchor': 'origin'}


def n3_pipe(eid, p, q, od, t, nm, cls='8.5', solid=False, cat='สุขาภิบาล'):
    m = member(_J(p), _J(q), od, od)
    m.update(shape='POLY', poly2d=_circ(od / 2))
    if not solid and t:
        m['hole2d'] = _circ(od / 2 - t)
    L = math.dist(p, q)
    add(eid, cat, 1, 'A07', m, name=nm, assumed=True,
        qty=dict(length=round(L, 3), od_mm=round(od * 1000, 1), cls=cls,
                 slope=round(abs(q[2] - p[2]) / max(math.hypot(q[0] - p[0], q[1] - p[1]), 1e-6), 4)))


def n3_box(eid, x0, y0, x1, y1, z0, t, nm, cat='สุขาภิบาล', qty=None):
    add(eid, cat, 1, 'A07', prism([(x0, _YM - y0), (x1, _YM - y0), (x1, _YM - y1), (x0, _YM - y1)], z0, t), name=nm, assumed=True, qty=qty or {})


def n3_chrome(eid, p, q, d, nm, qty=None, mat='BIM-โครเมียม', cat='สุขาภิบาล'):
    m = member(_J(p), _J(q), d, d)
    m.update(shape='POLY', poly2d=_circ(d / 2, 16))
    add(eid, cat, 1, 'A07', m, name=nm, assumed=True, qty=qty or {})
    elements[-1]['material'] = mat


def _hz(d):
    L = math.hypot(d[0], d[1])
    return [d[0] / L, d[1] / L, 0.0]


N3_P = {k: next(e for e in elements if e['id'] == f'PB-N3-{k}') for k in ('SOIL', 'WASTE', 'VENT')}
N3_XY = {k: (e['geom']['p0'][0], round(_YM - e['geom']['p0'][1], 4)) for k, e in N3_P.items()}   # พิกัด json
N3_CUTS = {'SOIL': [], 'WASTE': [], 'VENT': []}      # (z ศูนย์ข้อต่อ, ระยะก้นปากบน, ระยะก้นปากล่าง)
DN = [0, 0, -1]
WC_RI = 0.305                                        # ระยะท่อออกชักโครกจากผนังหลัง (มาตรฐาน; ยังไม่มีแบบติดตั้ง K2760)
OD50, T50, OD80, T80, OD100, T100 = SD_OD[50], SD_T[50], SD_OD[80], SD_T[80], SD_OD[100], SD_T[100]
for f in (2, 3, 4, 5):
    P = f'PB-N3-F{f}'
    FF = FL[f] - DROP + 0.02                         # ผิวกระเบื้องห้องน้ำ
    SB = FL[f] - DROP - S1_T                         # ท้องพื้น S1
    xs, ys = N3_XY['SOIL']; xw, yw = N3_XY['WASTE']; xv, yv = N3_XY['VENT']
    # 1) ชักโครก: ข้อต่อกันซึม + ข้องอ 90° + ท่อ 4" ใต้พื้น → TY-100 บนท่อส้วม
    wc = next(e for e in elements if e['id'] == f'FX-F{f}-N3-WC')
    wxs = [q[0] for q in wc['geom']['poly']]; wys = [_YM - q[1] for q in wc['geom']['poly']]
    xo, yo = max(wxs) - WC_RI, (min(wys) + max(wys)) / 2          # ถังพักชิดผนังกริด 4 (x มาก) หน้าหันไปทางผนัง B5
    n3_fit(f'{P}-WC-SLV', 'PVC-TS-FLANG-100', [xo, yo, SB], [1, 0, 0], [0, 1, 0], 'ข้อต่อกันซึม PVC 4" สีฟ้า SCG ใต้ชักโครก (ฝังในพื้น)', '4"')
    elements[-1]['qty'].update(brand='SCG', color='ฟ้า')
    zE = SB - 0.30                                   # ลดระดับท่อใต้พื้น ให้มีที่วางท่ออากาศหลังท่อ (ผู้ใช้สั่ง 23 พ.ย. 2569)
    d = _hz([xs - xo, ys - yo, 0])
    zT = zE - 0.02 * math.hypot(xs - xo, ys - yo)
    n3_fit(f'{P}-WC-EB', 'PVC-EB-90-100', [xo, yo, zE], [0, 0, 1], d, 'ข้องอ 90° ø4" ใต้ชักโครก', '4"')
    n3_pipe(f'{P}-WC-P1', [xo, yo, zE + 0.057], [xo, yo, SB + 0.10], OD100, T100, 'ท่อส้วม 4" PVC 8.5 จากชักโครกผ่านข้อต่อกันซึม')
    n3_fit(f'{P}-WC-TY', 'PVC-TY-100', [xs, ys, zT], DN, [-d[0], -d[1], 0], 'สามทางวาย (TY) ø4" รับท่อชักโครก บนท่อส้วม', '4"')
    N3_CUTS['SOIL'].append((zT, 0.040, 0.123))
    # ท่ออากาศหลังท่อชักโครก: สามทางลด TYR-100x55 ปากแยกตั้งขึ้น ห่างข้องอใต้ชักโครก 0.25
    sV = 0.25
    T = [xo + d[0] * sV, yo + d[1] * sV, zE - 0.02 * sV]
    n3_fit(f'{P}-WC-VT', 'PVC-TYR-100x55', T, [d[0], d[1], 0], [0, 0, 1], 'สามทางลด 4"x2" ท่ออากาศหลังท่อชักโครก', '4"x2"')
    n3_pipe(f'{P}-WC-P2', [xo + d[0] * 0.057, yo + d[1] * 0.057, zE], [T[0] - d[0] * 0.027, T[1] - d[1] * 0.027, T[2]], OD100, T100,
            'ท่อส้วม 4" PVC 8.5 ใต้พื้นห้องน้ำ ลาด 1:50 ชักโครก → สามทางท่ออากาศ')
    n3_pipe(f'{P}-WC-P3', [T[0] + d[0] * 0.061, T[1] + d[1] * 0.061, T[2]], [xs - d[0] * 0.123, ys - d[1] * 0.123, zT], OD100, T100,
            'ท่อส้วม 4" PVC 8.5 ใต้พื้นห้องน้ำ ลาด 1:50 → ท่อส้วม')
    # 2) อ่างล้างหน้า: ท่อหางอ่าง + P-trap 2" + ท่อทะลุผนังชาร์ฟ → TYR-80x55 บนท่อน้ำทิ้ง
    zA = FF + 0.45
    lav = next(e for e in elements if e['id'] == f'FX-F{f}-N3-LAV')
    lxs = [q[0] for q in lav['geom']['poly']]
    xwall = max(lxs)                                  # ผิวผนังชาร์ฟ SH1 ด้านห้องน้ำ
    oT = [xwall - 0.06, yw, zA - 0.058]
    n3_fit(f'{P}-LAV-TRAP', 'PVC-P-TRAP-55', oT, [1, 0, 0], [0, 1, 0], 'พีแทรปโครเมียม LUZERN OS-009-30 ใต้อ่างล้างหน้า (หลังขาอ่าง) รูปทรงแทนด้วย', '30 ซม.')
    elements[-1]['qty'].update(model='LUZERN OS-009-30 สีโครม', material='โครเมียม')      # วิวัฒน์ 24 พ.ย. 2569: ห้องน้ำหอพักใช้พีแทรปโครเมียม
    elements[-1]['material'] = 'BIM-โครเมียม'
    # สะดืออ่างสำเร็จรูป สแตนเลส แบบทั่วไปตามท้องตลาด (ผู้ใช้สั่ง 23 พ.ย. 2569) ใต้อ่างต่อท่อ 2"
    n3_chrome(f'{P}-LAV-WST', [oT[0] - 0.102, yw, FF + 0.55], [oT[0] - 0.102, yw, FF + 0.65], 0.040, 'สะดืออ่างล้างหน้าสำเร็จรูป สแตนเลส (แบบทั่วไปตามท้องตลาด) ต่อท่อ 2"',
              qty=dict(type='สะดืออ่างสแตนเลส', size='ต่อท่อ 2"'), mat='BIM-สแตนเลส')
    n3_pipe(f'{P}-LAV-P0', [oT[0] - 0.102, yw, oT[2] + 0.045], [oT[0] - 0.102, yw, FF + 0.55], OD50, T50, 'ท่อน้ำทิ้งใต้อ่าง 2" PVC 8.5 (สะดืออ่าง → P-trap)')
    n3_fit(f'{P}-LAV-TY', 'PVC-TYR-80x55', [xw, yw, zA], DN, [-1, 0, 0], 'สามทางวายลด (TYR) 3"x2" รับท่ออ่างล้างหน้า บนท่อน้ำทิ้ง', '3"x2"')
    N3_CUTS['WASTE'].append((zA, 0.025, 0.062))
    n3_pipe(f'{P}-LAV-P1', [oT[0] + 0.030, yw, zA], [xw - 0.076, yw, zA], OD50, T50, 'ท่อน้ำทิ้งอ่าง 2" PVC 8.5 ทะลุผนังชาร์ฟ → ท่อน้ำทิ้ง')
    # 3) ฟลอร์เดรน PVC มุมข้างชักโครก → ข้องอ 90° → ท่อ 3" ใต้พื้น → TY-80 บนท่อน้ำทิ้ง
    # ตำแหน่ง (ผู้ใช้สั่ง 23 พ.ย. 2569): มุมห้องแถวฝักบัว (มุมผนัง B5 กับผนังนอก) ใต้มุมเป็นคาน B5 (x ถึง 8.575) และ B4 (y ตั้งแต่ 15.30)
    # → วางชิดมุมที่สุดโดยท่อ 3" ลงพ้นข้างคานทั้งสอง
    xF, yF = 8.575 + 0.075, 15.30 - 0.075
    n3_box(f'{P}-FD', xF - 0.06, yF - 0.06, xF + 0.06, yF + 0.06, FF - 0.003, 0.006,
           'ฟลอร์เดรน PVC ฝังพื้น ตะแกรง 4" แบบกันกลิ่น (ท่อน้ำทิ้งจากการอาบน้ำ) มุมห้องข้างฝักบัว',
           qty=dict(type='ฟลอร์เดรน PVC กันกลิ่น', size='ตะแกรง 4" ต่อท่อ 3"'))
    elements[-1]['material'] = 'BIM-สแตนเลส'
    zF = SB - 0.30
    dF = _hz([xw - xF, yw - yF, 0])
    zTF = zF - 0.02 * math.hypot(xw - xF, yw - yF)
    n3_pipe(f'{P}-FD-P1', [xF, yF, FF - 0.003], [xF, yF, zF + 0.044], OD80, T80, 'ตัวฟลอร์เดรน/ท่อ 3" PVC ฝังพื้น')
    n3_fit(f'{P}-FD-EB', 'PVC-EB-90-80', [xF, yF, zF], [0, 0, 1], dF, 'ข้องอ 90° ø3" ใต้ฟลอร์เดรน', '3"')
    n3_fit(f'{P}-FD-TY', 'PVC-TY-80', [xw, yw, zTF], DN, [-dF[0], -dF[1], 0], 'สามทางวาย (TY) ø3" รับท่อฟลอร์เดรน บนท่อน้ำทิ้ง', '3"')
    N3_CUTS['WASTE'].append((zTF, 0.026, 0.096))
    sF = 0.15
    TF = [xF + dF[0] * sF, yF + dF[1] * sF, zF - 0.02 * sF]
    n3_fit(f'{P}-FD-VT', 'PVC-TYR-80x55', TF, [dF[0], dF[1], 0], [0, 0, 1], 'สามทางลด 3"x2" ท่ออากาศหลังท่อฟลอร์เดรน', '3"x2"')
    n3_pipe(f'{P}-FD-P2', [xF + dF[0] * 0.044, yF + dF[1] * 0.044, zF], [TF[0] - dF[0] * 0.025, TF[1] - dF[1] * 0.025, TF[2]], OD80, T80,
            'ท่อน้ำทิ้ง 3" PVC 8.5 ใต้พื้นห้องน้ำ ลาด 1:50 ฟลอร์เดรน → สามทางท่ออากาศ')
    n3_pipe(f'{P}-FD-P3', [TF[0] + dF[0] * 0.062, TF[1] + dF[1] * 0.062, TF[2]], [xw - dF[0] * 0.096, yw - dF[1] * 0.096, zTF], OD80, T80,
            'ท่อน้ำทิ้ง 3" PVC 8.5 ใต้พื้นห้องน้ำ ลาด 1:50 → ท่อน้ำทิ้ง')
    # ท่ออากาศหลังท่อ 2" ใต้พื้น (ผู้ใช้สั่ง 23 พ.ย. 2569): ฟลอร์เดรน → สามทางบนท่อตั้งหลังท่อชักโครก → ข้องอ 90° → ข้องอ 45° →
    # ลอดช่องระหว่างท่อน้ำทิ้งกับท่อส้วม → สามทาง TEE-55 บนท่ออากาศในช่องชาร์ฟ (ใต้ท้องพื้น); ท่อราบลาดลงหาท่อน้ำเสีย 1:100
    zTe, zV = SB - 0.15, SB - 0.06
    mx, my = ((xw + OD80 / 2) + (xs - OD100 / 2)) / 2, (yw + ys) / 2           # กึ่งกลางช่องระหว่างท่อน้ำทิ้งกับท่อส้วม
    d0 = _hz([mx - xv, my - yv, 0])
    best = None
    for sg in (-1, 1):                                    # หมุน d0 ±45° หาแนวที่ตัดกับจุดท่อตั้ง
        c, sn = 0.70711, 0.70711 * sg
        e = [d0[0] * c - d0[1] * sn, d0[0] * sn + d0[1] * c, 0]
        det = d0[0] * e[1] - d0[1] * e[0]
        bx, by = T[0] - xv, T[1] - yv
        t = (bx * e[1] - by * e[0]) / det; u = (d0[0] * by - d0[1] * bx) / det
        if t > 0.30 and u > 0.12 and (best is None or u < best[1]):
            best = (t, u, e)
    t, u, e = best
    G = [xv + d0[0] * t, yv + d0[1] * t, zV + 0.01 * u]
    zSt = G[2] + 0.01 * t
    # ท่อตั้งหลังท่อชักโครก + สามทางรับท่ออากาศฟลอร์เดรน + ข้องอ 90°
    dTF = _hz([TF[0] - T[0], TF[1] - T[1], 0])
    n3_pipe(f'{P}-AV-P1', [T[0], T[1], T[2] + 0.087], [T[0], T[1], zTe - 0.031], OD50, T50, 'ท่ออากาศหลังท่อชักโครก 2" PVC 8.5 (ท่อตั้ง)')
    n3_fit(f'{P}-AV-TE1', 'PVC-TEE-55', [T[0], T[1], zTe], DN, dTF, 'สามทาง ø2" รับท่ออากาศหลังท่อฟลอร์เดรน', '2"')
    n3_pipe(f'{P}-AV-P2', [T[0], T[1], zTe + 0.031], [T[0], T[1], zV - 0.030], OD50, T50, 'ท่ออากาศหลังท่อชักโครก 2" PVC 8.5 (ท่อตั้ง)')
    eb = [-e[0], -e[1], 0]
    n3_fit(f'{P}-AV-EB1', 'PVC-EB-90-55', [T[0], T[1], zV], DN, eb, 'ข้องอ 90° ø2" ท่ออากาศ', '2"')
    n3_pipe(f'{P}-AV-P3', [T[0] + eb[0] * 0.030, T[1] + eb[1] * 0.030, zV], [G[0] + e[0] * 0.0145, G[1] + e[1] * 0.0145, G[2]], OD50, T50,
            'ท่ออากาศ 2" PVC 8.5 ใต้พื้น (ลาด 1:100)')
    X, Y = _frame(e, [-d0[0], -d0[1], 0], (-0.7071, 0.7071))
    n3_fit(f'{P}-AV-EB2', 'PVC-EB-45-55.', G, X, Y, 'ข้องอ 45° ø2" ท่ออากาศ', '2"')
    n3_pipe(f'{P}-AV-P4', [G[0] - d0[0] * 0.0145, G[1] - d0[1] * 0.0145, G[2]], [xv + d0[0] * 0.031, yv + d0[1] * 0.031, zSt], OD50, T50,
            'ท่ออากาศ 2" PVC 8.5 ใต้พื้น ลอดระหว่างท่อน้ำทิ้งกับท่อส้วม → ท่ออากาศ')
    n3_fit(f'{P}-AV-TE2', 'PVC-TEE-55', [xv, yv, zSt], DN, d0, 'สามทาง ø2" รับท่ออากาศใต้พื้น บนท่ออากาศ', '2"')
    N3_CUTS['VENT'].append((zSt, 0.031, 0.031))
    # ท่ออากาศหลังท่อฟลอร์เดรน: ท่อตั้ง → ข้องอ 90° → ท่อราบเข้าสามทางบนท่อตั้งหลังท่อชักโครก
    zFv = zTe - 0.01 * math.hypot(TF[0] - T[0], TF[1] - T[1])
    n3_pipe(f'{P}-FV-P1', [TF[0], TF[1], TF[2] + 0.076], [TF[0], TF[1], zFv - 0.030], OD50, T50, 'ท่ออากาศหลังท่อฟลอร์เดรน 2" PVC 8.5 (ท่อตั้ง)')
    n3_fit(f'{P}-FV-EB1', 'PVC-EB-90-55', [TF[0], TF[1], zFv], DN, [-dTF[0], -dTF[1], 0], 'ข้องอ 90° ø2" ท่ออากาศ', '2"')
    n3_pipe(f'{P}-FV-P2', [TF[0] - dTF[0] * 0.030, TF[1] - dTF[1] * 0.030, zFv], [T[0] + dTF[0] * 0.031, T[1] + dTF[1] * 0.031, zTe], OD50, T50,
            'ท่ออากาศหลังท่อฟลอร์เดรน 2" PVC 8.5 ใต้พื้น (ลาด 1:100) → ท่อตั้งหลังท่อชักโครก')
    # 4) ท่ออากาศย่อย: ท่อส้วม +1.10, ท่อน้ำทิ้ง +1.25 → TEE-55 บนท่ออากาศ
    for k, zr, dn, prt, up_b, dn_b in (('SOIL', FF + 1.10, 'PVC-TYR-100x55', 0.087, 0.027, 0.061), ('WASTE', FF + 1.25, 'PVC-TYR-80x55', 0.076, 0.025, 0.062)):
        xk, yk = N3_XY[k]
        dv = _hz([xv - xk, yv - yk, 0])
        n3_fit(f'{P}-RV{k[0]}-TY', dn, [xk, yk, zr], DN, dv, f'สามทางวายลด ท่ออากาศย่อย 2" บน{"ท่อส้วม" if k == "SOIL" else "ท่อน้ำทิ้ง"}', dn[8:])
        N3_CUTS[k].append((zr, up_b, dn_b))
        n3_fit(f'{P}-RV{k[0]}-TE', 'PVC-TEE-55', [xv, yv, zr], DN, [-dv[0], -dv[1], 0], 'สามทาง ø2" รับท่ออากาศย่อย บนท่ออากาศ', '2"')
        N3_CUTS['VENT'].append((zr, 0.031, 0.031))
        n3_pipe(f'{P}-RV{k[0]}-P1', [xk + dv[0] * prt, yk + dv[1] * prt, zr], [xv - dv[0] * 0.031, yv - dv[1] * 0.031, zr], OD50, T50,
                f'ท่ออากาศย่อย 2" PVC 8.5 {"ท่อส้วม" if k == "SOIL" else "ท่อน้ำทิ้ง"} → ท่ออากาศ ห้อง N3 ชั้น {f}')
    # 5) ตัวยึดท่อใต้พื้น: เหล็กฉาก L50x50x5 + เพลทยึดข้างคาน + ห่วงรัดท่อ
    zS = SB - 0.15                                   # ตัวยึดชิดท้องพื้น เหนือสามทางรับท่อใต้พื้น
    ya0 = max(ys + OD100 / 2, yw + OD80 / 2) + 0.008
    xb0 = xv - OD50 / 2 - 0.02 - 0.05
    yB2 = _YM - (GY['B'] - 0.125) + PL_T              # ผิวฉาบข้างคาน B2 ด้านห้องน้ำ (json)
    xB3 = GX[3] - 0.125 - PL_T                        # ผิวฉาบข้างคาน B3-4-AB
    n3_box(f'{P}-SUP-A1', SH_X0 := xw - OD80 / 2 - 0.01, ya0, xB3, ya0 + 0.05, zS, 0.005, 'เหล็กฉาก L50x50x5 ขวางช่องชาร์ฟ (ปีกนอน) ยึดข้างคาน B3-4-AB', cat='สุขาภิบาล',
           qty=dict(type='เหล็กฉาก L50x50x5', length=round(xB3 - SH_X0, 3)))
    n3_box(f'{P}-SUP-A2', SH_X0, ya0, xB3, ya0 + 0.005, zS, 0.05, 'เหล็กฉาก L50x50x5 ขวางช่องชาร์ฟ (ปีกตั้ง)')
    n3_box(f'{P}-SUP-B1', xb0, yB2, xb0 + 0.05, ya0, zS, 0.005, 'เหล็กฉาก L50x50x5 แนวยาว (ปีกนอน) ยึดข้างคาน B2',
           qty=dict(type='เหล็กฉาก L50x50x5', length=round(ya0 - yB2, 3)))
    n3_box(f'{P}-SUP-B2', xb0 + 0.045, yB2, xb0 + 0.05, ya0, zS, 0.05, 'เหล็กฉาก L50x50x5 แนวยาว (ปีกตั้ง)')
    # เพลทยึด PL8x150x150 ยิงพุก 4-M12 เชื่อมกับเหล็กฉาก L50x5 (ผู้ใช้กำหนด 23 พ.ย. 2569) กึ่งกลางเพลทตรงกึ่งกลางเหล็กฉาก
    SP_T, SP_W = 0.008, 0.150
    n3_box(f'{P}-SUP-PL1', xB3 - SP_T, ya0 + 0.025 - SP_W / 2, xB3, ya0 + 0.025 + SP_W / 2, zS + 0.025 - SP_W / 2, SP_W,
           'เพลทเหล็ก PL8x150x150 ยิงพุก 4-M12 ข้างคาน B3-4-AB เชื่อมกับเหล็กฉาก L50x5',
           qty=dict(type='เพลทเหล็ก PL8x150x150 + พุก M12', size='150x150x8', bolts=4))
    n3_box(f'{P}-SUP-PL2', xb0 + 0.025 - SP_W / 2, yB2, xb0 + 0.025 + SP_W / 2, yB2 + SP_T, zS + 0.025 - SP_W / 2, SP_W,
           'เพลทเหล็ก PL8x150x150 ยิงพุก 4-M12 ข้างคาน B2 เชื่อมกับเหล็กฉาก L50x5',
           qty=dict(type='เพลทเหล็ก PL8x150x150 + พุก M12', size='150x150x8', bolts=4))
    for k, od in (('SOIL', OD100), ('WASTE', OD80), ('VENT', OD50)):
        xk, yk = N3_XY[k]
        m = member(_J([xk, yk, zS + 0.01]), _J([xk, yk, zS + 0.035]), od + 0.012, od + 0.012)
        m.update(shape='POLY', poly2d=_circ(od / 2 + 0.006), hole2d=_circ(od / 2 + 0.001))
        add(f'{P}-SUP-C{k[0]}', 'สุขาภิบาล', 1, 'A07', m, name=f'ห่วงรัดท่อเหล็กชุบกัลวาไนซ์ บุยาง {"4" if k == "SOIL" else "3" if k == "WASTE" else "2"}" ยึดกับเหล็กฉาก', assumed=True,
            qty=dict(type='ห่วงรัดท่อ', size=f'{round(od*1000)} มม.'))

# ---- ท่อน้ำดี PVC ชั้น 13.5 ห้องน้ำแนว N3 (ผู้ใช้สั่ง 23 พ.ย. 2569) ----
# น้ำมาจากมิเตอร์หน้าห้อง (ฝั่งตรงข้ามประตู) ท่อ 4 หุน (1/2") หลังมิเตอร์ (ผู้ใช้แก้จาก 6 หุน 23 พ.ย. 2569) ฝังพื้นเข้ามาริมเสา C1-4B แล้วขึ้นในผนังแนวช่องชาร์ฟ (ผู้ใช้สั่ง)
# ท่อฝังผนัง (สกัดร่อง) 1/2": สายตะวันตก → ผนัง B5 (ผนังร่วมระเบียง) หน้าชักโครก: สต็อปวาล์วฝักบัว +1.10 + ฝักบัวสายอ่อนแขวนขอ +1.80, ก๊อกระเบียง +0.60 ด้านระเบียง
#                         สายตะวันออก → มุมผนังชาร์ฟ ลง +0.55: วาล์วเปิดปิดอ่างล้างหน้า (angle valve) +0.55, สต็อปวาล์วชักโครก +0.20 ที่ผนังกริด 4
WOD = {'3/4': (0.0267, 0.0018), '1/2': (0.0222, 0.0016)}     # ชั้น 13.5 ค่าประมาณ


def n3_wpipe(eid, p, q, sz, nm):
    od, t = WOD[sz]
    n3_pipe(eid, p, q, od, t, f'{nm} ø{sz}" PVC ชั้น 13.5', cls='13.5', cat='สุขาภิบาล')
    elements[-1]['material'] = 'BIM-ท่อน้ำดี PVC ฟ้า'
    elements[-1]['qty']['size'] = f'{sz}"'


def n3_wfit(eid, p, sz, nm):
    h = WOD[sz][0] / 2 + 0.006
    n3_box(eid, p[0] - h, p[1] - h, p[0] + h, p[1] + h, p[2] - h, 2 * h, f'{nm} PVC ชั้น 13.5 ø{sz}" (ทำเอง ไม่มีในไฟล์ตัวอย่าง)', cat='สุขาภิบาล',
           qty=dict(type=nm, size=f'{sz}"'))
    elements[-1]['material'] = 'BIM-ท่อน้ำดี PVC ฟ้า'


def n3_wroute(pref, pts, sz, nm, fit_names=None):
    """ท่อผ่านจุด pts ข้องอ 90° (ทำเอง) ทุกจุดหักมุม — คืนรายการรหัส"""
    h = WOD[sz][0] / 2 + 0.006
    for j in range(len(pts) - 1):
        a, b = pts[j], pts[j + 1]
        d = _unit(_v(a, b))
        s0 = h if j > 0 else 0.0
        s1 = h if j < len(pts) - 2 else 0.0
        n3_wpipe(f'{pref}-P{j+1}', _pt(a, d, s0), _pt(b, d, -s1), sz, nm)
        if j < len(pts) - 2:
            n3_wfit(f'{pref}-EL{j+1}', b, sz, (fit_names or {}).get(j + 1, 'ข้องอ 90°'))


for f in (2, 3, 4, 5):
    P = f'PB-N3-F{f}-CW'
    FF = FL[f] - DROP + 0.02
    wc = next(e for e in elements if e['id'] == f'FX-F{f}-N3-WC')
    wys = [_YM - q[1] for q in wc['geom']['poly']]
    lav = next(e for e in elements if e['id'] == f'FX-F{f}-N3-LAV')
    lxs = [q[0] for q in lav['geom']['poly']]; lys = [_YM - q[1] for q in lav['geom']['poly']]
    y_bal = 13.885                                    # แนวท่อในผนังประตูห้องน้ำ (ผนัง BAL ฝั่งห้องน้ำ)
    x_b5f, x_b5b = 8.55, 8.45                         # ผิวฉาบผนัง B5 ด้านห้องน้ำ / ด้านระเบียง
    x_b5 = x_b5f - 0.0135                             # แนวท่อในผนัง B5
    x_sh = max(lxs) + 0.0135                          # แนวท่อในผนังชาร์ฟ SH1
    y_sh2 = 14.565 - 0.0135                           # แนวท่อในผนังชาร์ฟ SH2
    x_g4 = 10.45 + 0.0135                             # แนวท่อในผนังกริด 4
    y_s = (min(wys) + max(wys)) / 2                   # ฝักบัว/ก๊อกระเบียง ตรงหน้าชักโครก
    zM = FF + 2.30
    # ท่อ 4 หุน (1/2") จากมิเตอร์หน้าห้อง ฝังในพื้นทับหน้าห้องพัก แนวริมเสา C1-4B → ขึ้นในผนังแนวช่องชาร์ฟ (ผนังหลังห้อง) → สามทางที่มุมผนังชาร์ฟ (ผู้ใช้สั่ง 23 พ.ย. 2569)
    x_c = GX[3] - 0.175 - 0.025                       # ริมเสา C1-4B ด้านห้อง
    y_fr = _YM - (GY['C'] + 0.165)                    # ผิวฉาบผนังทางเดินด้านห้อง (มิเตอร์อยู่หน้าห้องฝั่งตรงข้ามประตู)
    zFl = FL[f] - 0.025                               # ฝังในคอนกรีตทับหน้า
    zJ = FF + 0.55
    n3_wroute(f'{P}-M', [[x_c, 8.535 + 0.0171, zFl], [x_c, y_bal, zFl], [x_c, y_bal, zJ], [x_sh, y_bal, zJ]], '1/2',
              'ท่อน้ำดี 4 หุน หลังมิเตอร์หน้าห้อง ฝังพื้น → ริมเสา → ผนังแนวช่องชาร์ฟ')
    elements[-1]['geom']['p1'] = _J([x_sh + WOD['1/2'][0] / 2 + 0.006, y_bal, zJ])
    n3_wfit(f'{P}-TE0', [x_sh, y_bal, zJ], '1/2', 'สามทาง')
    # สายตะวันตก: ขึ้นมุมผนังชาร์ฟ → ผนังประตูห้องน้ำ +2.30 (เหนือวงกบ) → ผนัง B5 → ลงฝักบัว/ก๊อกระเบียง
    n3_wroute(f'{P}-W', [[x_sh, y_bal, zJ], [x_sh, y_bal, zM], [x_b5, y_bal, zM], [x_b5, y_s, zM], [x_b5, y_s, FF + 1.10]], '1/2', 'ท่อน้ำดีฝังผนัง สายฝักบัว/ก๊อกระเบียง')
    n3_wfit(f'{P}-W-TE', [x_b5, y_s, FF + 1.10], '1/2', 'สามทาง')
    n3_wpipe(f'{P}-W-D1', [x_b5, y_s, FF + 1.10 - 0.0171], [x_b5, y_s, FF + 0.60 + 0.0171], '1/2', 'ท่อน้ำดีฝังผนัง ลงก๊อกระเบียง')
    n3_wfit(f'{P}-W-EL4', [x_b5, y_s, FF + 0.60], '1/2', 'ข้องอ 90°')
    n3_wpipe(f'{P}-W-D2', [x_b5 - 0.0171, y_s, FF + 0.60], [x_b5b, y_s, FF + 0.60], '1/2', 'ท่อน้ำดีทะลุผนัง B5 ไปก๊อกระเบียง')
    n3_wpipe(f'{P}-W-D3', [x_b5 + 0.0171, y_s, FF + 1.10], [x_b5f, y_s, FF + 1.10], '1/2', 'ท่อน้ำดีออกสต็อปวาล์วฝักบัว')
    # ชุดฝักบัวทั่วไป ราคาไม่สูง: สต็อปวาล์ว + ฝักบัวสายอ่อน + ขอแขวน
    zv = FF + 1.10
    n3_chrome(f'{P}-SHV', [x_b5f, y_s, zv], [x_b5f + 0.07, y_s, zv], 0.032, 'สต็อปวาล์วฝักบัว (วาล์วเดี่ยว ชุบโครเมียม) +1.10',
              qty=dict(type='สต็อปวาล์วฝักบัว', size='1/2"'))
    n3_chrome(f'{P}-SHV-H', [x_b5f + 0.035, y_s, zv], [x_b5f + 0.035, y_s, zv + 0.05], 0.012, 'ด้ามหมุนสต็อปวาล์วฝักบัว')
    n3_chrome(f'{P}-SHK', [x_b5f, y_s, FF + 1.80], [x_b5f + 0.05, y_s, FF + 1.80], 0.025, 'ขอแขวนฝักบัว ติดผนัง +1.80')
    n3_chrome(f'{P}-SHH', [x_b5f + 0.05, y_s, FF + 1.68], [x_b5f + 0.07, y_s, FF + 1.86], 0.028, 'ฝักบัวสายอ่อน (ด้ามจับ) ราคาประหยัด',
              qty=dict(type='ชุดฝักบัวสายอ่อน + สต็อปวาล์ว + ขอแขวน', grade='ทั่วไป ราคาไม่สูง'))
    n3_chrome(f'{P}-SHD', [x_b5f + 0.07, y_s, FF + 1.86], [x_b5f + 0.095, y_s, FF + 1.95], 0.09, 'หัวฝักบัวสายอ่อน ø9 ซม.')
    n3_chrome(f'{P}-SHS1', [x_b5f + 0.07, y_s, zv], [x_b5f + 0.10, y_s + 0.04, FF + 0.80], 0.012, 'สายฝักบัวสแตนเลส 1.20 ม. (ช่วงล่าง)', mat='BIM-สแตนเลส')
    n3_chrome(f'{P}-SHS2', [x_b5f + 0.10, y_s + 0.04, FF + 0.80], [x_b5f + 0.05, y_s, FF + 1.68], 0.012, 'สายฝักบัวสแตนเลส 1.20 ม. (ช่วงบน)', mat='BIM-สแตนเลส')
    # ก๊อกน้ำระเบียง 1 ตัว +0.60 (ด้านระเบียงของผนัง B5)
    n3_chrome(f'{P}-BTP', [x_b5b, y_s, FF + 0.60], [x_b5b - 0.08, y_s, FF + 0.60], 0.022, 'ก๊อกน้ำระเบียง (ก๊อกบอลสนาม ชุบโครเมียม) 1/2" +0.60',
              qty=dict(type='ก๊อกน้ำติดผนัง', size='1/2"'))
    n3_chrome(f'{P}-BTP-S', [x_b5b - 0.08, y_s, FF + 0.60], [x_b5b - 0.08, y_s, FF + 0.54], 0.018, 'ปากก๊อกน้ำระเบียง')
    # สายตะวันออก: ผนัง BAL → มุมผนังชาร์ฟ ลง +0.55 → วาล์วอ่าง → ผนัง SH2 → ผนังกริด 4 → สต็อปวาล์วชักโครก +0.20
    y_lv = (min(lys) + max(lys)) / 2 - 0.10
    y_wv = min(wys) - 0.07
    n3_wroute(f'{P}-E', [[x_sh, y_bal, zJ], [x_sh, y_sh2, FF + 0.55], [x_g4, y_sh2, FF + 0.55],
                         [x_g4, y_wv, FF + 0.55], [x_g4, y_wv, FF + 0.20], [10.45, y_wv, FF + 0.20]], '1/2', 'ท่อน้ำดีฝังผนัง สายอ่าง/ชักโครก')
    n3_wfit(f'{P}-E-TE', [x_sh, y_lv, FF + 0.55], '1/2', 'สามทาง')
    n3_wpipe(f'{P}-E-LV', [x_sh - 0.0171, y_lv, FF + 0.55], [max(lxs), y_lv, FF + 0.55], '1/2', 'ท่อน้ำดีออกวาล์วอ่างล้างหน้า')
    n3_chrome(f'{P}-LAVV', [max(lxs), y_lv, FF + 0.55], [max(lxs) - 0.06, y_lv, FF + 0.55], 0.03, 'วาล์วเปิดปิดน้ำอ่างล้างหน้า (angle valve) +0.55',
              qty=dict(type='angle valve', size='1/2"'))
    n3_chrome(f'{P}-LAVS', [max(lxs) - 0.06, y_lv, FF + 0.55], [max(lxs) - 0.12, y_lv + 0.05, FF + 0.80], 0.010, 'สายน้ำดีถัก 1/2" วาล์ว → ก๊อกอ่าง', mat='BIM-สแตนเลส')
    # ก๊อกล้างห้องในห้องน้ำ ใต้อ่างล้างหน้า เยื้องจากขาอ่างไปทางผนังประตู ให้ท่อน้ำดีลงได้ (ผู้ใช้สั่ง 23 พ.ย. 2569; สูง +0.40 ผมกำหนด)
    y_ct = min(lys) + 0.05
    n3_wfit(f'{P}-E-TE2', [x_sh, y_ct, FF + 0.55], '1/2', 'สามทาง')
    n3_wpipe(f'{P}-E-CT1', [x_sh, y_ct, FF + 0.55 - 0.0171], [x_sh, y_ct, FF + 0.40 + 0.0171], '1/2', 'ท่อน้ำดีฝังผนัง ลงก๊อกล้างห้อง')
    n3_wfit(f'{P}-E-EL-CT', [x_sh, y_ct, FF + 0.40], '1/2', 'ข้องอ 90°')
    n3_wpipe(f'{P}-E-CT2', [x_sh - 0.0171, y_ct, FF + 0.40], [max(lxs), y_ct, FF + 0.40], '1/2', 'ท่อน้ำดีออกก๊อกล้างห้อง')
    n3_chrome(f'{P}-CTP', [max(lxs), y_ct, FF + 0.40], [max(lxs) - 0.08, y_ct, FF + 0.40], 0.022, 'ก๊อกล้างห้อง (ก๊อกบอลสนาม ชุบโครเมียม) 1/2" ใต้อ่างล้างหน้า +0.40',
              qty=dict(type='ก๊อกน้ำติดผนัง', size='1/2"'))
    n3_chrome(f'{P}-CTP-S', [max(lxs) - 0.08, y_ct, FF + 0.40], [max(lxs) - 0.08, y_ct, FF + 0.34], 0.018, 'ปากก๊อกล้างห้อง')
    n3_chrome(f'{P}-WCV', [10.45, y_wv, FF + 0.20], [10.39, y_wv, FF + 0.20], 0.03, 'สต็อปวาล์วชักโครก (angle valve) +0.20', qty=dict(type='angle valve', size='1/2"'))
    n3_chrome(f'{P}-WCS', [10.39, y_wv, FF + 0.20], [10.40, y_wv + 0.10, FF + 0.25], 0.010, 'สายน้ำดีถัก 1/2" สต็อปวาล์ว → ถังพักชักโครก', mat='BIM-สแตนเลส')
ASSUMPTIONS.append('ท่อน้ำดีห้องน้ำแนว N3 (23 พ.ย. 2569): PVC ชั้น 13.5 (ผู้ใช้) ท่อหลังมิเตอร์ 1/2" (ผู้ใช้) จากมิเตอร์หน้าห้องฝังพื้นทับหน้าแนวริมเสา C1-4B ขึ้นในผนังแนวช่องชาร์ฟ (ผู้ใช้) ถึง +0.55 แล้วแยก 1/2" ฝังผนัง (ท่อในผนังห้องน้ำ 1/2" ทั้งหมด ผู้ใช้) สายฝักบัวขึ้นไปเดิน +2.30 เหนือวงกบประตู (ผมกำหนด); '
                   'ฝักบัวทั่วไปราคาไม่สูง = สต็อปวาล์ว +1.10 + ฝักบัวสายอ่อนแขวนขอ +1.80 ที่ผนัง B5 (ผนังร่วมระเบียง) ตรงหน้าชักโครก (ผู้ใช้กำหนดตำแหน่ง); ก๊อกระเบียง 1 ตัว +0.60 หลังผนังเดียวกัน; '
                   'วาล์วอ่าง +0.55, ก๊อกล้างห้องใต้อ่างเยื้องไปทางผนังประตู +0.40 (ผู้ใช้สั่ง, ความสูงผมกำหนด), สต็อปวาล์วชักโครก +0.20 ข้างชักโครก; ข้อต่อน้ำดีทำเอง (ไฟล์ตัวอย่างไม่มีขนาด 1/2"); ตัวมิเตอร์ไม่ได้เขียน')

# ---- ชุดมิเตอร์หน้าห้อง + ท่อเมนน้ำดีทางเดิน แถว N ชั้น 2–5 (ผู้ใช้สั่ง 23 พ.ย. 2569) ----
# ท่อเมน 1¼" PVC 13.5 ใต้ท้องคาน B2 แนว C 0.15 (ศูนย์ท่อ) ห่างหน้าเสา (ผิวฉาบ) 0.10 ฝั่งทางเดิน → สามทาง 1¼" ลงหน้าห้อง → ข้องอ → ข้อต่อลด 1¼"x1/2"
# → บอลวาล์ว (ก่อน) → มิเตอร์ 1/2" (4 หุน) +2.20 จากพื้นห้อง ยื่นพ้นหน้าผนังฝั่งทางเดิน → บอลวาล์ว (หลัง) → ข้องอเข้าผนัง → ท่อ 1/2" ฝังผนังลงพื้น → ข้องอ → ฝังพื้นเข้าห้อง
# มิเตอร์อยู่หน้าห้องฝั่งตรงข้ามประตู ริมเสา; จุดยึดท่อเมนทุกคาน B2 หน้าห้อง; ปลายท่อเมนที่ผนังกริด 1 ต่อท่อแนวดิ่ง 2" (ปลายล่างปิด รอต่อระบบปั๊ม)
WOD.update({'1 1/4': (0.0422, 0.0025), '2': (0.0603, 0.0030)})   # ชั้น 13.5 ค่าประมาณ
NW_ROOMS = (1, 2, 3, 5, 6, 7, 8, 9)
y_cf = 8.49                                       # ผิวฉาบเสา C ฝั่งทางเดิน (json)
y_mn = y_cf - 0.10                                # แนวศูนย์ท่อเมน
y_wf = 8.485                                      # ผิวฉาบผนังหน้าห้องฝั่งทางเดิน
y_wc = 8.535                                      # แนวท่อฝังกลางผนังหน้าห้อง
y_rf = _YM - (GY['C'] + 0.165)                    # ผิวฉาบผนังหน้าห้องด้านในห้อง
x_r = 0.13                                        # ท่อแนวดิ่ง 2" ที่ผนังกริด 1 (พ้นคาน B1-1-CD)
NW_MT = {}


def water_row(side, ROOMS):
    """ชุดมิเตอร์หน้าห้อง + ท่อเมนทางเดิน + จุดยึด + ท่อแนวดิ่ง 2" ที่กริด 1 ของแถว N หรือ S
    เขียนพิกัดเป็นแถว N (json) แล้วสะท้อนแกน y รอบแนวกลางทางเดิน (y' = 15.50 − y) สำหรับแถว S (อาคารสมมาตร)"""
    Y = (lambda v: v) if side == 'N' else (lambda v: round(GY['F'] - v, 6))
    J3 = lambda p: [p[0], Y(p[1]), p[2]]

    def bx(eid, x0, y0, x1, y1, z0, t, nm, **kw):
        y0, y1 = Y(y0), Y(y1)
        if side == 'S':
            y0, y1 = sorted((y0, y1))
        n3_box(eid, x0, y0, x1, y1, z0, t, nm, **kw)

    wpipe = lambda eid, p, q, sz, nm: n3_wpipe(eid, J3(p), J3(q), sz, nm)
    wfit = lambda eid, p, sz, nm: n3_wfit(eid, J3(p), sz, nm)
    chrome = lambda eid, p, q, d, nm, **kw: n3_chrome(eid, J3(p), J3(q), d, nm, **kw)
    wroute = lambda pref, pts, sz, nm: n3_wroute(pref, [J3(p) for p in pts], sz, nm)
    W = f'{side}W'
    for f in (2, 3, 4, 5):
        P = f'PB-{W}-F{f}'
        zMn = FL[f] + 3.20 - 0.60 - 0.15               # ท้องคาน B2 ชั้นบน − 0.15 (ชั้น 5 ไม่มีคานบน ใช้ระดับเดียวกัน)
        zMt = FL[f] + 2.20
        zFl = FL[f] - 0.025
        h12, h114, h2 = (WOD[s][0] / 2 + 0.006 for s in ('1/2', '1 1/4', '2'))
        tees = []
        for k in ROOMS:
            door = next(e for e in elements if e['id'] == f'W-F{f}-{side}{k}-COR-O1')
            dxs = [q[0] for q in door['geom']['poly']]
            xl, xr = GX[k - 1], GX[k]
            dc = (min(dxs) + max(dxs)) / 2
            x_m = xr - 0.20 if dc < (xl + xr) / 2 else xl + 0.20   # ริมเสาฝั่งตรงข้ามประตู
            s = 1 if x_m > (xl + xr) / 2 else -1                   # ทิศจากท่อดิ่งไปหามิเตอร์/เสา
            x_d = x_m - s * 0.53
            NW_MT[(side, f, k)] = x_m
            R = f'PB-{side}{k}-F{f}-MT'
            tees.append(x_d)
            # ท่อดิ่ง 1¼" จากสามทางบนเมน → ข้องอ → ข้อต่อลด → วาล์ว → มิเตอร์ → วาล์ว → ข้องอเข้าผนัง
            wfit(f'{R}-TE', [x_d, y_mn, zMn], '1 1/4', 'สามทาง')
            wpipe(f'{R}-P1', [x_d, y_mn, zMn - h114], [x_d, y_mn, zMt + h114], '1 1/4', 'ท่อน้ำดีลงมิเตอร์หน้าห้อง')
            wfit(f'{R}-EL1', [x_d, y_mn, zMt], '1 1/4', 'ข้องอ 90°')
            bx(f'{R}-RD', min(x_d + s * h114, x_d + s * 0.10), y_mn - 0.019, max(x_d + s * h114, x_d + s * 0.10), y_mn + 0.019, zMt - 0.019, 0.038,
               'ข้อต่อลด PVC 1¼"x1/2" ก่อนเข้ามิเตอร์', qty=dict(type='ข้อต่อลด', size='1¼"x1/2"'))
            elements[-1]['material'] = 'BIM-ท่อน้ำดี PVC ฟ้า'
            chrome(f'{R}-V1', [x_d + s * 0.10, y_mn, zMt], [x_d + s * 0.185, y_mn, zMt], 0.034, 'บอลวาล์วทองเหลือง 1/2" ก่อนมิเตอร์', qty=dict(type='บอลวาล์ว', size='1/2"'))
            bx(f'{R}-V1H', x_d + s * 0.1425 - 0.008, y_mn - 0.008, x_d + s * 0.1425 + 0.008, y_mn + 0.008, zMt + 0.017, 0.035, 'ด้ามบอลวาล์ว')
            elements[-1]['material'] = 'BIM-โครเมียม'
            x0, x1 = sorted((x_d + s * 0.19, x_d + s * 0.38))
            bx(f'{R}', x0, y_mn - 0.045, x1, y_mn + 0.045, zMt - 0.045, 0.09, 'มิเตอร์น้ำ 1/2" (4 หุน) หน้าห้อง +2.20 ยื่นพ้นหน้าผนังฝั่งทางเดิน',
               qty=dict(type='มิเตอร์น้ำ', size='1/2"'))
            elements[-1]['material'] = 'BIM-สแตนเลส'
            chrome(f'{R}-DL', [(x0 + x1) / 2, y_mn, zMt + 0.045], [(x0 + x1) / 2, y_mn, zMt + 0.065], 0.07, 'หน้าปัดมิเตอร์น้ำ')
            chrome(f'{R}-V2', [x_d + s * 0.385, y_mn, zMt], [x_d + s * 0.47, y_mn, zMt], 0.034, 'บอลวาล์วทองเหลือง 1/2" หลังมิเตอร์', qty=dict(type='บอลวาล์ว', size='1/2"'))
            bx(f'{R}-V2H', x_d + s * 0.4275 - 0.008, y_mn - 0.008, x_d + s * 0.4275 + 0.008, y_mn + 0.008, zMt + 0.017, 0.035, 'ด้ามบอลวาล์ว')
            elements[-1]['material'] = 'BIM-โครเมียม'
            wpipe(f'{R}-P2', [x_d + s * 0.47, y_mn, zMt], [x_m - s * h12, y_mn, zMt], '1/2', 'ท่อน้ำดีหลังมิเตอร์')
            # ข้องอเข้าผนัง → ฝังผนังลงพื้น → ข้องอ → ฝังพื้นเข้าห้อง
            # ห้องที่ห้องน้ำอยู่ฝั่งเดียวกับมิเตอร์: ต่อเข้าแนวท่อในพื้น (PB-*-F*-CW-M) ตรงจากข้องอโคนผนัง
            # ห้องที่ห้องน้ำอยู่ฝั่งประตู: เดินท่อในพื้นเข้าห้อง 0.15 แล้วข้องอเลียบผนังหน้าห้องไปฝั่งห้องน้ำ (ต่อในบล็อกท่อห้องน้ำ)
            same = wc_geo(k - 1, side, f)['dr'] == -1
            wroute(f'{R}-W', [[x_m, y_mn, zMt], [x_m, y_wc, zMt], [x_m, y_wc, zFl], [x_m, y_rf + 0.15, zFl]], '1/2',
                   'ท่อน้ำดีหลังมิเตอร์ ฝังผนังหน้าห้อง → ฝังพื้นเข้าห้อง')
            if same:
                elements.pop()
            wfit(f'{R}-W-EL0', [x_m, y_mn, zMt], '1/2', 'ข้องอ 90°')
            if not same:
                wfit(f'{R}-W-EL3', [x_m, y_rf + 0.15, zFl], '1/2', 'ข้องอ 90°')
        # ท่อเมน 1¼" จากท่อแนวดิ่งที่กริด 1 → สามทางหน้าห้องทุกห้อง → ปลายปิด
        xs = sorted(tees)
        x_end = xs[-1] + 0.15
        pts = [x_r] + xs + [x_end]
        for j in range(len(pts) - 1):
            a = pts[j] + (h2 if j == 0 else h114)
            b = pts[j + 1] - (h114 if j + 1 < len(pts) - 1 else h114)
            wpipe(f'{P}-MN{j+1}', [a, y_mn, zMn], [b, y_mn, zMn], '1 1/4', 'ท่อเมนน้ำดีทางเดิน ใต้คาน B2')
        wfit(f'{P}-MN-CAP', [x_end, y_mn, zMn], '1 1/4', 'ฝาครอบปิดปลายท่อเมน')
        # จุดยึดท่อเมน: ทุกคาน B2 หน้าห้อง (กลางช่วงคาน เลี่ยงสามทาง) เพลท PL8x150x150 ยิงพุก 4-M12 ข้างคาน + เหล็กฉาก L50x5 ห้อยลง + แขนรับใต้ท่อ + ห่วงรัดท่อ
        # ชั้น 5 ไม่มีคานบน → ยึดผนังหน้าห้องฝั่งทางเดินแทน
        zSo = zMn + 0.15
        for i in range(1, 10):
            xa, xb = GX[i - 1] + 0.175, GX[i] - 0.175
            if xa > x_end:
                continue
            xh = (xa + max(xb, xa)) / 2
            xh = min(xh, x_end - 0.20)
            while any(abs(xh - t) < 0.15 for t in tees):
                xh += 0.20
            Q = f'{P}-SUP{i}'
            yp = y_cf + 0.005 if f < 5 else y_wf     # ผิวคาน (ฉาบ) / ผิวผนัง
            if side == 'N' and f == 5 and i == 4:    # ชั้น 5 หน้าโถงบันไดไม่มีผนัง → ยึดหน้าเสา C1-5C แทน
                xh, yp = GX[4], y_cf
            zp0 = zSo if f < 5 else zMn + 0.05
            bx(f'{Q}-PL', xh - 0.075, yp - 0.008, xh + 0.075, yp, zp0, 0.15, 'เพลทเหล็ก PL8x150x150 ยิงพุก 4-M12 ' + ('ข้างคาน B2' if f < 5 else 'ผนังหน้าห้อง (ชั้น 5 ไม่มีคานบน)'),
               qty=dict(type='เพลทเหล็ก PL8x150x150 + พุก M12', size='150x150x8', bolts=4))
            elements[-1]['material'] = 'BIM-เหล็กชุบกัลวาไนซ์'
            zb = zMn - WOD['1 1/4'][0] / 2 - 0.005     # ผิวบนแขนรับ = ใต้ท่อ (เผื่อยาง)
            bx(f'{Q}-L1', xh - 0.025, yp - 0.013, xh + 0.025, yp - 0.008, zb - 0.005, zp0 + 0.075 - zb + 0.005, 'เหล็กฉาก L50x5 ห้อยลง เชื่อมกับเพลท',
               qty=dict(type='เหล็กฉาก L50x50x5', length=round(zp0 + 0.075 - zb + 0.005, 3)))
            elements[-1]['material'] = 'BIM-เหล็กชุบกัลวาไนซ์'
            bx(f'{Q}-L2', xh - 0.025, y_mn - 0.04, xh + 0.025, yp - 0.013, zb - 0.005, 0.005, 'เหล็กฉาก L50x5 แขนรับใต้ท่อเมน',
               qty=dict(type='เหล็กฉาก L50x50x5', length=round(yp - 0.013 - y_mn + 0.04, 3)))
            elements[-1]['material'] = 'BIM-เหล็กชุบกัลวาไนซ์'
            od = WOD['1 1/4'][0]
            m = member(_J([xh - 0.0125, Y(y_mn), zMn]), _J([xh + 0.0125, Y(y_mn), zMn]), od + 0.012, od + 0.012)
            m.update(shape='POLY', poly2d=_circ(od / 2 + 0.006), hole2d=_circ(od / 2 + 0.001))
            add(f'{Q}-CL', 'สุขาภิบาล', 1, 'A07', m, name='ห่วงรัดท่อเหล็กชุบกัลวาไนซ์ บุยาง 1¼" ยึดกับแขนเหล็กฉาก', assumed=True, qty=dict(type='ห่วงรัดท่อ', size='1¼"'))
            elements[-1]['material'] = 'BIM-เหล็กชุบกัลวาไนซ์'
    # ท่อแนวดิ่ง 2" ที่ผนังกริด 1: ปลายล่างใต้พื้นชั้น 2 ปิดไว้รอต่อระบบปั๊ม → สามทางลด 2"x1¼" ทุกชั้น 2–4 → ชั้น 5 ข้องอ
    zR = [FL[f] + 2.45 for f in (2, 3, 4, 5)]
    hb2 = WOD['2'][0] / 2 + 0.006
    zbot = FL[2] - SLAB_T - 0.30
    wfit(f'PB-{W}-RS-CAP', [x_r, y_mn, zbot], '2', 'ฝาครอบปิดปลายท่อ (รอต่อระบบปั๊ม)')
    zc = zbot
    for j, z in enumerate(zR):
        wpipe(f'PB-{W}-RS-P{j+1}', [x_r, y_mn, zc + hb2], [x_r, y_mn, z - hb2], '2', 'ท่อแนวดิ่งจ่ายน้ำแต่ละชั้น ผนังกริด 1')
        wfit(f'PB-{W}-RS-T{j+2}', [x_r, y_mn, z], '2', 'สามทางลด 2"x1¼"' if j < 3 else 'ข้องอ 90° + ข้อต่อลด 2"x1¼"')
        zc = z


water_row('N', NW_ROOMS)
water_row('S', tuple(range(1, 10)))  # แถว S ทุกห้อง (ผู้ใช้เลือก 24 พ.ย. 2569)
ASSUMPTIONS.append('ชุดมิเตอร์หน้าห้อง + ท่อเมนทางเดินแถว N ชั้น 2–5 (ผู้ใช้สั่ง 23 พ.ย. 2569): เมน 1¼" PVC 13.5 ใต้ท้องคาน 0.15 ห่างหน้าเสา 0.10 (ศูนย์ท่อ), ลด 1¼"x1/2" ก่อนมิเตอร์, '
                   'มิเตอร์ 1/2" +2.20 ฝั่งทางเดินริมเสาฝั่งตรงข้ามประตู, บอลวาล์วก่อน/หลัง, หลังมิเตอร์ 1/2" ฝังผนังลงพื้นเข้าห้อง, ท่อแนวดิ่ง 2" ที่ผนังกริด 1 ปลายล่างปิดรอต่อปั๊ม (ผู้ใช้); '
                   'ระยะชุดมิเตอร์/วาล์ว ขนาดมิเตอร์ 0.19x0.09x0.09, ตำแหน่งจุดยึดกลางช่วงคาน 1 จุด/คาน, ชั้น 5 ยึดผนัง (หน้าโถงบันไดยึดหน้าเสา C1-5C), ปลายล่างท่อแนวดิ่ง 0.30 ใต้พื้นชั้น 2, ห้องอื่นนอกจาก N3 ปิดปลายท่อในห้องรอต่อ (ผมกำหนด)')

# ตัดท่อดิ่งทุกแนว (N3 + แนวอื่นที่ทำตาม N3) เป็นท่อนตามข้อต่อ (ท่อนล่างสุดคงรหัสเดิม) — ระดับข้อต่อเท่ากันทุกห้อง
WC_ROOMS = [f'{sd}{i+1}' for sd in ('N', 'S') for i in range(9) if not (sd == 'N' and i == STAIR_BAY[0])]
for RM, k in ((rm, k) for rm in WC_ROOMS for k in N3_CUTS):
    cuts = N3_CUTS[k]
    e = next(x for x in elements if x['id'] == f'PB-{RM}-{k}'); g = e['geom']
    lo, hi = sorted((g['p0'][2], g['p1'][2]))
    x0, y0 = g['p0'][0], g['p0'][1]
    segs, z = [], lo
    for zc, ub, db in sorted(cuts):
        segs.append((z, zc - db)); z = zc + ub
    segs.append((z, hi))
    g['p0'] = [x0, y0, round(segs[0][0], 4)]; g['p1'] = [x0, y0, round(segs[0][1], 4)]
    e['qty']['length'] = round(segs[0][1] - segs[0][0], 3)
    for j, (a, b) in enumerate(segs[1:], 2):
        m = dict(e['geom']); m['p0'] = [x0, y0, round(a, 4)]; m['p1'] = [x0, y0, round(b, 4)]
        add(f'PB-{RM}-{k}-{j:02d}', 'สุขาภิบาล', 2, 'A07', m, name=e['name'].split(' แนวดิ่ง')[0] + f' แนวดิ่งในช่องชาร์ฟ ห้อง {RM} ท่อนที่ {j}', assumed=True,
            qty=dict(e['qty'], length=round(b - a, 3)))
for _e in elements:
    if re.match(r'^PB-N3-F\d-SUP-', _e['id']):
        _e['material'] = 'BIM-เหล็กชุบกัลวาไนซ์'

# ---- ระบบท่อห้องน้ำทุกห้อง N+S ทำตามแนว N3 (ผู้ใช้เลือก "ทุกห้อง N+S" 24 พ.ย. 2569) ----
# ห้องน้ำทุกห้องเป็นภาพสะท้อน/เลื่อนของ N3 (ตรวจแล้ว: ระยะผนัง B5, ชักโครก, อ่าง เทียบผนังกริดและผนังนอกเท่ากันทุกห้อง)
# x' = xg' − dr'·(x − xg_N3)  (dr_N3 = −1),  y' = yo' + s'·(y − yo_N3)  (พิกัดโมเดล ก่อนกลับแกน y)
import copy as _copy
_g3 = wc_geo(2, 'N', 2)


def _wc_xf(side, i):
    g = wc_geo(i, side, 2)
    fx = lambda x: round(g['xg'] - g['dr'] * (x - _g3['xg']), 4)
    fy = lambda y: round(g['yo'] + g['s'] * (y - _g3['yo']), 4)
    return fx, fy, -g['dr'], g['s']                          # สเกลแกน x, y (±1)


def _xf_geom(gm, fx, fy, sx, sy):
    t = gm['type']
    if t == 'member':
        for k in ('p0', 'p1'):
            gm[k] = [fx(gm[k][0]), fy(gm[k][1]), gm[k][2]]
        if gm.get('path'):
            gm['path'] = [[fx(q[0]), fy(q[1]), q[2]] for q in gm['path']]
    elif t == 'prism':
        gm['poly'] = [[fx(x), fy(y)] for x, y in gm['poly']]
        if sx * sy < 0:
            gm['poly'] = gm['poly'][::-1]
    elif t == 'multi':
        for q in gm['parts']:
            _xf_geom(q, fx, fy, sx, sy)
    else:
        raise ValueError(t)


_N3_SRC = [e for e in elements if re.match(r'^PB-N3-F\d-', e['id']) and not re.match(r'^PB-N3-F\d-MT', e['id'])]
_wc_new = []
for side in ('N', 'S'):
    for i in range(9):
        RM = f'{side}{i+1}'
        if RM == 'N3' or (side == 'N' and i == STAIR_BAY[0]):
            continue
        fx, fy, sx, sy = _wc_xf(side, i)
        same = wc_geo(i, side, 2)['dr'] == -1               # ห้องน้ำอยู่ฝั่งเดียวกับมิเตอร์
        for e0 in _N3_SRC:
            if not same and re.match(r'^PB-N3-F\d-CW-M-P1$', e0['id']):
                continue                                     # ห้องน้ำฝั่งประตู: ท่อช่วงแรกเดินใหม่จากมิเตอร์ (ด้านล่าง)
            e = _copy.deepcopy(e0)
            e['id'] = e['id'].replace('PB-N3-', f'PB-{RM}-', 1)
            e['name'] = e['name'].replace('ห้อง N3', f'ห้อง {RM}')
            _xf_geom(e['geom'], fx, fy, sx, sy)
            if 'fitting' in e:
                F = e['fitting']
                F['origin'] = [fx(F['origin'][0]), fy(F['origin'][1]), F['origin'][2]]
                F['x'] = [round(F['x'][0] * sx, 5) + 0.0, round(F['x'][1] * sy, 5) + 0.0, F['x'][2]]
                F['y'] = [round(F['y'][0] * sx, 5) + 0.0, round(F['y'][1] * sy, 5) + 0.0, F['y'][2]]
            _wc_new.append(e)
        if not same:
            # มิเตอร์อยู่ฝั่งตรงข้ามห้องน้ำ: ท่อ 1/2" ฝังพื้นเลียบผนังหน้าห้อง (ห่างผิวผนัง 0.15) จากข้องอใต้มิเตอร์ → ข้องอริมเสาฝั่งห้องน้ำ → ข้องอเดิมของแนว N3
            h = WOD['1/2'][0] / 2 + 0.006
            ctr = lambda e: ((min(q[0] for q in e['geom']['poly']) + max(q[0] for q in e['geom']['poly'])) / 2,
                             (min(q[1] for q in e['geom']['poly']) + max(q[1] for q in e['geom']['poly'])) / 2)
            for f in (2, 3, 4, 5):
                xc_, ybal = ctr(next(x for x in _wc_new if x['id'] == f'PB-{RM}-F{f}-CW-M-EL1'))       # พิกัดโมเดล
                xm_, yq = ctr(next(x for x in elements if x['id'] == f'PB-{RM}-F{f}-MT-W-EL3'))
                zFl = FL[f] - 0.025
                n = len(elements)
                n3_wroute(f'PB-{RM}-F{f}-CW-M0', [[xm_, _YM - yq, zFl], [xc_, _YM - yq, zFl], [xc_, _YM - ybal, zFl]], '1/2',
                          'ท่อน้ำดี 4 หุน หลังมิเตอร์ ฝังพื้นเลียบผนังหน้าห้อง → ฝั่งห้องน้ำ')
                p = elements[n]['geom']; dx = 1 if p['p1'][0] > p['p0'][0] else -1
                p['p0'][0] = round(p['p0'][0] + dx * h, 4)
                q = elements[-1]['geom']; dy = 1 if q['p1'][1] > q['p0'][1] else -1
                q['p1'][1] = round(q['p1'][1] - dy * h, 4)
                for x in elements[n:]:
                    if x['geom']['type'] == 'member':
                        x['qty']['length'] = round(math.dist(x['geom']['p0'], x['geom']['p1']), 3)
                _wc_new.extend(elements[n:]); del elements[n:]
elements.extend(_wc_new)
ASSUMPTIONS.append('ระบบท่อห้องน้ำแนว N3 ชั้น 2–5 (23 พ.ย. 2569): ท่อดิ่งจัดใหม่ ส้วม 4" ฝั่งชักโครก น้ำทิ้ง 3" ฝั่งอ่าง อากาศ 2" ฝั่งคาน B2; '
                   'ชักโครกผ่านข้อต่อกันซึม SCG 4" (ใช้คอมโพเนนต์ PVC-TS-FLANG-100 แทน) ท่อ 4" ใต้พื้นลาด 1:50 เข้า TY-100; ระยะท่อออกชักโครก 0.305 จากผนังหลัง (สมมติ); '
                   'อ่าง P-trap 2" ท่อทะลุผนังชาร์ฟที่ +0.45 เข้า TYR-80x55; ฟลอร์เดรน PVC กันกลิ่นที่มุมห้องข้างฝักบัว (มุมผนัง B5 กับผนังนอก ขยับพ้นคาน B5/B4) ท่อ 3" ใต้พื้น 1:50 เข้า TY-80; '
                   'ท่ออากาศย่อย 2" จากท่อส้วม +1.10 และท่อน้ำทิ้ง +1.25 เข้าท่ออากาศด้วย TEE-55; ตัวยึดเหล็กฉาก L50x50x5 + เพลท PL8x150x150 ยิงพุก 4-M12 ข้างคาน B2/B3-4-AB เชื่อมเหล็กฉาก + ห่วงรัดท่อ ทุกชั้นใต้พื้น')
ASSUMPTIONS.append('ท่ออากาศถังบำบัดเข้าท่ออากาศอาคาร ยกเลิก (ผู้ใช้สั่ง); คอถังก่ออิฐฉาบ ช่อง ø0.60 นอก ø0.80 จากปากถังถึงผิวดิน + ฝาถัง (ขนาดสมมติ) (23 พ.ย. 2569)')
ASSUMPTIONS.append('ท่อระบายจากโคนท่อแนวดิ่งถึงถังบำบัด (23 พ.ย. 2569): น้ำทิ้ง 3" เข้าท่อส้วม 4" ด้วยวายลด 100x80 ที่ −0.15, ลงดินด้วยข้องอ 45° 2 ตัว เข้าท่อรวม ø150 ใต้ระเบียง (ห่างกริด A 0.60) ด้วยวายลด 150x100 ลาด 1:100 ช่องล้างต้นสาย → บ่อพัก MH 0.80 ห่างหน้าถัง 1.00 → ท่อ ø100 ลาด 1:50 เข้าถังแบบขนาน; ท่อออกจากถังรวมด้วยวายลดเป็น ø150 ลาด 1:100 ไปทางกริด 11 ปิดปลายเลยกริด 11 1.00 ม.; ระยะ A ท่อเข้าต่ำจากปากถัง 0.40 (สมมติ) ปากถังต่ำกว่าดิน → ต้องก่อคอถัง; ท่ออากาศถัง ø50 โผล่เหนือดิน 0.30 รอกำหนดแนวต่อขึ้นสูงกว่าอาคาร; ฝาปิดช่องล้างทำเอง (ไฟล์ตัวอย่างไม่มี); ระดับดิน ±0.00 ไม่มีในโมเดล')

# ---- ระบบท่อห้องน้ำชาย-หญิง ชั้น 1 + ซิงค์ล้างจานหลังร้านค้า 3 ร้าน (ผู้ใช้สั่ง 24 พ.ย. 2569) ----
# พิกัดในบล็อกนี้เป็นพิกัด elements.json (กลับแกน y แล้ว) แปลงด้วย _J/_JV ผ่าน n3_* เหมือนบล็อก N3
# ผู้ใช้ยืนยัน 24 พ.ย. 2569: ซิงค์ทั้ง 3 ร้าน (กริด 5–8) ชุดทั่วไปราคาไม่แพง, ก๊อกซิงค์ติดผนัง 1/2",
#   น้ำดีชั้น 1 แยกจากท่อดิ่ง 2" ผนังกริด 1 เดินเมนใต้ท้องพื้นชั้น 2, ชักโครก/โถปัสสาวะลงถังบำบัด (โซน 3),
#   อ่างล้างมือ/อ่างรวม/ฟลอร์เดรน/ซิงค์ลงท่อน้ำทิ้ง → ท่อรวม ø150 ใต้ระเบียง (โซน 2) ผ่านบ่อพักเดิม
F1_FF, F1_SB = FL[1] + 0.02, FL[1] - 0.10          # ผิวกระเบื้อง 0.32, ท้องพื้น GS-F1 0.20
_f1n = collections.Counter()
F1_EB = {(45, 50): ('PVC-EB-45-55.', 0.0145), (90, 50): ('PVC-EB-90-55', 0.030), (45, 80): ('PVC-EB-45-80', 0.021),
         (90, 80): ('PVC-EB-90-80', 0.044), (45, 100): ('PVC-EB-45-100', 0.025), (90, 100): ('PVC-EB-90-100', 0.057),
         (45, 150): ('PVC-EB-45-150', 0.038)}
F1_T = {'TY100': ('PVC-TY-100', 0.040, 0.123, 0.123, '4"'), 'TYR55': ('PVC-TYR-100x55', 0.027, 0.061, 0.087, '4"x2"'),
        'TEE55': ('PVC-TEE-55', 0.031, 0.031, 0.031, '2"')}
F1_Y = {(150, 100): ('PVC-YR-150x100', 0.000, 0.160, 0.178), (100, 80): ('PVC-YR-100x80', 0.015, 0.114, 0.127)}
F1_IN = {50: '2"', 80: '3"', 100: '4"', 150: '6"'}


def _f1id(pref, k):
    _f1n[pref + '|' + k] += 1
    return f'{pref}-{k}{_f1n[pref + "|" + k]:02d}'


def _ortho(X, Y):
    X = _unit(X)
    d = sum(X[i] * Y[i] for i in range(3))
    return _unit([Y[i] - d * X[i] for i in range(3)])


def f1_pipe(pref, p, q, size, nm):
    eid = _f1id(pref, 'P')
    n3_pipe(eid, p, q, SD_OD[size], SD_T[size], f'{nm} ø{F1_IN[size]} PVC ชั้น 8.5')
    elements[-1]['qty']['size'] = f'ø{size}'
    return eid


def f1_fit(pref, kind, dname, o, X, Y, nm, size):
    eid = _f1id(pref, kind)
    n3_fit(eid, dname, o, X, Y, nm, size)
    return eid


def f1_eb(pref, ang, size, o, a, b, nm=None):
    """ข้องอที่จุด o: ท่อเข้าทิศ a (ไหลเข้าหา o), ท่อออกทิศ b — คืนระยะปากข้อต่อ"""
    dname, dp = F1_EB[(ang, size)]
    if ang == 45:
        X, Y = _frame([-c for c in a], b, (-0.7071, 0.7071))
    else:
        X, Y = _frame([-c for c in a], b, (0.0, 1.0))
    f1_fit(pref, 'EB', dname, o, X, Y, nm or f'ข้องอ {ang}° ø{F1_IN[size]}', f'{F1_IN[size]}')
    return dp


def f1_route(pref, pts, size, nm, s0=0.0, s1=0.0):
    """ท่อผ่านจุด pts (ทิศการไหล) ข้องอ 45°/90° อัตโนมัติที่จุดหักมุม; ตัดปลายแรก s0 ปลายท้าย s1"""
    cur = _pt(pts[0], _unit(_v(pts[0], pts[1])), s0)
    for i in range(1, len(pts) - 1):
        a = _unit(_v(pts[i - 1], pts[i])); b = _unit(_v(pts[i], pts[i + 1]))
        ang = math.degrees(math.acos(max(-1, min(1, sum(a[k] * b[k] for k in range(3))))))
        k = 45 if 30 < ang < 60 else 90
        assert 30 < ang < 60 or 75 < ang < 105, (pref, i, ang)
        dp = f1_eb(pref, k, size, pts[i], a, b)
        f1_pipe(pref, cur, _pt(pts[i], a, -dp), size, nm)
        cur = _pt(pts[i], b, dp)
    a = _unit(_v(pts[-2], pts[-1]))
    f1_pipe(pref, cur, _pt(pts[-1], a, -s1), size, nm)


def f1_tee(pref, key, o, X, Yb, nm):
    """สามทาง (TY/TYR/TEE) ที่ o: X = ทิศการไหล, Yb = ทิศไปหาท่อแยก — คืน (ปากเข้า, ปากออก, ปากแยก, แกนแยก)"""
    dname, du, dd, db, sz = F1_T[key]
    X = _unit(X); Y = _ortho(X, Yb)
    f1_fit(pref, 'T', dname, o, X, Y, nm, sz)
    return _pt(o, X, -du), _pt(o, X, dd), _pt(o, Y, db), Y


def f1_yr(pref, key, o, flow, bdir, nm):
    """วายลด: ทางออกทิศ flow, ปากแยกชี้ไปทาง bdir (ทำมุม 135° กับ flow) — คืน (ปากเข้า, ปากออก, ปากแยก, แกนแยก)"""
    dname, do, di, db = F1_Y[key]
    X, Y = _frame(flow, bdir, (-0.7071, 0.7071))
    f1_fit(pref, 'Y', dname, o, X, Y, nm, f'{key[0]}x{key[1]}')
    br = [-0.7071 * X[i] + 0.7071 * Y[i] for i in range(3)]
    return _pt(o, X, -di), _pt(o, X, do), _pt(o, br, db), br


def f1_cap(pref, p, d, size, nm='ฝาปิดปลายท่อ (ปลั๊กอุด)'):
    od = SD_OD[size] + 0.012
    q = _pt(p, d, 0.03)
    m = member(_J(p), _J(q), od, od)
    m.update(shape='POLY', poly2d=_circ(od / 2))
    add(_f1id(pref, 'CAP'), 'สุขาภิบาล', 1, 'A07', m, name=f'{nm} ø{F1_IN[size]} PVC (ทำเอง ไม่มีในไฟล์ตัวอย่าง)', assumed=True,
        qty=dict(type='ฝาปิดปลายท่อ (ปลั๊ก)', size=f'ø{size}'))


def f1_sleeve(eid, y, z, x0, x1, size, nm):
    od = SD_OD[size]
    m = member(_J([x0, y, z]), _J([x1, y, z]), od, od)
    m.update(shape='POLY', poly2d=_circ(od / 2), hole2d=_circ(od / 2 - SD_T[size]))
    add(eid, 'สุขาภิบาล', 1, 'A07', m, name=nm, assumed=True, qty=dict(type='ท่อปลอก', size=f'ø{size}', length=round(abs(x1 - x0), 3)))


def f1_drop(pref, c, size, z_top, b, nm):
    """ข้องอ 90° ที่ c (ใต้ดิน): ปากบนรับท่อดิ่งจาก z_top, ปากราบออกทิศ b — คืนจุดปากราบ"""
    dname, dp = F1_EB[(90, size)]
    f1_fit(pref, 'EB', dname, c, [0, 0, 1], _ortho([0, 0, 1], b), f'ข้องอ 90° ø{F1_IN[size]}', f'{F1_IN[size]}')
    f1_pipe(pref, [c[0], c[1], c[2] + dp], [c[0], c[1], z_top], size, nm)
    return _pt(c, _ortho([0, 0, 1], b), dp)


def _hdir(p, q, s):
    """ทิศจาก p ไป q ในแปลน ลาดขึ้น s (ใช้ตอนเดินย้อนจากปากข้อต่อขึ้นต้นน้ำ)"""
    L = math.hypot(q[0] - p[0], q[1] - p[1])
    return _unit([(q[0] - p[0]) / L, (q[1] - p[1]) / L, s])


def _up(p, q, s):
    """จุด q ในแปลน ระดับสูงขึ้นจาก p ตามความลาด s"""
    return [q[0], q[1], p[2] + s * math.hypot(q[0] - p[0], q[1] - p[1])]


def f1_dz(p, s, x=None, y=None):
    """เลื่อนจุดในแนวราบไป x หรือ y (แกนเดียว) ลาดขึ้น s"""
    q = [p[0] if x is None else x, p[1] if y is None else y, 0]
    return _up(p, q, s)


S_BK, S_GR, S_BR = 0.02, 0.01, 0.02          # ลาด: ท่อส้วม 1:50, ท่อน้ำทิ้งรวม ø100 1:100, ท่อแยก 2"/3" 1:50

# ---------- 1) ท่อส้วมชาย/หญิงแยกเส้นกัน ไปเชื่อมกันหลังอาคาร มีช่องล้าง CO ที่จุดเชื่อม (วิวัฒน์ 24 พ.ย. 2569) ----
#   ท่อชาย ø4": เดินแนวท่อรวมเดิม x = 29.20 → ท่อปลอก ø200 คาน GB2-B → ลดระดับข้องอ 45° 2 ตัว → ข้อต่อลด 6"x4" → ท่อรวม ø150
#   ท่อหญิง ø4": แนว x = 30.45 ไหล +y → ท่อปลอก ø150 คาน GB2-B → ลดระดับ 45° → วายลด 150x100 บนท่อรวมแนวทแยงไปถัง
#   ช่องล้าง CO: วายลด 150x100 ปากแยกชี้ขึ้น ก่อนจุดเชื่อมท่อหญิง → ท่อ ø4" ขึ้นระดับดิน ฝาปิด; ในห้องน้ำมี FCO ที่ต้นสายทั้ง 2 เส้น
_z3old = {k: next(e for e in elements if e['id'] == k) for k in
          ('SD-Z3-EB01', 'SD-Z3-P01', 'SD-Z3-CAP01', 'SD-Z3-P02', 'SD-Z3-EB02', 'SD-Z3-P03', 'SD-Z3-EB03', 'SD-Z3-P04', 'SD-Z3-P05')}
_g = _z3old['SD-Z3-P02']['geom']
_a, _b = _J(_g['p0']), _J(_g['p1'])
_z3a, _z3b = (_a, _b) if _a[1] < _b[1] else (_b, _a)            # ต้นน้ำ (y น้อย) / ท้ายน้ำ (ปากข้องอ EB02)
S3 = (_z3a[2] - _z3b[2]) / (_z3b[1] - _z3a[1])
z3 = lambda y: _z3a[2] - S3 * (y - _z3a[1])
_fo = lambda k: _J(_z3old[k]['fitting']['origin'])
_K, _L = _fo('SD-Z3-EB02'), _fo('SD-Z3-EB03')                    # จุดลดระดับเดิม (หลังคาน GB2-B)
_E4 = _J(next(e for e in elements if e['id'] == 'SD-Z3-EB04')['fitting']['origin'])
_g = _z3old['SD-Z3-P05']['geom']
_p5a, _p5b = sorted((_J(_g['p0']), _J(_g['p1'])), key=lambda p: math.dist(p, _E4))
elements[:] = [e for e in elements if e['id'] not in _z3old]
elements[:] = [e for e in elements if e['id'] != 'SD-Z3-SLV1']      # ท่อส้วมชายไม่ลอดคาน GB2-B9-10 แล้ว (26 พ.ย. 2569)
X30 = 29.20
# ข้อต่อลด 6"x4" หลังข้องอลดระดับ (แกน z ท้องถิ่นของคอมโพเนนต์ชี้จากปาก ø150 ไปปาก ø100 = ทวนน้ำ)
f4 = _unit(_v(_L, _E4))
_R = _pt(_L, f4, 0.25)
f1_fit('SD-Z3N', 'RS', 'PVC-RS-150x100', _R, [1, 0, 0], _unit([0, -f4[2], f4[1]]), 'ข้อต่อตรงลด 6"x4" (ท่อส้วมชาย → ท่อรวม ø150)', '6"x4"')
_R100, _R150 = _pt(_R, f4, -0.170), _pt(_R, f4, -0.086)
f1_pipe('SD-Z3N', _R150, _pt(_E4, f4, -0.038), 150, 'ท่อรวม (โซน 3)')
# จุดเชื่อมท่อหญิงบนท่อรวมแนวทแยง (x = 30.45) และช่องล้าง CO ก่อนจุดเชื่อม
W_X = 30.45
f5 = _unit(_v(_p5a, _p5b))
_YWj = _pt(_p5a, f5, (W_X - _p5a[0]) / f5[0])
wi, wo, wbp, wbr = f1_yr('SD-Z3N', (150, 100), _YWj, f5, [0, -1, S_BK], 'วายลด 150x100 รับท่อส้วมห้องน้ำหญิง (หลังอาคาร โซน 3)')
_oC = _pt(_YWj, f5, -0.55)
ci, co_, cbp, cbr = f1_yr('SD-Z3N', (150, 100), _oC, f5, [0, 0, 1], 'วายลด 150x100 ช่องล้าง CO ท่อรวมหลังอาคาร (จุดเชื่อมท่อส้วมชาย/หญิง)')
_cE = _pt(cbp, cbr, 0.07)
f1_pipe('SD-Z3N', cbp, _pt(_cE, cbr, -0.025), 100, 'ท่อช่องล้าง CO')
dp = f1_eb('SD-Z3N', 45, 100, _cE, cbr, [0, 0, 1], 'ข้องอ 45° ø4" ช่องล้าง CO')
_cT = [_cE[0], _cE[1], -0.03]
f1_pipe('SD-Z3N', _pt(_cE, [0, 0, 1], dp), _cT, 100, 'ท่อช่องล้าง CO ขึ้นระดับดิน')
f1_cap('SD-Z3N', _cT, [0, 0, 1], 100, 'ฝาปิดช่องล้าง CO (คลีนเอาท์ PVC เกลียว)')
elements[-1]['qty']['type'] = 'ฝาปิดช่องล้าง CO'
f1_pipe('SD-Z3N', _p5a, ci, 150, 'ท่อรวม (โซน 3)')
f1_pipe('SD-Z3N', co_, wi, 150, 'ท่อรวม (โซน 3)')
f1_pipe('SD-Z3N', wo, _p5b, 150, 'ท่อรวม (โซน 3)')


def f1_sleeve_y(eid, x, z, y0, y1, size, nm):
    od = SD_OD[size]
    m = member(_J([x, y0, z]), _J([x, y1, z]), od, od)
    m.update(shape='POLY', poly2d=_circ(od / 2), hole2d=_circ(od / 2 - SD_T[size]))
    add(eid, 'สุขาภิบาล', 1, 'A07', m, name=nm, assumed=True, qty=dict(type='ท่อปลอก', size=f'ø{size}', length=round(abs(y1 - y0), 3)))


# ---------- 3b) ท่ออากาศ 2" ห้องน้ำชั้น 1 (วิวัฒน์ 24 พ.ย. 2569: เดินไว้ด้านหลังอาคาร ต่อเข้าท่ออากาศดิ่งห้อง N8/N9) ----
#   แยกจากท่อส้วมใต้พื้นด้วยสามทางลด 4"x2" ระหว่างชักโครกตัวต้นสายกับผนังแนว B → ท่อ 2" ใต้พื้นไปมุมห้อง → ท่อดิ่งชิดผนังแนว B
#   ขึ้นถึงระดับ +2.60 → ข้องอ 90° ลอดผนังแนว B ออกหลังอาคาร → เดินราบชิดผนังด้านนอก (y = 14.065) ลาดขึ้น 1:100 → สามทาง 2" บนท่อดิ่ง N8/N9
S_V, Z_V, Y_VS = 0.01, 2.60, 14.065
NM_V = 'ท่ออากาศห้องน้ำชั้น 1'


def f1_vent(pref, line_o, Xline, Yb, corner, x_stack, side, nm_room):
    """สามทางลด 4"x2" ที่ line_o บนท่อส้วม (ทิศการไหล Xline, ปากแยกไปทาง Yb ลาดขึ้น) → มุมห้อง corner → ขึ้นดิ่ง → ลอดผนัง B → ท่อดิ่ง x_stack"""
    ti, to, tb, tY = f1_tee(pref, 'TYR55', line_o, Xline, Yb, f'สามทางวายลด (TYR) 4"x2" แยกท่ออากาศ{nm_room}')
    zb = tb[2] + S_BK * abs(corner[0] - tb[0])
    c1 = [corner[0], tb[1], zb]
    c2 = [corner[0], corner[1], zb]
    c3 = [corner[0], corner[1], Z_V]
    c4 = [corner[0], Y_VS, Z_V + S_V * (Y_VS - corner[1])]
    zj = c4[2] + S_V * abs(x_stack - corner[0])
    st = next(e for e in elements if e['id'] == f'PB-{side}-VENT')
    g = st['geom']; a, b = _J(g['p0']), _J(g['p1'])
    lo, hi = (a, b) if a[2] < b[2] else (b, a)
    elements[:] = [e for e in elements if e['id'] != st['id']]
    sti, sto, stb, _ = f1_tee(f'PB-{side}-VENT-F1', 'TEE55', [x_stack, Y_VS, zj], [0, 0, 1], [corner[0] - x_stack, 0, 0],
                             f'สามทาง ø2" รับท่ออากาศ{nm_room} (ท่ออากาศดิ่งห้อง {side})')
    f1_pipe(f'PB-{side}-VENT-F1', lo, sti, 50, f'ท่ออากาศดิ่งห้อง {side} ชั้น 1')
    f1_pipe(f'PB-{side}-VENT-F1', sto, hi, 50, f'ท่ออากาศดิ่งห้อง {side} ชั้น 1')
    f1_route(pref, [tb, c1, c2, c3, c4, stb], 50, f'{NM_V} {nm_room}')
    return ti, to


# ---------- 2) ท่อส้วมห้องน้ำหญิง ø100 ลาด 1:50: FCO ต้นสาย → ชักโครก 3 ตัว (ท่อออกห่างหลังถังพัก 0.305) แนว x = 30.45 ไหล +y → หลังอาคาร ----
_wcW = {}
for j in (1, 2, 3):
    wc = next(e for e in elements if e['id'] == f'FX-F1-WC2-{j}')
    xs = [q[0] for q in wc['geom']['poly']]; ys = [_YM - q[1] for q in wc['geom']['poly']]
    _wcW[j] = (max(xs) - 0.305, round((min(ys) + max(ys)) / 2, 4))
Xw = _unit([0, 1, -S_BK])
NM_W = 'ท่อส้วมห้องน้ำหญิง ชั้น 1 ลาด 1:50 (โซน 3)'
_jW = sorted(_wcW, key=lambda j: _wcW[j][1])                    # ต้นน้ำก่อน (y น้อย)
_y0W = _wcW[_jW[0]][1]
wz = lambda y: 0.03 - S_BK * (y - _y0W)
_hW = [W_X, 10.62, wz(10.62)]                                     # FCO ต้นสาย ในห้องส้วม 3 หน้าชักโครก
prev_out = f1_drop('SD-F1W', _hW, 100, F1_FF - 0.03, [0, 1, 0], 'ท่อช่องล้างพื้น (FCO) ห้องน้ำหญิง')
f1_cap('SD-F1W', [W_X, _hW[1], F1_FF - 0.03], [0, 0, 1], 100, 'ฝาปิดช่องล้างพื้น FCO (คลีนเอาท์ PVC เกลียว)')
elements[-1]['qty']['type'] = 'ฝาปิดช่องล้างพื้น FCO'
for jj in _jW:
    xo, yo = _wcW[jj]
    o = [W_X, yo, wz(yo)]
    ti, to, tb, tY = f1_tee('SD-F1W', 'TY100', o, Xw, [1, 0, S_BK], f'สามทางวาย (TY) ø4" รับท่อชักโครกหญิง ห้อง {jj}')
    f1_pipe('SD-F1W', prev_out, ti, 100, NM_W)
    zE = tb[2] + S_BK * (xo - tb[0])
    n3_fit(f'SD-F1W-WC{jj}-SLV', 'PVC-TS-FLANG-100', [xo, yo, F1_SB], [1, 0, 0], [0, 1, 0], 'ข้อต่อกันซึม PVC 4" สีฟ้า SCG ใต้ชักโครก (ฝังในพื้น)', '4"')
    elements[-1]['qty'].update(brand='SCG', color='ฟ้า')
    p = f1_drop('SD-F1W', [xo, yo, zE], 100, F1_SB + 0.10, [-1, 0, 0], 'ท่อส้วมจากชักโครก ผ่านข้อต่อกันซึม')
    f1_pipe('SD-F1W', p, tb, 100, 'ท่อส้วมชักโครก ใต้พื้น ลาด 1:50 (โซน 3)')
    prev_out, last_o = to, o
# สามทางลดแยกท่ออากาศ → ลอดคาน GB2-B (ท่อปลอก ø150) → ข้องอ 45° 2 ตัวลดระดับหลังอาคาร → วายลดบนท่อรวม
_vW = [W_X, 13.62, wz(13.62)]
vti, vto = f1_vent('SD-F1V', _vW, Xw, [-1, 0, S_BK], [30.30, 13.71], 28.25, 'N9', 'ห้องน้ำหญิง')
f1_pipe('SD-F1W', prev_out, vti, 100, NM_W)
last_o = _vW
_D1 = [W_X, 14.30, wz(14.30)]
_Ld = (wbp[1] - _D1[1] - _D1[2] + wbp[2]) / (-wbr[1] - wbr[2])
_D2 = _pt(wbp, wbr, _Ld)
f1_route('SD-F1W', [last_o, _D1, _D2, wbp], 100, 'ท่อส้วมห้องน้ำหญิง ชั้น 1 → หลังอาคาร (โซน 3)', s0=0.061)
f1_sleeve_y('SD-F1W-SLV1', W_X, round(wz(13.85), 4), 13.75, 13.95, 150, 'ท่อปลอก PVC ø150 ฝังคานคอดิน GB2-B10 สำหรับท่อส้วม ø100 ห้องน้ำหญิง ชั้น 1')

# ---------- 3) ท่อส้วมห้องน้ำชาย ø100 ลาด 1:50 (วิวัฒน์ 26 พ.ย. 2569: เดินจากชักโครก 2 ตัวออกหลังอาคารก่อน แล้วไปรวมก่อนเข้าถัง)
#   FCO ต้นสาย y 11.45 → TYR รับท่อโถปัสสาวะ (y 11.70) → TY ชักโครก 2 ตัว → TYR ท่ออากาศ → ท่อปลอก ø150 คาน GB2-B8-9
#   → หลังอาคาร y 14.60 เลี้ยว 90° ราบทิศ +x → ดิ่งลงที่ x 29.20 → ข้อต่อลด 6"x4" (จุดเดิม) → ท่อรวม ø150 → CO → รวมท่อหญิง → ถัง Z3 ----
M_X = 25.25
_wcM = {}
for j in (1, 2):
    wc = next(e for e in elements if e['id'] == f'FX-F1-WC1-{j}')
    xs = [q[0] for q in wc['geom']['poly']]; ys = [_YM - q[1] for q in wc['geom']['poly']]
    _wcM[j] = (min(xs) + 0.305, round((min(ys) + max(ys)) / 2, 4))
Xm = _unit([0, 1, -S_BK])
NM_M = 'ท่อส้วมห้องน้ำชาย ชั้น 1 ลาด 1:50 (โซน 3)'
M_Y0, M_YU, M_Z, M_YB = 11.45, 11.70, -0.02, 14.60
mz = lambda y: M_Z - S_BK * (y - M_YU)
_hM = [M_X, M_Y0, mz(M_Y0)]                                      # FCO ต้นสาย
prev_out = f1_drop('SD-F1M', _hM, 100, F1_FF - 0.03, [0, 1, 0], 'ท่อช่องล้างพื้น (FCO) ห้องน้ำชาย')
f1_cap('SD-F1M', [M_X, M_Y0, F1_FF - 0.03], [0, 0, 1], 100, 'ฝาปิดช่องล้างพื้น FCO (คลีนเอาท์ PVC เกลียว)')
elements[-1]['qty']['type'] = 'ฝาปิดช่องล้างพื้น FCO'
ui, uo, ub, uY = f1_tee('SD-F1M', 'TYR55', [M_X, M_YU, mz(M_YU)], Xm, [-1, 0, S_BR], 'สามทางวายลด (TYR) 4"x2" รับท่อโถปัสสาวะ')
f1_pipe('SD-F1M', prev_out, ui, 100, NM_M)
prev_out = uo
for jj in (2, 1):                                                # ต้นน้ำก่อน (y น้อย)
    xo, yo = _wcM[jj]
    o = [M_X, yo, mz(yo)]
    ti, to, tb, tY = f1_tee('SD-F1M', 'TY100', o, Xm, [-1, 0, S_BK], f'สามทางวาย (TY) ø4" รับท่อชักโครกชาย ห้อง {jj}')
    f1_pipe('SD-F1M', prev_out, ti, 100, NM_M)
    zE = tb[2] + S_BK * (tb[0] - xo)
    n3_fit(f'SD-F1M-WC{jj}-SLV', 'PVC-TS-FLANG-100', [xo, yo, F1_SB], [1, 0, 0], [0, 1, 0], 'ข้อต่อกันซึม PVC 4" สีฟ้า SCG ใต้ชักโครก (ฝังในพื้น)', '4"')
    elements[-1]['qty'].update(brand='SCG', color='ฟ้า')
    p = f1_drop('SD-F1M', [xo, yo, zE], 100, F1_SB + 0.10, [1, 0, 0], 'ท่อส้วมจากชักโครก ผ่านข้อต่อกันซึม')
    f1_pipe('SD-F1M', p, tb, 100, 'ท่อส้วมชักโครก ใต้พื้น ลาด 1:50 (โซน 3)')
    prev_out = to
_vM = [M_X, 13.60, mz(13.60)]                                    # สามทางลดแยกท่ออากาศ
vti, vto = f1_vent('SD-F1V', _vM, Xm, [1, 0, S_BK], [25.50, 13.71], 27.75, 'N8', 'ห้องน้ำชาย')
f1_pipe('SD-F1M', prev_out, vti, 100, NM_M)
_A = [M_X, M_YB, mz(M_YB)]
_B = _up(_A, [X30, M_YB, 0], -S_BK)
_Q = [X30, M_YB, _R100[2] + f4[2] * (M_YB - _R100[1]) / f4[1]]
f1_route('SD-F1M', [vto, _A, _B, _Q, _R100], 100, 'ท่อส้วมห้องน้ำชาย ชั้น 1 → หลังอาคาร (โซน 3)')
f1_sleeve_y('SD-F1M-SLV1', M_X, round(mz(13.85), 4), 13.75, 13.95, 150, 'ท่อปลอก PVC ø150 ฝังคานคอดิน GB2-B8-9 สำหรับท่อส้วม ø100 ห้องน้ำชาย ชั้น 1')
# โถปัสสาวะ 3 โถ (กะรัต K-17392X): ท่อ 2" ดิ่งหลังโถ → ใต้พื้นแนว y = 10.47 ไหลทิศ −x → ข้องอ 90° ที่ x = 24.70 → แนว +y → ข้องอ 90° → TYR ต้นสายท่อส้วม
U_Y, U_X0 = 10.47, 24.70
NM_U = 'ท่อน้ำทิ้งโถปัสสาวะ ใต้พื้น ลาด 1:50 (โซน 3)'
u1 = _up(ub, [U_X0, ub[1], 0], S_BR)
u2 = _up(u1, [U_X0, U_Y, 0], S_BR)
u3 = f1_dz(u2, S_BR, x=24.84)
f1_route('SD-F1U', [u3, u2, u1, ub], 50, NM_U, s0=F1_T['TEE55'][2])
prev_in = None
for k, xu in enumerate((24.84, 25.64, 26.44)):                   # ท้ายน้ำก่อน
    o = f1_dz(u3, S_BR, x=xu)
    if k < 2:
        ti, to, tb, tY = f1_tee('SD-F1U', 'TEE55', o, _unit([-1, 0, -S_BR]), [0, 0, 1], f'สามทาง ø2" รับท่อดิ่งโถปัสสาวะ ตัวที่ {k + 1}')
        if k == 1:
            f1_pipe('SD-F1U', to, prev_in, 50, NM_U)
        zt = tb[2]
        prev_in = ti
    else:
        dname, dp = F1_EB[(90, 50)]
        f1_fit('SD-F1U', 'EB', dname, o, [0, 0, 1], [-1, 0, 0], 'ข้องอ 90° ø2"', '2"')
        f1_pipe('SD-F1U', _pt(o, [-1, 0, 0], dp), prev_in, 50, NM_U)
        zt = o[2] + dp
    zU = F1_FF + 0.35                                            # ท่อออกโถปัสสาวะ (วิวัฒน์ยืนยัน +0.35)
    f1_fit('SD-F1U', 'EB', 'PVC-EB-90-55', [xu, U_Y, zU], [0, 0, -1], [0, 1, 0], 'ข้องอ 90° ø2" รับท่อออกหลังโถปัสสาวะ', '2"')
    f1_pipe('SD-F1U', [xu, U_Y, zt], [xu, U_Y, zU - 0.030], 50, 'ท่อน้ำทิ้งโถปัสสาวะ ดิ่งหลังโถ')

# ---------- 4) ท่อน้ำทิ้งห้องน้ำ ø100 ลาด 1:100 ตื้นใต้ท้องพื้น (วิวัฒน์ 26 พ.ย. 2569: ประมาณ 20 ซม. ใต้ท้องพื้น ลอดคานคอดินด้วยท่อปลอก)
#   แนว x = 27.00 ไหล +y → ท่อปลอก ø150 คาน GB2-B → ข้องอ 90° ดิ่งลง → ทแยง 45° → วายลด 150x100 บนท่อรวมโซน 2 (x = 26.40) ----
def f1_header_y(zone_pref, x_y, flow_sgn, bdir, nm):
    """แทรกวายลด 150x100 บนท่อรวม ø150 ใต้ระเบียง (y json 14.90) ที่ x_y: แยกท่อเดิมเป็น 2 ท่อน — คืน (ปากแยก, แกนแยก)"""
    hy = round(_YM - SD_HY, 4)
    cand = [e for e in elements if re.match(rf'^{zone_pref}-P\d+$', e['id'])]
    for e in cand:
        a, b = _J(e['geom']['p0']), _J(e['geom']['p1'])
        if abs(a[1] - hy) < 1e-3 and abs(b[1] - hy) < 1e-3 and min(a[0], b[0]) < x_y - 0.2 and max(a[0], b[0]) > x_y + 0.2:
            break
    else:
        raise RuntimeError('header pipe not found ' + zone_pref)
    up_, dn_ = (a, b) if (b[0] - a[0]) * flow_sgn > 0 else (b, a)
    zf = lambda x: up_[2] + (dn_[2] - up_[2]) * (x - up_[0]) / (dn_[0] - up_[0])
    o = [x_y, hy, zf(x_y)]
    Xh = _unit(_v(up_, dn_))
    yi, yo_, ybp, ybr = f1_yr(zone_pref + '-F1', (150, 100), o, Xh, bdir, nm)
    g = e['geom']
    k_dn = 'p0' if _J(g['p0'])[0] == dn_[0] else 'p1'
    g[k_dn] = [round(c, 4) for c in _J(yi)]
    e['qty']['length'] = round(math.dist(up_, yi), 3)
    f1_pipe(zone_pref + '-F1', yo_, dn_, 150, 'ท่อรวม')
    elements[-1]['name'] = e['name']
    return ybp, ybr


gP, gbr = f1_header_y('SD-Z2E', 26.40, -1, _unit([0.7071, -0.7071, S_GR]), 'วายลด 150x100 รับท่อน้ำทิ้งห้องน้ำชาย-หญิง ชั้น 1')
G_X = 27.00
gD = _pt(gP, gbr, (G_X - gP[0]) / gbr[0])                       # จุดเลี้ยว 45° ล่าง (y ≈ 14.30)
Xg = _unit([0, 1, -S_GR])
G_YX, G_ZX = 10.10, -0.02                                       # ต้นสาย ศก.ท่อ ≈ 22 ซม. ใต้ท้องพื้น (ท่อส้วมชายไม่ขวางแล้ว 26 พ.ย. 2569)
zg = lambda y: G_ZX - S_GR * (y - G_YX)
gT = [G_X, gD[1], zg(gD[1])]                                    # ข้องอ 90° บน (หลังคาน GB2-B) → ดิ่งลงถึง gD
# จุดรับบนแนวท่อ (ทิศการไหล +y): (y, ชนิด, ทิศไปหาท่อแยก)
G_J = [(10.10, 'TYR55', [-1, 0, S_BR], 'อ่างล้างมือรวมห้องน้ำชาย (ต้นสาย)'),
       (10.40, 'TYR55', [1, 0, S_BR], 'อ่างล้างมือรวมห้องน้ำหญิง'),
       (11.10, 'YR80', [0.7071, -0.7071, S_BR], 'ฟลอร์เดรนห้องน้ำหญิง'),
       (11.40, 'YR80', [-0.7071, -0.7071, S_BR], 'ฟลอร์เดรนห้องน้ำชาย'),
       (12.52, 'TYR55', [1, 0, S_BR], 'อ่างล้างหน้าชาย-หญิง ตัวที่ 2'),
       (13.32, 'TYR55', [1, 0, S_BR], 'อ่างล้างหน้าชาย-หญิง ตัวที่ 1')]
G_BP = {}
prev_out = None
for yj, kind, bd, what in G_J:
    o = [G_X, yj, zg(yj)]
    if kind == 'YR80':
        pin, pout, pb, pbr = f1_yr('SD-F1G', (100, 80), o, Xg, _unit(bd), f'วายลด 100x80 รับท่อ{what}')
    else:
        pin, pout, pb, pbr = f1_tee('SD-F1G', kind, o, Xg, bd, f'สามทางวายลด (TYR) 4"x2" รับท่อ{what}')
    G_BP[yj] = (pb, pbr)
    if prev_out is None:
        f1_cap('SD-F1G', pin, [0, -1, 0], 100, 'ฝาปิดปลายท่อต้นสาย (ปลั๊กอุด)')
    else:
        f1_pipe('SD-F1G', prev_out, pin, 100, 'ท่อน้ำทิ้งห้องน้ำ ชั้น 1 ลาด 1:100 (ลงท่อรวมโซน 2)')
    prev_out = pout
f1_route('SD-F1G', [prev_out, gT, gD, gP], 100, 'ท่อน้ำทิ้งห้องน้ำ ชั้น 1 ลาด 1:100 (ลงท่อรวมโซน 2)')
f1_sleeve_y('SD-F1G-SLV1', G_X, round(zg(13.85), 4), 13.75, 13.95, 150, 'ท่อปลอก PVC ø150 ฝังคานคอดิน GB2-B8-9 สำหรับท่อน้ำทิ้ง ø100 ห้องน้ำชั้น 1')


def f1_slv9(eid, a, b, size, nm):
    """ท่อปลอกในคาน GB1-9-BC (x 27.90–28.10) บนท่อแนวราบ a→b ที่ y คงที่"""
    z = a[2] + (b[2] - a[2]) * (28.0 - a[0]) / (b[0] - a[0])
    f1_sleeve(eid, a[1], round(z, 4), 27.90, 28.10, {50: 80, 80: 100}[size], nm)


def f1_trough_waste(eid, x, y, nm):
    tr_top = F1_FF - 0.02 + 0.45
    n3_chrome(eid, [x, y, tr_top - 0.005], [x, y, tr_top + 0.005], 0.075, nm, qty=dict(type='สะดืออ่างสแตนเลส (อ่างล้างมือรวม)', size='ต่อท่อ 2"'), mat='BIM-สแตนเลส')
    return tr_top


def f1_fd(pref, x, y, nm):
    n3_box(f'{pref}-FD', x - 0.06, y - 0.06, x + 0.06, y + 0.06, F1_FF - 0.003, 0.006, nm,
           qty=dict(type='ฟลอร์เดรน PVC กันกลิ่น', size='ตะแกรง 4" ต่อท่อ 3"'))
    elements[-1]['material'] = 'BIM-สแตนเลส'


# 4a) อ่างล้างมือรวมห้องน้ำชาย: สะดืออ่าง x = 26.55 → ท่อ 2" ดิ่ง → ข้องอ 90° → TYR ต้นสาย (จากทิศ −x)
pb, pbr = G_BP[10.10]
c = _up(pb, [26.55, pb[1], 0], S_BR)
zt = f1_trough_waste('SD-F1G-TRM-WST', 26.55, pb[1], 'สะดืออ่างล้างมือรวม สแตนเลส ห้องน้ำชาย ต่อท่อ 2"')
p = f1_drop('SD-F1G', c, 50, zt - 0.005, [1, 0, 0], 'ท่อน้ำทิ้งอ่างล้างมือรวม 2" ดิ่งผ่านตัวอ่าง')
f1_pipe('SD-F1G', p, pb, 50, 'ท่อน้ำทิ้งอ่างล้างมือรวม ใต้พื้น ลาด 1:50')
# 4b) อ่างล้างมือรวมห้องน้ำหญิง: สะดือ x = 29.45 y = 10.10 → ท่อ 2" ลึกลอดใต้คาน GB1-9 → ข้องอ 45° 2 ตัว → TYR (จากทิศ +x)
pb, pbr = G_BP[10.40]
w1 = _up(pb, [27.15, pb[1], 0], S_BR)
w2 = _up(w1, [27.45, 10.10, 0], S_BR)
w3 = _up(w2, [29.45, 10.10, 0], S_BR)
zt = f1_trough_waste('SD-F1G-TRW-WST', 29.45, 10.10, 'สะดืออ่างล้างมือรวม สแตนเลส ห้องน้ำหญิง ต่อท่อ 2"')
p = f1_drop('SD-F1G', w3, 50, zt - 0.005, [-1, 0, 0], 'ท่อน้ำทิ้งอ่างล้างมือรวม 2" ดิ่งผ่านตัวอ่าง')
f1_route('SD-F1G', [w3, w2, w1, pb], 50, 'ท่อน้ำทิ้งอ่างล้างมือรวมห้องน้ำหญิง ใต้พื้น ลาด 1:50 ลอดคานคอดิน (ท่อปลอก)', s0=0.030)
f1_slv9('SD-F1G-SLV2', w2, w3, 50, 'ท่อปลอก PVC ø80 ฝังคานคอดิน GB1-9-BC สำหรับท่อน้ำทิ้งอ่างล้างมือรวมห้องน้ำหญิง ø2"')
# 4c) ฟลอร์เดรนห้องน้ำชาย (หน้าโถปัสสาวะ): ท่อ 3" ดิ่ง → ข้องอ 90° ทิศทแยง → วายลด 100x80
pb, pbr = G_BP[11.40]
c = _pt(pb, pbr, (pb[0] - 26.60) / -pbr[0])
f1_fd('SD-F1G-M', c[0], c[1], 'ฟลอร์เดรน PVC ฝังพื้น ตะแกรง 4" แบบกันกลิ่น ห้องน้ำชาย ชั้น 1 (หน้าโถปัสสาวะ)')
p = f1_drop('SD-F1G', c, 80, F1_FF - 0.003, [-pbr[0], -pbr[1], 0], 'ตัวฟลอร์เดรน/ท่อ 3" PVC ฝังพื้น')
f1_pipe('SD-F1G', p, pb, 80, 'ท่อน้ำทิ้งฟลอร์เดรน ใต้พื้น ลาด 1:50')
# 4d) ฟลอร์เดรนห้องน้ำหญิง (ทางเดินหน้าห้องส้วม): ท่อ 3" ดิ่ง → ข้องอ 90° ราบ −y → ข้องอ 90° ราบ −x แนว y = 10.90 (เลี่ยงท่อส้วมชายแนวทแยง)
#     ลอดคาน GB1-9 (ท่อปลอก) → ข้องอ 45° → วายลด 100x80
pb, pbr = G_BP[11.10]
e1 = _pt(pb, pbr, (10.90 - pb[1]) / pbr[1])
e2 = _up(e1, [29.00, 10.90, 0], S_BR)
c = _up(e2, [29.00, 11.60, 0], S_BR)
f1_fd('SD-F1G-W', 29.00, 11.60, 'ฟลอร์เดรน PVC ฝังพื้น ตะแกรง 4" แบบกันกลิ่น ห้องน้ำหญิง ชั้น 1 (ทางเดินหน้าห้องส้วม)')
p = f1_drop('SD-F1G', c, 80, F1_FF - 0.003, [0, -1, 0], 'ตัวฟลอร์เดรน/ท่อ 3" PVC ฝังพื้น')
f1_route('SD-F1G', [c, e2, e1, pb], 80, 'ท่อน้ำทิ้งฟลอร์เดรน ใต้พื้น ลาด 1:50 ลอดคานคอดิน (ท่อปลอก)', s0=F1_EB[(90, 80)][1])
f1_slv9('SD-F1G-SLV3', e1, e2, 80, 'ท่อปลอก PVC ø100 ฝังคานคอดิน GB1-9-BC สำหรับท่อน้ำทิ้งฟลอร์เดรนห้องน้ำหญิง ø3"')
# 4e) อ่างล้างหน้า 2 คู่ (ชายติดผนังกริด 9 ด้านตะวันตก / หญิงด้านตะวันออก): P-trap 2" → ข้องอ 90° ลง → ท่อ 2" ลึกลอดใต้คาน GB1-9 → TEE รับอ่างชาย → TYR
for yj, j in ((13.32, 1), (12.52, 2)):
    pb, pbr = G_BP[yj]
    lm = next(e for e in elements if e['id'] == f'FX-F1-WC1-LAV{j}')
    lw = next(e for e in elements if e['id'] == f'FX-F1-WC2-LAV{j}')
    xm = sum(q[0] for q in lm['geom']['poly']) / len(lm['geom']['poly'])
    xw = sum(q[0] for q in lw['geom']['poly']) / len(lw['geom']['poly'])
    zb = lm['geom']['z0']                                       # ท้องอ่าง
    zA = F1_FF + 0.45                                           # ปากออก P-trap
    xtm = xm - 0.102 - 0.030 - 0.030                            # แนวท่อดิ่งชาย (P-trap หันปากออกทิศ −x)
    xtw = xw + 0.102 + 0.030 + 0.030
    t1 = _up(pb, [xtm, yj, 0], S_BR)
    c2 = _up(t1, [xtw, yj, 0], S_BR)
    ti, to, tb, tY = f1_tee('SD-F1G', 'TEE55', t1, _unit([-1, 0, -S_BR]), [0, 0, 1], f'สามทาง ø2" รับท่อดิ่งอ่างล้างหน้าชาย ตัวที่ {j}')
    f1_pipe('SD-F1G', to, pb, 50, 'ท่อน้ำทิ้งอ่างล้างหน้า ใต้พื้น ลาด 1:50')
    p = f1_drop('SD-F1G', c2, 50, zA - 0.030, [-1, 0, 0], 'ท่อน้ำทิ้งอ่างล้างหน้าหญิง 2" ดิ่ง')
    f1_pipe('SD-F1G', p, ti, 50, 'ท่อน้ำทิ้งอ่างล้างหน้า ใต้พื้น ลาด 1:50 ลอดคานคอดิน (ท่อปลอก)')
    f1_slv9(f'SD-F1G-SLV{3 + j}', t1, c2, 50, f'ท่อปลอก PVC ø80 ฝังคานคอดิน GB1-9-BC สำหรับท่อน้ำทิ้งอ่างล้างหน้าหญิง ตัวที่ {j} ø2"')
    for sx, xa, xt, who, ztop in ((-1, xm, xtm, 'ชาย', tb[2]), (1, xw, xtw, 'หญิง', None)):
        oT = [xa + sx * 0.102, yj, zA - 0.058]
        n3_fit(f'SD-F1G-LAV{"M" if sx < 0 else "W"}{j}-TRAP', 'PVC-P-TRAP-55', oT, [sx, 0, 0], [0, 1, 0], f'พีแทรปโครเมียม LUZERN OS-009-30 ใต้อ่างล้างหน้า{who} ตัวที่ {j} รูปทรงแทนด้วย', '30 ซม.')
        elements[-1]['qty'].update(model='LUZERN OS-009-30 สีโครม', material='โครเมียม')  # วิวัฒน์ 24 พ.ย. 2569: อ่างชั้น 1 ใช้พีแทรปโครเมียม
        elements[-1]['material'] = 'BIM-โครเมียม'
        n3_chrome(f'SD-F1G-LAV{"M" if sx < 0 else "W"}{j}-WST', [xa, yj, zb - 0.10], [xa, yj, zb], 0.040,
                  f'สะดืออ่างล้างหน้าสำเร็จรูป สแตนเลส ต่อท่อ 2" ห้องน้ำ{who} ชั้น 1', qty=dict(type='สะดืออ่างสแตนเลส', size='ต่อท่อ 2"'), mat='BIM-สแตนเลส')
        f1_pipe('SD-F1G', [xa, yj, oT[2] + 0.045], [xa, yj, zb - 0.10], 50, f'ท่อน้ำทิ้งใต้อ่างล้างหน้า{who} (สะดืออ่าง → P-trap)')
        ce = [xt, yj, zA]
        f1_fit('SD-F1G', 'EB', 'PVC-EB-90-55', ce, [-sx, 0, 0], [0, 0, -1], 'ข้องอ 90° ø2" หลัง P-trap ลงพื้น', '2"')
        if sx < 0:
            f1_pipe('SD-F1G', [xt, yj, zA - 0.030], tb, 50, 'ท่อน้ำทิ้งอ่างล้างหน้าชาย 2" ดิ่งลงพื้น')

# ---------- 5) ท่อน้ำทิ้งซิงค์ร้านค้า 3 ร้าน ø100 ลาด 1:100 ลึกใต้พื้นร้าน (แนว y ใต้ซิงค์ พ้นตอม่อ) → ทแยงลอดใต้คาน GB2-B7-8 → วายลด 150x100 บนท่อรวมโซน 2 ฝั่งกริด 5 (x = 23.30) ----
SK_W, SK_D, SK_H = 0.75, 0.45, 0.80                             # DYNA HOME DH-7545-TB 75x45 ซม. (สูงพร้อมขา 0.80 สมมติ)
SK_Y0, SK_Y1 = 13.80 - SK_D, 13.80                              # ชิดผิวฉาบผนังหลังร้าน (แนว B)
SK = {}
for n, i in ((1, 5), (2, 6), (3, 7)):
    x1 = GX[i] - 0.185                                          # ชิดผิวฉาบเสา C1-{i+1}B
    SK[n] = (x1 - SK_W, x1, (x1 - SK_W / 2))
SK_YC = (SK_Y0 + SK_Y1) / 2
S_YD = round(SK_YC - 0.102 - 0.030 - 0.030, 4)                  # แนวท่อดิ่ง/ท่อรวม (P-trap หันปากออกทิศ −y)
sP, sbr = f1_header_y('SD-Z2W', 23.30, +1, _unit([-0.7071, -0.7071, S_GR]), 'วายลด 150x100 รับท่อน้ำทิ้งซิงค์ร้านค้า ชั้น 1')
sD = _pt(sP, sbr, (S_YD - sP[1]) / sbr[1])                      # จุดเลี้ยว 45° บนแนว y = S_YD
Xs = _unit([1, 0, -S_GR])
zs = lambda x: sD[2] + S_GR * (sD[0] - x)
udg = _unit(_v(sD, sP))
dpS = f1_eb('SD-F1S', 45, 100, sD, Xs, udg)
# ซิงค์ร้าน 3: ท่อแยก 2" ตั้งฉากกับแนวทแยง เข้า TYR บนแนวทแยง
x3c = SK[3][2]
tq = (x3c - sD[0]) * udg[0] + (S_YD - sD[1]) * udg[1]
tq /= math.hypot(udg[0], udg[1]) ** 2
Q3 = [sD[0] + udg[0] * tq, sD[1] + udg[1] * tq, sD[2] + udg[2] * tq]
Xd = _unit([udg[0], udg[1], udg[2]])
ti, to, tb3, tY3 = f1_tee('SD-F1S', 'TYR55', Q3, Xd, [x3c - Q3[0], S_YD - Q3[1], 0.02 * math.hypot(x3c - Q3[0], S_YD - Q3[1])], 'สามทางวายลด (TYR) 4"x2" รับท่อซิงค์ร้าน 3')
f1_pipe('SD-F1S', _pt(sD, udg, dpS), ti, 100, 'ท่อน้ำทิ้งซิงค์ร้านค้า ลาด 1:100 ลอดใต้คานคอดิน (ลงท่อรวมโซน 2)')
f1_pipe('SD-F1S', to, sP, 100, 'ท่อน้ำทิ้งซิงค์ร้านค้า ลาด 1:100 (ลงท่อรวมโซน 2)')
c3 = _up(tb3, [x3c, S_YD, 0], S_BR)
SK_ZT = {}
SK_ZT[3] = c3
# แนว y = S_YD (ไหล +x): TYR ซิงค์ร้าน 2, 1 (ปากแยกตั้งขึ้นรับท่อดิ่ง) → ปลายต้นสายปิดปลั๊ก
cur_dn = _pt(sD, Xs, -dpS)
for n in (2, 1):
    o = [SK[n][2], S_YD, zs(SK[n][2])]
    ti, to, tb, tY = f1_tee('SD-F1S', 'TYR55', o, Xs, [0, 0, 1], f'สามทางวายลด (TYR) 4"x2" รับท่อดิ่งซิงค์ร้าน {n}')
    f1_pipe('SD-F1S', to, cur_dn, 100, 'ท่อน้ำทิ้งซิงค์ร้านค้า ใต้พื้นร้าน ลาด 1:100')
    SK_ZT[n] = tb
    cur_dn = ti
f1_cap('SD-F1S', cur_dn, [-1, 0, 0], 100, 'ฝาปิดปลายท่อต้นสาย (ปลั๊กอุด)')
SK_TOP = F1_FF + SK_H                                            # ขอบบนซิงค์ 1.12
SK_BOT = SK_TOP - 0.20                                           # ก้นหลุมซิงค์ (ลึก 0.20 สมมติ)
for n in (1, 2, 3):
    x0, x1, xc = SK[n]
    # ตัวซิงค์ (แผ่นบน + หลุม) + ขาตั้ง 4 ขา
    parts = [prism([(x0, _YM - SK_Y0), (x1, _YM - SK_Y0), (x1, _YM - SK_Y1), (x0, _YM - SK_Y1)], SK_BOT, SK_TOP - SK_BOT)]
    for lx, ly in ((x0 + 0.03, SK_Y0 + 0.03), (x1 - 0.03, SK_Y0 + 0.03), (x0 + 0.03, SK_Y1 - 0.03), (x1 - 0.03, SK_Y1 - 0.03)):
        parts.append(prism([(lx - 0.02, _YM - ly + 0.02), (lx + 0.02, _YM - ly + 0.02), (lx + 0.02, _YM - ly - 0.02), (lx - 0.02, _YM - ly - 0.02)], F1_FF, SK_BOT - F1_FF))
    add(f'FX-F1-SH{n}-SINK', 'สุขภัณฑ์', 1, 'A21', dict(type='multi', parts=parts),
        name=f'ซิงค์ล้างจานสแตนเลส 1 หลุม พร้อมขาตั้ง DYNA HOME DH-7545-TB 75x45 ซม. หลังร้าน {n} มุมแนวหน้าต่าง', assumed=True,
        qty=dict(count=1, type='ซิงค์ล้างจาน 1 หลุม พร้อมขาตั้ง', model='DYNA HOME DH-7545-TB', size='75x45 ซม.', height=SK_H))
    elements[-1]['material'] = 'BIM-สแตนเลส'
    # สะดือซิงค์ → ท่อหาง → P-trap 2" (ปากออก −y) → ข้องอ 90° ลง → ท่อ 2" ดิ่ง
    zA = SK_BOT - 0.20
    oT = [xc, SK_YC - 0.102, zA - 0.058]
    n3_fit(f'SD-F1S-SK{n}-TRAP', 'PVC-P-TRAP-55', oT, [0, -1, 0], [1, 0, 0], f'พีแทรปโครเมียม ใต้ซิงค์ร้าน {n} รูปทรงแทนด้วย', '1½"')
    elements[-1]['qty'].update(model='พีแทรปซิงค์ โครเมียม 1½"', material='โครเมียม')      # วิวัฒน์ 24 พ.ย. 2569: ซิงค์ใช้พีแทรปโครเมียม
    elements[-1]['material'] = 'BIM-โครเมียม'
    n3_chrome(f'SD-F1S-SK{n}-WST', [xc, SK_YC, SK_BOT - 0.05], [xc, SK_YC, SK_BOT], 0.045, f'สะดือซิงค์ (มากับชุดซิงค์) ร้าน {n}', qty=dict(type='สะดือซิงค์ (มากับชุดซิงค์)', size='ต่อท่อ 2"'), mat='BIM-สแตนเลส')
    f1_pipe('SD-F1S', [xc, SK_YC, oT[2] + 0.045], [xc, SK_YC, SK_BOT - 0.05], 50, f'ท่อน้ำทิ้งใต้ซิงค์ร้าน {n} (สะดือ → P-trap)')
    f1_fit('SD-F1S', 'EB', 'PVC-EB-90-55', [xc, S_YD, zA], [0, 1, 0], [0, 0, -1], 'ข้องอ 90° ø2" หลัง P-trap ลงพื้น', '2"')
    if n < 3:
        f1_pipe('SD-F1S', [xc, S_YD, zA - 0.030], SK_ZT[n], 50, f'ท่อน้ำทิ้งซิงค์ร้าน {n} 2" ดิ่งลงพื้น')
    else:
        p = f1_drop('SD-F1S', c3, 50, zA - 0.030, [tb3[0] - c3[0], tb3[1] - c3[1], 0], f'ท่อน้ำทิ้งซิงค์ร้าน {n} 2" ดิ่งลงพื้น')
        f1_pipe('SD-F1S', p, tb3, 50, 'ท่อน้ำทิ้งซิงค์ร้าน 3 ใต้ดิน ลาด 1:50 ลอดใต้คานคอดิน')

# ---------- 6) ท่อน้ำดีชั้น 1 PVC ชั้น 13.5: สามทางลดบนท่อดิ่ง 2" ผนังกริด 1 (ใต้ท้องพื้นชั้น 2) → เมน 1¼" ใต้ท้องคานทางเดินชั้น 1 ----
#     → ห้องน้ำชาย 3/4" (โถปัสสาวะ อ่างรวม อ่างล้างหน้าชาย-หญิง ชักโครกชาย) → ต่อ 1/2" ไปก๊อกซิงค์ 3 ร้าน (ท่อเดินในร้านชิดผนังหลังร้าน) ; ห้องน้ำหญิง 3/4" (อ่างรวม ชักโครกหญิง)
CW = 'PB-F1-CW'
h2, h114, h34, h12 = (WOD[s][0] / 2 + 0.006 for s in ('2', '1 1/4', '3/4', '1/2'))
zW = 2.70                                                       # ระดับท่อน้ำดีชั้น 1 (ใต้ท้องคาน 2.90)
yWm = 8.20                                                      # แนวท่อเมนทางเดิน (ห่างคาน B2-C 0.30)
rs = next(e for e in elements if e['id'] == 'PB-NW-RS-P1')
_g = rs['geom']
_lo = 'p0' if _g['p0'][2] < _g['p1'][2] else 'p1'
xR, yR = _g[_lo][0], round(_YM - _g[_lo][1], 4)
zR0 = _g[_lo][2]
zRT = 3.25
_g[_lo][2] = round(zRT + h2, 4)
rs['qty']['length'] = round(abs(_g['p0'][2] - _g['p1'][2]), 3)
n3_wpipe(f'{CW}-RS-P0', [xR, yR, zR0], [xR, yR, zRT - h2], '2', 'ท่อแนวดิ่งจ่ายน้ำ ผนังกริด 1 (ช่วงล่าง)')
n3_wfit(f'{CW}-RS-T', [xR, yR, zRT], '2', 'สามทางลด 2"x1¼" (แยกจ่ายชั้น 1)')


def cw_run(pref, pts, sz, nm, s0, s1):
    """ท่อน้ำดีผ่านจุด pts ข้องอ 90° (ทำเอง) ที่จุดหักมุม; ตัดปลายแรก s0 ปลายท้าย s1"""
    h = WOD[sz][0] / 2 + 0.006
    for j in range(len(pts) - 1):
        a, b = pts[j], pts[j + 1]
        d = _unit(_v(a, b))
        n3_wpipe(_f1id(pref, 'P'), _pt(a, d, s0 if j == 0 else h), _pt(b, d, -(s1 if j == len(pts) - 2 else h)), sz, nm)
        if j < len(pts) - 2:
            n3_wfit(_f1id(pref, 'EL'), b, sz, 'ข้องอ 90°')


def cw_tee(pref, p, sz, nm='สามทาง'):
    n3_wfit(_f1id(pref, 'TE'), p, sz, nm)


def cw_valve(eid, p, d, sz, nm, kind='บอลวาล์ว'):
    h = 0.045 if sz == '1/2' else 0.06
    n3_chrome(eid, _pt(p, d, -h), _pt(p, d, h), WOD[sz][0] + 0.012, f'{nm} {sz}"', qty=dict(type=kind, size=f'{sz}"'))
    n3_box(eid + 'H', p[0] - 0.008, p[1] - 0.008, p[0] + 0.008, p[1] + 0.008, p[2] + WOD[sz][0] / 2 + 0.006, 0.035, 'ด้ามบอลวาล์ว')
    elements[-1]['material'] = 'BIM-โครเมียม'


# 6.1 เมน 1¼": ท่อดิ่ง → ทิศ −y 0.19 → ลง 2.70 → ตามแนวทางเดิน y = 8.20 ไปทางกริด 10
x_mt, x_wt = 26.60, 30.72                                        # สามทางแยกเข้าห้องน้ำชาย (ทะลุผนังแนว C ฝั่งตะวันตกของเสาเอ็นประตูผนังกั้นกลาง) / หญิง (ช่องทางเข้าโล่ง)
x_vm = 0.60
cw_run(f'{CW}-MN', [[xR, yR, zRT], [xR, yWm, zRT], [xR, yWm, zW], [x_vm, yWm, zW]], '1 1/4', 'ท่อเมนน้ำดีชั้น 1 ใต้ท้องพื้นชั้น 2', h2, 0.06)
cw_valve(f'{CW}-MN-V', [x_vm, yWm, zW], [1, 0, 0], '1 1/4', 'บอลวาล์วทองเหลือง ท่อเมนน้ำดีชั้น 1')
n3_wpipe(f'{CW}-MN-P10', [x_vm + 0.06, yWm, zW], [x_mt - h114, yWm, zW], '1 1/4', 'ท่อเมนน้ำดีชั้น 1 ใต้ท้องคานทางเดิน')
cw_tee(f'{CW}-MN', [x_mt, yWm, zW], '1 1/4', 'สามทางลด 1¼"x3/4"')
n3_wpipe(f'{CW}-MN-P11', [x_mt + h114, yWm, zW], [x_wt - h114, yWm, zW], '1 1/4', 'ท่อเมนน้ำดีชั้น 1 ใต้ท้องคานทางเดิน')
n3_wfit(f'{CW}-MN-EL9', [x_wt, yWm, zW], '1 1/4', 'ข้องอ 90° + ข้อต่อลด 1¼"x3/4" (ปลายท่อเมน)')
# จุดแขวนท่อ: ใต้คาน B1-CD ทุกกริด + ใต้คาน B2-C ตรงท่อแยกเข้าห้องน้ำ + กลางห้องน้ำ (แขวนจากท้องพื้นชั้น 2)
F1_HG = []


def cw_hang(eid, p, sz, z_top, where, ax=(1, 0, 0)):
    od = WOD[sz][0]
    n3_chrome(eid + '-ROD', [p[0], p[1], z_top], [p[0], p[1], p[2] + od / 2 + 0.008], 0.010, f'เหล็กเส้นเกลียว M10 ชุบกัลวาไนซ์ + พุกเหล็ก M10 ยึด{where}',
              qty=dict(type='เหล็กเส้นเกลียว M10 + พุกเหล็ก M10', length=round(z_top - p[2] - od / 2 - 0.008, 3)), mat='BIM-เหล็กชุบกัลวาไนซ์')
    m = member(_J(_pt(p, ax, -0.0125)), _J(_pt(p, ax, 0.0125)), od + 0.012, od + 0.012)
    m.update(shape='POLY', poly2d=_circ(od / 2 + 0.006), hole2d=_circ(od / 2 + 0.001))
    add(eid + '-CL', 'สุขาภิบาล', 1, 'A07', m, name=f'ห่วงแขวนท่อเหล็กชุบกัลวาไนซ์ บุยาง {sz}"', assumed=True, qty=dict(type='ห่วงแขวนท่อ', size=f'{sz}"'))
    elements[-1]['material'] = 'BIM-เหล็กชุบกัลวาไนซ์'
    F1_HG.append(eid)


Z_BSOF, Z_CEIL = 2.90, 3.31                                      # ท้องคานชั้น 2 / ผิวฉาบใต้ท้องพื้นชั้น 2
for i in range(1, 9):
    cw_hang(f'{CW}-HG{i}', [GX[i], yWm, zW], '1 1/4', Z_BSOF, 'ท้องคาน B1-CD')
cw_hang(f'{CW}-HG9', [29.75, yWm, zW], '1 1/4', Z_CEIL, 'ท้องพื้นชั้น 2')
# 6.2 ห้องน้ำชาย 3/4": จากสามทางบนเมน → +y (ผ่านใต้คาน B2-C ทางเข้าโล่ง) → ทะลุผนังกั้นกลางเหนือประตู → สามทาง (โถปัสสาวะ/อ่างรวม) → สามทาง (อ่างล้างหน้า) → ข้องอ → ทิศ −x
yMW = 10.35                                                     # แนวกลางผนังกั้นกลาง
y_bs, y_ws = 12.92, 13.55                                       # สามทางอ่างล้างหน้า / แนวท่อชิดผนังหลัง (หน้าคาน B2-B)
n3_wpipe(f'{CW}-M-P01', [x_mt, yWm + h114, zW], [x_mt, 9.40 - 0.045, zW], '3/4', 'ท่อน้ำดีห้องน้ำชาย ชั้น 1')
cw_valve(f'{CW}-M-V', [x_mt, 9.40, zW], [0, 1, 0], '3/4', 'บอลวาล์วทองเหลือง ห้องน้ำชาย')
n3_wpipe(f'{CW}-M-P02', [x_mt, 9.40 + 0.045, zW], [x_mt, yMW - h34, zW], '3/4', 'ท่อน้ำดีห้องน้ำชาย ชั้น 1 ทะลุผนังกั้นกลาง')
cw_tee(f'{CW}-M', [x_mt, yMW, zW], '3/4', 'สามทางลด 3/4"x1/2"')
n3_wpipe(f'{CW}-M-P03', [x_mt, yMW + h34, zW], [x_mt, y_bs - h34, zW], '3/4', 'ท่อน้ำดีห้องน้ำชาย ชั้น 1')
cw_tee(f'{CW}-M', [x_mt, y_bs, zW], '3/4', 'สามทางลด 3/4"x1/2"')
n3_wpipe(f'{CW}-M-P04', [x_mt, y_bs + h34, zW], [x_mt, y_ws - h34, zW], '3/4', 'ท่อน้ำดีห้องน้ำชาย ชั้น 1')
n3_wfit(f'{CW}-M-EL1', [x_mt, y_ws, zW], '3/4', 'ข้องอ 90°')
x_g8 = 24.50
n3_wpipe(f'{CW}-M-P05', [x_mt - h34, y_ws, zW], [x_g8 + h34, y_ws, zW], '3/4', 'ท่อน้ำดีห้องน้ำชาย ชั้น 1 ชิดผนังหลัง')
cw_tee(f'{CW}-M', [x_g8, y_ws, zW], '3/4', 'สามทางลด 3/4"x1/2" (ในผนังกริด 8)')
for k, yh in enumerate((9.55, 11.65, 13.20)):
    cw_hang(f'{CW}-M-HG{k+1}', [x_mt, yh, zW], '3/4', Z_CEIL, 'ท้องพื้นชั้น 2', ax=(0, 1, 0))
cw_hang(f'{CW}-M-HG4', [x_mt, 8.625, zW], '3/4', Z_BSOF, 'ท้องคาน B2-C8-9', ax=(0, 1, 0))
cw_hang(f'{CW}-M-HG5', [25.90, y_ws, zW], '3/4', Z_CEIL, 'ท้องพื้นชั้น 2')
# โถปัสสาวะ + อ่างรวมชาย: ท่อ 1/2" ฝังผนังกั้นกลาง +2.70 → ท่อดิ่งในผนัง 3 จุด → ฟลัชวาล์วโถปัสสาวะ (ด้านห้องส้วม) + ก๊อกอ่างรวม (ด้านอ่าง)
X_UR = (26.44, 25.64, 24.84)
Z_FV, Z_TT = F1_FF + 1.15, F1_FF + 0.80                         # ฟลัชวาล์ว / ก๊อกอ่างรวม (ขอบอ่าง +0.58)
y_mwB, y_mwC = 10.40, 10.30                                     # ผิวฉาบผนังกั้นกลาง ด้านห้องส้วม / ด้านอ่างรวม


def cw_mw_drops(pref, xs_, x_from, sz, tap_who, fv=False):
    """ท่อ 1/2" ฝังผนังกั้นกลางจาก x_from ไปตามลำดับ xs_ (สามทาง ... ข้องอปลาย) แล้วดิ่งลงแต่ละจุด"""
    cur = x_from
    for k, xu in enumerate(xs_):
        last = k == len(xs_) - 1
        sgn = 1 if xu > cur else -1
        n3_wpipe(_f1id(pref, 'P'), [cur + sgn * (h34 if k == 0 else h12), yMW, zW], [xu - sgn * h12, yMW, zW], '1/2', 'ท่อน้ำดีฝังผนังกั้นกลาง')
        n3_wfit(_f1id(pref, 'EL' if last else 'TE'), [xu, yMW, zW], '1/2', 'ข้องอ 90°' if last else 'สามทาง')
        zlow = Z_TT
        if fv:
            n3_wpipe(_f1id(pref, 'P'), [xu, yMW, zW - h12], [xu, yMW, Z_FV + h12], '1/2', 'ท่อน้ำดีฝังผนัง ดิ่งลงฟลัชวาล์ว')
            n3_wfit(_f1id(pref, 'TE'), [xu, yMW, Z_FV], '1/2', 'สามทาง')
            n3_wpipe(_f1id(pref, 'P'), [xu, yMW + h12, Z_FV], [xu, y_mwB, Z_FV], '1/2', 'ท่อน้ำดีออกฟลัชวาล์วโถปัสสาวะ')
            n3_chrome(_f1id(pref, 'FV'), [xu, y_mwB, Z_FV], [xu, y_mwB + 0.09, Z_FV], 0.045, 'ฟลัชวาล์วโถปัสสาวะ กะรัต K-11702X-CP (มากับชุดโถ) +1.15',
                      qty=dict(type='ฟลัชวาล์วโถปัสสาวะ (มากับชุดโถ)', size='3/4"', model='กะรัต K-11702X-CP'))
            n3_chrome(_f1id(pref, 'FVP'), [xu, y_mwB + 0.07, Z_FV], [xu, y_mwB + 0.07, F1_FF + 0.60], 0.019, 'ท่อจ่ายน้ำฟลัชวาล์ว → โถปัสสาวะ (มากับชุด)')
            n3_wpipe(_f1id(pref, 'P'), [xu, yMW, Z_FV - h12], [xu, yMW, Z_TT + h12], '1/2', 'ท่อน้ำดีฝังผนัง ดิ่งลงก๊อกอ่างรวม')
        else:
            n3_wpipe(_f1id(pref, 'P'), [xu, yMW, zW - h12], [xu, yMW, Z_TT + h12], '1/2', 'ท่อน้ำดีฝังผนัง ดิ่งลงก๊อกอ่างรวม')
        n3_wfit(_f1id(pref, 'EL'), [xu, yMW, Z_TT], '1/2', 'ข้องอ 90°')
        n3_wpipe(_f1id(pref, 'P'), [xu, yMW - h12, Z_TT], [xu, y_mwC, Z_TT], '1/2', 'ท่อน้ำดีออกก๊อกอ่างรวม')
        n3_chrome(_f1id(pref, 'TAP'), [xu, y_mwC, Z_TT], [xu, y_mwC - 0.08, Z_TT], 0.022, f'ก๊อกอ่างล้างมือรวม{tap_who} (ก๊อกบอลสนาม ชุบโครเมียม) 1/2" +0.80',
                  qty=dict(type='ก๊อกน้ำติดผนัง', size='1/2"'))
        n3_chrome(_f1id(pref, 'TAPS'), [xu, y_mwC - 0.08, Z_TT], [xu, y_mwC - 0.08, Z_TT - 0.06], 0.018, 'ปากก๊อกอ่างล้างมือรวม')
        cur = xu


cw_mw_drops(f'{CW}-MU', X_UR, x_mt, '1/2', 'ชาย', fv=True)
# อ่างล้างหน้า ชาย+หญิง: 1/2" จากสามทาง → ผนังกริด 9 → ดิ่งในผนังลง +0.55 → สามทาง → ราบในผนัง → สามทางที่จุดวาล์ว → ออกผิวผนังทั้ง 2 ด้าน + วาล์วเปิดปิด (angle valve)
x_g9 = 28.00
Z_LV = F1_FF + 0.55
cw_run(f'{CW}-LV', [[x_mt, y_bs, zW], [x_g9, y_bs, zW], [x_g9, y_bs, Z_LV]], '1/2', 'ท่อน้ำดีอ่างล้างหน้า (ฝังผนังกริด 9)', h34, h12)
cw_tee(f'{CW}-LV', [x_g9, y_bs, Z_LV], '1/2')
for yv in (13.22, 12.42):
    sgn = 1 if yv > y_bs else -1
    n3_wpipe(_f1id(f'{CW}-LV', 'P'), [x_g9, y_bs + sgn * h12, Z_LV], [x_g9, yv - sgn * h12, Z_LV], '1/2', 'ท่อน้ำดีฝังผนังกริด 9')
    cw_tee(f'{CW}-LV', [x_g9, yv, Z_LV], '1/2')
    for sx, xf, who in ((-1, 27.95, 'ชาย'), (1, 28.05, 'หญิง')):
        n3_wpipe(_f1id(f'{CW}-LV', 'P'), [x_g9 + sx * h12, yv, Z_LV], [xf, yv, Z_LV], '1/2', 'ท่อน้ำดีออกวาล์วอ่างล้างหน้า')
        n3_chrome(_f1id(f'{CW}-LV', 'AV'), [xf, yv, Z_LV], [xf + sx * 0.06, yv, Z_LV], 0.03, f'วาล์วเปิดปิดน้ำอ่างล้างหน้า{who} (angle valve) +0.55',
                  qty=dict(type='angle valve', size='1/2"'))
        n3_chrome(_f1id(f'{CW}-LV', 'HS'), [xf + sx * 0.06, yv, Z_LV], [xf + sx * 0.20, yv + 0.10, F1_FF + 0.80], 0.010, 'สายน้ำดีถัก 1/2" วาล์ว → ก๊อกอ่าง', mat='BIM-สแตนเลส')
        elements[-1]['qty'] = dict(type='สายน้ำดีถักสแตนเลส', size='1/2"')
# ชักโครกชาย 2 ตัว (ผนังกริด 8): ดิ่งในผนังจากสามทาง → +0.20 → ราบในผนัง → สต็อปวาล์ว (angle valve) ข้างชักโครก
Z_WV = F1_FF + 0.20
y_wv1, y_wv2 = 13.22 - 0.07, 11.995 - 0.07
cw_run(f'{CW}-MW', [[x_g8, y_ws, zW], [x_g8, y_ws, Z_WV], [x_g8, y_wv2, Z_WV]], '1/2', 'ท่อน้ำดีชักโครกชาย (ฝังผนังกริด 8)', h34, 0.0)
elements.pop()
n3_wpipe(_f1id(f'{CW}-MW', 'P'), [x_g8, y_ws - h12, Z_WV], [x_g8, y_wv1 + h12, Z_WV], '1/2', 'ท่อน้ำดีชักโครกชาย (ฝังผนังกริด 8)')
cw_tee(f'{CW}-MW', [x_g8, y_wv1, Z_WV], '1/2')
n3_wpipe(_f1id(f'{CW}-MW', 'P'), [x_g8, y_wv1 - h12, Z_WV], [x_g8, y_wv2 + h12, Z_WV], '1/2', 'ท่อน้ำดีชักโครกชาย (ฝังผนังกริด 8)')
n3_wfit(_f1id(f'{CW}-MW', 'EL'), [x_g8, y_wv2, Z_WV], '1/2', 'ข้องอ 90°')


def cw_wc_valve(pref, xw, xf, sx, y, who):
    n3_wpipe(_f1id(pref, 'P'), [xw + sx * h12, y, Z_WV], [xf, y, Z_WV], '1/2', 'ท่อน้ำดีออกสต็อปวาล์วชักโครก')
    n3_chrome(_f1id(pref, 'WV'), [xf, y, Z_WV], [xf + sx * 0.06, y, Z_WV], 0.03, f'สต็อปวาล์วชักโครก{who} (angle valve) +0.20', qty=dict(type='angle valve', size='1/2"'))
    n3_chrome(_f1id(pref, 'HS'), [xf + sx * 0.06, y, Z_WV], [xf + sx * 0.12, y + 0.10, Z_WV + 0.05], 0.010, 'สายน้ำดีถัก 1/2" สต็อปวาล์ว → ถังพักชักโครก', mat='BIM-สแตนเลส')
    elements[-1]['qty'] = dict(type='สายน้ำดีถักสแตนเลส', size='1/2"')


for y in (y_wv1, y_wv2):
    cw_wc_valve(f'{CW}-MW', x_g8, 24.55, 1, y, 'ชาย')
# ก๊อกซิงค์ร้าน 3 ร้าน: 1/2" ต่อจากสามทางในผนังกริด 8 → ทะลุผนังกริด 7, 6 ในร้าน แนวเดียวกัน (+2.70 ชิดผนังหลัง) → สามทาง → ฝังผนังหลังร้านดิ่งลงก๊อก
Z_ST = SK_TOP + 0.25                                            # ก๊อกซิงค์ติดผนัง +1.05 (สูงกว่าขอบซิงค์ 0.25)
y_bw, y_bf = 13.85, 13.80                                       # แนวกลางผนังหลังร้าน / ผิวฉาบด้านในร้าน
xs_sk = [SK[n][2] for n in (3, 2, 1)]
cur = x_g8
for k, xc in enumerate(xs_sk):
    last = k == len(xs_sk) - 1
    n3_wpipe(_f1id(f'{CW}-SH', 'P'), [cur - (h34 if k == 0 else h12), y_ws, zW], [xc + h12, y_ws, zW], '1/2', 'ท่อน้ำดีก๊อกซิงค์ร้านค้า (ในร้าน ชิดผนังหลัง +2.70)')
    n = 3 - k
    n3_wfit(_f1id(f'{CW}-SH', 'EL' if last else 'TE'), [xc, y_ws, zW], '1/2', 'ข้องอ 90°' if last else 'สามทาง')
    cw_run(f'{CW}-SH{n}', [[xc, y_ws, zW], [xc, y_bw, zW], [xc, y_bw, Z_ST], [xc, y_bf, Z_ST]], '1/2', f'ท่อน้ำดีก๊อกซิงค์ร้าน {n} (ฝังผนังหลังร้าน)', h12, 0.0)
    n3_chrome(f'{CW}-SH{n}-TAP', [xc, y_bf, Z_ST], [xc, y_bf - 0.20, Z_ST], 0.022, f'ก๊อกซิงค์ติดผนัง VEGARR VHY1108F 1/2" ร้าน {n} +{Z_ST - F1_FF:.2f}',
              qty=dict(type='ก๊อกซิงค์ติดผนัง', size='1/2"', model='VEGARR VHY1108F'))
    n3_chrome(f'{CW}-SH{n}-TAPS', [xc, y_bf - 0.20, Z_ST], [xc, y_bf - 0.22, Z_ST - 0.08], 0.020, 'ปากก๊อกซิงค์')
    cur = xc
for k, xh in enumerate((23.00, 22.20, 20.00, 19.00, 17.20)):
    cw_hang(f'{CW}-SH-HG{k+1}', [xh, y_ws, zW], '1/2', Z_CEIL, 'ท้องพื้นชั้น 2')
# 6.3 ห้องน้ำหญิง 3/4": จากปลายเมน → +y → บอลวาล์ว → ผนังกั้นกลาง +2.70 → สามทาง → ก๊อกอ่างรวม 3 จุด / ผนังกริด 10 ดิ่งลง +0.20 → สต็อปวาล์วชักโครก 3 ตัว
n3_wpipe(f'{CW}-W-P01', [x_wt, yWm + h114, zW], [x_wt, 9.40 - 0.045, zW], '3/4', 'ท่อน้ำดีห้องน้ำหญิง ชั้น 1')
cw_valve(f'{CW}-W-V', [x_wt, 9.40, zW], [0, 1, 0], '3/4', 'บอลวาล์วทองเหลือง ห้องน้ำหญิง')
n3_wpipe(f'{CW}-W-P02', [x_wt, 9.40 + 0.045, zW], [x_wt, yMW - h34, zW], '3/4', 'ท่อน้ำดีห้องน้ำหญิง ชั้น 1')
cw_tee(f'{CW}-W', [x_wt, yMW, zW], '3/4', 'สี่ทางลด 3/4"x1/2" (ทิศ −x, +x, +y)')
cw_hang(f'{CW}-W-HG1', [x_wt, 8.625, zW], '3/4', Z_BSOF, 'ท้องคาน B2-C9-10', ax=(0, 1, 0))
cw_hang(f'{CW}-W-HG2', [x_wt, 9.70, zW], '3/4', Z_CEIL, 'ท้องพื้นชั้น 2', ax=(0, 1, 0))
cw_mw_drops(f'{CW}-WU', (30.38, 29.70), x_wt, '1/2', 'หญิง')
x_g10 = 31.64
cw_mw_drops(f'{CW}-WE', (31.06,), x_wt, '1/2', 'หญิง')
# เปลี่ยนข้องอที่ 31.06 เป็นสามทาง แล้วเดินต่อไปผนังกริด 10
_el = next(e for e in elements if e['id'] == f'{CW}-WE-EL01')
_el['id'] = f'{CW}-WE-TE01'; _el['name'] = _el['name'].replace('ข้องอ 90°', 'สามทาง'); _el['qty']['type'] = 'สามทาง'
y_wvW = {}
for j in (3, 2, 1):
    wc = next(e for e in elements if e['id'] == f'FX-F1-WC2-{j}')
    ys = [_YM - q[1] for q in wc['geom']['poly']]
    y_wvW[j] = round((max(ys) + 0.07) if j > 1 else (min(ys) - 0.07), 4)      # ข้างชักโครก ด้านที่ไม่ติดประตู
# ชักโครกหญิง 3 (ติดผนังกั้นกลาง): ต่อจากสายตะวันออกในผนังกั้นกลาง → ผนังกริด 10 → ดิ่งลง +0.20 → สต็อปวาล์ว (ไม่ผ่านเสาเอ็น G10-TC1)
cw_run(f'{CW}-WW', [[31.06, yMW, zW], [x_g10, yMW, zW], [x_g10, 10.60, zW], [x_g10, 10.60, Z_WV], [x_g10, y_wvW[3], Z_WV]], '1/2',
       'ท่อน้ำดีชักโครกหญิง ห้อง 3 (ฝังผนังกั้นกลาง/ผนังกริด 10)', h12, h12)
n3_wfit(_f1id(f'{CW}-WW', 'EL'), [x_g10, y_wvW[3], Z_WV], '1/2', 'ข้องอ 90°')
cw_wc_valve(f'{CW}-WW', x_g10, 31.59, -1, y_wvW[3], 'หญิง')
# ชักโครกหญิง 2, 1: ท่อ 1/2" ต่อจากสามทางผนังกั้นกลาง เดินต่อ +y เหนือผนังกั้นห้องส้วม (+2.70) → ผนังกริด 10 ที่ห้อง 2 → ดิ่งลง +0.20 → สามทาง → ห้อง 1
n3_wpipe(f'{CW}-W-P03', [x_wt, yMW + h34, zW], [x_wt, y_wvW[2] - h12, zW], '1/2', 'ท่อน้ำดีชักโครกหญิง ห้อง 1–2 (+2.70 เหนือผนังกั้นห้องส้วม)')
cw_run(f'{CW}-WN', [[x_wt, y_wvW[2], zW], [x_g10, y_wvW[2], zW], [x_g10, y_wvW[2], Z_WV]], '1/2', 'ท่อน้ำดีชักโครกหญิง ห้อง 1–2 (ฝังผนังกริด 10)', h12, h12)
n3_wfit(_f1id(f'{CW}-WN', 'EL'), [x_wt, y_wvW[2], zW], '1/2', 'ข้องอ 90°')
cw_tee(f'{CW}-WN', [x_g10, y_wvW[2], Z_WV], '1/2')
cw_wc_valve(f'{CW}-WN', x_g10, 31.59, -1, y_wvW[2], 'หญิง')
n3_wpipe(_f1id(f'{CW}-WN', 'P'), [x_g10, y_wvW[2] + h12, Z_WV], [x_g10, y_wvW[1] - h12, Z_WV], '1/2', 'ท่อน้ำดีชักโครกหญิง ห้อง 1 (ฝังผนังกริด 10)')
n3_wfit(_f1id(f'{CW}-WN', 'EL'), [x_g10, y_wvW[1], Z_WV], '1/2', 'ข้องอ 90°')
cw_wc_valve(f'{CW}-WN', x_g10, 31.59, -1, y_wvW[1], 'หญิง')
cw_hang(f'{CW}-W-HG3', [x_wt, 11.90, zW], '1/2', Z_CEIL, 'ท้องพื้นชั้น 2', ax=(0, 1, 0))
ASSUMPTIONS.append('ระบบท่อห้องน้ำชาย-หญิง ชั้น 1 + ซิงค์หลังร้านค้า (24 พ.ย. 2569): ชักโครก/โถปัสสาวะลงท่อรวมโซน 3 (ถัง Z3-1) — ย้ายช่องล้างต้นสายโซน 3 ไป y 10.95 รับท่อส้วม 4" ชาย/หญิงด้วยวายลด 150x100 ลาด 1:50, '
                   'ท่อส้วมชายลอดคาน GB1-9 ด้วยท่อปลอก ø150; อ่างล้างหน้า อ่างล้างมือรวม ฟลอร์เดรน (ห้องละ 1 จุด) ลงท่อน้ำทิ้ง 4" ลาด 1:100 ลึกใต้คานคอดิน เข้าท่อรวม ø150 โซน 2 ฝั่งกริด 10 ที่ x 26.40; '
                   'ซิงค์ DYNA HOME DH-7545-TB 75x45 3 ร้าน ชิดเสาฝั่งหน้าต่าง P-trap 2" ลงท่อน้ำทิ้ง 4" ใต้พื้นร้าน ลาด 1:100 เข้าท่อรวม ø150 โซน 2 ฝั่งกริด 5 ที่ x 23.30 (ผู้ใช้); '
                   'น้ำดี: สามทางลดบนท่อดิ่ง 2" ผนังกริด 1 ที่ +3.25 → เมน 1¼" +2.70 แนวทางเดิน (ห่างคาน B2-C 0.30) → ห้องน้ำชาย/หญิง 3/4" มีบอลวาล์ว → 1/2" ฝังผนัง: ฟลัชวาล์ว +1.15, ก๊อกอ่างรวม +0.80, วาล์วอ่าง +0.55, สต็อปวาล์วชักโครก +0.20; '
                   'ก๊อกซิงค์ VEGARR VHY1108F ติดผนังหลังร้าน +1.05 ท่อ 1/2" ต่อจากห้องน้ำชายเดินในร้านชิดผนังหลัง +2.70; ระดับ/ตำแหน่งท่อ ระยะ ความสูงอุปกรณ์ ความสูงซิงค์ 0.80 ท่อออกโถปัสสาวะ +0.35 (ผมกำหนด); '
                   'ห้องน้ำชั้น 1 ยังไม่มีท่ออากาศ (รอผู้ใช้ตัดสินใจ)')

# =====================================================================
# งานระบบไฟฟ้าเมน + ไฟฟ้าร้านค้า/ห้องน้ำชั้น 1 (วิวัฒน์สั่ง 25 พ.ย. 2569; ยืนยันข้อเสนอ "ตามนี้ได้เลย")
# - ตู้ทุกชั้นติดผนังโถงบันไดด้าน B (กริด 5, ผิวฉาบ x = 13.95) ช่วงระหว่างเสา C1-5C กับขอบช่องบันได
# - ชั้น 1: ตู้ MDB + ตู้มิเตอร์ 4 ลูก (ร้านค้า 3 + ห้องน้ำรวม 1) / ชั้น 2–5: ตู้ DB + ตู้มิเตอร์ 17 ลูก
# - สายเมนจาก MDB ขึ้นแต่ละชั้นในท่อ EMT 1¼" แนวดิ่ง (ชั้นละ 1 ท่อ) ลอดพื้นข้างคาน B1-5-BC
# - สายจากมิเตอร์ไปตู้ห้อง: รางวายเวย์ 100x100 ใต้ท้องคานทางเดิน + ท่อ EMT ½" แยกลงตู้ห้อง ลอดผนังทางเดินเข้าหลังตู้
# พิกัดในบล็อกนี้เขียนเป็นพิกัด elements.json (กลับแกน y แล้ว) แล้วแปลงกลับก่อนเก็บ
# ขนาดตู้ ขนาดสาย ขนาดท่อ เป็นค่าสมมติจากการคำนวณโหลดห้องละ 15A (แสดงวิธีคิดใน BOQ) ต้องให้วิศวกรไฟฟ้ารับรอง
# =====================================================================
EMT = {'1/2': 0.0179, '3/4': 0.0234, '1': 0.0295, '1-1/4': 0.0421}     # โตนอกท่อ EMT (ม.)
X_HALL = 13.95                                   # ผิวฉาบผนังโถงบันไดด้าน B (ฝั่งโถง)
X_RS = 13.845                                    # แนวศูนย์ท่อสายเมนแนวดิ่ง (พ้นผิวฉาบคาน B1-5-BC x = 13.8725)
Y_RS = {5: 9.10, 4: 9.16, 3: 9.22, 2: 9.28}      # แนวท่อสายเมนแต่ละชั้น (ชั้นสูงสุดชิดเสา)
ZC0, ZC1 = 2.495, 2.595                          # รางวายเวย์ช่วงทางเดิน ชิดผิวฉาบท้องคานซอยขวางทางเดิน (FL+2.595) ท่อน้ำเข้ามิเตอร์ (สูงสุด FL+2.477) อยู่ต่ำกว่าราง (วิวัฒน์สั่ง 25 พ.ย. 2569)
ZW0, ZW1 = ZC0, ZC1                              # รางวายเวย์ช่วงโถงบันได ระดับเดียวกับทางเดิน ชิดผิวฉาบท้องคาน B2 แนว C (FL+2.595) ท่อเมนน้ำ (สูงสุด FL+2.471) อยู่ต่ำกว่า
Y_WW = (7.70, 7.80)                              # รางวายเวย์กลางทางเดิน
X_WWH = (13.70, 13.80)                           # รางวายเวย์ช่วงโถงบันได (พ้นผิวฉาบเสา C1-5C x = 13.815)
DB_Y, MP_Y = (9.34, 9.74), (9.82, 11.02)         # ตู้ DB / ตู้มิเตอร์ 17 ลูก ชั้น 2–5
F1C = FL[2] - SLAB_T - PL_T - 0.012              # แนวท่อใต้ท้องพื้นชั้น 2 (ชั้น 1)


def _jy(y):
    return round(_YM - y, 4)


def ej_box(x0, x1, y0, y1, z0, z1):
    return prism([(x0, _jy(y0)), (x1, _jy(y0)), (x1, _jy(y1)), (x0, _jy(y1))], z0, z1 - z0)


def ej_run(pts, od):
    """ท่อแนวเส้นหลายช่วง (พิกัด json) คืน geom, ความยาว, จำนวนมุมหัก"""
    pts = [list(p) for p in pts]
    parts = [dict(type='member', p0=[round(v, 4) for v in _J(a)], p1=[round(v, 4) for v in _J(b)], w=od, d=od, shape='O', sec=dict(d=od))
             for a, b in zip(pts, pts[1:]) if math.dist(a, b) > 1e-4]
    L = sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))
    bends = 0
    for a, b, c in zip(pts, pts[1:], pts[2:]):
        u = [b[k] - a[k] for k in range(3)]; v = [c[k] - b[k] for k in range(3)]
        if math.dist(a, b) > 1e-4 and math.dist(b, c) > 1e-4 and abs(sum(u[k] * v[k] for k in range(3))) < 1e-6 * max(1e-9, math.dist(a, b) * math.dist(b, c)) + 1e-9:
            bends += 1
    return (parts[0] if len(parts) == 1 else dict(type='multi', parts=parts)), round(L, 3), bends


def em_add(eid, f, geom, name, qty):
    add(eid, 'ไฟฟ้า', f, 'A21', geom, name=name, assumed=True, qty=qty)


def emt_add(eid, f, pts, size, name, cable, qty=None):
    g, L, nb = ej_run(pts, EMT[size])
    q = dict(length=L, size=f'EMT {size}"', bend_90=nb, connector=2, cable=cable, part='เมน')
    em_add(eid, f, g, name, q | (qty or {}))
    return L


def pvc_add(eid, f, runs, name, part, qty=None):
    """ท่อ PVC ขาว 20 มม. ในร้านค้า/ห้องน้ำ (เหมือนห้องพัก) runs = รายการ polyline"""
    parts, L, nb = [], 0.0, 0
    for r in runs:
        g, l, b = ej_run(r, EL_PIPE)
        parts += g['parts'] if g['type'] == 'multi' else [g]
        L += l; nb += b
    em_add(eid, f, dict(type='multi', parts=parts), name, dict(length=round(L, 3), size='PVC ขาว 20 มม.', bend_90=nb, part=part) | (qty or {}))
    return L


# ---------- ชั้น 1: ตู้ MDB + ตู้มิเตอร์ 4 ลูก ----------
fl1 = FL[1]
em_add('EM-F1-MDB', 1, ej_box(13.65, X_HALL, 9.06, 9.86, fl1 + 0.80, fl1 + 2.00),
       'ตู้ MDB ชั้น 1 โถงบันได (ขนาดสมมติ 0.80x1.20x0.30) เมน 3P 250AT จ่ายตู้ DB ชั้น 2–5 และตู้มิเตอร์ชั้น 1',
       dict(count=1, size='0.80x1.20x0.30', main='3P 250AT', feeders='3P 63AT x4 (ชั้น 2–5), 3P 40AT x1 (ตู้มิเตอร์ชั้น 1)', part='เมน', panel='MDB'))
em_add('EM-F1-MP', 1, ej_box(13.70, X_HALL, 9.95, 10.55, fl1 + 0.80, fl1 + 1.60),
       'ตู้มิเตอร์ 4 ลูก ชั้น 1 (ร้านค้า 3 + ห้องน้ำรวม 1) ขนาดสมมติ 0.60x0.80x0.25',
       dict(count=1, size='0.60x0.80x0.25', meters=4, meter='15(45)A 1 เฟส', breaker='1P 20A x3 (ร้านค้า), 1P 16A x1 (ห้องน้ำรวม)', part='เมน', panel='MP'))
emt_add('EM-F1-FD-MP', 1, [(13.80, 9.70, fl1 + 2.00), (13.80, 9.70, fl1 + 2.25), (13.80, 10.45, fl1 + 2.25), (13.80, 10.45, fl1 + 1.60)], '1',
        'ท่อ EMT 1" สาย MDB → ตู้มิเตอร์ชั้น 1', 'THW 4x10 + G 6 ตร.มม.', dict(load='3P 40AT'))
# ---------- สายเมนขึ้นชั้น 2–5 + ตู้ DB + ตู้มิเตอร์ 17 ลูก ----------
for f in (2, 3, 4, 5):
    fl = FL[f]
    yr = Y_RS[f]
    # ชั้น 5 ทางเดินไม่มีคาน คสล. → รางชิดใต้ขื่อเหล็กหลังคา (ท้องขื่อ RB, วิวัฒน์เลือก 25 พ.ย. 2569)
    zc0, zc1 = (ZC0, ZC1) if f < 5 else (RB - fl - 0.10, RB - fl)
    zw0, zw1 = (ZW0, ZW1) if f < 5 else (zc0, zc1)
    ydb = (DB_Y[0] + DB_Y[1]) / 2
    emt_add(f'EM-RS-F{f}', f, [(X_RS, yr, fl1 + 2.00), (X_RS, yr, fl + 2.25), (X_RS, ydb, fl + 2.25), (X_RS, ydb, fl + 1.80)], '1-1/4',
            f'ท่อ EMT 1¼" สายเมน MDB → ตู้ DB ชั้น {f} (แนวดิ่งโถงบันได)', 'THW 4x16 + G 10 ตร.มม.',
            dict(load='3P 63AT', slab_cross=f - 1))
    em_add(f'EM-F{f}-DB', f, ej_box(13.80, X_HALL, DB_Y[0], DB_Y[1], fl + 1.30, fl + 1.80),
           f'ตู้ DB ชั้น {f} (ตู้สาขา 3 เฟส เมน 3P 63AT จ่ายบัสบาร์ตู้มิเตอร์) ขนาดสมมติ 0.40x0.50x0.15',
           dict(count=1, size='0.40x0.50x0.15', main='3P 63AT', part='เมน', panel='DB'))
    em_add(f'EM-F{f}-MP', f, ej_box(13.70, X_HALL, MP_Y[0], MP_Y[1], fl + 0.80, fl + 2.00),
           f'ตู้มิเตอร์ 17 ลูก ชั้น {f} ขนาดสมมติ 1.20x1.20x0.25 (6x3 ช่อง)',
           dict(count=1, size='1.20x1.20x0.25', meters=17, meter='15(45)A 1 เฟส', breaker='1P 20A x17', part='เมน', panel='MP'))
    emt_add(f'EM-F{f}-DBMP', f, [(13.875, DB_Y[1], fl + 1.55), (13.875, MP_Y[0], fl + 1.55)], '1-1/4',
            f'ท่อ EMT 1¼" ต่อตู้ DB → ตู้มิเตอร์ ชั้น {f}', 'THW 4x16 + G 10 ตร.มม.')
    # รางวายเวย์: ท่อนตั้งเหนือตู้มิเตอร์ → แนวโถงบันได → แนวทางเดิน
    ym = (MP_Y[0] + MP_Y[1]) / 2
    ww = [ej_box(X_WWH[0], X_WWH[1], ym - 0.05, ym + 0.05, fl + 2.00, fl + zw0),
          ej_box(X_WWH[0], X_WWH[1], Y_WW[1], ym + 0.05, fl + zw0, fl + zw1)]
    # ปลายรางทางเดิน: ถึงแนวท่อแยกลงตู้ห้องริมสุด
    cus = [e for e in elements if re.match(rf'^EL-F{f}-[NS]\d-CU$', e['id'])]
    xs = [sum(p[0] for p in e['geom']['poly']) / 4 for e in cus]
    xa, xb = min(xs) - 0.06, max(xs) + 0.06
    ww.append(ej_box(X_WWH[0], X_WWH[1], Y_WW[0], Y_WW[1], fl + zw0, fl + zc1))      # ช่วงสามทาง โถง → ทางเดิน (ระดับเดียวกัน)
    ww.append(ej_box(xa, xb, Y_WW[0], Y_WW[1], fl + zc0, fl + zc1))
    Lww = (zw0 - 2.00) + (ym + 0.05 - Y_WW[1]) + (xb - xa)
    em_add(f'EM-F{f}-WW', f, dict(type='multi', parts=ww),
           f'รางวายเวย์ 100x100 มม. ชั้น {f} จากตู้มิเตอร์ไปตาม' + ('ใต้ท้องคานทางเดิน' if f < 5 else 'ใต้ขื่อเหล็กหลังคา (ชั้น 5 ไม่มีคานทางเดิน)'),
           dict(length=round(Lww, 3), size='วายเวย์ 100x100 มม.', elbow=1, tee=1, end_cap=2, part='เมน'))
    # ท่อแยกลงตู้ห้อง: ออกข้างราง → (ชั้น 5 ลงแนวดิ่ง) → ลอดผนังทางเดินเหนือท่อน้ำ → ลงชิดผนังด้านในห้องเข้าด้านบนตู้
    for e in sorted(cus, key=lambda e: e['id']):
        tag = e['id'][3:-3]
        poly = e['geom']['poly']
        xc = sum(p[0] for p in poly) / 4
        yj = [_jy(p[1]) for p in poly]
        zc = e['geom']['z0'] + e['geom']['t'] / 2
        s = 'N' if '-N' in tag else 'S'
        if s == 'S':      # ห้องฝั่ง y ต่ำ: ผนังทางเดิน 6.93–7.00 ตู้อยู่ด้านห้อง y ≤ 6.915
            yw0, yface, yback = Y_WW[0], 7.253 + 0.009 + 0.010, max(yj)       # ลงแนวดิ่งก่อนถึงผิวฉาบคาน B2 แนว D (y 7.253)
        else:
            yw0, yface, yback = Y_WW[1], 8.248 - 0.009 - 0.010, min(yj)       # ลงแนวดิ่งก่อนถึงผิวฉาบคาน B2 แนว C (y 8.248)
        zr = fl + (zc0 + zc1) / 2
        # ลอดผนังทางเดินเหนือท่อน้ำเข้ามิเตอร์ (ท่อน้ำสูงสุด FL+2.477) ที่ FL+2.545 แล้วลงแนวดิ่งชิดผนังด้านในห้องเข้าหลังตู้ด้านบน (วิวัฒน์สั่ง 25 พ.ย. 2569)
        zp = fl + (ZC0 + ZC1) / 2
        ztop = e['geom']['z0'] + e['geom']['t']
        yin = yback + (0.0179 / 2 + 0.01) * (-1 if s == 'S' else 1)      # แนวดิ่งในห้อง ห่างผิวผนังด้านในห้อง 1 ซม.
        # ลอดผนังก่อที่แนวกลางตู้ (พ้นเสาเอ็น TC1) แล้วเลี้ยวเลียบผนังในห้องเหนือกล่องพักสาย JB1 ไปลงด้านบนตู้ฝั่งเสา (เลี่ยง JB1 และท่อในห้องที่ออกจากกลางตู้)
        xd = min(p[0] for p in poly) + 0.03
        pts = [(xc, yw0, zr)] + ([(xc, yface, zr), (xc, yface, zp)] if abs(zr - zp) > 1e-6 else []) + [(xc, yin, zp), (xd, yin, zp), (xd, yin, ztop)]
        # ความยาวสายจากตู้มิเตอร์: ท่อนตั้ง + แนวโถง + แนวทางเดินถึงจุดแยก + ท่อแยก
        Lc = (zw0 - 2.00 + 0.05) + (zc1 - zw0) + abs(ym - (Y_WW[0] + Y_WW[1]) / 2) + abs(xc - (X_WWH[0] + X_WWH[1]) / 2)
        emt_add(f'EM-FD-{tag}', f, pts, '1/2', f'ท่อ EMT ½" สายจากมิเตอร์ → ตู้คอนซูมเมอร์ ชั้น {f} ห้อง {tag.split("-")[1]}',
                'THW 2x4 + G 2.5 ตร.มม.', dict(cable_in_wireway=round(Lc, 3), load='1P 20A (โหลด 15A)'))
ASSUMPTIONS.append('งานไฟฟ้าเมน: ตู้ทุกชั้นติดผนังโถงบันไดด้าน B (กริด 5) ช่วง y 9.06–11.02; ขนาดตู้ MDB 0.80x1.20x0.30, ตู้มิเตอร์ 17 ลูก 1.20x1.20x0.25, ตู้มิเตอร์ 4 ลูก 0.60x0.80x0.25, '
                   'ตู้ DB 0.40x0.50x0.15 เป็นค่าสมมติ; ท่อสายเมน EMT 1¼" แนวดิ่ง x = 13.845 เจาะพื้นสำเร็จรูปข้างคาน B1-5-BC; รางวายเวย์ 100x100 ช่วงทางเดินชิดท้องคานซอย FL+2.495–2.595 ช่วงโถงบันไดระดับเดียวกัน ชั้น 5 ชิดใต้ขื่อเหล็กหลังคา กลางทางเดิน; '
                   'ท่อแยก EMT ½" ลอดผนังทางเดินที่ FL+2.545 เหนือท่อน้ำเข้ามิเตอร์ แล้วลงแนวดิ่งชิดผนังด้านในห้องเข้าด้านบนตู้คอนซูมเมอร์')

# ---------- ชั้น 1: สายจากตู้มิเตอร์ไปร้านค้า 3 ร้าน และห้องน้ำรวม ----------
_SHX = {1: GX[4], 2: GX[5], 3: GX[6]}           # ขอบซ้ายร้าน (กริด 5, 6, 7)
_FY = {1: 10.34, 2: 10.28, 3: 10.22, 'WC': 10.16}
Y_CU1 = 10.25                                    # กึ่งกลางตู้คอนซูมเมอร์ร้าน บนผนังด้านซ้าย
Z_F1 = fl1 + 2.30                                # แนวท่อสายจากมิเตอร์ลอดผนังกั้นร้าน (ใต้คาน 2.90)
for k in (1, 2, 3, 'WC'):
    y = _FY[k]
    xe = (_SHX[k] + 0.10) if k != 'WC' else 24.55
    pts = [(13.93, y, fl1 + 1.60), (13.93, y, Z_F1), (xe, y, Z_F1)]
    if k != 'WC':
        pts.append((xe, y, fl1 + 1.80 + EL_CU[1]))
    emt_add(f'EM-FD-F1-{"SH" + str(k) if k != "WC" else "WC"}', 1, pts, '1/2',
            f'ท่อ EMT ½" สายจากมิเตอร์ → {"ตู้คอนซูมเมอร์ร้านค้า " + str(k) if k != "WC" else "กล่องต่อสายห้องน้ำรวมชั้น 1"} (ลอดผนังกั้นร้านใต้คาน)',
            'THW 2x4 + G 2.5 ตร.มม.' if k != 'WC' else 'THW 2x2.5 + G 2.5 ตร.มม.', dict(load='1P 20A' if k != 'WC' else '1P 16A'))

# ---------- ไฟฟ้าในร้านค้า 3 ร้าน (ร้านละ: ตู้คอนซูมเมอร์ 1, โคม T8 1x18W 2, สวิตช์ 1, เต้ารับคู่ 3 (1 จุดที่ซิงค์)) ----------
for k, x0 in _SHX.items():
    tag, nm = f'F1-SH{k}', f'ร้านค้า {k}'
    xl, xr = x0 + 0.05, x0 + 3.45                # ผิวฉาบผนังซ้าย/ขวา (ด้านในร้าน)
    em_add(f'EL-{tag}-CU', 1, ej_box(xl, xl + EL_CU[2], Y_CU1 - EL_CU[0] / 2, Y_CU1 + EL_CU[0] / 2, fl1 + 1.80, fl1 + 1.80 + EL_CU[1]),
           f'ตู้คอนซูมเมอร์ 4 วงจร {nm} ผนังด้านซ้าย สูง 1.80', dict(count=1, model='RACER เมน+4 ช่อง', bottom=1.80, part='ใน'))
    em_add(f'EL-{tag}-SW1', 1, ej_box(xl, xl + EL_BOX[2], 9.30 - EL_BOX[0] / 2, 9.30 + EL_BOX[0] / 2, fl1 + EL_SW_Z - EL_BOX[1] / 2, fl1 + EL_SW_Z + EL_BOX[1] / 2),
           f'สวิตช์ไฟ 1 จุด (โคม 2 ชุด) {nm} ผนังด้านซ้ายใกล้หน้าร้าน', dict(count=1, box='บล็อกลอย 2x4 นิ้ว', gang=1, height=EL_SW_Z, part='ใน'))
    for j, yl in ((1, 10.40), (2, 12.20)):
        xm = x0 + 1.75
        em_add(f'EL-{tag}-LP{j}', 1, ej_box(xm - EL_LAMP[0] / 2, xm + EL_LAMP[0] / 2, yl - EL_LAMP[1] / 2, yl + EL_LAMP[1] / 2, F1C + 0.012 - EL_LAMP[2], F1C + 0.012),
               f'โคมรางตัวยู T8 1x18W {nm} ชุดที่ {j}', dict(count=1, model='T8 1x18 หลอดเดี่ยว', part='ใน'))
    sos = ((1, xl, Y_CU1, 0.30, 1, 'ผนังด้านซ้ายใต้ตู้'), (2, xr, 11.00, 0.30, -1, 'ผนังด้านขวา'), (3, xr, 13.10, 1.10, -1, 'ข้างซิงค์ เหนือเคาน์เตอร์'))
    for j, xw, yo, hz, dn, where in sos:
        xa, xb = sorted((xw, xw + dn * EL_BOX[2]))
        em_add(f'EL-{tag}-SO{j}', 1, ej_box(xa, xb, yo - EL_BOX[0] / 2, yo + EL_BOX[0] / 2, fl1 + hz - EL_BOX[1] / 2, fl1 + hz + EL_BOX[1] / 2),
               f'เต้ารับคู่ {nm} {where} สูง {hz:.2f}', dict(count=1, box='บล็อกลอย 2x4 นิ้ว', outlets=2, height=hz, part='ใน'))
    cx = x0 + 0.10                               # ศูนย์ตู้/ท่อบนผนังซ้าย
    z28 = fl1 + 2.50                              # ใต้ท้องคาน (2.90 - ฉาบ) แนวหลบคานกริด
    cu_t, cu_b = fl1 + 1.80 + EL_CU[1], fl1 + 1.80
    lit = [[(cx, Y_CU1, cu_t), (cx, Y_CU1, z28), (cx, 9.30, z28), (cx, 9.30, fl1 + EL_SW_Z + EL_BOX[1] / 2)],
           [(cx, Y_CU1, z28), (x0 + 0.30, Y_CU1, z28), (x0 + 0.30, Y_CU1, F1C), (x0 + 0.30, 10.40, F1C), (x0 + 1.75 - EL_LAMP[0] / 2, 10.40, F1C)],
           [(x0 + 0.30, 10.40, F1C), (x0 + 0.30, 12.20, F1C), (x0 + 1.75 - EL_LAMP[0] / 2, 12.20, F1C)]]
    pvc_add(f'EL-{tag}-CD1', 1, lit, f'ท่อร้อยสาย PVC ขาว 20 มม. วงจรแสงสว่าง {nm}', 'ใน', dict(circuit='แสงสว่าง', wire='THW 2x1.5', points=4))
    xs_ = xr - 0.0125
    so = [[(cx, Y_CU1, cu_b), (cx, Y_CU1, fl1 + 0.30 + EL_BOX[1] / 2)],
          [(x0 + 0.30, 12.20, F1C), (x0 + 3.20, 12.20, F1C), (x0 + 3.20, 13.10, F1C), (x0 + 3.20, 13.10, z28), (xs_, 13.10, z28), (xs_, 13.10, fl1 + 1.10 + EL_BOX[1] / 2)],
          [(x0 + 3.20, 12.20, F1C), (x0 + 3.20, 11.00, F1C), (x0 + 3.20, 11.00, z28), (xs_, 11.00, z28), (xs_, 11.00, fl1 + 0.30 + EL_BOX[1] / 2)]]
    pvc_add(f'EL-{tag}-CD2', 1, so, f'ท่อร้อยสาย PVC ขาว 20 มม. วงจรเต้ารับ {nm} (ใช้ท่อร่วมกับวงจรแสงสว่างช่วงเพดาน)', 'ใน',
            dict(circuit='เต้ารับ', wire='THW 2x2.5 + G 2.5', points=4))

# ---------- ไฟฟ้าห้องน้ำรวมชั้น 1 (ห้องละ: โคมซาลาเปา LED 2, สวิตช์ 1 จุด, พัดลมดูดอากาศ 1) ----------
em_add('EL-F1-WC-JB', 1, ej_box(24.55, 24.60, _FY['WC'] - 0.05, _FY['WC'] + 0.05, Z_F1 - 0.05, Z_F1 + 0.05),
       'กล่องต่อสาย 4x4 นิ้ว รับสายจากมิเตอร์ห้องน้ำรวม (ผนังกริด 8 ด้านห้องน้ำชาย)', dict(count=1, size='4x4 นิ้ว', part='ใน'))
LED_R, LED_H = 0.125, 0.06                         # โคมซาลาเปา LED Ø0.25 สูง 0.06 (ค่าสมมติ)
FAN = (0.25, 0.25, 0.10)                           # พัดลมดูดอากาศติดผนัง 8 นิ้ว (กว้าง สูง ลึก) ค่าสมมติ


def _led(xc, yc):
    n = 16
    return prism([(xc + LED_R * math.cos(2 * math.pi * k / n), _jy(yc + LED_R * math.sin(2 * math.pi * k / n))) for k in range(n)][::-1],
                 F1C + 0.012 - LED_H, LED_H)


_WC = {1: dict(nm='ห้องน้ำชาย', L1=(26.25, 9.55), L2=(27.10, 12.10), fan=27.60, sw=26.70),
       2: dict(nm='ห้องน้ำหญิง', L1=(29.68, 9.55), L2=(28.90, 12.10), fan=29.55, sw=30.35)}
for k, d in _WC.items():
    tag = f'F1-WC{k}'
    for j in (1, 2):
        em_add(f'EL-{tag}-LP{j}', 1, _led(*d[f'L{j}']), f'โคมซาลาเปา LED ติดเพดาน {d["nm"]} ชั้น 1 ชุดที่ {j}',
               dict(count=1, model='โคมซาลาเปา LED (ยังไม่ระบุรุ่น)', part='ใน'))
    em_add(f'EL-{tag}-SW1', 1, ej_box(d['sw'] - EL_BOX[0] / 2, d['sw'] + EL_BOX[0] / 2, 8.80, 8.80 + EL_BOX[2], fl1 + EL_SW_Z - EL_BOX[1] / 2, fl1 + EL_SW_Z + EL_BOX[1] / 2),
           f'สวิตช์ 1 จุด (โคม 2 ชุด + พัดลมดูดอากาศ) {d["nm"]} ชั้น 1 ข้างทางเข้า', dict(count=1, box='บล็อกลอย 2x4 นิ้ว', gang=2, height=EL_SW_Z, part='ใน'))
    em_add(f'EL-{tag}-FAN', 1, ej_box(d['fan'] - FAN[0] / 2, d['fan'] + FAN[0] / 2, 13.80 - FAN[2], 13.80, fl1 + 2.15 - FAN[1] / 2, fl1 + 2.15 + FAN[1] / 2),
           f'พัดลมดูดอากาศติดผนัง 8 นิ้ว {d["nm"]} ชั้น 1 ผนังหลัง (แนว B) สูง 2.15', dict(count=1, model='พัดลมดูดอากาศ 8 นิ้ว (ยังไม่ระบุรุ่น)', part='ใน'))
z28 = fl1 + 2.50
ysw = 8.80 + 0.0125
wc = [[(24.60, 10.16, Z_F1), (24.80, 10.16, Z_F1), (24.80, 10.16, F1C), (24.80, 9.55, F1C), (26.25, 9.55, F1C)],          # → โคม 1 ห้องน้ำชาย
      [(24.80, 10.16, F1C), (24.80, 12.10, F1C), (27.10, 12.10, F1C)],                                                   # → โคม 2 ห้องน้ำชาย
      [(26.25, 9.55, F1C), (26.70, 9.55, F1C), (26.70, 9.05, F1C), (26.70, 9.05, z28), (26.70, ysw, z28), (26.70, ysw, fl1 + EL_SW_Z + EL_BOX[1] / 2)],   # สวิตช์ชาย
      [(27.10, 12.10, F1C), (27.60, 12.10, F1C), (27.60, 13.50, F1C), (27.60, 13.50, z28), (27.60, 13.75, z28), (27.60, 13.75, fl1 + 2.15 + FAN[1] / 2)],  # พัดลมชาย
      [(27.60, 12.10, F1C), (27.60, 12.10, z28), (28.40, 12.10, z28), (28.40, 12.10, F1C), (28.90, 12.10, F1C)],         # ลอดผนังกริด 9 → โคม 2 ห้องน้ำหญิง
      [(28.40, 12.10, F1C), (28.40, 9.55, F1C), (29.68, 9.55, F1C)],                                                    # → โคม 1 ห้องน้ำหญิง
      [(29.68, 9.55, F1C), (30.35, 9.55, F1C), (30.35, 9.05, F1C), (30.35, 9.05, z28), (30.35, ysw, z28), (30.35, ysw, fl1 + EL_SW_Z + EL_BOX[1] / 2)],   # สวิตช์หญิง
      [(28.90, 12.10, F1C), (29.55, 12.10, F1C), (29.55, 13.50, F1C), (29.55, 13.50, z28), (29.55, 13.75, z28), (29.55, 13.75, fl1 + 2.15 + FAN[1] / 2)]]  # พัดลมหญิง
pvc_add('EL-F1-WC-CD1', 1, wc, 'ท่อร้อยสาย PVC ขาว 20 มม. วงจรแสงสว่าง/พัดลมดูดอากาศ ห้องน้ำรวมชั้น 1', 'ใน', dict(circuit='แสงสว่าง+พัดลม', wire='THW 2x1.5', points=9))
ASSUMPTIONS.append('ไฟฟ้าร้านค้า/ห้องน้ำชั้น 1: ร้านละตู้คอนซูมเมอร์ 1 (ผนังซ้าย สูง 1.80), โคม T8 1x18W 2, สวิตช์ 1, เต้ารับคู่ 3 (ใต้ตู้, ผนังขวา, ข้างซิงค์ +1.10); '
                   'ห้องน้ำชาย/หญิง ห้องละโคมซาลาเปา LED 2 สวิตช์ 1 พัดลมดูดอากาศ 8 นิ้วติดผนังหลัง 1 รับไฟจากมิเตอร์ลูกที่ 4 ตู้มิเตอร์ชั้น 1 ผ่านกล่องต่อสาย (ไม่มีตู้คอนซูมเมอร์); '
                   'ท่อ PVC ขาว 20 มม. เดินลอยใต้ท้องพื้นชั้น 2 และผนัง ตำแหน่งอุปกรณ์ผมกำหนด')

ASSUMPTIONS.append('พิกัดใน elements.json กลับแกน y แล้ว: กริด A อยู่ที่ y = 15.50, กริด F ที่ y = 0 (มุมมองด้านบนตรงกับแปลน)')

def _merge_rects(parts):
    """รวมสี่เหลี่ยมแกนตรงหลายชิ้น (z0/t เดียวกัน) เป็นรูปหลายเหลี่ยมเดียว (+รู) ต่อกลุ่มที่ต่อเนื่องกัน
    ใช้กับกระเบื้องพื้น: ให้พื้นเดียวกันเป็นผืนเดียวเนื้อเดียว ไม่เห็นรอยต่อชิ้น (แก้ 17 พ.ย. 2569)"""
    R = lambda v: round(v, 4)
    rects = []
    for p in parts:
        xs = sorted({R(x) for x, _ in p['poly']}); ys = sorted({R(y) for _, y in p['poly']})
        if len(p['poly']) != 4 or len(xs) != 2 or len(ys) != 2:
            return None
        rects.append((xs[0], ys[0], xs[1], ys[1]))
    X = sorted({v for r in rects for v in (r[0], r[2])}); Y = sorted({v for r in rects for v in (r[1], r[3])})
    full = set()
    for i in range(len(X) - 1):
        for j in range(len(Y) - 1):
            cx, cy = (X[i] + X[i + 1]) / 2, (Y[j] + Y[j + 1]) / 2
            if any(r[0] < cx < r[2] and r[1] < cy < r[3] for r in rects):
                full.add((i, j))
    # แยกกลุ่มเซลล์ที่ต่อกัน (ติดด้าน)
    comps, seen = [], set()
    for c in sorted(full):
        if c in seen:
            continue
        st, comp = [c], set()
        seen.add(c)
        while st:
            i, j = st.pop(); comp.add((i, j))
            for n in ((i + 1, j), (i - 1, j), (i, j + 1), (i, j - 1)):
                if n in full and n not in seen:
                    seen.add(n); st.append(n)
        comps.append(comp)
    out = []
    for comp in comps:
        # ขอบมีทิศ (ทวนเข็ม) ของเซลล์ที่ติดเซลล์ว่าง
        E = {}
        for i, j in comp:
            a, b, c, d = (X[i], Y[j]), (X[i + 1], Y[j]), (X[i + 1], Y[j + 1]), (X[i], Y[j + 1])
            if (i, j - 1) not in comp: E.setdefault(a, []).append(b)
            if (i + 1, j) not in comp: E.setdefault(b, []).append(c)
            if (i, j + 1) not in comp: E.setdefault(c, []).append(d)
            if (i - 1, j) not in comp: E.setdefault(d, []).append(a)
        loops = []
        while E:
            s = next(iter(E)); loop = [s]; cur = s
            while True:
                nx = E[cur].pop()
                if not E[cur]: del E[cur]
                if nx == s: break
                loop.append(nx); cur = nx
            # ตัดจุดกลางแนวตรง
            n = len(loop); keep = []
            for k in range(n):
                p0, p1, p2 = loop[k - 1], loop[k], loop[(k + 1) % n]
                if not ((p0[0] == p1[0] == p2[0]) or (p0[1] == p1[1] == p2[1])):
                    keep.append([p1[0], p1[1]])
            area = sum(keep[k][0] * keep[(k + 1) % len(keep)][1] - keep[(k + 1) % len(keep)][0] * keep[k][1] for k in range(len(keep))) / 2
            loops.append((area, keep))
        loops.sort(key=lambda t: -t[0])
        g = dict(type='prism', poly=loops[0][1], z0=parts[0]['z0'], t=parts[0]['t'])
        holes = [l for a, l in loops[1:]]
        if holes:
            g['holes'] = holes
        out.append(g)
    return out


def merge_tile_parts(e):
    g = e['geom']
    if e['category'] != 'กระเบื้อง' or g['type'] != 'multi':
        return
    ps = g['parts']
    if not all(p['type'] == 'prism' and not p.get('holes') for p in ps) or len({(p['z0'], p['t']) for p in ps}) != 1:
        return
    m = _merge_rects(ps)
    if m:
        e['geom'] = m[0] if len(m) == 1 else dict(type='multi', parts=m)


if __name__ == '__main__':
    for e in elements:
        merge_tile_parts(e)
        mirror_y(e['geom'])
        if 'finish' in e:
            e['finish']['origin'][1] = round(GY['F'] - e['finish']['origin'][1], 4)
        if 'component_place' in e:
            e['component_place']['pt'][1] = round(GY['F'] - e['component_place']['pt'][1], 4)
            e['component_place']['dir'][1] = -e['component_place']['dir'][1]
        if 'fitting' in e:
            _f = e['fitting']
            _f['origin'][1] = round(GY['F'] - _f['origin'][1], 4)
            if _f.get('anchor') != 'center':       # ข้อต่อสมมาตรตามระนาบ z ท้องถิ่น: กลับแกน y ได้; บ่อพัก (center) คงแกนเดิม
                _f['x'][1] = -_f['x'][1]
                _f['y'][1] = -_f['y'][1]
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
