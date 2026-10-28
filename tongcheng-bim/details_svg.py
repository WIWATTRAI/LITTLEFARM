# -*- coding: utf-8 -*-
"""แบบขยายรอยต่อเสาเหล็ก–หัวเสา คสล. (SVG) สร้างจากค่าใน model.BP ใช้สีจาก CSS variables ของหน้า viewer"""
import model as M

INK, MUTED, ACC, STEEL, CONC = "var(--ink)", "var(--ink-2)", "var(--accent)", "var(--steel)", "var(--rule)"


def _dim(x1, y1, x2, y2, txt, off=0, vertical=False):
    if vertical:
        x = x1 + off
        return (f'<line x1="{x}" y1="{y1}" x2="{x}" y2="{y2}" stroke="{MUTED}" stroke-width="0.8"/>'
                f'<line x1="{x-4}" y1="{y1}" x2="{x+4}" y2="{y1}" stroke="{MUTED}"/><line x1="{x-4}" y1="{y2}" x2="{x+4}" y2="{y2}" stroke="{MUTED}"/>'
                f'<text x="{x-6}" y="{(y1+y2)/2}" font-size="11" fill="{INK}" text-anchor="end" dominant-baseline="middle">{txt}</text>')
    y = y1 + off
    return (f'<line x1="{x1}" y1="{y}" x2="{x2}" y2="{y}" stroke="{MUTED}" stroke-width="0.8"/>'
            f'<line x1="{x1}" y1="{y-4}" x2="{x1}" y2="{y+4}" stroke="{MUTED}"/><line x1="{x2}" y1="{y-4}" x2="{x2}" y2="{y+4}" stroke="{MUTED}"/>'
            f'<text x="{(x1+x2)/2}" y="{y-5}" font-size="11" fill="{INK}" text-anchor="middle">{txt}</text>')


def baseplate_svg():
    bp = M.BP
    s = 0.62                      # px per mm (plan)
    W, H = 980, 560
    out = [f'<svg viewBox="0 0 {W} {H}" width="{W}" role="img" aria-label="แบบขยายรอยต่อเสาเหล็กกับหัวเสา คสล.">']
    # ---------------- plan: RC 500 (horizontal) x 300 (vertical), plate 450 x 200
    ox, oy = 60, 120
    cw, ch = 500*s, 300*s
    out.append(f'<text x="{ox}" y="40" font-size="14" font-weight="600" fill="{INK}">แปลนหัวเสา คสล. C1 0.30x0.50 + แผ่นเหล็กฐาน</text>')
    out.append(f'<text x="{ox}" y="58" font-size="11" fill="{MUTED}">มาตราส่วนโดยประมาณ 1:8 · หน่วย มม.</text>')
    out.append(f'<rect x="{ox}" y="{oy}" width="{cw}" height="{ch}" fill="{CONC}" fill-opacity="0.45" stroke="{INK}" stroke-width="1.4"/>')
    px, py = ox + (500-450)/2*s, oy + (300-200)/2*s
    out.append(f'<rect x="{px}" y="{py}" width="{450*s}" height="{200*s}" fill="none" stroke="{STEEL}" stroke-width="2"/>')
    # H244x175 outline (web along long side)
    cx, cy = ox + cw/2, oy + ch/2
    d, bf, tw, tf = 244*s, 175*s, 7*s, 11*s
    out.append(f'<path d="M{cx-d/2},{cy-bf/2} h{tf} v{bf} h{-tf} z M{cx+d/2-tf},{cy-bf/2} h{tf} v{bf} h{-tf} z M{cx-d/2+tf},{cy-tw/2} h{d-2*tf} v{tw} h{-(d-2*tf)} z" fill="{STEEL}" fill-opacity="0.55" stroke="{STEEL}"/>')
    for (u, v) in bp["bolts"]:
        out.append(f'<circle cx="{cx+u*1000*s}" cy="{cy+v*1000*s}" r="{11*s}" fill="none" stroke="{ACC}" stroke-width="1.6"/>'
                   f'<circle cx="{cx+u*1000*s}" cy="{cy+v*1000*s}" r="{10*s*0.45}" fill="{ACC}"/>')
    # assumed corner bars (dashed) cover 40 + tie 9 + bar 16/2
    off = 40 + 9 + 8
    for sx in (-1, 1):
        for sy in (-1, 1):
            out.append(f'<circle cx="{cx+sx*(250-off)*s}" cy="{cy+sy*(150-off)*s}" r="{8*s}" fill="none" stroke="{MUTED}" stroke-dasharray="2 2"/>')
    out.append(_dim(ox, oy, ox+cw, oy, "500", off=-22))
    out.append(_dim(px, oy+ch, px+450*s, oy+ch, "450 (แผ่นเหล็ก)", off=26))
    out.append(_dim(ox, oy, ox, oy+ch, "300", off=-14, vertical=True))
    out.append(_dim(px+450*s, py, px+450*s, py+200*s, "", off=18, vertical=True))
    out.append(f'<text x="{px+450*s+24}" y="{py+100*s}" font-size="11" fill="{INK}" dominant-baseline="middle">200</text>')
    out.append(_dim(cx-175*s, oy+ch, cx, oy+ch, "175", off=50))
    out.append(_dim(cx, oy+ch, cx+175*s, oy+ch, "175", off=50))
    lx = ox
    for i, t in enumerate(["แผ่นเหล็กฐาน PL 20x200x450 มม. 46 แผ่น (14.13 กก./แผ่น)",
                           "Anchor bolt M20 ยาว 750 มม. 6 ชุด/เสา = 276 ชุด (ระยะสลักสมมติ 175 x 100 มม.)",
                           "เสาเหล็ก H244x175x7x11 (44.1 กก./ม.) แกนลึกตามด้านยาวเสา คสล.",
                           "วงประ = เหล็กยืนมุมเสาสมมติ DB16 ระยะหุ้ม 40 ปลอก RB9 (รอตารางเสา)"]):
        out.append(f'<text x="{lx}" y="{oy+ch+100+i*17}" font-size="11.5" fill="{INK if i < 3 else MUTED}">{t}</text>')
    # ---------------- section: from +3.70 to +4.75 (exaggerated), and top plate note
    s2 = 0.30
    ex, ey0 = 600, 90
    def Y(z): return ey0 + (4.75 - z)*1000*s2
    out.append(f'<text x="{ex}" y="40" font-size="14" font-weight="600" fill="{INK}">รูปตัดรอยต่อที่ระดับ +4.50</text>')
    colw = 500*s2
    out.append(f'<rect x="{ex}" y="{Y(4.50)}" width="{colw}" height="{Y(3.70)-Y(4.50)}" fill="{CONC}" fill-opacity="0.45" stroke="{INK}" stroke-width="1.4"/>')
    gz, pz, cz = 4.50 + bp["grout"], 4.50 + bp["grout"] + bp["t"], 4.75
    out.append(f'<rect x="{ex+(500-450)/2*s2-6}" y="{Y(gz)}" width="{450*s2+12}" height="{Y(4.50)-Y(gz)}" fill="{MUTED}" fill-opacity="0.35"/>')
    out.append(f'<rect x="{ex+(500-450)/2*s2}" y="{Y(pz)}" width="{450*s2}" height="{Y(gz)-Y(pz)}" fill="{STEEL}"/>')
    out.append(f'<rect x="{ex+(500-244)/2*s2}" y="{Y(cz)}" width="{244*s2}" height="{Y(pz)-Y(cz)}" fill="{STEEL}" fill-opacity="0.35" stroke="{STEEL}"/>')
    for u in (-0.175, 0.0, 0.175):
        bx = ex + colw/2 + u*1000*s2
        top = pz + bp["bolt_proj"] - bp["t"]
        out.append(f'<line x1="{bx}" y1="{Y(top)}" x2="{bx}" y2="{Y(top - bp["bolt_L"])}" stroke="{ACC}" stroke-width="2.2"/>'
                   f'<rect x="{bx-5}" y="{Y(pz)-6}" width="10" height="5" fill="{ACC}"/><line x1="{bx}" y1="{Y(top-bp["bolt_L"])}" x2="{bx+10}" y2="{Y(top-bp["bolt_L"])}" stroke="{ACC}" stroke-width="2.2"/>')
    R = ex + colw + 16
    for z, t, dy in [(pz, "แผ่นเหล็กฐาน 20 มม. (+4.545)", -22), (gz, "ปูนเกราท์ไม่หดตัว 25 มม.", 0), (4.50, "หัวเสา คสล. +4.50", 22),
                     (pz + bp["bolt_proj"] - bp["t"] - bp["bolt_L"], "ปลายสลักงอ (ฝังในคอนกรีต 645 มม.)", 0)]:
        out.append(f'<polyline points="{ex+colw},{Y(z)} {R},{Y(z)} {R+10},{Y(z)+dy}" fill="none" stroke="{MUTED}" stroke-dasharray="3 3"/>'
                   f'<text x="{R+14}" y="{Y(z)+dy}" font-size="11" fill="{INK}" dominant-baseline="middle">{t}</text>')
    out.append(_dim(ex - 10, Y(pz + bp["bolt_proj"] - bp["t"]), ex - 10, Y(pz + bp["bolt_proj"] - bp["t"] - bp["bolt_L"]), "750", vertical=True))
    for i, t in enumerate(["แผ่นเหล็กหัวเสา (Top plate) PL 20x200x450 มม.", "ที่ระดับ +9.00 ขนาดเดียวกัน 46 แผ่น",
                           "การต่อกับโครงถักรอแบบโครงหลังคา", "สลักคู่กลางอยู่ระหว่างปีกเสา H ชิดเอว: ตรวจที่ขันน็อต"]):
        out.append(f'<text x="{ex}" y="{Y(3.70)+22+i*16}" font-size="11.5" fill="{INK if i < 2 else MUTED}">{t}</text>')
    out.append('</svg>')
    return "".join(out)


if __name__ == "__main__":
    open("out/D01_รอยต่อเสาเหล็ก_baseplate.svg", "w", encoding="utf-8").write(
        baseplate_svg().replace("var(--ink-2)", "#4b5b5f").replace("var(--ink)", "#15262b").replace("var(--accent)", "#d9861c")
        .replace("var(--steel)", "#2f5d73").replace("var(--rule)", "#c9cfcb").replace('<svg ', '<svg xmlns="http://www.w3.org/2000/svg" style="background:#fff" ', 1))
    print("ok")
