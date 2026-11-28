"""เขียนไฟล์ IFC4 งานระบบสุขาภิบาล + ไฟฟ้า หอพัก A จาก mep.json (ข้อมูลชุดเดียวกับเว็บดูโมเดล)

ใช้:  python3 build_mep_ifc.py mep.json OUT.ifc
- ชั้น (IfcBuildingStorey) 1-5 ตาม floor ของแต่ละชิ้น
- layer (IfcPresentationLayerAssignment) = ระบบย่อย x ชั้น เช่น "สุขาภิบาล-ท่อน้ำดี-ชั้น2"
- ระบบ (IfcDistributionSystem) = ระบบย่อย 13 ระบบ
- รูปทรง: ท่อ/กล่อง = IfcExtrudedAreaSolid, คอมโพเนนต์ = IfcMappedItem ของ IfcTriangulatedFaceSet
- ไม่ใช้ไลบรารีภายนอก (เขียน STEP เอง)
"""
import sys, json, base64, uuid, collections, datetime
import numpy as np

SRC, OUT = sys.argv[1], sys.argv[2]
D = json.load(open(SRC))
items = D['items']
FL = {int(k): v for k, v in D['floors'].items()}
LAY = {L['key']: L for L in D['layers']}

def b64(s, t):
    return np.frombuffer(base64.b64decode(s), t)

# ---------- STEP helpers ----------
lines = []
def add(txt):
    lines.append(txt)
    return '#%d' % len(lines)

def S(s):
    if s is None:
        return '$'
    out, run = [], []
    def flush():
        if run:
            out.append('\\X2\\' + ''.join('%04X' % o for o in run) + '\\X0\\')
            run.clear()
    for ch in str(s):
        o = ord(ch)
        if 32 <= o < 127:
            flush()
            out.append("''" if ch == "'" else '\\\\' if ch == '\\' else ch)
        else:
            run.append(o)
    flush()
    return "'" + ''.join(out) + "'"

def R(v):
    t = '%.6f' % float(v)
    t = t.rstrip('0')
    return '0.' if t in ('-0.', '0.') else t

def P3(v):
    return add('IFCCARTESIANPOINT((%s,%s,%s));' % (R(v[0]), R(v[1]), R(v[2])))

_dirs = {}
def DIR(v):
    k = (R(v[0]), R(v[1]), R(v[2]))
    if k not in _dirs:
        _dirs[k] = add('IFCDIRECTION((%s,%s,%s));' % k)
    return _dirs[k]

_C = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz_$'
def GID(key):
    n = uuid.uuid5(uuid.NAMESPACE_URL, 'dormA-mep/' + key).int
    return "'" + _C[n >> 126] + ''.join(_C[(n >> (6 * i)) & 63] for i in range(20, -1, -1)) + "'"

# ---------- project / context / units ----------
ORIGIN = P3((0, 0, 0)); ZD = DIR((0, 0, 1)); XD = DIR((1, 0, 0))
WCS = add('IFCAXIS2PLACEMENT3D(%s,$,$);' % ORIGIN)
CTX = add("IFCGEOMETRICREPRESENTATIONCONTEXT($,'Model',3,1.E-05,%s,$);" % WCS)
P2D = add('IFCAXIS2PLACEMENT2D(%s,$);' % add('IFCCARTESIANPOINT((0.,0.));'))
BODY = add("IFCGEOMETRICREPRESENTATIONSUBCONTEXT('Body','Model',*,*,*,*,%s,$,.MODEL_VIEW.,$);" % CTX)
U = [add('IFCSIUNIT(*,.LENGTHUNIT.,$,.METRE.);'), add('IFCSIUNIT(*,.AREAUNIT.,$,.SQUARE_METRE.);'),
     add('IFCSIUNIT(*,.VOLUMEUNIT.,$,.CUBIC_METRE.);'), add('IFCSIUNIT(*,.PLANEANGLEUNIT.,$,.RADIAN.);')]
UA = add('IFCUNITASSIGNMENT((%s));' % ','.join(U))
PROJ = add("IFCPROJECT(%s,$,%s,%s,$,$,$,(%s),%s);" % (GID('project'), S('หอพัก A ชัยเสรี'), S('งานระบบสุขาภิบาลและไฟฟ้า'), CTX, UA))
def LP(rel=None):
    return add('IFCLOCALPLACEMENT(%s,%s);' % (rel or '$', add('IFCAXIS2PLACEMENT3D(%s,$,$);' % ORIGIN)))
SITE_P = LP(); SITE = add("IFCSITE(%s,$,%s,$,$,%s,$,$,.ELEMENT.,$,$,$,$,$);" % (GID('site'), S('ที่ตั้งโครงการ'), SITE_P))
BLD_P = LP(SITE_P); BLD = add("IFCBUILDING(%s,$,%s,$,$,%s,$,$,.ELEMENT.,$,$,$);" % (GID('building'), S('หอพัก A'), BLD_P))
add("IFCRELAGGREGATES(%s,$,$,$,%s,(%s));" % (GID('agg-site'), PROJ, SITE))
add("IFCRELAGGREGATES(%s,$,$,$,%s,(%s));" % (GID('agg-bld'), SITE, BLD))
STO, STO_P = {}, {}
for f in range(1, 6):
    STO_P[f] = LP(BLD_P)
    STO[f] = add("IFCBUILDINGSTOREY(%s,$,%s,$,$,%s,$,$,.ELEMENT.,%s);" % (GID('storey%d' % f), S('ชั้น %d' % f), STO_P[f], R(FL[f])))
add("IFCRELAGGREGATES(%s,$,$,$,%s,(%s));" % (GID('agg-sto'), BLD, ','.join(STO[f] for f in range(1, 6))))

# ---------- styles ----------
STYLE = {}
def style_for(layer):
    if layer not in STYLE:
        c = LAY[layer]['color'].lstrip('#')
        r, g, b = (int(c[i:i + 2], 16) / 255 for i in (0, 2, 4))
        rgb = add('IFCCOLOURRGB($,%s,%s,%s);' % (R(r), R(g), R(b)))
        sh = add('IFCSURFACESTYLESHADING(%s,0.);' % rgb)
        STYLE[layer] = add('IFCSURFACESTYLE(%s,.BOTH.,(%s));' % (S(LAY[layer]['name']), sh))
    return STYLE[layer]
def styled(item, layer):
    add('IFCSTYLEDITEM(%s,(%s),$);' % (item, style_for(layer)))

# ---------- geometry per element ----------
geo = collections.defaultdict(lambda: {'swept': [], 'mapped': [], 'tess': []})
def unit(v):
    n = np.linalg.norm(v)
    return v / n, n

bad = collections.Counter()
for p in D['prim']:
    M = b64(p['m'], np.float32).reshape(-1, 3, 4).astype(float)
    E = b64(p['e'], np.uint32)
    for m, e in zip(M, E):
        X, Y, Z, O = m[:, 0], m[:, 1], m[:, 2], m[:, 3]
        if p['kind'] == 'cyl':
            ax, L = unit(Y); rx, r = unit(X)
            if L < 1e-5 or r < 1e-5:
                bad['cyl'] += 1; continue
            base = O - Y / 2
            prof = add('IFCCIRCLEPROFILEDEF(.AREA.,$,%s,%s);' % (P2D, R(r)))
        else:
            ax, L = unit(Z); rx, xd = unit(X); _, yd = unit(Y)
            if L < 1e-5 or xd < 1e-5 or yd < 1e-5:
                bad['box'] += 1; continue
            base = O - Z / 2
            prof = add('IFCRECTANGLEPROFILEDEF(.AREA.,$,%s,%s,%s);' % (P2D, R(xd), R(yd)))
        rx = rx - ax * (rx @ ax)            # ตั้งฉากกับแกนให้แน่นอน
        rx, _ = unit(rx)
        pos = add('IFCAXIS2PLACEMENT3D(%s,%s,%s);' % (P3(base), DIR(ax), DIR(rx)))
        sol = add('IFCEXTRUDEDAREASOLID(%s,%s,%s,%s);' % (prof, pos, ZD, R(L)))
        styled(sol, p['layer'])
        geo[int(e)]['swept'].append(sol)

# คอมโพเนนต์: RepresentationMap ต่อ def
MAPS = {}
def rep_map(dn, layer):
    if dn not in MAPS:
        P = b64(D['defs'][dn]['pos'], np.float32).reshape(-1, 3)
        I = b64(D['defs'][dn]['idx'], np.uint32).reshape(-1, 3) + 1
        pl = add('IFCCARTESIANPOINTLIST3D((%s));' % ','.join('(%s,%s,%s)' % (R(a), R(b), R(c)) for a, b, c in P))
        fs = add('IFCTRIANGULATEDFACESET(%s,$,$,(%s),$);' % (pl, ','.join('(%d,%d,%d)' % tuple(t) for t in I)))
        styled(fs, layer)
        sr = add("IFCSHAPEREPRESENTATION(%s,'Body','Tessellation',(%s));" % (BODY, fs))
        MAPS[dn] = add('IFCREPRESENTATIONMAP(%s,%s);' % (add('IFCAXIS2PLACEMENT3D(%s,$,$);' % ORIGIN), sr))
    return MAPS[dn]

for p in D['inst']:
    M = b64(p['m'], np.float32).reshape(-1, 3, 4).astype(float)
    E = b64(p['e'], np.uint32)
    rm = rep_map(p['def_'], p['layer'])
    for m, e in zip(M, E):
        X, Y, Z, O = m[:, 0], m[:, 1], m[:, 2], m[:, 3]
        sx, sy, sz = (np.linalg.norm(v) for v in (X, Y, Z))
        if min(sx, sy, sz) < 1e-9:
            bad['inst'] += 1; continue
        if max(abs(sx - 1), abs(sy - 1), abs(sz - 1)) < 1e-4:
            op = add('IFCCARTESIANTRANSFORMATIONOPERATOR3D(%s,%s,%s,1.,%s);' % (DIR(X), DIR(Y), P3(O), DIR(Z)))
        else:
            op = add('IFCCARTESIANTRANSFORMATIONOPERATOR3DNONUNIFORM(%s,%s,%s,%s,%s,%s,%s);' % (
                DIR(X / sx), DIR(Y / sy), P3(O), R(sx), DIR(Z / sz), R(sy), R(sz)))
        geo[int(e)]['mapped'].append(add('IFCMAPPEDITEM(%s,%s);' % (rm, op)))

for m in D['mesh']:
    P = b64(m['pos'], np.float32).reshape(-1, 3)
    I = b64(m['idx'], np.uint32).reshape(-1, 3)
    TE = b64(m['te'], np.uint32)
    by = collections.defaultdict(list)
    for t, e in enumerate(TE):
        by[int(e)].append(I[t])
    for e, tris in by.items():
        tris = np.array(tris)
        vs, inv = np.unique(tris.reshape(-1), return_inverse=True)
        pl = add('IFCCARTESIANPOINTLIST3D((%s));' % ','.join('(%s,%s,%s)' % tuple(R(c) for c in P[v]) for v in vs))
        fs = add('IFCTRIANGULATEDFACESET(%s,$,$,(%s),$);' % (pl, ','.join('(%d,%d,%d)' % tuple(t + 1) for t in inv.reshape(-1, 3))))
        styled(fs, m['layer'])
        geo[e]['tess'].append(fs)

# ---------- IFC class ----------
def ifc_class(layer, name):
    n = name
    if layer.startswith('ELE'):
        if n.startswith('ตู้'): return 'IFCELECTRICDISTRIBUTIONBOARD', 'NOTDEFINED'
        if n.startswith('กล่อง'): return 'IFCJUNCTIONBOX', 'NOTDEFINED'
        if n.startswith('ก้ามปู'): return 'IFCDISCRETEACCESSORY', 'NOTDEFINED'
        if n.startswith('รางวายเวย์'): return 'IFCCABLECARRIERSEGMENT', 'CABLETRUNKINGSEGMENT'
        if n.startswith('ท่อ'): return 'IFCCABLECARRIERSEGMENT', 'CONDUITSEGMENT'
        if n.startswith('โคม'): return 'IFCLIGHTFIXTURE', 'NOTDEFINED'
        if n.startswith('พัดลม'): return 'IFCFAN', 'NOTDEFINED'
        if n.startswith('สวิตช์'): return 'IFCSWITCHINGDEVICE', 'NOTDEFINED'
        if n.startswith('เต้ารับ'): return 'IFCOUTLET', 'POWEROUTLET'
        return 'IFCBUILDINGELEMENTPROXY', 'NOTDEFINED'
    if layer == 'SAN-SUP': return 'IFCDISCRETEACCESSORY', 'NOTDEFINED'
    if layer == 'SAN-FIX':
        if 'ส้วม' in n: return 'IFCSANITARYTERMINAL', 'TOILETPAN'
        if 'ปัสสาวะ' in n and not n.startswith('แผง'): return 'IFCSANITARYTERMINAL', 'URINAL'
        if 'ซิงค์' in n: return 'IFCSANITARYTERMINAL', 'SINK'
        if 'อ่าง' in n: return 'IFCSANITARYTERMINAL', 'WASHHANDBASIN'
        return 'IFCSANITARYTERMINAL', 'NOTDEFINED'
    if n.startswith(('ถังบำบัด', 'คอถัง', 'ฝาถัง')): return 'IFCTANK', 'NOTDEFINED'
    if n.startswith('บ่อพัก'): return 'IFCDISTRIBUTIONCHAMBERELEMENT', 'INSPECTIONCHAMBER'
    if n.startswith(('ข้อ', 'สามทาง', 'สี่ทาง', 'วาย', 'ฝาครอบ', 'ฝาปิด')): return 'IFCPIPEFITTING', 'NOTDEFINED'
    if n.startswith('สายน้ำดี'): return 'IFCPIPESEGMENT', 'FLEXIBLESEGMENT'
    if 'ฟลอร์เดรน' in n and not n.startswith('ท่อ'): return 'IFCWASTETERMINAL', 'FLOORTRAP'
    if n.startswith(('มิเตอร์', 'หน้าปัดมิเตอร์')): return 'IFCFLOWMETER', 'WATERMETER'
    if n.startswith(('ก๊อก', 'ปากก๊อก')): return 'IFCVALVE', 'FAUCET'
    if 'วาล์ว' in n and not n.startswith('ท่อ'): return 'IFCVALVE', 'NOTDEFINED'
    if n.startswith(('ฝักบัว', 'หัวฝักบัว', 'ขอแขวนฝักบัว', 'สายฝักบัว')): return 'IFCSANITARYTERMINAL', 'SHOWER'
    if layer == 'SAN-SLV': return 'IFCPIPESEGMENT', 'NOTDEFINED'
    return 'IFCPIPESEGMENT', 'NOTDEFINED'

# ---------- elements ----------
_sp = {}
def shared_props(layer, floor):
    # ค่าเดียวกันทั้งระบบย่อย/ชั้น: ใช้ property ร่วมกัน (ลดขนาดไฟล์)
    k = (layer, floor)
    if k not in _sp:
        _sp[k] = [add("IFCPROPERTYSINGLEVALUE(%s,$,IFCLABEL(%s),$);" % (S('ระบบ'), S(LAY[layer]['sys']))),
                  add("IFCPROPERTYSINGLEVALUE(%s,$,IFCLABEL(%s),$);" % (S('ระบบย่อย'), S(LAY[layer]['name']))),
                  add("IFCPROPERTYSINGLEVALUE(%s,$,IFCINTEGER(%d),$);" % (S('ชั้น'), floor))]
    return _sp[k]
by_storey = collections.defaultdict(list)
by_layer_floor = collections.defaultdict(list)     # -> shape representations
by_sys = collections.defaultdict(list)
cls_count = collections.Counter()
no_geom = []
for e, it in enumerate(items):
    eid, name, layer, floor, size = it
    g = geo.get(e)
    if not g or not (g['swept'] or g['mapped'] or g['tess']):
        no_geom.append(eid); continue
    reps = []
    if g['swept']:
        reps.append(add("IFCSHAPEREPRESENTATION(%s,'Body','SweptSolid',(%s));" % (BODY, ','.join(g['swept']))))
    if g['mapped']:
        reps.append(add("IFCSHAPEREPRESENTATION(%s,'Body','MappedRepresentation',(%s));" % (BODY, ','.join(g['mapped']))))
    if g['tess']:
        reps.append(add("IFCSHAPEREPRESENTATION(%s,'Body','Tessellation',(%s));" % (BODY, ','.join(g['tess']))))
    pds = add('IFCPRODUCTDEFINITIONSHAPE($,$,(%s));' % ','.join(reps))
    cls, pt = ifc_class(layer, name)
    cls_count[cls] += 1
    pl = add('IFCLOCALPLACEMENT(%s,%s);' % (STO_P[floor], WCS))
    el = add("%s(%s,$,%s,$,%s,%s,%s,%s,.%s.);" % (cls, GID('el/' + eid), S(name), S(LAY[layer]['name']), pl, pds, S(eid), pt))
    props = [add("IFCPROPERTYSINGLEVALUE('BIM4D_Id',$,IFCIDENTIFIER(%s),$);" % S(eid)),
             *shared_props(layer, floor)]
    if size:
        props.append(add("IFCPROPERTYSINGLEVALUE(%s,$,IFCLABEL(%s),$);" % (S('ขนาด/รุ่น'), S(size))))
    ps = add("IFCPROPERTYSET(%s,$,'Pset_DormA_BIM',$,(%s));" % (GID('ps/' + eid), ','.join(props)))
    add("IFCRELDEFINESBYPROPERTIES(%s,$,$,$,(%s),%s);" % (GID('rdp/' + eid), el, ps))
    by_storey[floor].append(el)
    by_layer_floor[(layer, floor)].extend(reps)
    by_sys[layer].append(el)

for f, els in sorted(by_storey.items()):
    add("IFCRELCONTAINEDINSPATIALSTRUCTURE(%s,$,$,$,(%s),%s);" % (GID('cont%d' % f), ','.join(els), STO[f]))

SYS_PT = {'SAN-CW': 'DOMESTICCOLDWATER', 'SAN-SOIL': 'SEWAGE', 'SAN-WASTE': 'WASTEWATER', 'SAN-VENT': 'VENT',
          'SAN-UG': 'SEWAGE', 'ELE-PNL': 'ELECTRICAL', 'ELE-MAIN': 'ELECTRICAL', 'ELE-CD': 'ELECTRICAL',
          'ELE-LGT': 'LIGHTING', 'ELE-SW': 'ELECTRICAL'}
for k in LAY:
    if not by_sys[k]:
        continue
    L = LAY[k]
    sysid = add("IFCDISTRIBUTIONSYSTEM(%s,$,%s,$,$,%s,.%s.);" % (GID('sys/' + k), S(L['sys'] + '-' + L['name']), S(k), SYS_PT.get(k, 'NOTDEFINED')))
    add("IFCRELASSIGNSTOGROUP(%s,$,$,$,(%s),$,%s);" % (GID('grp/' + k), ','.join(by_sys[k]), sysid))
    add("IFCRELSERVICESBUILDINGS(%s,$,$,$,%s,(%s));" % (GID('svc/' + k), sysid, BLD))

layer_names = []
for (k, f), reps in sorted(by_layer_floor.items(), key=lambda kv: (list(LAY).index(kv[0][0]), kv[0][1])):
    L = LAY[k]
    nm = '%s-%s-ชั้น%d' % (L['sys'], L['name'], f)
    layer_names.append(nm)
    add("IFCPRESENTATIONLAYERASSIGNMENT(%s,%s,(%s),%s);" % (S(nm), S(k), ','.join(reps), S('%s-F%d' % (k, f))))

now = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
hdr = ("ISO-10303-21;\nHEADER;\nFILE_DESCRIPTION(('ViewDefinition [ReferenceView_V1.2]'),'2;1');\n"
       "FILE_NAME(%s,'%s',(''),(''),'dorm-bim build_mep_ifc.py','dorm-bim %s','');\nFILE_SCHEMA(('IFC4'));\nENDSEC;\nDATA;\n"
       % (S(OUT.split('/')[-1]), now, D.get('sha', '')))
with open(OUT, 'w', encoding='ascii') as fo:
    fo.write(hdr)
    for i, t in enumerate(lines, 1):
        fo.write('#%d=%s\n' % (i, t))
    fo.write('ENDSEC;\nEND-ISO-10303-21;\n')

print('entities', len(lines), 'elements', sum(len(v) for v in by_storey.values()), 'no_geom', len(no_geom), no_geom[:6])
print('bad', dict(bad), 'layers', len(layer_names), 'maps', len(MAPS))
print(dict(cls_count))
print({f: len(v) for f, v in sorted(by_storey.items())})
