"""Fit the dancer's arm height into what the robot's arm can reach.

User 2026-10-29: when the dancer lifts an arm the robot sometimes stays low.
The shoulder pitch servo is at its 25 deg stop there (180 deg servo through
14:19 gears = ~132 deg of joint), so an exact copy is out of reach; the user
chose not to remount the gears and asked for a lift that LOOKS like the
dancer's instead: same direction, same up and down timing, height scaled into
the robot's range.

Per arm and per compass direction (azimuth, 10 deg bins) the highest upper-arm
elevation the joint limits allow is found by sampling the rig. The dancer's
own top (a high percentile over the song) is mapped onto that reach, linearly
above kneeDeg; below the knee nothing changes. The whole arm (upper and fore)
is turned by the same angle about the horizontal axis, so the elbow bend and
the direction are kept.
"""
import dataclasses

import numpy as np
import torch

Y = np.array([0.0, 1.0, 0.0])


def elevation(v):
    return np.degrees(np.arcsin(np.clip(v[..., 1], -1, 1)))


def azimuth(v):
    return np.degrees(np.arctan2(v[..., 0], v[..., 2]))


def rotate(v, axis, ang):
    """Rodrigues: v (..., 3) about unit axis (..., 3) by ang rad (...)."""
    c, s = np.cos(ang)[..., None], np.sin(ang)[..., None]
    return v * c + np.cross(axis, v) * s + axis * (axis * v).sum(-1, keepdims=True) * (1 - c)


class ArmReach:
    def __init__(self, kin, rig, cfg, seed=0):
        self.cfg = cfg
        self.bins = int(360 / cfg["binDeg"])
        lo, hi = np.array(rig["min"], float), np.array(rig["max"], float)
        g = np.random.default_rng(seed)
        top = np.full((2, self.bins), -90.0)
        for _ in range(cfg["samples"] // 50000):
            q = lo + (hi - lo) * g.random((50000, 10))
            b = kin.bones(kin.points(torch.as_tensor(q, dtype=kin.dtype))).cpu().numpy()
            up = b[:, :, 0]                                   # (B, 2 arms, 3)
            e, k = elevation(up), self.bin(azimuth(up))
            for a in range(2):
                np.maximum.at(top[a], k[:, a], e[:, a])
        for a in range(2):                                    # a bin no sample reached: its neighbours
            for i in np.flatnonzero(top[a] <= -90):
                top[a, i] = max(top[a, i - 1], top[a, (i + 1) % self.bins])
        self.top = top

    def bin(self, az):
        return (np.floor((az + 180) / self.cfg["binDeg"]).astype(int)) % self.bins

    def remap(self, dance):
        """A copy of the dance whose arm heights fit the reach; raw_bones keeps the original.

        The dancer's height is first scaled into the robot's best reach (its
        highest bin). The robot only lifts that high toward some directions
        (with these limits: to the side, not straight ahead), so each sample
        may also swing sideways: per candidate azimuth the cost is
        azWeight * |swing| + (wanted height - height reachable there), and the
        cheapest wins. A lift then stays a lift, a little more to the side."""
        cfg, knee = self.cfg, self.cfg["kneeDeg"]
        bones = dance.bones.copy()
        cand = (np.arange(self.bins) + 0.5) * cfg["binDeg"] - 180
        info = {}
        for a in range(2):
            up = bones[:, a, 0]
            e, az = elevation(up), azimuth(up)
            seen = dance.arm_ok[:, a]
            if not seen.any():
                continue
            reach = self.top[a] - cfg["marginDeg"]
            top_d = max(np.percentile(e[seen], cfg["dancerTopPct"]), knee + 1)
            best = reach.max()
            want = np.where(e > knee, knee + (e - knee) * np.clip((best - knee) / (top_d - knee), 0, 1), e)
            swing = (cand[None, :] - az[:, None] + 180) % 360 - 180                   # (N, bins) deg
            got = np.minimum(want[:, None], np.maximum(reach, knee)[None, :])   # a lift never turns into a drop
            cost = cfg["azWeight"] * np.abs(swing) + (want[:, None] - got)
            pick = cost.argmin(1)
            d_az = np.where(want > knee, swing[np.arange(len(e)), pick], 0.0)
            e_new = np.where(want > knee, got[np.arange(len(e)), pick], np.minimum(e, np.maximum(reach[self.bin(az)], knee)))
            turn_y = np.radians(d_az)
            yaxis = np.broadcast_to(Y, up.shape)
            for b in range(2):                                 # swing round the vertical, height kept
                bones[:, a, b] = rotate(bones[:, a, b], yaxis, turn_y)
            up = bones[:, a, 0]
            turn = np.radians(e_new - elevation(up))
            axis = np.cross(up, Y)
            n = np.linalg.norm(axis, axis=-1, keepdims=True)
            axis = np.where(n > 1e-6, axis / np.maximum(n, 1e-9), np.array([1.0, 0, 0]))
            for b in range(2):                                 # then up or down toward the vertical
                bones[:, a, b] = rotate(bones[:, a, b], axis, turn)
            changed = seen & ((np.abs(turn) > 1e-3) | (np.abs(d_az) > 1e-3))
            info["LR"[a]] = {"dancerTopDeg": round(float(top_d), 1), "robotTopDeg": round(float(best), 1),
                             "changedPct": round(float(changed[seen].mean() * 100), 1),
                             "meanSwingDeg": round(float(np.abs(d_az)[changed].mean()) if changed.any() else 0.0, 1)}
        return dataclasses.replace(dance, bones=bones, raw_bones=dance.bones), info
