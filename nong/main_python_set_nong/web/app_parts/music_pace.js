// --- speed limit with music (A48-23) ---
// User 2026-10-27: a show that follows its song may run faster than the 60 °/s
// safety cap, set PER SEQUENCE and tuned by the user, who then cuts, adds or
// changes the moves that still cannot keep up. One number per sequence:
// empty = the robot's own music_dps, 0 = only the servos' top speed. It is
// saved in the project and written into the file as `pace: music N`, which
// the board obeys for that file only (PACE MUSIC N, NongModule.cpp).
const musicPace = {
  // the cap a list K follows its music at
  cap(K = keys) {
    if (SEQ_MUSIC_DPS != null) return SEQ_MUSIC_DPS;
    for (const k of K) {
      const m = /^music\s+(\d+(?:\.\d+)?)/i.exec(keyCue(k, "pace") || "");
      if (m) return +m[1];
    }
    return MUSIC_DPS;
  },
  cue() { return "pace: music" + (SEQ_MUSIC_DPS != null ? " " + SEQ_MUSIC_DPS : ""); },
  // the value in the box, then every pace cue and every music-timed move follow it
  changed() {
    const raw = ($("musicDpsSeq").value || "").trim(), v = Math.round(+raw);
    SEQ_MUSIC_DPS = raw === "" || !(v >= 0) ? null : v > 0 && v < 5 ? 5 : Math.min(v, Math.round(slowestDps()));
    $("musicDpsSeq").value = SEQ_MUSIC_DPS == null ? "" : SEQ_MUSIC_DPS;
    keys.forEach(k => {
      if (k.cues) k.cues = k.cues.map(c => /^pace:\s*music/i.test(c) ? this.cue() : c);
    });
    this.retime();
    renderTimeline();
  },
  // A move timed by the song gets back the song's time when the cap allows
  // it, and only as much more as the servos need when it does not.
  retime() {
    bumpKeys();
    keys.forEach((k, i) => { if (k.musicMs > 0) k.t = Math.max(k.musicMs, keyMin(i)); });
  },
  // the moves that cannot keep up at this cap: [{i, behindMs, why}]
  late() {
    if (planPace() !== "music") return [];
    const out = [];
    keys.forEach((k, i) => {
      if (k.off || !(i > 0)) return;
      const want = k.musicMs > 0 ? k.musicMs : null;
      if (want == null) return;
      const w = minTimeWhy(keys[i - 1].pose, k.pose);
      if (w.ms > want + 10) out.push({ i, behindMs: w.ms - want, why: w.why });
    });
    return out;
  },
  render() {
    const row = $("musicPaceRow");
    if (!row) return;
    const music = planPace() === "music";
    row.hidden = !music;
    $("musicFitStat").hidden = !music;
    const list = $("musicFitList");
    list.innerHTML = "";
    if (!music) return;
    if (document.activeElement !== $("musicDpsSeq"))
      $("musicDpsSeq").value = SEQ_MUSIC_DPS == null ? "" : SEQ_MUSIC_DPS;
    $("musicDpsSeq").placeholder = MUSIC_DPS > 0 ? String(MUSIC_DPS) : "robot";
    const cap = this.cap(), late = this.late();
    const at = cap > 0 ? `${cap} °/s` : "the servos' top speed";
    if (!late.length) { $("musicFitStat").textContent = `Every move keeps up with the song at ${at}.`; return; }
    const behind = late.reduce((s, x) => s + x.behindMs, 0);
    $("musicFitStat").textContent = `${late.length} move(s) cannot keep up with the song at ${at}; ` +
      `the show ends ${(behind / 1000).toFixed(1)} s after the music. Raise the limit, or click a move to ` +
      "shorten, change or remove it.";
    late.slice(0, 40).forEach(x => {
      const b = document.createElement("button");
      b.className = "secondary mini";
      b.textContent = `${keys[x.i].name || "move " + x.i} +${(x.behindMs / 1000).toFixed(2)} s`;
      b.title = "held back by " + x.why;
      b.onclick = () => selectKey(x.i);
      list.appendChild(b);
    });
  },
};
