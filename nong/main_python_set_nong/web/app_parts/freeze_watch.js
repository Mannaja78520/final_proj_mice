// --- freeze watch ---
// User 2026-09-17: the whole Studio page freezes, while playing, dragging, in
// live mode, and sometimes doing nothing. It did not reproduce headless (0 long
// tasks, fake robot), so the page records it where it happens: a frame gap over
// FREEZE_MS while the tab is visible sends one report to the hub (/api/report)
// with what was running and the slowest recent hub calls.
const FREEZE_MS = 1500;
const _fw = { last: 0, hiddenSince: 0, sentAt: -1e9, calls: [], longs: [] };
(function () {
  const realFetch = window.fetch.bind(window);
  window.fetch = function (url, opts) {            // remember how long hub calls take
    const t0 = performance.now(), u = String(url && url.url || url).slice(0, 90);
    const done = () => {
      _fw.calls.push({ u, ms: Math.round(performance.now() - t0), at: Math.round(t0) });
      if (_fw.calls.length > 40) _fw.calls.shift();
    };
    const p = realFetch(url, opts);
    p.then(done, done);
    return p;
  };
  try {
    new PerformanceObserver(l => l.getEntries().forEach(e => {
      _fw.longs.push({ ms: Math.round(e.duration), at: Math.round(e.startTime) });
      if (_fw.longs.length > 20) _fw.longs.shift();
    })).observe({ entryTypes: ["longtask"] });
  } catch (e) { /* older browser: frame gaps still count */ }
  document.addEventListener("visibilitychange", () => {
    _fw.hiddenSince = document.hidden ? performance.now() : 0;
    _fw.last = 0;                                  // a hidden tab is not a freeze
  });
})();
function freezeCheck(now) {
  const gap = _fw.last ? now - _fw.last : 0;
  _fw.last = now;
  if (gap < FREEZE_MS || document.hidden || now - _fw.sentAt < 30000) return;
  _fw.sentAt = now;
  const gi = (renderer && renderer.info) || {};
  const state = {
    gapMs: Math.round(gap), playing: typeof playing !== "undefined" && playing,
    live: !!($("liveChk") && $("liveChk").checked),
    monitor: !!($("monChk") && $("monChk").checked),
    usb: haveUsb(), wifi: haveWifi(), keys: keys.length,
    gpu: { geometries: gi.memory && gi.memory.geometries, textures: gi.memory && gi.memory.textures,
           programs: gi.programs && gi.programs.length },
    heapMB: performance.memory ? Math.round(performance.memory.usedJSHeapSize / 1048576) : null,
    longTasks: _fw.longs.filter(x => x.at > now - gap - 2000),
    slowCalls: _fw.calls.filter(c => c.ms > 300 || c.at > now - gap - 2000).slice(-15),
  };
  fetch("/api/report", { method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text: "STUDIO FREEZE " + JSON.stringify(state), page: "studio",
                           time: new Date().toISOString(), attachDiag: false }) }).catch(() => {});
}
