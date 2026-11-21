// A stranger's walk through every page of the hub: open it, press every safe button, write down what broke.
//   NODE_PATH=$(npm root -g) node tools/bench/page_crawl.js <out.json> [base=http://127.0.0.1:8642] [width=1280]
// Per page: console errors, uncaught exceptions, failed or 4xx/5xx requests, buttons that did nothing visible,
// raw technical words on screen (stack traces, "undefined", "NaN", "[object Object]", "Traceback"), sideways scroll.
// Buttons whose label looks destructive or hardware-touching are listed, never pressed.
// User 2026-11-21: "test as someone who knows nothing about the project, every program in the main hub, list the problems".
const { chromium } = require('playwright');
const fs = require('fs');

const out = process.argv[2] || 'crawl.json';
const base = process.argv[3] || 'http://127.0.0.1:8642';
const width = +(process.argv[4] || 1280);
const SKIP = /stop|delete|remove|erase|clear|reset|reboot|restart|flash|firmware|update|upload|format|forget|unlink|log ?out|sign ?out|shutdown|quit|exit|kill|install|uninstall|start|ลบ|หยุด/i;
const BAD_TEXT = /undefined|NaN|\[object Object\]|Traceback|TypeError|ReferenceError|Internal Server Error|ECONN|WinError|errno/;

async function discover(page) {
  await page.goto(base + '/', { waitUntil: 'load' });
  await page.waitForTimeout(1500);
  const links = await page.evaluate(() => Array.from(document.querySelectorAll('a[href]'))
    .map(a => a.getAttribute('href')).filter(h => h && h.startsWith('/') && !h.startsWith('//')));
  // every app the hub lists, and every tab of the home page (#tab opens it)
  const apps = await page.evaluate(() => fetch('/api/apps').then(r => r.json()).then(d => (d.apps || []).map(a => a.path)).catch(() => []));
  const tabs = await page.evaluate(() => Array.from(document.querySelectorAll('#tabs [data-go]')).map(e => '/#' + e.getAttribute('data-go')));
  const set = new Set(['/', '/studio/', '/help', '/help.html', ...apps, ...tabs, ...links.map(h => h.split('#')[0])]);
  return Array.from(set).filter(h => !/\.(png|jpg|svg|zip|exe|json|js|css|mp3|wav)$/i.test(h) && !h.startsWith('/api/'));
}

(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width, height: 900 } });
  const page = await ctx.newPage();
  let errs = [];
  page.on('console', m => { if (m.type() === 'error') errs.push('console: ' + m.text().slice(0, 200)); });
  page.on('pageerror', e => errs.push('exception: ' + String(e).slice(0, 200)));
  page.on('requestfailed', r => errs.push('request failed: ' + r.url().replace(base, '') + ' ' + (r.failure() || {}).errorText));
  page.on('response', r => { if (r.status() >= 400) errs.push(r.status() + ' ' + r.url().replace(base, '')); });

  const pages = await discover(page);
  const report = [];
  for (const path of pages) {
    errs = [];
    const row = { path, errors: [], pressed: 0, skipped: [], dead: [], bad_text: [], sideways: false, load_ms: 0 };
    const t0 = Date.now();
    try {
      await page.goto(base + path, { waitUntil: 'load', timeout: 20000 });
    } catch (e) { row.errors.push('goto: ' + String(e).slice(0, 120)); }
    await page.waitForTimeout(1200);
    row.load_ms = Date.now() - t0;
    row.sideways = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1);
    const labels = await page.evaluate(() => Array.from(document.querySelectorAll('button, [role=button], summary'))
      .map((b, i) => ({ i, t: (b.innerText || b.getAttribute('aria-label') || b.title || '').trim().slice(0, 40),
                        vis: !!(b.offsetWidth || b.offsetHeight), dis: b.disabled === true })));
    for (const b of labels.slice(0, 60)) {
      if (!b.vis || b.dis) continue;
      if (SKIP.test(b.t)) { row.skipped.push(b.t); continue; }
      const before = await page.evaluate(() => document.body.innerText.length + '|' + location.href + '|' + document.querySelectorAll('*').length);
      const nErr = errs.length;
      try {
        await page.evaluate(i => document.querySelectorAll('button, [role=button], summary')[i].click(), b.i);
        await page.waitForTimeout(250);
      } catch (e) { continue; }
      row.pressed++;
      const after = await page.evaluate(() => document.body.innerText.length + '|' + location.href + '|' + document.querySelectorAll('*').length);
      if (before === after && errs.length === nErr) row.dead.push(b.t || '(no label)');
      if (!page.url().startsWith(base + path.split('#')[0].replace(/\/$/, ''))) await page.goto(base + path, { waitUntil: 'load' }).catch(() => {});
    }
    const text = await page.evaluate(() => document.body.innerText);
    const m = text.match(BAD_TEXT);
    if (m) row.bad_text.push(m[0]);
    row.errors.push(...Array.from(new Set(errs)).slice(0, 12));
    report.push(row);
    console.log(path, 'pressed', row.pressed, 'errors', row.errors.length, 'dead', row.dead.length, 'bad', row.bad_text.join(','), 'sideways', row.sideways, row.load_ms + 'ms');
  }
  fs.writeFileSync(out, JSON.stringify(report, null, 1));
  await browser.close();
})();
