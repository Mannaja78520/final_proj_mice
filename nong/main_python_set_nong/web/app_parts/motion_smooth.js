// --- one smoothing stage for every move (A54-1) ---
// User 2026-10-29: the moves stutter, RL or not; one smoother like a plugin
// that everything goes through. Every move used to be a cosine that STOPS at
// its keyframe, so a dance with a key every 167-500 ms stopped at every key.
// Now a keyframe where a joint keeps going the same way is passed THROUGH at
// a speed (its pass speed), the move a cubic Hermite between the two speeds.
// Same maths as main_python/motion_smooth.py (check_motion_smooth compares
// them on the same moves); the board plays it with `pass:` / PASS (NongMath.h).
// Settings are DATA in motion_smooth.json: on/off per maker of moves, limits.
let SMOOTH = { on: false, sources: {} };
fetch("motion_smooth.json").then(r => r.json()).then(j => { SMOOTH = j; motionSmooth.forget(); }).catch(() => {});

class MotionSmooth {
  // the curve of one joint, s 0..1 of a move T seconds long: cosine rest to
  // rest (as before), else a Hermite through the two pass speeds (deg/s)
  static curve(q0, q1, v0, v1, T, s) {
    s = s <= 0 ? 0 : s >= 1 ? 1 : s;
    if (v0 === 0 && v1 === 0) return q0 + (q1 - q0) * (0.5 - 0.5 * Math.cos(Math.PI * s));
    const s2 = s * s, s3 = s2 * s;
    return q0 + (q1 - q0) * (3 * s2 - 2 * s3) + T * (v0 * (s3 - 2 * s2 + s) + v1 * (s3 - s2));
  }
  // [speed deg/s, speed-up deg/s2] at s
  static curveD(q0, q1, v0, v1, T, s) {
    const d = q1 - q0;
    if (v0 === 0 && v1 === 0)
      return [d * Math.PI / 2 * Math.sin(Math.PI * s) / T, d * Math.PI * Math.PI / 2 * Math.cos(Math.PI * s) / (T * T)];
    return [d * (6 * s - 6 * s * s) / T + v0 * (3 * s * s - 4 * s + 1) + v1 * (3 * s * s - 2 * s),
            (d * (6 - 12 * s) / T + v0 * (6 * s - 4) + v1 * (6 * s - 2)) / T];
  }
  // PASS for the move INTO key i: start speeds then end speeds (2 x joints),
  // null when it rests at both ends. The board plays the curve only when the
  // arm really moves at the start speeds, else the old cosine from rest.
  static passFor(V, i) {
    if (!V || i <= 0 || !(V[i - 1].some(v => v) || V[i].some(v => v))) return null;
    return [...V[i - 1], ...V[i]];
  }
  static pose(a, b, va, vb, ms, s) {
    return a.map((q, j) => MotionSmooth.curve(q, b[j], va[j], vb[j], ms / 1000, s));
  }

  // opts: cfg (motion_smooth.json), maxDps[] and acc[] per joint (the rig),
  // cap (a peak speed cap in force, 0 = none), touches(pose) -> truthy,
  // rest(key) -> true where the arm must stop anyway
  constructor(opts) {
    this.cfg = opts.cfg || {}; this.maxDps = opts.maxDps || []; this.acc = opts.acc || [];
    this.cap = +opts.cap || 0; this.touches = opts.touches || null; this.rest = opts.rest || null;
    this.off = +(this.touches ? this.cfg.maxOffLineDeg : this.cfg.uncheckedOffLineDeg) || 1;
  }
  num(k, d) { const v = this.cfg[k]; return Number.isFinite(+v) && v !== null && v !== "" ? +v : d; }
  top(j) { let t = +this.maxDps[j] || 400; if (this.cap > 0) t = Math.min(t, this.cap); return t; }
  vmax(j) { return this.top(j) * this.num("velScale", 0.85); }
  amax(j) { const a = +this.acc[j] || 0; return a > 0 ? a * this.num("accScale", 1) : Infinity; }

  // monotone tangents (Fritsch-Carlson, uneven spacing); 0 where a joint
  // turns back, holds, stands still and at both ends
  firstGuess(K) {
    const n = K.length, nj = K[0].pose.length, floor = this.num("minViaDps", 2);
    const V = K.map(() => new Array(nj).fill(0));
    for (let i = 1; i < n - 1; i++) {
      if ((K[i].hold || 0) > 0 || (this.rest && this.rest(K[i]))) continue;
      const h0 = K[i].t / 1000, h1 = K[i + 1].t / 1000;
      if (!(h0 > 0) || !(h1 > 0)) continue;
      for (let j = 0; j < nj; j++) {
        const d0 = (K[i].pose[j] - K[i - 1].pose[j]) / h0, d1 = (K[i + 1].pose[j] - K[i].pose[j]) / h1;
        if (d0 * d1 <= 0) continue;
        const w1 = 2 * h1 + h0, w2 = h1 + 2 * h0;
        let v = (w1 + w2) / (w1 / d0 + w2 / d1);
        v = Math.sign(v) * Math.min(Math.abs(v), this.vmax(j));
        V[i][j] = Math.abs(v) >= floor ? v : 0;
      }
    }
    return V;
  }
  // the board lengthens a move under its floor and plays it rest to rest
  tooShort(a, b, T) {
    if (T * 1000 < this.num("minMoveMs", 80)) return true;
    let big = 0;
    for (let j = 0; j < a.length; j++) {
      if (Math.abs(b[j] - a[j]) / (+this.maxDps[j] || 400) > T) return true;
      big = Math.max(big, Math.abs(b[j] - a[j]));
    }
    return this.cap > 0 && big * Math.PI / 2 / this.cap > T;
  }
  // past a key, off the line, over the servo speed, or more speed-up than allowed?
  bad(a, b, va, vb, T) {
    const nj = a.length, ns = this.num("samples", 24), u = b.map((x, j) => x - a[j]);
    const uu = u.reduce((s, x) => s + x * x, 0);
    for (let k = 1; k < ns; k++) {
      const s = k / ns, p = new Array(nj);
      for (let j = 0; j < nj; j++) {
        p[j] = MotionSmooth.curve(a[j], b[j], va[j], vb[j], T, s);
        if (p[j] < Math.min(a[j], b[j]) - 1e-6 || p[j] > Math.max(a[j], b[j]) + 1e-6) return true;
        const [vel, acc] = MotionSmooth.curveD(a[j], b[j], va[j], vb[j], T, s);
        if (Math.abs(vel) > this.top(j) + 1e-6 && (va[j] || vb[j])) return true;
        const plain = 4.935 * Math.abs(b[j] - a[j]) / (T * T);    // rest to rest (cosine) peak
        if (Math.abs(acc) > Math.max(this.amax(j), plain) + 1e-6) return true;
      }
      if (uu > 0) {
        let w = 0;
        for (let j = 0; j < nj; j++) w += (p[j] - a[j]) * u[j];
        w = Math.min(1, Math.max(0, w / uu));
        let dist = 0;
        for (let j = 0; j < nj; j++) dist += (p[j] - a[j] - w * u[j]) ** 2;
        if (Math.sqrt(dist) > this.off) return true;
      }
    }
    return false;
  }
  // collision check on the smoothed path, as finely as Studio's straight
  // checks (SAFE.checkDeg), never coarser than `samples`
  touching(a, b, va, vb, T) {
    let big = 0;
    for (let j = 0; j < a.length; j++) big = Math.max(big, Math.abs(b[j] - a[j]));
    const step = Math.max(0.05, Math.min(1, +this.cfg.checkDeg || 1));
    const ns = Math.max(this.num("samples", 24), Math.ceil(big / step));
    for (let k = 1; k < ns; k++)
      if (this.touches(MotionSmooth.pose(a, b, va, vb, T * 1000, k / ns))) return true;
    return false;
  }
  // per keyframe, per joint: the speed (deg/s) the arm passes it with
  vias(K) {
    if (!K.length) return [];
    if (K.length < 3) return K.map(k => new Array(k.pose.length).fill(0));
    const V = this.firstGuess(K), shrink = this.num("shrink", 0.5), tries = this.num("tries", 6);
    const used = new Array(K.length).fill(0), any = r => r.some(v => v !== 0);
    // a key's speed is shared by the move before and after it, so a shrink can
    // break the move already passed: sweep until none breaks; after `tries` a
    // move rests (0), its straight line, so the sweep always ends
    let changed = true;
    while (changed) {
      changed = false;
      for (let i = 1; i < K.length; i++) {
        if (!any(V[i - 1]) && !any(V[i])) continue;
        const T = K[i].t / 1000, a = K[i - 1].pose, b = K[i].pose;
        if (T > 0 && this.tooShort(a, b, T)) used[i] = tries;
        else if (T > 0 && !this.bad(a, b, V[i - 1], V[i], T)) {
          if (!(this.touches && this.touching(a, b, V[i - 1], V[i], T))) continue;
          used[i] = tries;                       // touching: its straight line, now
        }
        used[i]++;
        const f = T > 0 && used[i] < tries ? shrink : 0;
        V[i - 1] = V[i - 1].map(v => v * f); V[i] = V[i].map(v => v * f);
        changed = true;
      }
    }
    return V.map(r => r.map(v => Math.round(v * 10) / 10 || 0));
  }
}

// Studio's side: which maker a list of moves came from, its limits, and a
// cache so a list is smoothed once per edit, not once per frame.
const motionSmooth = {
  cache: new WeakMap(),
  on(source) { return !!SMOOTH.on && (SMOOTH.sources || {})[source] !== false; },
  forget() { this.cache = new WeakMap(); },
  sig(K) {
    let s = K.length;
    for (const k of K) { s = s * 31 + (+k.t || 0) + (+k.hold || 0) * 7; for (const v of k.pose) s = (s * 1.000001 + v) % 1e12; }
    return s + "|" + RIG.servoMaxDps + "|" + RIG.servoAccel + "|" + maxDps() + "|" + JSON.stringify(SMOOTH);
  },
  // V for the list K, or null when this maker is not smoothed (cosine)
  of(K, source = "studio") {
    if (!K || K.length < 3 || !this.on(source)) return null;
    const sig = this.sig(K), got = this.cache.get(K);
    if (got && got.sig === sig) return got.V;
    const sm = new MotionSmooth({
      cfg: { ...SMOOTH, checkDeg: SAFE.checkDeg },
      maxDps: Array.from({ length: NJ }, (_, j) => jointMaxDps(j)),
      acc: RIG.servoAccel, cap: planPace(K) === "music" ? musicPace.cap(K) : SAFE_DPS,
      touches: p => !!collisionAt(p),
      // planner detours (safe_path.js marks them k.via) are corners the RRT
      // chose; with "planner" off the arm rests on them exactly as before
      rest: k => !!k.via && !this.on("planner"),
    });
    const V = sm.vias(K);
    this.cache.set(K, { sig, V });
    return V;
  },
};
