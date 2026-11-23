// Visual regression shooter: every page x language x theme x viewport, plus automatic
// "what a person would notice" probes (stray Thai in en/zh/ja, console errors, popups stuck at 0,0,
// off-screen/overflowing content). Run: NODE_PATH=$(npm root -g) node tools/visual/shoot.js <base> <outdir> [--quick]
// Pages live in tools/visual/pages.json (DATA: a new page is a new entry).
const { chromium } = require("playwright");
const fs = require("fs"), path = require("path");
const base = process.argv[2], out = process.argv[3], quick = process.argv.includes("--quick");
const cfg = JSON.parse(fs.readFileSync(path.join(__dirname, "pages.json"), "utf8"));
const only = (process.argv.find(a => a.startsWith("--lang=")) || "").slice(7);
const langs = only ? [only] : quick ? ["th", "en"] : cfg.langs, themes0 = quick ? cfg.themes.slice(0, 1) : cfg.themes;
// --themes=indigo,carnival picks others than the two in pages.json (the default look is "indigo")
const pick = (process.argv.find(a => a.startsWith("--themes=")) || "").slice(9);
const themes = pick ? pick.split(",").map(id => ({ id })) : themes0;
const vps = quick ? cfg.viewports.slice(0, 1) : cfg.viewports;
const PROBE = "(function(){" + fs.readFileSync(path.join(__dirname, "probe.js"), "utf8") + "; return visualProbe(document); })()";
(async () => {
  const br = await chromium.launch({ args: ["--use-gl=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"] });
  const report = [];
  for (const vp of vps) for (const lang of langs) for (const theme of themes) {
    const ctx = await br.newContext({ viewport: { width: vp.w, height: vp.h }, deviceScaleFactor: 1 });
    await ctx.request.post(base + "/api/login", { data: { password: process.env.HUB_PW || "qc-test-password" } }).catch(() => {});
    await ctx.addInitScript(([l, t]) => { try { localStorage.setItem("mice.lang", l); if (t) localStorage.setItem("mice_theme", t); } catch (e) {} }, [lang, theme.id]);
    for (const pg of cfg.pages) {
      const p = await ctx.newPage(); const errs = [];
      // no animations: a screenshot taken mid-fade shows a "dim" button that is not a bug (seen 2026-11-23)
      await p.addInitScript(() => { const st = document.createElement("style"); st.textContent = "*,*::before,*::after{transition:none!important;animation:none!important}"; document.addEventListener("DOMContentLoaded", () => document.head.appendChild(st)); });
      p.on("pageerror", e => errs.push("js: " + e.message.slice(0, 120)));
      p.on("console", m => { if (m.type() === "error") errs.push("console: " + m.text().slice(0, 120)); });
      p.on("response", r => { if (r.status() >= 400) errs.push(r.status() + " " + r.url().replace(base, "")); });
      const states = [{ name: "base", steps: [] }].concat(pg.states || []);
      for (const st of states) {
        if (st.desktopOnly && vp.w < 500) continue;
        const tag = [pg.id, st.name, lang, theme.id || "default", vp.id].join("__");
        try {
          await p.goto(base + pg.url, { waitUntil: "load", timeout: 20000 });
          await p.waitForTimeout(pg.wait || 1500);
          for (const s of st.steps) {
            if (s.click) await p.click(s.click, { timeout: 4000 });
            if (s.eval) await p.evaluate(s.eval);
            await p.waitForTimeout(s.wait || 500);
          }
          const probe = await p.evaluate(PROBE);
          const file = path.join(out, tag + ".png");
          fs.mkdirSync(out, { recursive: true });
          await p.screenshot({ path: file, fullPage: !!pg.full && vp.w > 500 });
          report.push({ tag, probe, errs: errs.splice(0) });
        } catch (e) { report.push({ tag, fail: String(e).slice(0, 160), errs: errs.splice(0) }); }
      }
      await p.close();
    }
    await ctx.close();
  }
  fs.writeFileSync(path.join(out, "report.json"), JSON.stringify(report, null, 1));
  await br.close();
  console.log("shots:", report.length);
})();
