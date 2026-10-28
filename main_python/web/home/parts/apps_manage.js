// This PC's apps as extensions (A51-2, user 2026-10-27): add by folder,
// remove (hide, never delete), bring back, update. The hub decides what a
// folder is (main_python/extensions.py); this part only asks and draws.
class MiceAppsManager {
  constructor() {
    this.say = new Mice.Status('apps-say');
    document.getElementById('apps-add').onclick = () => this.add(document.getElementById('apps-folder').value);
    document.getElementById('apps-pick').onclick = () => this.pick();
  }
  button(text, fn, cls) {
    const b = document.createElement('button');
    b.type = 'button';
    b.textContent = text;
    if (cls) b.className = cls;
    b.onclick = fn;
    return b;
  }
  row(title, sub, tech, buttons) {
    const row = document.createElement('div');
    row.className = 'mod';
    const nm = document.createElement('span');
    nm.className = 'nm';
    nm.textContent = title;
    const ip = document.createElement('span');
    ip.className = 'ip';
    ip.textContent = sub;
    if (tech) {
      const t = document.createElement('span');
      t.className = 'tech mini';
      t.textContent = ' ' + tech;
      ip.appendChild(t);
    }
    row.append(nm, ip, ...buttons);
    return row;
  }
  async ask(path, body, good, opts) {
    this.say.loading('กำลังทำ…');
    const ans = await Mice.Api.post(path, body, opts);
    if (ans.needLogin) { this.say.error('เข้าสู่ระบบก่อน แล้วลองอีกครั้ง', ans.tech); return ans; }
    this.say.from(ans, good);
    if (ans.ok) { this.draw(ans.data.list); if (window.miceTools) window.miceTools.load(); }
    return ans;
  }
  add(folder) {
    if (!String(folder || '').trim()) { this.say.warn('ใส่โฟลเดอร์ของแอป หรือกด "เลือกโฟลเดอร์…"'); return; }
    return this.ask('/api/extensions/add', {folder: folder.trim()}, 'เพิ่มแอปแล้ว');
  }
  async pick() {
    const ans = await Mice.Api.post('/api/extensions/pick', {}, {timeout: 600000});
    if (ans.ok && ans.data.folder) document.getElementById('apps-folder').value = ans.data.folder;
    else this.say.warn('เปิดหน้าต่างเลือกโฟลเดอร์ไม่ได้ พิมพ์โฟลเดอร์แทนได้', ans.says);
  }
  draw(d) {
    if (!d) return;
    const found = document.getElementById('apps-found');
    found.replaceChildren(...(d.found || []).map(f =>
      this.row(f.name, 'พร้อมเพิ่ม', f.folder, [this.button('เพิ่ม', () => this.add(f.folder), 'primary')])));
    if (!(d.found || []).length) found.textContent = 'ไม่เจอแอปใหม่ข้างโฟลเดอร์ของ Hub';
    const partners = {};
    (d.partners || []).forEach(p => { partners[p.id] = p; });
    const list = document.getElementById('apps-list');
    list.replaceChildren(...(d.apps || []).map(a => {
      const p = a.needs ? partners[a.needs] : null;
      const hidden = (d.hidden || []).includes(a.id);
      let sub = a.shown ? 'แสดงอยู่' : hidden ? 'ถอดออกจากเครื่องนี้แล้ว' : 'ไม่ได้ติดตั้งในเครื่องนี้';
      const btns = [];
      if (hidden) btns.push(this.button('ใส่กลับ', () => this.ask('/api/extensions/restore', {id: a.id}, 'ใส่กลับแล้ว')));
      else btns.push(this.button('ถอด', () => this.ask('/api/extensions/remove', {id: a.id}, 'ถอดแล้ว')));
      const upId = p ? p.id : (a.added ? a.id : '');
      if (upId && (!p || p.update)) btns.push(this.button('อัปเดต', () =>
        this.ask('/api/extensions/update', {id: upId}, 'อัปเดตแล้ว', {timeout: 330000})));
      return this.row((a.icon ? a.icon + ' ' : '') + (a.name || a.id), sub, p ? p.folder : '', btns);
    }));
  }
  async load() {
    const ans = await Mice.Api.get('/api/extensions');
    if (!ans.ok) { this.say.error('โหลดรายการแอปไม่ได้', ans.tech || ans.says); return; }
    this.draw(ans.data);
  }
}
window.miceApps = new MiceAppsManager();
onTab('tools', () => window.miceApps.load());
