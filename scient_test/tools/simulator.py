#!/usr/bin/env python3
"""simulator.py — a fake module, so the test app can be learned with no hardware.

`testapp.py --transport sim --sim nong` talks to this instead of a real board.
It re-implements the firmware's motion maths exactly as written in
code/firmware/src/modules/{nong,lift}: the cosine ease, the 20 ms (50 Hz)
update tick, the move-time floor `max(80 ms, delta / max_dps)`, the lift's
encoder counts and its 3.57 mm-per-count resolution.

Use it to:
  - see what a trace looks like before touching the robot,
  - check that a sweep does what you expect before spending servo life on it,
  - tell apart "the app is wrong" from "the robot is wrong" — if a number is
    right here and wrong on the bench, the difference is the real hardware.

It is NOT a substitute for a measurement: the simulator has no servo lag, no
friction, no supply sag. It only reproduces what the firmware code says.
"""
import json
import math
import time

TICK_MS = 20.0          # NongModule::loop() updates the servos at 50 Hz
MIN_MOVE_MS = 80.0      # NONG_MIN_MOVE_MS
SIM_LATENCY_MS = 5.0    # pretend USB round trip, so sample rates look realistic

JOINT_NAMES = ["L_SH_P", "L_SH_R", "L_EL_P", "L_EL_R",
               "R_SH_P", "R_SH_R", "R_EL_P", "R_EL_R", "WAIST", "SHRUG"]


def _now_ms():
    return time.monotonic() * 1000.0


class FakeNong:
    """NongModule, in Python. Same formulas, same 10 joints, same defaults."""

    name = "sim-nong"

    def __init__(self):
        self.min = [30, 30, 30, 30, 30, 30, 30, 30, 30, 87]
        self.max = [150, 150, 150, 150, 150, 150, 150, 150, 150, 93]
        self.max_dps = [375, 375, 400, 400, 375, 375, 400, 400, 200, 400]
        self.neutral = [90.0] * 10
        self.cur = [90.0] * 10
        self.frm = [90.0] * 10
        self.target = [90.0] * 10
        self.speed_dps = 120.0
        self.move_start = 0.0
        self.move_dur = 0.0
        self.moving = False
        self.attached = True

    # ---- firmware maths, copied formula for formula
    def _clamp(self, i, deg):
        return max(self.min[i], min(self.max[i], deg))

    def _max_delta(self, tgt):
        return max(abs(t - c) for t, c in zip(tgt, self.cur))

    def _duration_for(self, tgt):
        return max(MIN_MOVE_MS, self._max_delta(tgt) / self.speed_dps * 1000.0)

    def _min_duration(self, tgt):
        need = max(abs(t - c) / d for t, c, d in zip(tgt, self.cur, self.max_dps))
        return max(MIN_MOVE_MS, need * 1000.0)

    def _start_move(self, tgt, ms):
        tgt = [self._clamp(i, v) for i, v in enumerate(tgt)]
        self.frm = list(self.cur)
        self.target = tgt
        self.move_start = _now_ms()
        self.move_dur = max(ms, self._min_duration(tgt))
        self.moving = True
        return self.move_dur

    def _advance(self):
        if not self.moving:
            return
        elapsed = _now_ms() - self.move_start
        # the firmware only recomputes on a 20 ms tick, so quantise the same way
        elapsed = math.floor(elapsed / TICK_MS) * TICK_MS
        t = elapsed / self.move_dur if self.move_dur > 0 else 1.0
        if t >= 1.0:
            t, self.moving = 1.0, False
        e = 0.5 - 0.5 * math.cos(math.pi * t)
        self.cur = [f + (g - f) * e for f, g in zip(self.frm, self.target)]

    # ---- the command language
    def handle(self, line):
        self._advance()
        a = line.split()
        if not a:
            return "ERR empty"
        c = a[0]                      # module commands are case-sensitive
        if c.upper() == "PING":
            return "PONG 9 %s nong" % self.name
        if c.upper() == "INFO":
            return json.dumps({
                "id": 9, "name": self.name, "type": "nong", "fw": "1.0.0-sim",
                "sd": False, "wifi": {"mode": "off", "ip": "", "rssi": 0, "host": self.name},
                "module": {
                    "joints": [round(v, 1) for v in self.cur],
                    "target": [round(v, 1) for v in self.target],
                    "moving": self.moving, "attached": self.attached,
                    "speed_dps": self.speed_dps, "link": False, "peer": 0,
                    "move_ms": int(self.move_dur),
                    "move_left": int(max(0, self.move_dur - (_now_ms() - self.move_start)))
                    if self.moving else 0}})
        if c in ("POSE?", "POSE") and (c == "POSE?" or len(a) == 1):
            return " ".join("%.1f" % v for v in self.cur)
        if c == "HOME" or c == "ZERO":
            ms = int(a[2]) if len(a) >= 3 and a[1].upper() == "T" else -1
            dur = self._start_move(list(self.neutral),
                                   ms if ms > 0 else self._duration_for(self.neutral))
            return "OK home T=%dms" % dur
        if c == "JOINT":
            if len(a) < 3:
                return "ERR usage: JOINT <1-10|name> <deg> [T <ms>]"
            j = self._index(a[1])
            if j < 0:
                return "ERR joint 1-10 or name"
            tgt = list(self.target)
            tgt[j] = self._clamp(j, float(a[2]))
            ms = int(a[4]) if len(a) >= 5 and a[3].upper() == "T" else -1
            dur = self._start_move(tgt, ms if ms > 0 else self._duration_for(tgt))
            return "OK %s=%.1f T=%dms" % (JOINT_NAMES[j], tgt[j], dur)
        if c == "POSE":
            vals, ms = a[1:], -1
            if len(a) >= 3 and a[-2].upper() == "T":
                ms, vals = int(a[-1]), a[1:-2]
            tgt = list(self.target)
            for i, tok in enumerate(vals[:10]):
                if tok not in ("-", "~"):
                    tgt[i] = self._clamp(i, float(tok))
            dur = self._start_move(tgt, ms if ms > 0 else self._duration_for(tgt))
            return "OK pose T=%dms" % dur
        if c in ("SPEED", "SPEED?"):
            cap = min(self.max_dps)
            if c == "SPEED?" or len(a) < 2:
                return "SPEED %d deg/s (90 deg in ~%.2fs)" % (self.speed_dps, 90.0 / self.speed_dps)
            v = float(a[1])
            if v < 5 or v > cap:
                return "ERR range 5-%d deg/s (slowest joint's max_dps)" % cap
            self.speed_dps = v
            return "OK speed=%d deg/s" % v
        if c == "PULSE":
            if len(a) < 4:
                return "PULSE " + " ".join("%s=500-2400us@%ddps" % (n, d)
                                           for n, d in zip(JOINT_NAMES, self.max_dps))
            j = self._index(a[1])
            dps = float(a[4]) if len(a) >= 5 else 0
            for i in range(10):
                if (j < 0 and a[1].upper() == "ALL") or i == j:
                    if dps >= 30:
                        self.max_dps[i] = dps
                    elif dps:
                        self.max_dps[i] = 30
            return "OK pulse %s %s-%s us" % (a[1], a[2], a[3])
        if c == "LIMIT?" or c == "LIMIT":
            if c == "LIMIT?" or len(a) == 1:
                return json.dumps({"min": self.min, "max": self.max,
                                   "max_dps": self.max_dps})
            j = self._index(a[1])
            if j < 0:
                return "ERR joint 1-10 or name"
            lo, hi = float(a[2]), float(a[3])
            if lo < 0 or hi > 180 or lo >= hi:
                return "ERR need 0<=min<max<=180"
            self.min[j], self.max[j] = lo, hi
            return "OK %s limit %.0f..%.0f" % (JOINT_NAMES[j], lo, hi)
        if c == "STOP":
            self.moving = False
            self.target = list(self.cur)
            return "OK stopped"
        return "ERR unknown cmd: %s" % c.upper()

    def _index(self, token):
        if token.upper() in JOINT_NAMES:
            return JOINT_NAMES.index(token.upper())
        if token.isdigit() and 1 <= int(token) <= 10:
            return int(token) - 1
        return -1


class FakeLift:
    """LiftModule, in Python: encoder counts, stages, limits, PWM speed map."""

    name = "sim-lift"

    def __init__(self):
        self.mm_per_rev = math.pi * 2 * 25          # 157.08
        self.counts_per_rev = 11 * 4                # 44
        self.cpm = self.counts_per_rev / self.mm_per_rev   # 0.280 counts/mm
        self.stage_mm = 500.0
        self.stages = 4
        self.counts_per_stage = round(self.stage_mm * self.cpm)   # 140
        self.tol = max(4, round(2.0 * self.cpm))                  # 4 counts
        self.slow = max(self.tol * 4, round(40.0 * self.cpm))     # 16 counts
        self.max_rpm = 100.0
        self.pwm = 900
        self.speed_mms = 0.0
        self.pos = 0.0            # true rack position in counts (float)
        self.state = "idle"
        self.target_counts = 0
        self.homed = False
        self.vel = 0.0
        self.last = _now_ms()

    def max_mms(self):
        return self.max_rpm / 60.0 * self.mm_per_rev

    def est_mms(self, pwm):
        return self.max_mms() * pwm / 1023.0

    def travel_pwm(self):
        if self.speed_mms > 0 and self.max_mms() > 1:
            return max(100, min(1023, round(self.speed_mms / self.max_mms() * 1023)))
        return self.pwm

    def top_limit(self):
        return self.pos >= (self.stages - 1) * self.counts_per_stage

    def down_limit(self):
        return self.pos <= 0

    def _advance(self):
        now = _now_ms()
        dt = (now - self.last) / 1000.0
        self.last = now
        if dt <= 0:
            return
        pwm, direction = 0, 0
        if self.state == "up":
            if self.top_limit():
                self._stop()
            else:
                pwm, direction = self.travel_pwm(), 1
        elif self.state in ("down", "homing"):
            if self.down_limit():
                self.pos = 0.0
                self.homed = True
                self._stop()
            else:
                pwm = self.travel_pwm() if self.state == "down" else 350
                direction = -1
        elif self.state == "goto":
            err = self.target_counts - self.pos
            if err > 0 and self.top_limit():
                self._stop()
            elif err < 0 and self.down_limit():
                self.pos = 0.0
                self.homed = True
                self._stop()
            elif abs(err) <= self.tol:
                self._stop()
            else:
                pwm = self.travel_pwm() if abs(err) > self.slow else 350
                direction = 1 if err > 0 else -1
        if direction:
            mms = self.est_mms(pwm)
            self.pos += direction * mms * self.cpm * dt
            self.pos = max(0.0, min(self.pos, (self.stages - 1) * self.counts_per_stage))
            self.vel = direction * mms
        else:
            self.vel = 0.0

    def _stop(self):
        self.state = "idle"
        self.vel = 0.0

    def stage(self):
        if not self.homed:
            return -1
        return max(0, min(self.stages - 1,
                          int((int(self.pos) + self.counts_per_stage // 2) // self.counts_per_stage)))

    def handle(self, line):
        self._advance()
        a = line.split()
        if not a:
            return "ERR empty"
        c = a[0]
        if c.upper() == "PING":
            return "PONG 7 %s lift" % self.name
        if c.upper() == "INFO":
            return json.dumps({
                "id": 7, "name": self.name, "type": "lift", "fw": "1.0.0-sim",
                "sd": False, "wifi": {"mode": "off", "ip": "", "rssi": 0, "host": self.name},
                "module": {
                    "state": self.state, "stage": self.stage(), "stages": self.stages,
                    "homed": self.homed, "enc": True, "encoder": int(self.pos),
                    "pos_mm": round(int(self.pos) / self.cpm, 1),
                    "stage_mm": self.stage_mm, "speed": self.pwm,
                    "speed_mms": self.speed_mms, "speed_pwm": self.travel_pwm(),
                    "est_mms": round(self.est_mms(self.travel_pwm()), 1),
                    "vel_mms": round(self.vel, 1),
                    "limit_top": self.top_limit(), "limit_down": self.down_limit()}})
        if c == "UP":
            self.state = "up"
            return "OK up"
        if c == "DOWN":
            self.state = "down"
            return "OK down"
        if c == "STOP":
            self._stop()
            return "OK stopped"
        if c == "HOME":
            self.state = "homing"
            return "OK homing"
        if c == "GOTO":
            if len(a) < 2:
                return "ERR usage: GOTO <stage>"
            s = int(a[1])
            if s < 0 or s > self.stages - 1:
                return "ERR stage 0-%d" % (self.stages - 1)
            if not self.homed:
                self.state = "homing"
                return "OK homing first, then goto %d" % s
            self.target_counts = s * self.counts_per_stage
            self.state = "goto"
            return "OK goto %d" % s
        if c in ("STAGE?", "STAGE"):
            return str(self.stage())
        if c in ("SPEED", "SPEED?"):
            if c == "SPEED?" or len(a) < 2:
                p = self.travel_pwm()
                v = self.est_mms(p)
                return ("SPEED %s: pwm=%d ~%.2f m/s, %.0fmm stage in ~%.1fs (max %.2f m/s)"
                        % ("m/s mode" if self.speed_mms else "pwm mode", p, v / 1000.0,
                           self.stage_mm, self.stage_mm / v if v > 1 else 0,
                           self.max_mms() / 1000.0))
            v = float(a[1])
            unit = a[2].upper() if len(a) >= 3 else ""
            if unit in ("MS", "M/S", "MPS"):
                v, unit = v * 1000.0, "MMS"
            if unit == "MMS":
                if v < 1 or v > self.max_mms() * 1.01:
                    return "ERR range 0.001-%.2f m/s" % (self.max_mms() / 1000.0)
                self.speed_mms = v
                return ("OK speed=%.2f m/s (pwm %d, %.0fmm in ~%.1fs)"
                        % (v / 1000.0, self.travel_pwm(), self.stage_mm, self.stage_mm / v))
            self.pwm = max(100, min(1023, int(v)))
            self.speed_mms = 0.0
            return "OK speed pwm=%d (~%.2f m/s)" % (self.pwm, self.est_mms(self.pwm) / 1000.0)
        return "ERR unknown cmd: %s" % c.upper()


class SimLink:
    """Same interface as bench.WifiLink / bench.SerialLink, no hardware."""

    def __init__(self, kind="nong", latency_ms=SIM_LATENCY_MS):
        self.module = FakeNong() if kind == "nong" else FakeLift()
        self.name = "sim-" + kind
        self.latency = latency_ms / 1000.0

    def send(self, cmd):
        if self.latency:
            time.sleep(self.latency)
        return self.module.handle(cmd.strip())

    def close(self):
        pass


if __name__ == "__main__":
    # tiny smoke test: drive a 60 deg move and show the eased trajectory
    link = SimLink("nong")
    print(link.send("HOME"))
    print(link.send("SPEED 120"))
    print(link.send("JOINT 3 150"))
    t0 = time.monotonic()
    while time.monotonic() - t0 < 0.7:
        print("%6.0f ms  %s" % ((time.monotonic() - t0) * 1000, link.send("POSE?")))
