"""The synthetic accuracy table in docs/experiments/2026-10-28_robot_pose.md.

    python -m tools.robot_pose.bench            -> .local/robot_pose/bench_<date>.json

Per cell: 8 camera azimuths x 3 random poses, camera 1400 mm away, 15 deg up,
60 deg fov, 640x480; Gaussian pixel noise; the fit starts at the truth plus
N(0, 10 deg) per joint (a command the robot did not quite follow).
"""
import json
import time
from pathlib import Path

import numpy as np

from .camera import Camera
from .fit import PoseFitter
from .synth import SynthViews

ROOT = Path(__file__).resolve().parents[2]


def joint_errors(ncam, noise, seed=0):
    sv = SynthViews(seed=3)
    f = PoseFitter(sv.kp)
    rng = np.random.default_rng(seed)
    errs = []
    for az in range(0, 360, 45):
        for _ in range(3):
            cams = [Camera.orbit(az + 90 * i, 15, 1400, (0, 100, 0), 60, 640, 480) for i in range(ncam)]
            pose = sv.pose()
            vs = [sv.view(pose, c) for c in cams]
            start = np.clip(np.array(pose) + rng.normal(0, 10, 10), f.lo, f.hi)
            fit = f.fit_pose(cams, [v["uv"] + rng.normal(0, noise, v["uv"].shape) for v in vs],
                             [(v["vis"] == 2) * 1.0 for v in vs], start)
            errs.append(np.abs(np.array(fit.pose) - pose))
    return np.array(errs)


def main():
    rows = []
    for ncam in (1, 2):
        for noise in (0.0, 1.0, 2.0):
            t0 = time.time()
            e = joint_errors(ncam, noise)
            rows.append({"cameras": ncam, "noisePx": noise, "trials": len(e), "meanDegPerJoint": e.mean(0).round(2).tolist(),
                         "medianDeg": float(np.median(e)), "p90Deg": float(np.percentile(e, 90)),
                         "s": round(time.time() - t0, 1)})
            print(rows[-1], flush=True)
    out = ROOT / ".local" / "robot_pose" / ("bench_%s.json" % time.strftime("%Y-%m-%d"))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rows, indent=1), encoding="utf-8")
    print("->", out)


if __name__ == "__main__":
    main()
