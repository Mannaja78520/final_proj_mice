// Below the media element's minimum rate, advance source frames using the
// checked robot clock. Never clamp a detour into an unchecked faster preview.
class VideoCheckedPlayback {
  constructor(now = () => performance.now()) { this.now = now; this.manual = null; this.notified = false; }
  reset(video) { this.manual = null; this.notified = false; if (video) video.playbackRate = 1; }
  stop(video) { this.reset(video); video.pause(); }
  start(video, robotMs) {
    video.pause(); this.manual = { robotMs, wallMs: this.now() };
    if (!this.notified) {
      this.notified = true;
      vidSay("Very slow detours play frame by frame; sound pauses. Play both pauses or resumes.");
    }
  }
  update(video, made, sourceMs, fromSeconds, endMs) {
    if (!made?.keys.length || made.keepMusic !== false) return sourceMs;
    if (this.manual) {
      const robotMs = this.manual.robotMs + Math.max(0, this.now() - this.manual.wallMs);
      const next = VideoRigFitter.sourceForClock(made.keys, robotMs);
      if (!video.seeking) video.currentTime = fromSeconds + next.sourceMs / 1000;
      if (next.end || next.sourceMs >= endMs) { this.stop(video); return Math.min(endMs, next.sourceMs); }
      const rate = VideoRigFitter.clockForSource(made.keys, next.sourceMs).rate;
      if (rate >= 0.0625 && !video.seeking) {
        this.manual = null; video.playbackRate = Math.min(4, rate); video.play().catch(() => {});
      }
      return next.sourceMs;
    }
    const mapped = VideoRigFitter.clockForSource(made.keys, sourceMs);
    if (mapped.rate < 0.0625) {
      if (!video.paused) {
        this.start(video, mapped.ms);
      }
    } else video.playbackRate = Math.min(4, mapped.rate);
    return sourceMs;
  }
}
const vidCheckedPlayback = new VideoCheckedPlayback();
