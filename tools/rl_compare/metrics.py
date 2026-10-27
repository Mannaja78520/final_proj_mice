"""One scorecard for every contender, from the motion the servos really make.

Input: servo angles q and board commands c at the board's 50 Hz, from the
moment the music starts. Scores (all against the dancer in reference.Dance):
  boneMusic   mean bone angle error at the song's own clock (Studio's measure:
              every seen bone of every trusted sample, body frame)
  boneShape   the same after the best monotone time warp: the shape, ignoring
              timing (Studio's own 7.5 deg v2 score is a warp of this kind)
  drift       how late the robot is on the song (median / at the end, s), and
              the robot's length over the song's length
  jerk        RMS third derivative of the servo angles, deg/s^3
  limits      frames whose command sits on a joint stop
  clearance   approximate smallest gap (TorchRig, hands as balls), plus the
              frames Studio's own checker flags at collisionMm (studio_eval)
"""
import numpy as np
import torch

from .kin import angle_deg


class Scorer:
    def __init__(self, dance, rig, kin, cfg, hz):
        self.dance, self.rig, self.kin, self.cfg, self.hz = dance, rig, kin, cfg, hz
        inside = dance.times <= dance.length + 1e-9
        self.t = dance.times[inside]
        self.want = torch.tensor(dance.bones[inside], dtype=kin.dtype, device=kin.device)
        self.ok = torch.tensor(dance.arm_ok[inside], device=kin.device)
        self.body = dance.body[inside]
        self.body_ok = dance.body_ok[inside]

    def _bones(self, q):
        out = []
        for chunk in torch.split(q, 8192):
            out.append(self.kin.bones(self.kin.points(chunk)))
        return torch.cat(out)

    def _errors(self, got):
        """(N, M) mean seen-bone error of human sample i vs robot sample j."""
        ang = angle_deg(self.want[:, None, :, :, :], got[None, :, :, :, :])     # N, M, 2, 2
        w = self.ok[:, None, :, None].expand_as(ang).to(ang.dtype)
        return ((ang * w).sum((-1, -2)) / w.sum((-1, -2)).clamp_min(1)), w.sum((-1, -2)) > 0

    def warp(self, cost):
        """Monotone match of each human sample to one robot sample (robot may
        hold or skip ahead): min total cost by a running-minimum DP."""
        n, m = cost.shape
        D = np.empty_like(cost)
        arg = np.empty((n, m), dtype=np.int64)
        D[0] = cost[0]
        idx = np.arange(m)
        for i in range(1, n):
            run = np.minimum.accumulate(D[i - 1])
            arg[i] = np.maximum.accumulate(np.where(D[i - 1] == run, idx, 0))
            D[i] = cost[i] + run
        path = np.empty(n, dtype=np.int64)
        path[-1] = int(np.argmin(D[-1]))
        for i in range(n - 1, 0, -1):
            path[i - 1] = arg[i, path[i]]
        return path

    def score(self, q, c):
        """q, c: (F, 10) tensors at self.hz from music time 0."""
        q = q.to(self.kin.device, self.kin.dtype)
        frames = q.shape[0]
        at = np.clip(np.round(self.t * self.hz).astype(int), 0, frames - 1)
        got_now = self._bones(q[at])
        now = angle_deg(self.want, got_now)
        w = self.ok[..., None].expand_as(now)
        bone_music = float(now[w].mean()) if w.any() else float("nan")
        worst = (now * w).amax((-1, -2)).cpu().numpy()
        # shape: every robot sample at the dancer's own rate, over the robot's whole run
        step = max(1, int(round(self.hz * float(np.median(np.diff(self.t))))))
        robot_idx = np.arange(0, frames, step)
        cost, seen = self._errors(self._bones(q[robot_idx]))
        cost = cost.cpu().numpy()
        path = self.warp(cost)
        matched = cost[np.arange(len(path)), path]
        seen_rows = seen[:, 0].cpu().numpy()
        tau = robot_idx[path] / self.hz
        drift = tau - self.t
        qn = q.cpu().numpy()
        cn = c.cpu().numpy() if torch.is_tensor(c) else np.asarray(c)
        body_err = np.abs(qn[at][:, [8, 9]] - self.body)[self.body_ok]
        dt = 1.0 / self.hz
        vel = np.diff(qn, axis=0) / dt
        jerk = np.diff(qn, n=3, axis=0) / dt ** 3
        lo, hi = np.array(self.rig["min"]), np.array(self.rig["max"])
        margin = self.cfg["limitDeg"]
        on_stop = ((cn <= lo + margin) | (cn >= hi - margin)).any(1)
        gaps = torch.cat([self.kin.clearance(self.kin.points(ch)) for ch in torch.split(q, 8192)]).cpu().numpy()
        return {
            "boneMusicDeg": bone_music,
            "boneMusicWorstP95Deg": float(np.percentile(worst, 95)),
            "boneShapeDeg": float(matched[seen_rows].mean()),
            "waistErrDeg": float(body_err[:, 0].mean()) if len(body_err) else None,
            "shrugErrDeg": float(body_err[:, 1].mean()) if len(body_err) else None,
            "driftMedianS": float(np.median(drift)),
            "driftEndS": float(drift[-1]),
            "lengthRatio": float((frames - 1) * dt / self.dance.length),
            "jerkRms": float(np.sqrt((jerk ** 2).mean())),
            "peakDps": float(np.abs(vel).max()),
            "limitFramesPct": float(100 * on_stop.mean()),
            "limitHits": int(np.count_nonzero(np.diff(on_stop.astype(int)) == 1) + int(on_stop[0])),
            "minGapMmApprox": float(gaps.min()),
            "touchFramesApprox": int((gaps < 0).sum()),
            "collisionFramesApprox": int((gaps < (self.cfg.get("collisionMm") or self.kin.clear)).sum()),
            "curve": {"t": self.t.round(3).tolist(), "boneMusic": (now * w).sum((-1, -2)).div(w.sum((-1, -2)).clamp_min(1)).cpu().numpy().round(2).tolist(),
                      "driftS": drift.round(3).tolist()},
        }
