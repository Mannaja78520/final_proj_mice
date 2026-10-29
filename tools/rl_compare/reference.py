"""The human dance every contender is scored against: one cheer v2 analysis.

`<name>_analysis.json` is what Studio's video page measured (PC .local, private):
fit.times (ms, 6 per second), fit.targets[i].arms[a].upper/fore = the dancer's
bone directions in the robot's body frame (Studio's bodyGroup, waist removed),
fit.poses = Studio's IK fit per sample, whose WAIST/SHRUG came from the
dancer's hips and shoulders. The planner and the RL policy both start from
this one file, so neither gets information the other lacks.
"""
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

WAIST, SHRUG = 8, 9


@dataclass
class Dance:
    name: str
    times: np.ndarray        # (N,) s from the song's start
    bones: np.ndarray        # (N, 2 arms, 2 bones upper/fore, 3) unit, body frame
    arm_ok: np.ndarray       # (N, 2) the dancer's arm was seen and trusted
    arm_fill: np.ndarray     # (N, 2) not trusted, but bridged between two trusted samples
    body: np.ndarray         # (N, 2) WAIST, SHRUG the dancer asks for, deg
    body_ok: np.ndarray      # (N,) the sample was trusted at all
    ik: np.ndarray           # (N, 10) Studio's IK fit (the planner's input)
    start_pose: list         # the first key: both contenders start the song here
    project: dict            # the Studio project (video options, rig)
    source: dict             # video id, from/to s in the source video

    @property
    def length(self):
        return float(self.times[-1])


def fill_gaps(times, bones, ok, max_s):
    """Bridge short untrusted runs (fast swings, an arm behind the body) by
    blending the trusted samples on both sides. Holding the last direction
    (the old way) froze the arm, and an unscored arm let the RL policy drop it
    (user 2026-10-29: arms fall and miss the flicks). Longer runs stay held."""
    out, fill = bones.copy(), np.zeros_like(ok)
    for a in range(ok.shape[1]):
        good = np.flatnonzero(ok[:, a])
        for lo, hi in zip(good[:-1], good[1:]):
            if hi - lo < 2 or times[hi] - times[lo] > max_s:
                continue
            f = ((times[lo + 1:hi] - times[lo]) / (times[hi] - times[lo]))[:, None, None]
            v = bones[lo, a] * (1 - f) + bones[hi, a] * f
            out[lo + 1:hi, a] = v / np.maximum(1e-9, np.linalg.norm(v, axis=-1, keepdims=True))
            fill[lo + 1:hi, a] = True
    return out, fill


def load_dance(folder, name, fill_gap_s=0.0):
    folder = Path(folder)
    analysis = json.loads((folder / f"{name}_analysis.json").read_text(encoding="utf-8"))
    project = json.loads((folder / f"{name}.json").read_text(encoding="utf-8"))
    fit = analysis["fit"]
    n = len(fit["times"])
    bones = np.zeros((n, 2, 2, 3))
    arm_ok = np.zeros((n, 2), bool)
    body_ok = np.zeros(n, bool)
    for i, t in enumerate(fit["targets"]):
        if not t:
            continue
        body_ok[i] = True
        for a, arm in enumerate(t["arms"]):
            if arm.get("ok"):
                arm_ok[i, a] = True
                for b, key in enumerate(("upper", "fore")):
                    v = np.array([arm[key]["x"], arm[key]["y"], arm[key]["z"]], float)
                    bones[i, a, b] = v / max(1e-9, np.linalg.norm(v))
    ik = np.array(fit["poses"], float)
    times = np.array(fit["times"], float) / 1000
    bones, arm_fill = fill_gaps(times, bones, arm_ok, fill_gap_s)
    return Dance(name=name, times=times, bones=bones, arm_ok=arm_ok, arm_fill=arm_fill,
                 body=ik[:, [WAIST, SHRUG]].copy(), body_ok=body_ok, ik=ik,
                 start_pose=list(project["keys"][0]["pose"]), project=project,
                 source=dict(analysis["source"]))


class DenseReference:
    """The dance resampled on a fixed clock (the policy's control rate), held
    past the end so a look-ahead never runs off. Unseen arms keep the last
    seen direction for the observation but carry weight 0 in every score;
    bridged arms (fill_gaps) carry fill_weight in the RL reward only."""

    def __init__(self, dance, hz, pad_s=2.0, fill_weight=0.0):
        self.hz = hz
        self.steps = int(round(dance.length * hz)) + 1          # inside the song
        total = self.steps + int(pad_s * hz) + 1
        t = np.arange(total) / hz
        idx = np.clip(np.searchsorted(dance.times, t, side="right") - 1, 0, len(dance.times) - 1)
        nxt = np.minimum(idx + 1, len(dance.times) - 1)
        span = np.maximum(1e-9, dance.times[nxt] - dance.times[idx])
        f = np.clip((t - dance.times[idx]) / span, 0, 1)[:, None]
        held = self._held(dance.bones, dance.arm_ok)
        bones = held[idx] * (1 - f[..., None, None]) + held[nxt] * f[..., None, None]
        self.bones = bones / np.maximum(1e-9, np.linalg.norm(bones, axis=-1, keepdims=True))
        self.arm_ok = dance.arm_ok[idx] & dance.arm_ok[nxt]
        self.body = dance.body[idx] * (1 - f) + dance.body[nxt] * f
        self.body_ok = dance.body_ok[idx] & dance.body_ok[nxt]
        self.ik = dance.ik[idx] * (1 - f) + dance.ik[nxt] * f
        self.arm_ok[t > dance.length] = False
        usable = dance.arm_ok | dance.arm_fill
        self.arm_w = np.where(self.arm_ok, 1.0, np.where(usable[idx] & usable[nxt], fill_weight, 0.0))
        self.arm_w[t > dance.length] = 0
        self.body_ok[t > dance.length] = False

    @staticmethod
    def _held(bones, ok):
        out = bones.copy()
        for a in range(2):
            last = np.array([[0, -1.0, 0], [0, -1.0, 0]])    # arms hanging down
            for i in range(len(out)):
                if ok[i, a]:
                    last = out[i, a]
                else:
                    out[i, a] = last
        return out
