"""Turn a contender's sim motion (RL, hybrid) into a sequence the board plays.

User 2026-10-29: run the RL dance on the real robot tonight. The policy gives
50 Hz commands; the board plays pose steps, each a cosine ease that stops at
its key, and a long file crashed MOVE on 2026-10-28. So the commands are
thinned to keys (Ramer-Douglas-Peucker: a key wherever the straight line
between kept keys misses the motion by more than tolDeg), every key keeps its
own time on the music clock, and the file asks `pace: music 0` (servo limits
only, NongModule PACE) so the board does not stretch it.

The file is then played back exactly as the board would (BoardClock + servo
model) and scored and collision-checked like every contender, as
<contender>_board. Nothing is written if Studio flags a touch.

    python -m tools.rl_compare.to_sequence --dance come_and_cheer_center_30fps \
        --data-dir .local/cheer_rig_1029_30fps --out .local/rl_compare_30fps --contender hybrid
"""
import argparse
import json
import sys

import numpy as np
import torch

from tools.nong_sim.board_clock import BoardClock

from . import run as R


def thin(c, tol, min_gap):
    """Indices of the keys kept (RDP on all 10 joints, max abs deviation)."""
    keep = {0, len(c) - 1}
    stack = [(0, len(c) - 1)]
    while stack:
        a, b = stack.pop()
        if b - a < 2 * min_gap:
            continue
        f = np.linspace(0, 1, b - a + 1)[:, None]
        line = c[a] + (c[b] - c[a]) * f
        dev = np.abs(c[a:b + 1] - line).max(1)
        dev[:min_gap] = dev[-min_gap:] = 0
        i = int(dev.argmax())
        if dev[i] > tol:
            keep.add(a + i)
            stack += [(a, a + i), (a + i, b)]
    return sorted(keep)


class SequenceExport:
    def __init__(self, case, cfg):
        self.case, self.cfg = case, cfg
        self.hz = case.hz

    def keys(self, c, idx):
        keys = [{"pose": np.round(c[0], 1).tolist(), "t": self.cfg["entryMs"], "hold": 0}]
        for a, b in zip(idx, idx[1:]):
            keys.append({"pose": np.round(c[b], 1).tolist(), "t": round((b - a) * 1000 / self.hz), "hold": 0})
        return keys

    def close_frames(self, q):
        """Board frames closer than the scenario gap + marginMm (kin's fast approx)."""
        kin = self.case.kin
        gap = kin.clearance(kin.points(torch.as_tensor(q, dtype=kin.dtype))).numpy()
        return np.flatnonzero(gap < self.case.gap + self.cfg["marginMm"])

    def build(self, c, music):
        """Thin, play, and wherever the played file comes too close (the straight
        line between two keys cut a corner the sim motion went round), keep the
        sim key there too and play again. The board may run a little late, so a
        close frame is traced back to the step being played, not the same index."""
        idx = set(thin(c, self.cfg["tolDeg"], max(1, int(self.cfg["minKeyMs"] / 1000 * self.hz))))
        for attempt in range(self.cfg["refineRounds"] + 1):
            keys = self.keys(c, sorted(idx))
            steps = self.steps(keys, music)
            played, info = self.play(steps)
            q = self.case.servo.follow(torch.as_tensor(played, dtype=self.case.kin.dtype)).numpy()
            bad = self.close_frames(q)
            if not len(bad):                                   # kin's approx is clear: ask Studio itself
                self.case.studio_check(q, "to_sequence_probe")
                bad = np.flatnonzero(self.case.last_flags)
            info["refineRounds"] = attempt
            if not len(bad):
                break
            order = sorted(idx)
            starts = np.array([m.start for m in self.moves])
            added = set()
            for f in bad:
                j = int(np.searchsorted(starts, self.music_at + f / self.hz, side="right") - 1)
                for k in (j, j - 1):                        # this step, and the one the servo still lags
                    if 1 <= k < len(order) and order[k] - order[k - 1] >= 2:
                        added.add((order[k] + order[k - 1]) // 2)
            if not added:
                break
            idx |= added
        return keys, steps, played, q, info

    def steps(self, keys, music):
        out = [("pace", "music 0"), ("pose", self.pose(keys[0]) + "    # start pose"), ("play", music)]
        return out + [("pose", self.pose(k)) for k in keys[1:]]

    @staticmethod
    def pose(k):
        return '"' + " ".join("%g" % v for v in k["pose"]) + " T %d" % k["t"] + '"'

    def play(self, steps):
        """Commands at the board's 50 Hz from the music cue, as the firmware runs them."""
        clock = BoardClock(self.case.exp.rig, self.case.exp.facts)        # today's firmware cap, then PACE
        moves = clock.plan([(k, v.split("#")[0].strip().strip('"')) for k, v in steps])
        t = clock.music_at + np.arange(int((clock.length - clock.music_at) * self.hz) + 1) / self.hz
        c = np.array([BoardClock.target(moves, x) for x in t])
        late = sum(1 for m in moves if m.took > m.asked + 1e-6)
        self.moves, self.music_at = moves, clock.music_at
        return c, {"boardLengthS": clock.length - clock.music_at, "lengthened": late, "keys": len(moves)}

    def chunks(self, prefix, steps, pace="music 0"):
        """The same steps as chained files (`next:`), each re-asking the pace: a
        30 KB file crashed MOVE on 2026-10-28 and the board follows at most
        SequencePlayer MAX_CHAIN (16) files, so at most maxFiles of them."""
        head, poses = steps[:3], steps[3:]
        per = max(self.cfg["perFile"], -(-len(poses) // self.cfg["maxFiles"]))
        parts = [poses[i:i + per] for i in range(0, len(poses), per)]
        out = {}
        for i, part in enumerate(parts):
            name = "%s%02d" % (prefix, i)
            lines = ["name: " + name, "loop: false"]
            if i + 1 < len(parts):
                lines.append("next: %s%02d.yaml" % (prefix, i + 1))
            first = [("pace", pace)] + head[1:]
            body = (first if i == 0 else [("pace", pace)]) + part
            out[name + ".yaml"] = "\n".join(lines + ["steps:"] + ["  - %s: %s" % s for s in body]) + "\n"
        return out

    def yaml(self, name, steps):
        head = ["# made by tools/rl_compare/to_sequence.py from the %s sim motion" % self.cfg["contender"],
                "# pose order: L_SH_P L_SH_R L_EL_P L_EL_R R_SH_P R_SH_R R_EL_P R_EL_R WAIST SHRUG  (joint deg, T = ms)",
                "# pace: music 0 = servo limits only (no 60 deg/s cap). Ramp up in the lab: see the README.",
                "name: " + name, "loop: false", "steps:"]
        return "\n".join(head + ["  - %s: %s" % s for s in steps]) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dance", required=True)
    ap.add_argument("--scenario", default="servo_5mm")
    ap.add_argument("--data-dir")
    ap.add_argument("--out")
    ap.add_argument("--contender", default="hybrid")
    ap.add_argument("--name", help="sequence name (default <dance>_<contender>)")
    ap.add_argument("--ramp", default="120,240,0",
                    help="lab ramp: one chained set per pace cap in deg/s, 0 = servo max (the scored one)")
    ap.add_argument("--prefix", default="rl_", help="chained file names <prefix>NN.yaml and <prefix>.mp3 (keep short)")
    a = ap.parse_args(argv)
    exp = R.Experiment(argparse.Namespace(quick=False, dance=[a.dance], scenario=[a.scenario], data_dir=a.data_dir,
                                          out=a.out, fresh=False, no_video=True))
    case = R.Case(exp, a.dance, exp.scenarios[0])
    cfg = dict(exp.cfg["sequence"], contender=a.contender)
    ex = SequenceExport(case, cfg)
    src = np.load(case.out / f"{a.contender}_motion.npz")["c"]
    name = a.name or f"{a.dance}_{a.contender}"
    keys, steps, c, q, info = ex.build(src, a.prefix.rstrip("_") + ".mp3")
    row = case.scored(f"{a.contender}_board", f"{a.contender} as a board sequence", (200, 200, 200), c, q, info)
    s = row["score"]
    print(json.dumps({k: round(v, 2) if isinstance(v, float) else v for k, v in s.items()
                      if k in ("boneMusicDeg", "boneMusicWorstP95Deg", "jerkRms", "driftEndS", "minGapMmApprox",
                               "collisionFramesApprox", "boardLengthS", "lengthened", "keys", "refineRounds")}), flush=True)
    print("studio", json.dumps({k: v for k, v in s["studio"].items() if k != "reasons"}), flush=True)
    if s["studio"].get("flagged") or s["collisionFramesApprox"]:
        print("NOT WRITTEN: the played motion touches", flush=True)
        return 1
    out = case.out / f"{name}.yaml"
    out.write_text(ex.yaml(name, steps), encoding="utf-8")
    print("wrote", out, len(keys), "keys", flush=True)
    folder = case.out / f"{name}_board" / "moves"
    folder.mkdir(parents=True, exist_ok=True)
    for old in folder.glob("*.yaml"):
        old.unlink()
    for cap in [int(x) for x in a.ramp.split(",")]:
        files = ex.chunks("%s%03d_" % (a.prefix, cap), steps, "music %d" % cap)
        for fname, text in files.items():
            (folder / fname).write_bytes(text.encode("utf-8"))
        print("   cap %d: %s ... %d files, largest %d bytes" % (cap, min(files), len(files), max(map(len, files.values()))), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
