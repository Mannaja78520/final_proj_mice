// Offline, time-based denoising. Unknown frames remain holds, and an opening
// pose never borrows a future observation. Recheck geometry after filtering.
class VideoMotionSmoother {
  constructor(config = VIDEO_FOLLOW.smoothing) { this.config = config; }
  static quality(poses, times) {
    let reversals = 0, travel = 0, largestStep = 0;
    for (let i = 1; i < poses.length; i++) for (let j = 0; j < NJ; j++) {
      const d = poses[i][j] - poses[i - 1][j];
      travel += Math.abs(d); largestStep = Math.max(largestStep, Math.abs(d));
      if (i > 1 && times[i] - times[i - 2] < 700) {
        const previous = poses[i - 1][j] - poses[i - 2][j];
        if (d * previous < 0 && Math.min(Math.abs(d), Math.abs(previous)) > 2) reversals++;
      }
    }
    return { reversals, travel, largestStep };
  }
  apply(poses, times, frames) {
    if (!poses.length) return { poses: [], before: null, after: null };
    const cfg = this.config, before = VideoMotionSmoother.quality(poses, times);
    const out = [poses[0].slice()], velocity = poses[0].map(() => 0);
    const reliable = i => frames[i]?.trusted !== false && frames[i]?.action !== 'uncertain' && frames[i]?.action !== 'hold';
    for (let i = 1; i < poses.length; i++) {
      const previous = out[i - 1], dt = Math.max(.001, (times[i] - times[i - 1]) / 1000);
      if (!reliable(i)) { out.push(previous.slice()); velocity.fill(0); continue; }
      const samples = [];
      for (let k = Math.max(1, i - 3); k < Math.min(poses.length, i + 4); k++) {
        if (Math.abs(times[k] - times[i]) > cfg.windowMs || !reliable(k) || frames[k]?.shot !== frames[i]?.shot) continue;
        // Do not smooth through an unknown interval, an actual hold or a cut.
        let connected = true;
        for (let n = Math.min(i, k); n <= Math.max(i, k); n++) if (!reliable(n) || frames[n]?.shot !== frames[i]?.shot) connected = false;
        if (connected) samples.push({ pose: poses[k], weight: 1 - Math.abs(times[k] - times[i]) / (cfg.windowMs + 1) });
      }
      const next = poses[i].map((value, j) => {
        const sorted = samples.map(s => s.pose[j]).sort((a, b) => a - b);
        const median = sorted.length ? sorted[Math.floor(sorted.length / 2)] : value;
        let sum = 0, weight = 0;
        for (const s of samples) {
          const w = s.weight * Math.min(1, cfg.outlierDegrees / Math.max(1, Math.abs(s.pose[j] - median)));
          sum += s.pose[j] * w; weight += w;
        }
        const target = weight ? sum / weight : value;
        let distance = target - previous[j];
        // Continuous damping retains slow intentional motion; a hard deadband
        // turns it into a series of small stops and jumps.
        if (Math.abs(distance) < cfg.deadbandDegrees) distance *= Math.abs(distance) / cfg.deadbandDegrees;
        let speed = Math.max(-cfg.maxTargetDps, Math.min(cfg.maxTargetDps, distance / dt));
        speed = Math.max(velocity[j] - cfg.maxTargetAccelDps2 * dt, Math.min(velocity[j] + cfg.maxTargetAccelDps2 * dt, speed));
        const delta = Math.sign(speed) === Math.sign(distance) ? Math.sign(distance) * Math.min(Math.abs(distance), Math.abs(speed * dt)) : 0;
        velocity[j] = delta / dt; return clampJ(j, previous[j] + delta);
      });
      out.push(next);
    }
    return { poses: out, before, after: VideoMotionSmoother.quality(out, times) };
  }
}
