# -*- coding: utf-8 -*-
"""สร้างผลลัพธ์ทั้งหมดจาก model.py:
   out/TC-WH_BIM.ifc        IFC4 (โมเดล 3 มิติ + Pset BOQ/4D + IfcTask/IfcWorkSchedule)
   out/TC-WH_BIM_QTO.xlsx   ถอดปริมาณจากโมเดล + ตารางทวนสอบ BOQ + แผนงาน 4D
   out/model.json           ข้อมูลสำหรับ viewer
   index.html               3D/4D viewer (เปิดในเบราว์เซอร์ได้ทันที)
ใช้งาน:  python3 build.py
"""
import json, math, os, time, uuid, collections, datetime as dt
import model as M

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
os.makedirs(OUT, exist_ok=True)

E = M.build()
S = M.schedule()
TASK_ORDER = [t[0] for t in M.TASKS]


# ---------------------------------------------------------------- QTO
def prism_area(e):
    a = M.poly_area(e["outer"]) - sum(M.poly_area(h) for h in e["holes"])
    return a


def qty(e):
    if e["kind"] == "box":
        a, b, h = e["a"], e["b"], e["h"]
        return dict(vol=a*b*h, a=a, b=b, h=h)
    ar = prism_area(e)
    return dict(vol=ar*e["h"], area=ar, h=e["h"])


def steel_kg(e):
    w = e["extra"].get("น้ำหนัก (กก./ม.)")
    if w is None and e["mark"] == "MB": w = 21.3
    if w is None: return 0.0
    return w * e["h"]


groups = collections.OrderedDict()
for e in E:
    k = (e["boq"], e["mark"], e["name"].split(" @")[0])
    g = groups.setdefault(k, dict(n=0, len=0.0, vol=0.0, area=0.0, kg=0.0, src=e["src"], task=e["task"], ifc=e["ifc"]))
    q = qty(e); g["n"] += 1; g["vol"] += q["vol"]
    if e["kind"] == "box":
        g["len"] += e["h"]
        g["area"] += e["a"]*e["h"] if e["ifc"] in ("IfcWall", "IfcCovering", "IfcDoor") else e["a"]*e["b"]
    else:
        g["area"] += q["area"]
    g["kg"] += steel_kg(e)

cnt = collections.Counter(e["mark"] for e in E)
tot_kg = sum(steel_kg(e) for e in E)
pile_len = sum(e["h"] for e in E if e["ifc"] == "IfcPile")
fill_ext = next(e for e in E if e["mark"] == "FILL-EXT"); fill_b = next(e for e in E if e["mark"] == "FILL-BLDG")
fill_vol = qty(fill_ext)["vol"] + qty(fill_b)["vol"]
site_area = M.poly_area(M.SITE); site_per = M.poly_perim(M.SITE)
road = next(e for e in E if e["mark"] == "S2" and e["kind"] == "prism")
road_area = prism_area(road)
roof_area = sum(e["a"]*e["b"] for e in E if e["mark"] == "RF")
clad_area = sum((M.poly_area(e["outer"]) if e["kind"] == "prism" else e["b"]*e["h"]) for e in E if e["mark"] == "W2")
wall_area = sum(e["a"]*e["h"] if e["a"] > e["b"] else e["b"]*e["h"] for e in E if e["mark"] == "W1")
drain_len = sum(e["h"] for e in E if e["mark"] == "DR")
b1_len = sum(e["h"] for e in E if e["mark"] == "B1")


def fill_for(eg):
    ext = (site_area - 3240.0) * (-0.25 - eg); b = 3240.0 * (0.10 - eg)
    return ext + b


fill_scen = [(eg, fill_for(eg)) for eg in (-1.50, -1.00, -0.50)]
fdt_layers = math.ceil((0.10 - M.EXIST_GROUND) / 0.20)
fdt_tests = fdt_layers * math.ceil(site_area / 500)

# ---------------------------------------------------------------- verification
# status: ok | diff | missing | assume
V = [
    ("1.3.1", "ถมดินปรับระดับ (ลบ.ม.)", "1,856", "ถนนอ้างอิง -1.50 / ถนนรอบอาคาร ±0.00 / FFL +0.50 (A202)",
     f"{fill_vol:,.0f}", "diff",
     f"BOQ สมมติถมเฉลี่ย 0.50 ม. แต่แบบ A202 ระดับถนนอ้างอิงต่ำกว่าถนนรอบอาคาร 1.50 ม. ถ้าดินเดิมอยู่ที่ -1.50 ต้องถม ~{fill_vol:,.0f} ลบ.ม. (ดินเดิม -1.00 ≈ {fill_scen[1][1]:,.0f} / -0.50 ≈ {fill_scen[2][1]:,.0f}) ให้ยืนยันด้วยผลสำรวจระดับ P1.2 ก่อนยื่นราคา และเสนอเป็นราคาต่อ ลบ.ม."),
    ("1.4.3", "ทดสอบความแน่นดินถม (จุด)", "6", "ทุก 500 ตร.ม./ชั้น (ข้อกำหนด 1.3.2 ชั้นละ 0.20 ม.)",
     f"{fdt_tests}", "diff", f"พื้นที่ {site_area:,.0f} ตร.ม. ÷ 500 = {math.ceil(site_area/500)} จุด/ชั้น × {fdt_layers} ชั้น (ถมหนา {0.10-M.EXIST_GROUND:.2f} ม.) = {fdt_tests} จุด"),
    ("2.1", "เสาเข็มรวม (ต้น)", "470", "737 (S201-B ตาราง S2)", f"{sum(1 for e in E if e['ifc']=='IfcPile')}", "diff",
     "BOQ ขาด 267 ต้น: เข็มพื้นถนนรอบอาคาร I22 249 ต้น, ฐานหม้อแปลง 6 ต้น, ถังใต้ดิน 17 ต้น; ระบุขนาดเข็มตามแบบ (I22/I26/I35) ยาว 22 ม."),
    ("2.1.1", "เข็มฐานราก I-260x260 ยาว 22 ม. (ต้น)", "92", "105 (I26-22)", f"{cnt['I26-22']}", "diff",
     "แบบนับรวมฐาน F1P-1 เข็มเดี่ยว 11 ต้น (อาคารประกอบ) และ F2P 47 ฐาน; โมเดลวาง F2P ได้ 46 ฐาน = 92 + 11 = 103"),
    ("2.1.2", "เข็มใต้พื้น I-350x350 ยาว 22 ม. (ต้น)", "360", "360 (I35-22)", f"{cnt['I35-22']}", "ok",
     "ตรงกัน ระยะ 3.00x3.00 ม. เยื้องกริด 1.50 ม. ระวัง: ขนาด 350 มม. ใหญ่กว่าเข็มฐานราก ราคาต่อต้นต่างกัน"),
    ("2.1.3", "เข็มอาคารประกอบ (ต้น)", "18", "I26 ถังใต้ดิน 17 + I22-TR หม้อแปลง 6 = 23", f"{cnt['I26']+cnt['I22-TR']}", "diff",
     "แยกรายการตามขนาดเข็ม เข็มถังใต้ดินตัดหัวลดระดับ 1 ม."),
    ("—", "เข็ม I-220x220 รับพื้นถนนรอบอาคาร (ต้น)", "ไม่มี", "249 (I22-22)", f"{cnt['I22-22']}", "missing",
     "เพิ่มในหมวดงานบริเวณ พร้อมฐาน F1A 0.60x0.60x0.30 249 ฐาน (คอนกรีต 26.78 ลบ.ม.)"),
    ("2.1.4", "ตัดหัวเข็ม (ต้น)", "470", "737", "737", "diff", "ปรับตามจำนวนเข็มจริง"),
    ("2.2.1", "ฐานราก F2P 0.60x1.50x0.80 (ฐาน)", "46", "47 (ปริมาตร 33.12 ลบ.ม. = 46 ฐาน)", f"{cnt['F2P']}", "assume",
     "ตารางนับ 47 แต่ปริมาตรเท่ากับ 46 ฐาน (0.72 ลบ.ม./ฐาน) และผัง S201 นับได้ 46 → ตรวจหาฐานซ้อนใน Revit"),
    ("—", "Drop panel F1P 1.00x1.00x0.20 (จุด)", "ไม่มี", "360 (72.00 ลบ.ม.)", f"{cnt['F1P']}", "missing", "เพิ่มรายการ หรือระบุว่ารวมในพื้น 2.3.2"),
    ("—", "ฐาน F1P-1 0.60x0.60x0.60 (ฐาน)", "ไม่มี", "11 (2.38 ลบ.ม.)", f"{cnt['F1P-1']}", "missing", "เพิ่มในหมวด 2.5 อาคารประกอบ"),
    ("2.2.2", "เสาตอม่อ/เสา คสล. (ต้น)", "46", "C1 0.30x0.50 45 + C2 0.50x0.50 1 (33.50 ลบ.ม.)", f"{cnt['C1']}", "ok",
     "เสา C1 สูงจากหลังฐานรากถึง +4.50 (4.90 ม.) ไม่ใช่ตอม่อสั้น ไม้แบบ 362.6 ตร.ม."),
    ("2.3.1", "คานคอดิน B1 0.20x0.60 (ม.)", "ว่าง", "282.00 ม. / 32.04 ลบ.ม.", f"{b1_len:,.2f}", "missing",
     "กรอกปริมาณ: แนวรอบอาคาร + แนวกริด 6, ไม้แบบ 394.8 ตร.ม., B3 0.20x0.40 40.45 ม."),
    ("2.3.2", "พื้น S1 คสล. หนา 0.20 (ตร.ม.)", "3,240", "3,206.48 ตร.ม. / 641.30 ลบ.ม.", "3,240 (รวมช่องเสา)", "ok", "พื้นวางบนเข็ม TOP +0.50 BOT +0.30"),
    ("2.4.1", "โครงสร้างเหล็ก (กก.)", "ว่าง", "เสา H250x175x44.1 47 ต้น ยาว 215.72 ม.", f"{tot_kg*1.1:,.0f}", "missing",
     f"ประมาณการจากโมเดล {tot_kg:,.0f} กก. + จุดต่อ 10% (≈ {tot_kg*1.1/3240:.1f} กก./ตร.ม.) หน้าตัดโครงถัก/แปเป็นค่าสมมติ รอแบบโครงหลังคา"),
    ("—", "ชั้นลอย F8 (ตร.ม.)", "ไม่มี", "306.15 ตร.ม. + เสา H250x250x66.5 36 ต้น", "306", "missing", "เพิ่มรายการโครงเหล็กชั้นลอย พื้น และบันได"),
    ("3.1", "หลังคาเมทัลชีท (ตร.ม. ตามลาด)", "ว่าง", "สันหลังคา +14.10, Jack roof +15.25 (A202)", f"{roof_area:,.0f}", "missing",
     f"ผนังเมทัลชีท ≈ {clad_area:,.0f} ตร.ม., Jack roof 6.00x42.00 ม., รางน้ำ 2 x 55 ม."),
    ("3.2", "ผนังก่ออิฐ ถึง +4.50 (ตร.ม.)", "ว่าง", "ยังไม่มีแบบสถาปัตย์ผนัง", f"{wall_area:,.0f}", "assume", "สมมติผนังก่อถึงระดับหัวเสาคอนกรีต +4.50 ตามรูปด้าน A202"),
    ("3.3.1", "พื้นขัดมันผสม Floor Hardener (ตร.ม.)", "3,240", "3,206.48", "3,240", "ok", ""),
    ("—", "พื้นถนนรอบอาคาร S2 หนา 0.15 (ตร.ม.)", "ไม่มี", "2,440.69 ตร.ม. / 366.10 ลบ.ม.", f"{road_area:,.0f}", "missing",
     "ชื่องาน \"งานก่อสร้างอาคารโกดังและงานบริเวณ\" แต่ BOQ ยังไม่มีหมวดงานบริเวณ ควรเพิ่มหมวด 4"),
    ("—", "ถังเก็บน้ำใต้ดิน คสล. (TF -2.60 / BF -2.85)", "ไม่มี", "S202 + เข็ม I26 17 ต้น", "1 ชุด", "missing", "ต้องขุดลึก ~3.0 ม. ใช้ Sheet pile/ค้ำยันดิน และสูบน้ำ"),
    ("—", "รางระบายน้ำพร้อมฝาปิด (ม.)", "ไม่มี", "A101 แนวรอบที่ดิน", f"{drain_len:,.0f}", "missing", "ขนาดรางรอแบบขยาย (โมเดลสมมติ 0.40x0.50)"),
    ("—", "ฐานหม้อแปลง SF02 / ห้อง MDB / ห้องเก็บสารเคมี", "ไม่มี", "SF02 93.26 ตร.ม., MDB 17.79 ตร.ม., Chem 21.84 ตร.ม.", "มีในโมเดล", "missing", "เพิ่มในหมวด 2.5/3.6"),
    ("1.2.1", "รั้วชั่วคราว (ม.)", "308", f"เส้นรอบที่ดิน (A101) ≈ {site_per:,.0f}", f"{site_per:,.0f}", "ok", "ใกล้เคียงค่าที่สมมติ"),
    ("P2.1", "เคลียร์พื้นที่ (ตร.ม.)", "5,920", f"พื้นที่ดินตามผัง A101 ≈ {site_area:,.0f}", f"{site_area:,.0f}", "ok", "ใกล้เคียงค่าที่สมมติ"),
    ("1.4.2", "Dynamic Load Test (ต้น)", "2", "เข็ม 3 ขนาด", "≥ 3", "assume", "แนะนำอย่างน้อย 1 ต้นต่อขนาดเข็ม (I22/I26/I35) หรือ 1% ของจำนวนเข็ม"),
    ("1.2.9/1.5", "ระยะเวลาก่อสร้าง (เดือน)", "6", "—", f"{(S['M52']['finish']-S['M0']['start']).days/30.4:.1f}", "ok",
     f"แผน CPM งานหลัก {S['M0']['start']:%d/%m/%Y} – {S['M52']['finish']:%d/%m/%Y} สายงานวิกฤตผ่านถมดิน → ตอกเข็ม → ฐานราก/เสา → โครงเหล็ก → หลังคา → พื้น"),
    ("แบบ", "กรอบชื่อแบบ", "—", "ช่องโครงการระบุ \"แบบก่อสร้างบ้านพักอาศัย คสล 1 ชั้น\" ทุกแผ่น / Date 03/31/22", "—", "diff", "แก้กรอบชื่อแบบก่อนแนบประกอบใบเสนอราคา"),
]

# ---------------------------------------------------------------- IFC
import ifcopenshell, ifcopenshell.api, ifcopenshell.guid

f = ifcopenshell.api.run("project.create_file", version="IFC4")
proj = ifcopenshell.api.run("root.create_entity", f, ifc_class="IfcProject", name="WEC-TC-6901 งานก่อสร้างอาคารโกดังและงานบริเวณ")
ifcopenshell.api.run("unit.assign_unit", f, length={"is_metric": True, "raw": "METERS"})
ctx = ifcopenshell.api.run("context.add_context", f, context_type="Model")
body = ifcopenshell.api.run("context.add_context", f, context_type="Model", context_identifier="Body", target_view="MODEL_VIEW", parent=ctx)
site = ifcopenshell.api.run("root.create_entity", f, ifc_class="IfcSite", name="10/7 หมู่ 5 ต.ท่าข้าม อ.สามพราน จ.นครปฐม")
bld = ifcopenshell.api.run("root.create_entity", f, ifc_class="IfcBuilding", name="อาคารโกดัง TC Electric 60x54 ม.")
ifcopenshell.api.run("aggregate.assign_object", f, relating_object=proj, products=[site])
ifcopenshell.api.run("aggregate.assign_object", f, relating_object=site, products=[bld])
STOREYS = [("B1", "ฐานราก/เสาเข็ม", -1.20), ("00", "ระดับถนนรอบอาคาร ±0.00", 0.0), ("01", "พื้นชั้นที่ 1 +0.50", 0.50),
           ("02", "พื้นชั้นลอย +3.30", 3.30), ("03", "หัวเสาคอนกรีต +4.50", 4.50), ("RF", "หัวเสารับหลังคา +9.00", 9.00)]
st = {}
for code, nm, el in STOREYS:
    s_ = ifcopenshell.api.run("root.create_entity", f, ifc_class="IfcBuildingStorey", name=f"{code} {nm}")
    s_.Elevation = el
    ifcopenshell.api.run("aggregate.assign_object", f, relating_object=bld, products=[s_])
    st[code] = s_

ORIGIN = f.createIfcCartesianPoint((0.0, 0.0, 0.0))
ZDIR = f.createIfcDirection((0.0, 0.0, 1.0))
P2D = f.createIfcAxis2Placement2D(f.createIfcCartesianPoint((0.0, 0.0)), None)
A3D0 = f.createIfcAxis2Placement3D(ORIGIN, None, None)


def r3(v): return tuple(round(float(c), 4) for c in v)


def placement(loc, ez, ex):
    return f.createIfcLocalPlacement(None, f.createIfcAxis2Placement3D(
        f.createIfcCartesianPoint(r3(loc)), f.createIfcDirection(r3(ez)), f.createIfcDirection(r3(ex))))


def storey_for(e):
    m, c = e["mark"], e["cat"]
    if c in ("pile", "found") or m in ("UGT",): return st["B1"]
    if c in ("ext",): return st["00"]
    if m in ("MC", "MB", "F8", "ST"): return st["02"]
    if c == "steel" and m == "SC1": return st["03"]
    if c in ("steel", "roof") or m in ("W2",): return st["RF"]
    if c in ("site", "earth", "temp"): return None
    return st["01"]


IFC_MAP = {"IfcEarthworksFill": ("IfcBuildingElementProxy", "USERDEFINED", "EarthworksFill")}
by_container = collections.defaultdict(list)
by_task = collections.defaultdict(list)
pset_rows = []
t0 = time.time()
for i, e in enumerate(E):
    cls, pre, otype = e["ifc"], e.get("pre"), None
    if cls in IFC_MAP: cls, pre, otype = IFC_MAP[cls]
    el = f.create_entity(cls, GlobalId=ifcopenshell.guid.new(), Name=e["name"][:255], Tag=e["mark"])
    if otype: el.ObjectType = otype
    if pre:
        try: el.PredefinedType = pre
        except Exception: el.PredefinedType = "USERDEFINED"; el.ObjectType = pre
    if e["kind"] == "box":
        loc = M.sub(e["c"], M.mul(e["ez"], e["h"]/2))
        el.ObjectPlacement = placement(loc, e["ez"], e["ex"])
        prof = f.createIfcRectangleProfileDef("AREA", None, P2D, round(e["a"], 4), round(e["b"], 4))
        solid = f.createIfcExtrudedAreaSolid(prof, A3D0, ZDIR, round(e["h"], 4))
    else:
        el.ObjectPlacement = placement(e["o"], e["ez"], e["ex"])
        def pl(pts): return f.createIfcPolyline([f.createIfcCartesianPoint((round(p[0], 4), round(p[1], 4))) for p in list(pts)+[pts[0]]])
        if e["holes"]:
            prof = f.createIfcArbitraryProfileDefWithVoids("AREA", None, pl(e["outer"]), [pl(h) for h in e["holes"]])
        else:
            prof = f.createIfcArbitraryClosedProfileDef("AREA", None, pl(e["outer"]))
        solid = f.createIfcExtrudedAreaSolid(prof, A3D0, ZDIR, round(e["h"], 4))
    rep = f.createIfcShapeRepresentation(body, "Body", "SweptSolid", [solid])
    el.Representation = f.createIfcProductDefinitionShape(None, None, [rep])
    cont = storey_for(e) or site
    by_container[cont.id()].append(el)
    by_task[e["task"]].append(el)
    t = S[e["task"]]
    q = qty(e)
    props = {"WBS": e["wbs"], "BOQ_Item": e["boq"], "TypeMark": e["mark"], "Source": e["src"],
             "TaskID": e["task"], "TaskName": t["name"], "PlannedStart": t["start"].isoformat(),
             "PlannedFinish": t["finish"].isoformat(), "Volume_m3": round(q["vol"], 4)}
    if e["kind"] == "box": props.update({"Length_m": round(e["h"], 3), "Width_m": round(e["a"], 3), "Depth_m": round(e["b"], 3)})
    else: props["Area_m2"] = round(q["area"], 2)
    if steel_kg(e): props["SteelWeight_kg"] = round(steel_kg(e), 1)
    if e.get("remove_task"): props["RemovedBy"] = e["remove_task"]
    for k, v in e["extra"].items(): props["X_" + k] = v
    pset_rows.append((el, props))

for cid, els in by_container.items():
    f.createIfcRelContainedInSpatialStructure(ifcopenshell.guid.new(), None, None, None, els, f.by_id(cid))


def props_ifc(d):
    out = []
    for k, v in d.items():
        if isinstance(v, bool): val = f.createIfcBoolean(v)
        elif isinstance(v, int): val = f.createIfcInteger(v)
        elif isinstance(v, float): val = f.createIfcReal(v)
        else: val = f.createIfcLabel(str(v)[:255])
        out.append(f.createIfcPropertySingleValue(k, None, val, None))
    return out


# share psets per element (one pset each - required by viewers to show per-element values)
for el, d in pset_rows:
    ps = f.createIfcPropertySet(ifcopenshell.guid.new(), None, "Pset_TC_BOQ_4D", None, props_ifc(d))
    f.createIfcRelDefinesByProperties(ifcopenshell.guid.new(), None, None, None, [el], ps)

# 4D: work plan / schedule / tasks
wp = ifcopenshell.api.run("sequence.add_work_plan", f, name="แผนงานเสนอราคา TC Warehouse")
ws = ifcopenshell.api.run("sequence.add_work_schedule", f, name="Baseline (Bid) – CPM", work_plan=wp)
ifc_tasks = {}
for tid in TASK_ORDER:
    t = S[tid]
    task = ifcopenshell.api.run("sequence.add_task", f, work_schedule=ws, name=t["name"], identification=tid)
    task.Description = f"WBS {t['wbs']} | {t['crew']}"
    tt = ifcopenshell.api.run("sequence.add_task_time", f, task=task)
    ifcopenshell.api.run("sequence.edit_task_time", f, task_time=tt, attributes={
        "ScheduleStart": dt.datetime.combine(t["start"], dt.time(8)), "ScheduleFinish": dt.datetime.combine(t["finish"], dt.time(17)),
        "ScheduleDuration": f"P{t['dur']}D", "IsCritical": bool(t["critical"]), "TotalFloat": f"P{max(t['float'],0)}D"})
    ifc_tasks[tid] = task
for tid in TASK_ORDER:
    for (p, typ, lag) in S[tid]["preds"]:
        rel = ifcopenshell.api.run("sequence.assign_sequence", f, relating_process=ifc_tasks[p], related_process=ifc_tasks[tid])
        rel.SequenceType = "FINISH_START" if typ == "FS" else "START_START"
        if lag:
            ifcopenshell.api.run("sequence.assign_lag_time", f, rel_sequence=rel, lag_value=f"P{lag}D", duration_type="WORKTIME")
for tid, els in by_task.items():
    f.createIfcRelAssignsToProcess(ifcopenshell.guid.new(), None, f"Outputs {tid}", None, els, None, ifc_tasks[tid], None)

ifc_path = os.path.join(OUT, "TC-WH_BIM.ifc")
f.write(ifc_path)
print("IFC", ifc_path, os.path.getsize(ifc_path)//1024, "KB", f"{time.time()-t0:.1f}s")

# ---------------------------------------------------------------- viewer JSON
strings = []; sidx = {}


def sid(s):
    if s not in sidx: sidx[s] = len(strings); strings.append(s)
    return sidx[s]


def rnd(v, n=3): return [round(x, n) for x in v]


els = []
for i, e in enumerate(E):
    rec = {"g": e["cat"], "n": sid(e["name"]), "m": sid(e["mark"]), "t": TASK_ORDER.index(e["task"]),
           "b": sid(e["boq"]), "s": sid(e["src"]), "i": sid(e["ifc"])}
    if e.get("remove_task"): rec["r"] = TASK_ORDER.index(e["remove_task"])
    q = qty(e); rec["v"] = round(q["vol"], 3)
    kg = steel_kg(e)
    if kg: rec["kg"] = round(kg, 1)
    if e["kind"] == "box":
        rec["k"] = 0
        rec["M"] = rnd(M.mul(e["ex"], e["a"])) + rnd(M.mul(e["ey"], e["b"])) + rnd(M.mul(e["ez"], e["h"])) + rnd(e["c"])
        rec["d"] = [round(e["a"], 3), round(e["b"], 3), round(e["h"], 3)]
    else:
        rec["k"] = 1
        rec["o"] = rnd(e["o"]); rec["ex"] = rnd(e["ex"]); rec["ey"] = rnd(e["ey"]); rec["ez"] = rnd(e["ez"])
        rec["P"] = [rnd(p, 2) for p in e["outer"]]; rec["H"] = [[rnd(p, 2) for p in h] for h in e["holes"]]; rec["h"] = round(e["h"], 3)
        rec["ar"] = round(q["area"], 1)
    els.append(rec)

tasks_json = [dict(id=t, wbs=S[t]["wbs"], name=S[t]["name"], dur=S[t]["dur"], start=S[t]["start"].isoformat(),
                   finish=S[t]["finish"].isoformat(), crit=bool(S[t]["critical"]), fl=S[t]["float"], crew=S[t]["crew"],
                   pred=[f"{p} {typ}{('+'+str(lag)) if lag else ''}" for (p, typ, lag) in S[t]["preds"]],
                   n=sum(1 for e in E if e["task"] == t)) for t in TASK_ORDER]
qto_json = [dict(boq=k[0], mark=k[1], name=k[2], n=g["n"], len=round(g["len"], 2), area=round(g["area"], 2), vol=round(g["vol"], 3),
                 kg=round(g["kg"], 1), src=g["src"], task=g["task"]) for k, g in groups.items()]
data = dict(
    meta=dict(project="งานก่อสร้างอาคารโกดังและงานบริเวณ", owner="บริษัท ตงเฉิน อีเล็คทริค เคเบิ้ล แอนด์ไวร์ จำกัด",
              site="เลขที่ 10/7 หมู่ที่ 5 ต.ท่าข้าม อ.สามพราน จ.นครปฐม 73110", no="WEC-TC-6901",
              contractor="WISDOM Engineering & Construction", generated=dt.date.today().isoformat(),
              drawings=["S201", "S201-B", "S202", "A101", "A202"], levels=M.LV, exist_ground=M.EXIST_GROUND,
              grid=dict(x=M.GX, y=M.GY, xn=M.GXN, yn=M.GYN), site_poly=M.SITE,
              kpi=dict(elements=len(E), piles=sum(1 for e in E if e["ifc"] == "IfcPile"), pile_len=round(pile_len),
                       steel_t=round(tot_kg*1.1/1000, 1), fill=round(fill_vol), site_area=round(site_area), road_area=round(road_area),
                       roof_area=round(roof_area), start_main=S["M0"]["start"].isoformat(), finish=S["M52"]["finish"].isoformat()),
              fill_scen=[[a, round(b)] for a, b in fill_scen]),
    strings=strings, els=els, tasks=tasks_json, qto=qto_json,
    verify=[dict(item=a, desc=b, boq=c, dwg=d, model=e_, st=s_, note=n) for (a, b, c, d, e_, s_, n) in V])
with open(os.path.join(OUT, "model.json"), "w", encoding="utf-8") as fh:
    json.dump(data, fh, ensure_ascii=False, separators=(",", ":"))
tpl = open(os.path.join(HERE, "viewer.html"), encoding="utf-8").read()
html = tpl.replace("/*__DATA__*/null", json.dumps(data, ensure_ascii=False, separators=(",", ":")))
with open(os.path.join(HERE, "index.html"), "w", encoding="utf-8") as fh:
    fh.write(html)
print("viewer", len(html)//1024, "KB")

# ---------------------------------------------------------------- XLSX
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

wb = Workbook()
HDR = PatternFill("solid", fgColor="1F3A4D"); HF = Font(color="FFFFFF", bold=True, name="Tahoma")
FILLS = {"ok": "D9EAD3", "diff": "FCE5CD", "missing": "F4CCCC", "assume": "FFF2CC"}
LBL = {"ok": "ตรง", "diff": "ต่าง", "missing": "ขาดใน BOQ", "assume": "สมมติ/ตรวจ"}
thin = Side(style="thin", color="BBBBBB")


def sheet(ws, title, header, rows, widths):
    ws.append([title]); ws["A1"].font = Font(bold=True, size=13, name="Tahoma")
    ws.append([f"{data['meta']['project']} – {data['meta']['owner']} | Project No. {data['meta']['no']} | สร้างจากโมเดล BIM {data['meta']['generated']}"])
    ws.append(header)
    for c in range(1, len(header)+1):
        cell = ws.cell(row=3, column=c); cell.fill = HDR; cell.font = HF; cell.alignment = Alignment(wrap_text=True, vertical="center")
    for r in rows: ws.append(r)
    for i, w in enumerate(widths, 1): ws.column_dimensions[get_column_letter(i)].width = w
    for row in ws.iter_rows(min_row=4):
        for cell in row:
            cell.border = Border(top=thin, bottom=thin, left=thin, right=thin)
            cell.alignment = Alignment(wrap_text=True, vertical="top"); cell.font = Font(name="Tahoma", size=10)
    ws.freeze_panes = "A4"


ws = wb.active; ws.title = "1-ทวนสอบ BOQ"
sheet(ws, "ตารางทวนสอบ BOQ เทียบแบบและโมเดล BIM", ["รายการ BOQ", "รายละเอียด", "BOQ", "แบบ (S201-B/S202/A101/A202)", "โมเดล BIM", "ผล", "ข้อสังเกต / สิ่งที่ต้องแก้"],
      [[a, b, c, d, e_, LBL[s_], n] for (a, b, c, d, e_, s_, n) in V], [9, 34, 12, 34, 14, 12, 70])
for r, row in enumerate(V, start=4):
    ws.cell(row=r, column=6).fill = PatternFill("solid", fgColor=FILLS[row[5]])

ws2 = wb.create_sheet("2-QTO จากโมเดล")
sheet(ws2, "ถอดปริมาณจากโมเดล BIM (Quantity Take-off)", ["รายการ BOQ", "Type Mark", "ชิ้นส่วน", "จำนวน", "ความยาวรวม (ม.)", "พื้นที่ (ตร.ม.)", "ปริมาตร (ลบ.ม.)", "เหล็ก (กก.)", "กิจกรรม 4D", "ที่มา"],
      [[q["boq"], q["mark"], q["name"], q["n"], q["len"], q["area"], q["vol"], q["kg"] or None, q["task"], q["src"]] for q in qto_json],
      [30, 10, 46, 8, 13, 13, 13, 12, 9, 22])
ws3 = wb.create_sheet("3-แผนงาน 4D")
sheet(ws3, "แผนงานก่อสร้าง (CPM) วันทำงาน จันทร์–เสาร์ หักวันหยุดราชการ", ["ID", "WBS", "กิจกรรม", "วันทำงาน", "เริ่ม", "เสร็จ", "Float (วัน)", "วิกฤต", "ก่อนหน้า", "ทรัพยากร", "ชิ้นส่วนในโมเดล"],
      [[t["id"], t["wbs"], t["name"], t["dur"], dt.date.fromisoformat(t["start"]), dt.date.fromisoformat(t["finish"]), t["fl"], "●" if t["crit"] else "", ", ".join(t["pred"]), t["crew"], t["n"]] for t in tasks_json],
      [7, 6, 52, 9, 12, 12, 9, 7, 22, 40, 11])
for row in ws3.iter_rows(min_row=4, min_col=5, max_col=6):
    for c in row: c.number_format = "dd/mm/yyyy"
ws4 = wb.create_sheet("4-ดินถม")
sheet(ws4, "สถานการณ์ปริมาณดินถม (ยืนยันด้วยสำรวจระดับ P1.2)", ["ระดับดินเดิมสมมติ", "ภายนอกอาคาร ถมถึง -0.25 (ลบ.ม.)", "ใต้อาคาร ถมถึง +0.10 (ลบ.ม.)", "รวม (ลบ.ม. บดอัด)", "เทียบ BOQ 1,856"],
      [[eg, round((site_area-3240)*(-0.25-eg)), round(3240*(0.10-eg)), round(v), f"x{v/1856:.1f}"] for eg, v in fill_scen], [18, 26, 24, 18, 14])
xl = os.path.join(OUT, "TC-WH_BIM_QTO.xlsx"); wb.save(xl)
print("xlsx", xl)
print("KPI", data["meta"]["kpi"])
