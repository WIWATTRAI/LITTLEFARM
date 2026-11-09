# หอพักคนงาน 5 ชั้น อาคาร A — โมเดล BIM-4D (SketchUp)

| ไฟล์ | ใช้ทำอะไร |
|---|---|
| `model.py` | นิยามชิ้นส่วนทั้งหมด (กริด ระดับ หน้าตัด รหัสกิจกรรม ค่าสมมติ) รัน `python3 model.py` ได้ `elements.json` |
| `schedule.json` | แผนงาน Gantt อาคาร A R3 (เริ่ม 9 พ.ย. 2569) 25 รายการ อ่านจาก Google Sheet |
| `build_sketchup.rb` | สร้างโมเดลใน SketchUp: `DormBIM.build(elements, schedule)` และ `DormBIM.make_scenes(schedule)` |
| `export_glb.py` | ส่งออก GLB สำหรับหน้า Three.js (1 node ต่อชิ้นส่วน พร้อม extras ข้อมูล 4D) |

แหล่งแบบ: FOR CON (S101, S102, S910, S911), S001, S106, S107, A201, A203
พิกัด: x ตามกริด 1→10, y = 0 ที่กริด F ถึง 15.50 ที่กริด A (มุมมองด้านบนตรงกับแปลน)
ค่าที่ไม่มีในแบบอยู่ใน `ASSUMPTIONS` ของ `model.py` และชิ้นส่วนที่ใช้ค่าสมมติมี `assumed = true`
