"use strict";

// Every camera on one page (user 2026-11-23). The list comes from the hub
// (GET /api/cameras: boards, this PC's webcams, cameras people added); a camera
// is watched through /api/dev/cam.stream?dev=<dev>, the same URL for all of
// them, so the face app and the watch window read exactly what this page reads.
class CameraApp extends (window.Mice && window.Mice.App ? window.Mice.App : Object) {
  constructor() {
    super("camera");
    this.$ = id => document.getElementById(id);
    this.esc = s => {
      const d = document.createElement('div');
      d.textContent = s == null ? '' : String(s);
      return d.innerHTML;
    };
    this.cams = [];
    this.kinds = [];
    this.KIND_WORDS = {esp32: 'Camera board', usb: 'USB camera on this PC',
                       link: 'Network camera', demo: 'Demo camera'};
  }

  init() {
    this.load(false);
    this.loadKinds();
    if (window.miceLogin) {
      window.miceLogin.mount(this.$('loginHere'));
    }
    this.$('addKind').onchange = () => this.showKind();
  }

  // Which kinds can be added comes from config/cameras.json, through the hub.
  async loadKinds() {
    try {
      const data = await (await fetch('/api/cameras/kinds')).json();
      this.kinds = data.kinds || [];
    } catch (_) { this.kinds = []; }
    const sel = this.$('addKind');
    sel.innerHTML = this.kinds.map(k =>
      `<option value="${this.esc(k.kind)}">${this.esc(k.label)}</option>`).join('');
    this.showKind();
  }

  showKind() {
    const k = this.kinds.find(x => x.kind === this.$('addKind').value) || {};
    this.$('addLinkRow').hidden = k.needs !== 'value';
    this.$('addHint').textContent = k.hint || '';
  }

  toggleAdd() {
    const box = this.$('addBox');
    box.hidden = !box.hidden;
  }

  async add() {
    const say = this.$('addSay');
    const body = {kind: this.$('addKind').value, name: this.$('addName').value,
                  value: this.$('addLink').value};
    say.textContent = 'adding…';
    try {
      const r = await fetch('/api/cameras/add', {method: 'POST', body: JSON.stringify(body)});
      const d = await r.json().catch(() => ({}));
      if (r.status === 401) { say.textContent = 'Log in first (the box at the top), then add the camera'; return; }
      if (!r.ok || d.ok === false) { say.textContent = d.error || 'the camera could not be added'; return; }
      say.textContent = 'added';
      this.$('addName').value = '';
      this.$('addLink').value = '';
      this.load(false);
    } catch (_) { say.textContent = 'the hub did not answer'; }
  }

  async load(force) {
    const generation = this.loadGeneration = (this.loadGeneration || 0) + 1;
    this.$('stat').textContent = 'looking…';
    let data = null;
    try {
      if (force) await fetch('/api/scan?force=1');
      const r = await fetch('/api/cameras');
      data = await r.json();
      if (!r.ok || data.ok === false || !Array.isArray(data.cameras)) data = null;
    } catch (_) { data = null; }
    if (generation !== this.loadGeneration) return;
    if (data) {
      this.cams = data.cameras;
      this.render();
    } else {
      this.$('none').hidden = true;
      this.$('stat').textContent = 'Could not look for cameras. What is shown may be old. Press Look again to try again.';
    }
  }

  render() {
    const box = this.$('cams');
    // A camera that is being watched keeps its card: redrawing it would cut its picture.
    const live = new Set();
    box.querySelectorAll('input[type=checkbox][data-live]:checked').forEach(c => live.add(c.dataset.dev));
    box.innerHTML = '';
    this.$('none').hidden = this.cams.length > 0;
    this.$('stat').textContent = this.cams.length ? (this.cams.length + ' found') : '';
    this.cams.forEach(c => box.appendChild(this.createCard(c, live.has(c.dev))));
  }

  createCard(c, wasLive) {
    const d = document.createElement('div');
    d.className = 'card cam';
    const live = c.live !== false;
    const dev = c.dev, enc = encodeURIComponent(dev);
    const kind = this.KIND_WORDS[c.kind] || c.kind;
    const streamUrl = location.origin + '/api/dev/cam.stream?dev=' + enc;
    const watching = c.viewers ? c.viewers + ' watching' : '';
    d.innerHTML =
      `<h2>${this.esc(c.name)} <span class="kind">${this.esc(kind)}</span></h2>` +
      `<img class="shot" alt="the view from ${this.esc(c.name)}">` +
      `<div class="row" style="margin-top:var(--sp-2)">` +
        `<label><input type="checkbox" data-live="1" data-dev="${this.esc(dev)}"> live view</label>` +
        `<button class="shotbtn">📷 Take a picture</button>` +
        `<a href="watch.html?dev=${enc}&name=${encodeURIComponent(c.name)}" target="_blank" rel="noopener">🪟 Open in its own window</a>` +
      `</div>` +
      `<div class="row">` +
        `<label><input type="checkbox" class="face"> Recognise faces with this camera</label>` +
        (c.kind === 'esp32' ? `<a href="/mod?dev=${enc}">settings</a>` : '') +
        (c.removable ? `<button class="secondary rm">Remove</button>` : '') +
      `</div>` +
      `<div class="mini say"></div>` +
      (live ? '' : `<div class="mini">Reachable only on a cable. Pictures need WiFi — a JPEG does not fit down a command line. Put this camera on the network to see it here; its settings still work over the cable.</div>`) +
      `<div class="mini tech">${this.esc(dev)} · ${this.esc(c.where || '')}${watching ? ' · ' + this.esc(watching) : ''}<br>Link for other programs: <code>${this.esc(streamUrl)}</code></div>`;
    this.bind(d, c, live, wasLive);
    return d;
  }

  bind(card, c, live, wasLive) {
    const img = card.querySelector('.shot'), say = card.querySelector('.say');
    const url = p => '/api/dev/' + p + '?dev=' + encodeURIComponent(c.dev);
    const shot = card.querySelector('.shotbtn'), box = card.querySelector('[data-live]');
    shot.disabled = box.disabled = !live;
    if (!live) shot.title = 'this camera is only on a cable — pictures need WiFi';

    shot.onclick = () => {
      say.textContent = 'taking…';
      img.onerror = () => { say.textContent = 'no picture — is the camera plugged in?'; };
      img.onload = () => { say.textContent = ''; };
      img.src = url('cam.jpg') + '&t=' + Date.now();
    };

    const start = () => {
      say.textContent = 'live';
      img.onerror = () => {
        say.textContent = 'the live view stopped — the camera stopped answering';
        box.checked = false;
      };
      img.src = url('cam.stream') + '&t=' + Date.now();
    };
    box.onchange = () => {
      if (box.checked) start();
      else {
        img.removeAttribute('src');      // dropping the src closes the connection
        say.textContent = '';
      }
    };
    if (wasLive && live) { box.checked = true; start(); }

    const face = card.querySelector('.face');
    face.checked = !!c.face;
    face.onchange = async () => {
      try {
        const r = await fetch('/api/cameras/face',
          {method: 'POST', body: JSON.stringify({dev: c.dev, on: face.checked})});
        if (r.status === 401) {
          face.checked = !face.checked;
          say.textContent = 'Log in first (the box at the top)';
        } else {
          say.textContent = face.checked
            ? 'The face app now looks through this camera (within a few seconds).'
            : 'The face app no longer uses this camera.';
        }
      } catch (_) { face.checked = !face.checked; say.textContent = 'the hub did not answer'; }
    };

    const rm = card.querySelector('.rm');
    if (rm) rm.onclick = async () => {
      img.removeAttribute('src');
      const r = await fetch('/api/cameras/remove', {method: 'POST', body: JSON.stringify({id: c.id})});
      if (r.status === 401) { say.textContent = 'Log in first (the box at the top)'; return; }
      this.load(false);
    };
  }
}

// Initialize application on load
window.cameraApp = new CameraApp();

document.addEventListener("DOMContentLoaded", () => {
  window.cameraApp.init();
});

// Expose legacy global functions for inline HTML event handlers
window.load = (force) => window.cameraApp.load(force);
