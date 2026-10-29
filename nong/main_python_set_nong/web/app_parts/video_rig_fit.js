class VideoRigFitter {
  constructor(options) { this.options = options; this.settings = VIDEO_FOLLOW.fitting; this.tables = {}; }
  bodyTable(joint) {
    if (this.tables[joint]) return this.tables[joint];
    const saved = pose, rows = [];
    try {
      pose = RIG.neutral.slice();
      for (let v = RIG.min[joint]; v <= RIG.max[joint]; v += 0.5) {
        pose[joint] = v; applyPose(); robot.updateMatrixWorld(true);
        let angle;
        if (joint === 8) {
          const front = new THREE.Vector3(0, 0, 1).applyQuaternion(bodyGroup.getWorldQuaternion(new THREE.Quaternion()));
          angle = Math.atan2(front.x, front.z);
        } else {
          const local = o => bodyGroup.worldToLocal(o.getWorldPosition(new THREE.Vector3()));
          const line = local(jointGroups[0]).sub(local(jointGroups[4]));
          angle = Math.atan2(line.y, Math.hypot(line.x, line.z));
        }
        rows.push({ v, angle });
      }
    } finally { pose = saved; applyPose(); robot.updateMatrixWorld(true); }
    const base = rows.reduce((a, b) => Math.abs(b.v - RIG.neutral[joint]) < Math.abs(a.v - RIG.neutral[joint]) ? b : a).angle;
    return (this.tables[joint] = { rows, base });
  }
  setBody(joint, target) {
    const table = this.bodyTable(joint);
    const best = table.rows.reduce((a, b) => Math.abs(VideoBodyMotion.wrap(b.angle - table.base - target)) < Math.abs(VideoBodyMotion.wrap(a.angle - table.base - target)) ? b : a);
    pose[joint] = clampJ(joint, best.v);
  }
  armCost(arm, bones) {
    applyPose(); robot.updateMatrixWorld(true);
    const local = o => bodyGroup.worldToLocal(o.getWorldPosition(new THREE.Vector3()));
    const s = local(jointGroups[arm * 4]), e = local(elbowBalls[arm]), w = local(wristBalls[arm]);
    const upper = e.clone().sub(s).normalize(), fore = w.clone().sub(e).normalize();
    return 1 - upper.dot(bones.upper) + 1 - fore.dot(bones.fore);
  }
  arm(arm, bones, first) {
    const before = pose.slice();
    const objective = () => this.armCost(arm, bones) + this.settings.continuityWeight *
      pose.slice(arm * 4, arm * 4 + 4).reduce((sum, v, k) => sum + (v - before[arm * 4 + k]) ** 2, 0) / 10000;
    // Existing solver is a seed; the objective below evaluates BOTH achieved
    // bone directions, so an unreachable elbow cannot redirect the forearm.
    vidFitArm(arm, bones, first);
    let bestPose = pose.slice(), best = objective();
    const seeds = first ? [pose.slice(), before, RIG.neutral.map((v, j) => j >= arm * 4 && j < arm * 4 + 4 ? v : pose[j])] : [pose.slice(), before];
    for (const seed of seeds) {
      pose = seed.slice();
      for (const step of this.settings.steps) for (let pass = 0; pass < this.settings.passes; pass++) {
        let improved = false;
        for (let j = arm * 4; j < arm * 4 + 4; j++) {
          const old = pose[j]; let chosen = old;
          const cost = objective;
          let score = cost();
          for (const sign of [-1, 1]) {
            pose[j] = clampJ(j, old + sign * step); const value = cost();
            if (value < score - 1e-8) { score = value; chosen = pose[j]; improved = true; }
          }
          pose[j] = chosen;
        }
        if (!improved) break;
      }
      const score = objective();
      if (score < best + 1e-8) { best = score; bestPose = pose.slice(); }
    }
    pose = bestPose; applyPose(); return this.armCost(arm, bones);
  }
  repair(target, previous) {
    if (!collisionAt(target)) return { pose: target, repaired: false };
    let best = previous && !collisionAt(previous) ? previous.slice() : null;
    let distance = best ? Math.hypot(...best.map((v, j) => v - target[j])) : Infinity;
    const consider = candidate => {
      if (collisionAt(candidate)) return;
      const d = Math.hypot(...candidate.map((v, j) => v - target[j]));
      if (d < distance) { best = candidate.slice(); distance = d; }
    };
    consider(RIG.neutral.map((v, j) => clampJ(j, v)));
    for (const step of this.settings.repairDegrees) {
      for (let j = 0; j < NJ; j++) for (const sign of [-1, 1]) {
        const candidate = target.slice(); candidate[j] = clampJ(j, candidate[j] + sign * step); consider(candidate);
      }
      if (best && distance < step) break;
    }
    // A deterministic local search can adjust two interacting hands together.
    const random = safeRng(17);
    for (let k = 0; k < 64; k++) {
      const candidate = target.map((v, j) => clampJ(j, v + (random() - 0.5) * (k < 32 ? 24 : 60)));
      consider(candidate);
    }
    return best ? { pose: best, repaired: true } : null;
  }
  frames(frames) {
    const saved = pose, poses = [], times = [], targets = [], acceptedFrames = [], quality = { repaired: 0, missing: 0, uncertain: 0, worstBoneDegrees: 0 };
    let previous = null, shot = null;
    try {
      pose = RIG.neutral.map((v, j) => clampJ(j, v));
      for (const frame of frames) {
        let body = frame.body;
        if (body) body = { ...body, arms: body.arms.map(a => ({ ...a,
          upper: new THREE.Vector3(a.upper.x, a.upper.y, a.upper.z), fore: new THREE.Vector3(a.fore.x, a.fore.y, a.fore.z) })) };
        else body = VideoBodyMotion.measure(frame.w, false);
        if (body && this.options.mirror) body = { ...body, twist: -body.twist, roll: -body.roll,
          arms: [body.arms[1], body.arms[0]].map(a => ({ ...a,
            upper: new THREE.Vector3(-a.upper.x, a.upper.y, a.upper.z), fore: new THREE.Vector3(-a.fore.x, a.fore.y, a.fore.z) })) };
        const trusted = frame.trusted !== false;
        if (!body || !trusted) { quality[body ? "uncertain" : "missing"]++; }
        else if (!(previous && frame.action === "hold")) {
          if (this.options.waist) this.setBody(8, frame.waist == null ? body.twist : frame.waist * (this.options.mirror ? -1 : 1));
          if (this.options.shrug) this.setBody(9, body.roll);
          applyPose();
          for (const a of [0, 1]) if (body.arms[a].ok) {
            this.arm(a, body.arms[a], previous === null || shot !== frame.shot);
          }
        }
        const target = this.repair(pose.map((v, j) => clampJ(j, v)), previous);
        if (!target) { quality.uncertain++; continue; }
        if (target.repaired) quality.repaired++;
        pose = target.pose.slice(); previous = pose.slice(); shot = frame.shot;
        poses.push(pose.slice()); times.push(frame.t * 1000);
        targets.push(body && trusted ? body : null); acceptedFrames.push(frame);
      }
      if (this.options.smooth !== false && VIDEO_FOLLOW.smoothing && poses.length > 1) {
        const smoothed = new VideoMotionSmoother().apply(poses, times, acceptedFrames);
        quality.smoothing = { before: smoothed.before, after: smoothed.after };
        let previousSafe = poses[0];
        for (let i = 0; i < poses.length; i++) {
          const repaired = this.repair(smoothed.poses[i], previousSafe);
          poses[i] = repaired ? repaired.pose.slice() : previousSafe.slice();
          previousSafe = poses[i];
        }
        quality.smoothing.afterRepair = VideoMotionSmoother.quality(poses, times);
      }
    } finally { pose = saved; applyPose(); robot.updateMatrixWorld(true); }
    return poses.length ? { poses, times, targets, videoMs: Math.round(times.at(-1)), quality, mirror: this.options.mirror, waist: this.options.waist, shrug: this.options.shrug } : null;
  }
  static assess(fit, made) {
    if (!fit.targets || !made.keys.length) return null;
    const saved = pose, errors = []; let sum = 0, worst = 0, count = 0;
    try {
      fit.targets.forEach((body, i) => {
        if (!body) return;
        pose = easeKeys(made.keys, this.clockForSource(made.keys, fit.times[i]).ms, "video").pose;
        applyPose(); robot.updateMatrixWorld(true);
        const local = o => bodyGroup.worldToLocal(o.getWorldPosition(new THREE.Vector3()));
        let error = 0;
        for (const a of [0, 1]) if (body.arms[a].ok) {
          const s = local(jointGroups[a * 4]), e = local(elbowBalls[a]), w = local(wristBalls[a]);
          for (const [got, wanted] of [[e.clone().sub(s).normalize(), body.arms[a].upper], [w.clone().sub(e).normalize(), body.arms[a].fore]]) {
            const angle = THREE.MathUtils.radToDeg(got.angleTo(wanted)); error = Math.max(error, angle); sum += angle; count++;
          }
        }
        worst = Math.max(worst, error); errors.push({ t: fit.times[i], degrees: Math.round(error * 10) / 10 });
      });
    } finally { pose = saved; applyPose(); robot.updateMatrixWorld(true); }
    return { meanBoneDegrees: count ? sum / count : null, worstBoneDegrees: worst, samples: errors,
      measuredAfterCollisionAndTiming: true, limitedTransitions: made.partial,
      pathCorrections: { around: made.safe.around, dropped: made.safe.dropped, failed: made.safe.failed } };
  }
  static clockForSource(keys, sourceMs) {
    if (!keys.length || !Number.isFinite(keys[0].sourceMs)) return { ms: Math.max(0, sourceMs), rate: 1 };
    let clock = 0;
    for (let i = 0; i < keys.length; i++) {
      const key = keys[i], arrival = i ? clock + key.t : 0;
      if (i && sourceMs <= key.sourceMs) {
        const previous = keys[i - 1], from = previous.sourceHoldEnd ?? previous.sourceMs;
        const fraction = Math.max(0, Math.min(1, (sourceMs - from) / Math.max(1, key.sourceMs - from)));
        return { ms: clock + fraction * key.t, rate: (key.sourceMs - from) / Math.max(1, key.t) };
      }
      const end = key.sourceHoldEnd ?? key.sourceMs;
      if (sourceMs < end) {
        const fraction = Math.max(0, Math.min(1, (sourceMs - key.sourceMs) / Math.max(1, end - key.sourceMs)));
        return { ms: arrival + fraction * (key.hold || 0), rate: (end - key.sourceMs) / Math.max(1, key.hold || 0) };
      }
      clock = arrival + (key.hold || 0);
    }
    return { ms: clock, rate: 1 };
  }
  static sourceForClock(keys, robotMs) {
    let clock = 0;
    for (let i = 0; i < keys.length; i++) {
      const key = keys[i], arrival = i ? clock + key.t : 0;
      if (i && robotMs <= arrival) {
        const from = keys[i - 1].sourceHoldEnd ?? keys[i - 1].sourceMs;
        return { sourceMs: from + (key.sourceMs - from) * Math.max(0, (robotMs - clock) / Math.max(1, key.t)), rate: (key.sourceMs - from) / Math.max(1, key.t), end: false };
      }
      const end = arrival + (key.hold || 0);
      if (robotMs <= end) return { sourceMs: key.sourceMs + ((key.sourceHoldEnd ?? key.sourceMs) - key.sourceMs) *
        Math.max(0, (robotMs - arrival) / Math.max(1, key.hold || 0)), rate: ((key.sourceHoldEnd ?? key.sourceMs) - key.sourceMs) / Math.max(1, key.hold || 0), end: false };
      clock = end;
    }
    const last = keys.at(-1);
    return { sourceMs: last ? (last.sourceHoldEnd ?? last.sourceMs ?? robotMs) : 0, rate: 1, end: true };
  }
}
