"use strict";

class CameraApp extends (window.Mice && window.Mice.App ? window.Mice.App : Object) {
  constructor() {
    super("camera");
    this.$ = id => document.getElementById(id);
    this.esc = s => {
      const d = document.createElement('div');
      d.textContent = s == null ? '' : String(s);
      return d.innerHTML;
    };
    this.foundCams = new Map();
  }

  init() {
    this.load(false);
    if (window.miceLogin) {
      window.miceLogin.mount(this.$('loginHere'));
    }
  }

  async load(force) {
    const generation = this.loadGeneration = (this.loadGeneration || 0) + 1;
    this.$('stat').textContent = 'กำลังค้นหากล้อง…';
    const found = new Map();
    let failed = 0;
    for (const url of ['/api/mine', '/api/scan' + (force ? '?force=1' : '')]) {
      try {
        const response = await fetch(url), data = await response.json();
        if (!response.ok || data.ok === false || !Array.isArray(data.modules)) throw Error('scan failed');
        data.modules.filter(m => m.type === 'cam').forEach(m => {
          const wireless = url.startsWith('/api/scan');
          found.set(String(m.chip || m.id), {id:m.id, name:m.name,
            dev:wireless ? 'wifi:' + m.ip : m.dev, ip:wireless ? m.ip : undefined});
        });
      } catch (_) { failed++; }
    }
    if (generation !== this.loadGeneration) return;
    if (failed < 2) this.foundCams = found;
    this.render();
    if (failed) {
      this.$('none').hidden = true;
      this.$('stat').textContent = failed === 2
        ? 'ค้นหากล้องไม่ได้ ข้อมูลที่แสดงอาจเก่า กด Look again เพื่อลองอีกครั้ง'
        : 'ค้นหาได้บางส่วน อาจมีกล้องที่ยังไม่แสดง กด Look again เพื่อลองอีกครั้ง';
    }
  }

  render() {
    const box = this.$('cams');
    box.innerHTML = '';
    this.$('none').hidden = this.foundCams.size > 0;
    this.$('stat').textContent = this.foundCams.size ? (this.foundCams.size + ' found') : '';
    
    this.foundCams.forEach(c => {
      box.appendChild(this.createCard(c));
    });
  }

  createCard(c) {
    const d = document.createElement('div');
    d.className = 'card cam';
    const live = c.dev.indexOf('wifi:') === 0;
    
    const displayName = c.name || ('camera ' + c.id);
    const techSpan = live ? '' : ' · ' + this.esc(c.dev);
    
    const cableWarning = live ? '' : 
      `<div class="mini">Reachable only on a cable. Pictures need WiFi — a JPEG does not fit down a command line. Put this camera on the network to see it here; its settings still work over the cable.</div>`;

    d.innerHTML =
      `<h2>${this.esc(displayName)} <span class="mini tech">#${this.esc(c.id)}${techSpan}</span></h2>` +
      `<img class="shot" id="img_${this.esc(c.id)}" alt="the view from ${this.esc(displayName)}">` +
      `<div class="row" style="margin-top:var(--sp-2)">` +
        `<label><input type="checkbox" id="live_${this.esc(c.id)}"> live view</label>` +
        `<button id="shot_${this.esc(c.id)}">📷 Take a picture</button>` +
        `<a href="/mod?dev=${encodeURIComponent(c.dev)}">settings</a>` +
        `<span class="mini" id="say_${this.esc(c.id)}"></span>` +
      `</div>` +
      cableWarning;
    
    this.bindCardEvents(d, c, live);
    return d;
  }

  bindCardEvents(cardEl, c, live) {
    const img = cardEl.querySelector('#img_' + c.id);
    const say = cardEl.querySelector('#say_' + c.id);
    const url = p => '/api/dev/' + p + '?dev=' + encodeURIComponent(c.dev);

    const shot = cardEl.querySelector('#shot_' + c.id);
    shot.disabled = !live;
    if (!live) {
      shot.title = 'this camera is only on a cable — pictures need WiFi';
    }
    
    shot.onclick = () => {
      say.textContent = 'taking…';
      img.onerror = () => { say.textContent = 'no picture — is the camera plugged in?'; };
      img.onload = () => { say.textContent = ''; };
      img.src = url('cam.jpg') + '&t=' + Date.now();
    };
    
    const box = cardEl.querySelector('#live_' + c.id);
    box.disabled = !live;
    box.onchange = () => {
      if (box.checked) {
        say.textContent = 'live';
        img.onerror = () => {
          say.textContent = 'the live view stopped — the camera stopped answering';
          box.checked = false;
        };
        img.src = url('cam.stream') + '&t=' + Date.now();
      } else {
        img.removeAttribute('src'); // dropping the src closes the connection
        say.textContent = '';
      }
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

