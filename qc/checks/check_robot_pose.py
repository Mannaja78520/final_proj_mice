"""nong's skeleton from a camera finds the joints, the facing, and what is wrong.

User 2026-10-28: *like YOLO pose, check the skeleton to find our robot's pose
from a camera, to prevent collisions later, see if a move is right, and auto
calibrate if sizes change*; and *tell which is front, back, left, right*.
tools/robot_pose puts keypoints on Studio's own rig (NongTree), so this holds,
on synthetic views where the truth is known:

* the keypoints move with the rig (a longer upper arm moves the elbow by
  exactly that much) and the L/R flip list mirrors every L_ to its R_;
* two cameras recover a random pose to < 1 deg; one camera with 1 px noise
  stays within a few degrees of the truth when it starts near the command
  (one camera cannot see depth flips: the docstring of fit_pose says so);
* front / left / back / right come out right from every side, and keypoints
  named by image side (left/right swapped) are noticed and undone;
* the compare finds a servo lag, a joint sitting off by a bias, and a stuck
  joint; the calibrator finds a longer arm and a joint offset;
* a YOLO-pose label has 5 + 3K numbers in [0, 1], and the chest marker is
  "hidden" (v=1) from behind.
Measured numbers for the same pipeline: docs/experiments/2026-10-28_robot_pose.md.
Nothing here is checked against a real video yet (needs the trained model).
"""
import copy
import json
import tempfile
from pathlib import Path

import qc as F

AREA = "robot-pose"
TITLE = "the robot's own skeleton from a camera: joints, facing, lag, calibration"
SLOW = False


def run(t):
    import numpy as np
    from tools.nong_sim.studio import StudioFacts, load_rig
    from tools.robot_pose.calibrate import Calibrator
    from tools.robot_pose.camera import Camera, axis_angle, rodrigues
    from tools.robot_pose.compare import MoveCheck
    from tools.robot_pose.detect import read_keypoints, write_keypoints
    from tools.robot_pose.fit import PoseFitter
    from tools.robot_pose.keypoints import RobotKeypoints, load_config
    from tools.robot_pose.synth import SynthViews

    cfg, rig, facts = load_config(), load_rig(), StudioFacts()
    kp = RobotKeypoints(rig, facts, cfg)
    home = rig["home"]
    rng = np.random.default_rng(7)

    # keypoints follow the rig
    longer = copy.deepcopy(rig)
    longer["dims"]["upperLenL"] += 20
    a, b = kp.points3d(home), RobotKeypoints(longer, facts, cfg).points3d(home)
    i, s = kp.index["L_elbow"], kp.index["L_shoulder"]
    grow = np.linalg.norm(b[i] - b[s]) - np.linalg.norm(a[i] - a[s])
    t.ok(abs(grow - 20) < 1e-6, "a 20 mm longer upper arm moves the elbow 20 mm", "%.3f" % grow)
    t.ok(all(kp.names[kp.flip[j]] == RobotKeypoints.mirror(n) for j, n in enumerate(kp.names))
         and kp.flip != list(range(len(kp.names))), "the flip list mirrors every L_ keypoint to its R_")
    r = rng.normal(0, 1, 3)
    t.ok(np.allclose(axis_angle(rodrigues(r)), r) and np.allclose(axis_angle(rodrigues([0, np.pi, 0])) ,
         [0, np.pi, 0]), "camera rotations survive a round trip (incl. 180 deg)")

    fit = PoseFitter(kp, cfg)
    sv = SynthViews(kp, cfg, seed=5)

    # two cameras: the exact pose
    worst = 0.0
    for n in range(4):
        pose = sv.pose()
        cams = [Camera.orbit(30 + 90 * n + 90 * k, 15, 1400, (0, 100, 0), 60, 640, 480) for k in range(2)]
        views = [sv.view(pose, c) for c in cams]
        start = np.clip(np.array(pose) + rng.normal(0, 10, 10), fit.lo, fit.hi)
        f = fit.fit_pose(cams, [v["uv"] for v in views], [(v["vis"] == 2) * 1.0 for v in views], start)
        worst = max(worst, float(np.abs(np.array(f.pose) - pose).max()))
    t.ok(worst < 1.0, "two cameras put every joint within 1 deg of the truth", "worst %.2f deg" % worst)

    # one camera, 1 px noise, started near the command
    errs = []
    for n in range(6):
        pose = sv.pose()
        cam = Camera.orbit(60 * n, 15, 1400, (0, 100, 0), 60, 640, 480)
        v = sv.view(pose, cam)
        start = np.clip(np.array(pose) + rng.normal(0, 10, 10), fit.lo, fit.hi)
        f = fit.fit_pose(cam, v["uv"] + rng.normal(0, 1, v["uv"].shape), (v["vis"] == 2) * 1.0, start)
        errs.append(np.abs(np.array(f.pose) - pose))
    med = float(np.median(errs))
    t.ok(med < 3.0, "one camera with 1 px noise: median joint error under 3 deg", "%.2f deg" % med)

    # facing, and keypoints named by image side. From the side the two arms
    # overlap, so which is which is the detector's job (by look), not geometry's:
    # the swap is only required to be undone from the front and the back.
    ok, swaps = [], []
    for az, want in ((0, "front"), (90, "left"), (180, "back"), (270, "right")):
        cam = Camera.orbit(az, 10, 1500, (0, 100, 0), 60, 640, 480)
        pose = list(home)
        pose[1] = 120                                  # left arm out only: the arms differ
        v = sv.view(pose, cam)
        f = fit.fit_pose(cam, v["uv"], (v["vis"] == 2) * 1.0, home)
        ok.append((want, f.facing))
        if want in ("front", "back"):
            sw = fit.fit_pose(cam, v["uv"][kp.flip], ((v["vis"] == 2) * 1.0)[kp.flip], home)
            swaps.append((want, sw.swapped, round(float(np.abs(np.array(sw.pose) - pose).max()), 1)))
    t.ok(all(w == g for w, g in ok), "front / left / back / right are told from every side", str(ok))
    t.ok(all(s and e < 2 for _, s, e in swaps), "keypoints with left and right swapped are noticed and undone",
         str(swaps))
    # a photo from an unknown camera far behind (telephoto: almost no
    # perspective), arms named by image side: only the chest marker NOT being
    # seen says "back" - without it the mirrored front view fits as well
    tele = Camera.orbit(180, 10, 8000, (0, 100, 0), 8, 640, 480)
    v = sv.view(home, tele)
    blind = fit.fit_view(v["uv"][kp.flip], ((v["vis"] == 2) * 1.0)[kp.flip])
    t.ok(blind.facing == "back", "an unknown camera far behind the robot says back (the chest marker)",
         blind.facing)
    # compare: lag, bias, stuck
    names = list(facts.joint_names)
    cmd = lambda tt: [90 + 40 * np.sin(tt + j) for j in range(10)]
    times = np.arange(0, 8, 0.05)
    seen = np.array([cmd(tt - 0.1) for tt in times])
    seen[:, 2] += 9                                   # sits 9 deg off
    seen[:, 4] = 90                                   # never moves
    rep = MoveCheck(names, cfg).run(times, seen, cmd)
    j = {x["joint"]: x for x in rep["joints"]}
    t.ok(abs(j[names[0]]["lagS"] - 0.1) < 0.03 and j[names[0]]["verdict"] == "ok",
         "a servo 0.1 s behind is found as lag, not as error", str(j[names[0]]))
    t.ok(abs(j[names[2]]["biasDeg"] - 9) < 0.5 and j[names[2]]["verdict"] in ("warn", "bad"),
         "a joint sitting 9 deg off is found, with its bias", str(j[names[2]]))
    t.ok(j[names[4]]["verdict"] == "stuck" and rep["verdict"] == "stuck", "a joint that never moves is stuck")

    # calibration: a longer left upper arm and an elbow offset
    true = copy.deepcopy(rig)
    true["dims"]["upperLenL"] += 15
    tkp = RobotKeypoints(true, facts, cfg)
    tsv = SynthViews(tkp, cfg, seed=9)
    cams = [Camera.orbit(20, 15, 1400, (0, 100, 0), 60, 640, 480),
            Camera.orbit(110, 15, 1400, (0, 100, 0), 60, 640, 480)]
    el = names.index("L_EL_P")
    frames = []
    for n in range(10):
        pose = tsv.pose()
        real = list(pose)
        real[el] += 4                                 # the servo sits 4 deg past what it was told
        vs = [tsv.view(real, c) for c in cams]
        frames.append((pose, [v["uv"] for v in vs], [(v["vis"] == 2) * 1.0 for v in vs]))
    guess = [Camera.from_json(dict(c.to_json(), t=list(np.array(c.t) + 30))) for c in cams]
    res = Calibrator(kp, cfg).run(guess, frames)
    d = res["lengthsMm"]["upperLenL"]["diff"]
    o = res["jointOffsetDeg"]["L_EL_P"]
    t.ok(abs(d - 15) < 3 and abs(o - 4) < 1, "calibration finds a 15 mm longer arm and a 4 deg elbow offset",
         "%.1f mm, %.2f deg" % (d, o))
    t.ok(res["note"].startswith("suggestions only") and "WAIST" not in res["jointOffsetDeg"],
         "calibration only suggests, and leaves the waist offset alone (the camera could explain it)")

    # YOLO label, visibility, keypoints file
    back = sv.view(home, Camera.orbit(180, 10, 1500, (0, 100, 0), 60, 640, 480))
    line = SynthViews.yolo_line(back["uv"], back["vis"], 640, 480).split()
    nums = [float(x) for x in line[1:]]
    t.ok(len(line) == 5 + 3 * len(kp.names) and all(0 <= x <= 2 for x in nums),
         "a YOLO-pose label line is class + box + 3 numbers per keypoint", str(len(line)))
    t.ok(back["vis"][kp.index["chest_front"]] == 1, "the chest marker is hidden from behind")
    t.ok("flip_idx: %s" % json.dumps(kp.flip) in sv.dataset_yaml("x"), "the dataset yaml carries flip_idx")
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "k.jsonl"
        write_keypoints(p, list(reversed(kp.names)), [{"t": 0, "cam": 0, "kp": [[i, i] for i in range(len(kp.names))],
                                                       "conf": [1] * len(kp.names)}])
        rows = read_keypoints(p, kp.names)
        t.ok(rows[0]["kp"][0] == [len(kp.names) - 1] * 2, "a keypoints file in another order reads back right")
