// The picker fills itself from the stylesheet - see shared/web/mice.js. The
// page does not know which themes exist, and must not: that is the whole point
// of keeping them in one file. The technical switch is the shared one in the
// head (miceAdv + Mice.TopBar), the same on every page.
document.addEventListener('DOMContentLoaded', function(){
  if (window.miceTheme) miceTheme.picker(document.getElementById('themePick'));
});

function paintSettings(){
  loadUsers();
  if (authed) resourceView.load();
  $('setWho').textContent = authed
    ? ('Logged in on ' + (MY_PC || 'this PC') + ' — you can move, flash and delete.')
    : ('Not logged in' + (MY_PC ? ' on ' + MY_PC : '') + ' — you can look at '
       + 'everything, but changing anything needs the hub password.');
}

onTab('settings', paintSettings);

class ResourceSettingsView {
  constructor() { this.revision = null; this.loading = false; }
  async request(options) {
    const controller = new AbortController(), timer = setTimeout(() => controller.abort(), 6000);
    try {
      const response = await fetch('/api/resources', Object.assign({signal: controller.signal}, options));
      const data = await response.json();
      if (!response.ok || data.ok === false) throw Error(data.error || 'อ่านหรือบันทึกค่าไม่ได้');
      return data;
    } finally { clearTimeout(timer); }
  }
  select(id, choices, value) {
    const box = document.getElementById(id); box.textContent = '';
    choices.forEach(p => { const option = document.createElement('option'); option.value = p.id; option.textContent = p.label; box.appendChild(option); });
    box.value = value;
  }
  async load() {
    if (this.loading) return; this.loading = true;
    try {
      const data = await this.request(); this.revision = data.revision;
      this.select('resourceMode', [{id:'auto',label:'อัตโนมัติ'}].concat(data.choices.profiles), data.settings.mode);
      this.select('resourceDevice', data.choices.devices, data.settings.device);
      const advanced = document.getElementById('resourceAdvanced'); advanced.textContent = '';
      const labels = {cpuThreads:'จำนวนเธรด (0 = อัตโนมัติ)', workers:'งานพร้อมกัน (0 = อัตโนมัติ)', ramReserveMiB:'RAM ที่เว้นไว้ (MiB)', vramReserveMiB:'VRAM ที่เว้นไว้ (MiB)'};
      Object.keys(data.choices.limits).forEach(key => {
        const label = document.createElement('label'), input = document.createElement('input');
        label.textContent = labels[key] || key; input.type = 'number'; input.id = 'resource_' + key;
        input.min = data.choices.limits[key][0]; input.max = data.choices.limits[key][1]; input.step = '1';
        input.value = data.settings[key]; label.appendChild(input); advanced.appendChild(label);
      });
      this.settings = data.settings;
      document.getElementById('resourceSummary').textContent = 'ค่าที่จะใช้กับการโหลดใหม่: ' + data.effective.label + ' · ' + data.effective.device.toUpperCase() + ' · ' + data.effective.cpuThreads + ' เธรด · ' + data.effective.workers + ' งานพร้อมกัน';
      document.getElementById('resourceNotice').textContent = data.notice;
      document.getElementById('resourceStatus').textContent = data.effective.warning || 'พร้อมใช้กับการโหลดงานครั้งถัดไป';
      const client = window.MiceResources;
      if (client) {
        this.select('resourceDisplay', [{id:'auto',label:'อัตโนมัติ'}].concat(client.registry.profiles || []), client.mode);
        document.getElementById('resourceDisplay').onchange = event => client.setMode(event.target.value);
      }
    } catch (error) { document.getElementById('resourceStatus').textContent = 'อ่านค่าไม่ได้ ลองโหลดค่าปัจจุบันอีกครั้ง: ' + error.message; }
    finally { this.loading = false; }
  }
  async save() {
    if (!this.settings || !this.revision || this.saving) return;
    this.saving = true; document.getElementById('resourceSave').disabled = true;
    try {
      const settings = Object.assign({}, this.settings, {mode: document.getElementById('resourceMode').value, device: document.getElementById('resourceDevice').value});
      Object.keys(settings).filter(k => k !== 'mode' && k !== 'device').forEach(k => { settings[k] = Number(document.getElementById('resource_' + k).value); });
      await this.request({method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({settings,revision:this.revision})});
      await this.load();
      document.getElementById('resourceStatus').textContent += ' · บันทึกแล้ว งานที่เปิดอยู่ยังใช้ค่าเดิม';
    } catch (error) { document.getElementById('resourceStatus').textContent = 'ยังไม่ได้บันทึก ค่าที่กรอกยังอยู่: ' + error.message; }
    finally { this.saving = false; document.getElementById('resourceSave').disabled = false; }
  }
}
const resourceView = new ResourceSettingsView();
