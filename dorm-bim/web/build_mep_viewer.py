"""ข้อมูลหน้าเว็บดูงานระบบสุขาภิบาล + ไฟฟ้า หอพัก A (จาก elements.json + ชิ้นส่วนคอมโพเนนต์จาก SketchUp)
ใช้: python3 build_mep_viewer.py elements.json defs.json inst.json OUT.json SHA
  defs.json / inst.json = เมชคอมโพเนนต์ (ข้อต่อ PVC, สุขภัณฑ์, MH) และตำแหน่งสุขภัณฑ์ ส่งออกจาก SketchUp (เมตร)
ผลลัพธ์: JSON เดียว มีรายการชิ้นส่วน + บัฟเฟอร์ base64 (Float32/Uint32) สำหรับ three.js InstancedMesh / BufferGeometry
"""
import sys, os, json, math, base64, collections, re
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from export_glb import mesh as _glb_mesh


def _plain(g):
    # ชิ้นส่วน POLY (เช่น สลักเกลียว) ไม่มี 'sec' : ใช้กล่อง w×d แทน
    if g.get('type') == 'multi':
        return dict(g, parts=[_plain(p) for p in g['parts']])
    if g.get('type') == 'member' and g.get('shape') == 'POLY':
        return {k: v for k, v in g.items() if k not in ('shape', 'poly2d')}
    return g


def ctx_mesh(g):
    return _glb_mesh(_plain(g))

src, fdefs, finst, OUT, SHA = sys.argv[1:6]
EL = json.load(open(src))['elements']
DEFS = json.load(open(fdefs))
INST = json.load(open(finst))
FL = {1: 0.30, 2: 3.50, 3: 6.70, 4: 9.90, 5: 13.10}

LAYERS = [  # key, ระบบ, ชื่อ layer, สี
    ('SAN-CW', 'สุขาภิบาล', 'ท่อน้ำดี วาล์ว มิเตอร์ ก๊อก', '#2f7fd8'),
    ('SAN-SOIL', 'สุขาภิบาล', 'ท่อส้วม (ชักโครก โถปัสสาวะ)', '#9a5b2e'),
    ('SAN-WASTE', 'สุขาภิบาล', 'ท่อน้ำทิ้ง (อ่าง ฟลอร์เดรน ซิงค์)', '#3f9a6e'),
    ('SAN-VENT', 'สุขาภิบาล', 'ท่ออากาศ', '#8fa3b5'),
    ('SAN-UG', 'สุขาภิบาล', 'ท่อระบายใต้ดิน ถังบำบัด บ่อพัก', '#6b4f8a'),
    ('SAN-FIX', 'สุขาภิบาล', 'สุขภัณฑ์', '#e9edf0'),
    ('SAN-SUP', 'สุขาภิบาล', 'จุดยึด/แขวนท่อ', '#5d6670'),
    ('SAN-SLV', 'สุขาภิบาล', 'ท่อปลอกฝังคาน', '#c9a227'),
    ('ELE-PNL', 'ไฟฟ้า', 'ตู้ MDB ตู้ DB ตู้มิเตอร์ ตู้คอนซูมเมอร์', '#d64541'),
    ('ELE-MAIN', 'ไฟฟ้า', 'สายเมน ท่อ EMT รางวายเวย์', '#e67e22'),
    ('ELE-CD', 'ไฟฟ้า', 'ท่อร้อยสาย กล่องพักสาย ก้ามปู', '#c7b26a'),
    ('ELE-LGT', 'ไฟฟ้า', 'โคมไฟ พัดลมดูดอากาศ', '#f4c430'),
    ('ELE-SW', 'ไฟฟ้า', 'สวิตช์ เต้ารับ', '#a05ad6'),
]
CTX = [('CTX-ST', 'อาคาร (อ้างอิง)', 'โครงสร้าง เสา คาน พื้น บันได', '#9aa0a6', ('เสา', 'คาน', 'คานคอดิน', 'พื้น', 'พื้นทับหน้า', 'พื้นสำเร็จรูป', 'บันได')),
       ('CTX-WL', 'อาคาร (อ้างอิง)', 'ผนัง', '#c8b8a6', ('ผนัง',))]


def layer_of(e):
    cat, i, n = e['category'], e['id'], e['name']
    s = i + ' ' + n
    if cat == 'สุขภัณฑ์':
        return 'SAN-FIX'
    if cat == 'ไฟฟ้า':
        if n.startswith('ตู้'):
            return 'ELE-PNL'
        if i.startswith('EM-'):
            return 'ELE-MAIN'
        if any(k in n for k in ('ท่อร้อยสาย', 'กล่องพักสาย', 'กล่องต่อสาย', 'ก้ามปู')):
            return 'ELE-CD'
        if 'สวิตช์' in n or 'เต้ารับ' in n:
            return 'ELE-SW'
        if 'โคม' in n or 'พัดลม' in n:
            return 'ELE-LGT'
        return 'ELE-CD'
    if i.startswith('SEP-') or any(k in n for k in ('ถังบำบัด', 'บ่อพัก', 'ฝาถัง', 'คอถัง')):
        return 'SAN-UG'
    if any(k in s for k in ('เหล็กฉาก', 'เพลทเหล็ก', 'ห่วงรัด', 'ห่วงแขวน', 'เหล็กเส้นเกลียว', '-SUP')):
        return 'SAN-SUP'
    if 'ท่อปลอก' in n or '-SLV' in i and 'กันซึม' not in n:
        return 'SAN-SLV'
    if re.match(r'^SD-(Z\d|OUT)', i) or i.startswith('SD-Z') or any(k in n for k in ('ท่อเข้าถัง', 'ท่อออกจากถัง', 'ท่อทิ้งรวม')):
        return 'SAN-UG'
    if i.startswith('SD-F1U') or n.startswith('ท่อส้วม'):
        return 'SAN-SOIL'
    if n.startswith('ท่อน้ำทิ้ง'):
        return 'SAN-WASTE'
    if 'อากาศ' in n or re.search(r'-(VENT|AV|FV|RVS|RVW)\b', i) or i.startswith('SD-F1V'):
        return 'SAN-VENT'
    if re.search(r'-(CW|MT|MN|RS)\b', i) or any(k in n for k in ('น้ำดี', 'ก๊อก', 'วาล์ว', 'ฝักบัว', 'มิเตอร์')):
        return 'SAN-CW'
    if 'ฟลอร์เดรน' in n:
        return 'SAN-WASTE'
    if 'ส้วม' in n or 'ชักโครก' in n or 'ปัสสาวะ' in n or re.search(r'-(SOIL|WC)\b', i) or re.match(r'^SD-F1[MWU]-', i):
        return 'SAN-SOIL'
    return 'SAN-WASTE'


def floor_of(z):
    for f in (5, 4, 3, 2):
        if z >= FL[f] - 0.60:
            return f
    return 1


# ---------- รายการชิ้นส่วน ----------
MEP = [e for e in EL if e['category'] in ('สุขาภิบาล', 'สุขภัณฑ์', 'ไฟฟ้า')]
inst_by_id = collections.defaultdict(list)
for i, dn, t in INST:
    inst_by_id[i].append((dn, t))
items = []       # [id, ชื่อ, layer, ชั้น]
idx_of = {}
prim = collections.defaultdict(lambda: collections.defaultdict(list))   # layer -> kind -> [(12 floats, elem)]
meshes = collections.defaultdict(lambda: ([], [], []))                  # layer -> (pos, idx, tri->elem)
dinst = collections.defaultdict(lambda: collections.defaultdict(list))  # layer -> def -> [(12, elem)]


def frame(p0, p1):
    p0, p1 = np.array(p0, float), np.array(p1, float)
    u = p1 - p0; L = np.linalg.norm(u)
    if L < 1e-6:
        return None
    u /= L
    z = np.array([0, 0, 1.0])
    s = np.array([1.0, 0, 0]) if abs(u @ z) > 0.999 else np.cross(u, z)
    s /= np.linalg.norm(s)
    t = np.cross(s, u)
    return p0, u, s, t, L


def aff(X, Y, Z, O):   # คอลัมน์ X Y Z O (สำหรับ Matrix4.set แบบแถว)
    return [X[0], Y[0], Z[0], O[0], X[1], Y[1], Z[1], O[1], X[2], Y[2], Z[2], O[2]]


def add_cyl(layer, ei, p0, p1, r):
    f = frame(p0, p1)
    if not f:
        return
    p0, u, s, t, L = f
    prim[layer]['cyl'].append((aff(s * r, u * L, t * r, p0 + u * L / 2), ei))   # หน่วยทรงกระบอก: แกน Y สูง 1 รัศมี 1


def add_box(layer, ei, p0, p1, w, d):
    f = frame(p0, p1)
    if not f:
        return
    p0, u, s, t, L = f
    prim[layer]['box'].append((aff(s * w, u * L, t * d, p0 + u * L / 2), ei))    # หน่วยกล่อง 1x1x1


def add_mesh(layer, ei, V, T):
    pos, idx, te = meshes[layer]
    b = len(pos) // 3
    pos.extend(np.asarray(V, float).reshape(-1).tolist())
    idx.extend([k + b for tr in T for k in tr])
    te.extend([ei] * len(T))


def prism_geom(layer, ei, g):
    P = g['poly']
    xs = [p[0] for p in P]; ys = [p[1] for p in P]
    if len(P) == 4:
        # สี่เหลี่ยมผืนผ้า (ไม่จำเป็นต้องขนานแกน)
        a, b, c4 = np.array(P[0]), np.array(P[1]), np.array(P[3])
        e1, e2 = b - a, c4 - a
        if abs(e1 @ e2) < 1e-6 * (np.linalg.norm(e1) * np.linalg.norm(e2) + 1e-9) and np.allclose(np.array(P[2]), a + e1 + e2, atol=1e-4):
            O = np.array([*(a + (e1 + e2) / 2), g['z0'] + g['t'] / 2])
            prim[layer]['box'].append((aff([e1[0], e1[1], 0], [e2[0], e2[1], 0], [0, 0, g['t']], O), ei))
            return
    V, T = ctx_mesh(g)
    add_mesh(layer, ei, V, T)


def geom(layer, ei, g):
    t = g['type']
    if t == 'multi':
        for p in g['parts']:
            geom(layer, ei, p)
    elif t == 'member':
        pts = g.get('path') or [g['p0'], g['p1']]
        sh = g.get('shape')
        if sh == 'POLY':
            r = max(math.hypot(*p) for p in g['poly2d'])
            for a, b in zip(pts, pts[1:]):
                add_cyl(layer, ei, a, b, r)
        elif sh == 'O':
            for a, b in zip(pts, pts[1:]):
                add_cyl(layer, ei, a, b, g['sec']['d'] / 2)
        elif sh is None:
            for a, b in zip(pts, pts[1:]):
                add_box(layer, ei, a, b, g['w'], g['d'])
        else:
            V, T = ctx_mesh(g)
            add_mesh(layer, ei, V, T)
    elif t == 'prism':
        prism_geom(layer, ei, g)
    else:
        V, T = ctx_mesh(g)
        add_mesh(layer, ei, V, T)


def zmid(g):
    if g['type'] == 'multi':
        return zmid(g['parts'][0])
    if g['type'] == 'member':
        return (g['p0'][2] + g['p1'][2]) / 2
    if g['type'] == 'prism':
        return g['z0'] + g['t'] / 2
    return 0


nfit = ninst = 0
for e in MEP:
    L = layer_of(e)
    f = e.get('fitting')
    z = f['origin'][2] if f else zmid(e['geom'])
    ei = len(items)
    q = e.get('qty') or {}
    items.append([e['id'], e['name'], L, floor_of(z), q.get('size') or q.get('model') or ''])
    if f:
        X = np.array(f['x'], float); Y = np.array(f['y'], float); Z = np.cross(X, Y)
        dinst[L][f['def']].append((aff(X, Y, Z, f['origin']), ei)); nfit += 1
    elif e['id'] in inst_by_id:
        for dn, t in inst_by_id[e['id']]:
            m = np.array(t, float).reshape(4, 4).T          # SketchUp: คอลัมน์ต่อคอลัมน์
            dinst[L][dn].append(([*m[0, :4], *m[1, :4], *m[2, :4]], ei)); ninst += 1
    else:
        geom(L, ei, e['geom'])

# ---------- เมชคอมโพเนนต์: รวมจุดซ้ำ ----------
def_out = {}
used = {d for L in dinst for d in dinst[L]}
for dn in used:
    P = np.array(DEFS[dn]['pos'], float).reshape(-1, 3)
    I = np.array(DEFS[dn]['idx'], np.int64)
    key = np.round(P / 0.0005).astype(np.int64)
    uq, inv = np.unique(key, axis=0, return_inverse=True)
    inv = inv.reshape(-1)
    P2 = np.zeros((len(uq), 3)); P2[inv] = P
    I2 = inv[I].reshape(-1, 3)
    I2 = I2[(I2[:, 0] != I2[:, 1]) & (I2[:, 1] != I2[:, 2]) & (I2[:, 0] != I2[:, 2])]
    def_out[dn] = dict(pos=P2.astype(np.float32), idx=I2.reshape(-1).astype(np.uint32))

# ---------- อาคารอ้างอิง ----------
ctx = {}
bad = 0
for key, sysname, nm, col, cats in CTX:
    pos, idx = [], []
    for e in EL:
        if e['category'] in cats:
            try:
                V, T = ctx_mesh(e['geom'])
            except Exception:
                bad += 1; continue
            b = len(pos) // 3
            pos.extend(np.asarray(V, float).reshape(-1).tolist()); idx.extend([k + b for tr in T for k in tr])
    ctx[key] = dict(pos=np.array(pos, np.float32), idx=np.array(idx, np.uint32))

B = lambda a: base64.b64encode(np.ascontiguousarray(a).tobytes()).decode()
out = dict(sha=SHA, floors=FL, items=items,
           layers=[dict(key=k, sys=s, name=n, color=c) for k, s, n, c in LAYERS],
           ctx=[dict(key=k, sys=s, name=n, color=c, pos=B(ctx[k]['pos']), idx=B(ctx[k]['idx'])) for k, s, n, c, _ in CTX],
           defs={dn: dict(pos=B(d['pos']), idx=B(d['idx'])) for dn, d in def_out.items()},
           prim=[], inst=[], mesh=[])
for L in prim:
    for kind, rows in prim[L].items():
        out['prim'].append(dict(layer=L, kind=kind, m=B(np.array([r[0] for r in rows], np.float32)), e=B(np.array([r[1] for r in rows], np.uint32))))
for L in dinst:
    for dn, rows in dinst[L].items():
        out['inst'].append(dict(layer=L, def_=dn, m=B(np.array([r[0] for r in rows], np.float32)), e=B(np.array([r[1] for r in rows], np.uint32))))
for L, (pos, idx, te) in meshes.items():
    out['mesh'].append(dict(layer=L, pos=B(np.array(pos, np.float32)), idx=B(np.array(idx, np.uint32)), te=B(np.array(te, np.uint32))))
json.dump(out, open(OUT, 'w'), ensure_ascii=False, separators=(',', ':'))
cnt = collections.Counter((it[2], it[3]) for it in items)
print('items', len(items), 'fit', nfit, 'inst', ninst, 'ctx_bad', bad, 'size', os.path.getsize(OUT))
print({k: sum(v for (l, f), v in cnt.items() if l == k) for k, *_ in LAYERS})
print('prim', {(p['layer'], p['kind']): len(base64.b64decode(p['e'])) // 4 for p in out['prim']})
print('mesh tris', {m['layer']: len(base64.b64decode(m['te'])) // 4 for m in out['mesh']})
print('ctx tris', {k: len(ctx[k]['idx']) // 3 for k in ctx}, 'defs tris', sum(len(d['idx']) // 3 for d in def_out.values()))
