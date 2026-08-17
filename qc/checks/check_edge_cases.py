"""Edge cases: empty, all-suspended, first/last suspended, one keyframe left.

Normal use is well covered elsewhere. This is the awkward stuff a user reaches
by accident — suspending everything, suspending the start pose, a timeline with
one active keyframe — where a function that assumes "there is always a previous
keyframe" throws or writes a file with no moves in it.
"""
import browser
import fake_serial
import qc as F

AREA = "edge cases"
TITLE = "empty / all-suspended / first / last"
SLOW = True

DRIVER = """
function report(tag, fn){
  try { qcMark(tag + "-" + fn()); }
  catch(e){ qcMark(tag + "-THREW:" + String(e.message||e).replace(/[^A-Za-z0-9]/g,"_").slice(0,40)); }
}
function step(){
  try{
    if (typeof playKeys !== "function") return setTimeout(step, 200);
    if (!haveUsb()) return setTimeout(step, 300);
    qcMark("connected");

    keys = [];
    [40, 80, 120].forEach(function(v){
      pose = pose.map(function(){ return v; });
      addKey();
    });

    // ---- every keyframe suspended --------------------------------
    keys.forEach(function(k){ k.off = true; });
    report("ALL_PLAY",  function(){ return playKeys().length; });
    report("ALL_TOTAL", function(){ return totalMs(); });
    report("ALL_POSE",  function(){ return poseAt(0).length; });
    report("ALL_SEG",   function(){ return segmentAt(0); });
    report("ALL_YAML",  function(){
      var y = buildYaml().yaml;
      return /- pose:/.test(y) ? "has-poses" : "no-poses";
    });
    report("ALL_COLL",  function(){ return checkCollisions(false).length; });
    report("ALL_RENDER", function(){ renderTimeline(); return "ok"; });
    // a poseless file must be REFUSED, not written to the card
    report("ALL_EXPORT", function(){
      document.getElementById("tlStat").textContent = "";
      exportYaml();
      return /suspended/.test(document.getElementById("tlStat").textContent)
        ? "refused" : "wrote-it";
    });
    report("ALL_UPLOAD", function(){
      document.getElementById("sdStat").textContent = "";
      uploadYaml();
      return /suspended/.test(document.getElementById("sdStat").textContent)
        ? "refused" : "wrote-it";
    });

    // ---- only the START pose suspended ---------------------------
    keys.forEach(function(k){ delete k.off; });
    keys[0].off = true;
    report("K0_PLAY",  function(){ return playKeys().map(function(k){ return Math.round(k.pose[0]); }).join("_"); });
    report("K0_TOTAL", function(){ return totalMs() > 0 ? "positive" : totalMs(); });
    report("K0_POSE",  function(){ return Math.round(poseAt(0)[0]); });
    report("K0_YAML",  function(){ return (buildYaml().yaml.match(/- pose:/g)||[]).length; });

    // ---- only the LAST suspended ---------------------------------
    keys.forEach(function(k){ delete k.off; });
    keys[keys.length - 1].off = true;
    report("KL_PLAY",  function(){ return playKeys().length; });
    report("KL_END",   function(){ return Math.round(poseAt(totalMs() + 5000)[0]); });

    // ---- exactly ONE active keyframe -----------------------------
    keys.forEach(function(k){ k.off = true; });
    delete keys[1].off;
    report("ONE_PLAY", function(){ return playKeys().length; });
    report("ONE_TOTAL", function(){ return totalMs(); });
    report("ONE_POSE", function(){ return Math.round(poseAt(0)[0]); });
    report("ONE_SEG",  function(){ return segmentAt(0); });
    report("ONE_PLAYBTN", function(){ togglePlay(); var p = playing; playing = false; return p ? "started" : "refused"; });

    // ---- no keyframes at all -------------------------------------
    keys = [];
    report("NONE_PLAY",  function(){ return playKeys().length; });
    report("NONE_TOTAL", function(){ return totalMs(); });
    report("NONE_POSE",  function(){ return poseAt(0).length; });
    report("NONE_SEG",   function(){ return segmentAt(0); });
    report("NONE_REM",   function(){ return segRemaining(0); });
    report("NONE_RENDER", function(){ renderTimeline(); return "ok"; });
    report("NONE_COLL",  function(){ return checkCollisions(false).length; });
    qcMark("done");
  }catch(e){ qcFail(e); }
}
window.addEventListener("load", function(){ setTimeout(step, 1200); });
"""


def run(t):
    if not browser.available():
        t.give_up("headless Edge not found — run --quick")
    fake_serial.reset()
    base, main = F.start_hub()
    browser.page(DRIVER, query="%s/studio/_qcdriver.html?dev=usb%%3A%s"
                 % (base, fake_serial.PORT), seconds=22)

    marks = fake_serial.qc_marks
    t.contains(marks, "connected", "the editor loaded")
    t.contains(marks, "done", "it survived every edge case without hanging")
    got = {m.split("-", 1)[0]: m.split("-", 1)[1] for m in marks if "-" in m}

    # nothing may throw — a thrown error stops the animation loop dead
    threw = sorted(k for k, v in got.items() if str(v).startswith("THREW"))
    t.eq(threw, [], "no edge case throws: " + repr({k: got[k] for k in threw}))

    # ---- everything suspended ------------------------------------
    t.eq(got.get("ALL_PLAY"), "0", "all suspended: nothing plays")
    t.eq(got.get("ALL_TOTAL"), "0", "all suspended: the run is zero long")
    t.eq(got.get("ALL_SEG"), "-1", "all suspended: no segment is running")
    t.eq(got.get("ALL_COLL"), "0", "all suspended: nothing can collide")
    t.eq(got.get("ALL_YAML"), "no-poses",
         "all suspended: such a file would carry no poses at all")
    t.eq(got.get("ALL_EXPORT"), "refused",
         "all suspended: Export refuses instead of writing a file with no moves")
    t.eq(got.get("ALL_UPLOAD"), "refused",
         "all suspended: Upload refuses instead of putting a do-nothing file on the card")

    # ---- the start pose suspended --------------------------------
    t.eq(got.get("K0_PLAY"), "80_120", "keyframe 0 suspended: the rest still plays")
    t.eq(got.get("K0_TOTAL"), "positive", "and the run still has a length")
    t.eq(got.get("K0_POSE"), "80", "playback starts from the new first keyframe")
    t.eq(got.get("K0_YAML"), "2", "the file carries the remaining poses")

    # ---- the last suspended --------------------------------------
    t.eq(got.get("KL_PLAY"), "2", "last suspended: the rest still plays")
    t.eq(got.get("KL_END"), "80", "the run ends on the new last keyframe")

    # ---- exactly one active --------------------------------------
    t.eq(got.get("ONE_PLAY"), "1", "one active keyframe is a valid state")
    t.eq(got.get("ONE_TOTAL"), "0", "with nothing to move to, the run is zero long")
    t.eq(got.get("ONE_POSE"), "80", "and the pose is that keyframe")
    t.eq(got.get("ONE_PLAYBTN"), "refused",
         "Play refuses one keyframe instead of starting an empty run")

    # ---- no keyframes --------------------------------------------
    t.eq(got.get("NONE_PLAY"), "0", "empty timeline: nothing plays")
    t.eq(got.get("NONE_TOTAL"), "0", "empty timeline: zero length")
    t.eq(got.get("NONE_SEG"), "-1", "empty timeline: no segment")
    t.eq(got.get("NONE_REM"), "0", "empty timeline: nothing remaining")
    t.eq(got.get("NONE_COLL"), "0", "empty timeline: nothing collides")
