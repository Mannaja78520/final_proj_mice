/* Browser-local display choices. Hub CPU/GPU capacity never classifies a phone. */
(function (root) {
  "use strict";
  class MiceResourceClient {
    constructor(registry, hints, storage) {
      this.registry = registry || {};
      this.hints = {};
      try {
        const cpu = (hints || {}).hardwareConcurrency, memory = (hints || {}).deviceMemory;
        this.hints = {hardwareConcurrency: Number.isFinite(cpu) && cpu > 0 ? cpu : 1,
          deviceMemory: Number.isFinite(memory) && memory > 0 ? memory : 0};
      } catch (_) {}
      this.storage = storage;
      this.mode = "auto";
      this.lastFrame = null;
      try { this.mode = storage.getItem("mice_display_mode") || "auto"; } catch (_) {}
      if (!this.modes().includes(this.mode)) this.mode = "auto";
      if (root.addEventListener) root.addEventListener("storage", event => {
        if (event.key !== "mice_display_mode" && event.key !== null) return;
        this.mode = this.modes().includes(event.newValue) ? event.newValue : "auto";
        this.lastFrame = null;
        if (root.dispatchEvent && root.CustomEvent) root.dispatchEvent(new root.CustomEvent("mice-resource-change"));
      });
    }
    modes() { return ["auto"].concat((this.registry.profiles || []).map(p => p.id)); }
    display() {
      const profiles = this.registry.profiles || [];
      // Bootstrap absent: one conservative fallback, not a second preset table.
      let selected = profiles[0] || {id: "fallback", fps: 24, pixelRatio: 1, antialias: false};
      if (this.mode === "auto") {
        for (const p of profiles) {
          if ((this.hints.hardwareConcurrency || 1) >= p.minCpus &&
              (this.hints.deviceMemory || 0) >= p.minMemoryGiB) selected = p;
        }
      } else selected = profiles.find(p => p.id === this.mode) || selected;
      return Object.assign({}, selected);
    }
    setMode(mode) {
      if (!this.modes().includes(mode)) throw Error("ไม่มีโหมดภาพนี้");
      this.mode = mode;
      try { this.storage.setItem("mice_display_mode", mode); } catch (_) {}
      this.lastFrame = null;
      if (root.dispatchEvent && root.CustomEvent) root.dispatchEvent(new root.CustomEvent("mice-resource-change"));
    }
    frameDue(now) { return this.lastFrame === null || now >= this.lastFrame + 1000 / this.display().fps; }
    // The next frame is due one interval after the last DUE time, not after the
    // vsync it landed on: "now - last >= 25 ms" on a 60 Hz screen drew every
    // second vsync, 30 fps for a 40 fps profile (2026-10-27). A late frame
    // never borrows more than one interval, so a stall does not cause a burst.
    rendered(now) {
      const gap = 1000 / this.display().fps;
      this.lastFrame = this.lastFrame === null ? now : Math.max(this.lastFrame + gap, now - gap);
    }
    applyRenderer(renderer, ratio) {
      renderer.setPixelRatio(Math.min(ratio || 1, this.display().pixelRatio));
      this.lastFrame = null;
    }
  }
  root.MiceResourceClient = MiceResourceClient;
  try {
    let storage;
    try { storage = root.localStorage; } catch (_) {}
    root.MiceResources = new MiceResourceClient(root.MiceResourceRegistry, root.navigator, storage);
  } catch (_) { /* Keep the existing page usable if bootstrap data is missing. */ }
})(window);
