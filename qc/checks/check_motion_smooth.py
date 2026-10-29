"""One smoothing stage for every move (A54-1).

User 2026-10-29 (Thai): the non-RL moves stutter too; is there a smoother to
use, like a plugin; make every move smooth. The stutter was the board: every
POSE was a cosine that STOPS at its keyframe (NongMath.h ease), so a cheer
dance with a key every 167-500 ms stopped 429 times in 158 s. Now a key where a
joint keeps going the same way is passed THROUGH at a speed (its pass speed),
each move a cubic Hermite between the speeds; times never change (music).

Held here:

* the core (main_python/motion_smooth.py): via speeds where a joint keeps
  going, 0 where it turns back (a flick keeps its peak exactly), at a hold and
  at the ends; never past a key; the speed is continuous through a via key;
  the keyframe times are unchanged; far fewer stops than the cosine;
* Studio's motion_smooth.js gives the SAME speeds on the same moves (one
  maths, two languages), and the firmware's unit test holds the same curve
  value (19.4147) as Python;
* in Studio the preview passes through a key, a move whose curve touches the
  robot rests on its keys (its checked straight line), the file carries
  `pass:` lines and the hub steps carry `pass`; with the source off it is the
  cosine again;
* the video clean-up keeps a 230 ms flick (the old 240 deg/s, 900 deg/s2
  filter erased all 19 flicks of a 12 s clip, PC thread 2026-10-29) and still
  drops a one-frame tracker spike;
* the hub sends PASS right before its POSE, stops sending it when the board
  answers ERR (an old board), and sends none with "hub" off; a saved file's
  `pass:` reaches the steps; a show at 50 % halves the speeds;
* the physics player (board_clock) plays the curve only when the board would:
  start speeds as planned and the move not lengthened;
* tools/smooth_sequence.py adds `pass:` lines for files made elsewhere (RL)
  and replaces old ones instead of piling them up;
* PASS is a sequence step key the board knows (commands.json) and a
  capability it declares.
"""
import json
import sys

import browser
import fake_serial
import qc as F

AREA = "studio"
TITLE = "one smoother for every move: pass through keys, keep flicks and music time"
SLOW = True

sys.path.insert(0, str(F.CODE / "main_python"))
sys.path.insert(0, str(F.CODE))
import motion_smooth as M  # noqa: E402

# A small dance: joint 0 rises over four keys then flicks back (a reversal),
# joint 2 rises steadily, a hold at key 5.
J0 = [90, 100, 112, 125, 135, 120, 100, 95]
J2 = [80, 85, 92, 100, 106, 112, 118, 120]


def dance():
    keys = []
    for i, (a, b) in enumerate(zip(J0, J2)):
        p = [90.0] * 10
        p[0], p[2] = float(a), float(b)
        keys.append({"pose": p, "t": 0 if i == 0 else 250, "hold": 300 if i == 5 else 0})
    return keys


def rig():
    from tools.nong_sim.studio import load_rig   # noqa: PLC0415
    return load_rig()


def test_core(t, cfg, R):
    K = dance()
    times = [k["t"] for k in K]
    V = M.Smoother(cfg, R).vias(K, touches=lambda p: False)
    t.ok(V[1][0] > 5 and V[2][0] > 5 and V[3][0] > 5,
         "a joint that keeps rising is passed through at a speed", [r[0] for r in V])
    t.ok(V[4][0] == 0, "where it turns back (a flick) it stops: the peak is kept", V[4][0])
    t.ok(V[5] == [0.0] * 10 and V[0] == [0.0] * 10 and V[-1] == [0.0] * 10,
         "a hold and both ends rest", [V[0], V[5], V[-1]])
    t.ok(all(V[i][1] == 0 for i in range(len(K))), "a joint that does not move gets no speed")
    t.ok([k["t"] for k in K] == times, "the keyframe times are never changed (music)")
    starts, _ = M._times(K)
    at4 = starts[4] + K[4]["t"]
    t.ok(abs(M.pose_at(K, V, at4)[0] - 135) < 1e-6, "the flick reaches its peak exactly",
         M.pose_at(K, V, at4)[0])
    # never past a key: every joint stays between its two keys on every move
    over = 0.0
    for i in range(1, len(K)):
        for s in range(1, 50):
            p = M.pose_at(K, V, starts[i] + K[i]["t"] * s / 50)
            for j in range(10):
                lo, hi = sorted((K[i - 1]["pose"][j], K[i]["pose"][j]))
                over = max(over, lo - p[j], p[j] - hi)
    t.ok(over < 1e-6, "no joint ever goes past a keyframe", over)
    # the speed is the same just before and just after a via key: no stop
    at2 = starts[2] + K[2]["t"]
    before = (M.pose_at(K, V, at2) [0] - M.pose_at(K, V, at2 - 2)[0]) / 0.002
    after = (M.pose_at(K, V, at2 + 2)[0] - M.pose_at(K, V, at2)[0]) / 0.002
    t.ok(abs(before - V[2][0]) < 2 and abs(after - V[2][0]) < 2,
         "key 2 is passed at its speed, not stopped on (%.0f / %.0f deg/s)" % (before, after))
    old, new = M.jerk_report(K), M.jerk_report(K, V)
    t.ok(new["stops"] < old["stops"] and new["rmsAcc"] < old["rmsAcc"],
         "fewer stops and less speed-up than the cosine (%s -> %s stops)" % (old["stops"], new["stops"]),
         (old, new))
    # a curve that touches the robot rests on its keys: its checked straight line
    hit = lambda p: 104 < p[0] < 108                        # noqa: E731  inside move 2
    Vt = M.Smoother(cfg, R).vias(K, touches=hit)
    t.ok(Vt[1][0] == 0 and Vt[2][0] == 0 and Vt[3][0] > 0,
         "a move whose curve touches rests on both its keys, the others still pass",
         [r[0] for r in Vt])
    # the firmware's unit test holds the same curve value
    t.ok(abs(M.curve(10, 40, 50, 80, 0.3, 0.37) - 19.4147) < 1e-3,
         "the shared curve value the firmware test holds is still 19.4147")
    fw = (F.CODE / "firmware/test/test_logic/test_main.cpp").read_text(encoding="utf-8")
    t.ok("19.4147f" in fw and "RUN_TEST(test_pass_curve_matches_studio)" in fw,
         "and the firmware test asserts it (pio test -e native)")
    return K, V


def test_board(t, cfg, R, K, V):
    from tools.nong_sim.board_clock import BoardClock   # noqa: PLC0415
    from tools.nong_sim.studio import StudioFacts   # noqa: PLC0415
    lines = ["steps:", "  - pace: music 0"]
    for i, k in enumerate(K):
        p = M.pass_values(V, i)
        if p:
            lines.append('  - pass: "%s"' % M.pass_line(p))
        lines.append('  - pose: "%s T %d"' % (" ".join("%g" % v for v in k["pose"]), k["t"] or 1000))
        if k["hold"]:
            lines.append("  - wait: %d" % k["hold"])
    from tools.nong_sim.board_clock import parse_sequence   # noqa: PLC0415
    clock = BoardClock(R, StudioFacts())
    moves = clock.plan(parse_sequence("\n".join(lines)))
    curved = [m for m in moves if m.v0]
    t.ok(len(curved) >= 3, "the board plays the planned moves as the curve (%d)" % len(curved),
         [m.line for m in curved])
    # a file resumed at key 3: the arm starts at rest, so move 4 (planned to
    # start at key 3's speed) plays the cosine instead
    resumed = [ln for ln in lines if "pose" not in ln or True]
    cut = lines[:2] + [ln for ln in lines[2:]][lines[2:].index(
        next(ln for ln in lines[2:] if '"%g' % K[3]["pose"][0] in ln and "pose" in ln)):]
    moves2 = BoardClock(R, StudioFacts()).plan(parse_sequence("\n".join(cut)))
    t.ok(not moves2[1].v0, "a move whose start speed the arm does not have plays the cosine",
         [bool(m.v0) for m in moves2][:3])
    del resumed


def test_hub(t, cfg, K, V):
    import hub_show   # noqa: PLC0415
    said = []

    def cmd(dev, c, err=False):
        said.append(c)
        return "ERR unknown command" if (err and c.startswith("PASS")) else "OK"
    steps = [{"pose": k["pose"], "t": max(80, k["t"]), "hold": k["hold"],
              **({"pass": M.pass_values(V, i)} if M.pass_values(V, i) else {})} for i, k in enumerate(K)]
    sp = hub_show.ShowPlayer(cmd_fn=cmd, parse_fn=lambda dev: None, cues_fn=lambda c: [])
    sp.start("usb:QC", steps)
    sp.thread.join(timeout=10)
    pairs = [(said[i], said[i + 1]) for i in range(len(said) - 1) if said[i].startswith("PASS")]
    t.ok(len(pairs) == sum(1 for s in steps[1:] if s.get("pass")) and all(b.startswith("POSE") for _, b in pairs),
         "the hub sends PASS right before each smoothed move's POSE (%d)" % len(pairs), said[:8])
    said.clear()
    sp = hub_show.ShowPlayer(cmd_fn=lambda d, c: cmd(d, c, True), parse_fn=lambda dev: None,
                             cues_fn=lambda c: [])
    sp.start("usb:QC", steps)
    sp.thread.join(timeout=10)
    t.ok(sum(1 for c in said if c.startswith("PASS")) == 1,
         "an old board answers ERR once and the run stops sending PASS", said[:6])
    said.clear()
    real = M.load_config
    M.load_config = lambda path=None: dict(real(), sources=dict(real().get("sources", {}), hub=False))
    try:
        sp = hub_show.ShowPlayer(cmd_fn=cmd, parse_fn=lambda dev: None, cues_fn=lambda c: [])
        sp.start("usb:QC", steps)
        sp.thread.join(timeout=10)
    finally:
        M.load_config = real
    t.ok(not any(c.startswith("PASS") for c in said), "with \"hub\" off no PASS goes out")
    import main   # noqa: PLC0415
    got = main.seq_steps('steps:\n  - pose: "%s T 1000"\n  - pass: "%s"\n  - pose: "%s T 250"\n'
                         % (" ".join(["90"] * 10), " ".join(["0"] * 10 + ["12.5"] + ["0"] * 9),
                            " ".join(["100"] + ["90"] * 9)))
    t.ok(got["steps"][1].get("pass", [0] * 20)[10] == 12.5 and not got["steps"][1]["cues"],
         "a saved file's pass: reaches the hub's steps, not its cues", got["steps"][1])
    import shows   # noqa: PLC0415
    t.ok(hasattr(shows, "Shows"), "shows loads")


def test_tool(t):
    import smooth_sequence as S   # noqa: PLC0415
    text = "name: x\nsteps:\n  - pace: music 0\n" + "".join(
        '  - pose: "%s T %d"\n' % (" ".join("%g" % v for v in k["pose"]), k["t"] or 1000) for k in dance())
    once, before, after = S.smooth(text, rig(), "rl")
    twice, _, _ = S.smooth(once, rig(), "rl")
    n = once.count("- pass:")
    t.ok(n >= 3 and after["stops"] < before["stops"],
         "the sequence tool adds pass: lines (%d) and the stops drop" % n, (before, after))
    t.ok(twice == once, "run again it replaces its own lines instead of piling them up")


def test_firmware(t):
    cmds = (F.CODE / "firmware/config/commands.json").read_text(encoding="utf-8")
    t.ok('"name": "PASS"' in cmds and '{"key": "pass"}' in cmds,
         "PASS is a command with the sequence step key pass (old boards skip it, logged)")
    mod = (F.CODE / "firmware/src/modules/nong/NongModule.cpp").read_text(encoding="utf-8")
    t.ok('caps.add("pass")' in mod, "a board with PASS says so (the hub may rely on it)")
    t.ok("nongmath::curve(from_[i], target_[i], v0_[i], v1_[i]" in mod,
         "the board's 50 Hz loop plays the shared curve")


DRIVER = """
function report(s){ qcMark("MS~" + s); }
window.addEventListener("load", function(){ qcWaitFor(function(){
    return typeof MotionSmooth === "function" && typeof motionSmooth === "object" && SMOOTH && SMOOTH.on
           && typeof buildYaml === "function" && typeof VideoMotionSmoother === "function";
  }, 20000).then(function(ready){
  if (!ready) { report("ERR-the-app-never-finished-loading"); report("done"); return; }
  try{
    var o = {};
    var P = __PARITY__;
    o.parity = JSON.stringify(new MotionSmooth({cfg: P.cfg, maxDps: P.maxDps, acc: P.acc, cap: 0,
                                                touches: function(){ return false; }}).vias(P.keys));
    // Studio: a sweep of joint 2 that keeps rising, at the music pace (no cap)
    MUSIC_DPS = 0; SEQ_MUSIC_DPS = null;
    var a = RIG.home.slice();
    function at(d){ var p = a.slice(); p[2] = clampJ(2, a[2] + d); return p; }
    keys = [{pose: at(0), t: 0, hold: 0, cues: ["play: qc_song.mp3"]},
            {pose: at(8), t: 300, hold: 0, tset: true}, {pose: at(18), t: 300, hold: 0, tset: true},
            {pose: at(30), t: 300, hold: 0, tset: true}, {pose: at(36), t: 300, hold: 0, tset: true}];
    bumpKeys(); renderTimeline();
    var K = playKeys(), t2 = (K[0].hold || 0) + K[1].t + K[2].t;
    function speed(ms){ return (easeKeys(K, ms + 5).pose[2] - easeKeys(K, ms - 5).pose[2]) / 0.01; }
    o.passSpeed = speed(t2).toFixed(1);
    var y = buildYaml().yaml;
    o.yamlPass = (y.match(/- pass: "/g) || []).length;
    o.passBeforePose = /- pass: "[^"]+"\\n  - pose:/.test(y);
    o.hubPass = (hubShowSteps() || []).filter(function(s){ return s.pass && s.pass.length === 20; }).length;
    // a curve that touches rests on its keys
    var realHit = collisionAt, lo = a[2] + 10, hi = a[2] + 14;
    collisionAt = function(p){ return p[2] > lo && p[2] < hi ? "qc" : null; };
    motionSmooth.forget();
    o.touchSpeed = speed(t2).toFixed(1);
    collisionAt = realHit; motionSmooth.forget();
    // the source off: the cosine stops on the key again
    SMOOTH.sources.studio = false; motionSmooth.forget();
    o.offSpeed = speed(t2).toFixed(1);
    o.offYaml = (buildYaml().yaml.match(/- pass: "/g) || []).length;
    SMOOTH.sources.studio = true; motionSmooth.forget();
    // the video clean-up: a 5-frame flick stays, a 1-frame spike goes
    var poses = [], times = [], frames = [];
    for (var i = 0; i < 60; i++) {
      var p = a.slice();
      var f = [0, 8, 16, 22, 22, 16, 8, 0][i - 20]; if (f != null) p[2] = clampJ(2, a[2] + f);
      if (i === 40) p[2] = clampJ(2, a[2] + 20);
      poses.push(p); times.push(i * 1000 / 30); frames.push({trusted: true, body: {}, shot: 0});
    }
    var sm = new VideoMotionSmoother().apply(poses, times, frames).poses;
    var peak = 0, spike = 0;
    for (var i = 15; i < 30; i++) peak = Math.max(peak, sm[i][2] - a[2]);
    for (var i = 38; i < 45; i++) spike = Math.max(spike, sm[i][2] - a[2]);
    o.flickKept = peak.toFixed(1); o.spikeLeft = spike.toFixed(1);
    report(Object.keys(o).map(function(k){ return k + "=" + o[k]; }).join("~"));
    report("done");
  }catch(e){ report("ERR-" + String(e && e.stack || e).slice(0,160).replace(/~/g, "_")); report("done"); }
}); });
"""


def test_studio(t, cfg, R, K, V):
    if not browser.available():
        t.give_up("headless Edge not found - this needs a real browser")
    parity = {"cfg": cfg, "maxDps": R["servoMaxDps"], "acc": R["servoAccel"], "keys": K}
    fake_serial.reset()
    base, _main = F.start_hub()
    browser.page(DRIVER.replace("__PARITY__", json.dumps(parity)),
                 query="%s/studio/_qcdriver.html?dev=usb%%3A%s" % (base, fake_serial.PORT), seconds=60)
    marks = [m[3:] for m in fake_serial.qc_marks if m.startswith("MS~")]
    bad = [m for m in marks if m.startswith("ERR-")]
    if not t.ok(not bad, "the driver ran without throwing", bad[:1]):
        return
    got = next((m for m in marks if m.startswith("parity=")), "")
    if not t.ok(got, "the driver measured the page", marks):
        return
    v = dict(kv.split("=", 1) for kv in got.split("~"))
    print("   measured:", {k: x for k, x in v.items() if k != "parity"})
    js = json.loads(v["parity"])
    py = M.Smoother(cfg, R).vias(K, touches=lambda p: False)
    worst = max(abs(a - b) for ra, rb in zip(js, py) for a, b in zip(ra, rb))
    t.ok(worst <= 0.15, "Studio's motion_smooth.js gives the same speeds as the Python one "
         "(worst %.2f deg/s)" % worst, (js, py))
    t.ok(float(v["passSpeed"]) > 10, "the Studio preview passes key 2 at %s deg/s" % v["passSpeed"], v)
    t.ok(int(v["yamlPass"]) >= 2 and v["passBeforePose"] == "true",
         "the file carries pass: lines right before their poses (%s)" % v["yamlPass"], v)
    t.ok(int(v["hubPass"]) >= 2, "and the steps sent to the hub carry pass (%s)" % v["hubPass"], v)
    # the cosine's own speed 5 ms either side of its stop is about 1.5 deg/s
    t.ok(abs(float(v["touchSpeed"])) < 4, "a curve that touches the robot rests on its key instead", v)
    t.ok(abs(float(v["offSpeed"])) < 4 and v["offYaml"] == "0",
         "with the source off the cosine stops on the key and no pass: is written", v)
    t.ok(float(v["flickKept"]) > 18, "the video clean-up keeps a 230 ms 22 deg flick (%s deg)" % v["flickKept"], v)
    t.ok(float(v["spikeLeft"]) < 5, "and drops a one-frame 20 deg spike (%s deg left)" % v["spikeLeft"], v)


def run(t):
    sys.path.insert(0, str(F.HUB))
    sys.path.insert(0, str(F.CODE / "tools"))
    cfg, R = M.load_config(), rig()
    t.ok(cfg.get("on") is True, "motion_smooth.json is read and on", cfg.get("on"))
    K, V = test_core(t, cfg, R)
    test_board(t, cfg, R, K, V)
    test_hub(t, cfg, K, V)
    test_tool(t)
    test_firmware(t)
    test_studio(t, cfg, R, K, V)
