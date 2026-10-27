// --- safe paths (A46-1) ---
// User 2026-10-22: the arm must not hit itself when it copies a person or
// gestures while talking. A move is a straight line in joint space (the board
// eases every joint together), so the fast answer is that line, checked with
// collisionAt() on THIS rig's sizes. Only when the line hits does a planner
// look for a way round: a quick RRT-Connect seed, then genuine RRT* parent
// selection and rewiring, followed by checked shortcuts. The choices are DATA in
// safe_path.json beside this page (planner, step, budgets); the long story is
// in qc/checks/check_safe_path.py.
let SAFE = {
  planner: "rrt-star",      // "straight" refuses; rrt-connect remains available
  clearMm: 10,              // every check: closer than this is a hit (CLEAR)
  musicGapMm: 7,            // extra gap at the music pace: fast moves cut corners (nong_sim)
  checkDeg: 1,              // biggest joint change between two checked points
  stepDeg: 12,              // how far a tree grows per try
  goalBias: 0.2,
  budgetMs: 1500,           // planning in the editor (video, gestures)
  liveBudgetMs: 60,         // planning while following: miss it and the arm holds
  shortcuts: 60,
  seed: 1,
  seedBudgetMs: 40,
  optimizeMs: 80,
  sliceMs: 12,
  maxNodes: 2000,
  rewireFactor: 1.1,
};
let SAFE_ERROR = "";
function loadSafeSettings(j) {
  const bounds = { checkDeg: [0.05, 10], stepDeg: [0.1, 180], goalBias: [0, 1],
    budgetMs: [1, 30000], liveBudgetMs: [1, 5000], shortcuts: [0, 500],
    seed: [0, 4294967295], seedBudgetMs: [0, 100], optimizeMs: [0, 1000],
    sliceMs: [1, 50], maxNodes: [2, 10000], rewireFactor: [1, 5], musicGapMm: [0, 100], clearMm: [0, 50] };
  if (!j || typeof j !== "object") { SAFE_ERROR = "invalid path settings"; return false; }
  const next = { ...SAFE };
  for (const key of Object.keys(SAFE)) if (key in j) next[key] = j[key];
  if (!["straight", "rrt-connect", "rrt-star"].includes(next.planner)) {
    SAFE_ERROR = "unknown path planner"; return false;
  }
  for (const [key, [lo, hi]] of Object.entries(bounds)) {
    if (!Number.isFinite(next[key]) || next[key] < lo || next[key] > hi ||
        (["shortcuts", "seed", "maxNodes"].includes(key) && !Number.isInteger(next[key]))) {
      SAFE_ERROR = "invalid path setting: " + key; return false;
    }
  }
  Object.assign(SAFE, next); SAFE_ERROR = ""; CLEAR = SAFE.clearMm; return true;
}
fetch("safe_path.json").then(r => r.json()).then(loadSafeSettings).catch(() => {});
function safeRevision() { return JSON.stringify([SAFE, SAFE_ERROR, RIG]); }

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
  if (SAFE_ERROR || !Number.isFinite(SAFE.checkDeg) || SAFE.checkDeg <= 0)
    return SAFE_ERROR || "invalid collision sampling distance";
  const n = Math.max(1, Math.ceil(safeGap(a, b) / Math.max(0.05, Math.min(1, SAFE.checkDeg))));
  for (let s = 0; s <= n; s++) {
    const hit = collisionAt(safeLerp(a, b, s / n));
    if (hit) return hit;
  }
  return null;
}
// a -> b without a hit. { path: [a, ..., b], how: "straight"|"around", ms }
// or { fail: why }. Both endpoints, including the source, must be valid.
function planSafe(a, b, budgetMs, seed) {
  const saved = pose;
  try {
    const search = safeSearch(Array.isArray(a) ? a.slice() : a, Array.isArray(b) ? b.slice() : b, budgetMs, seed);
    let result;
    do { result = search.next(); } while (!result.done);
    return result.value;
  } finally {
    pose = saved;
    applyPose();
  }
}
// Live search yields between iterations. sliceMs is a scheduling target;
// one geometry check and final path validation must finish before yielding.
async function planSafeAsync(a, b, budgetMs, seed, cancelled = () => false) {
  const revision = safeRevision();
  const stale = () => cancelled() || revision !== safeRevision();
  const search = safeSearch(Array.isArray(a) ? a.slice() : a, Array.isArray(b) ? b.slice() : b, budgetMs, seed);
  for (;;) {
    if (stale()) return { fail: "movement cancelled or safety settings changed", cancelled: true };
    const saved = pose, until = performance.now() + Math.max(1, SAFE.sliceMs);
    let result;
    try {
      do { result = search.next(); } while (!result.done && performance.now() < until);
    } finally { pose = saved; applyPose(); }
    if (result.done) return stale() ? { fail: "movement cancelled or safety settings changed", cancelled: true } : result.value;
    await new Promise(resolve => setTimeout(resolve, 0));
  }
}
function safePoseError(q) {
  if (SAFE_ERROR) return SAFE_ERROR;
  if (!Array.isArray(q) || q.length !== NJ) return "a pose needs all " + NJ + " joints";
  for (let j = 0; j < NJ; j++) {
    if (!Number.isFinite(RIG.min[j]) || !Number.isFinite(RIG.max[j]) || RIG.min[j] > RIG.max[j])
      return "the rig has invalid joint limits";
    if (!Number.isFinite(q[j])) return "a joint angle is not a number";
    if (q[j] < RIG.min[j] - 1e-6 || q[j] > RIG.max[j] + 1e-6)
      return "joint " + (j + 1) + " is outside the rig limits";
  }
  return poseHit(q);
}
function* safeSearch(a, b, budgetMs, seed) {
  const t0 = performance.now(), budget = Math.max(1, budgetMs ?? SAFE.budgetMs);
  for (const [label, q] of [["starting pose", a], ["destination", b]]) {
    const error = safePoseError(q);
    if (error) return { fail: label + ": " + error };
  }
  const stats = { rewires: 0, parentChoices: 0, improvements: 0 };
  let path, how = "straight";
  if (!pathHit(a, b)) path = [a.slice(), b.slice()];
  else {
    how = "around";
    if (SAFE.planner === "straight") return { fail: "the move goes through the body, and going round is off" };
    if (SAFE.planner === "rrt-connect") path = rrtConnect(a, b, budget, safeRng(seed ?? SAFE.seed), t0);
    else path = yield* rrtStar(a, b, budget, safeRng(seed ?? SAFE.seed), t0, stats);
    if (!path) return { fail: "no checked way round found in " + Math.round(budget) + " ms" };
    path = safeShortcut(path, safeRng((seed ?? SAFE.seed) + 7));
  }
  // Check what will actually go over the wire, after rounding/shortcuts.
  path = path.map((q, i) => i === 0 ? a.slice() : q.map(v => +fmtA(v)));
  for (let i = 0; i < path.length; i++) {
    if (safePoseError(path[i]) || (i && pathHit(path[i - 1], path[i])))
      return { fail: "the final rounded path is not clear; the robot will hold" };
  }
  return { path, how, planner: SAFE.planner, stats, ms: performance.now() - t0 };
}
// RRT*: minimum-cost checked parent, neighbor rewiring, descendant cost updates.
// A short connect search supplies an initial answer; rewiring can improve it.
function* rrtStar(a, b, budgetMs, rnd, t0, stats) {
  const end = t0 + budgetMs;
  const body = q => q.slice();
  const distance = (p, q) => Math.hypot(...p.map((v, j) => v - q[j]));
  const free = (p, q) => !pathHit(body(p), body(q));
  const goal = b.slice(0, NJ), nodes = [], goals = new Set();
  const add = (q, up) => {
    const n = { q, up, children: new Set(), cost: up < 0 ? 0 : nodes[up].cost + distance(nodes[up].q, q) };
    nodes.push(n);
    if (up >= 0) nodes[up].children.add(nodes.length - 1);
    return nodes.length - 1;
  };
  add(a.slice(0, NJ), -1);
  const seeded = rrtConnect(a, b, Math.min(budgetMs * 0.25, SAFE.seedBudgetMs), rnd, t0);
  if (seeded) for (let i = 1; i < seeded.length; i++) add(seeded[i].slice(0, NJ), nodes.length - 1);
  if (seeded) goals.add(nodes.length - 1);
  let best = seeded ? nodes.length - 1 : -1;
  let bestCost = best < 0 ? Infinity : nodes[best].cost;
  let improveUntil = seeded ? Math.min(end, performance.now() + SAFE.optimizeMs) : end;
  while (performance.now() < improveUntil && nodes.length < SAFE.maxNodes) {
    const sample = rnd() < SAFE.goalBias ? goal : RIG.min.slice(0, NJ).map((l, j) => l + rnd() * (RIG.max[j] - l));
    const ranked = nodes.map((n, i) => ({ i, d: distance(n.q, sample) })).sort((x, y) => x.d - y.d);
    const nearest = nodes[ranked[0].i].q;
    const gap = Math.max(...sample.map((v, j) => Math.abs(v - nearest[j])));
    if (gap < 1e-6) { yield; continue; }
    const q = nearest.map((v, j) => v + (sample[j] - v) * Math.min(1, SAFE.stepDeg / gap));
    const k = Math.min(nodes.length, Math.ceil(SAFE.rewireFactor * Math.E * (1 + 1 / NJ) * Math.log(nodes.length + 1)));
    const near = nodes.map((n, i) => ({ i, d: distance(n.q, q) })).sort((x, y) => x.d - y.d).slice(0, k);
    const parents = near.slice().sort((x, y) => nodes[x.i].cost + x.d - nodes[y.i].cost - y.d);
    let parent = -1;
    for (const n of parents) {
      if (performance.now() >= end) break;
      if (free(nodes[n.i].q, q)) { parent = n.i; break; }
    }
    if (parent < 0) { yield; continue; }
    if (parent !== ranked[0].i) stats.parentChoices++;
    const index = add(q, parent);
    for (const n of near) {
      if (performance.now() >= end) break;
      const newCost = nodes[index].cost + n.d;
      if (n.i === parent || newCost + 1e-7 >= nodes[n.i].cost || !free(q, nodes[n.i].q)) continue;
      const delta = newCost - nodes[n.i].cost;
      nodes[nodes[n.i].up].children.delete(n.i);
      nodes[n.i].up = index;
      nodes[index].children.add(n.i);
      const pending = [n.i];
      while (pending.length) { const child = pending.pop(); nodes[child].cost += delta; pending.push(...nodes[child].children); }
      stats.rewires++;
    }
    if (performance.now() < end && free(q, goal)) goals.add(index);
    for (const i of goals) {
      const cost = nodes[i].cost + distance(nodes[i].q, goal);
      if (cost + 1e-7 < bestCost) {
        if (best < 0) improveUntil = Math.min(end, performance.now() + SAFE.optimizeMs);
        else stats.improvements++;
        best = i; bestCost = cost;
      }
    }
    yield;
  }
  if (best < 0) return null;
  const qs = [goal];
  for (let i = best; i >= 0; i = nodes[i].up) if (distance(nodes[i].q, qs[qs.length - 1]) > 1e-7) qs.push(nodes[i].q);
  qs.reverse();
  return qs.map((q, i) => body(q, i / (qs.length - 1)));
}
// Search all joints: shoulder lift changes physical clearances too.
function rrtConnect(a, b, budgetMs, rnd, t0) {
  const lo = RIG.min.slice(0, NJ), hi = RIG.max.slice(0, NJ);
  const body = q => q.slice();
  const arm = p => p.slice(0, NJ);
  const free = (p, q) => !pathHit(body(p, 0.5), body(q, 0.5));
  const A = [{ q: arm(a), up: -1 }], B = [{ q: arm(b), up: -1 }];
  const near = (T, q) => {
    let best = 0, bd = Infinity;
    for (let i = 0; i < T.length; i++) {
      let d = 0;
      for (let j = 0; j < NJ; j++) d += (T[i].q[j] - q[j]) ** 2;
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
    while (performance.now() - t0 < budgetMs) {
      const i = extend(T, q);
      if (i < 0) return -1;
      if (Math.max(...T[i].q.map((v, j) => Math.abs(v - q[j]))) < 1e-6) return i;
    }
    return -1;
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
  return p;
}
// A list of timeline keys made safe in one pass (video, recording, gestures):
// a key whose pose hits is dropped (its time goes to the move before, so the
// rhythm stays), and a move that would go through the body gets in-between
// keys that go round. Each leg gets what the servos need (minTime) plus a
// share of the rest by distance. keepTime (a video's "stay with the music"):
// a way round that cannot fit in the move's own time is a fail, so the arm
// holds instead of falling behind the music. Returns
// { keys, dropped, around, failed } - failed moves are dropped too.
function safeKeys(K, budgetMs, keepTime) {
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
      if (Number.isFinite(k.sourceMs)) prev.sourceHoldEnd = k.sourceHoldEnd ?? k.sourceMs;
      tally[poseHit(k.pose) ? "dropped" : "failed"]++;
      continue;
    }
    if (plan.how === "around") {
      const legs = plan.path.slice(1).map((q, i) => safeGap(plan.path[i], q));
      const need = plan.path.slice(1).map((q, i) => Math.max(MIN_MOVE_MS, minTime(plan.path[i], q)));
      const all = legs.reduce((s, v) => s + v, 0) || 1;
      const spare = (k.t || 0) - need.reduce((s, v) => s + v, 0);
      if (keepTime && spare < 0) {
        prev.hold = (prev.hold || 0) + (k.t || 0) + (k.hold || 0);
        if (Number.isFinite(k.sourceMs)) prev.sourceHoldEnd = k.sourceHoldEnd ?? k.sourceMs;
        tally.failed++;
        continue;
      }
      tally.around++;
      const legT = i => Math.round(need[i] + Math.max(0, spare) * legs[i] / all);
      const total = legs.reduce((s, _, i) => s + legT(i), 0), sourceFrom = prev.sourceHoldEnd ?? prev.sourceMs;
      let elapsed = 0;
      plan.path.slice(1, -1).forEach((q, i) => {
        elapsed += legT(i);
        const sourceMs = Number.isFinite(k.sourceMs) ? sourceFrom + (k.sourceMs - sourceFrom) * elapsed / total : undefined;
        out.push({ pose: q, hold: 0, tset: k.tset, via: true, t: legT(i), sourceMs, sourceHoldEnd: sourceMs });
      });
      k.t = legT(legs.length - 1);
    } else if (keepTime && minTime(prev.pose, k.pose) > (k.t || 0) + 1) {
      // a dropped pose before it made this move longer: go as far as the time
      // allows, along the line just checked clear (like vidReachSide)
      const f = Math.max(0, Math.min(1, ((k.t || 0) - 1) / minTime(prev.pose, k.pose)));
      k.pose = safeLerp(prev.pose, k.pose, f).map((v, j) => clampJ(j, v));
    }
    // Validate the actual shortened/rounded motion, including body joints.
    const actualPrev = out[out.length - 1];
    if (!keepTime) k.t = Math.max(k.t || 0, minTime(actualPrev.pose, k.pose));
    if (keepTime && minTime(actualPrev.pose, k.pose) > k.t) {
      const target = k.pose.slice(); let lo = 0, hi = 1, best = actualPrev.pose.slice();
      for (let z = 0; z < 18; z++) {
        const f = (lo + hi) / 2, q = safeLerp(actualPrev.pose, target, f).map((v, j) => clampJ(j, v));
        if (minTime(actualPrev.pose, q) <= k.t) { best = q; lo = f; } else hi = f;
      }
      k.pose = best;
    }
    if (poseHit(k.pose) || pathHit(actualPrev.pose, k.pose)) {
      actualPrev.hold = (actualPrev.hold || 0) + (k.t || 0) + (k.hold || 0);
      if (Number.isFinite(k.sourceMs)) actualPrev.sourceHoldEnd = k.sourceHoldEnd ?? k.sourceMs;
      tally.failed++; continue;
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
