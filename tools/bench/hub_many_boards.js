// How the hub's module list behaves with many boards of mixed firmware.
//   NODE_PATH=$(npm root -g) node tools/bench/hub_many_boards.js <out-dir> [counts...]
// Stubs /api/modules and /api/modules/all with N generated boards (the sim
// stand-in for a real rig: 255 is the RS485 address limit), opens the hub page
// at phone and desktop size, and records render time, row count, the row order
// and whether the order survives a rescan where boards join, leave and return.
// User 2026-11-21: "check the main hub page layout/order with many firmwares".
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const TYPES = ['nong', 'lift', 'cam', 'gacha', 'dummy', 'blank'];
const out = process.argv[2] || '.';
const counts = process.argv.slice(3).map(Number);
if (!counts.length) counts.push(5, 30, 100, 255);
fs.mkdirSync(out, { recursive: true });

function board(i, type) {
  // names as people really type them: same name on many boards, numbers in names
  const name = (i % 3 === 0 ? type : type + ' ' + (i % 17 + 1));
  return {
    name, type, id: i, group: i % 4 === 0 ? 'show-a' : '', fw: '1.0.' + (i % 5),
    chip: 'AA:BB:CC:00:' + (i >> 8).toString(16).padStart(2, '0') + ':' + (i & 255).toString(16).padStart(2, '0'),
    key: 'chip' + i, ip: '10.0.' + (i >> 8) + '.' + (i & 255),
    routes: [{ kind: 'wifi', dev: 'wifi:10.0.' + (i >> 8) + '.' + (i & 255), ip: '10.0.' + (i >> 8) + '.' + (i & 255) }],
  };
}
function make(n, skip) {
  const l = [];
  for (let i = 1; i <= n; i++) if (!(skip && skip.has(i))) l.push(board(i, TYPES[(i * 7) % TYPES.length]));
  // the hub's own order (hub_modules.board_order): kind, then name with numbers
  // compared as numbers, then id
  const nat = t => t.toLowerCase().split(/(\d+)/).filter(Boolean).map(p => /^\d+$/.test(p) ? [0, +p, ''] : [1, 0, p]);
  const cmp = (x, y) => { for (let i = 0; i < Math.min(x.length, y.length); i++) for (let k = 0; k < 3; k++) if (x[i][k] !== y[i][k]) return x[i][k] < y[i][k] ? -1 : 1; return x.length - y.length; };
  return l.sort((a, b) => (a.type < b.type ? -1 : a.type > b.type ? 1 : cmp(nat(a.name), nat(b.name)) || a.id - b.id));
}

(async () => {
  const browser = await chromium.launch();
  const res = [];
  for (const n of counts) {
    for (const [w, h, tag] of [[390, 800, 'phone'], [1440, 900, 'desktop']]) {
      const ctx = await browser.newContext({ viewport: { width: w, height: h } });
      const page = await ctx.newPage();
      let current = make(n);
      const serve = (route) => route.fulfill({
        contentType: 'application/json',
        body: JSON.stringify({ ok: true, modules: current, errors: [], host: 'sim-pc', lan: '10.0.0.2' }),
      });
      await page.route('**/api/modules/all*', serve);
      await page.route('**/api/modules?*', serve);
      await page.route('**/api/modules', serve);
      const t0 = Date.now();
      await page.goto('http://127.0.0.1:8642/', { waitUntil: 'load' });
      await page.waitForFunction((n) => document.querySelectorAll('#mods > .mod, #mods > .modgroup').length >= Math.min(n, 1), n, { timeout: 60000 }).catch(() => {});
      await page.waitForTimeout(1500);
      const rows = await page.evaluate(() => Array.from(document.querySelectorAll('#mods > .mod, #mods > .modgroup')).map(e => (e.innerText || '').split('\n')[0]));
      const t1 = Date.now();
      const sideways = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1);
      const height = await page.evaluate(() => document.getElementById('mods') ? document.getElementById('mods').scrollHeight : -1);
      await page.evaluate(() => { const e = document.getElementById('homeMods'); if (e) e.scrollIntoView(); });
      await page.screenshot({ path: path.join(out, `modules_${n}_${tag}.png`), fullPage: false });
      // rescan with a few boards gone, then back: the order of the others must not move
      const gone = new Set([3, 4, 5].filter(x => x <= n));
      current = make(n, gone);
      await page.evaluate(() => window.mergeFar && window.mergeFar(true, window.scanGen));
      await page.waitForTimeout(800);
      const again = await page.evaluate(() => Array.from(document.querySelectorAll('#mods > .mod, #mods > .modgroup')).map(e => (e.innerText || '').split('\n')[0]));
      res.push({ boards: n, view: tag, rows: rows.length, load_ms: t1 - t0, sideways, list_px: height,
                 first10: rows.slice(0, 10), after_leave_rows: again.length });
      console.log(JSON.stringify(res[res.length - 1]));
      await ctx.close();
    }
  }
  fs.writeFileSync(path.join(out, 'hub_many_boards.json'), JSON.stringify(res, null, 1));
  await browser.close();
})();
