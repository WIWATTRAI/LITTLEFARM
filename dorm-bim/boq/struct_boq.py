"""BOQ + ใบราคาวัสดุ งานโครงสร้าง หอพัก A จาก elements.json
ใช้: python3 struct_boq.py elements.json OUTDIR SHA  → BOQ_struct.xlsx/.html, PRICE_struct.xlsx/.html"""
import sys, os, json, math, collections, html
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill
sys.path.insert(0, os.path.dirname(__file__))
from price_common import tw, tws, write_xlsx, write_html

src, OUT, SHA = sys.argv[1:4]
EL = json.load(open(src))['elements']
c = math.ceil
FLOORS = [1, 2, 3, 4, 5]

# ---------- ปริมาณ ----------
B = collections.OrderedDict()      # (หมวด, รายการ, สเปก, หน่วย) -> {floor: qty}


def put(cat, item, spec, unit, floor, q):
    d = B.setdefault((cat, item, spec, unit), collections.defaultdict(float))
    d[floor] += q


CONC = {'เสา': 'คอนกรีตเสา (รวมตอม่อ)', 'คาน': 'คอนกรีตคาน', 'คานคอดิน': 'คอนกรีตคานคอดิน', 'พื้น': 'คอนกรีตพื้นหล่อในที่',
        'พื้นทับหน้า': 'คอนกรีตทับหน้าแผ่นพื้นสำเร็จ (รวมเติมร่อง)', 'บันได': 'คอนกรีตบันได คสล.'}
for e in EL:
    cat = e['category']; q = e.get('qty') or {}; f = e.get('floor')
    if cat in CONC and q.get('concrete'):
        put('1 คอนกรีต', CONC[cat], '', 'ลบ.ม.', f, q['concrete'])
    if cat == 'พื้นสำเร็จรูป':
        put('2 แผ่นพื้นสำเร็จรูป', f'แผ่นพื้นสำเร็จรูปท้องเรียบ ยาว {q["plank_length"]:.2f} ม.', q.get('plank_size', ''), 'แผ่น', f, q.get('planks', 0))
        put('2 แผ่นพื้นสำเร็จรูป', 'พื้นที่แผ่นพื้นสำเร็จรูป', '', 'ตร.ม.', f, q.get('area', 0))
    if cat == 'โครงหลังคาเหล็ก':
        sec = q.get('section'); mk = q.get('mark')
        if sec:
            n = 2 if sec.startswith('2C') else 1
            base = sec[1:] if n == 2 else sec
            put('3 โครงหลังคาเหล็ก', f'เหล็กตัวซี {base}', 'รวมทุกชิ้น (2C = 2 ตัวประกบ)', 'ม.', f, q['length'] * n)
            put('3 โครงหลังคาเหล็ก', f'เหล็กตัวซี {base} (น้ำหนัก)', '', 'กก.', f, q.get('weight_kg', 0))
        elif mk == 'PL':
            put('3 โครงหลังคาเหล็ก', 'เพลทฐานโครงหลังคา', '', 'แผ่น', f, q.get('count', 1))
            put('3 โครงหลังคาเหล็ก', 'เพลทฐานโครงหลังคา (น้ำหนัก)', '', 'กก.', f, q.get('weight_kg', 0))
        elif mk == 'JB':
            put('3 โครงหลังคาเหล็ก', 'J-bolt ยึดเพลทฐาน', f'ยาว {q.get("length", 0):.3f} ม.', 'ตัว', f, q.get('count', 1))
        elif 'model' in q:
            put('3 โครงหลังคาเหล็ก', 'แปเหล็กกัลวาไนซ์ หนา 0.55 มม.', q['model'], 'ม.', f, q['length'])
    if e['id'].startswith(('SC-', 'FS-')):
        nm = e['name']
        if 'section' in q:
            put('4 เหล็กโครงสร้าง บันไดหนีไฟ', f'เหล็ก {q["section"]}', nm.split(' ')[0], 'ม.', f, q['length'])
        elif 'size' in q and 'PL' in q['size']:
            put('4 เหล็กโครงสร้าง บันไดหนีไฟ', f'เพลท {q["size"]}', '', 'แผ่น', f, q.get('count', 1))
            put('4 เหล็กโครงสร้าง บันไดหนีไฟ', 'เพลทรวม (น้ำหนัก)', '', 'กก.', f, q.get('weight_kg', 0))
        elif q.get('size') == 'M16x200':
            put('4 เหล็กโครงสร้าง บันไดหนีไฟ', 'สลักยึดเสา M16x200 + แหวน + น็อต', '', 'ชุด', f, q.get('count', 1))
        elif q.get('size') == 'DB16':
            put('4 เหล็กโครงสร้าง บันไดหนีไฟ', 'เหล็กเดือย DB16', 'ยาว 0.20 ม./ท่อน', 'ม.', f, q['count'] * q['length_each'])
        elif 'riser' in q:
            put('4 เหล็กโครงสร้าง บันไดหนีไฟ', 'เหล็กแผ่นลาย 4 มม. (ขั้นบันได พับ Z)', '', 'ตร.ม.', f, q['count'] * q['width'] * (q['going'] + q['riser']))
        elif 'area' in q:
            put('4 เหล็กโครงสร้าง บันไดหนีไฟ', 'เหล็กแผ่นลาย 4 มม. (ชานพัก)', '', 'ตร.ม.', f, q['area'])
        elif 'pipe_1.5in_m' in q:
            put('4 เหล็กโครงสร้าง บันไดหนีไฟ', 'ท่อเหล็กดำ 1½" หนา 2.3 มม. (ราวจับ)', '', 'ม.', f, q['pipe_1.5in_m'])
            put('4 เหล็กโครงสร้าง บันไดหนีไฟ', 'ท่อเหล็กดำ 1" หนา 2.3 มม. (ราวจับ)', '', 'ม.', f, q['pipe_1in_m'])
        elif 'pieces' in q:
            put('4 เหล็กโครงสร้าง บันไดหนีไฟ', 'โครงชานพัก เหล็กกล่อง 125x75x3.2 + 100x50x3.2', 'ความยาวไม่ได้เก็บในโมเดล', 'ชิ้น', f, q['pieces'])


# เรียงตามหมวด (คงลำดับภายในหมวด; คอนกรีตเรียงตาม CONC)
_co = list(CONC.values())
B = collections.OrderedDict(sorted(B.items(), key=lambda kv: (kv[0][0], _co.index(kv[0][1]) if kv[0][1] in _co else 0)))


def tot(k):
    return sum(B[k].values())


def find(cat, item):
    return next(k for k in B if k[0] == cat and k[1] == item)


# ---------- BOQ xlsx/html ----------
wb = Workbook(); ws = wb.active; ws.title = 'BOQ โครงสร้าง'
ws.append(['BOQ งานโครงสร้าง หอพัก A (แยกชั้น จากโมเดล BIM)']); ws['A1'].font = Font(bold=True, size=14)
ws.append([f'โมเดล BIM commit {SHA} · ปริมาณสุทธิ ยังไม่เผื่อเศษ · ไม่มีฐานราก/เสาเข็ม และเหล็กเสริมคอนกรีตในโมเดล'])
hdr = ['หมวด', 'รายการ', 'สเปก/หมายเหตุ', 'หน่วย'] + [f'ชั้น {f}' for f in FLOORS] + ['รวม']
ws.append([]); ws.append(hdr)
for cc in ws[4]:
    cc.font = Font(bold=True); cc.fill = PatternFill('solid', fgColor='DDEBF7')
rows_html = []
for k, d in B.items():
    vals = [round(d.get(f, 0), 3) for f in FLOORS]
    ws.append(list(k) + [v or None for v in vals] + [round(sum(vals), 3)])
    rows_html.append(list(k) + vals + [round(sum(vals), 3)])
for col, wd in zip('ABCDEFGHIJ', (26, 46, 40, 8, 10, 10, 10, 10, 10, 11)):
    ws.column_dimensions[col].width = wd
NOTES_B = ['ปริมาณคอนกรีตเป็นปริมาตรสุทธิจากรูปทรงในโมเดล ยังไม่เผื่อเศษ (ควรเผื่อ 3–5%)',
           'ยังไม่มีในโมเดล: ฐานราก เสาเข็ม เหล็กเสริมคอนกรีต แบบหล่อ — ต้องถอดจากแบบโครงสร้าง (S-series) เพิ่ม',
           'เหล็กตัวซีหลังคา: 2C = เหล็กตัวซี 2 ตัวประกบ ความยาวในตารางคิดรวมทั้ง 2 ตัวแล้ว',
           'แปหลังคาอยู่หมวดโครงหลังคาตามโมเดล; กระเบื้องหลังคาและเชิงชายไม่รวม']
ws.append([]); ws.append(['หมายเหตุ'])
for i, n in enumerate(NOTES_B, 1):
    ws.append([f'{i}) {n}'])
wb.save(os.path.join(OUT, 'BOQ_struct.xlsx'))
E = lambda v: '' if v is None else html.escape(str(v))
N = lambda v: '' if not v else (f'{v:,.3f}'.rstrip('0').rstrip('.'))
trs = []; last = None
for r in rows_html:
    if r[0] != last:
        trs.append(f'<tr class=cat><td colspan="{len(hdr) - 1}">{E(r[0])}</td></tr>'); last = r[0]
    trs.append('<tr>' + ''.join(f'<td>{E(x)}</td>' for x in r[1:4]) + ''.join(f'<td class=n>{N(x)}</td>' for x in r[4:]) + '</tr>')
open(os.path.join(OUT, 'BOQ_struct.html'), 'w').write(f'''<!doctype html><html><head><meta charset="utf-8"><style>@page{{size:A4 landscape;margin:10mm}}body{{font-family:Loma,sans-serif;font-size:10.5px}}
h1{{font-size:16px;margin:0 0 3px}}p.s{{color:#444;margin:0 0 6px}}table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #999;padding:3px 5px;vertical-align:top}}th{{background:#ddebf7}}
td.n{{text-align:right}}tr.cat td{{background:#eef3e2;font-weight:bold}}tr{{page-break-inside:avoid}}</style></head><body>
<h1>BOQ งานโครงสร้าง — หอพัก A (แยกชั้น จากโมเดล BIM)</h1><p class=s>โมเดล BIM commit {SHA} · ปริมาณสุทธิ ยังไม่เผื่อเศษ</p>
<table><tr>{''.join(f'<th>{E(h)}</th>' for h in hdr[1:])}</tr>{''.join(trs)}</table><p><b>หมายเหตุ</b></p><ol>{''.join(f'<li>{E(n)}</li>' for n in NOTES_B)}</ol></body></html>''')

# ---------- ราคา ----------
R = []


def add(*a):
    R.append(a)


K = 'คอนกรีต'
for item in CONC.values():
    k = find('1 คอนกรีต', item); q = round(tot(k), 3)
    add(K, item, 'คอนกรีตผสมเสร็จ 240 ksc (ลูกบาศก์)', q, q, 'ลบ.ม.', q, 'ลบ.ม.', 'ไทวัสดุ', 'คอนกรีตทั่วไป 240 Cube Slump 7.5±2.5 อินทรีคอนกรีต (60212350)', 2750, tw('60212350'),
        'กำลังอัดสมมติ 240 ksc (ยังไม่ตรวจกับแบบ); ราคาต่อ ลบ.ม. ยังไม่รวมค่ารถ/ค่าปั๊ม')
K = 'แผ่นพื้นสำเร็จรูป'
for k in B:
    if k[0] == '2 แผ่นพื้นสำเร็จรูป' and k[3] == 'แผ่น':
        q = round(tot(k))
        add(K, k[1], k[2], q, q, 'แผ่น', q, 'แผ่น', None, None, None, tws('แผ่นพื้นสำเร็จรูป'), 'ไทวัสดุไม่มี ต้องขอราคาโรงงานแผ่นพื้น')
K = 'โครงหลังคาเหล็ก'
for base, sku, pr, prod in (('C100x50x20x3.2', '60195174', 768, 'เหล็กตัวซีมีขอบ 3.2 มม. มอก. 100x50x20 มม. (60195174)'),
                            ('C125x50x20x3.2', '60195178', 849, 'เหล็กตัวซีมีขอบ 3.2 มม. มอก. 125x50x20 มม. (60195178)')):
    k = find('3 โครงหลังคาเหล็ก', f'เหล็กตัวซี {base}'); L = tot(k)
    add(K, f'เหล็กตัวซี {base}', 'ยาว 6 ม./เส้น', round(L, 1), round(L, 1), 'ม.', c(L / 6), 'เส้น', 'ไทวัสดุ', prod, pr, tw(sku), 'ไม่เผื่อเศษตัด')
k = find('3 โครงหลังคาเหล็ก', 'แปเหล็กกัลวาไนซ์ หนา 0.55 มม.'); L = tot(k)
add(K, 'แปเหล็กกัลวาไนซ์ หนา 0.55 มม.', 'โมเดลระบุ SCG ยาว 4 ม.', round(L, 1), round(L, 1), 'ม.', c(L / 6), 'เส้น (6 ม.)', 'ไทวัสดุ', 'แปกัลวาไนซ์ เบอร์ 24 GIANT KINGKONG JL005 หนา 0.55 มม. ยาว 6 ม. (60278280)', 86, tw('60278280'), 'ไทวัสดุไม่มีแป SCG ราคานี้เป็นยี่ห้ออื่น ยาว 6 ม.')
for item, note in (('เพลทฐานโครงหลังคา', 'ตัดจากเหล็กแผ่นตามขนาด ไม่ได้หาราคา'), ('J-bolt ยึดเพลทฐาน', 'ไม่พบที่ไทวัสดุ')):
    k = next(k for k in B if k[1] == item); q = round(tot(k))
    add(K, item, k[2], q, q, k[3], q, k[3], None, None, None, '', note)
K = 'เหล็กโครงสร้าง บันไดหนีไฟ'
for k in B:
    if k[0] != '4 เหล็กโครงสร้าง บันไดหนีไฟ' or k[3] == 'กก.':
        continue
    q = round(tot(k), 3)
    if k[1].startswith('เหล็กแผ่นลาย'):
        add(K, k[1], 'แผ่น 5x10 ฟุต (4.645 ตร.ม.)', q, q, 'ตร.ม.', c(q / 4.645 * 1.15), 'แผ่น', 'ไทวัสดุ', 'เหล็กแผ่นลาย 4 มม. TMT 5x10 ฟุต (60442755)', 7005, tw('60442755'), 'เผื่อเศษตัด 15%; หมดสต็อกบนเว็บ')
    elif k[1] == 'สลักยึดเสา M16x200 + แหวน + น็อต':
        add(K, k[1], 'ตัดจากสตัดเกลียว M16 ยาว 1 ม. (5 ตัว/เส้น)', q, q, 'ชุด', c(q / 5), 'เส้น', 'ไทวัสดุ', 'สตัดเหล็กเกลียวมิล M16 ยาว 1 ม. GIANT KINGKONG (60418564)', 118, tw('60418564'), 'ยังไม่รวมแหวนและน็อต')
    elif k[1] == 'เหล็กเดือย DB16':
        add(K, k[1], 'SD40 16 มม. x 10 ม.', q, q, 'ม.', c(q / 10), 'เส้น', 'ไทวัสดุ', 'เหล็กข้ออ้อย (ตรง) SD-40T 16 มม. x 10 ม. (60194100)', 303.25, tw('60194100'), '')
    else:
        note = {'เหล็ก H175x175x11x16': 'ไทวัสดุมีแต่ H175x175x7.5x11 (18,085/12 ม.) หน้าตัดไม่ตรง',
                'เหล็ก H200x100x7x11': 'ไม่พบที่ไทวัสดุ', 'เหล็ก C200x100x7.5x11': 'ไทวัสดุมีแต่รางน้ำ 3–4 นิ้ว',
                }.get(k[1], 'ไม่พบขนาด/ความหนานี้ที่ไทวัสดุ' if 'ท่อ' in k[1] else 'ไม่ได้หาราคา')
        add(K, k[1], k[2], q, q, k[3], q, k[3], None, None, None, tws(k[1]), note)

notes = [f'ปริมาณจากโมเดล BIM (commit {SHA}) ปริมาณสุทธิ ยังไม่เผื่อเศษ (ยกเว้นที่ระบุ); ยังไม่มีงานที่ทำไปแล้ว คงเหลือ = ทั้งหมด',
         'ราคาไทวัสดุ ณ 26 พ.ย. 2569 ราคาบนเว็บ ไม่รวมค่าขนส่ง ควรตรวจในลิงก์ก่อนสั่งซื้อ',
         'แถวสีแดง = ยังไม่มีราคา ไม่รวมในยอดรวม',
         'ยังไม่รวม: ฐานราก เสาเข็ม เหล็กเสริมคอนกรีต แบบหล่อ ค่าแรง สีกันสนิม ลวดเชื่อม',
         'ใช้เป็นฐานข้อมูลราคาสำหรับอาคารหลังอื่นได้ โดยเปลี่ยนปริมาณตามโมเดลของอาคารนั้น']
title = 'ราคาวัสดุ งานโครงสร้าง — หอพัก A (จากโมเดล BIM)'
sub = f'คอนกรีต แผ่นพื้นสำเร็จรูป โครงหลังคาเหล็ก เหล็กโครงสร้างบันไดหนีไฟ · ปริมาณจาก BOQ_งานโครงสร้าง_หอพักA (commit {SHA}) · ราคาไทวัสดุ ณ 26 พ.ย. 2569'
T, TR = write_xlsx(os.path.join(OUT, 'PRICE_struct.xlsx'), title, sub, R, notes)
write_html(os.path.join(OUT, 'PRICE_struct.html'), title, sub, R, notes, T, TR)
print({k: round(v) for k, v in T.items()}, round(sum(T.values())))
for k in B:
    print(k[0][:12], k[1][:45], round(tot(k), 2), k[3])
