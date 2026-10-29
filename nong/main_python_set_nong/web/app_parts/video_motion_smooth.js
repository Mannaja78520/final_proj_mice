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
    const reliable = i => frames[i]?.trusted !== false && frames[i]?.action !== 'uncertain' &&
      (frames[i]?.trusted === true || frames[i]?.body || frames[i]?.w);
    for (let i = 1; i < poses.length; i++) {
      const previous = out[i - 1], dt = Math.max(.001, (times[i] - times[i - 1]) / 1000);
      if (!reliable(i)) { out.push(previous.slice()); velocity.fill(0); continue; }
      const samples = [];
      for (let k = Math.max(1, i - 3); k < Math.min(poses.length, i + 4); k++) {
        if (Math.abs(times[k] - times[i]) > cfg.windowMs || !reliable(k) || frames[k]?.shot !== frames[i]?.shot) continue;
        // Do not smooth through an unknown interval, an actual hold or a cut.
        let connected = true;
        for (let n = Math.min(i, k); n <= Math.max(i, k); n++) if (!reliable(n) || frames[n]?.shot !== frames[i]?.shot) connected = false;
        if (connected) samples.push(poses[k]);
      }
      const next = poses[i].map((value, j) => {
        // A54-1 (PC thread 2026-10-29: this filter dropped all 19 flicks of a
        // 12 s clip). It averaged 350 ms around each frame and capped the
        // target at 240 deg/s and 900 deg/s2, so a 300 ms flick there and back
        // could never form. Now: the MEDIAN of the frames within windowMs
        // (one frame each side at 30 fps), which removes a one-frame tracker
        // spike and keeps anything two frames long; and the limits are the
        // servo's own (rig max deg/s and speed-up, x the scales), so a flick is
        // kept as fast as the arm can really do it. Smoothness between the
        // moves is motion_smooth.js's job.
        const sorted = samples.map(p => p[j]).sort((a, b) => a - b);
        const median = sorted.length ? sorted[Math.floor(sorted.length / 2)] : value;
        const target = frames[i]?.action === 'hold' ? value : median;
        let distance = target - previous[j];
        // Continuous damping retains slow intentional motion; a hard deadband
        // turns it into a series of small stops and jumps.
        if (Math.abs(distance) < cfg.deadbandDegrees) distance *= Math.abs(distance) / cfg.deadbandDegrees;
        const top = jointMaxDps(j) * (+cfg.speedScale || 1);
        const accel = (+RIG.servoAccel[j] || 3000) * (+cfg.accelScale || 1);
        let speed = Math.max(-top, Math.min(top, distance / dt));
        speed = Math.max(velocity[j] - accel * dt, Math.min(velocity[j] + accel * dt, speed));
        const delta = Math.sign(speed) === Math.sign(distance) ? Math.sign(distance) * Math.min(Math.abs(distance), Math.abs(speed * dt)) : 0;
        velocity[j] = delta / dt; return clampJ(j, previous[j] + delta);
      });
      out.push(next);
    }
    return { poses: out, before, after: VideoMotionSmoother.quality(out, times) };
  }
}
