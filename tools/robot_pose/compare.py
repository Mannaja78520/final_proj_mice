"""Seen against commanded: per joint error, servo lag, stuck joints, a verdict.

`seen` is what the camera fit says the robot did; `commanded` is what the board
was told, on the board's own clock (tools/nong_sim BoardClock, the same rules
the firmware plays a file by). Thresholds are config/robot_pose.json compare.
"""
import numpy as np

from tools.nong_sim.board_clock import BoardClock, parse_sequence


def commanded_from_sequence(text, rig, facts, safe_dps=None):
    """t (s from the first step) -> the pose the board commands then."""
    clock = BoardClock(rig, facts, safe_dps)
    moves = clock.plan(parse_sequence(text))
    return lambda t: BoardClock.target(moves, t), clock.length


class MoveCheck:
    def __init__(self, joint_names, cfg):
        self.names, self.c = list(joint_names), cfg["compare"]

    def run(self, times, seen, commanded):
        """times (N,), seen (N, J) deg, commanded: t -> pose. -> report dict."""
        times, seen = np.asarray(times, float), np.asarray(seen, float)
        cmd = lambda shift: np.array([commanded(t - shift) for t in times], float)
        lags = np.arange(-self.c["lagSearchS"], self.c["lagSearchS"] + 1e-9, self.c["lagStepS"])
        # the lag is found with each joint's own bias taken out, or a shift would
        # be "found" that cancels part of an offset (a 9 deg offset read as 0.3 s)
        def spread(e):
            return np.abs(e - np.median(e, 0)).mean(0)
        err_by_lag = np.array([spread(seen - cmd(L)) for L in lags])      # (lags, J)
        c0 = cmd(0.0)
        joints = []
        for j, name in enumerate(self.names):
            k = int(np.argmin(err_by_lag[:, j]))
            cj = cmd(lags[k])[:, j]
            e = seen[:, j] - cj
            moved, saw = np.ptp(c0[:, j]), np.ptp(seen[:, j])
            p95 = float(np.percentile(np.abs(e), 95))
            stuck = bool(moved >= self.c["stuckMoveDeg"] and saw <= self.c["stuckSeenDeg"])
            verdict = "stuck" if stuck else "ok" if p95 <= self.c["okDeg"] else \
                "warn" if p95 <= self.c["warnDeg"] else "bad"
            joints.append({"joint": name, "verdict": verdict, "lagS": float(lags[k]),
                           "meanAbsDeg0": float(np.abs(seen[:, j] - c0[:, j]).mean()),
                           "meanAbsDeg": float(np.abs(e).mean()), "p95Deg": p95,
                           "maxDeg": float(np.abs(e).max()), "biasDeg": float(e.mean()),
                           "commandedRangeDeg": float(moved), "seenRangeDeg": float(saw)})
        order = ["ok", "warn", "bad", "stuck"]
        return {"frames": int(len(times)), "joints": joints,
                "verdict": max((j["verdict"] for j in joints), key=order.index) if joints else "ok"}
