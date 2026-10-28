class VideoSubjectTracker {
  constructor(options, config = VIDEO_FOLLOW) {
    this.options = options; this.config = config.tracking; this.tracks = []; this.nextId = 1;
    this.primary = null; this.shot = 0; this.lastImage = null; this.history = [];
    this.policy = new VideoTemporalPolicy(VIDEO_POLICY, options.cameraMode); this.observations = [];
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
  candidates(result, image = null) {
    return (result.worldLandmarks || []).map((points, i) => {
      const w = points.map(p => ({ x: p.x, y: p.y, z: p.z, v: p.visibility ?? 1 }));
      const p = result.landmarks[i].map(v => ({ x: v.x, y: v.y, v: v.visibility ?? 1 }));
      const body = VideoBodyMotion.measure(w, false);
      const cx = (p[11].x + p[12].x + p[23].x + p[24].x) / 4, cy = (p[11].y + p[12].y + p[23].y + p[24].y) / 4;
      const size = Math.hypot(p[11].x - p[23].x, p[11].y - p[23].y) + Math.hypot(p[12].x - p[24].x, p[12].y - p[24].y);
      const appearance = result.appearances?.[i] || VideoAppearanceDescriptor.measure(p, image, this.config.imageWidth, this.config.imageHeight);
      return { w, p, body, cx, cy, size, appearance, confidence: body?.confidence || 0 };
    }).filter(p => p.body && p.size > 0.025);
  }
  step(result, t, image = null, sceneOverride = null) {
    const scene = sceneOverride ?? this.imageChange(image);
    const candidates = this.candidates(result, image), used = new Set();
    const sameView = this.primary && candidates.some(c => Math.hypot(c.cx - this.primary.cx, c.cy - this.primary.cy) < 0.06 &&
      Math.abs(Math.log(c.size / this.primary.size)) < 0.15 && c.body.viewUp.angleTo(this.primary.body.viewUp) < 0.5 && c.body.viewLeft.angleTo(this.primary.body.viewLeft) < 0.7);
    const cut = this.options.cameraMode !== "fixed" && scene > this.config.cutDifference && !sameView;
    const policyScene = cut ? Math.max(0.25, scene) : scene;
    if (cut) { this.shot++; this.tracks = []; this.observations = []; }
    for (const c of candidates) {
      let match = null, cost = Infinity;
      for (const previous of this.tracks) if (!used.has(previous.id) && t - previous.t <= this.config.missingSeconds) {
        const spatial = Math.hypot(c.cx - previous.cx, c.cy - previous.cy);
        const distance = spatial + 0.15 * Math.abs(Math.log(c.size / previous.size)) + VideoBodyMotion.difference(c.body, previous.body) / 180 * 0.04;
        if (spatial < this.config.identityGap && distance < cost) { match = previous; cost = distance; }
      }
      c.id = match ? match.id : this.nextId++; c.t = t; used.add(c.id);
    }
    const actors = candidates.map(c => ({ id: c.id, body: c.body, w: c.w, p: c.p, cx: c.cx, size: c.size, appearance: c.appearance, confidence: c.confidence }));
    // An explicit person is always followed independently, regardless of sex
    // or apparent clothing. Different choreographies are never averaged.
    const explicit = this.options.dancer && this.options.dancer !== "auto";
    let chosen = candidates.find(c => String(c.id) === String(this.options.dancer));
    if (!chosen && this.primary && (!explicit || String(this.primary.id) === String(this.options.dancer))) chosen = candidates.find(c => c.id === this.primary.id);
    if (!chosen && this.primary && (cut || t - this.primary.t > this.config.missingSeconds)) {
      const ranked = candidates.map(c => ({ c, score: VideoBodyMotion.difference(c.body, this.primary.body) +
        THREE.MathUtils.radToDeg(Math.abs(VideoBodyMotion.wrap(c.body.twist - this.primary.body.twist))) })).sort((a, b) => a.score - b.score);
      if (ranked.length && ranked[0].score < this.config.styleDegrees && (ranked.length === 1 || ranked[1].score - ranked[0].score > 8)) {
        chosen = ranked[0].c; chosen.id = this.primary.id;
      }
    }
    if (!chosen && (explicit || (this.primary && !cut && t - this.primary.t <= this.config.missingSeconds))) {
      const state = this.policy.step(null, policyScene, cut, 0);
      return { t, w: null, p: null, shot: this.shot, cut, scene, ...state, candidates: candidates.length, actors };
    }
    if (!chosen && candidates.length) {
      const previousBody = this.policy.accepted;
      chosen = candidates.slice().sort((a, b) => {
        const score = c => (previousBody ? VideoBodyMotion.difference(c.body, previousBody) / 90 : 0) + Math.abs(c.cx - (this.options.anchorX ?? 0.5)) - c.size;
        return score(a) - score(b);
      })[0];
    }
    this.tracks = candidates;
    if (!chosen) return { t, w: null, p: null, shot: this.shot, cut, scene, ...this.policy.step(null, policyScene, cut, 0), candidates: 0, actors };
    this.primary = chosen;
    this.observations.push(chosen.body); this.observations = this.observations.slice(-3);
    if (this.observations.length === 3) {
      const median = values => values.sort((a, b) => a - b)[1];
      const smooth = { ...chosen.body, arms: chosen.body.arms.map(a => ({ ...a })) };
      for (const arm of [0, 1]) for (const key of ["upper", "fore"])
        smooth.arms[arm][key] = new THREE.Vector3(...["x", "y", "z"].map(axis => median(this.observations.map(b => b.arms[arm][key][axis])))).normalize();
      smooth.twist = chosen.body.twist + median(this.observations.map(b => VideoBodyMotion.wrap(b.twist - chosen.body.twist)));
      smooth.roll = median(this.observations.map(b => b.roll)); chosen.body = smooth;
      smooth.hipYaw = chosen.body.hipYaw + median(this.observations.map(b => VideoBodyMotion.wrap(b.hipYaw - chosen.body.hipYaw)));
    }
    const supporters = candidates.filter(c => VideoBodyMotion.styleDifference(c.body, chosen.body) <= this.config.styleDegrees);
    const styles = [];
    for (const c of candidates) {
      const group = styles.find(s => VideoBodyMotion.styleDifference(c.body, s.leader.body) <= this.config.styleDegrees);
      if (group) group.people.push(c.id); else styles.push({ leader: c, people: [c.id] });
    }
    const state = this.policy.step(chosen.body, policyScene, cut, chosen.confidence >= this.config.confidence ? 1 : 0);
    let repeatAt = null;
    for (const old of this.history) if (t - old.t > 1 && t - old.t <= this.config.repeatSeconds &&
      VideoBodyMotion.styleDifference(chosen.body, old.body) < 3) { repeatAt = old.t; break; }
    this.history.push({ t, body: chosen.body }); this.history = this.history.filter(h => t - h.t <= this.config.repeatSeconds);
    return { t, w: chosen.w, p: chosen.p, shot: this.shot, cut, scene, ...state,
      actors, track: chosen.id, candidates: candidates.length, supporters: supporters.length, repeatAt,
      styles: styles.map(s => ({ people: s.people, x: s.leader.cx })),
      people: candidates.map(c => ({ id: c.id, x: c.cx, y: c.cy })) };
  }
}
