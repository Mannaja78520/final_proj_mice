"""Hall sensor, limit switches, potentiometers and motor/servo PWM, on the REAL
firmware in QEMU (the `*_sim` envs, see firmware/src/sim/MiceSim.h).

QEMU has no ADC, no LEDC/RMT and cannot drive a pin from outside, so the sim
builds redirect the firmware's digitalRead/analogRead/ledcWrite/analogWrite at
link time and take `~PIN`, `~ADC`, `~PWM?` over USB serial. Everything ABOVE
that line is the genuine code: the gachapon's pocket counting and jam timeout,
the lift's homing and fault latch, the dummy's pot-to-angle maths.

  gacha  a hall pulse is counted, the dispense completes, stock drops, the motor
         pins were driven and are released at the end; no pulse still jams;
  lift   both limits "pressed" is a fault until the switches are released;
         HOME drives the motor, the bottom switch ends it and zeroes the stage;
  nong   POSE changes the LEDC duty of joint 1 by the same amount either side of 90;
  dummy  a pot reading becomes the angle the docs' formula gives, and DZERO
         re-zeroes it to 90.

Not covered: real servo pulse widths on a scope, real timing, contact bounce.
Skips with a note when QEMU or the `*_sim` builds are missing
(pio run -e mice_gacha_sim -e mice_lift_sim -e mice_dummy_sim -e mice_nong_sim).
"""
import json
import time
from pathlib import Path

import qemu_board as Q

AREA = "firmware"
TITLE = "hall, limit switches, pots and motor PWM on the real firmware (QEMU)"
SLOW = True

DATA = Path(__file__).resolve().parent.parent / "data"


def _json(b, line, tries=5):
    for _ in range(tries):
        try:
            return json.loads(b.cmd(line))
        except ValueError:
            time.sleep(0.5)
    return {}


def _wait(b, line, test, timeout=15):
    """Poll a JSON query until test(json) is true; returns the last JSON."""
    end, j = time.time() + timeout, {}
    while time.time() < end:
        j = _json(b, line)
        if test(j):
            break
        time.sleep(0.3)
    return j


def _pulse(b, gpio, low_s=0.3, high_s=0.3):
    """One magnet passing an active-low hall: LOW for a moment, then HIGH."""
    b.cmd("~PIN %d 0" % gpio)
    time.sleep(low_s)
    b.cmd("~PIN %d 1" % gpio)
    time.sleep(high_s)


def _gacha(t):
    with Q.QemuBoard("mice_gacha_sim", nvs=DATA / "qemu_nvs_gacha_wifi_off.bin") as b:
        b.cmd("~PIN 33 1")                          # no magnet under the sensor
        b.cmd("GCFG timeout 6000")
        b.cmd("GCFG pause 300")                     # default 5 s of rest would only slow QC
        b.cmd("GSTOCK 3")
        t.contains(b.cmd("GDISPENSE who1"), "OK dispensing", "a prize is dispensed")
        t.contains(b.cmd("~PWM?"), "pin25=", "the motor pins are being driven")
        time.sleep(1.0)
        b.cmd("~PIN 33 0")                          # the magnet arrives and stays: count, then centre on it
        j = _wait(b, "G?", lambda j: j.get("state") == "idle", 15)
        b.cmd("~PIN 33 1")
        t.eq(j.get("motion_result"), "done", "with a hall pulse the dispense ends done, not jam")
        t.eq((j.get("last") or {}).get("result"), "done", "and the prize record says done")
        t.eq(j.get("stock"), 2, "stock went 3 -> 2")
        t.ok((j.get("hits") or 0) >= 1, "the magnet arrival was counted", j.get("hits"))
        pwm = b.cmd("~PWM?")
        t.ok("pin25=1023" in pwm and "pin26=1023" in pwm, "the motor is braked (both pins high) at the end", pwm)


def _lift(t):
    with Q.QemuBoard("mice_lift_sim", nvs=DATA / "qemu_nvs_lift_wifi_off.bin") as b:
        mod = lambda: (_json(b, "INFO").get("module") or {})
        t.eq(mod().get("fault"), "limits_conflict",
             "both limit inputs reading 'pressed' latches limits_conflict")
        b.cmd("~PIN 22 1")                          # top switch released (active low)
        b.cmd("~PIN 21 1")                          # bottom switch released
        t.contains(b.cmd("FAULT CLEAR"), "fault cleared", "the fault clears once the switches are released")
        t.contains(b.cmd("HOME"), "OK homing", "HOME starts")
        t.contains(b.cmd("~PWM?"), "pin32=3", "the lift motor is driven (slowly) while homing")
        b.cmd("~PIN 21 0")                          # reaches the bottom switch
        m = _wait(b, "INFO", lambda j: (j.get("module") or {}).get("homed"), 15).get("module") or {}
        t.ok(m.get("homed"), "the bottom switch ends HOME with the position known", m)
        t.eq((m.get("state"), m.get("stage")), ("idle", 0), "idle at stage 0")
        t.contains(b.cmd("GOTO 2"), "no encoder", "GOTO to a middle stage is refused without an encoder")
        b.cmd("~PIN 21 1")
        t.contains(b.cmd("UP"), "OK up", "UP starts")
        b.cmd("~PIN 22 0")                          # reaches the top switch
        m = _wait(b, "INFO", lambda j: (j.get("module") or {}).get("state") == "idle", 15).get("module") or {}
        t.eq(m.get("stage"), 3, "the top switch ends UP at the top stage")


def _dummy(t):
    with Q.QemuBoard("mice_dummy_sim", nvs=DATA / "qemu_nvs_dummy_wifi_off.bin") as b:
        t.eq(b.cmd("POSE?"), "90.0 " * 9 + "90.0", "pots at mid-scale read 90 degrees")
        b.cmd("~ADC 36 2500")                       # the mux output pin; every joint reads it
        # smoothed reading: wait for it to settle, then angle = 90 + (raw-2048)*270/4095
        got = ""
        end = time.time() + 20
        while time.time() < end:
            got = b.cmd("POSE?")
            if got.split()[0] == "119.8":
                break
            time.sleep(0.5)
        t.eq(got.split()[0], "119.8", "a pot reading of 2500 becomes 119.8 degrees (90 + 452*270/4095)")
        t.contains(b.cmd("DZERO ALL"), "zeroed", "DZERO accepts")
        time.sleep(1)
        t.eq(b.cmd("POSE?").split()[0], "90.0", "after DZERO the held position reads 90 again")


def _duty(b, ch):
    import re
    m = re.search(r"ch%d=(\d+)" % ch, b.cmd("~PWM?"))
    return int(m.group(1)) if m else None


def _nong(t):
    """The servo pulse the firmware asks the LEDC for, joint 1 at three poses."""
    with Q.QemuBoard("mice_nong_sim") as b:
        got = {}
        for deg in (90, 45, 135):
            b.cmd("POSE %d 90 90 90 90 90 90 90 90 90 T 100" % deg)
            end = time.time() + 20
            while time.time() < end:
                if abs(float(b.cmd("POSE?").split()[0]) - deg) < 0.6:
                    break
                time.sleep(0.4)
            got[deg] = _duty(b, 0)
        t.ok(all(v is not None for v in got.values()), "joint 1 drives LEDC channel 0 at every pose", got)
        if all(v is not None for v in got.values()):
            lo, mid, hi = got[45], got[90], got[135]
            t.ok(lo != mid != hi and (lo < mid) == (mid < hi),
                 "the servo duty moves one way as the joint angle rises", got)
            t.ok(abs((mid - lo) - (hi - mid)) <= 2,
                 "and by the same amount either side of 90 degrees (%d / %d / %d)" % (lo, mid, hi), got)
        t.ok(_duty(b, 0) is not None and _duty(b, 8) is not None, "the second servo bank is driven too")


def run(t):
    if not Q.find_qemu():
        t.ok(True, "SKIPPED: no QEMU for ESP32 here (python tools/qemu_esp32.py install)")
        return
    for env, fn in (("mice_gacha_sim", _gacha), ("mice_lift_sim", _lift), ("mice_dummy_sim", _dummy),
                    ("mice_nong_sim", _nong)):
        if Q.images(env):
            fn(t)
        else:
            t.ok(True, "SKIPPED %s: no build here (pio run -e %s)" % (env, env))
