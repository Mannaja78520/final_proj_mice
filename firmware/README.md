# Modular show-module firmware (ESP32)

One firmware for every module in the installation. Each module knows its own
**ID**, **name** and **type** (stored in NVS flash), talks over **RS485 and
WiFi at the same time**, hosts its **own control website**, and keeps its data
(settings YAML, music, movement sequences) on a **microSD card**.

Current module types: `lift` (motor up/down between stages, RGB strip,
speaker, stage tracking) and `nong` (humanoid upper body: 2 arms, universal
shoulder + universal elbow per arm — hardware is just 8× MG90S + SD card;
poses/sequences authored in the desktop editor at
`code/nong/main_python_set_nong`). More types plug into `src/modules/`.

**Upload once, choose later:** the same binary runs every module type — flash
each board one time, then pick what it is with `SET TYPE lift|nong` (Settings
card on the website) and reboot. The firmware lives here at `code/firmware`
and is shared by the whole installation.

## Layout

```
config/                 hardware config, split per module + shared core:
  esp32_hardware.h              shared core ONLY (MCU/PWM, RS485, SD) + includes:
  esp32_hardware_lift_module.h    lift: motor/encoder/limits/rack + RGB + I2S amp
  esp32_hardware_nong_module.h    nong: servos/pulse/limits/gear
  (RGB strip + I2S speaker are lift-only, so they live in the lift file;
   only RS485 + SD are shared by every module type)
  conf_network.h                WiFi AP fallback
  (these are only DEFAULTS — each board's real pin map lives in its NVS and is
   set from the website "Hardware pins" card / PIN command, no recompile)
src/main.cpp            boot + wiring, ~50 lines
src/core/               shared services, used by every module type
  Identity              id/name/type/wifi stored in NVS
  HwConfig              runtime pin map in NVS (hw.pins.*), set from the web
  UserStore             Setup-page login accounts in NVS (default manny/12345678)
  CommandRouter         one command language for RS485 / web / serial / sequences
  RS485Bus              half-duplex UART2 bus, addressed + broadcast
  WebPortal             WiFi (STA + AP fallback), website, REST, WebSocket, file manager
  SDStore               SD card + YAML, one mutex for the shared SPI bus
  AudioPlayer           MP3/WAV from SD over I2S
  RgbStrip              WS2812B effects
  SequencePlayer        /moves/*.yaml step player
src/modules/            one folder per module type
  lift/LiftModule       the lift implementation
  nong/NongModule       the humanoid upper body (8x MG90S, multi-ESP link mode)
sd_card_example/        copy this onto each module's SD card
```

## Command language (same everywhere)

**Full reference with per-channel examples (website, HTTP API, USB serial,
RS485 framing, sequence YAML): [COMMANDS.md](COMMANDS.md).** Any single link
reaches the whole fleet: `#<id>`-prefixed lines on USB or the website console
are bridged onto the RS485 bus, and `tools/usb-console.html` gives a
website-like UI over a USB cable (Chrome/Edge). Quick table:

Over the website console, `GET /api/cmd?c=...`, USB serial, or RS485
(`#<id> <command>`, replies `@<id> <reply>`, `#*` = broadcast):

| Command | Meaning |
|---|---|
| `PING` | → `PONG <id> <name> <type>` (broadcast-safe discovery) |
| `INFO` | one-line status JSON |
| `SET ID <1-247>` / `SET NAME <name>` / `SET TYPE <lift\|nong\|blank>` | change identity, saved to chip |
| `SET WIFI <ssid> <pass>` | stored WiFi override (reboot to apply) |
| `SET WIFI ON\|OFF\|AP` | radio mode — `OFF` = USB/RS485 only, `AP` = own hotspot only |
| `UP` / `DOWN` / `STOP` / `HOME` | manual motion (limits always win) |
| `GOTO <stage>` | move to a stage; auto-homes first if needed (no encoder: endpoints only) |
| `STAGE?` | current stage (`-1` = not homed yet) |
| `SPEED <pwm>` / `SPEED <v> MS` / `SPEED?` | travel speed as PWM or m/s (rack module 2 + 25T pinion = 157.08 mm/rev) |
| `TIME? [stage]` | estimated travel time at the current speed |
| `RGB <r> <g> <b>` / `RGB BRIGHT <n>` / `RGB EFFECT solid\|rainbow\|chase\|breathe\|off` | strip |
| `PLAY <file>` / `PLAY STOP` / `VOL <0-100>` | speaker (files in `/music`) |
| `POSE <a1..a8> [T <ms>]` / `POSE?` / `JOINT <n> <deg>` | nong arms (8 joints, deg 0-180; T floors at the servo limit; see COMMANDS.md) |
| `RELAX` / `ATTACH` / `SPEED <deg/s>` | nong: servos limp / powered, move speed |
| `MOVE <file>` / `MOVE STOP` | run a `/moves/*.yaml` sequence |
| `CFG` / `CFG <key> <n>` / `CFG CLEAR [key]` | module settings stored on the chip (works without SD): `leds speed stages counts_per_stage volume` |
| `REBOOT` | restart |

## First boot

A freshly flashed board names itself after its chip MAC (**MOD-XXXXXX**, and a
MAC-derived RS485 id) and boots as type **blank** — no hardware assumptions.
Open its website (or USB serial / RS485), go to Settings, and pick what it is:
`SET TYPE lift`, give it a name and id, save & reboot. The MAC name guarantees
every board is unique out of the box, even before you configure anything.

## Website

`http://<name>.local/` (or the IP printed on serial). If the configured WiFi
is unreachable the module opens its own AP named after the module (fallback
pass in `conf_network.h`), serves the same page there, and keeps retrying the
real network every 60 s in the background — if the router/hotspot appears
later, the module joins it automatically. On a failed connect it prints a
diagnosis on serial: whether the SSID is visible on 2.4 GHz, its channel and
auth, and the disconnect reason (wrong password vs network not found).
**Note: the ESP32 only supports 2.4 GHz WiFi — phone/laptop hotspots often
default to 5 GHz.** The page controls motion, RGB, speaker, sequences, has
an SD file manager (upload/download/delete) and a settings panel for
ID/name/type/WiFi.

### Fleet view (many modules at once)

Every module advertises itself as mDNS service `_module._tcp` and scans for
the others in the background. The **"Modules on network"** panel at the top of
every module's website lists the whole fleet — name, ID, type, IP — and
clicking one jumps to that module's page. So whichever module you open acts as
the main website; there is no separate master to set up.

## SD card (optional)

Copy `sd_card_example/` contents to the card root: `/data/module.yaml`
(settings: speed, stages, counts_per_stage, leds, volume), `/music/*.mp3|wav`,
`/moves/*.yaml`.

**No card?** Everything still runs — website, RS485, motion, RGB, identity.
Only music and `/moves` sequences need the card. Settings then live in NVS via
the `CFG` command (which also *overrides* the card's `module.yaml` when both
exist), e.g. `CFG leds 60`, `CFG counts_per_stage 3800`, `CFG CLEAR`.

## Wiring (see `config/esp32_hardware.h`)

| Function | Pins |
|---|---|
| Motor driver (lift) | IN_A 33, IN_B 32 |
| Encoder (lift) | A 25, B 26 |
| Limit switches (lift, active LOW) | top 22, bottom 21 |
| Nong servos 1-8 (MG90S signal) | 32, 33, 25, 26, 21, 22, 27, 14 |
| RS485 (UART2) | RX 16, TX 17, DE+/RE 4 |
| microSD (VSPI) | CS 5, SCK 18, MISO 19, MOSI 23 |
| WS2812B strip | 13 |
| I2S amp (MAX98357A) | BCLK 27, LRC 14, DIN 2 |

A nong board uses ONLY the servo pins, the SD card and RS485/WiFi — no
encoder, RGB or speaker. The servo pins reuse lift-only pins (a board is one
type at a time; all ordinary GPIOs, no boot straps, so one ESP32 runs the
whole humanoid) and are per-board configurable with `servo_pins` in
`module.yaml` — set a pin to `-1` when that joint lives on another board
(2-ESP humanoid: pick the partner with `link`/`peer`, see COMMANDS.md).
Power the servos from a separate 5 V supply with common GND; 8 MG90S can
pull several amps.

## Adding the next module type

1. `src/modules/<type>/<Type>Module.h/.cpp` implementing `Module`
2. register it in `src/modules/ModuleFactory.cpp` (`create()` + `KNOWN_TYPES`)
3. `SET TYPE <type>` + reboot — same firmware binary on every board.
