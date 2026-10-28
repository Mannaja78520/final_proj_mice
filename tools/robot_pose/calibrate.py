"""Auto-calibration SUGGESTIONS from frames whose command is known.

Fits, together with the camera(s): each joint's offset (where it really sits
minus where it was told to be) and the arm lengths / shoulder spots listed in
config/robot_pose.json calibrate. Nothing is written to the rig: the user's
rule (2026-10-23) is that axes, senses, zero and home are tuned to the real
robot by hand, so this only says what it measured.
torsoH is never fitted: it holds the scale (a bigger robot further away looks
the same). The waist offset is fixed for the reason in the config.
"""
import copy

import numpy as np

from .keypoints import RobotKeypoints
from .solver import least_squares


class Calibrator:
    def __init__(self, kp=None, cfg=None):
        self.kp = kp or RobotKeypoints(cfg=cfg)
        self.cfg = self.kp.cfg if cfg is None else cfg
        self.cc = self.cfg["calibrate"]
        names = list(self.kp.facts.joint_names)
        self.free = [j for j, n in enumerate(names) if n not in self.cc["zeroFixed"]]
        self.lengths = list(self.cc["lengths"])
        self._cache = {}

    def _kp(self, dims):
        key = tuple(np.round(dims, 6))
        if key not in self._cache:
            rig = copy.deepcopy(self.kp.rig)
            rig["dims"].update(dict(zip(self.lengths, map(float, dims))))
            self._cache = {key: RobotKeypoints(rig, self.kp.facts, self.cfg)}   # one entry: memory flat
        return self._cache[key]

    def run(self, cams, frames, min_conf=0.3):
        """cams: [Camera]; frames: [(commanded_pose, [kp2d per cam], [conf per cam])]."""
        nz, nd = len(self.free), len(self.lengths)
        d0 = np.array([self.kp.rig["dims"][k] for k in self.lengths], float)
        cam_p = [c.params() for c in cams]
        sizes = [len(p) for p in cam_p]
        x0 = np.concatenate([np.zeros(nz), d0] + cam_p)
        zr, lr = self.cc["zeroRangeDeg"], self.cc["lengthRangeMm"]
        lo = np.concatenate([np.full(nz, -zr), d0 - lr] + [np.full(s, -np.inf) for s in sizes])
        hi = np.concatenate([np.full(nz, zr), d0 + lr] + [np.full(s, np.inf) for s in sizes])

        def unpack(x):
            b = np.zeros(len(self.kp.rig["zero"]))
            b[self.free] = x[:nz]
            out, i = [], nz + nd
            for c, s in zip(cams, sizes):
                out.append(c.with_params(x[i:i + s]))
                i += s
            return b, x[nz:nz + nd], out

        def res(x):
            b, dims, cs = unpack(x)
            kp = self._kp(dims)
            parts = []
            for pose, uvs, confs in frames:
                P = kp.points3d(np.asarray(pose, float) + b)
                for c, uv, w in zip(cs, uvs, confs):
                    w = np.asarray(w, float)
                    p, _ = c.project(P)
                    parts.append(((p - uv) * np.sqrt(np.where(w >= min_conf, w, 0))[:, None]).ravel())
            parts.append(self.cc["priorPx"] * np.concatenate([x[:nz], (x[nz:nz + nd] - d0) / 10]))
            return np.concatenate(parts)

        x, cost = least_squares(res, x0, lo, hi, iters=80)
        b, dims, cs = unpack(x)
        names = list(self.kp.facts.joint_names)
        return {"jointOffsetDeg": {names[j]: float(b[j]) for j in self.free},
                "lengthsMm": {k: {"rig": float(a), "measured": float(m), "diff": float(m - a)}
                              for k, a, m in zip(self.lengths, d0, dims)},
                "cameras": [c.to_json() for c in cs], "cost": float(cost), "frames": len(frames),
                "note": "suggestions only; the rig is not changed"}
