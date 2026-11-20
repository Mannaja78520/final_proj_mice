// Client matrix: every page x device profile x network, numbers per cell.
// Asked 2026-11-20: customers may use a TV, phones, old PCs, slow Wi-Fi.
// node tools/client_matrix/run.js [hubUrl] [outFile]  (hub must be running)
// Profiles are DATA in profiles.json: a new device is a new row, no code.
const fs = require("fs"), path = require("path");
const pw = require("playwright");
const HUB = process.argv[2] || "http://127.0.0.1:8642";
const OUT = process.argv[3] || path.join(__dirname, "results.json");
const cfg = JSON.parse(fs.readFileSync(path.join(__dirname, "profiles.json"), "utf8"));

async function cell(browserType, prof, net, page) {
  const opts = prof.device ? Object.assign({}, pw.devices[prof.device]) : {viewport: prof.viewport};
  const ctx = await browserType.newContext(opts);
  const p = await ctx.newPage();
  const errors = [];
  p.on("pageerror", e => errors.push(String(e.message).slice(0, 120)));
  let wire = 0;
  let cdp = null;
  if (browserType.name() === "chromium") {
    cdp = await ctx.newCDPSession(p);
    await cdp.send("Network.enable");
    await cdp.send("Emulation.setCPUThrottlingRate", {rate: prof.cpu || 1});
    await cdp.send("Network.emulateNetworkConditions", {offline: false, latency: net.latency,
      downloadThroughput: net.down * 1024 / 8, uploadThroughput: net.up * 1024 / 8});
    cdp.on("Network.loadingFinished", e => wire += e.encodedDataLength);
  }
  const t0 = Date.now();
  let status = "ok";
  try { await p.goto(HUB + page.path, {waitUntil: "load", timeout: 60000}); }
  catch (e) { status = "timeout"; }
  const load = Date.now() - t0;
  await p.waitForTimeout(page.settle || 1500);
  const m = await p.evaluate(() => {
    const nav = performance.getEntriesByType("navigation")[0] || {};
    const long = performance.getEntriesByType("longtask") || [];
    return {over: document.documentElement.scrollWidth - window.innerWidth,
            dcl: Math.round(nav.domContentLoadedEventEnd || 0),
            heapMB: performance.memory ? Math.round(performance.memory.usedJSHeapSize / 1048576) : null};
  }).catch(() => ({}));
  let fps = null;
  if (page.fps) {
    fps = await p.evaluate(() => new Promise(r => { let n = 0; const t = performance.now();
      (function f() { n++; if (performance.now() - t < 3000) requestAnimationFrame(f); else r(Math.round(n / 3)); })(); })).catch(() => null);
  }
  await ctx.close();
  return {profile: prof.name, net: net.name, page: page.path, status, load_ms: load, dcl_ms: m.dcl,
          wire_kb: Math.round(wire / 1024), heap_mb: m.heapMB, sideways_px: m.over, fps, errors};
}

(async () => {
  const rows = [];
  for (const prof of cfg.profiles) {
    const bt = pw[prof.engine || "chromium"];
    let br;
    try { br = await bt.launch(); } catch (e) { rows.push({profile: prof.name, status: "engine not installed"}); continue; }
    for (const net of cfg.networks) {
      if (prof.nets && !prof.nets.includes(net.name)) continue;
      for (const page of cfg.pages) {
        const ctxBrowser = {name: () => bt.name(), newContext: o => br.newContext(o)};
        const r = await cell(ctxBrowser, prof, net, page);
        rows.push(r);
        console.log([r.profile, r.net, r.page, r.status, r.load_ms + "ms", r.wire_kb + "KB", "fps=" + r.fps, "over=" + r.sideways_px, r.errors.length ? "ERR" : ""].join(" | "));
      }
    }
    await br.close();
  }
  fs.writeFileSync(OUT, JSON.stringify({when: new Date().toISOString(), hub: HUB, rows}, null, 1));
})();
