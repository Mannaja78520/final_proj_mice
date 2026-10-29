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
- the board-clock sampler matches tools/nong_sim BoardClock.target;
- an untrusted arm run up to fillGapS is bridged between the trusted samples
  (it used to be held, unscored, and the policy let the arm fall: user
  2026-10-29), a longer run stays held and weight 0, and scores still count
  trusted samples only;
- the shared smoothing stage keeps a move on the music clock (zero phase) and
  takes the jitter out; it is the project smoother (main_python/motion_smooth,
  A54-1) the board plays with `pass:`, so a joint that keeps going is passed
  through its keys, a flick keeps its peak, and to_sequence writes `pass:`
  steps that BoardClock plays as the curve;
- to_sequence thins the sim motion to keys within tolDeg, keeps each key's
  time, and splits the board file into chained files that each re-ask the
  pace, no more than the board follows (MAX_CHAIN) (user 2026-10-29: run RL
  on the robot; a 30 KB file crashed MOVE on 2026-10-28);
- reach fitting (user 2026-10-29: look like the dancer's lift, the shoulder
  stop keeps an exact copy out of reach) leaves low arms alone, brings every
  lift within the robot's reach, keeps lifts ordered by height and keeps the
  elbow bend.
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


def gaps_and_smoothing(t, np):
    from tools.rl_compare.reference import Dance, DenseReference, fill_gaps
    from tools.rl_compare.smooth import CommandSmoother
    n, hz = 31, 10
    times = np.arange(n) / hz
    ang = np.radians(np.linspace(0, 90, n))                    # the arm sweeps 90 deg in 3 s
    v = np.stack([np.sin(ang), -np.cos(ang), 0 * ang], 1)
    bones = np.repeat(v[:, None, None, :], 2, 1).repeat(2, 2)
    ok = np.ones((n, 2), bool)
    ok[10:15, 0] = False                                       # 0.5 s unseen: bridged
    ok[5:25, 1] = False                                        # 2 s unseen: held
    seen = bones.copy()
    seen[~ok] = 0
    out, fill = fill_gaps(times, seen, ok, 1.0)
    err = np.degrees(np.arccos(np.clip((out[10:15, 0] * bones[10:15, 0]).sum(-1), -1, 1))).max()
    t.ok(fill[10:15, 0].all() and err < 1.0, "a short unseen arm run follows the sweep between trusted samples",
         f"worst {err:.2f} deg from the true sweep")
    t.ok(not fill[:, 1].any(), "a run longer than fillGapS is not bridged", f"{int(fill[:, 1].sum())} bridged")
    d = Dance(name="gap", times=times, bones=out, arm_ok=ok, arm_fill=fill, body=np.zeros((n, 2)), body_ok=np.ones(n, bool),
              ik=np.zeros((n, 10)), start_pose=[0] * 10, project={}, source={})
    dense = DenseReference(d, hz, pad_s=0, fill_weight=0.5)
    t.ok(dense.arm_w[12, 0] == 0.5 and dense.arm_w[15, 1] == 0 and dense.arm_w[2, 1] == 1 and not dense.arm_ok[12, 0],
         "bridged frames weigh fillWeight in the reward, held ones 0, and stay out of the score",
         f"{dense.arm_w[12, 0]}, {dense.arm_w[15, 1]}, {dense.arm_w[2, 1]}")
    hz = 50
    k = np.arange(5 * hz)
    step = np.clip((k - 2 * hz) / (0.5 * hz), 0, 1)
    move = (0.5 - 0.5 * np.cos(np.pi * step))[:, None] * np.full((1, 10), 40.0)
    noisy = move + np.where(k % 2, 1.0, -1.0)[:, None]          # 1 deg jitter every frame
    from tools.nong_sim.studio import load_rig
    rig = load_rig()
    smooth = CommandSmoother({"tolDeg": 3.0, "minKeyMs": 120}, hz, [-90] * 10, [90] * 10, rig)
    sm = smooth(noisy)
    half = lambda c: int(np.argmax(c[:, 0] >= 20))
    jerk = lambda c: float(np.sqrt((np.diff(c[:, 0], 3) ** 2).mean()))
    t.ok(abs(half(sm) - half(move)) <= 1 and jerk(sm) < 0.2 * jerk(noisy),
         "smoothing keeps the move on the music clock and takes the jitter out",
         f"midpoint frame {half(sm)} vs {half(move)}, jerk {jerk(sm):.2f} vs {jerk(noisy):.2f}")
    # the shared smoother (A54-1), not a second one: a 40 deg/s ramp
    # thinned to keys is passed through, not stopped on at every key; a flick
    # there and back keeps its peak
    ramp = np.zeros((3 * hz, 10))
    ramp[:, 0] = -60 + 40 * k[:3 * hz] / hz
    ramp[:, 0] += 4 * np.sin(2 * np.pi * k[:3 * hz] / hz)      # wavy (never back): RDP keeps keys
    r = smooth(ramp)
    speed = np.abs(np.diff(r[:, 0])) * hz
    # the motion itself never goes under 15 deg/s; stopping at a key drops a
    # frame to ~2 (measured 2026-10-29: 2.4 stopping, 17.9 passing through)
    t.ok(speed[5:-5].min() > 10, "a joint that keeps going the same way passes through its keys (no stop at each key)",
         f"slowest {speed[5:-5].min():.1f} deg/s between the ends")
    flick = np.zeros((2 * hz, 10))
    flick[:, 0] = 30 * np.clip(1 - np.abs(k[:2 * hz] - hz) / (0.15 * hz), 0, 1)
    f = smooth(flick)
    t.ok(f[:, 0].max() >= 29, "a flick keeps its peak", f"peak {f[:, 0].max():.1f} of 30")


def sequence_export(t, np, cfg):
    from types import SimpleNamespace
    from tools.rl_compare.to_sequence import SequenceExport, thin
    hz = 50
    k = np.arange(10 * hz) / hz
    c = np.stack([60 + 30 * np.sin(2 * np.pi * 0.7 * k + j) for j in range(10)], 1)
    sc = cfg["sequence"]
    idx = thin(c, sc["tolDeg"], 2)
    line = np.concatenate([c[a] + (c[b] - c[a]) * np.linspace(0, 1, b - a + 1)[:-1, None] for a, b in zip(idx, idx[1:])] + [c[-1:]])
    miss = float(np.abs(line - c).max())
    t.ok(idx[0] == 0 and idx[-1] == len(c) - 1 and miss <= sc["tolDeg"] + 1e-9 and len(idx) < len(c) / 3,
         "the sim motion is thinned to keys that stay within tolDeg", f"{len(idx)} keys, worst {miss:.2f} deg")
    ex = SequenceExport(SimpleNamespace(hz=hz), sc)
    keys = ex.keys(c, idx)
    t.ok(sum(x["t"] for x in keys[1:]) == round((len(c) - 1) * 1000 / hz), "every key keeps its time on the music clock",
         str(sum(x["t"] for x in keys[1:])))
    many = keys + keys * 10                                  # longer than one file can hold
    files = ex.chunks("x_", ex.steps(many, "x.mp3"), "music 0")
    names = sorted(files)
    chained = all(("next: %s" % b) in files[a] for a, b in zip(names, names[1:])) and "next:" not in files[names[-1]]
    paced = all("  - pace: music 0\n" in f for f in files.values())
    poses = sum(f.count("- pose:") for f in files.values())
    t.ok(len(files) <= min(sc["maxFiles"], 16) and chained and paced and poses == len(many)
         and files[names[0]].count("- play:") == 1,
         "the board file is split into chained files that each ask the pace, within MAX_CHAIN",
         f"{len(files)} files, chained {chained}, paced {paced}, {poses}/{len(many)} poses")
    from tools.nong_sim.board_clock import BoardClock
    from tools.nong_sim.studio import StudioFacts, load_rig
    steps = ex.steps(keys, "x.mp3")
    passes = sum(1 for k_, _ in steps if k_ == "pass")
    moves = BoardClock(load_rig(), StudioFacts()).plan([(k_, v.split("#")[0].strip().strip('"')) for k_, v in steps])
    curved = sum(1 for m in moves if m.v0 or m.v1)
    split = all(not f.rstrip().endswith('"') or "- pass:" not in f.rstrip().splitlines()[-1] for f in files.values())
    t.ok(passes > len(keys) // 3 and curved >= passes // 2 and split,
         "the board file passes through keys (shared smoother `pass:`), the board clock plays them as the curve, and no file ends on a pass",
         f"{passes} pass steps, {curved} curved moves of {len(moves)}, split ok {split}")


def reach_fitting(t, np, kin, rig, cfg):
    from tools.rl_compare.reach import ArmReach, azimuth, elevation
    from tools.rl_compare.reference import Dance
    rc = dict(cfg["reach"], samples=100000)
    reach = ArmReach(kin, rig, rc)
    n = 72
    e = np.radians(np.linspace(-80, 85, n))                     # every height, every direction
    az = np.radians(np.linspace(-180, 175, n) * 7 % 360 - 180)
    up = np.stack([np.cos(e) * np.sin(az), np.sin(e), np.cos(e) * np.cos(az)], -1)
    fore = up * 0.6 + np.array([0, -0.8, 0])                       # a bent elbow
    fore /= np.linalg.norm(fore, axis=-1, keepdims=True)
    bones = np.stack([np.stack([up, fore], 1)] * 2, 1)            # (n, 2 arms, 2 bones, 3)
    d = Dance(name="reach", times=np.arange(n) / 10, bones=bones, arm_ok=np.ones((n, 2), bool), arm_fill=np.zeros((n, 2), bool),
              body=np.zeros((n, 2)), body_ok=np.ones(n, bool), ik=np.zeros((n, 10)), start_pose=[90] * 10, project={}, source={})
    out, _ = reach.remap(d)
    new_e, new_up = elevation(out.bones[:, :, 0]), out.bones[:, :, 0]
    top = np.array([reach.top[a][reach.bin(azimuth(new_up[:, a]))] for a in range(2)]).T
    low = elevation(up) <= rc["kneeDeg"]
    kept_low = np.abs(new_e[low] - elevation(up)[low, None]).max() if low.any() else 0
    over = float((new_e - np.maximum(top - rc["marginDeg"], rc["kneeDeg"]))[~low].max())   # never pushed below the knee
    bend = lambda b: np.degrees(np.arccos(np.clip((b[:, :, 0] * b[:, :, 1]).sum(-1), -1, 1)))
    hi = ~low
    t.ok(over <= 1e-6, "every fitted lift is within the robot's reach", f"worst {over:.2f} deg above reach - margin")
    t.ok(float(np.abs(bend(out.bones) - bend(bones)).max()) < 1e-6, "the elbow bend is kept", "")
    # a lift the robot can show in its own direction stays a lift (one across the body may flatten:
    # swinging it to the other side would not look like the dancer either)
    own = np.array([reach.top[a][reach.bin(azimuth(up))] for a in range(2)]).T
    big = (elevation(up)[:, None].repeat(2, 1) >= rc["kneeDeg"] + 30) & (own - rc["marginDeg"] >= rc["kneeDeg"] + 10)
    t.ok(big.any() and new_e[hi].min() > rc["kneeDeg"] - 1e-6 and (new_e[big] > rc["kneeDeg"] + 5).all(),
         "a lift stays a lift after fitting (30 deg+ lifts the robot can show end above knee + 5 deg)",
         f"lowest fitted big lift {new_e[big].min():.1f} deg; low arms moved at most {kept_low:.1f} deg where reachable")


def run(t):
    import numpy as np
    from tools.nong_sim.board_clock import BoardClock
    from tools.nong_sim.kinematics import NongTree
    from tools.nong_sim.studio import StudioFacts, load_rig
    cfg = json.loads((F.CODE / "config" / "rl_compare.json").read_text(encoding="utf-8"))
    ids = [v["id"] for v in cfg["planner"]["variants"]] + [cfg["rl"]["id"]]
    t.ok(len(set(ids)) == len(ids), "every contender has its own id", str(ids))
    t.ok(cfg["out"].startswith(".local"), "results go to the git-ignored .local folder", cfg["out"])
    gaps_and_smoothing(t, np)
    sequence_export(t, np, cfg)
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
    reach_fitting(t, np, kin, rig, cfg)

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
                  arm_fill=np.zeros((n, 2), bool),
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
    # lift reward (user 2026-10-29: follow the lifts more): with only the lift term on, an arm at the
    # dancer's height earns more than the same arm 40 deg lower, and lift 0 changes nothing
    only = {k: 0.0 for k in ("bone", "body", "smooth", "near", "limit")}
    lw = dict(rc, reward=dict(rc["reward"], **only, lift=1.0, liftSigmaDeg=10))
    le = DanceEnv(DenseReference(dance, rc["controlHz"]), kin, servo, 60, lw, "cpu")
    le.reset()
    le.t = torch.zeros_like(le.t)                                  # every robot at the song's first sample
    q0 = torch.as_tensor(dance.ik[0], dtype=torch.float64).repeat(64, 1)
    def lift_reward(q):
        le.q = q
        r, _ = le._reward(kin.points(q), torch.zeros_like(q), q)
        return r
    at = lift_reward(q0).mean().item()
    low = q0.clone(); low[:, [0, 4]] = torch.where(low[:, [0, 4]] > 90, low[:, [0, 4]] - 50, low[:, [0, 4]] + 50)  # the arm 50 deg off its pitch
    t.ok(at > lift_reward(low).mean().item(), "the lift reward pays an arm at the dancer's height more",
         f"{at:.3f} vs {lift_reward(low).mean().item():.3f}")
    le.w = dict(rc["reward"], lift=0.0)
    base = lift_reward(q0)
    le.w = dict(rc["reward"])
    t.ok(bool(torch.allclose(base, lift_reward(q0))) or rc["reward"].get("lift", 0) != 0,
         "lift 0 (the default) leaves the reward as it was", "")

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
