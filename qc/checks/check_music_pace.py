"""Speed limit with music and the real-servo picture (A48-23, A48-24).

User 2026-10-27: the cheer dances ran 3.9x slower than their songs because
every move was capped at the 60 deg/s safety limit. A sequence that follows
its song now has its OWN limit, set in Studio and tuned by the user ("ขอแบบ
ปรับได้ เดี๋ยวดูเอง"): empty = the robot's music_dps, 0 = the servos' top
speed. It is written into the file as `pace: music N` (the board's PACE MUSIC
N, for that file only) and the moves that cannot keep up at the chosen limit
are listed, clickable, with how far each falls behind the song.

Held here, in the real Studio page:

* with no song the limit row is hidden and moves keep the safety limit;
* with a song, limit 60 makes the fast move longer than its moment in the
  song and lists it; the button selects it; back to empty (robot: servos'
  top speed) gives the song's own time back - nothing stays stretched;
* the file says `pace: music 120` for a limit of 120, a bare `pace: music`
  for the robot's own, and `pace: normal` at its end;
* the real servos (delay, speed-up, top speed per joint on the rig) trail a
  fast move by more than the bad line and a slow one by less than the warn
  line; a longer delay on the rig trails further; the fast chip is marked;
* "Play like the real servos" shows the horns behind the plan.
"""
import browser
import fake_serial
import qc as F

AREA = "studio"
TITLE = "speed limit with music, moves that cannot keep up, real-servo lag"
SLOW = True

DRIVER = """
function report(s){ qcMark("MP~" + s); }
window.addEventListener("load", function(){ qcWaitFor(function(){
    return typeof musicPace === "object" && typeof ServoFollow === "function"
           && document.getElementById("musicDpsSeq") && typeof buildYaml === "function";
  }, 20000).then(function(ready){
  if (!ready) { report("ERR-the-app-never-finished-loading"); report("done"); return; }
  try{
    var o = {};
    var a = RIG.home.slice(), b = a.slice();
    b[0] = clampJ(0, a[0] + 60);
    function setKeys(song){
      keys = [{pose: a.slice(), t: 0, hold: 0, cues: song ? ["play: qc_song.mp3"] : []},
              {pose: b.slice(), t: 300, hold: 0, tset: true, musicMs: 300}];
      bumpKeys(); renderTimeline();
    }
    MUSIC_DPS = 0; SEQ_MUSIC_DPS = null;
    setKeys(false);
    o.normalHidden = document.getElementById("musicPaceRow").hidden;
    o.normalMin = minTime(a, b);
    setKeys(true);
    o.musicShown = !document.getElementById("musicPaceRow").hidden;
    o.freeLate = musicPace.late().length;
    var box = document.getElementById("musicDpsSeq");
    box.value = "60"; musicPace.changed();
    o.at60 = keys[1].t; o.late60 = musicPace.late().length;
    o.buttons = document.querySelectorAll("#musicFitList button").length;
    o.stat60 = /behind the song/.test(document.getElementById("musicFitStat").textContent);
    var btn = document.querySelector("#musicFitList button");
    if (btn) btn.click();
    o.selected = selKey;
    box.value = "120"; musicPace.changed();
    var y120 = buildYaml().yaml;
    o.cue120 = /- pace: music 120/.test(y120);
    o.endNormal = /- pace: normal\\s*$/.test(y120.trim() + "\\n") || /- pace: normal/.test(y120.split("\\n").slice(-4).join("\\n"));
    // a file read back with its own number keeps it when exported untouched
    SEQ_MUSIC_DPS = null; keys[0].cues = ["play: qc_song.mp3", "pace: music 50"]; bumpKeys();
    o.keeps50 = /- pace: music 50/.test(buildYaml().yaml) && musicPace.cap() === 50;
    // a project reopened with its own limit wins over an older cue in the moves
    SEQ_MUSIC_DPS = 80;
    var y80 = buildYaml().yaml;
    o.projectWins = /- pace: music 80/.test(y80) && !/- pace: music 50/.test(y80);
    box.value = "120"; musicPace.changed();
    o.cueFollows = keys[0].cues.indexOf("pace: music 120") >= 0;
    keys[0].cues = ["play: qc_song.mp3"]; bumpKeys();
    box.value = ""; musicPace.changed();
    o.backTo = keys[1].t; o.lateFree = musicPace.late().length;
    o.bareCue = /- pace: music\\s*\\n/.test(buildYaml().yaml);
    // the real servos
    var far = a.slice(); far[2] = clampJ(2, a[2] + 90);
    var fast = ServoFollow.trace([{pose: a, t: 0, hold: 0}, {pose: far, t: 160, hold: 0}]).worst.deg;
    var slow = ServoFollow.trace([{pose: a, t: 0, hold: 0}, {pose: far, t: 4000, hold: 0}]).worst.deg;
    var keep = RIG.servoLagMs.slice();
    RIG.servoLagMs = keep.map(function(v){ return v * 4; });
    var later = ServoFollow.trace([{pose: a, t: 0, hold: 0}, {pose: far, t: 160, hold: 0}]).worst.deg;
    RIG.servoLagMs = keep;
    o.fast = fast.toFixed(1); o.slow = slow.toFixed(1); o.later = later.toFixed(1);
    o.bad = SERVO_VIEW.badDeg; o.warn = SERVO_VIEW.warnDeg;
    keys = [{pose: a.slice(), t: 0, hold: 0}, {pose: far, t: 160, hold: 0, tset: true}];
    bumpKeys(); renderTimeline();
    o.chipMarked = document.querySelectorAll("#keys .key")[1].classList.contains("lagbad");
    o.servoStat = /behind/.test(document.getElementById("servoStat").textContent);
    document.getElementById("servoView").checked = true; servoPlay = null;
    servoPlayPose(a, 20); var horn = servoPlayPose(far, 20);
    o.hornBehind = (far[2] - horn[2]).toFixed(1);
    document.getElementById("servoView").checked = false;
    o.offPlain = servoPlayPose(far, 20)[2] === far[2];
    // settle: the plan turns a corner, the lagging horns cut it into a part
    // of the robot (a stand-in obstacle where only the cut corner passes)
    var A = RIG.home.slice(), B = A.slice(), C = A.slice();
    B[2] = clampJ(2, A[2] + 60); C[2] = B[2]; C[3] = clampJ(3, A[3] + 60);
    var d2 = B[2] - A[2], d3 = C[3] - A[3], realHit = collisionAt;
    collisionAt = function(p){ var u = (p[2] - A[2]) / d2, v = (p[3] - A[3]) / d3;
      return u > 0.85 && u < 0.985 && v > 0.02 && v < 0.15; };
    var K = [{pose: A, t: 0, hold: 0}, {pose: B, t: 200, hold: 0}, {pose: C, t: 200, hold: 0}];
    o.planClear = [0.25, 0.5, 0.75].every(function(f){
      return !collisionAt(A.map(function(x, j){ return x + (B[j] - x) * f; })) &&
             !collisionAt(B.map(function(x, j){ return x + (C[j] - x) * f; })); });
    o.cutHits = ServoFollow.trace(K, {hits: true}).moves.some(function(m){ return m.hitMs; });
    o.settled = ServoFollow.settle(K);
    o.afterHits = ServoFollow.trace(K, {hits: true}).moves.some(function(m){ return m.hitMs; });
    o.longer = K[1].t + K[2].t > 400;
    collisionAt = realHit;
    report(Object.keys(o).map(function(k){ return k + "=" + o[k]; }).join("~"));
    report("done");
  }catch(e){ report("ERR-" + String(e && e.stack || e).slice(0,160).replace(/~/g, "_")); report("done"); }
}); });
"""


def run(t):
    if not browser.available():
        t.give_up("headless Edge not found - this needs a real browser")
    fake_serial.reset()
    base, _main = F.start_hub()
    browser.page(DRIVER, query="%s/studio/_qcdriver.html?dev=usb%%3A%s"
                 % (base, fake_serial.PORT), seconds=60)
    marks = [m[3:] for m in fake_serial.qc_marks if m.startswith("MP~")]
    bad = [m for m in marks if m.startswith("ERR-")]
    if not t.ok(not bad, "the driver ran without throwing", bad[:1]):
        return
    got = next((m for m in marks if m.startswith("normalHidden=")), "")
    if not t.ok(got, "the driver measured the page", marks):
        return
    v = dict(kv.split("=", 1) for kv in got.split("~"))
    print("   measured:", v)
    t.ok(v["normalHidden"] == "true", "no song: the music limit row is hidden", v)
    t.ok(int(v["normalMin"]) > 1000, "and a 60 deg move keeps the safety limit (%s ms)" % v["normalMin"], v)
    t.ok(v["musicShown"] == "true" and v["freeLate"] == "0",
         "with a song and the servos' top speed, the 300 ms move keeps up", v)
    t.ok(int(v["at60"]) > 1000 and v["late60"] == "1" and v["stat60"] == "true",
         "limit 60: the move is stretched to %s ms and listed as behind the song" % v["at60"], v)
    t.ok(v["buttons"] == "1" and v["selected"] == "1", "the listed move is a button that selects it", v)
    t.ok(v["cue120"] == "true" and v["endNormal"] == "true",
         "limit 120 is written as pace: music 120 and the file ends with pace: normal", v)
    t.ok(v["keeps50"] == "true", "a file read back with pace: music 50 keeps its 50 when exported", v)
    t.ok(v["projectWins"] == "true", "a reopened project's own limit is what the file says", v)
    t.ok(v["cueFollows"] == "true", "and a new limit in the box rewrites that cue", v)
    t.ok(v["backTo"] == "300" and v["lateFree"] == "0",
         "back to the robot's own limit: the song's 300 ms comes back (%s)" % v["backTo"], v)
    t.ok(v["bareCue"] == "true", "and the file says a bare pace: music", v)
    t.ok(float(v["fast"]) > float(v["bad"]), "the real servos trail a 90 deg move in 160 ms "
         "by more than the bad line (%s deg)" % v["fast"], v)
    t.ok(float(v["slow"]) < float(v["warn"]), "and a 4 s one by less than the warn line (%s deg)" % v["slow"], v)
    t.ok(float(v["later"]) > float(v["fast"]), "a longer delay on the rig trails further (%s deg)" % v["later"], v)
    t.ok(v["chipMarked"] == "true" and v["servoStat"] == "true",
         "the fast move's chip is marked and the status line says the servos fall behind", v)
    t.ok(float(v["hornBehind"]) > 10, "Play like the real servos shows the horn %s deg behind" % v["hornBehind"], v)
    t.ok(v["offPlain"] == "true", "and unticked it shows the plan itself", v)
    t.ok(v["planClear"] == "true" and v["cutHits"] == "true",
         "a corner the plan turns cleanly is cut by the lagging horns into the robot", v)
    t.ok(int(v["settled"]) > 0 and v["afterHits"] == "false" and v["longer"] == "true",
         "settle lengthens those moves until the horns pass clear (%s moves)" % v["settled"], v)
