# Test files — how to read and run them

Five test files, each one a self-contained experiment set. Every test in them
is written the same way, so once you can read one table you can read all of
them.

| File | What it tests | Runs on |
|---|---|---|
| [T1_nong_module.md](T1_nong_module.md) | the **nong** humanoid module — 10 servo joints, gear/travel/limit/speed maths | a board with `SET TYPE nong` |
| [T2_lift_module.md](T2_lift_module.md) | the **lift** module — motor, encoder, stages, rack geometry, RGB + audio | a board with `SET TYPE lift` |
| [T3_rs485.md](T3_rs485.md) | the **RS485 bus** transport, on its own | each module separately |
| [T4_wifi.md](T4_wifi.md) | the **WiFi** transport (website / HTTP API / WebSocket / mDNS), on its own | each module separately |
| [T5_usb.md](T5_usb.md) | the **USB serial** transport, on its own | each module separately |

The three transport files (T3, T4, T5) are **separate experiments on purpose**.
They are not "the same test run three ways": each transport has its own
independent variables (bus length and node count for RS485, distance and RSSI
for WiFi, cable and chunk size for USB) and its own failure modes. Each one is
run **per module** — once with the nong board as the device under test, once
with the lift board — and the module type is a *control* variable inside the
transport test, not the thing being varied.

## The three variable types

Every test names its variables using the standard experiment vocabulary:

| Type | Meaning here | Example |
|---|---|---|
| **Independent Variable (IV)** | the ONE thing you change on purpose, one value per run | `SPEED` in deg/s on the nong |
| **Dependent Variable (DV)** | what you measure as a result — the number that answers the question | measured move time in ms |
| **Control Variable (CV)** | everything held identical between runs so the DV can only be caused by the IV | supply voltage, start pose, transport used, firmware version |

Rule: **one IV per test.** If two things change in one run, the result cannot
be attributed to either. Where a test needs a second knob moved (e.g. gear
ratio *and* servo travel), it is written as two separate tests.

## Table layout used in every test file

Each test file has, in order:

1. **Variable table** — the IV, the DV(s), and the CV list for that module or
   transport, with the source of truth in the code (`file:line`-style
   references to the firmware / Nong Studio).
2. **Test tables** — one row per run. Columns:

   | Column | Meaning |
   |---|---|
   | `ID` | test id, e.g. `NONG-03`. Use it in the results CSV. |
   | `IV setting` | the exact value to set for this run |
   | `Command / action` | the literal command line to send |
   | `Measure (DV)` | what number to write down and with what instrument |
   | `Expected` | what the code says should happen — the prediction |
   | `Pass if` | the tolerance that decides pass/fail |

3. **Recording** — which CSV in [`../results/`](../results/) to fill in.

## Before every run — the standing control variables

These are the CVs that apply to **all five files**. Fix them once, write them
at the top of the results CSV, and don't change them mid-series.

| CV | Value to use | Why it matters |
|---|---|---|
| Firmware version | one build, note `FW_VERSION` from `PING`/`INFO` | different builds change the maths |
| Supply voltage | servo/motor rail measured at the board, e.g. 5.00 V / 12.0 V | servo speed and motor RPM both scale with volts |
| Battery vs bench PSU | bench PSU (regulated) | a sagging battery silently changes every DV |
| Ambient temperature | note it (°C) | servo speed drifts warm |
| Command case | **UPPERCASE always** | core commands (`PING`, `INFO`, `CFG`…) are case-insensitive, but **module commands are matched case-sensitively** — `pose 90 …` in lowercase reaches the module and returns `ERR unknown cmd`, `POSE 90 …` works. Sending mixed case turns a transport test into a firmware test by accident |
| Transport | one transport for the whole module test (USB is the least variable) | a WiFi hiccup must not be recorded as a servo error |
| Starting state | `HOME` (nong) / `HOME` then `GOTO 0` (lift) before every run | motion time depends on where you started |
| Calibration file | note whether `/data/nong_cal.yaml` exists; delete it (`FDEL /data/nong_cal.yaml`) for a clean baseline | it overrides `module.yaml` at boot |
| Repeats | 3 runs per IV value, record all three, report mean and spread | one reading is an anecdote |

## You cannot see milliseconds — so don't try

Most of the dependent variables here are in milliseconds: a 20 ms servo tick,
an 80 ms minimum move, a 150 ms physical floor, a 500 ms status push. **No eye
and no hand stopwatch can measure those** (a hand stopwatch is ±200 ms, worse
than the whole quantity being measured). Only the slow, big DVs can be taken by
a person: a 2 s lift stage, a joint angle, a tape reading, a current draw.

So the work is split three ways, and every test row belongs to exactly one:

| Who measures | What | How |
|---|---|---|
| **The app** (`tools/testapp.py`) | anything in milliseconds, and anything the module already knows: reported vs executed move duration, the 20 ms update tick, effective `T`, encoder counts and speed, arrival spread, latency, loss, throughput, boot time | polls the module's own state and timestamps every reply on the PC |
| **Your eye + a hand tool** | things that hold still after the motion stops: joint angle with a gauge, rack position with a tape, "did it arrive", audio drop-outs by ear, end-stop buzz | take the reading **after** the move — nothing is timed |
| **An instrument** | peak current, rail voltage sag, temperature, payload mass | bench PSU readout / clamp meter / scale |
| **A 60 fps phone video** (fallback) | the few things neither the app nor the eye can do: two-board sync error (NONG-11b), physical arm lag behind the plan | one frame = 16.7 ms; step through frames |

**How the app gets millisecond numbers with no extra hardware:** it polls the
module and timestamps each reply on the PC. `POSE?` is a short reply, so over
USB it samples at roughly 100–200 Hz — about 5–10 ms per sample, fine enough to
see the firmware's 20 ms interpolation steps. `INFO` (the lift's status) is a
long JSON reply, so it samples far slower, around 10–15 Hz over USB. **Every
command prints the sample rate it actually achieved** — that number *is* the
resolution of the result, so you always know how much to trust it. Never quote a
duration finer than the sample interval printed next to it.

## The app: `tools/testapp.py`

```
python ../tools/testapp.py info        --transport usb --port COM5
python ../tools/testapp.py trace-nong  --transport usb --port COM5 --joint 3 --to 150 --T 300 --html
python ../tools/testapp.py nong-sweep  --transport usb --port COM5 --iv T --values 1000,300,150,50
python ../tools/testapp.py lift-repeat --transport usb --port COM5 --stage 2 -n 10
python ../tools/testapp.py latency     --transport wifi --host nong.local -n 50 --rate 10
```

Which test each command does the timing for:

| Test rows | App command | What it hands you | What is still yours to read |
|---|---|---|---|
| NONG-03, NONG-04, NONG-05 | `nong-sweep --iv speed\|T\|maxdps` | commanded `T`, reported `T`, **executed ms**, error, the 20 ms tick | the final joint angle, with a gauge |
| NONG-01, NONG-02, NONG-06, NONG-07 | `trace-nong` (one move) | that the move ran and settled; the reported angle | **the measurement itself** — angle gauge on the joint |
| NONG-08, NONG-09 | `trace-nong` | timing and whether the move completed | current, rail voltage, droop angle |
| NONG-10b/c | `trace-nong` repeated | reported angle after each cycle | gauge reading each cycle (the real spread) |
| NONG-11b | — | — | 60 fps video, both arms in frame |
| LIFT-01, LIFT-02, LIFT-03 | `lift-sweep --values …` | **travel time**, peak and mean encoder speed, counts moved | the tape reading for true mm |
| LIFT-08 (accuracy + repeatability) | `lift-repeat --stage 2 -n 10` | **the whole result** — arrival counts, spread in counts and mm, stdev. No eye needed | nothing, unless you want a tape cross-check |
| LIFT-04…07, LIFT-12 | `trace-lift` | `pos_mm`, counts, stage, state, timing | the tape (these tests compare reported vs true) |
| LIFT-09, LIFT-10, LIFT-11 | `trace-lift` | time and speed per run | mass, current, drop-outs by ear |
| every latency / loss row in T3, T4, T5 | `latency` or `bench.py` | **the whole result** | nothing |

Outputs: a summary row appended to a CSV, plus — with `--trace-csv` and
`--html` — the raw samples and a **self-contained plot you can open in a
browser**. That plot is how you finally *see* what was too fast to watch: the
cosine ease, the 20 ms staircase, the lift's 3.57 mm encoder steps.

### Try it before you wire anything up

```
python ../tools/testapp.py trace-nong --transport sim --joint 3 --to 150 --T 300 --html
python ../tools/testapp.py trace-lift --transport sim --sim lift --stage 1 --html
```

`--transport sim` talks to `tools/simulator.py`, a fake module that
re-implements the firmware's motion maths (cosine ease, 20 ms tick, the
`max(80 ms, Δ/max_dps)` floor, the lift's encoder counts). Output goes to
`results/sim/`, never mixed with real measurements. Use it to learn the app,
and to tell "the app is wrong" apart from "the robot is wrong": if a number is
right in the simulator and wrong on the bench, the difference is real hardware.
The simulator has no friction, no servo lag and no supply sag — it is a
teaching aid, never a result.

## Measuring instruments

| DV kind | Instrument | Note |
|---|---|---|
| Joint angle | digital angle gauge / protractor on the **joint**, not on the servo horn | the gear ratio means servo deg ≠ joint deg |
| Position (lift) | steel tape on the rack, mark the carriage | compare against `pos_mm` in `INFO` |
| Time / latency | **`tools/testapp.py`** (durations, ticks) and `tools/bench.py` (round-trip) | a hand stopwatch is ±200 ms — useless against an 80 ms floor |
| Speed | encoder value `vel_mms` via the app **and** tape+video as an independent check | `vel_mms` is the firmware's own measurement, so it can't validate itself alone |
| Current / voltage sag | bench PSU readout or a clamp meter, measured **at the board** | 10 servos moving together is several amps |
| Reply text | the app copies it into the CSV automatically | `OK pose T=800ms` *is* a measurement — it reports the effective `T` |

## Running the latency helper

```
python ../tools/bench.py wifi  --host 10.77.237.159 --cmd "PING" -n 50
python ../tools/bench.py usb   --port COM5 --cmd "PING" -n 50
python ../tools/bench.py rs485 --port COM6 --id 3 --cmd "PING" -n 50
```

It prints `sent / replied / lost %`, and min / mean / p95 / max round-trip in
ms — the DV for every latency row in T3, T4 and T5. (`testapp.py latency` does
the same thing; `bench.py` is the smaller standalone one, handy for a quick
check or a `--csv` log.) WiFi mode needs nothing but Python; USB and RS485
modes need `pyserial` (`pip install pyserial`) and say so if it is missing.

## Safety before you power the servos

- **Nong:** run `LIMIT?` first and confirm the joint limits are the safe ones
  (arms `30..150`, `SHRUG 87..93`). A universal joint driven past its bind
  point stalls and burns the servo. Any test that widens a limit (`NONG-06`)
  is done with the arm **free of the body** and a hand on the power switch.
- **Lift:** the limit switches are the only hard stop. Before any speed test,
  verify both switches with `INFO` (`limit_top` / `limit_down` flip when
  pressed by hand). Never run a speed test with the carriage already near an
  end stop.
- Keep the servo/motor rail on a current-limited bench supply during testing —
  a stall then shows up as a current reading instead of smoke.

## Recording results

Copy the matching CSV from [`../results/`](../results/), fill one row per run
(three rows per IV value), and keep it next to the test file. The CSV columns
match the test table columns, plus `run`, `value`, `pass`, `notes`.

## Changing these tests

The test files are **patched**, like the Nong Studio web app: after editing
anything in `tests/`, run

```
python ../save_patch.py "what changed"
```

from the `scient_test` folder. Old versions are never overwritten — see
[../PATCHES.md](../PATCHES.md).
