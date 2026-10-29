"""One smoothing stage for every contender's board commands (user 2026-10-29:
"make it not jerky, one way for all of them").

It is the shared smoother every move in the project goes through (A54-1,
main_python/motion_smooth.py), so what is scored and filmed here is what the
board plays: the dense commands are thinned to keys (a key wherever the
straight line between kept keys misses the motion by more than tolDeg; frame
jitter under that is dropped), each key keeps its own time on the music
clock (zero phase: nothing shifts later), and the arm passes THROUGH a key
where a joint keeps going the same way (motion_smooth vias, the board's
`pass:`) instead of stopping on it. It stops where a joint turns back, so a
real flick keeps its peak. The servo model still caps speed afterwards.
Replaced the Savitzky-Golay prototype of 2026-10-29: a second smoother the
board could not play.
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "main_python"))
import motion_smooth  # noqa: E402


def thin(c, tol, min_gap):
    """Indices of the keys kept (RDP on all 10 joints, max abs deviation)."""
    keep = {0, len(c) - 1}
    stack = [(0, len(c) - 1)]
    while stack:
        a, b = stack.pop()
        if b - a < 2 * min_gap:
            continue
        f = np.linspace(0, 1, b - a + 1)[:, None]
        line = c[a] + (c[b] - c[a]) * f
        dev = np.abs(c[a:b + 1] - line).max(1)
        dev[:min_gap] = dev[-min_gap:] = 0
        i = int(dev.argmax())
        if dev[i] > tol:
            keep.add(a + i)
            stack += [(a, a + i), (a + i, b)]
    return sorted(keep)


def keys_of(c, idx, hz, first_ms=0):
    """Studio/hub keys for the kept frames: t = ms of the move INTO each key."""
    keys = [{"pose": np.round(c[idx[0]], 1).tolist(), "t": first_ms, "hold": 0}]
    for a, b in zip(idx, idx[1:]):
        keys.append({"pose": np.round(c[b], 1).tolist(), "t": round((b - a) * 1000 / hz), "hold": 0})
    return keys


def vias(keys, rig, cap_dps=0.0, cfg=None):
    """Pass speeds per key (motion_smooth), None when "rl" is switched off."""
    cfg = cfg if cfg is not None else motion_smooth.load_config()
    if not motion_smooth.enabled(cfg, "rl") or len(keys) < 3:
        return None
    return motion_smooth.Smoother(cfg, rig, cap_dps).vias(keys)


class CommandSmoother:
    def __init__(self, cfg, hz, lo, hi, rig=None):
        """cfg: {"tolDeg": key tolerance, "minKeyMs": shortest move}; rig: Studio's
        rig (servoMaxDps, servoAccel) for the pass speeds; no cap (music 0)."""
        self.tol, self.hz = float(cfg["tolDeg"]), hz
        self.gap = max(1, int(round(cfg["minKeyMs"] / 1000 * hz)))
        self.lo, self.hi, self.rig = np.asarray(lo, float), np.asarray(hi, float), rig or {}

    def __call__(self, c):
        c = np.asarray(c, float)
        if len(c) < 3:
            return c.copy()
        idx = thin(c, self.tol, self.gap)
        keys = keys_of(c, idx, self.hz)
        V = vias(keys, self.rig)
        out = np.array([motion_smooth.pose_at(keys, V, k * 1000 / self.hz) for k in range(len(c))])
        return np.clip(out, self.lo, self.hi)
