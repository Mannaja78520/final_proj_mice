function esc(t){ return String(t==null?'':t).replace(/[&<>"]/g,function(c){
  return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]; }); }

// Both launchers use the registry's order and metadata; no second app catalog.
class MiceToolsManager {
  constructor() { this.revision = 0; }
  boxes() { return Array.from(document.querySelectorAll('.js-tools')); }
  destination(app) {
    if (!app || typeof app.path !== 'string' || !app.path.trim())
      throw new Error('app path is missing');
    const url = new URL(app.path, location.href);
    if (!['http:', 'https:'].includes(url.protocol))
      throw new Error('unsupported app destination');
    return url.href;
  }
  createToolRow(app) {
    const row = document.createElement('div');
    row.className = 'mod tool-tile';
    const name = document.createElement('span');
    name.className = 'nm';
    name.textContent = (app.icon ? app.icon + ' ' : '') + (app.name || app.id || 'เครื่องมือ');
    const description = document.createElement('span');
    description.className = 'ip';
    description.textContent = app.blurb || '';
    const open = document.createElement('a');
    open.className = 'btn tool-open';
    open.href = this.destination(app);
    open.target = '_blank';
    open.rel = 'noopener';
    open.textContent = 'เปิด ↗';
    open.setAttribute('aria-label', 'เปิด ' + (app.name || app.id || 'เครื่องมือ') + ' (แท็บใหม่)');
    open.title = open.getAttribute('aria-label');
    row.append(name, description, open);
    return row;
  }
  render(box, apps) {
    box.replaceChildren(...apps.map(app => this.createToolRow(app)));
    box.setAttribute('aria-busy', 'false');
  }
  state(kind, text, detail) {
    this.boxes().forEach(box => {
      const state = document.createElement('div');
      state.className = 'tool-state empty-state';
      state.dataset.state = kind;
      const message = document.createElement('span');
      message.setAttribute('role', 'status');
      message.textContent = text;
      state.appendChild(message);
      if (kind !== 'loading') {
        const retry = document.createElement('button');
        retry.textContent = 'ลองอีกครั้ง';
        retry.onclick = () => this.load(box);
        state.appendChild(retry);
      }
      if (detail) {
        const tech = document.createElement('span');
        tech.className = 'tech';
        tech.textContent = detail;
        state.appendChild(tech);
      }
      box.replaceChildren(state);
      box.setAttribute('aria-busy', String(kind === 'loading'));
    });
  }
  async load(focusBox) {
    const revision = ++this.revision;
    const keepFocus = focusBox && focusBox.contains(document.activeElement);
    this.state('loading', 'กำลังโหลดเครื่องมือ…');
    try {
      const result = await Mice.Api.get('/api/apps');
      if (revision !== this.revision) return;
      const data = result.data;
      if (!result.ok || !data || data.error || !Array.isArray(data.apps))
        throw new Error(result.says || (data && data.error) || 'invalid app registry response');
      // Validate every destination before drawing either list. Malformed is not empty.
      data.apps.forEach(app => this.destination(app));
      if (!data.apps.length)
        this.state('empty', 'ยังไม่มีเครื่องมือในรายการ เพิ่มเครื่องมือแล้วลองอีกครั้ง');
      else this.boxes().forEach(box => this.render(box, data.apps));
    } catch (error) {
      if (revision !== this.revision) return;
      this.state('error', 'โหลดรายการเครื่องมือไม่ได้ ตรวจว่า Hub ยังทำงานอยู่ แล้วลองอีกครั้ง',
        String(error.message || error) + (window.HUB_BUILT ? ' — hub build ' + window.HUB_BUILT : ''));
    }
    // A retry replaces its button. Move focus to the new result instead of losing it.
    if (keepFocus && focusBox.isConnected) {
      const target = focusBox.querySelector('a, button');
      if (target) target.focus();
    }
  }
}
window.MiceToolsManager = MiceToolsManager;
window.miceTools = new MiceToolsManager();
function toolBoxes(){ return window.miceTools.boxes(); }
function toolRow(app){ return window.miceTools.createToolRow(app); }
async function loadApps(){ return window.miceTools.load(); }
loadApps();
