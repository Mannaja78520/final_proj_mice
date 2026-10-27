"""Batched (torch) forward kinematics and an approximate clearance for Nong.

The joint tree is tools/nong_sim NongTree (itself held to Studio's 3D scene by
check_nong_sim); this file only evaluates that tree for thousands of poses at
once on the GPU. Everything is in Studio's body frame (bodyGroup: the waist
yaw removed), the frame the dancer's bones and Studio's collision check use.

Clearance is an APPROXIMATION for the RL reward: capsules and spheres with
Studio's radii; each 34x46x5 mm hand paddle (build_rig.js) is three 5.5 mm
capsules side by side, so it reads ~3 mm thicker than it is. Scores that
count are taken with Studio's own checker (studio_eval.cjs).
"""

import math

import torch

from tools.nong_sim.kinematics import NongTree

WAIST = 8


def _qmul(a, b):
    w1, x1, y1, z1 = a.unbind(-1)
    w2, x2, y2, z2 = b.unbind(-1)
    return torch.stack([w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2, w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
                        w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2, w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2], -1)


def _qrot(q, v):
    u, w = q[..., 1:], q[..., :1]
    return v + 2 * torch.cross(u, torch.cross(u, v, dim=-1) + w * v, dim=-1)


def _seg_dist(p1, q1, p2, q2):
    """Closest distance between segments, batched (Studio's segSegDist)."""
    d1, d2, r = q1 - p1, q2 - p2, p1 - p2
    a, e = (d1 * d1).sum(-1), (d2 * d2).sum(-1)
    f, c, b = (d2 * r).sum(-1), (d1 * r).sum(-1), (d1 * d2).sum(-1)
    den = a * e - b * b
    s = torch.where(den > 1e-8, ((b * f - c * e) / den.clamp_min(1e-8)).clamp(0, 1), torch.zeros_like(a))
    s = torch.where(a > 1e-8, s, torch.zeros_like(a))
    t = torch.where(e > 1e-8, (b * s + f) / e.clamp_min(1e-8), torch.zeros_like(a))
    lo, hi = t < 0, t > 1
    t = t.clamp(0, 1)
    s = torch.where(lo & (a > 1e-8), (-c / a.clamp_min(1e-8)).clamp(0, 1), s)
    s = torch.where(hi & (a > 1e-8), ((b - c) / a.clamp_min(1e-8)).clamp(0, 1), s)
    return ((p1 + d1 * s[..., None]) - (p2 + d2 * t[..., None])).norm(dim=-1)


class TorchRig:
    POINTS = ("shL", "elL", "wrL", "shR", "elR", "wrR")

    def __init__(self, rig, facts, device="cpu", dtype=torch.float32):
        self.rig, self.facts, self.device, self.dtype = rig, facts, device, dtype
        tree = NongTree(rig, facts)
        self.tree = tree
        names = [b.name for b in tree.bodies]
        T = lambda v: torch.tensor(v, device=device, dtype=dtype)
        self.parent = [names.index(b.parent) if b.parent != "world" else -1 for b in tree.bodies]
        self.pos = T([list(b.pos) for b in tree.bodies])
        self.quat = T([list(b.quat) for b in tree.bodies])
        self.joint = [b.joint for b in tree.bodies]
        self.axis = T([list(b.axis) if b.axis else [0, 0, 0] for b in tree.bodies])
        self.slide = [(b.slide, b.arm) for b in tree.bodies]
        self.point_index = {k: names.index(v) for k, v in tree.points.items()}
        self.wrist_index = {s: names.index(s + "_wrist") for s in ("L", "R")}
        self.sense = T([facts.base_dir[i] * (-1 if rig["invert"][i] else 1) for i in range(10)])
        self.zero = T(rig["zero"])
        self.lo, self.hi = T(rig["min"]), T(rig["max"])
        curve = sorted((p for p in rig.get("shrugCurve") or [] if "j" in p), key=lambda p: p["j"])
        self.curve = T([[p["j"], p.get("l", 0), p.get("r", 0)] for p in curve]) if len(curve) >= 2 else None
        self._shapes()

    def _rise(self, j):
        c = self.curve
        x = j.clamp(c[0, 0], c[-1, 0])
        k = torch.searchsorted(c[:, 0].contiguous(), x.contiguous()).clamp(1, len(c) - 1)
        x0, x1 = c[k - 1, 0], c[k, 0]
        f = ((x - x0) / (x1 - x0).clamp_min(1e-9))[..., None]
        return c[k - 1, 1:] + (c[k, 1:] - c[k - 1, 1:]) * f        # (B, 2) left, right

    def points(self, pose):
        """pose (B,10) deg -> {name: (B,3) mm} in the body frame (waist removed)."""
        B = pose.shape[0]
        delta = torch.deg2rad((pose - self.zero) * self.sense)
        delta = torch.cat([delta[:, :WAIST], torch.zeros_like(delta[:, WAIST:WAIST + 1]), delta[:, WAIST + 1:]], 1)
        rise = self._rise(pose[:, 9]) if self.curve is not None else None
        P, Q = [], []
        for k in range(len(self.parent)):
            pk = self.parent[k]
            p0 = P[pk] if pk >= 0 else torch.zeros(B, 3, device=self.device, dtype=self.dtype)
            q0 = Q[pk] if pk >= 0 else self.quat.new_tensor([1.0, 0, 0, 0]).expand(B, 4)
            pos = self.pos[k].expand(B, 3)
            slide, arm = self.slide[k]
            if slide is not None and rise is not None:
                pos = pos + torch.stack([torch.zeros_like(rise[:, 0]), rise[:, arm], torch.zeros_like(rise[:, 0])], -1)
            q = _qmul(q0, self.quat[k].expand(B, 4))
            j = self.joint[k]
            if j is not None:
                h = delta[:, j] / 2
                q = _qmul(q, torch.cat([torch.cos(h)[:, None], self.axis[k] * torch.sin(h)[:, None]], 1))
            P.append(p0 + _qrot(q0, pos))
            Q.append(q)
        out = {n: P[i] for n, i in self.point_index.items()}
        for s, i in self.wrist_index.items():
            out["q" + s] = Q[i]          # the forearm's frame: the hand paddle hangs from it
        return out

    @staticmethod
    def bones(pts):
        """(B, 2 arms, 2 bones, 3) unit directions upper (shoulder->elbow), fore."""
        out = []
        for s in ("L", "R"):
            up = pts["el" + s] - pts["sh" + s]
            fo = pts["wr" + s] - pts["el" + s]
            out.append(torch.stack([up / up.norm(dim=-1, keepdim=True).clamp_min(1e-9),
                                    fo / fo.norm(dim=-1, keepdim=True).clamp_min(1e-9)], 1))
        return torch.stack(out, 1)

    # ---- approximate clearance (reward only) ----------------------------
    # build_rig.js: BoxGeometry(34, 46, 5) centred 30 mm past the wrist
    PADDLE = [(x, -12.5, -47.5, 5.5) for x in (-11.5, 0.0, 11.5)]

    def _shapes(self):
        r, f, d = self.rig, self.facts, self.rig["dims"]
        self.clear = f.clear_mm + (r.get("extraClearanceMm") or 0)
        self.torso = (torch.tensor([0, -d["torsoH"] / 2, 0.0], device=self.device, dtype=self.dtype),
                      torch.tensor([0, d["torsoH"] / 2, 0.0], device=self.device, dtype=self.dtype),
                      max(d["torsoW"], d["torsoD"]) / 2)
        self.head = (torch.tensor([0, d["torsoH"] / 2 + 68, 0.0], device=self.device, dtype=self.dtype), f.head_r)

    def _parts(self, pts, side):
        """Each arm as (a, b, radius) capsules; a sphere is a capsule of length 0."""
        arm = 0 if side == "L" else 1
        s, e, w = pts["sh" + side], pts["el" + side], pts["wr" + side]
        sr, er = self.rig["jointR"][arm * 2], self.rig["jointR"][arm * 2 + 1]
        length = (e - s).norm(dim=-1, keepdim=True).clamp_min(1)
        start = s + (e - s) * torch.clamp((sr + self.facts.clear_mm) / length, max=0.8)
        turn = math.radians((self.rig.get("palmTurn") or [0, 0])[arm] or 0)
        qh = _qmul(pts["q" + side], torch.tensor([math.cos(turn / 2), 0, math.sin(turn / 2), 0],
                                                  device=self.device, dtype=self.dtype).expand_as(pts["q" + side]))
        parts = {"upper": (start, e, self.rig["barR"][arm * 2]), "fore": (e, w, self.rig["barR"][arm * 2 + 1]),
                 "shoulder": (s, s, sr), "elbow": (e, e, er)}
        for k, (x, y0, y1, r) in enumerate(self.PADDLE):
            a = w + _qrot(qh, torch.tensor([x, y0, 0.0], device=self.device, dtype=self.dtype).expand_as(w))
            b = w + _qrot(qh, torch.tensor([x, y1, 0.0], device=self.device, dtype=self.dtype).expand_as(w))
            parts["hand%d" % k] = (a, b, r)
        return parts

    def clearance(self, pts):
        """(B,) smallest surface gap in mm over the pairs Studio checks (approx)."""
        L, R = self._parts(pts, "L"), self._parts(pts, "R")
        B = pts["shL"].shape[0]
        gaps = []
        ta, tb, tr = self.torso
        ha, hr = self.head
        for a in L.values():
            for b in R.values():
                gaps.append(_seg_dist(a[0], a[1], b[0], b[1]) - a[2] - b[2])
        for arm in (L, R):
            for key in [k for k in arm if k not in ("shoulder",)]:
                a0, a1, ar = arm[key]
                gaps.append(_seg_dist(a0, a1, ta.expand(B, 3), tb.expand(B, 3)) - ar - tr)
                gaps.append(_seg_dist(a0, a1, ha.expand(B, 3), ha.expand(B, 3)) - ar - hr)
            s0, _, sr = arm["shoulder"]
            gaps.append(_seg_dist(s0, s0, ha.expand(B, 3), ha.expand(B, 3)) - sr - hr)
            f0, f1, fr = arm["fore"]
            gaps.append(_seg_dist(f0, f1, s0, s0) - fr - sr)
            u0, u1, ur = arm["upper"]
            for k in range(len(self.PADDLE)):
                h0, h1, hr2 = arm["hand%d" % k]
                gaps.append(_seg_dist(h0, h1, s0, s0) - hr2 - sr)
                gaps.append(_seg_dist(h0, h1, u0, u1) - hr2 - ur)
        return torch.stack(gaps, 1).min(1).values


def angle_deg(a, b):
    """Angle between unit vectors, deg, safe at 0 and 180."""
    return torch.rad2deg(torch.atan2(torch.cross(a, b, dim=-1).norm(dim=-1), (a * b).sum(-1)))


def wrap180(x):
    return (x + 180) % 360 - 180


