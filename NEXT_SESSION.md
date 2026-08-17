# Plan: split the firmware per module type — ALL FIVE STEPS DONE 2026-08-09

Every step below is finished and landed. The tree is green at **QC 1290**
(it was 1021 when this plan was written). Each step's own section says what it
turned into, and the CHANGELOG has the user-facing version.

| step | what | result |
|---|---|---|
| 1 | one binary per module type | nong 65.9%, lift 72.8%, cam 68.0%, blank 62.5% |
| 2 | the hub as the show clock | `POST /api/play` — a rehearsal survives the browser |
| 3 | hub flashes over USB | ⚡ flash … as, on any port, cable handed to esptool |
| 4 | OTA over WiFi | two app slots existed all along; a failed update cannot brick |
| 5 | camera module | `cam` type + `config/modules.json` registry |

**All of it has now run on real hardware** (2026-08-09, three boards):

| board | as | proven |
|---|---|---|
| COM9 | `nong` | flashed from the hub, boots as nong, type gate refuses `lift`, sequence/preemption and the hub clock drive it |
| COM16 | `lift` | flashed from the hub, `types:["lift","blank"]`, `STAGE?`/`RGB` answer |
| COM17 | `cam` | flashed from the hub, **updated over WiFi twice**, serves real 320×240 JPEGs |

Six faults came out of those sessions that no PC-side check could have found —
see the CHANGELOG entries for 2026-08-09. Each has a QC check now.

Still open on hardware:

1. A **nong board with servos actually attached** — COM9 is lift hardware, so
   the joints were never driven against a real arm.
2. **RS485** between two modules has not been exercised this session.
3. The camera's **SD card** path (`SNAP <name>`) — that board has no card, and
   its socket is on the SDMMC bus the camera also needs.

Also still open, and needing you rather than code: the SHRUG measurements below,
and the two boards that drop off USB (cable or power).

Read first: `code/qc/README.md`, `code/firmware/CLAUDE.md`,
`code/nong/main_python_set_nong/CLAUDE.md`. Work in `code/.staging/` and land
through `python promote.py` (full QC gate).

---

## Why this is being done

One binary today contains **every** module type. A nong carries the lift code
*and* the lift's web cards, and vice versa. Measured on 2026-08-07:

| | |
|---|---|
| flash used | **74.9%** — 1,472,545 of 1,966,080 bytes |
| free | ~493 KB |
| module website served by every board | **43.9 KB** |
| a lift's page contains `id="jointRows"` (nong markup) | **yes** — hidden at runtime, not absent |

Three more module types are planned plus a camera (esp32-camera is ~60–120 KB).
Adding any of it to the shared binary costs **every** module.

The user's own insight resolved it: **if the hub flashes boards, each board only
needs its own type.** Per-type builds then cost the other modules nothing.

It also closes a safety hole. Only a runtime capability check (`has('joints')`)
stops a lift showing joint sliders — and that check has already failed once:
`isNong` was used and never defined, which threw mid-handler and made the *right*
controls vanish. The mirror of that bug shows the *wrong* controls. With per-type
builds the wrong markup is **absent**, so no JavaScript bug can show it.

---

## Step 1 — split the build per module type — **DONE 2026-08-09**

Landed as firmware patch 0021. What it turned into, and the numbers:

| build | flash | page |
|---|---|---|
| all types (`mice_module_firmware`, kept) | 75.0% | 43.1 KB |
| `mice_nong` | 65.5% | 38.5 KB |
| `mice_lift` | 72.5% | 31.9 KB |
| `mice_blank` (core only) | 62.5% | 27.2 KB |

- Type chosen by `-D MICE_TYPE_*` per env; `src/core/BuildTypes.h` turns it into
  `MICE_HAS_LIFT` / `MICE_HAS_NONG`, and no flag means "carry everything".
- `src/web/WebUI.h` is now the **master** page and is not compiled.
  `tools/gen_tables.py` writes this env's page, command table and servo table
  into `.pio/build/<env>/generated/`; per-type regions are marked
  `<!--#type nong-->` … `<!--#end-->` (and `//#type` inside `<script>`).
- Verified in the BINARY, not the source: `check_build_split.py` searches
  `firmware.bin` for the other type's markup, and was proven by breaking the
  split and watching those six assertions fail.
- Also fixed on the way: the ArduinoJson `-I` in platformio.ini named one env's
  libdeps folder and would have been wrong for every other env.

**One assumption below turned out wrong.** Step 4 says each binary would be
"well under 1 MB" after the split. It is not: **62.5% is the floor** — WiFi, the
web server, SD and YAML, before any module exists. The nong module adds ~58 KB,
the lift ~196 KB (it owns FastLED and the MP3 decoder). So OTA has to be judged
against ~1.29 MB (nong) and ~1.42 MB (lift), not ~0.9 MB. A dual-app 4 MB layout
gives roughly 1.5 MB per slot: the nong fits, the lift is tight, and dropping
FastLED/ESP8266Audio from the lift (or a 8 MB module) is the lever if it does
not.

Original goal, for reference: `mice_nong`, `mice_lift`, `mice_blank` (names
open), each sharing the same core and containing **only its own** module class
and web cards.

Shared core, unchanged: `Identity`, `WebPortal`, `CommandRouter`, `RS485Bus`,
`SequencePlayer`, `SDStore`, `PeerDiscovery`, groups/WiFi.

Where the per-type content lives today:

- `src/modules/ModuleFactory.cpp` — registers every type
- `src/web/WebUI.h` — ONE page, all cards, C++ raw string literal
- `config/commands.json` — entries already carry `scope: core|lift|nong`
- `firmware/tools/gen_tables.py` — **already generates headers at build time**
  (`ServoPresets.h`, `CommandHelp.h`) via a PlatformIO `extra_scripts` pre-hook

**Use the generator that already exists.** `gen_tables.py` is the established
pattern — extend it to emit a per-type `WebUI.h` and a per-type command table
from a build flag (e.g. `-D MICE_TYPE_NONG`). Do not hand-maintain three copies
of the web page.

Suggested shape in `platformio.ini`:

```ini
[env:mice_nong]
extends = env:mice_module_firmware
build_flags = ${env:mice_module_firmware.build_flags} -D MICE_TYPE_NONG
```

Keep `mice_module_firmware` working (all types) until the split is proven —
`check_firmware_build.py` builds it and QC depends on it.

**Verify:** each env builds; flash % drops for each; a lift binary contains no
`jointRows`; `pio test -e native` still passes (20 tests).

---

## Step 2 — hub becomes the show clock — **DONE 2026-08-09**

`ShowPlayer` in `main_python/main.py` + `POST /api/play`, `GET /api/play`,
`POST /api/play/stop`. Studio hands the timeline over whenever the link goes
through the hub (`hubDriven()` = live link and not Web Serial direct); the page
then draws only, and `playTick` sends nothing.

- Same wire traffic as before — `POSE … T <ms>`, one whole move at a time. The
  hub decides only WHEN a move starts, so the motion matches a module-played
  show exactly.
- One clock still: `MOVE STOP` before it starts, and a live motion command for
  the same device stops the hub player — the motion list is read from
  `firmware/config/commands.json`, the file the firmware compiles, so the two
  cannot disagree.
- Returning to the page re-syncs the play head from `GET /api/play`; the module
  hand-off is skipped while the hub drives.
- `check_hub_clock.py`, proven by breaking the wait and the takeover.
- Web Serial direct is unchanged: the browser owns that port, so the hub cannot
  reach the robot at all.

Original plan below.

### Step 2 (original)

This is the fix for *"it does not run in the background"*, and it is the biggest
day-to-day win for the user.

The browser **cannot** be fixed for this: a hidden tab has `requestAnimationFrame`
stopped and timers throttled to ~once a minute. That is browser policy, not a
JavaScript limitation. The user asked directly whether Python could do it —
**yes**, and that is the answer. The hub is a native process that already owns
the serial ports and nothing throttles it.

Three tiers, each right for a different job:

| Clock | Survives | Use for |
|---|---|---|
| Module (`MOVE <file>`) | PC off entirely | the show |
| **Hub (Python)** | browser closed | **editing / rehearsal — the missing one** |
| Browser | nothing | preview only |

The hub tier is also the only one that helps while *editing*, before a sequence
has been uploaded.

Already in place and should be kept: Studio hands off to the module on
`visibilitychange` (`handOffToRobot`), and `playTick` clamps `dt` to
`MAX_TICK_MS` so returning to the page cannot teleport the show.

---

## Step 3 — hub flashes boards over USB — **DONE 2026-08-09**

`Flasher` in `main_python/main.py` + `GET /api/flash/images`,
`POST /api/flash?port=&type=`, `GET /api/flash`. The hub page shows
**⚡ flash … as** on every USB port, including ones where nothing answered.

- The cable is given up for the whole job: the show player is stopped if it was
  on that port, the handle is closed, and `_flash_ports` makes `_usb_get` and
  the probe refuse it until esptool finishes. This is the `port is busy` fix.
- esptool comes from PlatformIO's own copy (`~/.platformio/packages/
  tool-esptoolpy/esptool.py`), run with PlatformIO's python when the hub is
  frozen. `MICE_ESPTOOL` overrides it — QC drives the whole path with a fake.
- Images are `firmware/.pio/build/mice_<type>/` (bootloader/partitions/
  boot_app0/firmware). Not built = the page says which command builds it.
- `check_flash.py`, proven by removing the cable guard.

**Still open for a fresh machine:** `MiceHub.exe` has no esptool bundled, so on
a PC without PlatformIO the button explains itself instead of working. Vendoring
esptool (~0.5 MB) into the repo is the fix when that matters.

### Step 3 (original)

The hub already knows which module is on which cable. Pick a type in the Network
tab → it flashes the right binary.

- needs esptool; `main.py` is stdlib-only, but `MiceHub.exe` is PyInstaller-frozen
  so bundling is fine
- **stop the hub, or close the port first** — uploads fail `port is busy`
  otherwise (hit repeatedly on 2026-08-07)

---

## Step 4 — OTA, flashing over WiFi — **DONE 2026-08-09**

**The blocker below was wrong, and it was wrong from the start.**
`min_spiffs.csv` does not give one app partition — it gives **two**:

```
app0, app, ota_0, 0x10000,  0x1E0000     1,966,080 bytes
app1, app, ota_1, 0x1F0000, 0x1E0000     1,966,080 bytes
```

That is why the build always reported "used X from 1966080 bytes" — 1966080 is
one slot, not the flash. So OTA needed no partition change and was never
blocked by size: nong sits at 66% of a slot, lift at 73%.

What was actually built:

- Firmware `POST /api/ota` (multipart `firmware.bin`) using `Update`, then
  reboot. Refused while moving or while a sequence plays (`?force=1` overrides)
  — a flash write stalls the servo loop.
- `OTA` command: `running=app0 size=… target=app1 room=… free=…`.
- Hub `POST /api/ota?ip=&type=`, sharing the one flashing job with USB
  flashing, and **⚡ update over WiFi** on any module row with an IP.
- Only the app image goes over the air; bootloader and partition table never do.
- `check_ota.py` — two slots, every build fits one with margin, the board's
  guards, and the image arrives byte for byte. Proven by truncating the upload.
- Cost: 6 KB of flash.

**First update still needs a cable** — older firmware has no `/api/ota`.

### Step 4 (original, with its wrong premise)

The user specifically wants this and finds it the most interesting part. It is
step 4 only because of a hard blocker, not priority:

OTA needs **two** app partitions so a failed update can boot the old firmware.
Today `board_build.partitions = min_spiffs.csv` gives ONE 1.9 MB app partition.
On 4 MB flash, OTA means ~1.5 MB each — and the current binary is **1.47 MB**.
That fits with ~30 KB spare, which is no margin.

**After step 1 each binary is well under 1 MB and OTA fits comfortably.** The
split is what makes WiFi flashing safe, not a detour before it.

---

## Step 5 — camera module — **DONE 2026-08-09**

`cam` is a real module type: `src/modules/cam/CamModule.{h,cpp}`,
`[env:mice_cam]` (board `esp32cam`, min_spiffs so it gets OTA too), `SNAP` and
`CAM` commands, a `/api/cam.jpg` frame endpoint and its own web card. 68.0% of
flash, and nong/lift are unchanged by it existing.

On the way it turned module types into a registry — `config/modules.json` —
because "just another type" is only true if adding one is a single declaration.
`BuildTypes.h` and `ModuleTable.h` (the factory) are generated from it, and the
hub's flash list reads it, so `ModuleFactory.cpp` is no longer a list.

`check_camera.py` walks that chain; `check_build_split.py` builds the camera too.

**Not run on hardware.** The ESP32-CAM has not been flashed or photographed
with. Everything here is a real build of the real driver plus source-level
checks. Flashing it may need BOOT/IO0 held to GND (the CAM-MB shield's button).

### Step 5 (original)

ESP32-CAM (AI-Thinker) + CAM-MB shield (CH340, appeared as COM17). By then it is
just another type, costing the other modules nothing.

**It can never be a servo module** — the camera occupies GPIO
0,5,18,19,21–23,25–27,32,34–36,39 and the SD card 2,4,12–15. Nothing left for PWM.
Flashing it may need BOOT/IO0 held to GND.

---

## Bench notes that cost time on 2026-08-07

- **COM numbers move constantly.** The same board was COM9/11/12/13/14/16 in one
  week. List ports and identify by `PING` (returns id, name, type). Never trust a
  remembered port number.
- **Stop the hub before flashing.** It re-opens ports and uploads then fail.
- Opening a port with pyserial **reboots the board** unless `dtr`/`rts` are set
  false *before* `open()`.
- Boards drop off USB mid-session (cable/power, not firmware).

## Open, waiting on the user

- **SHRUG measurements.** The calibration curve is built, tested and landed; it
  just needs numbers. Their rig has `neutral[9] = 93`, `min 79`, `max 107`.
  Table: SHRUG angle → left rise mm, right rise mm (up positive), 3–5 rows.
- Two boards dropping off USB — cable or power.

## A trap worth not repeating

`check_shrug_curve.py` hardcoded `93` as "a moved SHRUG position". The user's rig
has neutral **93**, so the test asserted the bar rocks while sitting at rest, and
blamed the code. **Derive test angles from `RIG`, never hardcode joint values** —
the rig is user data and it changes.
