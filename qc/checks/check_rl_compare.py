"""The RL-vs-planner experiment scores every contender honestly and the same way.

User 2026-10-27: *ทำ RL เป็นการทดลองแยก แล้วอัดวิดีโอเทียบกับแบบที่ใช้อยู่ ... เช็คว่าแบบไหนดีกว่ากัน*.
A comparison is only worth something if the yardstick is right, so this holds
the yardstick, on synthetic dances (the real cheer data is private on the PC):
- the GPU forward kinematics (tools/rl_compare/kin.py) puts the shoulder,
  elbow and wrist exactly where tools/nong_sim NongTree does (itself held to
  Studio's 3D scene by check_nong_sim), with the waist removed as Studio does;
- the approximate clearance used in the RL reward never calls a pose clear
  that Studio's own checker (studio_eval.cjs) flags, beyond 2 mm (Studio's
  box test inflates corners; the paddle is drawn as three capsules);
- a robot that dances the dancer's own motion scores ~0 on both the song
  clock and the shape; the same motion at half speed keeps ~0 shape error but
  is late, twice as long, and wrong on the song clock (so a slow planner is
  not mistaken for an accurate one, and the warp really finds the shape);
- the servo model never exceeds the servo's speed, and the policy's command
  never moves faster than the scenario cap or leaves the joint range;
- the board-clock sampler matches tools/nong_sim BoardClock.target.
Without torch installed (the PC before `pip install torch`) only the parts
that need no torch are run, and that is said.
"""
import json
import math
import random
import subprocess
import sys
import tempfile
from pathlib import Path

import qc as F

AREA = "tooling"
TITLE = "the RL vs planner experiment scores every contender the same, correct way"
SLOW = False

sys.path.insert(0, str(F.CODE))


def run(t):
    import numpy as np
    from tools.nong_sim.board_clock import BoardClock
    from tools.nong_sim.kinematics import NongTree
    from tools.nong_sim.studio import StudioFacts, load_rig
    cfg = json.loads((F.CODE / "config" / "rl_compare.json").read_text(encoding="utf-8"))
    ids = [v["id"] for v in cfg["planner"]["variants"]] + [cfg["rl"]["id"]]
    t.ok(len(set(ids)) == len(ids), "every contender has its own id", str(ids))
    t.ok(cfg["out"].startswith(".local"), "results go to the git-ignored .local folder", cfg["out"])
    rig, facts = load_rig(), StudioFacts()
    rnd = random.Random(7)
    poses = [[rnd.uniform(rig["min"][i], rig["max"][i]) for i in range(10)] for _ in range(400)]

    # board clock sampler == BoardClock.target
    from tools.rl_compare.planner import PlannerRun
    keys = [{"pose": rig["home"], "t": 1000, "hold": 0}] + [{"pose": p, "t": 700, "hold": 200 * (k % 2)} for k, p in enumerate(poses[:12])]
    pr = PlannerRun({"music": False}, {"safeDps": 60}, facts, 0)
    cmd, info = pr.commands(rig, keys, 50)
    clock = BoardClock(rig, facts, 60)
    moves = clock.plan(pr.steps(keys))
    t0 = moves[0].start + moves[0].took
    worst = max(np.abs(cmd[k] - np.array(BoardClock.target(moves, t0 + k / 50))).max() for k in range(0, len(cmd), 7))
    t.ok(worst < 1e-6, "the planner's commands are the board's own clock and ease", f"worst {worst:.2e} deg")

    try:
        import torch
    except ImportError:
        t.ok(True, "torch is not installed here: the GPU parts were not checked", "pip install torch")
        return
    from tools.rl_compare.env import DanceEnv
    from tools.rl_compare.kin import TorchRig
    from tools.rl_compare.metrics import Scorer
    from tools.rl_compare.reference import Dance, DenseReference
    from tools.rl_compare.servo import ServoModel
    kin = TorchRig(rig, facts, dtype=torch.float64)
    tree = NongTree(rig, facts)
    P = torch.tensor(poses, dtype=torch.float64)
    pts = kin.points(P)
    err = 0.0
    for k, p in enumerate(poses[:60]):
        flat = list(p)
        flat[8] = rig["zero"][8]                       # Studio's body frame: waist removed
        ref = tree.forward(flat)
        err = max(err, max(float(np.abs(ref[n] - pts[n][k].numpy()).max()) for n in TorchRig.POINTS))
    t.ok(err < 1e-6, "GPU kinematics put every joint where Studio's tree does", f"worst {err:.2e} mm")

    # approximate clearance vs Studio's own checker
    gap = facts.clear_mm + (rig.get("extraClearanceMm") or 0)
    approx = kin.clearance(pts).numpy()
    with tempfile.TemporaryDirectory() as tmp:
        src, out = Path(tmp) / "p.json", Path(tmp) / "o.json"
        src.write_text(json.dumps(poses))
        subprocess.run(["node", str(F.CODE / "tools" / "rl_compare" / "studio_eval.cjs"), str(src), str(out), "0"], check=True)
        verdict = json.loads(out.read_text())
    flags = np.array(verdict["flags"], bool)
    missed = flags & (approx >= gap + 2.0)
    t.ok(flags.any() and (~flags).any(), "the random poses include both clear and flagged ones",
         f"{int(flags.sum())} of {len(flags)} flagged by Studio")
    t.ok(not missed.any(), "the RL clearance never calls a pose clear that Studio flags (2 mm tolerance)",
         f"{int(missed.sum())} missed; worst approx gap there {float(approx[flags].max()):.1f} mm, gap {gap} mm")
    home = kin.clearance(kin.points(torch.tensor([rig["home"]], dtype=torch.float64))).item()
    t.ok(home > gap, "home is clear", f"{home:.1f} mm")

    # a synthetic dance: a smooth wander through safe poses, the dancer = the rig itself
    safe = [p for p, f in zip(poses, flags) if not f][:8]
    hz, fps, seg = 50, 6, 2.0
    frames = []
    for a, b in zip(safe, safe[1:]):
        for k in range(int(seg * hz)):
            e = 0.5 - 0.5 * math.cos(math.pi * k / (seg * hz))
            frames.append([x + (y - x) * e for x, y in zip(a, b)])
    q = torch.tensor(frames, dtype=torch.float64)
    step = hz // fps
    sample = q[::step]
    bones = kin.bones(kin.points(sample)).numpy()
    n = len(sample)
    dance = Dance(name="synthetic", times=np.arange(n) * step / hz, bones=bones, arm_ok=np.ones((n, 2), bool),
                  body=sample[:, 8:].numpy(), body_ok=np.ones(n, bool), ik=sample.numpy(), start_pose=safe[0],
                  project={}, source={"id": "none", "from": 0})
    scorer = Scorer(dance, rig, kin, {"limitDeg": 0.5}, hz, gap)
    same = scorer.score(q, q)
    t.ok(same["boneMusicDeg"] < 0.5 and same["boneShapeDeg"] < 0.5 and abs(same["driftMedianS"]) < 0.2,
         "the dancer's own motion scores ~0 on the song clock and the shape",
         f"music {same['boneMusicDeg']:.2f}, shape {same['boneShapeDeg']:.2f}, drift {same['driftMedianS']:.2f} s")
    slow = torch.repeat_interleave(q, 2, 0)
    late = scorer.score(slow, slow)
    t.ok(late["boneShapeDeg"] < 1.0, "half speed keeps the shape (the warp finds it)", f"{late['boneShapeDeg']:.2f} deg")
    t.ok(late["boneMusicDeg"] > 5 * max(0.5, same["boneMusicDeg"]) and late["driftEndS"] > 0.4 * dance.length
         and 1.8 < late["lengthRatio"] < 2.2,
         "half speed is late and wrong on the song clock, and twice as long",
         f"music {late['boneMusicDeg']:.1f} deg, end {late['driftEndS']:.1f} s late, x{late['lengthRatio']:.2f}")

    # servo and policy commands obey the speed rules and the joint range
    servo = ServoModel(rig, facts, cfg["servo"], dtype=torch.float64)
    jump = torch.tensor([rig["min"], rig["max"]] * 20, dtype=torch.float64)
    follow = servo.follow(jump, jump[0])
    speed = (follow.diff(dim=0).abs() / servo.dt - servo.vmax).max().item()
    t.ok(speed < 1e-6, "the servo never turns faster than its rated speed", f"over by {speed:.2e} deg/s")
    rc = dict(cfg["rl"], envs=64, collisionMm=gap, nearMm=cfg["metrics"]["nearMm"])
    env = DanceEnv(DenseReference(dance, rc["controlHz"]), kin, servo, 60, rc, "cpu")
    env.reset()
    before = env.c.clone()
    obs, rew, done, trunc = env.step(torch.ones(64, 10, dtype=torch.float64) * 5)
    moved = (env.c - before).abs().max().item()
    cap = min(60.0, servo.vmax.min().item()) / rc["controlHz"]
    t.ok(moved <= cap + 1e-9, "one decision moves a command no more than the 60 deg/s cap allows",
         f"{moved:.3f} <= {cap:.3f} deg")
    for _ in range(80):
        obs, rew, done, trunc = env.step(torch.ones(64, 10, dtype=torch.float64))
    t.ok(bool(((env.c >= kin.lo - 1e-9) & (env.c <= kin.hi + 1e-9)).all()), "commands never leave the joint range", "")
    t.ok(bool(torch.isfinite(obs).all() and torch.isfinite(rew).all()), "observations and rewards stay finite", "")

    # A stopped run carries on (lab 2026-10-28: stopped at 12/20, a rerun began
    # at round 1). Two rounds, then the same run asked for three: only round 3
    # trains, it starts from round 2's weights, and rounds 1-2 are kept as saved.
    import shutil
    from tools.rl_compare.rl import RLRun
    make = lambda dev: (TorchRig(rig, facts, dev), ServoModel(rig, facts, cfg["servo"], dev))
    tiny = dict(rc, envs=4, rounds=2, updatesPerRound=1, ppo=dict(rc["ppo"], steps=8, epochs=1))
    scen = {"id": "qc", "safeDps": 60}
    folder = Path(tempfile.mkdtemp(prefix="mice_rl_resume_"))
    try:
        first = RLRun(dance, make, scen, tiny, "cpu", folder).train()
        saved = torch.load(folder / "round_02" / "policy.pt")
        more = RLRun(dance, make, scen, dict(tiny, rounds=3), "cpu", folder)
        trained = []
        more.ppo.update = (lambda real: lambda b: trained.append(1) or real(b))(more.ppo.update)
        kept = more.resume()
        same_w = all(torch.equal(saved[k], v) for k, v in more.model.state_dict().items())
        t.ok(len(kept) == 2 and same_w, "a stopped run reloads its last finished round's weights",
             f"{len(kept)} rounds kept, weights equal {same_w}")
        rounds = more.train()
        t.ok([r["round"] for r in rounds] == [1, 2, 3] and len(trained) == 1 and rounds[:2] == first,
             "the rerun trains only the missing round and keeps the saved ones",
             f"rounds {[r['round'] for r in rounds]}, updates run {len(trained)}")
        t.ok((folder / "round_02" / "train_state.pt").exists() and rounds[2].get("resumedAt") == 3,
             "each round saves the optimizer too, and the resumed round says so", str(rounds[2].get("resumedAt")))
        changed = RLRun(dance, make, scen, dict(tiny, rounds=3, seed=tiny["seed"] + 1), "cpu", folder)
        try:
            changed.resume()
            refused = False
        except SystemExit:
            refused = True
        t.ok(refused, "a changed config is not resumed into the old rounds (needs --fresh)", "")
    finally:
        shutil.rmtree(folder, ignore_errors=True)
