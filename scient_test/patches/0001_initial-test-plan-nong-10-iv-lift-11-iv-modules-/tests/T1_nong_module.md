# T1 — Nong module (humanoid upper body)

Device under test: one ESP32 with `SET TYPE nong`, 10 servo joints.

```
1 L_SH_P  2 L_SH_R  3 L_EL_P  4 L_EL_R  5 R_SH_P  6 R_SH_R  7 R_EL_P  8 R_EL_R  9 WAIST  10 SHRUG
```

As built: shoulders **PDI-1181MG 270°** through **15:18**, elbows **MG90S 180°**
through **12:13**, WAIST **TianKongRC 35 kg 270°** 1:1, SHRUG **MG90S 180°** 1:1.

Source of truth for every prediction below:
`code/firmware/src/modules/nong/NongModule.cpp`,
`code/firmware/config/esp32_hardware_nong_module.h`,
`code/firmware/COMMANDS.md`, and the editor
`code/nong/main_python_set_nong/web/app.js`.

---

## The one equation the whole module rests on

`NongModule::writeServos()` converts a **joint** angle to a servo pulse:

```
sPerJoint = gear_gear / gear_pinion            (declared reduction)
servo     = servo_range/2 + (joint − 90) × sPerJoint
a         = clamp(servo + trim, 0, servo_range)      (invert: a = servo_range − a)
us        = pulse_min + a / servo_range × (pulse_max − pulse_min)
```

So the **measured** joint movement for a commanded movement is

```
Δjoint_measured / Δjoint_commanded  =  (k_declared / k_true) × (travel_true / servo_range_declared)

  k = gear_gear / gear_pinion        travel_true = the servo's real end-to-end travel (180 / 270°)
```

When every declared number matches the hardware the ratio is **1.000**. Tests
NONG-01…NONG-04 each break one term of that product on purpose and check that
the measured ratio moves exactly as predicted. That is the experiment.

---

## Variables

### Independent variables (10 — one per test, never two at once)

| # | Independent Variable | Set with | Range used | Code / default |
|---|---|---|---|---|
| 1 | **`servo_range`** — the SERVO's end-to-end travel in deg (180 vs 270) | `RANGE <j> <deg>` | 180, 270 | `NONG_SERVO_RANGE_DEF = {270,270,180,180,270,270,180,180,270,180}`, bounds 60–360 |
| 2 | **`gear_pinion:gear_gear`** — servo→joint reduction | `GEAR <j> <p> <g>` | 1:1, 12:13, 15:18 | `NONG_GEAR_*_DEF`, shoulders 15:18, elbows 12:13 |
| 3 | **`speed_dps`** — show speed for moves without `T` | `SPEED <deg/s>` | 30, 60, 120, 200 | default 120; accepted range 5 … `min(max_dps)` = **200** (WAIST caps it) |
| 4 | **commanded `T`** — requested move duration | `POSE … T <ms>` | 50, 100, 300, 1000 ms | floored at `max(80 ms, Δ/max_dps)` |
| 5 | **`max_dps`** — per-joint physical speed limit | `PULSE <j> <lo> <hi> <dps>` | 100, 200, 400 | `{375,375,400,400,375,375,400,400,200,400}`, clamped ≥30 |
| 6 | **`joint_min`/`joint_max`** — the JOINT's allowed travel | `LIMIT <j> <min> <max>` | 30–150, 60–120, 87–93 | arms `30..150`, SHRUG `87..93` |
| 7 | **`pulse_min`/`pulse_max`** — servo pulse span in µs | `PULSE <j> <lo> <hi>` | 500–2400, 500–2500, 1000–2000 | MG90S 500–2400, PDI 500–2500 |
| 8 | **number of joints moving at once** | `POSE` with 1 / 4 / 10 changed values | 1, 4, 10 | electrical, not in code |
| 9 | **payload mass on the forearm** | tape a known mass to the wrist | 0, 100, 200, 400 g | mechanical |
| 10 | **`link` / `peer`** — 2-ESP split humanoid | `CFG link 1`, `CFG peer <id>` | off, peer=id, peer=0 (broadcast) | leader repeats resolved `POSE … T <ms>` on RS485 |

### Dependent variables

| DV | Unit | How it is read |
|---|---|---|
| Measured joint angle | deg | digital angle gauge **on the joint** |
| Angle gain `Δmeasured/Δcommanded` | ratio | from two angle readings |
| Effective move duration | ms | the number in the reply `OK pose T=<n>ms` |
| Actual move duration | ms | 60 fps video, first frame of motion → last frame of motion |
| Reported vs commanded angle | deg | `POSE?` reply (10 values) |
| Supply voltage sag under load | V | bench PSU / meter at the board |
| Peak current | A | bench PSU readout |
| Home repeatability | deg spread | angle gauge after N `HOME` cycles |
| Two-board sync error | ms | 60 fps video, both arms in frame |
| Reply string | text | copied verbatim — `ERR …` is a valid result |

### Control variables (hold these fixed)

| CV | Fixed at |
|---|---|
| Servo rail | 5.00 V bench PSU, ≥5 A, measured at the board, common GND with the ESP32 |
| Board / servos | the same physical board and the same servo per joint for the whole series |
| Transport | USB serial only (removes WiFi/RS485 latency from every timing DV) |
| Joint under test | one joint at a time (NONG-01…07): **J3 `L_EL_P`**, elbow, MG90S 180°, 12:13 |
| Other 9 joints | left at neutral 90, `ATTACH`ed, not commanded |
| Start pose | `HOME` before every run, wait for `moving:false` in `INFO` |
| Calibration | `FDEL /data/nong_cal.yaml` + reboot before the series, so `module.yaml`/defaults are the baseline |
| `trim` | 0 for NONG-01…07 (no `SETZERO` mid-series — it changes trim) |
| Command case | UPPERCASE |
| Ambient temp | recorded, ±3 °C across the series |
| Repeats | 3 per IV value |

---

## Tests

### NONG-01 — servo travel (`RANGE`): does declaring 180 vs 270 change the joint by the predicted factor?

IV: `servo_range` on J3. CV: gear stays 12:13, pulse stays 500–2400, the servo
stays the same **real** MG90S (true travel 180°).
Predicted gain = `travel_true / servo_range_declared`.

| ID | IV setting | Command / action | Measure (DV) | Expected | Pass if |
|---|---|---|---|---|---|
| NONG-01a | 180 (correct) | `RANGE 3 180` → `JOINT 3 90` (read gauge) → `JOINT 3 120` (read gauge) | Δ joint deg | 30.0° → gain **1.000** | gain 1.00 ± 0.08 |
| NONG-01b | 270 (over-declared) | `RANGE 3 270` → `JOINT 3 90` → `JOINT 3 120` | Δ joint deg | 30 × 180/270 = **20.0°**, gain **0.667** | gain 0.67 ± 0.08 |
| NONG-01c | 120 (under-declared) | `RANGE 3 120` → `JOINT 3 90` → `JOINT 3 120` | Δ joint deg | 30 × 180/120 = **45.0°**, gain **1.500** | gain 1.50 ± 0.10 |
| NONG-01d | back to 180 | `RANGE 3 180` → `JOINT 3 90` | joint angle | returns to the NONG-01a home reading | within 2° |

> After NONG-01 restore with `RANGE 3 180`. Leaving it wrong poisons every
> later test.

### NONG-02 — reduction gear (`GEAR`)

IV: declared `pinion:gear` on J3. The real mechanism stays 12:13.
Predicted gain = `k_declared / k_true`, `k = gear/pinion`.

| ID | IV setting | Command / action | Measure (DV) | Expected | Pass if |
|---|---|---|---|---|---|
| NONG-02a | 12:13 (correct) | `GEAR 3 12 13` → `JOINT 3 90` → `JOINT 3 120` | Δ joint deg | 30.0°, gain 1.000 | 1.00 ± 0.08 |
| NONG-02b | 1:1 | `GEAR 3 1 1` → same 90→120 | Δ joint deg | 30 × (1 ÷ 1.0833) = **27.7°** | 0.92 ± 0.08 |
| NONG-02c | 15:18 (shoulder ratio on an elbow) | `GEAR 3 15 18` → same | Δ joint deg | 30 × (1.2 ÷ 1.0833) = **33.2°** | 1.11 ± 0.08 |
| NONG-02d | restore | `GEAR 3 12 13` | reply text | `OK gear L_EL_P 12:13 (servo = joint x 1.083)` | exact |

### NONG-03 — show speed (`SPEED`) vs measured move time

IV: `speed_dps`. Move: `POSE` moving J3 by exactly 60° (90 → 150), **no `T`**.
Firmware: `duration = Δmax / speed × 1000`, floor 80 ms, then raised to
`Δ/max_dps` if that is longer (`max_dps` J3 = 400 → floor 150 ms).

| ID | IV setting | Command / action | Measure (DV) | Expected | Pass if |
|---|---|---|---|---|---|
| NONG-03a | 30 deg/s | `SPEED 30` → `JOINT 3 150` | reply `T=`, video ms | `T=2000ms` | reply exact; video within ±60 ms |
| NONG-03b | 60 deg/s | `SPEED 60` → `JOINT 3 150` | same | `T=1000ms` | ±60 ms |
| NONG-03c | 120 deg/s (default) | `SPEED 120` → `JOINT 3 150` | same | `T=500ms` | ±60 ms |
| NONG-03d | 200 deg/s (the cap) | `SPEED 200` → `JOINT 3 150` | same | `T=300ms` | ±60 ms |
| NONG-03e | 250 deg/s (over the cap) | `SPEED 250` | reply text | `ERR range 5-200 deg/s (slowest joint's max_dps)` — the WAIST's 200 dps caps every joint | exact string |
| NONG-03f | 4 deg/s (under the floor) | `SPEED 4` | reply text | `ERR range 5-200 deg/s …` | exact string |

Plot `measured ms` against `1/speed`: the code predicts a straight line through
the origin with slope 60 000 (Δ 60° in ms·deg/s). Deviation = servo lag, not
firmware.

### NONG-04 — commanded `T` and the physical floor

IV: the `T` value in the command. Same 60° move on J3, `max_dps` at its default
400 → floor = 60/400 = **150 ms**.

| ID | IV setting | Command / action | Measure (DV) | Expected | Pass if |
|---|---|---|---|---|---|
| NONG-04a | T 1000 | `JOINT 3 150 T 1000` | reply `T=`, video | `T=1000ms`, arm arrives | ±60 ms |
| NONG-04b | T 300 | `JOINT 3 150 T 300` | same | `T=300ms` | ±60 ms |
| NONG-04c | T 150 (exactly the floor) | `JOINT 3 150 T 150` | same | `T=150ms` | ±40 ms |
| NONG-04d | T 50 (below the floor) | `JOINT 3 150 T 50` | reply `T=` | **raised to** `T=150ms`, not 50 | reply says 150 |
| NONG-04e | T 10 with a 2° move | `JOINT 3 92 T 10` | reply `T=` | raised to the 80 ms minimum (`NONG_MIN_MOVE_MS`) | reply says 80 |

### NONG-05 — `max_dps` sets that floor

IV: `max_dps` on J3 via the 4th argument of `PULSE`. Same 60° move, always
commanded `T 50` so the floor is what you see.

| ID | IV setting | Command / action | Measure (DV) | Expected | Pass if |
|---|---|---|---|---|---|
| NONG-05a | 400 dps | `PULSE 3 500 2400 400` → `JOINT 3 150 T 50` | reply `T=` | `T=150ms` | exact |
| NONG-05b | 200 dps | `PULSE 3 500 2400 200` → same | reply `T=` | `T=300ms` | exact |
| NONG-05c | 100 dps | `PULSE 3 500 2400 100` → same | reply `T=`, **video** | `T=600ms`; does the arm now actually arrive? | reply exact; measured error at the target ≤2° |
| NONG-05d | 20 dps (below the clamp) | `PULSE 3 500 2400 20` → `PULSE` (no args) | reported dps | clamped up to **30** (`if (maxDps_[i] < 30) maxDps_[i] = 30`) | reports 30 |
| NONG-05e | restore | `PULSE 3 500 2400 400` | reply | `OK pulse L_EL_P 500-2400us` | exact |

**The science claim being tested:** a `T` shorter than the servo can physically
achieve makes the *plan* finish before the *arm* does, so the next keyframe
starts from a pose that was never reached. NONG-05c is the run that shows it:
set 100 dps, command 50 ms, and compare the final angle with and without the
floor logic (temporarily commanding `SPEED 200` + `T 50` on a joint whose
`max_dps` you raised to 400 reproduces the "no floor" case).

### NONG-06 — joint limits (`LIMIT`) clamp the pose

IV: `joint_min`/`joint_max` on J3. **Arm free of the body for this one.**

| ID | IV setting | Command / action | Measure (DV) | Expected | Pass if |
|---|---|---|---|---|---|
| NONG-06a | 30..150 (default) | `LIMIT 3 30 150` → `POSE - - 170 - - - - - - -` → `POSE?` | 3rd value | clamped to **150.0** | exact |
| NONG-06b | 60..120 | `LIMIT 3 60 120` → `POSE - - 170 …` → `POSE?` | 3rd value | **120.0** | exact |
| NONG-06c | 60..120, live pose outside | pose to 150 first, then `LIMIT 3 60 120` | joint angle + `POSE?` | firmware pulls the live pose into range (80 ms move) → 120.0 | joint physically moves to 120 |
| NONG-06d | invalid | `LIMIT 3 150 30` | reply text | `ERR need 0<=min<max<=180` | exact |
| NONG-06e | persistence | `LIMIT 3 60 120`, power-cycle, `LIMIT?` | J3 min/max after reboot | still 60/120 **if an SD card is present** (`/data/nong_cal.yaml`); back to 30/150 without a card | matches SD presence |

> NONG-06e is the test that proves calibration survives a reboot — and that
> without an SD card it does not. Run it both ways and record which.

### NONG-07 — servo pulse span (`PULSE`)

IV: `pulse_min`/`pulse_max` µs on J3. Measured on the **servo horn** here
(joint gauge also fine — divide by the gear).

| ID | IV setting | Command / action | Measure (DV) | Expected | Pass if |
|---|---|---|---|---|---|
| NONG-07a | 500–2400 (MG90S spec) | `PULSE 3 500 2400` → `JOINT 3 30`, `JOINT 3 150` | servo travel deg between the two | ≈ full usable travel, no buzz at the ends | no stall buzz |
| NONG-07b | 1000–2000 (narrow) | `PULSE 3 1000 2000` → same two poses | servo travel deg | roughly **half** of NONG-07a — the same joint command reaches less angle | 0.5 ± 0.1 of 07a |
| NONG-07c | 500–2500 (wide) | `PULSE 3 500 2500` → same | servo travel deg, listen | more travel; **check for end-stop buzz** (stall current) | note buzz + current |
| NONG-07d | invalid | `PULSE 3 90 200` | reply text | `ERR need 100<=min, max>min+100, max<=5000 (us)` | exact |
| NONG-07e | restore | `PULSE 3 500 2400 400` | — | — | — |

### NONG-08 — electrical load: how many joints move at once

IV: number of joints changed in one `POSE`. All at `SPEED 120`, all moving 60°.
This is the test that finds brown-outs.

| ID | IV setting | Command / action | Measure (DV) | Expected | Pass if |
|---|---|---|---|---|---|
| NONG-08a | 1 joint | `POSE - - 150 - - - - - - -` | peak A, min V at the board | small step | V ≥ 4.75 |
| NONG-08b | 4 joints (one arm) | `POSE 150 150 150 150 - - - - - -` | peak A, min V | ~4× the current of 08a | V ≥ 4.75 |
| NONG-08c | 8 joints (both arms) | `POSE 150 150 150 150 150 150 150 150 - -` | peak A, min V, did the board reboot? | current climbs; watch for the ESP32 resetting | no reboot, V ≥ 4.75 |
| NONG-08d | 10 joints (+ WAIST, SHRUG) | `POSE 150 150 150 150 150 150 150 150 150 93` | peak A, min V, reboot? | worst case; WAIST is a 35 kg servo | no reboot, V ≥ 4.75 |
| NONG-08e | 10 joints, stalled | 08d with an arm held by hand for 2 s | peak A, min V, reboot? | stall current is several times running current | record; **do not hold >3 s** |

Plot peak current against joint count. A straight line means the supply is
holding; a knee means the rail is sagging and the DVs in every other test are
suspect from that point on.

### NONG-09 — payload mass

IV: mass taped at the wrist. Joint J1 `L_SH_P` (shoulder, carries the load),
`SPEED 120`, 60° lift move.

| ID | IV setting | Command / action | Measure (DV) | Expected | Pass if |
|---|---|---|---|---|---|
| NONG-09a | 0 g | `JOINT 1 150` | final angle error, actual ms | reaches the pose in the reported `T` | error ≤2° |
| NONG-09b | 100 g | same | final angle error, actual ms | small droop | error ≤3° |
| NONG-09c | 200 g | same | final angle error, actual ms, current | droop grows, move may take longer than `T` | record |
| NONG-09d | 400 g | same | final angle error, current, buzz | servo may not hold — the failure point | record the mass where error >5° |

The answer this produces: **the maximum payload at which the reported `T` is
still honest.** That number belongs in the build documentation.

### NONG-10 — `SETZERO` and home repeatability

IV: number of `HOME` cycles (not a setting — a count). CV: no `SETZERO` during
the run.

| ID | IV setting | Command / action | Measure (DV) | Expected | Pass if |
|---|---|---|---|---|---|
| NONG-10a | 1 cycle | `JOINT 3 150` → `HOME` | joint angle at home | reference reading | — |
| NONG-10b | 10 cycles | repeat 10× | spread (max − min) of the 10 home readings | open-loop servo, so a small drift | spread ≤2° |
| NONG-10c | 50 cycles | repeat 50× | spread, and drift direction | drift shows gear backlash | record |
| NONG-10d | `SETZERO` effect | pose to 120, `SETZERO`, read gauge before/after | joint angle change during `SETZERO` | **the arm must not move** — trim absorbs the offset | movement ≤1° |
| NONG-10e | `SETZERO` result | after 10d: `POSE?` and `HOME` | reported angle; where the arm goes | reports 90.0; `HOME` returns to the 120 position | exact |

### NONG-11 — 2-ESP link mode (`link` / `peer`)

Only if the humanoid is split over two boards. Board A = leader (SD card),
board B = follower, both `SET TYPE nong`, both on the RS485 bus, different ids.

| ID | IV setting | Command / action | Measure (DV) | Expected | Pass if |
|---|---|---|---|---|---|
| NONG-11a | link 0 (off) | `CFG link 0` on A, reboot → `POSE …` on A | does B move? | no | B still |
| NONG-11b | link 1, peer = B's id | `CFG link 1`, `CFG peer 5`, reboot → `POSE …` on A | sync error ms (60 fps video, both arms in frame) | both boards move together; B receives `#5 POSE … T <ms>` with the **resolved** duration | sync error ≤50 ms |
| NONG-11c | link 1, peer 0 (broadcast) | `CFG peer 0`, reboot → `POSE …` | do other (non-nong) modules react? | `#* POSE …` goes to everyone on the bus | note any module that reacts wrongly |
| NONG-11d | link 1 on **both** boards | set link 1 on A and B, `POSE …` | bus traffic (sniff on the USB console) | **command storm** — documented failure mode | confirm it storms, then undo |
| NONG-11e | follower alone | `POSE?` on B after a leader move | 10 values | B's angles match A's | ≤0.1° difference |

---

## Nong Studio (the editor) — same maths, second implementation

`code/nong/main_python_set_nong` (served by the hub at `/studio/`). The editor
computes move times itself; the point of these tests is that the **editor and
the firmware must produce identical numbers**. Two implementations of one
formula is exactly where a science test earns its keep.

Editor variables that matter: `RIG.gearPinion`, `RIG.gearGear`, `RIG.pulseMin`,
`RIG.pulseMax`, `RIG.servoRange`, `RIG.servoMaxDps`, `RIG.min`, `RIG.max`,
`RIG.zero`, `RIG.axis`, `RIG.tilt`, `RIG.invert`, `RIG.dims`, and the Timing
card's speed (deg/s) — `ARMJ = 8`, `NJ = 10`.

| ID | IV | Action | Measure (DV) | Expected | Pass if |
|---|---|---|---|---|---|
| STUDIO-01 | Timing speed (deg/s): 30, 60, 120, 200 | build 2 keyframes differing by 60° on one joint; read the chip's `T`; send `TIME? …` to the robot | editor `T` vs firmware `EST` ms | identical: `T = Δmax/speed×1000`, min 80 ms | equal to the ms |
| STUDIO-02 | per-joint `max °/s`: 400, 200, 100 | set it in Setup ▸ rig, type a **shorter** `T` on the chip | the `T` the editor snaps back to | equals the firmware's `max(Δi/max_dps_i)` floor | equal to the ms |
| STUDIO-03 | `travel°` per joint: 180 vs 270 | set it, press **⬆ Send limits + gear to robot**, then `LIMIT?` on the robot | `servo_range` array in the `LIMIT?` JSON | matches the editor row for all 10 joints | 10/10 match |
| STUDIO-04 | full rig push | change min/max, gear, pulse, travel on 3 joints → ⬆ Send → **⬇ Read from robot** | number of fields that differ after the round trip | 0 | 0 |
| STUDIO-05 | joint count in the exported step: 8 vs 10 values | export a 10-value sequence and hand-edit an 8-value one; `MOVE` both | robot pose after each step | 10-value: all joints move. 8-value: WAIST/SHRUG stay at 90, no error | both play |
| STUDIO-06 | crash check on/off | author a pose where the forearm passes through the torso; press **⚠ Check crash** | does it block Run/Upload, and does the real arm actually collide? | editor flags it red **and** the real arm would have hit | no false pass |
| STUDIO-07 | transport: WiFi / USB / RS485 | same 4-keyframe sequence, `live` mode on each transport | pose error vs the editor, dropped steps | identical poses on all three; only latency differs | ≤1° difference |
| STUDIO-08 | export → SD → `MOVE` | export YAML, upload to `/moves/`, run it from the module website | pose at each keyframe vs the editor preview | identical joint angles, identical step times | ≤2° / ±60 ms |

---

## Recording

Fill [`../results/nong_results.csv`](../results/nong_results.csv) — one row per
run, three runs per IV value. Keep the exact reply strings; `OK pose T=150ms`
is itself a measurement.
