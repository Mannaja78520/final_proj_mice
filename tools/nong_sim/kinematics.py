"""Nong's joint tree, built the way Studio's buildRigShapes()/applyPose() build it.

Studio frame: Y up, mm. Each joint group turns as  tilt * R(axis, delta) * after
(build_rig.js applyPose), delta = (pose - zero) * BASE_DIR * (invert ? -1 : 1).
The same tree gives a numpy forward kinematics (QC compares it with Studio's
own 3D scene, check_nong_sim) and the MuJoCo model, so the two cannot differ.
"""
import math
from dataclasses import dataclass, field

import numpy as np

AXES = {"x": (1.0, 0.0, 0.0), "y": (0.0, 1.0, 0.0), "z": (0.0, 0.0, 1.0)}
WAIST, SHRUG = 8, 9


def quat_axis(axis, rad):
    s = math.sin(rad / 2)
    return np.array([math.cos(rad / 2), axis[0] * s, axis[1] * s, axis[2] * s])


def quat_mul(a, b):
    w1, x1, y1, z1 = a
    w2, x2, y2, z2 = b
    return np.array([w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
                     w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
                     w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
                     w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2])


def quat_euler_xyz(deg):
    """THREE.Euler(x, y, z, "XYZ") as a quaternion (w, x, y, z)."""
    rx, ry, rz = (math.radians(v) for v in deg)
    return quat_mul(quat_mul(quat_axis(AXES["x"], rx), quat_axis(AXES["y"], ry)), quat_axis(AXES["z"], rz))


def quat_rotate(q, v):
    u = np.asarray(q[1:])
    v = np.asarray(v, dtype=float)
    return v + 2 * np.cross(u, np.cross(u, v) + q[0] * v)


@dataclass
class Geom:
    kind: str                 # box | sphere | capsule
    size: tuple               # box: half sizes; sphere: (r,); capsule: (r,)
    pos: tuple = (0, 0, 0)
    to: tuple = None          # capsule end
    part: str = ""


@dataclass
class Body:
    name: str
    parent: str
    pos: tuple
    quat: np.ndarray = field(default_factory=lambda: np.array([1.0, 0, 0, 0]))
    joint: int = None         # Studio joint index turned here
    axis: tuple = None
    slide: int = None         # calibrated shrug: this anchor slides in Y
    geoms: list = field(default_factory=list)
    arm: int = None           # 0 left, 1 right: same-arm parts never collide


class NongTree:
    def __init__(self, rig, facts):
        self.rig, self.facts = rig, facts
        self.bodies = []
        self.points = {}      # name -> body whose origin is that point
        self._build()

    def delta(self, pose, i):
        """Studio's jointDelta(i) in degrees."""
        sense = self.facts.base_dir[i] * (-1 if self.rig["invert"][i] else 1)
        return (pose[i] - self.rig["zero"][i]) * sense

    def shrug_rise(self, j):
        """Studio's shrugRise(): the measured 4-bar, or None (a plain rock)."""
        pts = sorted((p for p in self.rig.get("shrugCurve") or [] if "j" in p), key=lambda p: p["j"])
        if len(pts) < 2:
            return None
        if j <= pts[0]["j"]:
            return pts[0].get("l", 0), pts[0].get("r", 0)
        for a, b in zip(pts, pts[1:]):
            if j <= b["j"]:
                f = (j - a["j"]) / (b["j"] - a["j"]) if b["j"] - a["j"] > 1e-9 else 0
                return (a.get("l", 0) + (b.get("l", 0) - a.get("l", 0)) * f,
                        a.get("r", 0) + (b.get("r", 0) - a.get("r", 0)) * f)
        return pts[-1].get("l", 0), pts[-1].get("r", 0)

    def _add(self, body):
        self.bodies.append(body)
        return body.name

    def _build(self):
        d, r, f = self.rig["dims"], self.rig, self.facts
        piv = d.get("shrugPivot", 0) or 0
        calibrated = len(r.get("shrugCurve") or []) >= 2
        waist = self._add(Body("waist", "world", (0, 0, 0), joint=WAIST, axis=AXES["y"], geoms=[
            Geom("box", (d["torsoW"] / 2, d["torsoH"] / 2, d["torsoD"] / 2), part="torso"),
            Geom("sphere", (f.head_r,), (0, d["torsoH"] / 2 + 68, 0), part="head")]))
        mount = self._add(Body("mount", waist, (0, d["shoulderY"] + piv, 0),
                               joint=None if calibrated else SHRUG, axis=AXES["z"]))
        for arm, (side, key) in enumerate(((1, "L"), (-1, "R"))):
            mt = r["mount"][key]
            parent = self._add(Body(key + "_anchor", mount, (side * d["shoulderX"] + mt[0], -piv + mt[1], mt[2]),
                                    slide=SHRUG if calibrated else None, arm=arm))
            self.points["sh" + key] = parent
            order = r["order"][arm]
            pair = 0 if arm == 0 else 2
            upper, fore = d["upperLen" + key], d["foreLen" + key]
            for n, j in enumerate(order):
                bar = n in (1, 3)
                length = upper if n == 1 else fore
                pidx = pair + (0 if n < 2 else 1)
                geoms = []
                if n in (0, 2):
                    geoms.append(Geom("sphere", (r["jointR"][pidx],), part=f"{key}_joint{n // 2}"))
                if bar:
                    geoms.append(Geom("capsule", (r["barR"][pidx],), (0, 0, 0), (0, -length, 0),
                                      part=f"{key}_{'upper' if n == 1 else 'fore'}"))
                turn = self._add(Body(f"{key}_j{j}", parent, (0, 0, 0), quat_euler_xyz(r["tilt"][j]),
                                      joint=j, axis=AXES[r["axis"][j]], arm=arm))
                parent = self._add(Body(f"{key}_j{j}_after", turn, (0, 0, 0), quat_euler_xyz(r["after"][j]),
                                        geoms=geoms, arm=arm))
                if n == 1:
                    parent = self._add(Body(key + "_elbow", parent, (0, -upper, 0), arm=arm))
                    self.points["el" + key] = parent
            wrist = self._add(Body(key + "_wrist", parent, (0, -fore, 0), arm=arm,
                                   geoms=[Geom("sphere", (f.wrist_r,), part=key + "_hand")]))
            self.points["wr" + key] = wrist

    def forward(self, pose):
        """World (Studio frame, mm) position of every named point at a pose."""
        frames = {"world": (np.zeros(3), np.array([1.0, 0, 0, 0]))}
        rise = self.shrug_rise(pose[SHRUG])
        for b in self.bodies:
            p0, q0 = frames[b.parent]
            pos = np.array(b.pos, dtype=float)
            if b.slide is not None and rise:
                pos[1] += rise[0] if b.arm == 0 else rise[1]
            q = quat_mul(q0, b.quat)
            if b.joint is not None:
                q = quat_mul(q, quat_axis(b.axis, math.radians(self.delta(pose, b.joint))))
            frames[b.name] = (p0 + quat_rotate(q0, pos), q)
        return {k: frames[v][0] for k, v in self.points.items()}
