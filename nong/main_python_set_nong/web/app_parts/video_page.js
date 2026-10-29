// --- the Video page (A44-8) ---
// User 2026-10-19: a page of its own for moves from a video - the person with
// their music, the skeleton found on them and the robot moving beside them,
// in step - that takes YouTube, Google Drive and other links too, and whose
// moves and choices are Studio's own (the same time bar, the same saved file).
// It is the Video tab: while it is open the person shares the screen with the
// 3D view. The robot beside the video is a PREVIEW: nothing is sent to a board
// until the moves are on the time bar and played from there.
// Links are fetched by the hub (main_python/hub_video.py): a browser cannot
// read the picture of a video another site plays.
let vidSrc = null;          // what is on the stage: { kind: "file"|"link", name, url, id, file }
let vidFetchId = null, vidLinkBusy = false;
let vidHeld = null;         // the editor's pose, given back when the page closes
let vidView = "iso";        // the 3D view it had, given back too
let vidLastMs = -1, vidOn = false, vidFirstKey = -1;
let vidSaved = null;        // the video choices the open project was saved with
const VID_LOGIN = "Log in first (the Robot tab has the login): a link is fetched onto this PC.";

function vidPage(on) {
  if (on === vidOn) return;
  vidOn = on;
  document.body.classList.toggle("vidpage", on);
  const v = $("vidPlayer");
  if (on) {
    vidFill();
    vidHeld = pose.slice();
    vidLastMs = -1;
    // From the front the robot faces you as the person faces the camera, so
    // the two read the same way round.
    const cur = document.querySelector("#viewCube [data-view].on");
    vidView = cur ? cur.dataset.view : "iso";
    setView("front");
    requestAnimationFrame(vidTick);
    return;
  }
  vidGeneration++; if (vidBusy) vidStop = true;
  if (vidSeekCancel) vidSeekCancel();
  vidCheckedPlayback.reset(v);
  if (v && !v.paused) v.pause();
  // The page drew the video's poses on the editor's robot; give it back.
  if (vidHeld) { pose = vidHeld; applyPose(); renderSliders(); }
  vidHeld = null;
  setView(vidView);
}

// A video for the stage, from a file or a fetched link.
function vidSetSrc(url, src) {
  vidGeneration++;
  if (vidSeekCancel) vidSeekCancel();
  if (vidBusy) vidStop = true;
  const v = $("vidPlayer");
  vidCheckedPlayback.reset(v);
  const keepSaved = !!(vidSaved?.src?.url && src.url && vidSaved.src.url === src.url);
  if (!keepSaved) {
    vidSaved = null;
    $("vidRoutine").innerHTML = '<option value="auto">Find routines automatically</option>';
    $("vidRoutine").value = "auto";
    $("vidDancer").innerHTML = '<option value="auto">Automatic — discover dance groups</option>';
    $("vidDancer").value = "auto";
  }
  if (v.src && v.src.startsWith("blob:")) URL.revokeObjectURL(v.src);
  vidSrc = src;
  v.src = url;
  v.hidden = false;
  $("vidEmpty").hidden = true;
  vidFrames = null; vidMade = null; vidFit = null; vidPicks = null; vidRoutines = []; vidRoutineRange = null;
  vidList();
  vidDraw(null);
  $("vidUseBox").hidden = true;
  $("vidSoundBox").hidden = true;
  $("vidGo").disabled = false;
  $("vidGoSave").disabled = false;
  $("vidPlayBtn").disabled = false;
  $("vidTech").textContent = "";
  vidLastMs = -1;
  v.onloadedmetadata = () => {
    // a reopened project's part of the video is kept; a new video uses all of it
    const keep = keepSaved && vidSaved;
    $("vidFrom").value = keep ? String(vidSaved.from || 0) : "0";
    $("vidTo").value = keep && vidSaved.to ? String(vidSaved.to) : v.duration.toFixed(1);
    vidSay("Ready: " + v.duration.toFixed(1) + " s of video. Press Make moves.");
  };
  v.onerror = () => vidSay("This browser cannot play that video. Try an MP4 or WEBM file.", true);
  v.onended = v.onpause = () => { $("vidPlayBtn").textContent = "▶ Play person and robot"; };
  v.onplay = () => { $("vidPlayBtn").textContent = "❚❚ Pause"; };
}

// A link: the hub fetches it onto this PC and says how far it has got.
async function vidFetch() {
  if (vidLinkBusy) {                      // the button is Stop while it fetches
    if (vidFetchId) await Mice.Api.post("/api/video/fetch", { cancel: vidFetchId });
    return;
  }
  const url = $("vidLink").value.trim();
  if (!/^https?:\/\/\S+$/i.test(url)) {
    vidSay("Paste a whole link, starting with https://", true);
    return;
  }
  vidLinkBusy = true;
  $("vidFetchBtn").textContent = "■ Stop";
  $("vidTech").textContent = "";
  try {
    vidSay("Asking this PC to fetch the video…");
    let a = await Mice.Api.post("/api/video/fetch", { url });
    if (!a.ok) {
      vidSay(a.needLogin ? VID_LOGIN : "The link could not be fetched: " + a.says, true);
      $("vidTech").textContent = a.tech || "";
      return;
    }
    vidFetchId = a.data.id;
    let st = a.data;
    while (st.state === "working") {
      vidSay("Fetching the video onto this PC" + (st.how ? " (" + st.how + ")" : "")
             + ": " + (st.pct || 0) + "%" + (st.title ? " · " + st.title : ""));
      await new Promise(r => setTimeout(r, 700));
      a = await Mice.Api.get("/api/video/fetch?id=" + encodeURIComponent(vidFetchId));
      if (!a.ok) { vidSay(a.says, true); return; }
      st = a.data;
    }
    if (st.state !== "done") {
      vidSay(st.error || "The link could not be fetched.", st.error !== "Stopped.");
      $("vidTech").textContent = st.tech || "";
      return;
    }
    vidSetSrc("/api/video/file?id=" + encodeURIComponent(vidFetchId),
              { kind: "link", url, id: vidFetchId, name: st.title || "video" });
  } finally {
    vidLinkBusy = false;
    $("vidFetchBtn").textContent = "Fetch";
  }
}

// ---- the person and the robot, in step ------------------------------------
function vidPlayBoth() {
  const v = $("vidPlayer");
  if (!v.src) return;
  if (vidCheckedPlayback.manual) { vidCheckedPlayback.pause(v); return; }
  if (!v.paused) { v.pause(); return; }
  const from = +$("vidFrom").value || 0, to = +$("vidTo").value || v.duration;
  if (v.currentTime < from || v.currentTime >= to - 0.05) v.currentTime = from;
  v.muted = false;
  if (vidMade?.keepMusic === false && vidMade.keys.length) {
    const mapped = VideoRigFitter.clockForSource(vidMade.keys, (v.currentTime - from) * 1000);
    if (mapped.rate < 0.0625) { vidCheckedPlayback.start(v, mapped.ms); return; }
    v.playbackRate = Math.min(4, mapped.rate);
  }
  v.play().catch(e => vidSay("The video would not play: " + (e.message || e), true));
}
// Every frame while the page is open: the robot takes the made moves' pose at
// the video's moment and the skeleton its frame, whether the video plays or
// is dragged along. Nothing changes while the video stands still, so a click
// on a move's row (vidSee) is not overwritten.
function vidTick() {
  if (!vidOn) return;
  requestAnimationFrame(vidTick);
  const v = $("vidPlayer");
  if (!v.src || !isFinite(v.duration) || vidBusy || playing) return;
  const from = +$("vidFrom").value || 0, to = +$("vidTo").value || v.duration;
  if (!v.paused && v.currentTime >= to) v.pause();
  let ms = Math.round((v.currentTime - from) * 1000);
  ms = vidCheckedPlayback.update(v, vidMade, ms, from, (to - from) * 1000);
  if (ms === vidLastMs && !vidCheckedPlayback.manual) return;
  vidLastMs = ms;
  vidShowAt(ms, vidCheckedPlayback.robotMs);
}
function vidShowAt(ms, checkedMs = null) {
  if (vidFrames && vidFrames.length) {
    const f = vidFrames[Math.max(0, Math.min(vidFrames.length - 1, Math.round(ms * VID_FPS / 1000)))];
    vidDraw($("vidSkel").checked && ms >= 0 ? f.p : null);
  }
  if (vidMade && vidMade.keys.length && ms >= 0) {
    pose = easeKeys(vidMade.keys, checkedMs ?? VideoRigFitter.clockForSource(vidMade.keys, ms).ms, "video").pose;
    applyPose();
  }
  $("vidClock").textContent = ms >= 0 ? (ms / 1000).toFixed(1) + " s" : "";
}

// ---- after "Use as new moves": the moves are Studio's own ------------------
function vidOnBar(first) {
  vidFirstKey = first;
  vidHeld = null;                 // the time bar's pose is the editor's now
  $("vidSoundBox").hidden = !vidSrc;
}
// The video's sound as the music of the first video move: the hub cuts the
// same part the moves were made from (ffmpeg) and it goes onto the robot's
// card the way any track does (uploadMusicFile). A picked file is copied to
// the hub first; a link is already there.
async function vidSound() {
  if (vidMade?.keepMusic === false && vidMade.keys.length) {
    const last = vidMade.keys.at(-1), end = last.sourceHoldEnd ?? last.sourceMs;
    const timed = VideoRigFitter.clockForSource(vidMade.keys, end).ms;
    if (Number.isFinite(end) && timed > end - (vidMade.keys[0].sourceMs || 0) + 2) {
      vidSay("These moves use a slower clock. The original sound would be out of step; use a retimed music file for this show.", true);
      return;
    }
  }
  const k = keys[vidFirstKey];
  if (!vidSrc || !k) return;
  if (!haveRobot()) {
    vidSay("Connect the robot first (Robot tab): the music goes onto its card.", true);
    return;
  }
  const btn = $("vidSoundBtn");
  btn.disabled = true;
  try {
    if (!vidSrc.id && vidSrc.file) {
      vidSay("Copying the video to this PC's hub for its sound…");
      const r = await fetch("/api/video/put?name=" + encodeURIComponent(vidSrc.name),
                            { method: "POST", body: vidSrc.file }).catch(() => null);
      const j = r ? await r.json().catch(() => ({})) : {};
      if (!r || !j.ok) {
        vidSay(j.need_login ? VID_LOGIN : "The video could not be copied: "
               + (j.error || "the hub is not answering"), true);
        return;
      }
      vidSrc.id = j.id;
    }
    vidSay("Taking the sound out of the video…");
    const from = (+$("vidFrom").value || 0) + (vidMade ? vidMade.start / 1000 : 0);
    const a = await Mice.Api.post("/api/video/sound",
                                  { id: vidSrc.id, from, to: +$("vidTo").value || 0 });
    if (!a.ok) { vidSay(a.needLogin ? VID_LOGIN : a.says, true); return; }
    const r = await fetch("/api/video/file?kind=sound&id=" + encodeURIComponent(vidSrc.id));
    if (!r.ok) { vidSay("The sound was made but could not be read back.", true); return; }
    const name = robotTrackName((vidSrc.name || "video").replace(/\.[^.]*$/, "").slice(0, 40) + ".mp3");
    await uploadMusicFile(k, new File([await r.blob()], name, { type: "audio/mpeg" }), Object.assign(
      (track, why, renamed) => {
        if (!track) { vidSay("The sound did not reach the robot: " + why, true); return; }
        setCueTrack(k, track, false);
        renderTimeline();
        vidSay("♪ " + track + " is on the robot's card and plays with the first video move"
               + (renamed || "") + ". Save to keep it.");
      }, { busy: (t) => vidSay(t) }));
  } finally { btn.disabled = false; }
}

// ---- the choices ride in the project file -----------------------------------
// Saved with the moves, so a reopened project knows its video and how its
// moves were made; the video itself is not saved (a link is fetched again).
function vidSettings() {
  if (!vidSrc) return vidSaved;
  return { src: { kind: vidSrc.kind, name: vidSrc.name, url: vidSrc.url || "" },
           subjectMode: $("vidSubject")?.value || "auto", cameraMode: $("vidCamera")?.value || "auto",
           routine: $("vidRoutine")?.value || "auto", routineSummary: typeof vidRoutines !== "undefined" ? vidRoutines.map(r => ({ id: r.id, kind: r.kind, sourceStart: r.sourceStart, sourceEnd: r.sourceEnd, coverage: r.coverage, trustedCoverage: r.trustedCoverage, ambiguous: r.ambiguous })) : [],
           dancer: $("vidDancer")?.value || "auto", shrug: !!$("vidShrug")?.checked,
           anchorX: Number.isFinite(vidSaved?.anchorX) ? vidSaved.anchorX : 0.5,
           analysis: vidMade?.achieved ? { meanBoneDegrees: vidMade.achieved.meanBoneDegrees,
             worstBoneDegrees: vidMade.achieved.worstBoneDegrees, corrected: vidMade.safe.around,
             uncertain: vidMade.quality?.uncertain || 0, limited: vidMade.partial } : null,
           learned: $("vidLearned")?.checked !== false,
           detail: $("vidDetail").value, mirror: $("vidMirror").checked,
           music: $("vidMusic").checked, waist: $("vidWaist").checked,
           hand: [$("vidHand0").value, $("vidHand1").value],
           from: +$("vidFrom").value || 0, to: +$("vidTo").value || 0 };
}
function vidApplySettings(s) {
  vidSaved = s && typeof s === "object" ? s : null;
  if (!vidSaved) return;
  vidFill();
  const pick = (sel, id) => { if (sel && [...sel.options].some(o => o.value === id)) sel.value = id; };
  pick($("vidDetail"), s.detail);
  pick($("vidSubject"), s.subjectMode || "auto");
  pick($("vidCamera"), s.cameraMode || "auto");
  if ($("vidShrug")) $("vidShrug").checked = !!s.shrug;
  if ($("vidLearned")) $("vidLearned").checked = s.learned !== false;
  if ($("vidDancer")) {
    if (s.dancer && ![...$("vidDancer").options].some(o => o.value === s.dancer))
      $("vidDancer").add(new Option("Performer " + s.dancer, s.dancer));
    $("vidDancer").value = s.dancer || "auto";
    if ($("vidDancer").options[0]) $("vidDancer").options[0].text = Number.isFinite(s.anchorX) && s.anchorX !== 0.5 ? "Saved reference" : "Main performer";
  }
  if ($("vidRoutine")) {
    if (s.routine && ![...$("vidRoutine").options].some(o => o.value === s.routine)) $("vidRoutine").add(new Option("Saved routine " + s.routine, s.routine));
    $("vidRoutine").value = s.routine || "auto";
  }
  (s.hand || []).forEach((h, a) => pick($("vidHand" + a), h));
  $("vidMirror").checked = !!s.mirror;
  $("vidMusic").checked = s.music === true;
  $("vidWaist").checked = !!s.waist;
  $("vidFrom").value = String(s.from || 0);
  if (s.to) $("vidTo").value = String(s.to);
  if (s.src && s.src.url) $("vidLink").value = s.src.url;
  if (s.src) vidSay("These moves were made from " + (s.src.url ? "a link: press Fetch to see it again."
    : "the file " + s.src.name + ": pick it again to see it."));
}
