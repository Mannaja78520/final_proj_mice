"""From 2D keypoints to nong's joint angles, the camera, and which way it faces.

Static camera, robot on its base: fit the camera ONCE from frames whose pose is
known (home, a hold), then each frame is only the 10 joint angles, which 12
keypoints (24 numbers) pin down. A single photo from an unknown camera is the
same fit with the camera free too (fit_view), started from every yaw in the
config so front and back are both tried.

Left/right: every fit is also tried with the L_/R_ keypoints swapped, so a
detector that names the arms by image side cannot flip the answer. Front/back:
a `seenFrom: front` keypoint (the chest marker) must be on the camera's side
of the neck when the detector sees it, and behind it when it does not.
"""
import math
from dataclasses import dataclass

import numpy as np

from .camera import Camera
from .keypoints import RobotKeypoints
from .solver import least_squares

TARGET_Y = 100.0   # mm: the camera looks at mid-torso when it is guessed


@dataclass
class Fit:
    pose: list
    camera: Camera
    rms_px: float
    swapped: bool
    facing_deg: float
    facing: str
    used: int          # keypoints confident enough to use


class PoseFitter:
    def __init__(self, kp=None, cfg=None):
        self.kp = kp or RobotKeypoints(cfg=cfg)
        self.cfg = self.kp.cfg if cfg is None else cfg
        self.fc = self.cfg["fit"]
        rig = self.kp.rig
        self.lo, self.hi = np.array(rig["min"], float), np.array(rig["max"], float)
        self.front_only = [i for i, k in enumerate(self.kp.kps) if k.get("seenFrom") == "front"]
        self.neck = self.kp.index.get("neck", 0)

    # ---- pieces -----------------------------------------------------------
    def guess_camera(self, azimuth):
        c = self.cfg["camera"]
        return Camera.orbit(azimuth, math.degrees(math.atan2(c["heightMm"] - TARGET_Y, c["distanceMm"])),
                            c["distanceMm"], (0, TARGET_Y, 0), c["fovDeg"], c["width"], c["height"])

    def _obs(self, kp2d, conf, swap):
        kp2d, conf = np.asarray(kp2d, float), np.asarray(conf, float)
        if swap:
            kp2d, conf = kp2d[self.kp.flip], conf[self.kp.flip]
        return kp2d, conf

    def residual(self, cam, pose, kp2d, conf, prior=None):
        P = self.kp.points3d(pose)
        uv, z = cam.project(P)
        use = conf >= self.fc["minConf"]
        w = np.sqrt(np.where(use, conf, 0.0))
        r = [((uv - kp2d) * w[:, None]).ravel()]
        m, sw = self.fc["seenMarginMm"], self.fc["seenWeight"]
        for i in self.front_only:            # in front of the neck = facing the camera
            ahead = z[self.neck] - z[i]       # +-m is a dead band: a side view is neither
            inside = cam.width is None or (0 <= uv[i, 0] < cam.width and 0 <= uv[i, 1] < cam.height)
            r.append([sw * max(0.0, -ahead - m) if use[i] else sw * max(0.0, ahead - m) if inside else 0.0])
        if prior is not None:
            r.append(self.fc["priorWeight"] * (np.asarray(pose) - np.asarray(prior)))
        return np.concatenate([np.ravel(x) for x in r])

    def rms(self, cam, pose, kp2d, conf):
        uv, _ = cam.project(self.kp.points3d(pose))
        use = conf >= self.fc["minConf"]
        return float(np.sqrt(np.mean(np.sum((uv[use] - kp2d[use]) ** 2, 1)))) if use.any() else float("inf")

    def facing(self, cam, pose):
        """Degrees from the robot's front to the camera, about its up axis: 0 front, 90 left."""
        f = self.kp.front(pose)
        left = np.cross([0.0, 1.0, 0.0], f)
        v = cam.center - np.array([0.0, TARGET_Y, 0.0])
        deg = math.degrees(math.atan2(v @ left, v @ f)) % 360
        for lab in self.cfg["facing"]["labels"]:
            lo, hi = lab["from"] % 360, lab["to"] % 360
            if (lo <= deg < hi) if lo < hi else (deg >= lo or deg < hi):
                return deg, lab["id"]
        return deg, "?"

    def _result(self, cam, pose, kp2d, conf, swapped):
        deg, label = self.facing(cam, pose)
        return Fit(list(map(float, pose)), cam, self.rms(cam, pose, kp2d, conf), swapped, deg, label,
                   int((conf >= self.fc["minConf"]).sum()))

    # ---- fits ---------------------------------------------------------------
    def _views(self, cams, kp2d, conf, swap):
        """One camera or several (a list each): -> [(cam, obs, conf)]."""
        if isinstance(cams, Camera):
            cams, kp2d, conf = [cams], [kp2d], [conf]
        return [(c,) + self._obs(k, w, swap) for c, k, w in zip(cams, kp2d, conf)]

    def _one(self, views, start, prior, swap):
        def res(q):
            parts = [self.residual(c, q, o, w) for c, o, w in views]
            parts.append(self.fc["priorWeight"] * (q - np.asarray(prior)))
            return np.concatenate(parts)
        x, cost = least_squares(res, start, self.lo, self.hi, iters=self.fc["iterations"])
        cam, o, w = views[0]
        fit = self._result(cam, x, o, w, swap)
        fit.rms_px = float(np.mean([self.rms(c, x, oo, ww) for c, oo, ww in views]))
        fit.cost = cost
        return fit

    def fit_pose(self, cams, kp2d, conf, start, rng=None):
        """Joint angles for one frame, camera(s) known. start: last frame's pose or the command.

        ONE camera cannot tell an elbow bent toward it from one bent away, nor a
        small waist turn left from right (the shoulders move in depth only): the
        fit lands on the answer nearest `start`. TWO cameras (front + side, a
        list each) remove that. A bad fit (rms > restartPx) is tried again from
        random poses; facing is given for the first camera."""
        rng = rng or np.random.default_rng(0)
        views = self._views(cams, kp2d, conf, False)
        best = self._one(views, start, start, False)
        for _ in range(self.fc["restarts"] if best.rms_px > self.fc["restartPx"] else 0):
            f = self._one(views, rng.uniform(self.lo, self.hi), start, False)
            if f.cost < best.cost:
                best = f
        if best.rms_px > self.fc["swapTryPx"]:
            f = self._one(self._views(cams, kp2d, conf, True), start, start, True)
            if f.cost < self.fc["swapMargin"] * best.cost:
                best = f
        return best

    def fit_camera(self, frames, guess=None):
        """frames: [(kp2d, conf, known_pose)]. -> Camera. Tries every yaw start."""
        starts = [guess] if guess else [self.guess_camera(a) for a in self.fc["yawStarts"]]
        best = None
        for g in starts:
            def res(p):
                cam = g.with_params(p)
                return np.concatenate([self.residual(cam, pose, np.asarray(k, float), np.asarray(c, float))
                                       for k, c, pose in frames])
            p, cost = least_squares(res, g.params(), iters=self.fc["iterations"] * 2)
            if best is None or cost < best[1]:
                best = (g.with_params(p), cost)
        return best[0]

    def fit_view(self, kp2d, conf, start=None):
        """One photo, camera unknown: camera and pose together, every yaw start, both L/R names."""
        start = np.asarray(start if start is not None else self.kp.rig["home"], float)
        best = None
        for swap in (False, True):
            o, c = self._obs(kp2d, conf, swap)
            for a in self.fc["yawStarts"]:
                g = self.guess_camera(a)
                n = len(g.params())

                def res(x):
                    return self.residual(g.with_params(x[:n]), x[n:], o, c, start)
                lo = np.concatenate([np.full(n, -np.inf), self.lo])
                hi = np.concatenate([np.full(n, np.inf), self.hi])
                x, cost = least_squares(res, np.concatenate([g.params(), start]), lo, hi,
                                        iters=self.fc["iterations"] * 2)
                if best is None or cost < best[0]:
                    best = (cost, g.with_params(x[:n]), x[n:], o, c, swap)
        cost, cam, pose, o, c, swap = best
        fit = self._result(cam, pose, o, c, swap)
        fit.cost = cost
        return fit
