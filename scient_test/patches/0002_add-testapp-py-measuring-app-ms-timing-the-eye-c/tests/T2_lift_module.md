# T2 — Lift module (rack & pinion stage lift)

Device under test: one ESP32 with `SET TYPE lift` — DC motor + driver,
quadrature encoder, two limit switches, WS2812 strip, I2S speaker.

Source of truth: `code/firmware/src/modules/lift/LiftModule.cpp`,
`code/firmware/config/esp32_hardware_lift_module.h`,
`code/firmware/COMMANDS.md`.

> **Use the app for the timing and the encoder; use the tape for the truth.**
> `python ../tools/testapp.py lift-sweep --transport usb --port COM5 --values 200,400,700,900,1023`
> runs LIFT-01 by itself and reports travel time, peak and mean encoder speed
> and the counts moved. `lift-repeat --stage 2 -n 10` produces the **whole** of
> LIFT-08 — arrival counts, spread in counts and mm, stdev — with nothing left
> for the eye. The tape reading is still yours everywhere the test compares
> *reported* position against *true* position (LIFT-04…07, LIFT-12), and so are
> mass, current and audio drop-outs. See [README.md](README.md) § "You cannot
> see milliseconds".

---

## The numbers the module is built on (compute these once, they drive every prediction)

```
mm_per_rev     = π × RACK_MODULE × PINION_TEETH = π × 2 × 25   = 157.08 mm of rack per pinion rev
counts_per_rev = ENCODER_PULSES × TICKS × GEAR_RATIO = 11 × 4 × 1 =  44 counts per pinion rev
cpm            = counts_per_rev / mm_per_rev                   =   0.280 counts per mm
                                                               →   3.57 mm per encoder count
counts_per_stage = round(stage_mm × cpm) = round(500 × 0.280)  = 140 counts
tol_counts     = max(4, round(LIFT_TOL_MM × cpm)) = max(4, 1)  =   4 counts  → 14.3 mm real tolerance
slow_counts    = max(4×tol, round(LIFT_SLOW_MM × cpm)) = max(16, 11) = 16 counts → 57 mm slow-down zone
max_mms        = max_rpm/60 × mm_per_rev = 100/60 × 157.08     = 261.8 mm/s = 0.262 m/s
est_mms(pwm)   = max_mms × pwm / 1023        → pwm 900 = 230 mm/s, pwm 350 (slow/home) = 90 mm/s
```

**The headline prediction of this whole file:** the encoder resolves only
**3.57 mm per count** and the arrival tolerance is **4 counts ≈ 14 mm**, so no
`GOTO` can be more accurate than about ±14 mm no matter what speed is used.
LIFT-01 and LIFT-08 are designed to confirm (or refute) exactly that number.

---

## Variables

### Independent variables (11 — one per test)

| # | Independent Variable | Set with | Range used | Code / default |
|---|---|---|---|---|
| 1 | **`speed`** — travel speed as raw PWM | `SPEED <100-1023>` | 200, 400, 700, 900, 1023 | `LIFT_DEFAULT_SPEED 900`, clamped 100…1023 |
| 2 | **`speed_mms`** — travel speed in m/s | `SPEED <v> MS` | 0.05, 0.10, 0.20, 0.26 m/s | 0 = PWM mode; `pwm = v/max_mms × 1023`, clamped ≥100 |
| 3 | **`max_rpm`** — the calibration constant that maps PWM ↔ m/s | `CFG max_rpm <n>` | 60, 100, 140 | `PINION_MAX_RPM = MOTOR_RPM = 100` |
| 4 | **`counts_per_rev`** — encoder counts per **pinion** rev | `CFG counts_per_rev <n>` | 44, 88, 176 | `11 × 4 × GEAR_RATIO = 44` |
| 5 | **`mm_per_rev`** — rack travel per pinion rev | `CFG mm_per_rev <n>` | 157.08, 100, 200 | π × 2 × 25 |
| 6 | **`stage_mm`** — rack travel between stages | `CFG stage_mm <n>` | 200, 500, 800 | `LIFT_STAGE_MM 500` |
| 7 | **`counts_per_stage`** — explicit override of #6 | `CFG counts_per_stage <n>` | derived, 100, 140, 200 | unset by default; when set it **beats** `stage_mm` |
| 8 | **`encoder`** — encoder present or not | `CFG encoder 0\|1` | 0, 1 | `LIFT_HAS_ENCODER 1` |
| 9 | **travel distance** — how many stages one `GOTO` covers | `GOTO 1\|2\|3` | 1, 2, 3 stages | `stages` default 4 |
| 10 | **payload mass** on the carriage | add known masses | 0, 1, 2, 5 kg | mechanical |
| 11 | **peripheral load** — LED count / volume / audio during motion | `CFG leds`, `VOL`, `PLAY` while moving | 0/30/120 LEDs; audio on/off | `RGB_DEFAULT_LEDS 30`, `RGB_MAX_LEDS 120` |

### Dependent variables

| DV | Unit | How it is read |
|---|---|---|
| True position | mm | steel tape on the rack against a carriage mark |
| Reported position | mm | `pos_mm` in `INFO` / `/api/status` |
| Position error | mm | true − reported, and true − commanded stage position |
| Repeatability | mm spread | max − min of N arrivals at the same stage |
| Measured speed (encoder) | mm/s | `vel_mms` in `INFO` |
| Measured speed (independent) | mm/s | tape distance ÷ 60 fps video time |
| Estimated speed | mm/s | `est_mms` in `INFO` — the open-loop prediction |
| Speed error | % | (measured − estimated) / estimated |
| Stage travel time | s | video; compare with `stage_s` in `INFO` and `TIME?` |
| Homing repeatability | counts | encoder count at the bottom limit over N homings |
| Overshoot past target | mm | tape, at the moment the motor stops |
| Peak current | A | PSU / clamp meter |
| Audio glitches | count | listen during motion; count drop-outs in 30 s |
| Reply string | text | verbatim, `ERR …` included |

### Control variables (hold fixed)

| CV | Fixed at |
|---|---|
| Motor supply | 12.0 V bench PSU, measured at the driver, current-limited |
| Carriage mass | unloaded baseline for LIFT-01…08; mass is the IV only in LIFT-10 |
| Rack / lubrication | untouched for the whole series; note if re-greased |
| Start position | `HOME` (bottom limit, encoder zeroed) before every run |
| Direction | **up** for LIFT-01…09 (gravity asymmetry is its own test, LIFT-09) |
| Transport | USB serial |
| Limit switches | verified by hand before the series (`INFO` → `limit_top` / `limit_down` flip) |
| `encoder` | 1, except in LIFT-08 where it is the IV |
| Geometry constants | defaults, except in the test where one of them is the IV |
| Firmware version | one build, noted from `PING` |
| Repeats | 3 per IV value; 10 for repeatability rows |

---

## Tests

### LIFT-01 — travel speed (PWM): is the open-loop m/s map right?

IV: `speed` PWM. Move: `GOTO 0` → `GOTO 1` (one 500 mm stage, upward).

| ID | IV setting | Command / action | Measure (DV) | Expected | Pass if |
|---|---|---|---|---|---|
| LIFT-01a | pwm 200 | `SPEED 200` → `HOME` → `GOTO 1` | `vel_mms`, video mm/s, time s | est 51 mm/s, one stage ≈ 9.8 s | measured within 20 % of est |
| LIFT-01b | pwm 400 | `SPEED 400` → same | same | est 102 mm/s, ≈4.9 s | within 20 % |
| LIFT-01c | pwm 700 | `SPEED 700` → same | same | est 179 mm/s, ≈2.8 s | within 20 % |
| LIFT-01d | pwm 900 (default) | `SPEED 900` → same | same | est 230 mm/s, ≈2.2 s | within 20 % |
| LIFT-01e | pwm 1023 | `SPEED 1023` → same | same | est 262 mm/s, ≈1.9 s | within 20 % |
| LIFT-01f | pwm 50 (under the clamp) | `SPEED 50` → `SPEED?` | reported pwm | clamped up to **100** | reports 100 |

Plot measured mm/s against PWM. The firmware assumes a **straight line through
the origin**. Real DC motors don't start at 0 — the low-PWM points will sit
below the line (stiction). Where the line stops being straight is the lowest
PWM this lift can be trusted at, and that is a result worth writing down.

### LIFT-02 — speed in m/s mode

IV: `speed_mms`. Same one-stage move.

| ID | IV setting | Command / action | Measure (DV) | Expected | Pass if |
|---|---|---|---|---|---|
| LIFT-02a | 0.05 m/s | `SPEED 0.05 MS` → `SPEED?` → `HOME` → `GOTO 1` | reply text, `vel_mms`, video | pwm = 50/261.8×1023 = 195; ≈10 s per stage | within 20 % |
| LIFT-02b | 0.10 m/s | `SPEED 0.1 MS` | same | pwm 391, ≈5.0 s | within 20 % |
| LIFT-02c | 0.20 m/s | `SPEED 0.2 MS` | same | reply `OK speed=0.20 m/s (pwm 781, 500mm in ~2.5s)` | reply exact, time within 20 % |
| LIFT-02d | 0.26 m/s | `SPEED 0.26 MS` | same | pwm ≈1016, at the ceiling | within 20 % |
| LIFT-02e | 0.40 m/s (over max) | `SPEED 0.4 MS` | reply text | `ERR range 0.001-0.26 m/s` | exact |
| LIFT-02f | mode switch back | `SPEED 900` → `SPEED?` | reply text | back to `SPEED pwm mode` (`speed_mms` reset to 0) | says pwm mode |

### LIFT-03 — `max_rpm` calibration constant

IV: `max_rpm`. This is the number you *tune*; the test finds its true value.
CV: one PWM (900) for every run.

| ID | IV setting | Command / action | Measure (DV) | Expected | Pass if |
|---|---|---|---|---|---|
| LIFT-03a | 60 | `CFG max_rpm 60`, reboot, `SPEED 900`, `GOTO 1` | `est_mms` vs `vel_mms` | est 138 mm/s; **measured is unchanged** — only the estimate moves | measured same as 03b/03c ±5 % |
| LIFT-03b | 100 (default) | `CFG max_rpm 100`, reboot, same | same | est 230 mm/s | — |
| LIFT-03c | 140 | `CFG max_rpm 140`, reboot, same | same | est 322 mm/s | — |
| LIFT-03d | calibrated | set `max_rpm` = measured_mms ÷ mm_per_rev × 60 ÷ (900/1023) | `est_mms` − `vel_mms` | the two agree | error ≤5 % |

LIFT-03 is the **calibration experiment**: the IV changes only the prediction,
never the physics, so the run where prediction meets measurement gives you the
true `max_rpm` for this lift. Record that value — every `SPEED … MS` and every
`TIME?` afterwards depends on it.

### LIFT-04 — encoder geometry (`counts_per_rev`)

IV: `counts_per_rev`. Move a **tape-measured 500 mm** by hand-driving with
`UP` + `STOP`, then read `pos_mm`.

| ID | IV setting | Command / action | Measure (DV) | Expected | Pass if |
|---|---|---|---|---|---|
| LIFT-04a | 44 (default) | `CFG counts_per_rev 44`, reboot, `HOME`, `UP`…`STOP` at tape 500 mm | `pos_mm`, `encoder` counts | 500 mm ⇒ 140 counts; `pos_mm` ≈ 500 | error ≤15 mm |
| LIFT-04b | 88 (wrong ×2) | `CFG counts_per_rev 88`, reboot, repeat | `pos_mm` at tape 500 mm | reports **≈250 mm** — half | ratio 0.5 ± 0.05 |
| LIFT-04c | 176 (wrong ×4) | same pattern | `pos_mm` at tape 500 mm | ≈125 mm | ratio 0.25 ± 0.05 |
| LIFT-04d | measured truth | count `encoder` over a tape-measured 1000 mm; set `counts_per_rev = counts/1000 × mm_per_rev` | error after re-test | `pos_mm` matches the tape | error ≤15 mm |

### LIFT-05 — rack geometry (`mm_per_rev`)

IV: `mm_per_rev`. Same hand-driven tape method — this one checks the pinion
was measured right (module 2 × 25 teeth).

| ID | IV setting | Command / action | Measure (DV) | Expected | Pass if |
|---|---|---|---|---|---|
| LIFT-05a | 157.08 (default) | `CFG mm_per_rev 157.08`, reboot, tape 500 mm | `pos_mm` | ≈500 | error ≤15 mm |
| LIFT-05b | 100 | `CFG mm_per_rev 100`, reboot, tape 500 mm | `pos_mm` | ≈318 mm (500 × 100/157.08) | ratio 0.64 ± 0.05 |
| LIFT-05c | 200 | same pattern | `pos_mm` | ≈637 mm | ratio 1.27 ± 0.05 |
| LIFT-05d | truth | mark the pinion, turn it exactly 10 revs by hand, tape the rack | mm per rev | matches 157.08 for module 2 / 25T | ≤2 % |

### LIFT-06 — stage size (`stage_mm`)

IV: `stage_mm`. `counts_per_stage = round(stage_mm × 0.280)`.

| ID | IV setting | Command / action | Measure (DV) | Expected | Pass if |
|---|---|---|---|---|---|
| LIFT-06a | 200 mm | `CFG stage_mm 200`, reboot, `HOME`, `GOTO 1` | tape mm from bottom | 56 counts ⇒ ≈200 mm | ±15 mm |
| LIFT-06b | 500 mm (default) | `CFG stage_mm 500`, reboot, `HOME`, `GOTO 1` | tape mm | 140 counts ⇒ ≈500 mm | ±15 mm |
| LIFT-06c | 800 mm | `CFG stage_mm 800`, reboot, `HOME`, `GOTO 1` | tape mm | 224 counts ⇒ ≈800 mm | ±15 mm |
| LIFT-06d | over-travel | `CFG stage_mm 800`, `GOTO 3` (2400 mm) with a shorter rack | where it stops, `INFO` | the **top limit switch wins** — `stopMotor()` on `limit_top` | stops at the switch, no jam |

### LIFT-07 — explicit `counts_per_stage` beats `stage_mm`

IV: `counts_per_stage`. This tests a precedence rule in `applySettings()`.

| ID | IV setting | Command / action | Measure (DV) | Expected | Pass if |
|---|---|---|---|---|---|
| LIFT-07a | unset (derived) | `CFG CLEAR counts_per_stage`, `CFG stage_mm 500`, reboot, `GOTO 1` | tape mm | ≈500 mm (140 counts, derived) | ±15 mm |
| LIFT-07b | 100 explicit | `CFG counts_per_stage 100`, reboot, `GOTO 1` | tape mm | 100 counts ⇒ ≈357 mm — **`stage_mm` is ignored** | ±15 mm |
| LIFT-07c | 200 explicit | `CFG counts_per_stage 200`, reboot, `GOTO 1` | tape mm | ≈714 mm | ±15 mm |
| LIFT-07d | precedence proof | keep 07c, also `CFG stage_mm 200`, reboot, `GOTO 1` | tape mm | still ≈714 mm (explicit wins) | ±15 mm |

### LIFT-08 — positioning accuracy and repeatability vs speed

IV: `speed` PWM again, but the DV is **accuracy**, not time. This is the test of
the 14 mm tolerance prediction.

| ID | IV setting | Command / action | Measure (DV) | Expected | Pass if |
|---|---|---|---|---|---|
| LIFT-08a | pwm 200 | `SPEED 200`, `HOME`, `GOTO 2` ×10 | 10 tape readings: mean error, spread | error ≤ tolerance (≈14 mm); slow approach ⇒ tight spread | spread ≤15 mm |
| LIFT-08b | pwm 600 | `SPEED 600`, same ×10 | same | spread grows with speed | record |
| LIFT-08c | pwm 900 | `SPEED 900`, same ×10 | same | biggest overshoot: the slow zone is only 57 mm (16 counts) | record |
| LIFT-08d | pwm 1023 | `SPEED 1023`, same ×10 | same, plus overshoot mm | may overshoot past `tol_counts` and hunt | note any oscillation |
| LIFT-08e | homing repeatability | `SPEED 900`, `HOME` ×10, read `encoder` right after each | spread in counts at the bottom limit | homing always uses `LIFT_SLOW_SPEED` 350, so spread should be small and speed-independent | spread ≤2 counts |

Plot spread (mm) against PWM. If the spread at pwm 200 is already ≈14 mm, the
limit is the **encoder resolution**, not the control loop — and the fix is a
finer encoder or a gearbox, not tuning. If the spread grows with PWM, the limit
is **braking distance**, and the fix is a wider `LIFT_SLOW_MM`.

### LIFT-09 — direction: up vs down

IV: direction of travel. Gravity is not symmetric; the open-loop m/s map
assumes it is.

| ID | IV setting | Command / action | Measure (DV) | Expected | Pass if |
|---|---|---|---|---|---|
| LIFT-09a | up | `SPEED 900`, `GOTO 0` → `GOTO 2` | `vel_mms`, time, arrival error | slower than estimate (lifting the mass) | record |
| LIFT-09b | down | `GOTO 2` → `GOTO 0` | same | faster than estimate, more overshoot | record |
| LIFT-09c | asymmetry | 09a vs 09b | (down − up) / up, % | a real asymmetry the firmware does **not** model | report the % |
| LIFT-09d | down into the limit | `DOWN` from stage 2 at pwm 1023 | does the bottom switch stop it? `homed` flag | `limit_down` ⇒ `enc_.setCount(0)`, `homed_ = true` | stops + re-zeroes |

### LIFT-10 — payload mass

IV: mass on the carriage. `SPEED 900`, one stage up.

| ID | IV setting | Command / action | Measure (DV) | Expected | Pass if |
|---|---|---|---|---|---|
| LIFT-10a | 0 kg | `HOME`, `GOTO 1` | `vel_mms`, current, arrival error | baseline | — |
| LIFT-10b | 1 kg | same | same | slightly slower, more current | record |
| LIFT-10c | 2 kg | same | same | speed error vs `est_mms` grows | record |
| LIFT-10d | 5 kg | same | same, plus: does it stall? does it slip back at rest? | the failure point | record the mass where error >20 % or it stalls |
| LIFT-10e | hold test | at 10d's mass, `STOP` mid-travel, wait 30 s | drift in `pos_mm` and on the tape | rack + gearbox must hold; `MOTOR_BRAKE true` | drift ≤5 mm |

The output is the **rated payload**: the largest mass at which `est_mms` and
`TIME?` stay honest and nothing slips.

### LIFT-11 — peripheral load (RGB + audio) during motion

IV: LED count and audio playback. This tests **interference**, not the lift:
audio streams from the SD card over the same SPI bus that everything else uses,
and the LEDs load the same rail.

| ID | IV setting | Command / action | Measure (DV) | Expected | Pass if |
|---|---|---|---|---|---|
| LIFT-11a | 0 LEDs, no audio | `RGB EFFECT off`, `GOTO 1` | time, `vel_mms`, current | the clean baseline | — |
| LIFT-11b | 30 LEDs solid white | `CFG leds 30`, reboot, `RGB 255 255 255`, `GOTO 1` | current, time | more current, motion unchanged | time within 5 % of 11a |
| LIFT-11c | 120 LEDs + rainbow | `CFG leds 120`, reboot, `RGB EFFECT rainbow`, `GOTO 1` | current, time, brown-out? | worst rail load | no reboot; time within 5 % |
| LIFT-11d | audio during motion | `VOL 80`, `PLAY intro.mp3`, then `GOTO 1` while it plays | audio drop-outs in 30 s, motion time | SD is mutex-shared; a drop-out is a real, reportable finding | count and report |
| LIFT-11e | audio + LEDs + motion + WiFi status polling | all of 11c, 11d, plus a browser open on the website | drop-outs, motion time, WS update rate | the full-show worst case | no reboot; report drop-outs |

### LIFT-12 — no-encoder mode

IV: `encoder` 0 vs 1. With `encoder 0` the lift only knows the two endpoints.

| ID | IV setting | Command / action | Measure (DV) | Expected | Pass if |
|---|---|---|---|---|---|
| LIFT-12a | encoder 1 | `CFG encoder 1`, reboot, `HOME`, `GOTO 2` | reply, arrival | `OK goto 2`, arrives mid-rack | as LIFT-08 |
| LIFT-12b | encoder 0, mid stage | `CFG encoder 0`, reboot, `GOTO 2` | reply text | `ERR no encoder: only stage 0 or 3` | exact |
| LIFT-12c | encoder 0, stage 0 | `GOTO 0` | reply, where it stops | `OK going down to the bottom limit` | stops at the switch |
| LIFT-12d | encoder 0, top stage | `GOTO 3` | reply, where it stops | `OK going up to the top limit` | stops at the switch |
| LIFT-12e | encoder 0, `STAGE?` between limits | `UP`, `STOP` halfway, `STAGE?` | value | **`-1`** — position unknown without an encoder | exact |
| LIFT-12f | encoder 0, `SPEED … MS` | `SPEED 0.2 MS`, `GOTO 3` | time, tape | open-loop mapping still works with no encoder | within 20 % |

---

## Recording

Fill [`../results/lift_results.csv`](../results/lift_results.csv) — one row per
run, three per IV value (ten for LIFT-08 rows). Keep the exact reply strings.
