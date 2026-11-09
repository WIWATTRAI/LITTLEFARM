# หอพักคนงาน 5 ชั้น อาคาร A — สร้างโมเดลใน SketchUp จาก elements.json + schedule.json
# ใช้: โหลดไฟล์นี้ใน SketchUp แล้วเรียก DormBIM.build(elements_hash, schedule_hash)
require 'json'
require 'date'

module DormBIM
  DICT = 'BIM4D'.freeze
  CAT_COLORS = {
    'คานคอดิน' => [120, 120, 120], 'เสา' => [204, 89, 77], 'คาน' => [89, 140, 102],
    'พื้น' => [205, 205, 200], 'พื้นสำเร็จรูป' => [140, 178, 217], 'พื้นทับหน้า' => [230, 217, 140], 'เสาเอ็นคานเอ็น' => [140, 140, 140], 'บันได' => [180, 170, 160], 'โครงหลังคาเหล็ก' => [70, 110, 160],
    'หลังคา' => [120, 60, 45], 'ผนัง' => [204, 158, 128],
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
    sec = g['sec']; b = sec['b']
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
      mat = material(model, e['category'])
      by_pb = use_pb && PB_CATS.include?(e['category'])
      g = by_pb ? pb_member(cg.entities, e, mat.name, pb_cache) : cg.entities.add_group
      g.name = e['id']
      case (by_pb ? nil : geo['type'])
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
      g.layer = tag(model, task_tag_name(e['task'], tasks), f_4d)
      t = tasks[e['task']]
      g.set_attribute(DICT, 'id', e['id'])
      g.set_attribute(DICT, 'name', e['name'])
      g.set_attribute(DICT, 'category', e['category'])
      g.set_attribute(DICT, 'discipline', discipline(e['category'])[1])
      g.set_attribute(DICT, 'tool', by_pb ? 'Profile Builder 3' : 'Ruby')
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
