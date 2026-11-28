import html,sys
from openpyxl import load_workbook
wb=load_workbook(sys.argv[1])
E=lambda v:'' if v is None else html.escape(str(v))
out=['<html><head><meta charset="utf-8"><style>@page{size:A4 landscape;margin:12mm}body{font-family:Loma,sans-serif;font-size:10.5px;color:#111}h1{font-size:17px;margin:0 0 4px}h2{font-size:13.5px;margin:0 0 3px}p.s{margin:0 0 6px;color:#444}section{page-break-after:always}section:last-child{page-break-after:auto}table{border-collapse:collapse;width:100%}th,td{border:1px solid #999;padding:3px 5px;vertical-align:top}th{background:#ddebf7}td.n{text-align:right}tr{page-break-inside:avoid}</style></head><body>']
out.append('<h1>รายการสุขภัณฑ์ ท่อ ข้อต่อ อุปกรณ์ และจุดยึด ห้องน้ำแต่ละแนว — หอพัก A (จากโมเดล BIM)</h1><p class="s">'+E(sys.argv[3])+'</p>')
for ws in wb.worksheets:
    rows=[r for r in ws.iter_rows(values_only=True)]
    out.append('<section>')
    hdr_i=None
    for i,r in enumerate(rows):
        if r and r[0] in ('หมวด','ชนิดจุดยึด'): hdr_i=i;break
    title=rows[0][0] if rows and rows[0] else ws.title
    out.append(f'<h2>{E(ws.title)} : {E(title)}</h2>' if ws.title not in ('หมายเหตุ',) else '<h2>หมายเหตุ</h2>')
    if hdr_i is None:
        for r in rows[1:]:
            if r and r[0]: out.append(f'<p>{E(r[0])}</p>')
    else:
        for r in rows[1:hdr_i]:
            if r and r[0]: out.append(f'<p class="s">{E(r[0])}</p>')
        h=[c for c in rows[hdr_i]]
        n=len([c for c in h if c is not None])
        out.append('<table><tr>'+''.join(f'<th>{E(c)}</th>' for c in h[:n])+'</tr>')
        for r in rows[hdr_i+1:]:
            if not any(r): continue
            out.append('<tr>'+''.join(f'<td class="{"n" if isinstance(c,(int,float)) else ""}">{E(c)}</td>' for c in r[:n])+'</tr>')
        out.append('</table>')
    out.append('</section>')
out.append('</body></html>')
open(sys.argv[2]+'.html','w').write(''.join(out))
