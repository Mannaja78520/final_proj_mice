# Changelog

Everything notable that changes in this repository, newest first. Each entry
says what changed, **why**, and what you have to do differently because of it.

Folder-level history also exists in two other places and is not repeated here:
`nong/main_python_set_nong/PATCHES.md` (every Nong Studio web-app snapshot) and
`scient_test/PATCHES.md` (every test-plan snapshot).

---

## 2026-07-26

### Added — `scient_test/tools/testapp.py`, the measuring app

Most dependent variables in the test plan are milliseconds: a 20 ms servo tick,
an 80 ms minimum move, a 150 ms physical floor, a 500 ms status push. **No eye
and no hand stopwatch can measure those**, so until now the fastest and most
important rows in the plan had no honest way to be filled in.

`testapp.py` polls the module and timestamps every reply on the PC. `POSE?` is
a short reply, so over USB it samples at ~100–200 Hz (5–10 ms per sample) —
fine enough to resolve the firmware's 20 ms interpolation steps. **Every
command prints the sample rate it achieved**, so the resolution of each number
is always visible, and a duration is never quoted finer than the sampling that
produced it.

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

`--html` writes a self-contained plot — that is how you finally *see* the
cosine ease, the 20 ms staircase, the lift's 3.57 mm encoder steps. `--csv`
writes the summary row straight into the results sheet; raw samples and plots
go to `results/traces/`.

`lift-repeat` (LIFT-08 arrival spread) and `latency` (every latency/loss row in
T3/T4/T5) need no eye at all and produce a finished result on their own.

### Added — `scient_test/tools/simulator.py`, a fake module

`--transport sim` talks to a Python re-implementation of the firmware's motion
maths: cosine ease, 20 ms tick, the `max(80 ms, Δ ÷ max_dps)` floor, the lift's
encoder counts and 4-count tolerance. Two reasons it exists — learn the app
without burning servo life, and tell **"the app is wrong"** apart from **"the
robot is wrong"** (a number that is right in sim and wrong on the bench is the
real hardware talking).

It has no friction, no servo lag and no supply sag, so **it is never a result**.
Its output goes to `results/sim/`, never mixed into `results/`.

### Changed — the test plan now says who measures each row

Every test file gained a note naming, per row, whether the app, your eye, or an
instrument takes the measurement:

- **the app** — anything timed in ms, plus anything the module already knows:
  reported vs executed move duration, the 20 ms tick, effective `T`, encoder
  counts and speed, arrival spread, latency, loss, throughput;
- **your eye and a hand tool** — whatever holds still once the motion stops:
  joint angle with a gauge, rack position with a tape, "did it arrive",
  drop-outs by ear;
- **an instrument** — current, rail voltage, mass, temperature.

New rule in `scient_test/CLAUDE.md`: any new test row whose DV is under ~1 s
must name the `testapp.py` command that measures it.

### Changed — `scient_test/tools/bench.py` shares its transport layer

New `open_link()` factory, so `bench.py` and `testapp.py` open WiFi / USB /
RS485 links through one piece of code instead of two copies. `bench.py` keeps
working exactly as before — it is now described as the small standalone latency
meter, handy for a quick check or a `--csv` log.

### Added — Nong Studio: save your tuned rig as *your* default

Tuning the rig to match the real robot is slow work, and **Reset defaults** used
to throw all of it away by returning to the factory scale.

New **★ Save current as default** button (Rig setup card) locks the current rig
into a separate, protected slot. **Reset to default** now returns to *your*
saved rig; it falls back to the factory rig only if you never saved one, and
asks for confirmation before it does. Tuned dimensions are never overwritten.

Stored per browser (`localStorage`), alongside the existing rig cache.

---

## 2026-07-26 — initial commit

First publication of the mice installation software:

| | |
|---|---|
| `firmware/` | ESP32 firmware — one binary for every module type (`lift`, `nong`, `blank`), chosen at boot from NVS |
| `main_python/` | Mice Control Hub — finds every module on the network and serves its page over WiFi, USB or RS485 |
| `nong/main_python_set_nong/` | Nong Studio — 3D pose and keyframe sequence editor for the humanoid |
| `scient_test/` | the experiment plan — IV/DV/CV test tables, results sheets |
| `auto_click/` | standalone screen-automation helper, unrelated to the robot |

Build output is not tracked: `.pio/` (~230 MB of PlatformIO libraries and
objects), CMake build trees, `__pycache__`, machine-specific VS Code files.
`pio run` regenerates all of it.
