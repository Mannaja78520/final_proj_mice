// --- the real servos (A48-24) ---
// User 2026-10-27: see in Studio where the real robot falls behind the timing.
// The board sends a target every frame; a hobby servo reaches it late: it
// answers after a delay (lag), speeds up no faster than its acceleration and
// turns no faster than its top speed. All three are per joint on the RIG
// (Setup > rig), so they follow this robot's servos; lag and acceleration are
// guesses until measured on the bench (lab-day.md). The warn/bad lines and the
// frame are DATA in servo_follow.json. tools/nong_sim/world.py uses the same
// model (_servo_step), so Studio and the physics player agree.
let SERVO_VIEW = { frameMs: 20, warnDeg: 8, badDeg: 20 };
fetch("servo_follow.json").then(r => r.json()).then(j => {
  for (const k of Object.keys(SERVO_VIEW)) if (Number.isFinite(j[k]) && j[k] > 0) SERVO_VIEW[k] = j[k];
}).catch(() => {});

class ServoFollow {
  constructor(start) { this.reset(start); }
  reset(start) {
    this.pos = [...start]; this.aim = [...start]; this.vel = new Array(NJ).fill(0);
  }
  // one step of dt ms toward target; returns where the horns are
  step(target, dt) {
    const s = dt / 1000;
    for (let j = 0; j < NJ; j++) {
      const lag = Math.max(0.1, +RIG.servoLagMs[j] || 0) / 1000;
      this.aim[j] += (target[j] - this.aim[j]) * (1 - Math.exp(-s / lag));
      const top = jointMaxDps(j), acc = Math.max(1, +RIG.servoAccel[j] || 1);
      const err = this.aim[j] - this.pos[j];
      // the fastest speed that can still stop on the aim: no overshoot
      const want = Math.sign(err) * Math.min(top, Math.sqrt(2 * acc * Math.abs(err)), Math.abs(err) / s);
      const dv = Math.max(-acc * s, Math.min(acc * s, want - this.vel[j]));
      this.vel[j] += dv;
      this.pos[j] += this.vel[j] * s;
    }
    return this.pos;
  }
  // The whole list K played at the board's frame: for every move, how far the
  // horns trailed the timeline at worst, and on which joint.
  static trace(K) {
    if (!K.length) return { moves: [], worst: null };
    const f = new ServoFollow(K[0].pose), dt = SERVO_VIEW.frameMs;
    const end = easeKeys(K, Infinity).end || 0, starts = [];
    let t = K[0].hold || 0;
    for (let i = 1; i < K.length; i++) { starts.push(t); t += K[i].t + (K[i].hold || 0); }
    const moves = K.map(() => ({ deg: 0, joint: -1 }));
    let worst = null, m = 0;
    for (let ms = 0; ms <= end + 500; ms += dt) {
      while (m < starts.length - 1 && ms >= starts[m + 1]) m++;
      const want = easeKeys(K, ms).pose, got = f.step(want, dt);
      for (let j = 0; j < NJ; j++) {
        const e = Math.abs(want[j] - got[j]), mv = moves[Math.min(m + 1, K.length - 1)];
        if (e > mv.deg) { mv.deg = e; mv.joint = j; }
        if (!worst || e > worst.deg) worst = { deg: e, joint: j, move: m + 1, ms };
      }
    }
    return { moves, worst };
  }
}

// What the time bar and the status line show: cached per edit of the moves.
const servoLag = {
  sig: "", res: null,
  of() {
    const sig = keysSignature() + "|" + RIG.servoLagMs + "|" + RIG.servoAccel + "|" + RIG.servoMaxDps + "|" + maxDps();
    if (sig !== this.sig) { this.sig = sig; this.res = ServoFollow.trace(playKeys()); }
    return this.res;
  },
  // for bar chip i: {deg, joint, level: "" | "warn" | "bad"}; a suspended
  // chip is not played, so the played list counts only the others
  forKey(i) {
    if (!keys[i] || keys[i].off) return null;
    let p = 0;
    for (let n = 0; n < i; n++) if (!keys[n].off) p++;
    const mv = this.of().moves[p];
    if (!p || !mv) return null;
    const level = mv.deg >= SERVO_VIEW.badDeg ? "bad" : mv.deg >= SERVO_VIEW.warnDeg ? "warn" : "";
    return { ...mv, level };
  },
  summary() {
    const w = this.of().worst;
    if (!w || w.deg < SERVO_VIEW.warnDeg) return "The real servos keep up with every move.";
    return `The real servos fall up to ${Math.round(w.deg)}° behind (${JOINT_LABELS[w.joint] || "joint " + (w.joint + 1)}, ` +
           `move ${w.move}). Marked moves on the bar; slow them or tick “Play like the real servos” to watch it.`;
  },
};
// "Play like the real servos": the 3D robot shows the horns, not the plan.
let servoPlay = null;
function servoPlayPose(target, dt) {
  if (!$("servoView") || !$("servoView").checked) { servoPlay = null; return target; }
  if (!servoPlay) servoPlay = new ServoFollow(target);
  return [...servoPlay.step(target, dt)];
}
