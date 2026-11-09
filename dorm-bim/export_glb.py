"""ส่งออก elements.json เป็น GLB (หนึ่ง node ต่อชิ้นส่วน ชื่อ node = รหัสชิ้นส่วน, extras = ข้อมูล 4D)
แกน glTF: Y ขึ้น  => (x, z, -y) จากพิกัดโมเดล
"""
import json, struct, math
import numpy as np

COLORS = {'คานคอดิน': (0.59, 0.59, 0.59), 'เสา': (0.80, 0.35, 0.30), 'คาน': (0.35, 0.55, 0.40),
          'พื้น': (0.8, 0.8, 0.78), 'พื้นสำเร็จรูป': (0.55, 0.70, 0.85), 'พื้นทับหน้า': (0.90, 0.85, 0.55), 'เสาเอ็นคานเอ็น': (0.55, 0.55, 0.55), 'บันได': (0.7, 0.67, 0.63), 'โครงหลังคาเหล็ก': (0.27, 0.43, 0.63),
          'หลังคา': (0.47, 0.24, 0.18), 'ผนัง': (0.80, 0.62, 0.50),
          'งานฉาบ': (0.93, 0.92, 0.88), 'ประตูหน้าต่าง': (0.45, 0.30, 0.20), 'กระเบื้อง': (0.85, 0.80, 0.70), 'สุขภัณฑ์': (0.97, 0.97, 0.97)}


def box_from_quad(base, off):
    """base: 4 จุด (ลำดับรอบรูป), off: เวกเตอร์ความหนา -> verts, tris"""
    b = np.array(base, float)
    t = b + np.array(off, float)
    v = np.vstack([b, t])
    tris = [(0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7)]
    for i in range(4):
        j = (i + 1) % 4
        tris += [(i, j, 4 + j), (i, 4 + j, 4 + i)]
    return v, tris


def poly_prism(base, off):
    b = np.array(base, float)
    n = len(b)
    t = b + np.array(off, float)
    v = np.vstack([b, t])
    tris = []
    for i in range(1, n - 1):
        tris += [(0, i + 1, i), (n, n + i, n + i + 1)]
    for i in range(n):
        j = (i + 1) % n
        tris += [(i, j, n + j), (i, n + j, n + i)]
    return v, tris


def ear_clip(pts2):
    """แบ่งรูปหลายเหลี่ยม 2 มิติ (เว้าได้) เป็นสามเหลี่ยม คืนดัชนี (ทวนเข็ม)"""
    P = [tuple(p) for p in pts2]
    area = sum(P[i][0] * P[(i + 1) % len(P)][1] - P[(i + 1) % len(P)][0] * P[i][1] for i in range(len(P)))
    idx = list(range(len(P))) if area > 0 else list(range(len(P)))[::-1]
    cross = lambda o, a, b: (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    def inside(p, a, b, c):
        return cross(a, b, p) >= 0 and cross(b, c, p) >= 0 and cross(c, a, p) >= 0
    tris = []
    guard = 0
    while len(idx) > 3 and guard < 1000:
        guard += 1
        for k in range(len(idx)):
            i0, i1, i2 = idx[k - 1], idx[k], idx[(k + 1) % len(idx)]
            a, b, c = P[i0], P[i1], P[i2]
            if cross(a, b, c) <= 1e-12:
                continue
            if any(inside(P[j], a, b, c) for j in idx if j not in (i0, i1, i2)):
                continue
            tris.append((i0, i1, i2))
            idx.pop(k)
            break
    tris.append(tuple(idx))
    return tris


def c_section(sec, shift, mirror):
    h, b, c, t = sec['h'], sec['b'], sec['c'], sec['t']
    pts = [(0, -h / 2), (b, -h / 2), (b, -h / 2 + c), (b - t, -h / 2 + c), (b - t, -h / 2 + t), (t, -h / 2 + t),
           (t, h / 2 - t), (b - t, h / 2 - t), (b - t, h / 2 - c), (b, h / 2 - c), (b, h / 2), (0, h / 2)]
    return [((-a if mirror else a) + shift, bb) for a, bb in pts]


def shape_member(g):
    p0, p1 = np.array(g['p0'], float), np.array(g['p1'], float)
    u = p1 - p0
    L = np.linalg.norm(u)
    u = u / L
    z = np.array([0, 0, 1.0])
    s = np.array([1.0, 0, 0]) if abs(u @ z) > 0.999 else np.cross(u, z)
    s /= np.linalg.norm(s)
    t = np.cross(s, u)
    sec, b = g['sec'], g['sec']['b']
    loops = [c_section(sec, -b, False), c_section(sec, b, True)[::-1]] if g['shape'] == '2C' else [c_section(sec, -b / 2, False)]
    V, T, base = [], [], 0
    for lp in loops:
        n = len(lp)
        bot = np.array([p0 + s * a + t * bb for a, bb in lp])
        top = bot + u * L
        cap = ear_clip(lp)
        # ด้านปลาย: สลับลำดับให้หันออก (ไม่สำคัญต่อการแสดงผลเพราะ flat normal ทั้งสองด้าน)
        tris = [(a, c, b2) for a, b2, c in cap] + [(n + a, n + b2, n + c) for a, b2, c in cap]
        for i in range(n):
            j = (i + 1) % n
            tris += [(i, j, n + j), (i, n + j, n + i)]
        V.append(np.vstack([bot, top]))
        T += [(a + base, b2 + base, c + base) for a, b2, c in tris]
        base += 2 * n
    return np.vstack(V), T


def mesh(g):
    if g['type'] == 'multi':
        V, T, base = [], [], 0
        for p in g['parts']:
            v, t = mesh(p)
            T += [(a + base, b + base, c + base) for a, b, c in t]
            V.append(np.asarray(v, float))
            base += len(v)
        return np.vstack(V), T
    if g['type'] == 'member' and g.get('shape'):
        return shape_member(g)
    if g['type'] == 'member':
        p0, p1 = np.array(g['p0']), np.array(g['p1'])
        u = p1 - p0
        L = np.linalg.norm(u)
        u = u / L
        z = np.array([0, 0, 1.0])
        s = np.array([1.0, 0, 0]) if abs(u @ z) > 0.999 else np.cross(u, z)
        s /= np.linalg.norm(s)
        t = np.cross(s, u)
        hw, hd = g['w'] / 2, g['d'] / 2
        base = [p0 + s * hw + t * hd, p0 - s * hw + t * hd, p0 - s * hw - t * hd, p0 + s * hw - t * hd]
        return box_from_quad(base, u * L)
    if g['type'] == 'prism':
        z0, th = g['z0'], g['t']
        if not g.get('holes'):
            return poly_prism([(x, y, z0) for x, y in g['poly']], (0, 0, th))
        # พื้นสี่เหลี่ยมมีช่องเปิดสี่เหลี่ยม: แบ่งเป็น 4 แผ่น
        xs = [p[0] for p in g['poly']]; ys = [p[1] for p in g['poly']]
        X0, X1, Y0, Y1 = min(xs), max(xs), min(ys), max(ys)
        h = g['holes'][0]
        hx = [p[0] for p in h]; hy = [p[1] for p in h]
        a0, a1, b0, b1 = min(hx), max(hx), min(hy), max(hy)
        parts = [(X0, X1, Y0, b0), (X0, X1, b1, Y1), (X0, a0, b0, b1), (a1, X1, b0, b1)]
        V, T, base = [], [], 0
        for x0, x1, y0, y1 in parts:
            v, t = poly_prism([(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0)], (0, 0, th))
            T += [(a + base, b + base, c + base) for a, b, c in t]
            V.append(v)
            base += len(v)
        return np.vstack(V), T
    if g['type'] == 'plate':
        p = np.array(g['pts'], float)
        n = np.cross(p[1] - p[0], p[2] - p[0])
        n /= np.linalg.norm(n)
        if n[2] > 0:
            n = -n
        return poly_prism(p, n * g['t'])
    raise ValueError(g['type'])


def to_gltf_axes(v):
    return np.stack([v[:, 0], v[:, 2], -v[:, 1]], axis=1)


def flat_normals(v, tris):
    """แยกจุดต่อสามเหลี่ยมเพื่อให้ได้ normal แบบเรียบเหลี่ยม"""
    P = v[np.array(tris).reshape(-1)]
    a, b, c = P[0::3], P[1::3], P[2::3]
    n = np.cross(b - a, c - a)
    ln = np.linalg.norm(n, axis=1, keepdims=True)
    ln[ln == 0] = 1
    n = np.repeat(n / ln, 3, axis=0)
    return P.astype(np.float32), n.astype(np.float32)


def export(model, schedule, path):
    tasks = {t['id']: t for t in schedule['tasks']}
    buf = bytearray()
    accessors, views, meshes, nodes = [], [], [], []
    mats, mat_idx = [], {}
    for cat, c in COLORS.items():
        mat_idx[cat] = len(mats)
        mats.append(dict(name=cat, doubleSided=(cat == 'โครงหลังคาเหล็ก'), pbrMetallicRoughness=dict(baseColorFactor=[*c, 1.0], metallicFactor=0.0, roughnessFactor=0.9)))

    def add_view(data, target):
        while len(buf) % 4:
            buf.append(0)
        off = len(buf)
        buf.extend(data)
        views.append(dict(buffer=0, byteOffset=off, byteLength=len(data), target=target))
        return len(views) - 1

    for e in model['elements']:
        v, tris = mesh(e['geom'])
        P, N = flat_normals(to_gltf_axes(np.asarray(v, float)), tris)
        pv = add_view(P.tobytes(), 34962)
        accessors.append(dict(bufferView=pv, componentType=5126, count=len(P), type='VEC3',
                              min=P.min(0).tolist(), max=P.max(0).tolist()))
        nv = add_view(N.tobytes(), 34962)
        accessors.append(dict(bufferView=nv, componentType=5126, count=len(N), type='VEC3'))
        meshes.append(dict(name=e['id'], primitives=[dict(attributes=dict(POSITION=len(accessors) - 2, NORMAL=len(accessors) - 1),
                                                          material=mat_idx.get(e['category'], 0))]))
        t = tasks.get(e['task'])
        nodes.append(dict(name=e['id'], mesh=len(meshes) - 1, extras=dict(
            id=e['id'], name=e['name'], category=e['category'], floor=e['floor'], task=e['task'],
            start=t['start'] if t else None, finish=t['finish'] if t else None,
            status=t['status'] if t else 'แล้วเสร็จ (ก่อนแผน R3)', assumed=e['assumed'], qty=e['qty'])))
    root = dict(name='หอพัก A', children=list(range(len(nodes))))
    nodes.append(root)
    gltf = dict(asset=dict(version='2.0', generator='dorm-bim export_glb.py'), scene=0,
                scenes=[dict(nodes=[len(nodes) - 1])], nodes=nodes, meshes=meshes, materials=mats,
                accessors=accessors, bufferViews=views, buffers=[dict(byteLength=len(buf))])
    js = json.dumps(gltf, ensure_ascii=False).encode('utf-8')
    js += b' ' * ((4 - len(js) % 4) % 4)
    while len(buf) % 4:
        buf.append(0)
    total = 12 + 8 + len(js) + 8 + len(buf)
    with open(path, 'wb') as f:
        f.write(struct.pack('<III', 0x46546C67, 2, total))
        f.write(struct.pack('<II', len(js), 0x4E4F534A)); f.write(js)
        f.write(struct.pack('<II', len(buf), 0x004E4942)); f.write(bytes(buf))


if __name__ == '__main__':
    import sys
    m = json.load(open('elements.json'))
    s = json.load(open('schedule.json'))
    out = sys.argv[1] if len(sys.argv) > 1 else 'dorm_A.glb'
    export(m, s, out)
    print('wrote', out)
