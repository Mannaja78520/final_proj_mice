// Physical envelopes, independent of helper visibility. FK uses the full pose;
// only the rigid waist frame is removed. SHRUG really changes clearances.
class StudioCollisionGeometry {
  static clamp(x, a, b) { return Math.max(a, Math.min(b, x)); }
  static box(center, axes, half, name, arm = -1) { return { center, axes, half, name, arm }; }
  static local(p, box) {
    const d = p.clone().sub(box.center);
    return box.axes.map(a => d.dot(a));
  }
  static pointBox(p, box) {
    return Math.hypot(...this.local(p, box).map((v, i) => Math.max(0, Math.abs(v) - box.half[i])));
  }
  // Exact minimum on the piecewise-quadratic segment-to-AABB distance.
  static segmentBox(a, b, box) {
    const p = this.local(a, box), q = this.local(b, box), d = q.map((v, i) => v - p[i]);
    const ts = [0, 1];
    for (let i = 0; i < 3; i++) if (Math.abs(d[i]) > 1e-10)
      for (const sign of [-1, 1]) { const t = (sign * box.half[i] - p[i]) / d[i]; if (t > 0 && t < 1) ts.push(t); }
    ts.sort((x, y) => x - y);
    const sq = t => p.reduce((s, v, i) => s + Math.max(0, Math.abs(v + d[i] * t) - box.half[i]) ** 2, 0);
    let best = Math.min(sq(0), sq(1));
    for (let k = 1; k < ts.length; k++) {
      const lo = ts[k - 1], hi = ts[k], mid = (lo + hi) / 2;
      let aa = 0, bb = 0;
      for (let i = 0; i < 3; i++) {
        const v = p[i] + d[i] * mid;
        if (Math.abs(v) > box.half[i]) { aa += d[i] ** 2; bb += d[i] * (p[i] - Math.sign(v) * box.half[i]); }
      }
      const t = aa ? this.clamp(-bb / aa, lo, hi) : mid;
      best = Math.min(best, sq(lo), sq(hi), sq(t));
    }
    return Math.sqrt(best);
  }
  static boxesHit(a, b, gap) {
    const axes = [...a.axes, ...b.axes];
    for (const x of a.axes) for (const y of b.axes) {
      const c = x.clone().cross(y); if (c.lengthSq() > 1e-12) axes.push(c.normalize());
    }
    const delta = b.center.clone().sub(a.center);
    for (const axis of axes) {
      const ra = a.axes.reduce((s, x, i) => s + (a.half[i] + gap / 2) * Math.abs(axis.dot(x)), 0);
      const rb = b.axes.reduce((s, x, i) => s + (b.half[i] + gap / 2) * Math.abs(axis.dot(x)), 0);
      if (Math.abs(delta.dot(axis)) >= ra + rb) return false;
    }
    return true;
  }
  static snapshot(p) {
    const saved = pose;
    try {
      pose = p.slice(); applyPose(); robot.updateMatrixWorld(true);
      const inv = bodyGroup.matrixWorld.clone().invert();
      const at = o => o.getWorldPosition(new THREE.Vector3()).applyMatrix4(inv);
      const basis = [new THREE.Vector3(1, 0, 0), new THREE.Vector3(0, 1, 0), new THREE.Vector3(0, 0, 1)];
      const d = RIG.dims;
      const torso = this.box(new THREE.Vector3(), basis, [d.torsoW / 2, d.torsoH / 2, d.torsoD / 2], "body");
      const head = { at: new THREE.Vector3(0, d.torsoH / 2 + 68, 0), r: R_HEAD, name: "head" };
      const arms = [0, 1].map(arm => {
        const label = arm ? "right" : "left", j = arm * 4;
        const s = at(jointGroups[j]), e = at(elbowBalls[arm]), w = at(wristBalls[arm]);
        const sr = RIG.jointR[arm * 2], er = RIG.jointR[arm * 2 + 1];
        const start = segPoint(s, e, Math.min(0.8, (sr + CLEAR) / Math.max(1, s.distanceTo(e))));
        const bars = [{ a: start, b: e, r: RIG.barR[arm * 2], name: label + " upper arm" },
                      { a: e, b: w, r: RIG.barR[arm * 2 + 1], name: label + " forearm" }];
        let hand = null;
        // BoxGeometry is the physical paddle; helper balls and visibility are irrelevant.
        palmMarks[arm].traverse(o => {
          if (hand || !o.geometry || o.geometry.type !== "BoxGeometry") return;
          o.geometry.computeBoundingBox(); const bb = o.geometry.boundingBox;
          const matrix = inv.clone().multiply(o.matrixWorld), el = matrix.elements;
          const center = bb.getCenter(new THREE.Vector3()).applyMatrix4(matrix);
          const axes = [new THREE.Vector3(el[0], el[1], el[2]), new THREE.Vector3(el[4], el[5], el[6]), new THREE.Vector3(el[8], el[9], el[10])];
          const size = bb.getSize(new THREE.Vector3()).toArray();
          const half = axes.map((a, i) => size[i] * a.length() / 2); axes.forEach(a => a.normalize());
          hand = this.box(center, axes, half, label + " hand", arm);
        });
        return { s, e, w, sr, er, bars, hand, label };
      });
      return { torso, head, arms };
    } finally { pose = saved; applyPose(); robot.updateMatrixWorld(true); }
  }
  static hit(p) {
    if (!Array.isArray(p) || p.length !== NJ || !p.every(Number.isFinite)) return "the pose is invalid";
    if (![...RIG.jointR, ...RIG.barR, RIG.dims.torsoW, RIG.dims.torsoH, RIG.dims.torsoD].every(v => Number.isFinite(v) && v > 0))
      return "the physical collision sizes are invalid";
    const extra = RIG.extraClearanceMm ?? 0;
    if (!Number.isFinite(extra) || extra < 0) return "the extra safety gap is invalid";
    const gap = CLEAR + extra, { torso, head, arms } = this.snapshot(p);
    const sphereBox = (s, box) => this.pointBox(s.at, box) < s.r + gap;
    const sphereBar = (s, bar) => segSegDist(s.at, s.at, bar.a, bar.b) < s.r + bar.r + gap;
    for (const a of arms) {
      if (sphereBar({ at: a.s, r: a.sr }, a.bars[1])) return a.label + " forearm is too close to its shoulder joint";
      const upper = a.bars[0], fore = a.bars[1];
      const upperEnd = segPoint(a.e, upper.a, Math.min(1, (a.er + upper.r + gap) / Math.max(1, a.e.distanceTo(upper.a))));
      const foreStart = segPoint(a.e, a.w, Math.min(1, (a.er + fore.r + gap) / Math.max(1, a.e.distanceTo(a.w))));
      if (segSegDist(upper.a, upperEnd, foreStart, a.w) < upper.r + fore.r + gap)
        return a.label + " forearm is too close to its upper arm";
      if (a.s.distanceTo(head.at) < a.sr + head.r + gap) return a.label + " shoulder joint is too close to the head";
      for (const bar of a.bars) {
        if (this.segmentBox(bar.a, bar.b, torso) < bar.r + gap) return bar.name + " is too close to the body";
        if (sphereBar(head, bar)) return bar.name + " is too close to the head";
      }
      const elbow = { at: a.e, r: a.er };
      if (sphereBox(elbow, torso)) return a.label + " elbow joint is too close to the body";
      if (a.e.distanceTo(head.at) < a.er + head.r + gap) return a.label + " elbow joint is too close to the head";
      if (a.hand) {
        if (this.pointBox(a.e, a.hand) < a.er + gap) return a.hand.name + " is too close to its elbow joint";
        if (this.boxesHit(a.hand, torso, gap)) return a.hand.name + " is too close to the body";
        if (sphereBox(head, a.hand)) return a.hand.name + " is too close to the head";
        if (this.segmentBox(a.bars[0].a, a.bars[0].b, a.hand) < a.bars[0].r + gap)
          return a.hand.name + " is too close to its upper arm";
        if (this.pointBox(a.s, a.hand) < a.sr + gap) return a.hand.name + " is too close to its shoulder joint";
      }
    }
    const [l, r] = arms;
    for (const a of [l, r]) {
      const other = a === l ? r : l;
      for (const bar of a.bars) {
        for (const ob of other.bars)
          if (segSegDist(bar.a, bar.b, ob.a, ob.b) < bar.r + ob.r + gap) return bar.name + " is too close to the opposite arm";
        for (const s of [{ at: other.s, r: other.sr }, { at: other.e, r: other.er }])
          if (sphereBar(s, bar)) return bar.name + " is too close to the opposite joint";
        if (other.hand && this.segmentBox(bar.a, bar.b, other.hand) < bar.r + gap)
          return bar.name + " is too close to the opposite hand";
      }
      if (a.hand) for (const s of [{ at: other.s, r: other.sr }, { at: other.e, r: other.er }])
        if (sphereBox(s, a.hand)) return a.hand.name + " is too close to the opposite joint";
    }
    for (const a of [{ at: l.s, r: l.sr }, { at: l.e, r: l.er }])
      for (const b of [{ at: r.s, r: r.sr }, { at: r.e, r: r.er }])
        if (a.at.distanceTo(b.at) < a.r + b.r + gap) return "the opposite joint balls are too close";
    if (l.hand && r.hand && this.boxesHit(l.hand, r.hand, gap)) return "the hands are too close to each other";
    return null;
  }
}
