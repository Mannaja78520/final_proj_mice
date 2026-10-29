"""The one smoothing stage every move passes through (A54-1).

User 2026-10-29: the moves stutter, RL or not; make one smoother, like a
plugin, that everything uses. The stutter was the board itself: every POSE was
a cosine ease from rest to rest (NongMath.h ease), so a dance with a key every
167-500 ms stopped dead at every key. Here each keyframe gets a VIA speed per
joint, the speed the arm passes through it with, and each move becomes a
cubic Hermite curve between the two keyframes' speeds, so the speed never
jumps and never drops to 0 where the joint keeps going (a joint resting at
both ends keeps the old cosine). Times never change, so the music stays put.

Where the arm must still stop: the ends, a hold, a joint that turns back
(a flick keeps its peak), a joint that does not move. A via speed is shrunk
until the curve stays inside its two keys (no overshoot), leaves the straight
line between them by at most maxOffLineDeg (collision checks were made on that
line), stays under the servo's speed and needs no more speed-up than allowed.
Studio's motion_smooth.js is the same maths (check_motion_smooth compares
them); the firmware plays the result (NongMath.h curve, `VIA`).
"""
import json
import math
import sys
from pathlib import Path

PART = ("nong", "main_python_set_nong", "web", "motion_smooth.json")
# the code tree, then (MiceHub.exe) beside the exe, its code tree, the bundle
_ROOTS = [Path(__file__).resolve().parent.parent]
if getattr(sys, "frozen", False):
    _exe = Path(sys.executable).resolve().parent
    _ROOTS = [_exe, _exe.parent, Path(getattr(sys, "_MEIPASS", "") or _exe)]
CONFIG = next((r.joinpath(*PART) for r in _ROOTS if r.joinpath(*PART).is_file()), _ROOTS[0].joinpath(*PART))


def load_config(path=None):
    """motion_smooth.json; unreadable = off (every move as before)."""
    try:
        return json.loads(Path(path or CONFIG).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"on": False}


def enabled(cfg, source):
    """Is this maker of moves smoothed? Off everywhere when `on` is false."""
    return bool(cfg.get("on")) and bool((cfg.get("sources") or {}).get(source, True))


# ---- the curve: cubic Hermite through the via speeds ------------------------
# Measured on the four cheer dances (2026-10-29, jerk at the board's 50 Hz):
# a quintic with speed-up 0 at every key was ROUGHER than the old cosine
# (rest to rest it needs more speed-up mid-move, and it overshoots the keys so
# its via speeds had to shrink); the cubic is monotone with these tangents
# (Fritsch-Carlson) and rest to rest (3s2 - 2s3) peaks at 1.5x the mean speed,
# under the cosine's pi/2 that the board's safety floor assumes. A joint that
# rests at both ends keeps the old cosine: rest to rest it is the smoother of
# the two, and it is exactly what an old board and an old file already do.
def curve(q0, q1, v0, v1, T, s):
    """One joint's position at s (0..1): cosine rest to rest, else hermite."""
    if v0 == 0 and v1 == 0:
        s = 0.0 if s <= 0 else 1.0 if s >= 1 else s
        return q0 + (q1 - q0) * (0.5 - 0.5 * math.cos(math.pi * s))
    return hermite(q0, q1, v0, v1, T, s)


def curve_d(q0, q1, v0, v1, T, s):
    if v0 == 0 and v1 == 0:
        d = q1 - q0
        return (d * math.pi / 2 * math.sin(math.pi * s) / T,
                d * math.pi * math.pi / 2 * math.cos(math.pi * s) / (T * T))
    return hermite_d(q0, q1, v0, v1, T, s)


def hermite(q0, q1, v0, v1, T, s):
    """Position at s (0..1) of a move of T seconds from q0 (speed v0 deg/s)
    to q1 (speed v1). Same polynomial as NongMath.h hermite and motion_smooth.js."""
    s = 0.0 if s <= 0 else 1.0 if s >= 1 else s
    s2 = s * s
    s3 = s2 * s
    return q0 + (q1 - q0) * (3 * s2 - 2 * s3) + T * (v0 * (s3 - 2 * s2 + s) + v1 * (s3 - s2))


def hermite_d(q0, q1, v0, v1, T, s):
    """(speed deg/s, speed-up deg/s2) at s."""
    d = q1 - q0
    vel = d * (6 * s - 6 * s * s) / T + v0 * (3 * s * s - 4 * s + 1) + v1 * (3 * s * s - 2 * s)
    acc = (d * (6 - 12 * s) / T + v0 * (6 * s - 4) + v1 * (6 * s - 2)) / T
    return vel, acc


def _times(keys):
    """Start time (ms) of every move into key i, and its length (ms)."""
    starts, t = [0.0] * len(keys), float(keys[0].get("hold", 0) or 0) if keys else 0.0
    for i in range(1, len(keys)):
        starts[i] = t
        t += float(keys[i]["t"]) + float(keys[i].get("hold", 0) or 0)
    return starts, t


class Smoother:
    """vias(keys) -> per key, per joint, the speed (deg/s) the arm passes it with.

    keys: [{pose: [10], t: ms of the move INTO it, hold: ms}] as Studio and the
    hub use them. rig: Studio's rig (servoMaxDps, servoAccel). cap_dps: a peak
    speed cap in force (the board's safety cap, or the music pace), 0 = none.
    touches(pose) -> bool: optional collision check (Studio passes collisionAt);
    a move whose curve touches gets rests at both ends, i.e. its straight line.
    """

    def __init__(self, cfg=None, rig=None, cap_dps=0.0):
        self.cfg = cfg if cfg is not None else load_config()
        rig = rig or {}
        self.max_dps = list(rig.get("servoMaxDps") or [])
        self.acc = list(rig.get("servoAccel") or [])
        self.cap = float(cap_dps or 0)

    def _vmax(self, j):
        top = float(self.max_dps[j]) if j < len(self.max_dps) and self.max_dps[j] else 400.0
        if self.cap > 0:
            top = min(top, self.cap)
        return top * float(self.cfg.get("velScale", 0.85))

    def _amax(self, j):
        a = float(self.acc[j]) if j < len(self.acc) and self.acc[j] else 0.0
        return a * float(self.cfg.get("accScale", 1.0)) if a > 0 else math.inf

    def first_guess(self, keys, rest=None, path=None):
        """Monotone tangents (Fritsch-Carlson, uneven spacing): 0 where a joint
        turns back, holds, stands still or at the ends. With the dense motion
        the keys were thinned from (DensePath), its own speed at each key."""
        n, nj = len(keys), len(keys[0]["pose"]) if keys else 0
        V = [[0.0] * nj for _ in range(n)]
        floor = float(self.cfg.get("minViaDps", 2))
        for i in range(1, n - 1):
            if (keys[i].get("hold") or 0) > 0 or (rest and rest(keys[i])):
                continue
            if path is not None:
                for j, v in enumerate(path.speed(i)):
                    v = math.copysign(min(abs(v), self._vmax(j)), v)
                    V[i][j] = v if abs(v) >= floor else 0.0
                continue
            h0, h1 = float(keys[i]["t"]) / 1000, float(keys[i + 1]["t"]) / 1000
            if h0 <= 0 or h1 <= 0:
                continue
            for j in range(nj):
                d0 = (keys[i]["pose"][j] - keys[i - 1]["pose"][j]) / h0
                d1 = (keys[i + 1]["pose"][j] - keys[i]["pose"][j]) / h1
                if d0 * d1 <= 0:
                    continue
                w1, w2 = 2 * h1 + h0, h1 + 2 * h0
                v = (w1 + w2) / (w1 / d0 + w2 / d1)
                v = math.copysign(min(abs(v), self._vmax(j)), v)
                V[i][j] = v if abs(v) >= floor else 0.0
        return V

    def _bad(self, a, b, va, vb, T, ref=None):
        """Does the move a->b with these via speeds break a rule? (no
        overshoot, near the straight line, under the servo speed and speed-up)
        ref(s) -> pose: the dense motion this move was thinned from; then the
        curve may go where that motion went, and its worst distance from it
        may be at most off more than the plain cosine move's, instead of near
        the line. Worst over the move, not per sample: a move that starts at
        rest lags a motion that does not, early, whatever its speeds."""
        nj, ns = len(a), int(self.cfg.get("samples", 24))
        off = self._off
        u = [b[j] - a[j] for j in range(nj)]
        uu = sum(x * x for x in u)
        R = [ref(k / ns) for k in range(1, ns)] if ref else None
        m = off if R else 1e-6                     # past where the motion went: at most off
        box = [(min([a[j], b[j]] + [r[j] for r in R or []]) - m,
                max([a[j], b[j]] + [r[j] for r in R or []]) + m) for j in range(nj)]
        worst = was = 0.0
        for k in range(1, ns):
            s = k / ns
            p = [curve(a[j], b[j], va[j], vb[j], T, s) for j in range(nj)]
            for j in range(nj):
                if not box[j][0] <= p[j] <= box[j][1]:
                    return True
                vel, acc = curve_d(a[j], b[j], va[j], vb[j], T, s)
                if abs(vel) > self._vmax(j) / float(self.cfg.get("velScale", 0.85)) + 1e-6 \
                        and (va[j] or vb[j]):
                    return True
                plain = 4.935 * abs(b[j] - a[j]) / (T * T)      # rest to rest (cosine) peak
                if abs(acc) > max(self._amax(j), plain) + 1e-6:
                    return True
            if R:
                r, e = R[k - 1], 0.5 - 0.5 * math.cos(math.pi * s)
                worst = max(worst, math.sqrt(sum((p[j] - r[j]) ** 2 for j in range(nj))))
                was = max(was, math.sqrt(sum((a[j] + (b[j] - a[j]) * e - r[j]) ** 2 for j in range(nj))))
            elif uu > 0:
                w = sum((p[j] - a[j]) * u[j] for j in range(nj)) / uu
                w = min(1.0, max(0.0, w))
                dist = math.sqrt(sum((p[j] - a[j] - w * u[j]) ** 2 for j in range(nj)))
                if dist > off:
                    return True
        # with the dense motion: its worst distance from it at most off more than the
        # plain move's (which the line rule allowed off from: the same bound, measured on the motion)
        return bool(R) and worst > was + off

    def _touches(self, a, b, va, vb, T, touches):
        ns = int(self.cfg.get("samples", 24))
        return any(touches([curve(a[j], b[j], va[j], vb[j], T, k / ns) for j in range(len(a))])
                   for k in range(1, ns))

    def _too_short(self, a, b, T):
        """The board lengthens a move shorter than its floor (NongMath.h
        moveFloor) and then plays it rest to rest, so it gets no via speeds."""
        ms = T * 1000
        if ms < float(self.cfg.get("minMoveMs", 80)):
            return True
        for j in range(len(a)):
            top = float(self.max_dps[j]) if j < len(self.max_dps) and self.max_dps[j] else 400.0
            if abs(b[j] - a[j]) / top > T:
                return True
        big = max(abs(y - x) for x, y in zip(a, b))
        return self.cap > 0 and big * math.pi / 2 / self.cap > T

    def vias(self, keys, touches=None, rest=None, path=None):
        """rest(key) -> True where the arm must stop anyway. path: the dense
        motion the keys were thinned from (DensePath), when there is one."""
        # without a collision check on the smoothed path it may barely leave
        # the line the checks passed (uncheckedOffLineDeg)
        self._off = float(self.cfg.get("maxOffLineDeg" if touches else "uncheckedOffLineDeg", 1))
        if len(keys) < 3:
            return [[0.0] * (len(keys[0]["pose"]) if keys else 0) for _ in keys]
        if not self.cfg.get("followDensePath", True):
            path = None
        V = self.first_guess(keys, rest, path)
        shrink, tries = float(self.cfg.get("shrink", 0.5)), int(self.cfg.get("tries", 6))
        used = [0] * len(keys)
        # A key's via speed is shared by the move before and after it, so a
        # shrink can break the move already passed: sweep until none breaks.
        # Each shrink counts on its move; after `tries` it rests (0), the
        # straight line, so the sweep always ends.
        changed = True
        while changed:
            changed = False
            for i in range(1, len(keys)):
                if not (any(V[i - 1]) or any(V[i])):
                    continue
                T = float(keys[i]["t"]) / 1000
                a, b = keys[i - 1]["pose"], keys[i]["pose"]
                if T > 0 and self._too_short(a, b, T):
                    used[i] = tries
                elif T > 0 and not self._bad(a, b, V[i - 1], V[i], T,
                                             path and (lambda s, i=i: path.at(i, s))):
                    if not (touches and self._touches(a, b, V[i - 1], V[i], T, touches)):
                        continue
                    used[i] = tries                 # touching: its straight line, now
                used[i] += 1
                f = shrink if T > 0 and used[i] < tries else 0.0
                V[i - 1] = [v * f for v in V[i - 1]]
                V[i] = [v * f for v in V[i]]
                changed = True
        if self.cfg.get("jerkGuard", True):
            self._guard(keys, V, shrink, tries)
        return [[round(v, 1) for v in row] for row in V]

    def _guard(self, keys, V, shrink, tries):
        """Never rougher than the plain cosine on the same keys (2026-10-30).
        Every rule above can pass and the curve still be rougher: a cubic's
        speed-up jumps at every key, so a via next to a stop can add jerk the
        cosine did not have. Per key, the jerk at the board's frame
        (jerkFrameMs) over the two moves it joins is compared with the
        cosine's; rougher shrinks that key's speeds (after `tries`, 0). Then
        the whole dance, so the sum is never rougher. Same in motion_smooth.js."""
        frame = float(self.cfg.get("jerkFrameMs", 20))
        base = move_jerk(keys, None, frame)
        used = [0] * len(keys)
        changed = True
        while changed:
            changed = False
            got = move_jerk(keys, V, frame)
            for i in range(1, len(keys) - 1):
                if any(V[i]) and got[i] + got[i + 1] > (base[i] + base[i + 1]) * (1 + 1e-9) + 1e-9:
                    used[i] += 1
                    f = shrink if used[i] < tries else 0.0
                    V[i] = [v * f for v in V[i]]
                    changed = True
        for k in range(tries + 1):
            if sum(move_jerk(keys, V, frame)) <= sum(base) * (1 + 1e-9) + 1e-9:
                return
            f = shrink if k < tries else 0.0
            for row in V:
                row[:] = [v * f for v in row]


class DensePath:
    """The dense motion (frames at hz, e.g. the RL policy's 50 Hz commands)
    that keys were thinned from: frame idx[i] became key i. Its own speed
    at a key is the via the arm should pass with; the motion between two keys
    is what the smoothed curve is measured against (it was what got scored
    and collision-checked), not the straight line between them."""

    def __init__(self, frames, idx, hz):
        self.c, self.idx, self.hz = frames, list(idx), float(hz)

    def speed(self, i):
        f = self.idx[i]
        a, b = max(0, f - 1), min(len(self.c) - 1, f + 1)
        return [(float(y) - float(x)) * self.hz / max(1, b - a) for x, y in zip(self.c[a], self.c[b])]

    def at(self, i, s):
        x = self.idx[i - 1] + s * (self.idx[i] - self.idx[i - 1])
        k = min(int(x), len(self.c) - 2)
        w = x - k
        return [float(p) + (float(q) - float(p)) * w for p, q in zip(self.c[k], self.c[k + 1])]


def _frames(keys, V, frame_ms):
    """(poses every frame_ms from 0, the move each frame belongs to) in one
    pass; same phases as pose_at (hold at key 0, move into 1, hold at 1...)."""
    starts, end = _times(keys)
    P, owner = [], []
    i, n = 1, len(keys)
    for k in range(int(end / frame_ms) + 2):
        ms = k * frame_ms
        while i + 1 < n and ms >= starts[i + 1]:
            i += 1
        owner.append(i)
        seg = float(keys[i]["t"])
        s = (ms - starts[i]) / seg if seg > 0 else 1.0
        if s < 0:                                     # the hold at key 0
            P.append(list(keys[0]["pose"]))
        elif s >= 1:                                  # the hold at key i, or past the end
            P.append(list(keys[i]["pose"]))
        else:
            a, b = keys[i - 1]["pose"], keys[i]["pose"]
            if V is None:
                e = 0.5 - 0.5 * math.cos(math.pi * s)
                P.append([x + (y - x) * e for x, y in zip(a, b)])
            else:
                P.append([curve(a[j], b[j], V[i - 1][j], V[i][j], seg / 1000, s) for j in range(len(a))])
    return P, owner


def move_jerk(keys, V, frame_ms=20.0):
    """Per move (index of the key it goes into), the sum of squared jerk of
    every joint at the frames in that move and the hold after it."""
    P, owner = _frames(keys, V, frame_ms)
    out = [0.0] * len(keys)
    for k in range(3, len(P)):
        a, b, c, d = P[k], P[k - 1], P[k - 2], P[k - 3]
        out[owner[k]] += sum((a[j] - 3 * b[j] + 3 * c[j] - d[j]) ** 2 for j in range(len(a)))
    return out


def pose_at(keys, V, ms):
    """The pose `ms` into the moves, smoothed (V from vias) - or the old cosine
    ease when V is None. Same phases as Studio's easeKeys: hold at key 0, move
    into 1, hold at 1, ..."""
    t = float(keys[0].get("hold", 0) or 0)
    if ms <= t:
        return list(keys[0]["pose"])
    for i in range(1, len(keys)):
        seg = float(keys[i]["t"])
        if ms < t + seg:
            s = (ms - t) / seg
            a, b = keys[i - 1]["pose"], keys[i]["pose"]
            if V is None:
                e = 0.5 - 0.5 * math.cos(math.pi * s)
                return [x + (y - x) * e for x, y in zip(a, b)]
            return [curve(a[j], b[j], V[i - 1][j], V[i][j], seg / 1000, s) for j in range(len(a))]
        t += seg + float(keys[i].get("hold", 0) or 0)
        if ms < t:
            return list(keys[i]["pose"])
    return list(keys[-1]["pose"])


def jerk_report(keys, V=None, frame_ms=20.0):
    """How rough the commanded path is, sampled at the board's frame (50 Hz):
    RMS and 95th percentile jerk, peak speed-up and speed over all joints, and
    how many keyframes the arm stops at although a joint keeps going the same
    way (the stutter). V None = the old cosine ease."""
    _, end = _times(keys)
    dt = frame_ms / 1000
    P = [pose_at(keys, V, k * frame_ms) for k in range(int(end / frame_ms) + 2)]
    nj = len(P[0])
    jerks, accs, peak_a, peak_v = [], [], 0.0, 0.0
    for k in range(3, len(P)):
        for j in range(nj):
            v = (P[k][j] - P[k - 1][j]) / dt
            a = (P[k][j] - 2 * P[k - 1][j] + P[k - 2][j]) / dt ** 2
            jk = (P[k][j] - 3 * P[k - 1][j] + 3 * P[k - 2][j] - P[k - 3][j]) / dt ** 3
            peak_v, peak_a = max(peak_v, abs(v)), max(peak_a, abs(a))
            jerks.append(abs(jk))
            accs.append(a * a)
    jerks.sort()
    stops = 0
    for i in range(1, len(keys) - 1):
        if (keys[i].get("hold") or 0) > 0:
            continue
        keeps = [j for j in range(nj)
                 if (keys[i]["pose"][j] - keys[i - 1]["pose"][j]) * (keys[i + 1]["pose"][j] - keys[i]["pose"][j]) > 0.25]
        if keeps and (V is None or all(V[i][j] == 0 for j in keeps)):
            stops += 1
    rms = math.sqrt(sum(x * x for x in jerks) / len(jerks)) if jerks else 0.0
    return {"rmsJerk": round(rms), "rmsAcc": round(math.sqrt(sum(accs) / len(accs))) if accs else 0, "p95Jerk": round(jerks[int(0.95 * (len(jerks) - 1))]) if jerks else 0,
            "peakAcc": round(peak_a), "peakDps": round(peak_v, 1), "stops": stops,
            "keys": len(keys), "seconds": round(end / 1000, 1)}


def pass_values(V, i):
    """PASS for the move INTO key i: the speeds it starts with, then the
    speeds it ends with (deg/s, 2 x joints). The board plays the curve only
    when the arm really is moving at the start speeds (the move before ended
    as planned); otherwise the old cosine from rest, so a lengthened or
    resumed move can never start off its curve. None when the move rests at
    both ends."""
    if not V or i <= 0 or not (any(V[i - 1]) or any(V[i])):
        return None
    return [float(x) for x in list(V[i - 1]) + list(V[i])]


def pass_line(values):
    """The `pass:` step value / PASS command arguments."""
    return " ".join("%g" % (round(x, 1) + 0.0) for x in values)


def add_pass(steps, rig=None, source="hub", cfg=None, cap_dps=0.0):
    """Give every step a `pass` (the hub's shape) when this source is smoothed.
    For makers with no collision check of their own on the curve (the hub's
    gestures): the path leaves the checked line by at most uncheckedOffLineDeg."""
    cfg = cfg if cfg is not None else load_config()
    if not enabled(cfg, source) or len(steps) < 3:
        return steps
    V = Smoother(cfg, rig, cap_dps).vias(steps)
    for i, s in enumerate(steps):
        p = pass_values(V, i)
        if p:
            s["pass"] = p
    return steps
