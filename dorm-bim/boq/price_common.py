"""ส่วนกลางสำหรับใบราคาวัสดุ (สถาปัตยกรรม / โครงสร้าง): เขียน xlsx + html (แปลงเป็น pdf ด้วย Playwright)"""
import html
from urllib.parse import quote
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill

TW = 'https://www.thaiwatsadu.com/th/product/'


def tw(sku):
    return TW + sku


def tws(q):
    return 'https://www.thaiwatsadu.com/th/search/' + quote(q)


# แถว: (หมวด, รายการ, ขนาด/สเปก, ปริมาณทั้งหมด, คงเหลือ, หน่วย, จำนวนซื้อ(ทั้งหมด), หน่วยซื้อ, ร้าน, สินค้าอ้างอิง, ราคา/หน่วยซื้อ, ลิงก์, หมายเหตุ)
HDR = ['หมวด', 'รายการ', 'ขนาด/สเปก', 'ปริมาณทั้งหมด', 'คงเหลือต้องจัดหา', 'หน่วย', 'จำนวนซื้อ (ทั้งหมด)', 'หน่วยซื้อ',
       'ร้าน', 'สินค้าอ้างอิง', 'ราคา/หน่วยซื้อ (บาท)', 'รวม ทั้งหมด (บาท)', 'รวม คงเหลือ (บาท)', 'ลิงก์', 'หมายเหตุ']


def amounts(r):
    cat, item, spec, q, rem, u, nb, bu, shop, prod, pr, link, note = r
    if pr is None:
        return None, None
    tot = pr * nb
    remv = tot * (rem / q) if q else 0
    return round(tot, 2), round(remv, 2)


def write_xlsx(path, title, sub, rows, notes):
    wb = Workbook(); ws = wb.active; ws.title = 'ราคาวัสดุ'
    ws.append([title]); ws['A1'].font = Font(bold=True, size=14)
    ws.append([sub])
    ws.append([]); ws.append(HDR)
    for c in ws[4]:
        c.font = Font(bold=True); c.fill = PatternFill('solid', fgColor='DDEBF7'); c.alignment = Alignment(wrap_text=True, vertical='top')
    T = {}; TR = {}
    for r in rows:
        tot, remv = amounts(r)
        cat = r[0]
        T[cat] = T.get(cat, 0) + (tot or 0); TR[cat] = TR.get(cat, 0) + (remv or 0)
        ws.append(list(r[:11]) + [tot, remv, r[11], r[12]])
        rr = ws.max_row
        if r[10] is None:
            for c in ws[rr]:
                c.fill = PatternFill('solid', fgColor='FCE4E4')
        if r[11]:
            ws.cell(rr, 14).hyperlink = r[11]; ws.cell(rr, 14).value = 'ลิงก์' if r[10] is not None else 'ค้นหา'
    ws.append([])
    for cat in T:
        ws.append(['', f'รวม{cat}', '', '', '', '', '', '', '', '', '', round(T[cat], 2), round(TR[cat], 2)])
        ws.cell(ws.max_row, 2).font = Font(bold=True)
    ws.append(['', 'รวมทั้งหมด (ไม่รวมแถวสีแดงที่ยังไม่มีราคา)', '', '', '', '', '', '', '', '', '', round(sum(T.values()), 2), round(sum(TR.values()), 2)])
    for c in ws[ws.max_row]:
        c.font = Font(bold=True)
    ws.append([])
    ws.append(['หมายเหตุ'])
    ws.cell(ws.max_row, 1).font = Font(bold=True)
    for i, n in enumerate(notes, 1):
        ws.append([f'{i}) {n}'])
    for col, wd in zip('ABCDEFGHIJKLMNO', (14, 40, 26, 12, 12, 8, 12, 9, 10, 46, 12, 14, 14, 8, 50)):
        ws.column_dimensions[col].width = wd
    for row in ws.iter_rows(min_row=5):
        for c in row:
            c.alignment = Alignment(wrap_text=True, vertical='top')
    wb.save(path)
    return T, TR


def write_html(path, title, sub, rows, notes, T, TR):
    E = lambda v: '' if v is None else html.escape(str(v))
    F = lambda v: '-' if v is None else f'{v:,.0f}'
    N = lambda v: f'{v:,.2f}'.rstrip('0').rstrip('.') if isinstance(v, float) else f'{v:,}'
    body = []
    for cat in T:
        body.append(f'<tr class="cat"><td colspan="12">{E(cat)}</td></tr>')
        for r in [r for r in rows if r[0] == cat]:
            tot, remv = amounts(r)
            _, item, spec, q, rem, u, nb, bu, shop, prod, pr, link, note = r
            lk = f'<a href="{E(link)}">{"ลิงก์" if pr is not None else "ค้นหา"}</a>' if link else ''
            body.append(f'<tr{" class=nf" if pr is None else ""}><td>{E(item)}</td><td>{E(spec)}</td><td class=n>{N(q)} {E(u)}</td>'
                        f'<td class=n>{N(rem)}</td><td class=n>{N(nb)} {E(bu)}</td><td>{E(shop or "ไม่พบ")}</td><td>{E(prod or "-")}</td>'
                        f'<td class=n>{F(pr)}</td><td class=n>{F(tot)}</td><td class=n>{F(remv)}</td><td>{lk}</td><td>{E(note)}</td></tr>')
        body.append(f'<tr class="sub"><td colspan="8">รวม{E(cat)}</td><td class=n>{F(T[cat])}</td><td class=n>{F(TR[cat])}</td><td colspan="2"></td></tr>')
    body.append(f'<tr class="grand"><td colspan="8">รวมทั้งหมด (ไม่รวมแถวสีแดงที่ยังไม่มีราคา)</td><td class=n>{F(sum(T.values()))}</td><td class=n>{F(sum(TR.values()))}</td><td colspan="2"></td></tr>')
    summ = ''.join(f'<tr><td>{E(c)}</td><td class=n>{F(T[c])}</td><td class=n>{F(TR[c])}</td></tr>' for c in T)
    summ += f'<tr class=grand><td>รวม</td><td class=n>{F(sum(T.values()))}</td><td class=n>{F(sum(TR.values()))}</td></tr>'
    nt = ''.join(f'<li>{E(n)}</li>' for n in notes)
    doc = f'''<!doctype html><html><head><meta charset="utf-8"><style>@page{{size:A4 landscape;margin:9mm}}body{{font-family:Loma,sans-serif;font-size:10px;color:#111}}
h1{{font-size:15px;margin:0 0 3px}}p.s{{margin:0 0 5px;color:#444}}table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #999;padding:2px 4px;vertical-align:top}}
th{{background:#ddebf7}}td.n{{text-align:right;white-space:nowrap}}tr.cat td{{background:#eef3e2;font-weight:bold}}tr.sub td{{background:#f2f2f2;font-weight:bold}}
tr.grand td{{background:#ffe699;font-weight:bold}}tr.nf td{{background:#fce4e4}}table.sm{{width:45%;margin:4px 0 8px}}tr{{page-break-inside:avoid}}ol{{margin:4px 0 0 18px;padding:0}}</style></head><body>
<h1>{E(title)}</h1><p class="s">{E(sub)}</p>
<table class=sm><tr><th>หมวด</th><th>รวมทั้งหมด (บาท)</th><th>รวมคงเหลือ (บาท)</th></tr>{summ}</table>
<table style="table-layout:fixed"><colgroup><col style="width:15%"><col style="width:9%"><col style="width:7%"><col style="width:5%"><col style="width:7%"><col style="width:5%"><col style="width:17%"><col style="width:5%"><col style="width:6%"><col style="width:6%"><col style="width:3%"><col style="width:15%"></colgroup>
<tr><th>รายการ</th><th>ขนาด/สเปก</th><th>ปริมาณทั้งหมด</th><th>คงเหลือ</th><th>จำนวนซื้อ</th><th>ร้าน</th><th>สินค้าอ้างอิง</th><th>ราคา/หน่วยซื้อ</th><th>รวมทั้งหมด</th><th>รวมคงเหลือ</th><th>ลิงก์</th><th>หมายเหตุ</th></tr>
{''.join(body)}</table><p><b>หมายเหตุ</b></p><ol>{nt}</ol></body></html>'''
    open(path, 'w').write(doc)
