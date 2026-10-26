class VideoSubjectTracker {
  constructor(options, config = VIDEO_FOLLOW) {
    this.options = options; this.config = config.tracking; this.tracks = []; this.nextId = 1;
    this.primary = null; this.shot = 0; this.lastImage = null; this.history = [];
    this.policy = new VideoTemporalPolicy();
  }
  imageChange(image) {
    if (!image) return 0;
    let difference = 0, count = 0;
    if (this.lastImage && this.lastImage.length === image.length)
      for (let i = 0; i < image.length; i += 4) {
        difference += Math.abs(image[i] - this.lastImage[i]) + Math.abs(image[i + 1] - this.lastImage[i + 1]) + Math.abs(image[i + 2] - this.lastImage[i + 2]); count += 3;
      }
    this.lastImage = new Uint8Array(image);
    return count ? difference / count / 255 : 0;
  }
  candidates(result) {
    return (result.worldLandmarks || []).map((points, i) => {
      const w = points.map(p => ({ x: p.x, y: p.y, z: p.z, v: p.visibility ?? 1 }));
      const p = result.landmarks[i].map(v => ({ x: v.x, y: v.y, v: v.visibility ?? 1 }));
      const body = VideoBodyMotion.measure(w, this.options.mirror);
      const cx = (p[11].x + p[12].x + p[23].x + p[24].x) / 4, cy = (p[11].y + p[12].y + p[23].y + p[24].y) / 4;
      const size = Math.hypot(p[11].x - p[23].x, p[11].y - p[23].y) + Math.hypot(p[12].x - p[24].x, p[12].y - p[24].y);
      return { w, p, body, cx, cy, size, confidence: body?.confidence || 0 };
    }).filter(p => p.body && p.size > 0.025);
  }
  step(result, t, image = null, sceneOverride = null) {
    const scene = sceneOverride ?? this.imageChange(image);
    const cut = this.options.cameraMode === "cuts" && scene > this.config.cutDifference;
    if (cut) { this.shot++; this.tracks = []; this.primary = null; }
    const candidates = this.candidates(result), used = new Set();
    for (const c of candidates) {
      let match = null, cost = Infinity;
      for (const previous of this.tracks) if (!used.has(previous.id) && t - previous.t <= this.config.missingSeconds) {
        const spatial = Math.hypot(c.cx - previous.cx, c.cy - previous.cy);
        const distance = spatial + 0.15 * Math.abs(Math.log(c.size / previous.size)) + VideoBodyMotion.difference(c.body, previous.body) / 180 * 0.04;
        if (spatial < this.config.identityGap && distance < cost) { match = previous; cost = distance; }
      }
      c.id = match ? match.id : this.nextId++; c.t = t; used.add(c.id);
    }
    // An explicit person is always followed independently, regardless of sex
    // or apparent clothing. Different choreographies are never averaged.
    let chosen = candidates.find(c => String(c.id) === String(this.options.dancer));
    if (!chosen && this.primary) chosen = candidates.find(c => c.id === this.primary.id);
    if (!chosen && this.primary && !cut && t - this.primary.t <= this.config.missingSeconds) {
      const state = this.policy.step(null, scene, cut, 0);
      return { t, w: null, p: null, shot: this.shot, cut, scene, ...state, candidates: candidates.length };
    }
    if (!chosen && candidates.length) {
      const previousBody = this.policy.accepted;
      chosen = candidates.slice().sort((a, b) => {
        const score = c => (previousBody ? VideoBodyMotion.difference(c.body, previousBody) / 90 : 0) + Math.abs(c.cx - (this.options.anchorX ?? 0.5)) - c.size;
        return score(a) - score(b);
      })[0];
    }
    this.tracks = candidates;
    if (!chosen) return { t, w: null, p: null, shot: this.shot, cut, scene, ...this.policy.step(null, scene, cut, 0), candidates: 0 };
    this.primary = chosen;
    const supporters = candidates.filter(c => VideoBodyMotion.difference(c.body, chosen.body) <= this.config.styleDegrees);
    const styles = [];
    for (const c of candidates) {
      const group = styles.find(s => VideoBodyMotion.difference(c.body, s.leader.body) <= this.config.styleDegrees);
      if (group) group.people.push(c.id); else styles.push({ leader: c, people: [c.id] });
    }
    const state = this.policy.step(chosen.body, scene, cut, chosen.confidence >= this.config.confidence ? 1 : 0);
    let repeatAt = null;
    for (const old of this.history) if (t - old.t > 1 && t - old.t <= this.config.repeatSeconds &&
      VideoBodyMotion.difference(chosen.body, old.body) < 3 && Math.abs(chosen.body.twist - old.body.twist) < 0.04) { repeatAt = old.t; break; }
    this.history.push({ t, body: chosen.body }); this.history = this.history.filter(h => t - h.t <= this.config.repeatSeconds);
    return { t, w: chosen.w, p: chosen.p, shot: this.shot, cut, scene, ...state,
      track: chosen.id, candidates: candidates.length, supporters: supporters.length, repeatAt,
      styles: styles.map(s => ({ people: s.people, x: s.leader.cx })),
      people: candidates.map(c => ({ id: c.id, x: c.cx, y: c.cy })) };
  }
}
