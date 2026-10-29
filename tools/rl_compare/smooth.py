"""One smoothing stage for every contender's board commands (user 2026-10-29:
"make it not jerky, one way for all of them").

Savitzky-Golay, run zero-phase over the whole song: it fits a low-order
polynomial in a short window instead of averaging, so a real flick keeps
most of its peak and nothing shifts later on the music clock (a causal
filter would add lag). The servo model still caps speed afterwards, so the
smoothed motion is scored on what the servos can make, like the raw one.
"""
import numpy as np
from scipy.signal import savgol_filter


class CommandSmoother:
    def __init__(self, cfg, hz, lo, hi):
        """cfg: {"windowS": window length, "order": polynomial order}."""
        n = max(3, int(round(cfg["windowS"] * hz)) | 1)          # odd sample count
        self.window, self.order = n, min(cfg["order"], n - 1)
        self.lo, self.hi = np.asarray(lo, float), np.asarray(hi, float)

    def __call__(self, c):
        c = np.asarray(c, float)
        if len(c) <= self.window:
            return c.copy()
        out = savgol_filter(c, self.window, self.order, axis=0, mode="interp")
        return np.clip(out, self.lo, self.hi)
