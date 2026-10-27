"""Contender 2's world: many Nongs on the GPU, each dancing a slice of the song.

Kinematic + servo only (no gravity or contacts): the same tree, servo model
and speed rules the planner is judged by. The policy moves each joint's
COMMAND by up to the scenario's cap per step (so it can never ask faster than
the board allows), the servo follows the command, and the reward is how
closely the robot's bones point where the dancer's do (DeepMimic-style
imitation), plus WAIST/SHRUG, smoothness, and staying clear of itself and
off the joint stops. A gap under collisionMm (approximate, kin.TorchRig) ends the episode.
"""
import math

import torch

from .kin import angle_deg


class DanceEnv:
    def __init__(self, dense, kin, servo, safe_dps, cfg, device):
        self.ref, self.kin, self.servo, self.cfg, self.device = dense, kin, servo, cfg, device
        dt = kin.dtype
        T = lambda a: torch.as_tensor(a, device=device, dtype=dt)
        self.bones = T(dense.bones)                    # (S, 2, 2, 3)
        self.arm_ok = torch.as_tensor(dense.arm_ok, device=device)
        self.body = T(dense.body)
        self.body_ok = torch.as_tensor(dense.body_ok, device=device)
        self.ik = T(dense.ik)
        self.n = cfg["envs"]
        self.hz = cfg["controlHz"]
        self.sub = max(1, round(servo_hz(servo) / self.hz))          # board frames per decision
        self.horizon = int(cfg["horizonS"] * self.hz)
        self.look = [int(round(s * self.hz)) for s in cfg["lookaheadS"]]
        self.cap = servo.command_cap(safe_dps) / self.hz             # deg per decision
        self.lo, self.hi = kin.lo, kin.hi
        self.mid, self.half = (self.lo + self.hi) / 2, (self.hi - self.lo) / 2
        self.w = cfg["reward"]
        self.near = cfg.get("nearMm", 10.0)
        self.collision = cfg.get("collisionMm") or kin.clear     # user 2026-10-27: 5 mm for servo backlash
        self.obs_dim = self.observe_dim()

    # ---- state ---------------------------------------------------------
    def reset(self, idx=None, start=None):
        """Random start inside the song (reference state init), at the IK fit."""
        if idx is None:
            idx = torch.arange(self.n, device=self.device)
            self.t = torch.zeros(self.n, dtype=torch.long, device=self.device)
            self.age = torch.zeros_like(self.t)
            self.q = torch.zeros(self.n, 10, device=self.device, dtype=self.kin.dtype)
            self.c = torch.zeros_like(self.q)
            self.prev_a = torch.zeros_like(self.q)
        k = len(idx)
        if start is None:
            last = max(1, self.ref.steps - self.horizon // 4)
            start = torch.randint(0, last, (k,), device=self.device)
        pose = self.ik[start] + torch.randn(k, 10, device=self.device, dtype=self.kin.dtype) * self.cfg["startNoiseDeg"]
        pose = torch.maximum(torch.minimum(pose, self.hi), self.lo)
        self.t[idx], self.age[idx] = start, 0
        self.q[idx], self.c[idx], self.prev_a[idx] = pose, pose, 0
        return self.observe()

    def observe_dim(self):
        return 10 * 3 + 12 + len(self.look) * (12 + 2 + 3)

    def observe(self, pts=None):
        pts = pts if pts is not None else self.kin.points(self.q)
        got = self.kin.bones(pts).reshape(-1, 12)
        parts = [(self.q - self.mid) / self.half, (self.c - self.q) / 10, self.prev_a, got]
        last = self.bones.shape[0] - 1
        for d in self.look:
            i = (self.t + d).clamp(max=last)
            parts += [self.bones[i].reshape(-1, 12), (self.body[i] - self.mid[8:]) / self.half[8:],
                      self.arm_ok[i].to(self.q.dtype), self.body_ok[i, None].to(self.q.dtype)]
        return torch.cat(parts, 1)

    # ---- one decision ---------------------------------------------------
    def step(self, action):
        a = action.clamp(-1, 1)
        start_c = self.c
        target = torch.maximum(torch.minimum(self.c + a * self.cap, self.hi), self.lo)
        for k in range(1, self.sub + 1):                   # the board ramps the command per frame
            self.q = self.servo.step(self.q, start_c + (target - start_c) * (k / self.sub))
        self.c = target
        self.t = self.t + 1
        self.age = self.age + 1
        pts = self.kin.points(self.q)
        reward, touch = self._reward(pts, a, target)
        self.prev_a = a
        done = touch if self.w.get("touchEnds", True) else torch.zeros_like(touch)
        trunc = (self.age >= self.horizon) | (self.t >= self.ref.steps - 1)
        return self.observe(pts), reward, done, trunc & ~done

    def _reward(self, pts, a, c):
        w, i = self.w, self.t
        ang = torch.deg2rad(angle_deg(self.kin.bones(pts), self.bones[i]))            # (n, 2, 2)
        seen = self.arm_ok[i][..., None].expand_as(ang).to(ang.dtype)
        mse = (ang ** 2 * seen).sum((1, 2)) / seen.sum((1, 2)).clamp_min(1)
        bone = torch.exp(-mse / (2 * math.radians(w["boneSigmaDeg"]) ** 2))
        bone = torch.where(seen.sum((1, 2)) > 0, bone, torch.ones_like(bone))
        berr = ((self.q[:, 8:] - self.body[i]) ** 2).sum(1)
        body = torch.where(self.body_ok[i], torch.exp(-berr / (2 * w["bodySigmaDeg"] ** 2)), torch.ones_like(berr))
        smooth = torch.exp(-w["smoothScale"] * ((a - self.prev_a) ** 2).mean(1))
        gap = self.kin.clearance(pts)
        near = ((self.near - gap) / (self.near - self.collision)).clamp(0, 1)
        on_stop = ((c <= self.lo + 0.5) | (c >= self.hi - 0.5)).to(c.dtype).mean(1)
        r = w["bone"] * bone + w["body"] * body + w["smooth"] * smooth - w["near"] * near - w["limit"] * on_stop
        return r, gap < self.collision


def servo_hz(servo):
    return 1.0 / servo.dt
