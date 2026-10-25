/* Browser-local display choices. Hub CPU/GPU capacity never classifies a phone. */
(function (root) {
  "use strict";
  class MiceResourceClient {
    constructor(registry, hints, storage) {
      this.registry = registry || {};
      this.hints = hints || {};
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
    frameDue(now) { return this.lastFrame === null || now - this.lastFrame >= 1000 / this.display().fps; }
    rendered(now) { this.lastFrame = now; }
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
