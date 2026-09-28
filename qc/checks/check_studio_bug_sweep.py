"""Five Studio editor bugs found in one sweep (2026-09-28), each held here.

1. Opening a project and taking its own rig clamped every pose to the OLD
   rig's joint limits first, then swapped the rig in. A project built on a
   wider rig opened with its moves silently cut short.
2. A project keyframe with a missing or broken time reached clampKeyTimes as
   undefined, and Math.max(undefined, floor) is NaN - the export then carried
   "T NaN" to the robot.
3. Changing the peak speed limit re-timed a PINNED move whose typed time
   happened to equal the automatic one. A pin means nothing automatic may
   touch it (check_time_pin), whatever number it holds.
4. Duplicating a keyframe copied its music/light cues, so the track started
   (or stopped) a second time at the copy.
5. Reopening a saved YAML lost every move name: buildYaml writes each name as
   an indented comment above its move, and the parser stripped all comments.

Asserted on `keys` because all five are the editor's own bookkeeping; what
reaches the module from `keys` is covered by check_studio_playback and
check_yaml_save_load.
"""
import browser
import fake_serial
import qc as F

AREA = "studio"
TITLE = "opening, re-timing, copying and re-reading a sequence keep what was made"
SLOW = True

DRIVER = """
function report(s){ rawCmd("MOVE QCMARK SWEEP~" + s); }
window.addEventListener("load", function(){ qcStudioReady().then(function(){ setTimeout(async function(){
  var out = [];
  try{
    // ---- 1 + 2: a project whose own rig allows 10..170, poses at 15 and 165,
    // one keyframe with no time at all
    var wide = JSON.parse(JSON.stringify(RIG));
    wide.min = Array(NJ).fill(10); wide.max = Array(NJ).fill(170);
    RIG.min = Array(NJ).fill(40); RIG.max = Array(NJ).fill(140);
    var p0 = Array(NJ).fill(90), p1 = Array(NJ).fill(90);
    p1[0] = 15; p1[4] = 165;
    var proj = {keys: [{pose: p0, t: 1000, hold: 0}, {pose: p1, hold: 0}],
                speedDps: 60, maxDps: 400, loop: false, rig: wide};
    var realFetch = window.fetch;
    window.fetch = function(url, o){
      if (String(url).indexOf("/api/load?") === 0)
        return Promise.resolve(new Response(JSON.stringify(proj), {status: 200}));
      return realFetch(url, o);
    };
    window.confirm = function(){ return true; };     // "use the project's setup"
    markClean(workSig(), "");                        // nothing unsaved on screen
    await loadProject("qc_sweep.json");
    window.fetch = realFetch;
    out.push("p10=" + keys[1].pose[0], "p14=" + keys[1].pose[4],
             "t1=" + keys[1].t, "yamlNaN=" + (buildYaml().yaml.indexOf("NaN") >= 0));

    // ---- 3: a pinned time that equals the automatic one. A low peak limit
    // makes the automatic time long; raising it would shorten an unpinned one.
    var a = Array(NJ).fill(90), b = Array(NJ).fill(90); b[0] = 130;
    keys = [{pose: a.slice(), t: 80, hold: 0}];
    document.getElementById("safeDpsInput").value = "20";
    safetyLimitChanged();
    document.getElementById("speedDps").value = "60";
    keys = [{pose: a.slice(), t: 80, hold: 0}, {pose: b.slice(), t: 0, hold: 0}];
    keys[1].t = autoTime(a, b, keyDps(1));
    pinTime(1);
    var pinnedT = keys[1].t;
    document.getElementById("safeDpsInput").value = "200";
    safetyLimitChanged();
    out.push("pinSame=" + (keys[1].t === pinnedT), "pinnedT=" + pinnedT, "after=" + keys[1].t);

    // ---- 4: a copy is a pose, not a second cue
    keys = [{pose: a.slice(), t: 80, hold: 0},
            {pose: b.slice(), t: 900, hold: 0, cues: ["play: song.mp3"], cuesAfter: ["rgb: 1 2 3"]}];
    selKey = 1; dupKey();
    out.push("copyCues=" + JSON.stringify(keys[2].cues || null) + "|" +
             JSON.stringify(keys[2].cuesAfter || null),
             "srcCues=" + (keys[1].cues || []).length);

    // ---- 5: names survive buildYaml -> parseSeqYaml
    keys = [{pose: a.slice(), t: 80, hold: 0, name: "start here"},
            {pose: b.slice(), t: 900, hold: 0, name: "wave"},
            {pose: a.slice(), t: 900, hold: 0}];
    var parsed = parseSeqYaml(buildYaml().yaml);
    out.push("names=" + parsed.keys.map(function(k){ return k.name || "-"; }).join(","));
  }catch(e){ out.push("ERR=" + String(e).slice(0,70)); }
  report(out.join("~"));
  setTimeout(function(){ report("done"); }, 300);
}, 150); }); });
"""


def run(t):
    if not browser.available():
        t.give_up("headless Edge not found - this needs a real browser")
    fake_serial.reset()
    base, _main = F.start_hub()
    browser.page(DRIVER, query="%s/studio/_qcdriver.html?dev=usb%%3A%s"
                 % (base, fake_serial.PORT), seconds=20)
    marks = [m[6:] for m in fake_serial.qc_marks if m.startswith("SWEEP~")]
    got = next((m for m in marks if m.startswith("p10=")), "")
    if not t.ok(got, "the driver opened, re-timed, copied and re-read", marks):
        return
    v = dict(kv.split("=", 1) for kv in got.split("~"))

    t.ok(v.get("p10") == "15" and v.get("p14") == "165",
         "a project opened WITH its own wider rig keeps its poses",
         "clamped to the old rig first, 15 and 165 came back as 40 and 140: %s" % v)
    t.ok(v.get("t1", "NaN") not in ("NaN", "undefined") and int(v.get("t1")) >= 80,
         "a keyframe saved without a time gets the floor, never NaN", v)
    t.ok(v.get("yamlNaN") == "false", "and no T NaN reaches the exported file", v)
    t.ok(v.get("pinSame") == "true",
         "a pinned time survives a new peak speed limit, even one that "
         "matched the automatic time",
         "the pin means nothing automatic may touch it: %s" % v)
    t.ok(v.get("copyCues") == "null|null" and v.get("srcCues") == "1",
         "a duplicated keyframe does not copy its music/light cues",
         "the copy restarted the track a second time: %s" % v)
    t.eq(v.get("names"), "start here,wave,-",
         "move names come back when a saved YAML is opened again")
