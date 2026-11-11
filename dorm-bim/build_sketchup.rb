# หอพักคนงาน 5 ชั้น อาคาร A — สร้างโมเดลใน SketchUp จาก elements.json + schedule.json
# ใช้: โหลดไฟล์นี้ใน SketchUp แล้วเรียก DormBIM.build(elements_hash, schedule_hash)
require 'json'
require 'date'

module DormBIM
  DICT = 'BIM4D'.freeze
  CAT_COLORS = {
    'คานคอดิน' => [120, 120, 120], 'เสา' => [204, 89, 77], 'คาน' => [89, 140, 102],
    'พื้น' => [205, 205, 200], 'พื้นสำเร็จรูป' => [140, 178, 217], 'พื้นทับหน้า' => [230, 217, 140], 'เสาเอ็นคานเอ็น' => [140, 140, 140], 'บันได' => [180, 170, 160], 'โครงหลังคาเหล็ก' => [150, 48, 36],
    'หลังคา' => [120, 60, 45], 'ราวบันได' => [25, 25, 25], 'ไฟฟ้า' => [245, 245, 240], 'ผนัง' => [204, 158, 128],
    'งานฉาบ' => [237, 235, 225], 'ประตูหน้าต่าง' => [115, 77, 51], 'กระเบื้อง' => [217, 204, 178], 'สุขภัณฑ์' => [248, 248, 248]
  }.freeze
  # หมวดงานสำหรับกรอง Tag: ST = โครงสร้าง, AR = สถาปัตย์
  STRUCT_CATS = ['คานคอดิน', 'เสา', 'คาน', 'พื้น', 'พื้นสำเร็จรูป', 'พื้นทับหน้า', 'บันได', 'โครงหลังคาเหล็ก'].freeze
  # ชิ้นส่วนที่ขึ้นด้วย Profile Builder 3
  PB_CATS = ['เสา', 'คาน', 'คานคอดิน'].freeze

  def self.discipline(cat)
    STRUCT_CATS.include?(cat) ? ['ST', 'งานโครงสร้าง'] : ['AR', 'งานสถาปัตย์']
  end

  def self.pb_api
    defined?(DM::ProfileBuilder3::PBAPI) ? DM::ProfileBuilder3::PBAPI : nil
  end

  # สร้างชิ้นส่วนด้วย Profile Builder 3: เสา (prism สี่เหลี่ยม) และคาน (member) คืน instance ของ PB
  def self.pb_member(ents, e, mat_name, cache)
    api = pb_api
    geo = e['geom']
    if geo['type'] == 'prism'
      xs = geo['poly'].map { |a| a[0] }; ys = geo['poly'].map { |a| a[1] }
      w = xs.max - xs.min; d = ys.max - ys.min
      cx = (xs.max + xs.min) / 2.0; cy = (ys.max + ys.min) / 2.0
      p0 = [cx, cy, geo['z0']]; p1 = [cx, cy, geo['z0'] + geo['t']]
    else
      w = geo['w']; d = geo['d']; p0 = geo['p0']; p1 = geo['p1']
    end
    pname = format('%s %dx%d', e['category'], (w * 1000).round, (d * 1000).round)
    prof = (cache[pname] ||= api::Profile.rectangle(w.m, d.m, pname))
    chain = api::Chain.new([pt(p0), pt(p1)])
    pm = api::ProfileMember.add(ents, chain)
    pm.profile = prof
    pm.material_name = mat_name
    pm.draw
    pm.instance
  end


  # ---------- Profile Builder: เหล็กรูปตัวซี / ชิ้นแนวเส้นที่ต้องตัดปลาย (ผู้ใช้สั่ง 11 พ.ย. 2569) ----------
  # หน้าตัด C จากหน้า (face) เพื่อให้ได้ profile 2 มิติ (ตัน); mirror = ปากหันไปทาง -a
  def self.pb_c_profile(model, sec, mirror, cache)
    key = format('C%dx%dx%dx%.1f%s', sec['h'] * 1000, sec['b'] * 1000, sec['c'] * 1000, sec['t'] * 1000, mirror ? 'M' : '')
    cache[key] ||= begin
      tmp = model.entities.add_group
      pts = c_section(sec, 0, mirror).map { |a, b| Geom::Point3d.new(a.m, b.m, 0) }
      f = tmp.entities.add_face(pts)
      prof = pb_api::Profile.new(f, "เหล็กรูปตัวซี #{key}")
      tmp.erase!
      prof
    end
  end

  def self.pb_plane(c)
    [Geom::Point3d.new(c[0].m, c[1].m, c[2].m), Geom::Vector3d.new(c[3], c[4], c[5])]
  end

  # สร้าง PB member หนึ่งเส้น (profile, x_offset) แล้วตัดปลายตามระนาบ trim
  def self.pb_line(ents, m, prof, xoff, mat_name)
    api = pb_api
    pm = api::ProfileMember.add(ents, api::Chain.new([pt(m['p0']), pt(m['p1'])]))
    pm.profile = prof
    pm.x_offset = xoff.m if xoff != 0
    pm.material_name = mat_name
    pm.draw
    (m['trim'] || []).each_with_index { |c, i| pm.trim_to_plane(pb_plane(c), i) if c }
    pm.instance
  end

  # ชิ้นส่วน member (หรือ multi ของ member) ที่ geom มี shape C/2C หรือ pb=true: ใส่ PB ทุกชิ้นในกลุ่มของ element
  def self.pb_shape_group(ents, e, mat_name, cache)
    model = Sketchup.active_model
    before = ents.to_a
    g = ents.add_group
    geo = e['geom']
    (geo['type'] == 'multi' ? geo['parts'] : [geo]).each do |m|
      if m['shape'] == '2C'
        b = m['sec']['b']
        pb_line(g.entities, m, pb_c_profile(model, m['sec'], false, cache), -b / 2.0, mat_name)
        pb_line(g.entities, m, pb_c_profile(model, m['sec'], true, cache), b / 2.0, mat_name)
      elsif m['shape'] == 'POLY'
        key = 'POLY ' + m['poly2d'].to_s
        prof = (cache[key] ||= begin
          tmp = model.entities.add_group
          f = tmp.entities.add_face(m['poly2d'].map { |a, b| Geom::Point3d.new(a.m, b.m, 0) })
          pr = pb_api::Profile.new(f, "#{e['category']} #{(m['w'] * 1000).round}x#{(m['d'] * 1000).round}")
          tmp.erase!
          pr
        end)
        pb_line(g.entities, m, prof, 0, mat_name)
      elsif m['shape'] == 'C'
        pb_line(g.entities, m, pb_c_profile(model, m['sec'], false, cache), 0, mat_name)
      else
        pname = format('%s %dx%d', e['category'], (m['w'] * 1000).round, (m['d'] * 1000).round)
        prof = (cache[pname] ||= pb_api::Profile.rectangle(m['w'].m, m['d'].m, pname))
        pb_line(g.entities, m, prof, 0, mat_name)
      end
    end
    # trim_to_plane ของ PB ทิ้งเศษที่ตัดออกเป็นกลุ่มชื่อหน้าตัดไว้ในกลุ่มแม่: ลบทิ้ง (ไม่ใช่ชิ้นงาน)
    (ents.to_a - before - [g]).each { |x| x.erase! if x.valid? && x.is_a?(Sketchup::Group) && x.get_attribute(DICT, 'id').nil? }
    g
  end

  def self.pb_shape?(geo)
    ms = geo['type'] == 'multi' ? geo['parts'] : [geo]
    ms.all? { |m| m['type'] == 'member' && (%w[C 2C POLY].include?(m['shape']) || m['pb']) }
  end

  def self.pt(a)
    Geom::Point3d.new(a[0].m, a[1].m, a[2].m)
  end

  # รูปตัด C ขอบพับ (lipped channel) ในพิกัดหน้าตัด (a ตามความกว้าง, b ตามความลึก) เปิดปากไปทาง +a
  def self.c_section(sec, shift, mirror)
    h = sec['h']; b = sec['b']; c = sec['c']; t = sec['t']
    pts = [[0, -h / 2], [b, -h / 2], [b, -h / 2 + c], [b - t, -h / 2 + c], [b - t, -h / 2 + t], [t, -h / 2 + t],
           [t, h / 2 - t], [b - t, h / 2 - t], [b - t, h / 2 - c], [b, h / 2 - c], [b, h / 2], [0, h / 2]]
    pts.map { |a, bb| [(mirror ? -a : a) + shift, bb] }
  end

  # C เดี่ยว: แกนกลางหน้าตัดอยู่บนเส้น, 2C: ประกบปากชนกันเป็นกล่อง กว้าง 2b
  def self.c_loops(g)
    sec = g['sec']
    if g['shape'] == 'O'          # เหล็กกลม: รูปหลายเหลี่ยม 16 ด้าน (ตรงกับ export_glb)
      r = sec['d'] / 2.0
      return [(0...16).map { |i| a = 2 * Math::PI * i / 16; [r * Math.cos(a), r * Math.sin(a)] }]
    end
    b = sec['b']
    if g['shape'] == '2C'
      [c_section(sec, -b, false), c_section(sec, b, true)]
    else
      [c_section(sec, -b / 2.0, false)]
    end
  end

  def self.member_frame(g)
    p0 = pt(g['p0']); p1 = pt(g['p1'])
    u = p1 - p0
    return nil if u.length < 0.001
    len = u.length
    u.normalize!
    z = Geom::Vector3d.new(0, 0, 1)
    s = u.parallel?(z) ? Geom::Vector3d.new(1, 0, 0) : u * z
    s.normalize!
    t = s * u
    t.normalize!
    [p0, u, s, t, len]
  end

  def self.shape_member(ents, g)
    fr = member_frame(g)
    return unless fr
    p0, u, s, t, len = fr
    c_loops(g).each do |loop|
      sg = ents.add_group
      pts = loop.map { |a, bb| p0.offset(s, a.m).offset(t, bb.m) }
      f = sg.entities.add_face(pts)
      f.reverse! if f.normal.dot(u) < 0
      f.pushpull(len)
    end
  end

  # กล่องตันหนึ่งชิ้น (กลุ่มย่อย) ช่วง [x0,x1]x[y0,y1]x[z0,z1] หน่วยเมตร
  def self.solid_box(ents, x0, y0, z0, x1, y1, z1, mat)
    g = ents.add_group
    f = g.entities.add_face([[x0.m, y0.m, z0.m], [x1.m, y0.m, z0.m], [x1.m, y1.m, z0.m], [x0.m, y1.m, z0.m]])
    f.reverse! if f.normal.z < 0             # หันขึ้น แล้วดันขึ้นจาก z0 ถึง z1
    f.pushpull((z1 - z0).m)
    g.material = mat
    g
  end

  # คอมโพเนนต์ประตูบานเลื่อนอะลูมิเนียม 2 บาน: วงกบเต็มช่อง w x h ลึก d (แกน y กึ่งกลางที่ 0), บานวิ่งบน 2 ราง
  def self.sliding_door_def(model, name, sp)
    cdef = model.definitions[name]
    return cdef if cdef
    w, h, d = sp['w'], sp['h'], sp['d']
    ft, sl, st, ov = sp['frame'], sp['sill'], sp['sash_t'], sp['overlap']
    al = model.materials['อะลูมิเนียม'] || model.materials.add('อะลูมิเนียม').tap { |m| m.color = Sketchup::Color.new(190, 192, 195) }
    gl = model.materials['กระจกใส'] || model.materials.add('กระจกใส').tap { |m| m.color = Sketchup::Color.new(170, 205, 220); m.alpha = 0.35 }
    cdef = model.definitions.add(name)
    e = cdef.entities
    hd = d / 2.0
    solid_box(e, 0, -hd, 0, ft, hd, h, al)                 # วงกบตั้งซ้าย
    solid_box(e, w - ft, -hd, 0, w, hd, h, al)             # วงกบตั้งขวา
    solid_box(e, ft, -hd, h - ft, w - ft, hd, h, al)       # วงกบบน
    solid_box(e, ft, -hd, 0, w - ft, hd, sl, al)           # ธรณี/รางล่าง
    ws = (w - 2 * ft + ov) / 2.0                           # ความกว้างบาน
    z0, z1 = sl, h - ft
    sf = 0.05                                              # หน้ากรอบบาน
    [[ft, -st / 2.0 - 0.003], [w - ft - ws, st / 2.0 + 0.003]].each do |x0, yc|
      y0, y1 = yc - st / 2.0, yc + st / 2.0
      x1 = x0 + ws
      solid_box(e, x0, y0, z0, x0 + sf, y1, z1, al)
      solid_box(e, x1 - sf, y0, z0, x1, y1, z1, al)
      solid_box(e, x0 + sf, y0, z0, x1 - sf, y1, z0 + sf * 1.6, al)
      solid_box(e, x0 + sf, y0, z1 - sf, x1 - sf, y1, z1, al)
      solid_box(e, x0 + sf, yc - 0.003, z0 + sf * 1.6, x1 - sf, yc + 0.003, z1 - sf, gl)
    end
    cdef.set_attribute(DICT, 'spec', sp.to_a.flatten.join(' '))
    cdef
  end

  def self.box_member(ents, g)
    return shape_member(ents, g) if g['shape']
    p0 = pt(g['p0']); p1 = pt(g['p1'])
    u = p1 - p0
    len = u.length
    return if len < 0.001
    u.normalize!
    z = Geom::Vector3d.new(0, 0, 1)
    s = u.parallel?(z) ? Geom::Vector3d.new(1, 0, 0) : u * z
    s.normalize!
    t = s * u
    t.normalize!
    hw = g['w'].m / 2.0; hd = g['d'].m / 2.0
    c = [p0.offset(s, hw).offset(t, hd), p0.offset(s, -hw).offset(t, hd),
         p0.offset(s, -hw).offset(t, -hd), p0.offset(s, hw).offset(t, -hd)]
    f = ents.add_face(c)
    f.reverse! if f.normal.dot(u) < 0
    f.pushpull(len)
  end

  def self.prism(ents, g)
    z0 = g['z0'].m
    pts = g['poly'].map { |x, y| Geom::Point3d.new(x.m, y.m, z0) }
    f = ents.add_face(pts)
    (g['holes'] || []).each do |h|
      hf = ents.add_face(h.map { |x, y| Geom::Point3d.new(x.m, y.m, z0) })
      hf.erase! if hf && hf.valid?
    end
    f = ents.grep(Sketchup::Face).max_by(&:area)
    f.reverse! if f.normal.z < 0
    f.pushpull(g['t'].m)
  end

  def self.plate(ents, g)
    pts = g['pts'].map { |a| pt(a) }
    f = ents.add_face(pts)
    f.reverse! if f.normal.z > 0
    f.pushpull(g['t'].m)
  end

  # ชิ้นตันจากรูปตัดในระนาบ y-z ยืดตามแกน x เป็น ComponentInstance (ใช้ definition ร่วมเมื่อรูปร่างเหมือนกัน)
  def self.xprofile_instance(ents, geo, cache)
    y0, z0 = geo['poly'][0]
    rel = geo['poly'].map { |y, z| [(y - y0).round(4), (z - z0).round(4)] }
    w = (geo['x1'] - geo['x0']).round(4)
    key = [rel, w]
    defn = cache[key]
    unless defn
      model = Sketchup.active_model
      name = "#{geo['component'] || 'xprofile'} ##{cache.size + 1}"
      defn = model.definitions.add(name)
      f = defn.entities.add_face(rel.map { |y, z| Geom::Point3d.new(0, y.m, z.m) })
      f.reverse! if f.normal.x < 0
      f.pushpull(w.m)
      cache[key] = defn
    end
    ents.add_instance(defn, Geom::Transformation.new(Geom::Point3d.new(geo['x0'].m, y0.m, z0.m)))
  end

  # ผิวกระเบื้องที่มี texture (เช่น Tara เจด้าไวท์ 60x60 ยาแนว 3 มม.): จัดร่องยาแนวให้ตรง origin ทุก pitch บนหน้าบน
  # ต้องมี material ชื่อนี้ในโมเดลก่อน (ภาพ texture ขนาด 1 ช่อง = pitch); ถ้าไม่มีจะข้าม
  def self.apply_finish(model, g, fin)
    m = model.materials[fin['material']]
    return unless m && m.texture
    ox, oy = fin['origin']; p = fin['pitch']
    g.entities.grep(Sketchup::Face).each do |f|
      next unless f.normal.z > 0.99
      z = f.vertices.first.position.z
      pts = [Geom::Point3d.new(ox.m, oy.m, z), Geom::Point3d.new(0, 0, 0),
             Geom::Point3d.new((ox + p).m, oy.m, z), Geom::Point3d.new(1, 0, 0),
             Geom::Point3d.new(ox.m, (oy + p).m, z), Geom::Point3d.new(0, 1, 0)]
      f.position_material(m, pts, true)
    end
  end

  # วัสดุเฉพาะชิ้น (e['material']) เช่น แปกัลวาไนซ์; ถ้ายังไม่มีในโมเดลสร้างเป็นสีล้วน (texture ใส่ในโมเดลภายหลัง)
  NAMED_COLORS = { 'BIM-แปกัลวาไนซ์' => [178, 182, 186],
                   # สีคานตามเบอร์คาน (ผู้ใช้เลือก 11 พ.ย. 2569)
                   'BIM-คาน-B1' => [40, 100, 200], 'BIM-คาน-B2' => [60, 160, 80], 'BIM-คาน-B3' => [240, 140, 30],
                   'BIM-คาน-B4' => [140, 70, 180], 'BIM-คาน-B5' => [235, 205, 40], 'BIM-คาน-BST1' => [40, 190, 200],
                   'BIM-คาน-BST2' => [230, 90, 170], 'BIM-คาน-BST3' => [130, 85, 50],
                   # คอนกรีตเททับหน้า + พื้นหล่อในที่ ชนิดเดียวกัน (ผู้ใช้สั่ง 11 พ.ย. 2569)
                   'BIM-คอนกรีตเทพื้น' => [196, 192, 182], 'BIM-เชิงชายสีซีเมนต์' => [168, 168, 163], 'BIM-กระเบื้องบันได' => [236, 234, 228], 'BIM-จมูกบันไดเทาเข้ม' => [70, 72, 74],
                   'BIM-เหล็กโครงสร้าง' => [28, 78, 168], 'BIM-สลักเหล็ก' => [120, 120, 125] }.freeze
  def self.named_material(model, name)
    model.materials[name] || model.materials.add(name).tap { |m| m.color = Sketchup::Color.new(*(NAMED_COLORS[name] || [200, 200, 200])) }
  end

  def self.material(model, cat)
    name = "BIM-#{cat}"
    m = model.materials[name]
    unless m
      m = model.materials.add(name)
      m.color = Sketchup::Color.new(*(CAT_COLORS[cat] || [200, 200, 200]))
    end
    m
  end

  def self.tag(model, name, folder = nil)
    l = model.layers[name] || model.layers.add(name)
    if folder && l.respond_to?(:folder=) && l.folder != folder
      l.folder = folder
    end
    l
  end

  def self.folder(model, name)
    return nil unless model.layers.respond_to?(:add_folder)
    model.layers.folders.find { |f| f.name == name } || model.layers.add_folder(name)
  end

  def self.task_tag_name(task_id, tasks)
    return '4D-DONE เสร็จก่อน 9 พ.ย. 2569' if task_id == 'DONE'
    t = tasks[task_id]
    t ? "4D-#{task_id} #{t['name']}"[0, 80] : "4D-#{task_id}"
  end

  # elements: hash จาก elements.json, schedule: hash จาก schedule.json
  # filter: lambda รับ element hash คืน true เพื่อสร้างเฉพาะบางส่วน (ส่งทีละชุดเพื่อไม่ให้ SketchUp ค้าง)
  def self.build(elements, schedule, filter = nil)
    model = Sketchup.active_model
    model.start_operation('สร้างโมเดลหอพัก A BIM-4D', true, false, false)
    tasks = {}
    schedule['tasks'].each { |t| tasks[t['id']] = t }
    f_cat = folder(model, 'หมวดงาน')
    f_disc = {}
    if f_cat
      ['งานโครงสร้าง', 'งานสถาปัตย์'].each do |n|
        f_disc[n] = f_cat.folders.find { |f| f.name == n } || f_cat.add_folder(n)
      end
    end
    use_pb = !pb_api.nil?
    pb_cache = {}
    comp_cache = {}
    f_4d = folder(model, '4D กิจกรรม')
    root = model.entities.grep(Sketchup::Group).find { |g| g.name == 'หอพัก A' }
    unless root
      root = model.entities.add_group
      root.name = 'หอพัก A'
    end
    groups = {}
    root.entities.grep(Sketchup::Group).each { |cg| groups[cg.get_attribute(DICT, 'key')] = cg }
    count = 0
    elements['elements'].each do |e|
      next if filter && !filter.call(e)
      key = "#{e['category']}|#{e['floor']}"
      cg = groups[key]
      unless cg
        cg = root.entities.add_group
        cg.name = "#{e['category']} ชั้น #{e['floor']}"
        code, dname = discipline(e['category'])
        cg.layer = tag(model, "#{code}-#{e['category']}", f_disc[dname] || f_cat)
        cg.set_attribute(DICT, 'key', key)
        groups[key] = cg
      end
      geo = e['geom']
      mat = e['material'] ? named_material(model, e['material']) : material(model, e['category'])
      by_pbs = use_pb && pb_shape?(geo)
      by_pb = by_pbs || (use_pb && PB_CATS.include?(e['category']))
      by_comp = geo['type'] == 'xprofile'
      g = if by_pbs
            pb_shape_group(cg.entities, e, mat.name, pb_cache)
          elsif by_pb
            pb_member(cg.entities, e, mat.name, pb_cache)
          elsif by_comp
            xprofile_instance(cg.entities, geo, comp_cache)
          else
            cg.entities.add_group
          end
      g.name = e['id']
      # บานประตู: ใช้คอมโพเนนต์ที่ผู้ใช้ใส่ในโมเดล (เช่น door2.dxf) ถ้ามี แทนแผ่นตัวแทน
      sliding_door_def(model, e['component'], e['component_spec']) if e['component_spec']
      cdef = e['component'] && model.definitions[e['component']]
      if cdef && geo['type'] == 'prism'
        xs = geo['poly'].map { |p| p[0] }
        ys = geo['poly'].map { |p| p[1] }
        db = cdef.bounds
        yc = (ys.min + ys.max) / 2.0
        t = if e['component_fit'] == 'opening'
              # ย่อ/ขยายให้พอดีช่องเปิด (กว้าง x สูง) วางกึ่งกลางความหนาผนัง
              sx = (xs.max - xs.min).m / db.width
              sz = geo['t'].m / db.depth
              Geom::Transformation.translation([xs.min.m - db.min.x * sx, yc.m - (db.min.y + db.max.y) / 2.0, geo['z0'].m - db.min.z * sz]) *
                Geom::Transformation.scaling(ORIGIN, sx, 1, sz)
            elsif (mt = e['component_mount'])
              # ประตูม้วน: กึ่งกลางช่อง, ด้านราง (local y max) ที่ back_y, กล่องยื่นไปทาง box_dir (-1 = y น้อย, +1 = y มาก), ขอบล่างที่พื้น
              cxm = (xs.min + xs.max).m / 2.0
              if mt['box_dir'].to_i > 0
                Geom::Transformation.translation([cxm + (db.min.x + db.max.x) / 2.0, mt['back_y'].m + db.max.y, geo['z0'].m]) *
                  Geom::Transformation.rotation(ORIGIN, Z_AXIS, Math::PI)
              else
                Geom::Transformation.translation([cxm - (db.min.x + db.max.x) / 2.0, mt['back_y'].m - db.max.y, geo['z0'].m])
              end
            else
              Geom::Transformation.translation([xs.min.m, yc.m - (db.min.y + db.max.y) / 2.0, geo['z0'].m])
            end
        g.entities.add_instance(cdef, t)
        geo = { 'type' => 'component' }
      end
      case (by_pb || by_comp ? nil : geo['type'])
      when 'member' then box_member(g.entities, geo)
      when 'prism' then prism(g.entities, geo)
      when 'plate' then plate(g.entities, geo)
      when 'multi'
        geo['parts'].each do |pp|
          sg = g.entities.add_group
          case pp['type']
          when 'member' then box_member(sg.entities, pp)
          when 'prism' then prism(sg.entities, pp)
          when 'plate' then plate(sg.entities, pp)
          end
        end
      end
      g.material = mat
      apply_finish(model, g, e['finish']) if e['finish']
      g.layer = tag(model, task_tag_name(e['task'], tasks), f_4d)
      t = tasks[e['task']]
      g.set_attribute(DICT, 'id', e['id'])
      g.set_attribute(DICT, 'name', e['name'])
      g.set_attribute(DICT, 'category', e['category'])
      g.set_attribute(DICT, 'discipline', discipline(e['category'])[1])
      g.set_attribute(DICT, 'tool', by_pb ? 'Profile Builder 3' : (by_comp ? 'Component' : (cdef ? e['component'] : 'Ruby')))
      g.set_attribute(DICT, 'floor', e['floor'])
      g.set_attribute(DICT, 'task_id', e['task'])
      g.set_attribute(DICT, 'task_name', t ? t['name'] : 'งานโครงสร้างเสร็จก่อนแผน R3')
      g.set_attribute(DICT, 'planned_start', t ? t['start'].to_s : '')
      g.set_attribute(DICT, 'planned_finish', t ? t['finish'].to_s : '')
      g.set_attribute(DICT, 'status', t ? t['status'].to_s : 'แล้วเสร็จ')
      g.set_attribute(DICT, 'assumed', e['assumed'] ? 'ค่าสมมติ' : 'ตามแบบ')
      (e['qty'] || {}).each { |k, v| g.set_attribute(DICT, "qty_#{k}", v) }
      count += 1
    end
    model.commit_operation
    count
  end

  # Scene ต่อสัปดาห์: แสดงงานที่เริ่มแล้ว ณ วันสิ้นสุดสัปดาห์นั้น
  def self.make_scenes(schedule, first = '2026-11-09', last = '2027-05-09')
    model = Sketchup.active_model
    model.start_operation('สร้าง Scene 4D', true)
    tasks = schedule['tasks'].select { |t| t['start'] }
    # ไม่ลบ scene เดิม (การลบ scene ทำให้ SketchUp บนเครื่องผู้ใช้ค้าง) ใช้วิธีอัปเดต scene ชื่อเดิม
    upsert = lambda do |name|
      pg = model.pages[name]
      if pg
        pg.update
        pg
      else
        model.pages.add(name)
      end
    end
    layers_for = lambda do |date|
      vis = ['4D-DONE เสร็จก่อน 9 พ.ย. 2569']
      tasks.each { |t| vis << task_tag_name(t['id'], schedule['tasks'].map { |x| [x['id'], x] }.to_h) if Date.parse(t['start']) <= date }
      vis
    end
    all4d = model.layers.select { |l| l.name.start_with?('4D-') }
    d = Date.parse(first)
    stop = Date.parse(last)
    idx = 0
    pages = []
    # ฉากเริ่มต้น
    all4d.each { |l| l.visible = (l.name.start_with?('4D-DONE')) }
    p = upsert.call('4D 00 สภาพ ณ 9 พ.ย. 2569 (ก่อนเริ่มแผน)')
    p.description = 'งานโครงสร้างที่เสร็จก่อนแผน R3'
    pages << p.name
    while d <= stop
      idx += 1
      we = d + 6
      vis = layers_for.call(we)
      all4d.each { |l| l.visible = vis.include?(l.name) }
      active = tasks.select { |t| Date.parse(t['start']) <= we && Date.parse(t['finish']) >= d }.map { |t| t['id'] }
      p = upsert.call(format('4D %02d สัปดาห์ %s', idx, d.strftime('%d/%m/%Y')))
      p.description = "กำลังทำ: #{active.join(', ')}"
      pages << p.name
      d += 7
    end
    all4d.each { |l| l.visible = true }
    model.commit_operation
    pages
  end
end
