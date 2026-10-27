// Below the media element's minimum rate, advance source frames using the
// checked robot clock. Never clamp a detour into an unchecked faster preview.
class VideoCheckedPlayback {
  constructor(now = () => performance.now()) { this.now = now; this.manual = null; this.notified = false; this.robotMs = null; this.pausedAt = null; }
  reset(video) { this.manual = null; this.robotMs = null; this.pausedAt = null; this.notified = false; if (video) video.playbackRate = 1; }
  stop(video) { this.reset(video); video.pause(); }
  pause(video) {
    if (this.manual) this.pausedAt = { robotMs: this.manual.robotMs + Math.max(0, this.now() - this.manual.wallMs), sourceSeconds: video.currentTime };
    this.manual = null; video.pause();
  }
  start(video, robotMs) {
    if (this.pausedAt && Math.abs(this.pausedAt.sourceSeconds - video.currentTime) < .001) robotMs = this.pausedAt.robotMs;
    this.pausedAt = null;
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
      this.robotMs = robotMs;
      const next = VideoRigFitter.sourceForClock(made.keys, robotMs);
      if (next.end || next.sourceMs >= endMs) { this.stop(video); return Math.min(endMs, next.sourceMs); }
      const rate = next.rate;
      if (!video.seeking) {
        // Setting currentTime starts a new asynchronous seek. Decide whether
        // to resume before that assignment can invalidate the ready state.
        video.currentTime = fromSeconds + next.sourceMs / 1000;
        if (rate >= 0.0625) {
          this.manual = null; video.playbackRate = Math.min(4, rate); video.play().catch(() => {});
        }
      }
      return next.sourceMs;
    }
    const mapped = VideoRigFitter.clockForSource(made.keys, sourceMs);
    this.robotMs = mapped.ms;
    if (mapped.rate < 0.0625) {
      if (!video.paused) {
        this.start(video, mapped.ms);
      }
    } else video.playbackRate = Math.min(4, mapped.rate);
    return sourceMs;
  }
}
const vidCheckedPlayback = new VideoCheckedPlayback();
