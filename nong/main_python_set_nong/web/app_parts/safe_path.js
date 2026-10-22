// --- safe paths (A46-1) ---
// User 2026-10-22: the arm must not hit itself when it copies a person or
// gestures while talking. A move is a straight line in joint space (the board
// eases every joint together), so the fast answer is that line, checked with
// collisionAt() on THIS rig's sizes. Only when the line hits does a planner
// look for a way round: RRT-Connect from both ends, then shortcuts, which
// leaves a short path close to what RRT* would give. The choices are DATA in
// safe_path.json beside this page (planner, step, budgets); the long story is
// in qc/checks/check_safe_path.py.
let SAFE = {
  planner: "rrt-connect",   // "straight" = never go round: a hit is a refusal
  checkDeg: 3,              // biggest joint change between two checked points
  stepDeg: 12,              // how far a tree grows per try
  goalBias: 0.2,
  budgetMs: 1500,           // planning in the editor (video, gestures)
  liveBudgetMs: 60,         // planning while following: miss it and the arm holds
  shortcuts: 60,
  seed: 1,
};
fetch("safe_path.json").then(r => r.json()).then(j => {
  Object.keys(SAFE).forEach(k => { if (k in j) SAFE[k] = j[k]; });
}).catch(() => {});        // no file: the built-in values above

// Seeded, so a plan made twice is the same plan (and QC can repeat it).
function safeRng(seed) {
  let s = (seed >>> 0) || 1;
  return () => { s ^= s << 13; s >>>= 0; s ^= s >> 17; s ^= s << 5; s >>>= 0; return s / 4294967296; };
}
function safeGap(a, b) {   // the biggest joint change, deg
  let m = 0;
  for (let j = 0; j < NJ; j++) m = Math.max(m, Math.abs((b[j] ?? 90) - (a[j] ?? 90)));
  return m;
}
function safeLerp(a, b, f) { return a.map((v, j) => v + (b[j] - v) * f); }
// null when the pose is clear, else what hits (collisionAt's words)
function poseHit(p) { return collisionAt(p); }
// null when every checked point on the straight move a->b is clear
function pathHit(a, b) {
  const n = Math.max(1, Math.ceil(safeGap(a, b) / SAFE.checkDeg));
  for (let s = 1; s <= n; s++) {
    const hit = collisionAt(safeLerp(a, b, s / n));
    if (hit) return hit;
  }
  return null;
}
// a -> b without a hit. { path: [a, ..., b], how: "straight"|"around", ms }
// or { fail: why }. `a` is assumed clear: it is where the arm already is.
function planSafe(a, b, budgetMs, seed) {
  const t0 = performance.now();
  const saved = pose;
  try {
    const endHit = poseHit(b);
    if (endHit) return { fail: "the pose itself: " + endHit };
    if (!pathHit(a, b)) return { path: [a.slice(), b.slice()], how: "straight", ms: performance.now() - t0 };
    if (SAFE.planner === "straight") return { fail: "the move goes through the body, and going round is off" };
    const path = rrtConnect(a, b, budgetMs ?? SAFE.budgetMs, safeRng(seed ?? SAFE.seed), t0);
    if (!path) return { fail: "no way round found in " + Math.round(budgetMs ?? SAFE.budgetMs) + " ms" };
    return { path: safeShortcut(path, safeRng((seed ?? SAFE.seed) + 7)), how: "around", ms: performance.now() - t0 };
  } finally {
    pose = saved;
    applyPose();
  }
}
// Two trees, one from each end, each try reaching for the other. Only the 8
// ARM joints are searched: the waist and shrug turn the body and arms
// together, so they cannot cause a hit (fkPoints holds them still) and they
// simply glide from a to b along the path.
function rrtConnect(a, b, budgetMs, rnd, t0) {
  const lo = RIG.min.slice(0, ARMJ), hi = RIG.max.slice(0, ARMJ);
  const body = (q, f) => q.concat([a[8] + (b[8] - a[8]) * f, a[9] + (b[9] - a[9]) * f]);
  const arm = p => p.slice(0, ARMJ);
  const free = (p, q) => !pathHit(body(p, 0.5), body(q, 0.5));
  const A = [{ q: arm(a), up: -1 }], B = [{ q: arm(b), up: -1 }];
  const near = (T, q) => {
    let best = 0, bd = Infinity;
    for (let i = 0; i < T.length; i++) {
      let d = 0;
      for (let j = 0; j < ARMJ; j++) d += (T[i].q[j] - q[j]) ** 2;
      if (d < bd) { bd = d; best = i; }
    }
    return best;
  };
  const steer = (from, to) => {
    const g = Math.max(...to.map((v, j) => Math.abs(v - from[j])));
    return g <= SAFE.stepDeg ? to.slice() : from.map((v, j) => v + (to[j] - v) * SAFE.stepDeg / g);
  };
  // grow T toward q by one step; the new node's index, or -1 when blocked
  const extend = (T, q) => {
    const n = near(T, q), s = steer(T[n].q, q);
    if (!free(T[n].q, s)) return -1;
    T.push({ q: s, up: n });
    return T.length - 1;
  };
  // keep growing T toward q until it gets there (the index) or is blocked
  const connect = (T, q) => {
    for (;;) {
      const i = extend(T, q);
      if (i < 0) return -1;
      if (Math.max(...T[i].q.map((v, j) => Math.abs(v - q[j]))) < 1e-6) return i;
    }
  };
  const chain = (T, i) => { const out = []; for (; i >= 0; i = T[i].up) out.push(T[i].q); return out; };
  let X = A, Y = B;
  while (performance.now() - t0 < budgetMs) {
    const goal = rnd() < SAFE.goalBias ? Y[0].q : lo.map((l, j) => l + rnd() * (hi[j] - l));
    const i = extend(X, goal);
    if (i >= 0) {
      const k = connect(Y, X[i].q);
      if (k >= 0) {
        const fromA = X === A ? chain(X, i).reverse() : chain(Y, k).reverse();
        const toB = X === A ? chain(Y, k).slice(1) : chain(X, i).slice(1);
        const qs = fromA.concat(toB);
        return qs.map((q, n) => body(q, n / (qs.length - 1)));
      }
    }
    [X, Y] = [Y, X];
  }
  return null;
}
// Random shortcuts: any two points of the path that see each other directly
// lose everything between them. What is left is short and has few corners.
function safeShortcut(path, rnd) {
  let p = path.slice();
  for (let r = 0; r < SAFE.shortcuts && p.length > 2; r++) {
    const i = Math.floor(rnd() * (p.length - 2)), k = i + 2 + Math.floor(rnd() * (p.length - i - 2));
    if (k < p.length && !pathHit(p[i], p[k])) p = p.slice(0, i + 1).concat(p.slice(k));
  }
  return p.map(q => q.map((v, j) => clampJ(j, v)));
}
// A list of timeline keys made safe in one pass (video, recording, gestures):
// a key whose pose hits is dropped (its time goes to the move before, so the
// rhythm stays), and a move that would go through the body gets in-between
// keys that go round. The move's time is shared by distance along the way
// round, and never below what the servos need. Returns
// { keys, dropped, around, failed } - failed moves are dropped too.
function safeKeys(K, budgetMs) {
  const out = [], tally = { dropped: 0, around: 0, failed: 0 };
  for (const k0 of K) {
    const k = { ...k0, pose: k0.pose.map((v, j) => clampJ(j, v)) };
    const prev = out[out.length - 1];
    if (!prev) {
      if (poseHit(k.pose)) { tally.dropped++; continue; }
      out.push(k); continue;
    }
    const plan = planSafe(prev.pose, k.pose, budgetMs);
    if (plan.fail) {
      prev.hold = (prev.hold || 0) + (k.t || 0) + (k.hold || 0);
      tally[poseHit(k.pose) ? "dropped" : "failed"]++;
      continue;
    }
    if (plan.how === "around") {
      tally.around++;
      const legs = plan.path.slice(1).map((q, i) => safeGap(plan.path[i], q));
      const all = legs.reduce((s, v) => s + v, 0) || 1;
      plan.path.slice(1, -1).forEach((q, i) => out.push({
        pose: q, hold: 0, tset: k.tset, via: true,
        t: Math.max(MIN_MOVE_MS, Math.round((k.t || 0) * legs[i] / all)),
      }));
      k.t = Math.max(MIN_MOVE_MS, Math.round((k.t || 0) * legs[legs.length - 1] / all));
    }
    out.push(k);
  }
  return Object.assign({ keys: out }, tally);
}
// In words, for the status lines; "" when nothing needed changing.
function safeSay(r) {
  const bits = [];
  if (r.around) bits.push(r.around + " move" + (r.around > 1 ? "s" : "") + " go round the body instead of through it");
  if (r.dropped) bits.push(r.dropped + " pose" + (r.dropped > 1 ? "s" : "") + " would make the arm hit itself, so the arm holds instead");
  if (r.failed) bits.push(r.failed + " move" + (r.failed > 1 ? "s" : "") + " had no safe way round, so the arm holds instead");
  return bits.length ? "Safe path: " + bits.join("; ") + "." : "";
}
