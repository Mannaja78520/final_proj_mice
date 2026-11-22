// --- undo / redo for the timeline ---
// Studio had no way back: one wrong tap on Delete lost a keyframe for good.
// bumpKeys() (timeline.js) is the one place every edit passes, so this class
// only listens there: it keeps the timeline as it was after the previous edit
// and files it when the next edit lands. Nothing in the editing code changes.
// Edits that keep the same number of keyframes and come within 0.7 s of each
// other (a drag, typing a time) count as ONE step, or Undo would crawl back a
// pixel at a time. Loading a file or a show calls reset(): that is a new start,
// not something to step back through.
class TimelineUndo {
  constructor() {
    this.MAX = 60; this.COALESCE_MS = 700;
    this.past = []; this.future = [];
    this.last = null; this.lastLen = 0; this.lastAt = 0; this.busy = false;
  }
  snap() { return JSON.stringify(keys); }
  seed() { if (this.last === null) { this.last = this.snap(); this.lastLen = keys.length; } }
  reset() { this.past = []; this.future = []; this.last = this.snap(); this.lastLen = keys.length; this.refresh(); }
  changed() {                           // called by bumpKeys after every edit
    if (this.busy) return;
    const now = this.snap();
    if (this.last === null || now === this.last) { this.last = now; this.lastLen = keys.length; return; }
    const t = Date.now();
    const sameStep = this.past.length && keys.length === this.lastLen && t - this.lastAt < this.COALESCE_MS;
    if (!sameStep) {
      this.past.push(this.last);
      if (this.past.length > this.MAX) this.past.shift();
    }
    this.future = [];
    this.last = now; this.lastLen = keys.length; this.lastAt = t;
    this.refresh();
  }
  undo() { if (this.past.length) { this.future.push(this.snap()); this.apply(this.past.pop()); } }
  redo() { if (this.future.length) { this.past.push(this.snap()); this.apply(this.future.pop()); } }
  apply(snapshot) {
    const before = keys;
    this.busy = true;
    try {
      keys = JSON.parse(snapshot);
      this.last = snapshot; this.lastLen = keys.length; this.lastAt = 0;
      // select the first keyframe that differs, so the change is where the eye goes
      let at = 0;
      while (at < keys.length - 1 && before[at] && JSON.stringify(before[at]) === JSON.stringify(keys[at])) at++;
      selKey = Math.max(0, Math.min(at, keys.length - 1));
      clearBadMarks();
      bumpKeys();
      renderTimeline();
      if (keys.length) selectKey(selKey);
    } finally { this.busy = false; }
    this.refresh();
  }
  refresh() {
    const u = $("undoBtn"), r = $("redoBtn");
    if (u) u.disabled = !this.past.length;
    if (r) r.disabled = !this.future.length;
  }
}
var timelineUndo = new TimelineUndo();
// Ctrl+Z / Ctrl+Y (Cmd on a Mac). A text box keeps its own undo.
window.addEventListener("keydown", (e) => {
  if (!(e.ctrlKey || e.metaKey) || e.altKey) return;
  const t = e.target, tag = t && t.tagName;
  if (tag === "TEXTAREA" || tag === "SELECT" || (tag === "INPUT" && !/^(range|checkbox|button)$/.test(t.type))) return;
  const k = e.key.toLowerCase();
  if (k === "z" && !e.shiftKey) timelineUndo.undo();
  else if (k === "y" || (k === "z" && e.shiftKey)) timelineUndo.redo();
  else return;
  e.preventDefault();
});
