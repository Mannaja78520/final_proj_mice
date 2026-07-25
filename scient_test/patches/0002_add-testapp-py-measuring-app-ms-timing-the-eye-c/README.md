# scient_test — the experiment folder for the mice installation

Controlled tests for the two module types and the three control transports,
written the way an experiment is written: every test names its **Independent
Variable** (the one thing changed), its **Dependent Variable** (what is
measured) and its **Control Variables** (what is held fixed so the result means
something).

Nothing in here changes the robot's code. It is a plan you run, plus sheets you
fill in, plus one small tool that does the timing measurements.

```
scient_test/
  README.md            this file — what exists and how it fits together
  CLAUDE.md            rules for working in this folder
  promt.md             auto-appended log of every prompt (hook in .claude/)
  save_patch.py        snapshot the test files — old versions never disappear
  PATCHES.md           index of those snapshots (created on the first patch)
  patches/             the snapshots themselves
  tests/
    README.md          how to read and run the test tables  <- start here
    T1_nong_module.md  nong humanoid: 10 IVs + Nong Studio cross-checks
    T2_lift_module.md  lift: 11 IVs
    T3_rs485.md        RS485 bus, on its own, run once per module
    T4_wifi.md         WiFi, on its own, run once per module
    T5_usb.md          USB serial, on its own, run once per module
  tools/
    testapp.py         THE MEASURING APP — does every millisecond measurement
    simulator.py       a fake module, so the app can be learned with no hardware
    bench.py           small standalone latency / loss meter (wifi, usb, rs485)
  results/
    nong_results.csv   pre-filled row per test — write the measurements in
    lift_results.csv
    rs485_results.csv
    wifi_results.csv
    usb_results.csv
    traces/            raw samples + HTML plots the app writes (created on use)
    sim/               anything produced by --transport sim, kept separate
```

**Start at [tests/README.md](tests/README.md)** — it explains the table format,
the standing control variables, the instruments, and the safety checks.

## You cannot see milliseconds — the app does that part

Most DVs here are milliseconds: a 20 ms servo tick, an 80 ms minimum move, a
150 ms floor, a 500 ms status push. No eye and no hand stopwatch can measure
them. So the work splits three ways:

- **the app** measures anything timed in ms and anything the module already
  knows — reported vs executed move duration, the 20 ms tick, effective `T`,
  encoder counts and speed, arrival spread, latency, loss, throughput;
- **your eye and a hand tool** measure whatever holds still after the motion
  stops — joint angle with a gauge, rack position with a tape, "did it arrive",
  drop-outs by ear;
- **an instrument** measures current, rail voltage, mass, temperature.

It works by polling the module and timestamping each reply on the PC. `POSE?`
is a short reply, so over USB it samples at ~100–200 Hz (5–10 ms) — fine enough
to resolve the firmware's 20 ms interpolation steps. **Every command prints the
sample rate it achieved**, so you always know the resolution of the number you
were handed.

```
python tools/testapp.py info        --transport usb --port COM5
python tools/testapp.py trace-nong  --transport usb --port COM5 --joint 3 --to 150 --T 300 --html
python tools/testapp.py nong-sweep  --transport usb --port COM5 --iv T --values 1000,300,150,50
python tools/testapp.py trace-lift  --transport usb --port COM5 --stage 1 --html
python tools/testapp.py lift-sweep  --transport usb --port COM5 --values 200,400,700,900,1023
python tools/testapp.py lift-repeat --transport usb --port COM5 --stage 2 -n 10
python tools/testapp.py latency     --transport wifi --host nong.local -n 50 --rate 10
python tools/testapp.py watch       --transport usb --port COM5
```

`--html` writes a self-contained plot you can open in a browser — that is how
you finally *see* the cosine ease, the 20 ms staircase and the lift's 3.57 mm
encoder steps. `--trace-csv` keeps the raw samples. `--csv <file>` chooses where
the summary row goes.

**Two commands need no eye at all** and produce a finished result on their own:
`lift-repeat` (LIFT-08 arrival spread, in counts and mm) and `latency` (every
latency/loss row in T3, T4, T5).

### Try it with no hardware

```
python tools/testapp.py trace-nong --transport sim --joint 3 --to 150 --T 300 --html
python tools/testapp.py nong-sweep --transport sim --iv T --values 1000,300,150,50
python tools/testapp.py trace-lift --transport sim --sim lift --stage 1 --html
```

`--transport sim` talks to [tools/simulator.py](tools/simulator.py), which
re-implements the firmware's maths — cosine ease, 20 ms tick, the
`max(80 ms, Δ ÷ max_dps)` floor, the lift's encoder counts and 4-count
tolerance. Output goes to `results/sim/`, never mixed with real data. It is for
learning the app and for telling "the app is wrong" apart from "the robot is
wrong"; it has no friction, no servo lag and no supply sag, so it is never a
result.

## Why the transports are three separate files

The nong tests and the lift tests measure **the module**. The RS485, WiFi and
USB files measure **the link**, and each link is a different experiment:

| | RS485 | WiFi | USB |
|---|---|---|---|
| topology | shared, half-duplex, addressed | wireless, routed | point-to-point |
| its own IVs | cable length, termination, node count, frame length, ids | distance, RSSI, obstacles, clients, mDNS, AP band | cable, UART chip, boot-log filter, chunk size |
| its own failures | collisions, duplicate ids, missing termination | 5 GHz-only AP, AP fallback, roaming | shared port with the boot log, port already open |
| run per module | yes — nong series, then lift series | yes | yes |

Merging them would mean no variable is isolated: a slow reply could be the
cable, the radio, or the servo loop. Kept apart, each file produces one number
you can act on — the bus's usable command rate, the WiFi's usable range, the
USB's saturation rate.

## The variables at a glance

### T1 — nong module (`code/firmware/src/modules/nong/`, `code/nong/main_python_set_nong/`)

| IV | Set with | Main DV |
|---|---|---|
| `servo_range` (servo travel 180 / 270°) | `RANGE <j> <deg>` | angle gain: measured ÷ commanded |
| gear `pinion:gear` | `GEAR <j> <p> <g>` | angle gain |
| `speed_dps` | `SPEED <deg/s>` | effective + actual move time (ms) |
| commanded `T` | `POSE … T <ms>` | effective `T` in the reply (the floor) |
| `max_dps` | `PULSE <j> <lo> <hi> <dps>` | effective `T`, does the arm arrive |
| `joint_min`/`joint_max` | `LIMIT <j> <min> <max>` | clamped angle in `POSE?` |
| `pulse_min`/`pulse_max` (µs) | `PULSE <j> <lo> <hi>` | servo travel, stall buzz |
| joints moving at once (1/4/10) | one `POSE` | peak current, rail sag, brown-out |
| payload mass | tape a mass to the wrist | angle error, rated payload |
| `link` / `peer` (2 boards) | `CFG link 1`, `CFG peer <id>` | two-board sync error (ms) |
| Nong Studio: speed, `max °/s`, `travel°`, rig push | editor UI | editor number vs firmware number — must be identical |

Controls: 5.00 V bench supply, USB transport, one joint (`L_EL_P`) under test,
`HOME` before every run, no SD calibration carried over, UPPERCASE commands,
3 repeats. Full list in the file.

### T2 — lift module (`code/firmware/src/modules/lift/`)

| IV | Set with | Main DV |
|---|---|---|
| `speed` (PWM) | `SPEED <100-1023>` | measured mm/s, stage time, arrival spread |
| `speed_mms` (m/s mode) | `SPEED <v> MS` | measured mm/s vs commanded |
| `max_rpm` (calibration constant) | `CFG max_rpm` | est vs measured error — finds the true value |
| `counts_per_rev` | `CFG counts_per_rev` | `pos_mm` vs tape |
| `mm_per_rev` | `CFG mm_per_rev` | `pos_mm` vs tape |
| `stage_mm` | `CFG stage_mm` | tape mm per stage |
| `counts_per_stage` (explicit) | `CFG counts_per_stage` | tape mm — proves it overrides `stage_mm` |
| `encoder` 0/1 | `CFG encoder` | which `GOTO`s are accepted, `STAGE?` = −1 |
| travel distance | `GOTO 1/2/3` | position error, drift over cycles |
| payload mass | masses on the carriage | speed error, stall point, hold drift |
| LEDs / audio during motion | `CFG leds`, `PLAY`, `VOL` | current, audio drop-outs, motion time |

Controls: 12.0 V supply, unloaded baseline, `HOME` first, upward travel, USB
transport, verified limit switches, 3 repeats (10 for accuracy rows).

Headline prediction the file tests: the encoder resolves **3.57 mm per count**
and the arrival tolerance is **4 counts ≈ 14 mm**, so no `GOTO` can beat ±14 mm
however it is tuned.

### T3 / T4 / T5 — the transports

| File | IVs | Main DVs |
|---|---|---|
| T3 RS485 | cable length, termination, node count, addressing, command rate, frame length, module id, `link` traffic, chunk size, motion noise | success %, latency, collisions, discovery completeness, throughput |
| T4 WiFi | distance, obstacles, RSSI, wifi mode, AP band, clients, poll rate, IP vs mDNS, file size, network load, module activity | latency, loss, time to ready / fallback / reconnect, WS interval, peers found, KB/s |
| T5 USB | cable, UART chip, command rate, host line-filter rule, command case, bridging, chunk size, host program, boot timing | latency, loss, boot-to-first-reply, throughput, misparse pass/fail |

Each file is run twice — once with the nong board as the device under test,
once with the lift board.

## The standalone latency meter

```
python tools/bench.py wifi  --host 10.77.237.159 --cmd PING -n 50
python tools/bench.py usb   --port COM5 --cmd PING -n 50 --rate 10
python tools/bench.py rs485 --port COM6 --id 3 --cmd PING -n 50
python tools/bench.py wifi  --host nong.local -n 50 --csv results/wifi_results.csv
```

Prints sent / replied / lost % and min / mean / p95 / max round-trip in ms —
the same measurement as `testapp.py latency`, in a smaller script that is handy
for a quick check or a `--csv` log. Both share one transport layer
(`bench.open_link`). WiFi mode is stdlib-only; USB and RS485 need
`pip install pyserial`.

## Two conventions carried over from the rest of the project

**Prompts are logged.** `.claude/settings.json` has the same `UserPromptSubmit`
hook as `code/firmware`, `code/main_python` and
`code/nong/main_python_set_nong`: every prompt sent while working here is
appended to [promt.md](promt.md). Don't edit or reorder it.

**Tests are patched.** After changing anything in `tests/` or `tools/`:

```
python save_patch.py "what changed"
python save_patch.py --list
python save_patch.py --restore 3
```

Each patch is a full snapshot in `patches/NNNN_<slug>/` plus a row in
[PATCHES.md](PATCHES.md). Nothing is ever overwritten, and `--restore`
auto-saves the current version first. Recorded data in `results/` is **not**
patched — that is measurement, not source. So a result sheet can always be
matched to the patch number of the test that produced it: write that number in
the sheet's `notes` column.

## Where the predictions come from

Every "Expected" cell in the test tables is derived from the code, not from a
guess:

| Subject | Source |
|---|---|
| nong joint↔servo maths, move-time floor, limits | `code/firmware/src/modules/nong/NongModule.cpp` |
| nong defaults (gear, pulse, travel, `max_dps`) | `code/firmware/config/esp32_hardware_nong_module.h` |
| lift motion, geometry, speed mapping | `code/firmware/src/modules/lift/LiftModule.cpp` |
| lift defaults (rack, pinion, encoder, PWM) | `code/firmware/config/esp32_hardware_lift_module.h` |
| RS485 framing, stagger, buffer limit | `code/firmware/src/core/RS485Bus.cpp` |
| WiFi states, timeouts, endpoints, mDNS | `code/firmware/src/core/WebPortal.cpp`, `PeerDiscovery.cpp`, `config/conf_network.h` |
| USB loop and bridging | `code/firmware/src/main.cpp` |
| command language, replies, YAML steps | `code/firmware/COMMANDS.md` (authoritative) |
| editor timing + rig variables | `code/nong/main_python_set_nong/web/app.js`, its README |

If the firmware changes, the affected "Expected" cells change with it — patch
the test in the same edit, exactly like COMMANDS.md is kept in sync with the
firmware.
