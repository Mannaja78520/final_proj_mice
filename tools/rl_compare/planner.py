"""Contender 1: the planner Nong uses now, run as Studio runs it.

planner.cjs loads Studio's own parts in Node and calls vidBuild (IK fit ->
picks -> collision-safe keys, RRT round a hit) with the scenario's SAFE_DPS,
timing it. The keys are then played on the board's clock exactly as the
firmware would (tools/nong_sim BoardClock: a move the servos or the safety cap
cannot make in time is lengthened), sampled at the board's 50 Hz.
"""
import json
import math
import subprocess
from pathlib import Path

import numpy as np

from tools.nong_sim.board_clock import BoardClock

HERE = Path(__file__).resolve().parent


class PlannerRun:
    def __init__(self, variant, scenario, facts, extra_mm):
        self.variant, self.scenario, self.facts, self.extra_mm = variant, scenario, facts, extra_mm
        self.safe_dps = scenario["safeDps"] or facts.max_dps

    def make_keys(self, folder, dance, out_path, repeats):
        """Run Studio's planner once (cached: the result does not change)."""
        out_path = Path(out_path)
        if not out_path.exists():
            out_path.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(["node", str(HERE / "planner.cjs"), str(Path(folder) / f"{dance}_analysis.json"),
                            str(Path(folder) / f"{dance}.json"), str(out_path), str(self.safe_dps),
                            "1" if self.variant["music"] else "0", str(self.extra_mm), str(repeats)], check=True)
        return json.loads(out_path.read_text(encoding="utf-8"))

    @staticmethod
    def steps(keys):
        out = []
        for k in keys:
            out.append(("pose", " ".join("%g" % v for v in k["pose"]) + " T %d" % max(1, round(k["t"]))))
            if k.get("hold"):
                out.append(("wait", str(k["hold"])))
        return out

    def commands(self, rig, keys, hz):
        """Board targets at hz from the moment the music starts (end of the entry move)."""
        clock = BoardClock(rig, self.facts, self.safe_dps)
        moves = clock.plan(self.steps(keys))
        start = moves[0].start + moves[0].took
        starts = np.array([m.start for m in moves])
        took = np.array([m.took for m in moves])
        a = np.array([m.start_pose for m in moves])
        b = np.array([m.pose for m in moves])
        t = start + np.arange(int(math.ceil((clock.length - start) * hz)) + 1) / hz
        i = np.clip(np.searchsorted(starts, t, side="right") - 1, 0, len(moves) - 1)
        f = np.clip((t - starts[i]) / np.maximum(1e-9, took[i]), 0, 1)
        e = (0.5 - 0.5 * np.cos(np.pi * f))[:, None]
        return a[i] + (b[i] - a[i]) * e, {"boardLengthS": clock.length - start,
                                           "lengthened": sum(1 for m in moves if m.took > m.asked + 1e-6)}
