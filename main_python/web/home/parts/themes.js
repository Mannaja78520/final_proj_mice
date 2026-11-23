// Themes page: preview cards, Use, Install from a file, Remove. The list comes from
// /api/themes (built-in packs + installed ones), so a new pack is a file and no code here.
class ThemeGallery {
  constructor(grid, say, fileInput, installBtn) {
    this.grid = grid; this.say = say; this.file = fileInput;
    installBtn.onclick = () => this.file.click();
    this.file.onchange = () => this.install();
    this.list = [];
    if (window.miceTheme) miceTheme.onChange(() => this.paint());
    this.load();
  }
  lang() { try { return localStorage.getItem('mice.lang') || 'en'; } catch (e) { return 'en'; } }
  label(t) { const n = t.name || {}; return n[this.lang()] || n.en || t.id; }
  // Colours of a theme read from its own stylesheet block: the picture on the card is the
  // real thing, for the four built-in CSS themes and for packs alike.
  sheetColors(id) {
    const out = {}, want = ['bg', 'card', 'txt', 'acc', 'ok', 'warn', 'err'];
    for (const sh of document.styleSheets) {
      let rules; try { rules = sh.cssRules; } catch (e) { continue; }
      for (const r of rules || []) {
        const parts = (r.selectorText || '').split(',').map(s => s.trim().replace(/'/g, '"'));
        if (!parts.includes(':root[data-theme="' + id + '"]')) continue;
        want.forEach(k => { const v = r.style.getPropertyValue('--' + k).trim(); if (v) out[k] = v; });
        out.mode = (r.style.getPropertyValue('--theme-mode') || '').replace(/["'\s]/g, '')
          || (/dark/.test(r.style.getPropertyValue('color-scheme')) ? 'dark' : 'light');
      }
    }
    return out;
  }
  async load() {
    let packs = [];
    try { packs = (await (await fetch('/api/themes')).json()).themes || []; } catch (e) { /* no packs */ }
    const meta = {}; packs.forEach(t => { meta[t.id] = t; });
    this.list = (window.miceTheme ? miceTheme.list() : []).map(t => {
      const c = this.sheetColors(t.id), m = meta[t.id];
      return {id: t.id, name: m ? m.name : {en: t.name}, note: t.note, mode: c.mode || 'light',
              source: m ? m.source : 'css', colors: c};
    });
    this.paint();
  }
  current() { return (window.miceTheme && miceTheme.get()) || document.documentElement.getAttribute('data-theme') || 'indigo'; }
  card(t) {
    const c = t.colors, on = t.id === this.current();
    const d = document.createElement('div');
    d.className = 'themeCard' + (on ? ' on' : '');
    d.setAttribute('data-id', t.id);
    const prev = document.createElement('div');
    prev.className = 'themePrev';
    prev.style.background = c.bg; prev.style.color = c.txt; prev.style.borderColor = c.acc;
    prev.innerHTML = '<span class="pCard"></span><b>Aa</b><span class="pBtn"></span>'
      + '<i class="pDot"></i><i class="pDot"></i><i class="pDot"></i>';
    prev.querySelector('.pCard').style.background = c.card;
    prev.querySelector('.pBtn').style.background = c.acc;
    const dots = prev.querySelectorAll('.pDot');
    [c.ok, c.warn, c.err].forEach((v, i) => { dots[i].style.background = v; });
    const name = document.createElement('div');
    name.className = 'themeName';
    name.textContent = this.label(t);
    const tag = document.createElement('span');
    tag.className = 'badge';
    tag.textContent = t.mode === 'dark' ? 'Dark' : 'Light';
    name.appendChild(tag);
    const note = document.createElement('div');
    note.className = 'mini';
    note.textContent = t.note || '';
    const row = document.createElement('div');
    row.className = 'row';
    const use = document.createElement('button');
    use.type = 'button';
    use.className = on ? 'secondary' : 'primary';
    use.disabled = on;
    use.textContent = on ? 'In use' : 'Use';
    use.onclick = () => { miceTheme.set(t.id); this.paint(); };
    row.appendChild(use);
    if (t.source === 'installed') {
      const rm = document.createElement('button');
      rm.type = 'button'; rm.className = 'danger'; rm.textContent = 'Remove';
      rm.onclick = () => this.remove(t);
      row.appendChild(rm);
    }
    [prev, name, note, row].forEach(x => d.appendChild(x));
    return d;
  }
  paint() {
    this.grid.textContent = '';
    this.list.forEach(t => this.grid.appendChild(this.card(t)));
  }
  refreshCss() {
    document.querySelectorAll('link[href^="/mice.css"]').forEach(l => { l.href = '/mice.css?v=' + Date.now(); });
  }
  async post(url, body, type) {
    const r = await fetch(url, {method: 'POST', body: body, headers: {'Content-Type': type}});
    let d = {};
    try { d = await r.json(); } catch (e) { /* not JSON */ }
    if (r.status === 401 || d.need_login) throw Error('Log in first to change themes.');
    if (!d.ok) throw Error(d.error || 'That did not work.');
    return d;
  }
  async install() {
    const f = this.file.files[0];
    this.file.value = '';
    if (!f) return;
    this.say.textContent = 'Installing…';
    try {
      const d = await this.post('/api/themes/install', await f.arrayBuffer(), 'application/octet-stream');
      this.refreshCss();
      this.say.textContent = 'Installed. Press Use to switch to it.';
      setTimeout(() => this.load(), 400);
    } catch (e) { this.say.textContent = e.message; }
  }
  async remove(t) {
    try {
      const d = await this.post('/api/themes/remove', JSON.stringify({id: t.id}), 'application/json');
      if (this.current() === t.id) miceTheme.set('indigo');
      this.refreshCss(); setTimeout(() => this.load(), 400);
      this.say.textContent = 'Removed.';
    } catch (e) { this.say.textContent = e.message; }
  }
}
document.addEventListener('DOMContentLoaded', function () {
  window.themeGallery = new ThemeGallery(document.getElementById('themeGrid'), document.getElementById('themeSay'),
    document.getElementById('themeFile'), document.getElementById('themeInstall'));
});
