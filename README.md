# final_proj_mice — code

All the software for the **mice** installation: the ESP32 firmware every module
board runs, the PC hub that finds and controls them, the humanoid pose editor,
and the experiment plan used to test the whole thing.

The installation is a set of **modules**. A module is one ESP32 board with its
own ID, name and type, its own website, an SD card, and two links to the world
at once — **RS485** and **WiFi**. Every module runs the *same* firmware binary;
what it *is* is chosen after flashing (`SET TYPE lift|nong` + reboot).

Module types today:

| Type | What it is |
|---|---|
| `lift` | motor lift that moves between stages, RGB strip, speaker, stage tracking |
| `nong` | humanoid upper body — 2 arms (universal shoulder + universal elbow), waist, shrug |
| `blank` | fresh board, not configured yet |

## Folders

```
firmware/                 ESP32 firmware — one binary for every module type
main_python/              Mice Control Hub — the PC program you start first
nong/main_python_set_nong Nong Studio — 3D pose & sequence editor for the humanoid
scient_test/              the experiment plan: tests, tools, measured results
auto_click/               small standalone screen-automation helper (unrelated to the robot)
```

Each folder has its own README with the full detail. Start with the one you
need:

### [firmware/](firmware/) — the module firmware

PlatformIO / ESP32 (`nodemcu-32s`). Shared core services (identity in NVS,
runtime pin map, command router, RS485 bus, web portal, SD store, audio, RGB,
sequence player) plus one folder per module type in `src/modules/`.

One binary per module type — a board carries only its own module's code and
web page:

```
pio run -e mice_nong             # the humanoid
pio run -e mice_lift             # the lift
pio run -e mice_blank            # core only, for a board that is not a module yet
pio run -e mice_module_firmware  # every type in one binary (legacy, kept for now)
```

**[firmware/COMMANDS.md](firmware/COMMANDS.md) is the authoritative reference**
for the command language — the same commands work over the website, the HTTP
API, USB serial, RS485 and inside sequence YAML.

### [main_python/](main_python/) — Mice Control Hub

The first page of everything. Start it and it scans the network for modules by
itself; no typing IPs.

```
MiceHub.exe          Windows (or run_hub.bat)
python main.py       any OS with Python 3.8+ (Ubuntu: sh run_hub.sh)
```

Opens `http://127.0.0.1:8642/` and also prints a WiFi URL that phones and other
laptops on the same network can open. It serves each module's own page over
WiFi **or** USB/RS485, so the UI is identical on every transport, and it hosts
Nong Studio at `/studio/`.

### [nong/main_python_set_nong/](nong/main_python_set_nong/) — Nong Studio

Blender-style editor for the `nong` humanoid: pose the 3D model (drag the servo
rings, or drag the wrist ball for IK), add keyframes like a video editor, and
export a `/moves/*.yaml` sequence onto the module's SD card. Standard library
only; three.js is vendored so it works offline.

```
python main.py       # or double-click run_nong_studio.bat
```

10 logical joints, order everywhere:
`L_SH_P L_SH_R L_EL_P L_EL_R R_SH_P R_SH_R R_EL_P R_EL_R WAIST SHRUG`
(degrees, neutral 90). The keyframe timing formula here is the same one the
firmware uses, so the plan and the real robot stay matched.

### [scient_test/](scient_test/) — the experiment folder

Controlled tests written as experiments: every test names its **Independent
Variable** (the one thing changed), its **Dependent Variable** (what is
measured) and its **Control Variables**. Five test files — `nong` module, `lift`
module, and RS485 / WiFi / USB each on their own — plus `tools/bench.py` for
latency and loss measurements and `results/*.csv` sheets to fill in. Nothing in
here modifies the robot's code.

### [auto_click/](auto_click/)

A standalone `pyautogui` script that waits for a time, finds a button image on
screen and clicks it. Not part of the robot; kept here because it lives with
the rest of the project's tooling.

## Hardware quick reference

| Function | Pins |
|---|---|
| Motor driver (lift) | IN_A 33, IN_B 32 |
| Encoder (lift) | A 25, B 26 |
| Limit switches (lift, active LOW) | top 22, bottom 21 |
| Nong servos 1–8 (signal) | 32, 33, 25, 26, 21, 22, 27, 14 |
| RS485 (UART2) | RX 16, TX 17, DE+/RE 4 |
| microSD (VSPI) | CS 5, SCK 18, MISO 19, MOSI 23 |
| WS2812B strip | 13 |
| I2S amp (MAX98357A) | BCLK 27, LRC 14, DIN 2 |

These are only **defaults** — each board's real pin map lives in its NVS and is
set from the website's "Hardware pins" card, no recompile. Nong servos as
built: PDI-1181MG shoulders (270°), MG90S elbows (180°), TianKongRC 35 kg waist
(270°), MG90S shrug — servo type, gear ratio, pulse range and max °/s are per
joint and changeable at runtime.

Power servos from a separate 5 V supply with common ground; eight MG90S can
pull several amps.

## Getting started

1. Flash any ESP32 with `firmware/` — `pio run -e mice_nong -t upload` (or
   `-e mice_lift`, or `-e mice_blank` if the board is not a module yet).
2. The board boots as **MOD-XXXXXX**, type `blank`. Open its website (it starts
   its own AP if it cannot reach WiFi), set ID / name / type, reboot. The type
   list offers what this binary was built with.
3. Run the hub (`main_python/`) on a PC on the same network — the module shows
   up in the list.
4. For a `nong` board, open Nong Studio from the hub, build a sequence, export
   the YAML to the SD card's `/moves/`, then run it with `MOVE <file>`.

## Not in this repository

`.pio/` (PlatformIO build output and downloaded libraries, ~230 MB) and other
build trees are ignored — `pio run` regenerates them. The CAD models live
outside this folder, in `../model/`.
