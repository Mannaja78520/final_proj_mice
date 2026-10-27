"""The MuJoCo player moves exactly like Studio and times moves exactly like the board.

User 2026-10-27: *can RL in a physics world learn the moves smoothly, and I
want to SEE the simulation as a 3D world*. The answer given was: no RL - Studio
already checks limits, collisions and speed exactly - but an optional MuJoCo
world (tools/nong_sim) shows any number of robots playing a sequence with
what Studio cannot model: servo lag, gravity, the board's own clock.

A simulator that moves differently from Studio is worse than none, because it
looks convincing. So the tree is held to Studio's real 3D scene: a rig with
EVERY option bent (tilt, after-turn, shoulder offsets, a swapped joint pair,
flipped senses, then a measured 4-bar shrug) is loaded into Studio in a
browser, random poses are applied, and the shoulder, elbow and wrist points
Studio draws must match tools/nong_sim within 0.05 mm. The board clock is
held to Studio's minTime() (itself held to the firmware by other checks).
With MuJoCo installed, the built world must put those same points in the same
place, and a hands-crossed pose must be reported as a hit while home is clear.
"""
import json
import math
import random
import sys

import browser
import fake_serial
import qc as F

AREA = "studio"
TITLE = "the MuJoCo player moves like Studio and keeps the board's clock"
SLOW = True

sys.path.insert(0, str(F.CODE))
from tools.nong_sim.board_clock import BoardClock, parse_sequence  # noqa: E402
from tools.nong_sim.kinematics import NongTree  # noqa: E402
from tools.nong_sim.studio import StudioFacts, load_rig  # noqa: E402

POINTS = ["shL", "elL", "wrL", "shR", "elR", "wrR"]

DRIVER = """
function report(s){ rawCmd("MOVE QCMARK SIM~" + s); }
var CASES = %s;
window.addEventListener("load", function(){ qcStudioReady().then(function(){ setTimeout(function(){
  try{
    CASES.forEach(function(c, n){
      RIG = mergeRig(JSON.parse(JSON.stringify(c.rig)));
      buildRobot();
      c.poses.forEach(function(p, k){
        pose = p.slice(); applyPose(); robot.updateMatrixWorld(true);
        var W = function(o){ var v = o.getWorldPosition(new THREE.Vector3()); return [v.x, v.y, v.z].map(function(x){ return x.toFixed(3); }).join(","); };
        report("fk" + n + "_" + k + "=" + [W(shrugAnchors.L), W(elbowBalls[0]), W(wristBalls[0]),
                                           W(shrugAnchors.R), W(elbowBalls[1]), W(wristBalls[1])].join(";"));
      });
    });
    var a = CASES[0].poses[0], b = CASES[0].poses[1];
    report("time=" + minTime(a, b) + "," + minTime(b, a));
  }catch(e){ report("ERR-" + String(e).slice(0, 90)); }
  setTimeout(function(){ report("done"); }, 300);
}, 150); }); });
"""


def bent_rig(calibrated):
    rig = load_rig()
    rnd = random.Random(7 + calibrated)
    rig["tilt"] = [[rnd.uniform(-20, 20) for _ in range(3)] for _ in range(10)]
    rig["after"] = [[rnd.uniform(-15, 15) for _ in range(3)] for _ in range(10)]
    rig["mount"] = {"L": [3, -5, 7], "R": [-4, 6, -2]}
    rig["order"] = [[1, 0, 2, 3], [4, 5, 7, 6]]
    rig["invert"] = [1 - v if i % 3 == 0 else v for i, v in enumerate(rig["invert"])]
    rig["dims"]["shrugPivot"] = 12
    rig["shrugCurve"] = [{"j": 80, "l": -9, "r": 7}, {"j": 100, "l": 11, "r": -6}] if calibrated else []
    return rig


def poses(rig, n, seed):
    rnd = random.Random(seed)
    return [[round(rnd.uniform(lo, hi), 1) for lo, hi in zip(rig["min"], rig["max"])] for _ in range(n)]


def run(t):
    facts = StudioFacts()
    cases = [{"rig": bent_rig(c), "poses": poses(load_rig(), 8, 11 + c)} for c in (0, 1)]
    want = {}
    for n, c in enumerate(cases):
        tree = NongTree(c["rig"], facts)
        for k, p in enumerate(c["poses"]):
            want["fk%d_%d" % (n, k)] = tree.forward(p)
    clock = BoardClock(load_rig(), facts)
    a, b = cases[0]["poses"][:2]
    t.ok(clock.floor_ms(a, b) >= facts.min_move_ms, "the board floor is never under the shortest move",
         clock.floor_ms(a, b))
    steps = parse_sequence('steps:\n  - speed: 60\n  - pose: "%s T 10"\n  - wait: 250\n' % " ".join(map(str, b)))
    moves = clock.plan(steps)
    t.ok(len(moves) == 1 and moves[0].took > moves[0].asked and clock.length > clock.asked_length,
         "a move asked faster than the servos can go is lengthened, and the show falls behind its music",
         [clock.length, clock.asked_length])
    t.ok(abs(clock.length - moves[0].took - 0.25) < 1e-9, "a wait adds to the same clock", clock.length)

    if not browser.available():
        t.give_up("headless browser unavailable - the parts above still ran")
    fake_serial.reset()
    base, _main = F.start_hub()
    browser.page(DRIVER % json.dumps(cases), query="%s/studio/_qcdriver.html?dev=usb%%3A%s"
                 % (base, fake_serial.PORT), seconds=30)
    got = dict(m[4:].split("=", 1) for m in fake_serial.qc_marks if m.startswith("SIM~") and "=" in m)
    errs = [m for m in fake_serial.qc_marks if m.startswith("SIM~ERR")]
    t.ok(not errs and len(got) >= len(want), "Studio drew every bent-rig pose", errs or sorted(got)[:4])
    worst, where = 0.0, ""
    for key, points in want.items():
        if key not in got:
            continue
        studio = [[float(v) for v in xyz.split(",")] for xyz in got[key].split(";")]
        for name, s in zip(POINTS, studio):
            d = math.dist(points[name], s)
            if d > worst:
                worst, where = d, "%s %s studio %s sim %s" % (key, name, s, list(points[name]))
    t.ok(worst < 0.05, "every shoulder, elbow and wrist lands where Studio draws it (tilt, after-turn, "
         "offsets, swapped pair, flipped senses, 4-bar shrug)", "worst %.4f mm at %s" % (worst, where))
    times = [int(v) for v in got.get("time", "0,0").split(",")]
    ours = [clock.floor_ms(a, b), clock.floor_ms(b, a)]
    # the firmware truncates to whole ms, Studio rounds up: 1 ms apart at most
    t.ok(all(abs(x - y) <= 1 for x, y in zip(ours, times)) and min(times) > 0,
         "the board clock lengthens a move as Studio's minTime does", [ours, times])

    try:
        import mujoco  # noqa: F401
    except ImportError:
        t.ok(True, "MuJoCo is not installed here: the 3D world itself was not run", "pip install mujoco")
        return
    from tools.nong_sim.play import load_config, run as play
    from tools.nong_sim.world import NongWorld
    cfg = load_config()
    cfg["robots"]["count"] = 1
    rig = cases[1]["rig"]
    world = NongWorld(rig, facts, cfg, [("still", [])])
    world.reset()
    tree = NongTree(rig, facts)
    home = tree.forward(rig["home"])
    base_pos = world.data.body("r0_base").xpos
    rot = world.data.body("r0_base").xmat.reshape(3, 3)
    sim = rot @ (home["wrL"] * 0.001) + base_pos
    t.ok(math.dist(sim, world.data.body("r0_L_wrist").xpos) * 1000 < 0.05,
         "MuJoCo's model puts the left wrist where Studio does", [list(sim), list(world.data.body("r0_L_wrist").xpos)])
    rig = load_rig()
    cross = list(rig["home"])
    cross[:8] = [25, 109.4, 25, 25, 25, 62.4, 155, 25]          # hello.yaml, arms folded over each other
    seq = parse_sequence('steps:\n  - pose: "%s T 1500"\n  - wait: 1000\n' % " ".join(map(str, cross)))
    report = play(NongWorld(rig, facts, cfg, [("cross", seq)]))[0]
    t.ok(report["hits"], "hands folded through each other are reported as a hit", report["hits"])
    calm = play(NongWorld(rig, facts, cfg, [("home", parse_sequence(
        'steps:\n  - pose: "%s T 800"\n' % " ".join(map(str, rig["home"]))))]))[0]
    t.ok(not calm["hits"] and calm["worstFollowDeg"] < 2, "standing at home: no hit, servos hold their pose",
         [calm["hits"], calm["worstFollowDeg"]])
