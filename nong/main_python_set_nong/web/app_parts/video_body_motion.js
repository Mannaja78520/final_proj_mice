// Keep observation geometry and inferred movement separate: a camera cut is
// not a robot command. Hip-relative measurements also preserve an opening twist.
let VIDEO_FOLLOW = null, VIDEO_POLICY = null, VIDEO_READY = null;
function videoFollowReady() {
  if (!VIDEO_READY) VIDEO_READY = (async () => {
    const config = await fetch("video_follow.json").then(r => r.json());
    if (!config.tracking || !config.fitting || config.version !== 1) throw new Error("Video follow settings could not be read");
    let policy = null;
    try { policy = await fetch(config.policy.model).then(r => r.json()); } catch (_) { /* conservative geometry fallback */ }
    VIDEO_POLICY = policy; VIDEO_FOLLOW = config; return config;
  })().catch(error => { VIDEO_READY = null; throw error; });
  return VIDEO_READY;
}
class VideoBodyMotion {
  static wrap(v) { return Math.atan2(Math.sin(v), Math.cos(v)); }
  static measure(w, mirror = false) {
    if (!w || w.length < 25) return null;
    const point = i => {
      const j = mirror ? (i % 2 ? i + 1 : i - 1) : i, p = w[j];
      return { at: new THREE.Vector3(mirror ? -p.x : p.x, -p.y, -p.z), seen: p.v ?? p.visibility ?? 1 };
    };
    const sl = point(11), sr = point(12), hl = point(23), hr = point(24);
    const confidence = Math.min(sl.seen, sr.seen, hl.seen, hr.seen);
    if (confidence < (VIDEO_FOLLOW?.tracking.confidence ?? 0.55)) return null;
    const left = hl.at.clone().sub(hr.at), spine = sl.at.clone().add(sr.at).sub(hl.at).sub(hr.at);
    if (left.length() < 0.025 || spine.length() < 0.05) return null;
    left.normalize();
    const up = spine.clone().addScaledVector(left, -spine.dot(left)).normalize();
    const front = left.clone().cross(up).normalize();
    const shoulder = sl.at.clone().sub(sr.at), sx = shoulder.dot(left), sz = shoulder.dot(front);
    const twist = Math.atan2(-sz, sx), roll = Math.atan2(shoulder.dot(up), Math.hypot(sx, sz));
    const torsoLeft = shoulder.clone().addScaledVector(up, -shoulder.dot(up)).normalize();
    const torsoFront = torsoLeft.clone().cross(up).normalize();
    const arms = [0, 1].map(a => {
      const S = point(11 + a), E = point(13 + a), W = point(15 + a);
      const local = v => new THREE.Vector3(v.dot(torsoLeft), v.dot(up), v.dot(torsoFront)).normalize();
      return { ok: Math.min(S.seen, E.seen, W.seen) >= (VIDEO_FOLLOW?.tracking.confidence ?? 0.55),
        upper: local(E.at.clone().sub(S.at)), fore: local(W.at.clone().sub(E.at)),
        rawUpper: E.at.clone().sub(S.at).normalize(), rawFore: W.at.clone().sub(E.at).normalize() };
    });
    return { arms, twist, roll, confidence, hipYaw: Math.atan2(front.x, front.z) };
  }
  static difference(a, b, raw = false) {
    if (!a || !b) return 180;
    let error = 0;
    for (let i = 0; i < 2; i++) if (a.arms[i].ok && b.arms[i].ok)
      for (const key of raw ? ["rawUpper", "rawFore"] : ["upper", "fore"])
        error = Math.max(error, THREE.MathUtils.radToDeg(a.arms[i][key].angleTo(b.arms[i][key])));
    return error;
  }
  static styleDifference(a, b) {
    if (!a || !b) return 180;
    return Math.max(this.difference(a, b), THREE.MathUtils.radToDeg(Math.max(
      Math.abs(this.wrap(a.twist - b.twist)), Math.abs(a.roll - b.roll))));
  }
  static blend(previous, observed, weight = 0.6) {
    return { ...observed,
      twist: previous.twist + this.wrap(observed.twist - previous.twist) * weight,
      roll: previous.roll + (observed.roll - previous.roll) * weight,
      arms: observed.arms.map((a, i) => ({ ...a,
        upper: previous.arms[i].upper.clone().lerp(a.upper, weight).normalize(),
        fore: previous.arms[i].fore.clone().lerp(a.fore, weight).normalize() })) };
  }
}
class VideoTemporalPolicy {
  constructor(model = VIDEO_POLICY, cameraMode = "fixed") {
    this.model = model; this.cameraMode = cameraMode; this.accepted = null; this.previous = null;
    this.headingBaseline = null; this.held = 0; this.heading = 0;
  }
  static bin(value, edges) { let n = 0; while (n < edges.length && value >= edges[n]) n++; return n; }
  static state(features, model) {
    return model.features.map((name, i) => VideoTemporalPolicy.bin(features[name], model.bins[i])).join(":");
  }
  step(body, scene, shot, groupTrust = 1) {
    if (!body) { this.held++; return { body: this.accepted, action: "uncertain", trusted: false, waist: this.accepted ? this.heading + this.accepted.twist : null }; }
    if (!this.accepted) {
      this.accepted = body; this.previous = body; this.headingBaseline = body.hipYaw;
      return { body, action: "initial", trusted: true, waist: body.twist };
    }
    const features = {
      invariant: VideoBodyMotion.difference(body, this.accepted), raw: VideoBodyMotion.difference(body, this.previous, true),
      body: THREE.MathUtils.radToDeg(Math.max(Math.abs(VideoBodyMotion.wrap(body.twist - this.accepted.twist)), Math.abs(body.roll - this.accepted.roll))),
      scene, confidence: body.confidence * groupTrust, held: this.held,
      heading: THREE.MathUtils.radToDeg(Math.abs(VideoBodyMotion.wrap(body.hipYaw - this.headingBaseline)))
    };
    let action = "uncertain", learned = false;
    const model = this.model;
    if (model?.enabled && model.schema === "mice-video-q-v1") {
      const row = model.q[VideoTemporalPolicy.state(features, model)];
      if (row && row.every(Number.isFinite)) {
        const ranks = row.map((q, i) => ({ q, i })).sort((a, b) => b.q - a.q);
        if (ranks[0].q - ranks[1].q >= (VIDEO_FOLLOW?.policy.minimumMargin ?? 0.5)) {
          action = model.actions[ranks[0].i]; learned = true;
        }
      }
    }
    // Explicit geometry fallback for unseen states or a policy that did not
    // meet held-out acceptance. Missing identity never authorizes a pose jump.
    if (!learned && features.confidence >= 0.55) {
      if (scene > 0.18 && features.invariant < 12 && features.body < 8) action = "compensate";
      else if (scene <= 0.18 && (features.invariant > 3 || features.body > 2 || features.heading > 3)) action = "accept";
      else if (features.invariant <= 3 && features.body <= 2) action = "hold";
    }
    if (groupTrust < 0.5 || (scene > 0.18 && (features.invariant > 45 || features.body > 35))) action = "uncertain";
    if (features.confidence >= 0.55 && features.invariant < (VIDEO_FOLLOW?.body.stillBonesDegrees ?? 6) &&
        features.body < (VIDEO_FOLLOW?.body.stillBodyDegrees ?? 3) && features.heading < 3 && scene < 0.1) action = "hold";
    const headingObservable = this.cameraMode === "fixed" || scene < 0.01;
    if (features.confidence >= 0.55 && features.heading >= 3 && !shot && scene <= 0.18 && headingObservable) {
      this.heading += VideoBodyMotion.wrap(body.hipYaw - this.headingBaseline);
      this.headingBaseline = body.hipYaw;
    }
    if (shot || scene > 0.18 || !headingObservable) this.headingBaseline = body.hipYaw;
    if (action === "accept" || action === "compensate") {
      this.accepted = action === "compensate" ? VideoBodyMotion.blend(this.accepted, body) : body; this.held = 0;
    }
    else this.held++;
    this.previous = body;
    return { body: this.accepted, action, learned, trusted: action !== "uncertain", features,
      waist: this.heading + this.accepted.twist };
  }
}
