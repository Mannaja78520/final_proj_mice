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

## Measuring instruments

| DV kind | Instrument | Note |
|---|---|---|
| Joint angle | digital angle gauge / protractor on the **joint**, not on the servo horn | the gear ratio means servo deg ≠ joint deg |
| Position (lift) | steel tape on the rack, mark the carriage | compare against `pos_mm` in `INFO` |
| Time / latency | `tools/bench.py` (round-trip ms) or a phone video at 60 fps (16.7 ms per frame) | a stopwatch by hand is ±200 ms — too coarse for the 80 ms floor |
| Speed | encoder value `vel_mms` in `INFO` **and** tape+video as an independent check | `vel_mms` is the firmware's own measurement, so it can't validate itself alone |
| Current / voltage sag | bench PSU readout or a clamp meter, measured **at the board** | 10 servos moving together is several amps |
| Reply text | copy the exact reply string into the CSV | `OK pose T=800ms` *is* a measurement — it reports the effective `T` |

## Running the timing helper

```
python ../tools/bench.py wifi  --host 10.77.237.159 --cmd "PING" -n 50
python ../tools/bench.py usb   --port COM5 --cmd "PING" -n 50
python ../tools/bench.py rs485 --port COM6 --id 3 --cmd "PING" -n 50
```

It prints `sent / replied / lost %`, and min / mean / p95 / max round-trip in
ms — the DV for every latency row in T3, T4 and T5. WiFi mode needs nothing
but Python; USB and RS485 modes need `pyserial` (`pip install pyserial`) and
say so if it is missing.

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
