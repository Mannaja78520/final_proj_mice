// Language leftover scan (user 2026-11-23): every page of OUR apps in th/en/zh/ja,
// lists text that is in the wrong language. Data: pages.json. Needs a running hub.
//   NODE_PATH=$(npm root -g) node tools/lang_scan/scan.js [base] [out.json] [page,page]
// Rules: en/zh/ja must have no Thai; en must have no CJK; th/zh/ja flag runs of
// 3+ Latin words (technical words in tech.json are skipped).
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path');
const base = process.argv[2] || 'http://127.0.0.1:8642';
const out = process.argv[3] || 'lang_scan_result.json';
const only = (process.argv[4] || '').split(',').filter(Boolean);
const pages = JSON.parse(fs.readFileSync(path.join(__dirname, 'pages.json'), 'utf8')).filter(p => !only.length || only.includes(p.name));
const LANGS = ['th', 'en', 'zh', 'ja'];
const THAI = /[฀-๿]/, CJK = /[぀-ヿ一-鿿]/;
const LATIN_RUN = /[A-Za-z][A-Za-z'’-]{2,}\s+[A-Za-z][A-Za-z'’-]{1,}/;   // 2+ Latin words
const grab = () => {
  const res = [];
  const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let n;
  while ((n = w.nextNode())) {
    const p = n.parentElement; if (!p || /^(SCRIPT|STYLE|NOSCRIPT)$/.test(p.tagName) || p.closest('#miceLang')) continue;
    const t = n.nodeValue.replace(/\s+/g, ' ').trim(); if (t) res.push(['text', t]);
  }
  document.querySelectorAll('[placeholder],[title],[aria-label],[alt]').forEach(e => {
    ['placeholder', 'title', 'aria-label', 'alt'].forEach(a => { const v = e.getAttribute(a); if (v && v.trim()) res.push([a, v.trim()]); });
  });
  document.querySelectorAll('input[type=button],input[type=submit],option').forEach(e => { if (e.value && e.tagName!=='OPTION') res.push(['value', e.value]); });
  res.push(['title', document.title]);   // the tab title too: it is translated by mice-lang.js (2026-11-23)
  return res;
};
(async () => {
  const browser = await chromium.launch(process.env.PW_CHANNEL ? { channel: process.env.PW_CHANNEL } : {});
  const report = [];
  for (const lang of LANGS) {
    const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
    await ctx.addInitScript(l => { try { localStorage.setItem('mice.lang', l); localStorage.setItem('mice.tech', '1'); } catch (e) {} }, lang);
    for (const pg of pages) {
      const page = await ctx.newPage();
      const seen = new Set(); const bad = [];
      const check = (items, where) => items.forEach(([k, t]) => {
        const key = k + '|' + t; if (seen.has(key)) return; seen.add(key);
        let why = null;
        if (lang !== 'th' && THAI.test(t)) why = 'thai';
        else if (lang === 'en' && CJK.test(t)) why = 'cjk';
        else if (LATIN_RUN.test(t) && !THAI.test(t) && !(lang === 'en' && !CJK.test(t))) why = 'latin-run';
        else if (lang === 'th' && LATIN_RUN.test(t) && !THAI.test(t)) why = 'latin-run';
        if (why) bad.push({ lang, page: pg.name, where, kind: k, why, text: t.slice(0, 900) });
      });
      try {
        await page.goto(base + pg.url + (pg.url.includes('?') ? '&' : '?') + 'lang=' + lang, { waitUntil: 'load', timeout: 20000 });
        await page.waitForTimeout(2500);
        check(await page.evaluate(grab), 'load');
        // click every tab-like control once, collect again
        const sel = pg.tabs || '[data-tab-btn],[data-go],.tabs button,.tab,nav button,[role=tab]';
        const n = await page.locator(sel).count();
        for (let i = 0; i < Math.min(n, 40); i++) {
          try { await page.locator(sel).nth(i).click({ timeout: 800 }); await page.waitForTimeout(500); check(await page.evaluate(grab), 'tab' + i); } catch (e) {}
        }
      } catch (e) { bad.push({ lang, page: pg.name, why: 'load-error', text: String(e.message).slice(0, 120) }); }
      report.push(...bad);
      await page.close();
    }
    await ctx.close();
  }
  await browser.close();
  fs.writeFileSync(out, JSON.stringify(report, null, 1));
  const byKey = {}; report.forEach(r => { const k = r.lang + ' ' + r.page + ' ' + r.why; byKey[k] = (byKey[k] || 0) + 1; });
  console.log(JSON.stringify(byKey, null, 1));
})();
