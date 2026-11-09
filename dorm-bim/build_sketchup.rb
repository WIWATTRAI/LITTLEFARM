# หอพักคนงาน 5 ชั้น อาคาร A — สร้างโมเดลใน SketchUp จาก elements.json + schedule.json
# ใช้: โหลดไฟล์นี้ใน SketchUp แล้วเรียก DormBIM.build(elements_hash, schedule_hash)
require 'json'
require 'date'

module DormBIM
  DICT = 'BIM4D'.freeze
  CAT_COLORS = {
    'คานคอดิน' => [150, 150, 150], 'เสา' => [190, 190, 185], 'คาน' => [170, 175, 180],
    'พื้น' => [205, 205, 200], 'บันได' => [180, 170, 160], 'โครงหลังคาเหล็ก' => [70, 110, 160],
    'หลังคา' => [120, 60, 45], 'ผนัง' => [225, 215, 195]
  }.freeze

  def self.pt(a)
    Geom::Point3d.new(a[0].m, a[1].m, a[2].m)
  end

  def self.box_member(ents, g)
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
  def self.build(elements, schedule)
    model = Sketchup.active_model
    model.start_operation('สร้างโมเดลหอพัก A BIM-4D', true)
    tasks = {}
    schedule['tasks'].each { |t| tasks[t['id']] = t }
    f_cat = folder(model, 'หมวดงาน')
    f_4d = folder(model, '4D กิจกรรม')
    root = model.entities.add_group
    root.name = 'หอพัก A'
    groups = {}
    count = 0
    elements['elements'].each do |e|
      key = "#{e['category']}|#{e['floor']}"
      cg = groups[key]
      unless cg
        cg = root.entities.add_group
        cg.name = "#{e['category']} ชั้น #{e['floor']}"
        cg.layer = tag(model, "#{e['category']}", f_cat)
        groups[key] = cg
      end
      g = cg.entities.add_group
      g.name = e['id']
      geo = e['geom']
      case geo['type']
      when 'member' then box_member(g.entities, geo)
      when 'prism' then prism(g.entities, geo)
      when 'plate' then plate(g.entities, geo)
      end
      g.material = material(model, e['category'])
      g.layer = tag(model, task_tag_name(e['task'], tasks), f_4d)
      t = tasks[e['task']]
      g.set_attribute(DICT, 'id', e['id'])
      g.set_attribute(DICT, 'name', e['name'])
      g.set_attribute(DICT, 'category', e['category'])
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
    model.pages.to_a.each { |p| model.pages.erase(p) if p.name.start_with?('4D ') }
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
    p = model.pages.add('4D 00 สภาพ ณ 9 พ.ย. 2569 (ก่อนเริ่มแผน)')
    p.description = 'งานโครงสร้างที่เสร็จก่อนแผน R3'
    pages << p.name
    while d <= stop
      idx += 1
      we = d + 6
      vis = layers_for.call(we)
      all4d.each { |l| l.visible = vis.include?(l.name) }
      active = tasks.select { |t| Date.parse(t['start']) <= we && Date.parse(t['finish']) >= d }.map { |t| t['id'] }
      p = model.pages.add(format('4D %02d สัปดาห์ %s', idx, d.strftime('%d/%m/%Y')))
      p.description = "กำลังทำ: #{active.join(', ')}"
      pages << p.name
      d += 7
    end
    all4d.each { |l| l.visible = true }
    model.commit_operation
    pages
  end
end
