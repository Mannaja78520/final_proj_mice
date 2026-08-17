# Command reference — WiFi / UART / RS485

One command language on every channel. Send a text line, get a text reply.
Replies start with `OK`, `ERR`, `PONG`, or are a bare value (`STAGE?` → `2`).

> This file is the authoritative reference. It is updated together with any
> firmware change that adds/changes commands or APIs.

## Channels

### 1. WiFi — website

Open `http://<name>.local/` or the IP printed on serial (e.g. `http://10.77.237.159/`).
Everything is clickable, and the **Console** card at the bottom sends any raw
command from this table. If the module can't join WiFi it opens its own AP
named after the module (pass in `config/conf_network.h`) with the same website
at `http://192.168.4.1/`.

### 2. WiFi — HTTP API (for scripts / show controller)

```
GET /api/cmd?c=<url-encoded command>      -> reply text
```
```bash
curl "http://lift.local/api/cmd?c=GOTO%202"
curl "http://10.77.237.159/api/cmd?c=RGB%20255%200%200"
curl "http://lift.local/api/cmd?c=PLAY%20/music/intro.mp3"
```

Other endpoints:

| Endpoint | What |
|---|---|
| `GET /api/status` | full status JSON (stage, rgb, audio, wifi, ...) |
| `GET /api/peers` | all modules found on the network |
| `GET /api/files?dir=/music` | list SD files (`/music`, `/moves`, `/data`) |
| `GET /api/download?path=/music/a.mp3` | download a file |
| `POST /api/upload?dir=/music` | upload (multipart form file) |
| `GET /api/delete?path=/music/a.mp3` | delete a file |
| `WS /ws` | WebSocket: status JSON pushed every 500 ms; send any command line as a text frame, reply comes back as `> ...` |

### 3. UART (USB serial)

115200 baud, newline-terminated. Plug in USB, open a monitor
(`pio device monitor`), type a command, press Enter:

```
PING
PONG 1 lift lift
GOTO 2
OK goto 2
```

**Website-like UI over USB:** open `tools/usb-console.html` in Chrome/Edge,
click Connect, pick the COM port — buttons, live status badges, RGB/volume
controls and a console, all over the USB cable (Web Serial; no WiFi needed).
The same page works with a USB-RS485 dongle: pick a bus address in the
dropdown or type `#3 ...` commands.

> A COM port belongs to **one program at a time**. `pio device monitor`,
> `tools/usb-console.html` and Nong Studio's *USB direct (Web Serial)* mode
> each take the cable for themselves. The Mice hub instead opens the port
> once and **shares** it, so the module website (`/mod?dev=usb:COM7`) and
> Nong Studio's *USB (shared)* link can drive one cable at the same time.
> Close the exclusive tools before using the hub on that port, and vice versa.

**Bridging — reach the whole RS485 fleet through one USB cable:** on the USB
console (and the website console) any line starting with `#` is forwarded
onto the RS485 bus by the module you're connected to:

```
#3 GOTO 2          -> "-> sent, module 3's reply appears when it answers"
@3 OK goto 2       (streamed back when module 3 replies)
#* PING            -> every module on the bus answers, staggered
```

So it never matters *which* connection you have: WiFi only, USB only, or
RS485 only — one link to one module reaches everything.

### 4. RS485 bus

Wiring (MAX485-style transceiver): `RO→GPIO16`, `DI→GPIO17`, `DE+/RE→GPIO4`
(tied together), `A/B` to the bus, common GND. 115200 baud 8N1.

Frame format (ASCII lines ending with `\n`):

```
#<id> <command>        request to module <id>        e.g.  #3 GOTO 2
@<id> <reply>          reply from module <id>        e.g.  @3 OK goto 2
#* <command>           broadcast: everyone executes, nobody replies
#* PING                discovery: every module replies, staggered by id*20ms
```

Examples:

```
#3 PING                -> @3 PONG 3 lift-left lift
#3 SET NAME lift-left  -> @3 OK name=lift-left
#* RGB 255 0 0            (all modules red, no replies)
#* PING                -> @1 PONG 1 ... then @3 PONG 3 ... (staggered)
```

## Writing your own controller app (Python etc.)

All three channels are **live at the same time** and speak the **same
protocol**, so one app can support WiFi, USB, and RS485 with the same code.
WiFi is optional: boot is non-blocking (USB/RS485 respond ~1 s after power-on
even with no network anywhere), and `SET WIFI OFF` turns the radio off
completely for installations that only use the bus. One app pattern:
send a command line, read a reply line. Machine-readable data is JSON:
`INFO` (= `/api/status`, includes the module's IP) and `FILES <dir>`
(= `/api/files`).

```python
# WiFi (HTTP)
import requests
st = requests.get("http://lift.local/api/status").json()
print(requests.get("http://lift.local/api/cmd", params={"c": "GOTO 2"}).text)

# USB serial
import serial, json
s = serial.Serial("COM5", 115200, timeout=2)
s.write(b"INFO\n")
line = s.readline().decode().strip()      # skip boot log lines starting with '['
st = json.loads(line)
s.write(b"GOTO 2\n"); print(s.readline())

# RS485 (via a USB-RS485 dongle) — address each module, or broadcast
s = serial.Serial("COM6", 115200, timeout=2)
s.write(b"#3 INFO\n")
reply = s.readline().decode().strip()     # "@3 {...}"
st = json.loads(reply.split(" ", 1)[1])
s.write(b"#* PING\n")                     # discover every module on the bus
```

Notes for app authors: on USB the boot log shares the port — ignore log lines,
but match them precisely as a bracket **tag** (`[wifi] …`, `[sd] …`,
`[  1234][I]…`), **not** just any line starting with `[`. Some replies are JSON
**arrays** that also start with `[` (`PIN VALID` → `[{…}]`, `FILES` →
`["…"]`); a naive "skip anything starting with `[`" drops them and makes pin
config look unsupported over USB (the hub had exactly this bug). On RS485 every
reply is prefixed `@<id> `. Status can be polled with `INFO`, or pushed: connect a WebSocket to
`ws://<ip>/ws` and status JSON arrives every 500 ms. SD files can be
written/read/deleted on **any** channel: over HTTP use
`/api/upload|download|delete`, over USB/RS485 use the `FBEGIN`/`FDATA`/
`FEND`/`FREAD`/`FDEL` commands (base64 chunks) — the pose editor uses both
interchangeably.

## Commands — every module type

| Command | Reply | Notes |
|---|---|---|
| `PING` | `PONG <id> <name> <type>` | safe on broadcast, used for discovery |
| `INFO` | one-line status JSON | same content as `/api/status` (minus wifi) |
| `HELP` / `HELP <cmd>` | `POSE <a1..a10> [T <ms>] - move every joint…` | every command this board understands, straight from `config/commands.json` — so it can never advertise one it lacks |
| `SET ID <1-247>` | `OK id=3` | RS485 address, saved to chip immediately |
| `SET NAME <name>` | `OK name=...` | spaces allowed; also renames WiFi hostname, `<name>.local`, AP SSID |
| `SET TYPE <lift\|nong\|blank>` | `OK ... (reboot to apply)` | which module code runs after reboot |
| `SET WIFI <ssid> [pass]` | `OK wifi stored (reboot to apply)` | ssid without spaces; omit pass for open network |
| `SET WIFI ON\|OFF\|AP` | `OK wifi mode=off (reboot to apply)` | radio mode: `OFF` = no WiFi at all (USB/RS485 only, fastest boot), `AP` = always host own hotspot, `ON` = join network with AP fallback (default) |
| `CFG` | `CFG leds=30 speed=900 ...` | list settings stored on the chip |
| `CFG <key> <value>` | `OK ... (reboot to apply)` | keys: `encoder leds speed speed_mms stages stage_mm mm_per_rev counts_per_rev max_rpm counts_per_stage volume speed_dps max_dps link` — works without SD card, overrides module.yaml |
| `CFG CLEAR [key]` | `OK cleared ...` | remove one / all stored settings |
| `PIN?` | `{"motor_a":{"gpio":33,...},...}` | current hardware pin map (JSON) |
| `PINS` / `PINS?` | same as `PIN?` | aliases, so either spelling works |
| `PIN VALID` | `[{"g":0,"c":"strap"},...]` | which GPIOs are usable + class (ok/strap/in/flash/rgb) |
| `PIN <name> <gpio>` | `OK motor_a=33 (reboot to apply)` | wire a function to a GPIO (`-1` = disable). Stored in NVS, applied at boot |
| `PIN CLEAR [name]` | `OK cleared ...` | reset one / all pins to the compile-time defaults |
| `FILES [dir]` | `[{"n":"a.mp3","s":1234},...]` | list SD files as JSON (`/music`, `/moves`, `/data`) — same data as `/api/files` |
| `FBEGIN <file>` | `OK writing /moves/wave.yaml` | start writing an SD file over the text channel (bare name → `/moves`) |
| `FDATA <base64>` | `OK 120` | append a chunk (keep chunks ≤120 bytes so an RS485 frame fits) |
| `FEND` | `OK wrote /moves/wave.yaml` | finish the write |
| `FREAD <file> <off> <n>` | `<base64>` / `EOF` | read n bytes (≤120) from an SD file |
| `FDEL <file>` | `OK deleted /moves/wave.yaml` | delete an SD file |
| `MOVE <file>` | `OK playing /moves/demo.yaml` | run a YAML sequence from SD (`MOVE demo.yaml` looks in `/moves`) |
| `MOVE STOP` | `OK move stopped` | |
| `REBOOT` | `OK rebooting` | restarts ~1 s later |
| `AUTH <user> <pass>` | `OK <user>` / `ERR bad login` | check Setup-page login (accounts stored in NVS) |
| `USER LIST <user> <pass>` | `["manny",...]` | list accounts (caller must be valid) |
| `USER ADD <user> <pass> <new> <newpass>` | `OK added ...` | add an account (any logged-in user can) |
| `USER DEL <user> <pass> <target>` | `OK removed ...` | delete an account (never the last one) |
| `USER PASS <user> <pass> <newpass>` | `OK password changed` | change your own password |

### Setup page login

The module website has a **Setup** button (top-right). It gates the config
cards — Settings (id/name/type/WiFi), Hardware pins, and (nong) the Zero
calibration — behind a login. Accounts live in the board's NVS memory
(default **manny / 12345678**); after logging in you can **add users**, delete
them, and change your password. Passwords can't contain spaces. This is a
convenience gate on the UI — the command channel itself stays open for
scripts/RS485 (local installation), but `USER ADD/DEL/LIST/PASS` require valid
credentials.

### Hardware pins (configured from the web, stored on the board)

Instead of editing pins in the firmware before flashing, each board's **pin
map lives in its own NVS memory** and is set from the website
(**Hardware pins** card) or with the `PIN` commands. The board reads it at
boot, so one firmware binary fits any wiring — a pin change needs a reboot to
apply. Pin names come from `PIN?`: `motor_a motor_b motor_pwm enc_a enc_b
limit_top limit_down rs485_rx rs485_tx rs485_de sd_cs sd_sck sd_miso sd_mosi
i2s_bclk i2s_lrc i2s_dout servo1..servo8`. `-1` disables a pin. GPIO 6–11 are
the flash pins (never usable); 34–39 are input-only (fine for `enc_*`/`limit_*`,
not for outputs); 0/2/5/12/15 are boot-strapping pins (usable with care). The
**WS2812/RGB data pin stays compile-time** (FastLED fixes it at build time) —
it's shown as `rgb` in `PIN VALID` and can't be reassigned from the web.

## Commands — lift module

**No encoder?** Set `encoder: 0` (module.yaml) or `CFG encoder 0`. The lift
then only moves between the limit switches: `UP`/`DOWN`/`HOME` work normally,
`GOTO` accepts only stage `0` (bottom limit) and the top stage, `STAGE?` knows
the stage only while a limit switch is pressed (`-1` in between), and the
web UI shows only the endpoint stage buttons. `SPEED <v> MS` still works
(open-loop mapping, no encoder needed).

| Command | Reply | Notes |
|---|---|---|
| `UP` / `DOWN` | `OK up` / `OK down` | run until limit switch or `STOP` |
| `STOP` | `OK stopped` | also cancels `GOTO` |
| `HOME` | `OK homing` | slow down to bottom limit, zeroes the encoder |
| `GOTO <stage>` | `OK goto 2` | 0..stages-1; auto-homes first if position unknown |
| `STAGE?` | `2` (or `-1` if not homed) | current stage |
| `SPEED <100-1023>` | `OK speed pwm=900 (~0.23 m/s)` | travel speed as raw PWM (persist with `CFG speed`) |
| `SPEED <v> MS` | `OK speed=0.20 m/s (pwm 781, 500mm in ~2.5s)` | travel speed in m/s, e.g. `SPEED 0.2 MS` (also `MMS` for mm/s); persist with `CFG speed_mms` |
| `SPEED?` | mode, pwm, m/s, time per stage | check the current speed setting |
| `TIME?` | `EST 2.5 s (500 mm @ 200 mm/s)` | estimated time for one full stage |
| `TIME? <stage>` | `EST 5.0 s (1000 mm to stage 2 @ 200 mm/s)` | estimated time from the current position to `<stage>` |
| `RGB <r> <g> <b> [bright]` | `OK rgb set` | 0-255 each |
| `RGB BRIGHT <0-255>` | `OK bright=128` | |
| `RGB EFFECT <name>` | `OK effect=rainbow` | `solid rainbow chase breathe off` |
| `PLAY <file>` | `OK playing /music/a.mp3` | mp3/wav from SD; `PLAY a.mp3` looks in `/music` |
| `PLAY STOP` | `OK audio stopped` | |
| `VOL <0-100>` | `OK vol=70` | runtime only; persist with `CFG volume` |

### Speed in m/s — how it works (rack & pinion)

Mechanics are configured in `config/esp32_hardware.h` / `module.yaml` / `CFG`:
rack **module 2** with a **25-tooth pinion** gives `mm_per_rev = π × 2 × 25 =
157.08 mm` of rack travel per pinion revolution. Rack speed at full PWM =
`max_rpm / 60 × mm_per_rev` (100 RPM → 0.262 m/s), and `SPEED <v> MS` maps m/s
to PWM linearly. With `stage_mm: 500`, one stage at 0.2 m/s takes ~2.5 s
(`TIME?` computes this live). The mapping is open loop — calibrate `max_rpm`
by comparing the `measured ... m/s` value shown in the web UI (encoder-based)
against the commanded speed. `counts_per_rev` = encoder counts per **pinion**
revolution (encoder counts/rev × gearbox ratio) makes positions and measured
speed correct.

## Commands — nong module (humanoid upper body)

Two arms, no fingers. **Hardware: 10 servos + (optional) microSD card**
(no encoder, no RGB strip, no speaker; those belong to the lift wiring, so
`RGB`/`PLAY`/`VOL` answer `ERR unknown cmd` on a nong board). **The SD card is
optional** — without it the nong still runs fully on live commands
(POSE/JOINT/HOME/SETZERO… from Nong Studio over WiFi/USB/RS485); the card is
only needed to store `/moves` sequences and to remember calibration across
reboots. One ESP32 drives the whole humanoid by default. Each arm: universal
joint in the shoulder + universal joint in the elbow, every universal joint =
**2 servos** → 8 arm joints, **plus 2 body joints**: `WAIST` (yaws the whole
upper body left/right so nong can look to the side) and `SHRUG` (lifts both
shoulders a little). **10 logical joints**, always in this order (angles are
**joint degrees** — the physical joint angle — neutral 90, clamped to each
joint's own `[min,max]`; a 2-servo universal joint cannot reach the full 0–180,
so the arm default range is 30–150, and SHRUG is deliberately tiny at 87–93 =
~6°. The servo itself runs its own travel — 180 or 270°; the firmware converts
joint→servo through the gear, so the servo uses its full range while the joint
stays safe):

| # | name | axis | # | name | axis |
|---|---|---|---|---|---|
| 1 | `L_SH_P` | left shoulder pitch | 6 | `R_SH_R` | right shoulder roll |
| 2 | `L_SH_R` | left shoulder roll | 7 | `R_EL_P` | right elbow pitch |
| 3 | `L_EL_P` | left elbow pitch | 8 | `R_EL_R` | right elbow roll |
| 4 | `L_EL_R` | left elbow roll | 9 | `WAIST` | body yaw (turn left/right) |
| 5 | `R_SH_P` | right shoulder pitch | 10 | `SHRUG` | both shoulders up/down |

As built: shoulders are **PDI-1181MG (270°)**, elbows **MG90S (180°)**, WAIST a
**TianKongRC 35kg (270°)**, SHRUG an **MG90S (180°)** — but every joint's servo
type, gear, pulse and travel is set per joint at runtime (see `SERVO`/`RANGE`
below), so any of them can be swapped later.

Moves are interpolated with a smooth ease-in/out over a duration `T`; without
`T` the duration is `largest joint delta ÷ speed` (deg/s). Poses/sequences are
authored in the desktop editor (`code/nong/main_python_set_nong`), exported as
YAML, copied to `/moves/` on the SD card, and picked + run from the website's
**Sequences** card (or `MOVE <file>`).

**Move times are physically honest.** The servos cannot exceed `max_dps`
(default 400 deg/s, MG90S), so any commanded `T` shorter than
`largest joint delta ÷ max_dps` is **raised** to that minimum — otherwise the
interpolation would "finish" before the real arm arrives and the next step
would start from a pose that was never reached. Longer times are always
allowed. The reply reports the effective `T`; the editor enforces the same
floor while authoring.

| Command | Reply | Notes |
|---|---|---|
| `POSE <a1..a10> [T <ms>]` | `OK pose T=800ms` | all 10 joints; `-` keeps a joint; a shorter list (e.g. an old 8-joint pose) leaves the rest untouched; no `T` = duration from speed; `T` below the physical minimum is raised |
| `POSE?` | `90.0 45.0 ...` | current 10 angles |
| `JOINT <1-10\|name> <deg> [T <ms>]` | `OK L_EL_P=120.0 T=500ms` | one joint, e.g. `JOINT WAIST 60` |
| `HOME [T <ms>]` / `ZERO` | `OK home T=1000ms` | move to the zero/home pose |
| `SETZERO` | `OK zero set ...` | calibrate: the current pose becomes home = 90° per joint (jog the arms straight first; trim absorbs the offset, the arm doesn't move). Saved to SD if present |
| `STOP` | `OK stopped` | freeze mid-move (pose holds) |
| `RELAX` | `OK relaxed (servos limp)` | servos unpowered — pose the arms by hand |
| `ATTACH` | `OK attached` | power the servos again, hold current pose |
| `SPEED <deg_per_s>` | `OK speed=120 deg/s` | 5–`max_dps`; persist with `CFG speed_dps` |
| `SPEED?` | `SPEED 120 deg/s (90 deg in ~0.75s)` | |
| `TIME? [a1..a10]` | `EST 800 ms @ 120 deg/s (min 225 ms @ max 400 deg/s)` | estimated + minimum duration of a move (editor helper) |
| `LIMIT?` | `{"min":[..],"max":[..],"gear_pinion":[..],"gear_gear":[..],"pulse_min":[..],"pulse_max":[..],"max_dps":[..],"servo_range":[..]}` | per-joint joint limits + gear + servo (JSON) |
| `LIMIT <1-8\|name> <min> <max>` | `OK L_EL_P limit 30..150` | set one **joint's** travel; clamps the pose, saved to `/data/nong_cal.yaml` |
| `GEAR [<1-8\|name\|ALL> <pinion> <gear>]` | `OK gear L_SH_P 15:18 ...` | **per-joint** servo→joint reduction; no args reports all 10 |
| `PULSE [<1-8\|name\|ALL> <minUs> <maxUs> [maxDps]]` | `OK pulse L_SH_P 500-2500us` | **per-joint** servo pulse range (+ optional speed limit); no args reports all 10 |
| `RANGE [<1-10\|name\|ALL> <deg>]` | `OK servo travel L_SH_P = 270 deg` | **per-joint SERVO travel**: 180 for a normal servo, 270 for a wide-angle one (60–360); no args reports all 10 |
| `RATE [<1-10\|name\|ALL> <hz>]` | `OK frame rate L_SH_P = 330 Hz` | **per-joint SERVO frame rate**: 50 for a normal hobby servo, **330 for the PDI-1181MG** digital servo (40–400). A wrong rate can make a digital servo chatter or cut torque ("disable itself"); no args reports all 10 |
| `SERVO [<1-10\|name\|ALL> <type>]` | `OK L_SH_P = pdi1181mg (500-2500us, 375 deg/s, 270 deg travel, 330 Hz)` | apply a servo preset — sets pulse + speed + travel + **frame rate**: `mg90s` (50Hz), `pdi1181mg` (270°, 330Hz), `tiankong35`, `generic180`, `generic270` (or a custom servo with `PULSE` + `RANGE` + `RATE`) |
| `CAL` | `CAL chip=saved sd=no card ...` | where the calibration is stored |
| `CAL CLEAR` | `OK calibration cleared ...` | forget it on the chip **and** the card; reboot loads the defaults |

**Joint limits + gear are dynamic and persistent — with or without an SD
card.** Angles are **joint degrees**; each joint is clamped to its own
`[min,max]` (a 2-servo universal joint binds near the ends — full 0–180 is not
reachable, default 30–150). `LIMIT`/`GEAR`/`PULSE`/`RANGE`/`RATE`/`SERVO`/
`SETZERO` change them live and save them **twice**:

| where | when | why |
|---|---|---|
| the chip's own memory (NVS) | always | so a board with **no SD card** keeps its calibration across a power cycle |
| `/data/nong_cal.yaml` | only if a card is fitted | a readable copy to inspect, back up, or move to another board |

At boot the card file is applied first and the chip copy second, so the chip
copy wins — it is written by every calibration command whether or not a card is
present, and can never be older than the file. `CAL` reports which copies
exist; `CAL CLEAR` forgets both and a reboot returns to the compile-time
defaults.
The **gear** (pinion on the servo, gear on the joint) means the joint
turns `pinion/gear` of the servo; the firmware converts each commanded joint
angle to `servo = travel/2 + (joint−90)×gear/pinion` using **that joint's own**
ratio and travel. Every joint's **rotation axis** (roll/pitch/yaw) is set in the
editor's Rig setup.

#### Servo travel (180 vs 270) — not the same as the joint limits

Two different numbers, and mixing them up is the usual mistake:

| | what it describes | set with |
|---|---|---|
| `servo_range` | how far the **servo** turns end to end — a property of the servo you bought (MG90S 180, wide-angle 270) | `RANGE` / `SERVO` |
| `joint_min`/`joint_max` | how far the **joint** may turn — a property of your mechanism | `LIMIT` |

Poses, sequences and neutral 90 are always **joint** degrees, so **fitting a
270° servo is a one-number change** — `RANGE 1 270` (or `SERVO 1 generic270`)
— and every saved sequence keeps working unchanged. Joint 90 sits at the
middle of the travel whatever the travel is (90° on a 180 servo, 135° on a
270), so the arm does not move at home; away from home the joint now turns the
correct amount instead of the amount a 180° servo would have given. Check the
motion away from home afterwards and re-run `SETZERO` if the joint needs
re-trimming. Each joint is independent: a 270 shoulder and a 180 elbow is fine.

### module.yaml keys (nong)

# order: 1-8 arms, then 9 WAIST, 10 SHRUG. A single number instead of a list
# applies to all 10 joints.
```yaml
servo_pins: [32, 33, 25, 26, 21, 22, 27, 14, 13, 15]  # pin per joint, -1 = other board
joint_min:  [30, 30, 30, 30, 30, 30, 30, 30, 30, 87]  # per-joint JOINT limits (deg):
joint_max:  [150,150,150,150,150,150,150,150,150, 93] # arms 30..150, WAIST wide,
                                              #   SHRUG tiny (~6 deg, 87..93)
trim:       [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]    # added at the servo (mounting offset)
invert:     [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]    # 1 = servo mounted mirrored
neutral:    [90, 90, 90, 90, 90, 90, 90, 90, 90, 90]  # HOME pose
# As built: shoulders PDI-1181MG 15:18 (270°), elbows MG90S 12:13 (180°),
# WAIST TianKongRC 35kg 1:1 (270°), SHRUG MG90S 1:1 (180°).
gear_pinion:  [15, 15, 12, 12, 15, 15, 12, 12, 1, 1]   # pinion teeth (on the servo)
gear_gear:    [18, 18, 13, 13, 18, 18, 13, 13, 1, 1]   # gear teeth (on the joint)
pulse_min:    [500,500,500,500,500,500,500,500,500,500]      # servo pulse (us)
pulse_max:    [2500,2500,2400,2400,2500,2500,2400,2400,2500,2400]
servo_range:  [270,270,180,180,270,270,180,180,270,180] # SERVO travel in deg —
                                              # 270 = wide-angle. NOT the joint's
                                              # range (that is joint_min/max)
frame_hz:     [50,50,50,50,50,50,50,50,50,50]  # SERVO frame rate (Hz): DEFAULT
                                              # 50 everywhere (it works). PDI-1181MG
                                              # datasheet says 330, but 330 tripped a
                                              # marginal shoulder — keep 50 unless a
                                              # servo needs more and current is safe.
speed_dps: 120                                # deg/s when a POSE has no T
max_dps: [375,375,400,400,375,375,400,400,200,400] # per-joint speed limit (floor
                                              # for move times); WAIST is slower
link: 0                                       # 1 on the LEADER only (2-ESP humanoid, below)
peer: 0                                       # partner module id (0 = broadcast to all)
```

### 2-ESP humanoid (link + peer)

**Use one ESP32 if you can** — the default pins drive all 10 servos from one
board (WAIST/SHRUG default to GPIO 13 and 15; if you also wire SD and RS485,
set those two to free GPIOs in the web pin config). Only if one board is not
enough (wiring runs, power) split the humanoid over two boards, e.g. one per
arm. All boards run the **same firmware** (upload once):

1. Flash both boards, `SET TYPE nong` on each, wire them to the same RS485
   bus, give them different ids (`SET ID`).
2. On each board set `servo_pins` so it drives only its own joints
   (`-1` for the others). Example right-arm + body board:
   `servo_pins: [-1, -1, -1, -1, 32, 33, 25, 26, 13, 15]`.
3. The board with the SD card (where sequences run) is the **leader**:
   `CFG link 1`, and **select its partner** with `CFG peer <id>` (the other
   board's RS485 id) — or use the "2-ESP pair" row on the leader's website
   (Nong Arms card). Every `POSE / JOINT / HOME / RELAX / ATTACH / SPEED`
   the leader executes is repeated to the partner as `#<id> POSE ... T <ms>`
   **with the resolved duration**, so both boards move seamlessly as one
   robot. `peer 0` broadcasts to every module instead — fine when the
   humanoid is the only thing on the bus, but with several robots always set
   the id. The partner keeps `link 0` — never set `link 1` on two boards.

Every board tracks all 10 logical angles (even joints it doesn't drive), so
`POSE?`/status on the leader always shows the whole humanoid.

## Sequence files (`/moves/*.yaml` on SD)

Each step key maps to a command, so anything above works in a file:

| YAML step | Runs | Waits? |
|---|---|---|
| `- goto: 2` | `GOTO 2` | waits until arrived |
| `- home: 1` | `HOME` | waits until homed |
| `- up: 1` / `- down: 1` | `UP` / `DOWN` | waits until limit |
| `- stop: 1` | `STOP` | no |
| `- wait: 1000` | (pause ms) | yes |
| `- rgb: [255, 0, 0]` or `- rgb: "255 0 0"` | `RGB 255 0 0` | no |
| `- effect: rainbow` | `RGB EFFECT rainbow` | no |
| `- bright: 200` | `RGB BRIGHT 200` | no |
| `- play: /music/a.mp3` | `PLAY /music/a.mp3` | no (plays in background) |
| `- vol: 80` | `VOL 80` | no |

### Chaining — one show from several files

A sequence can start another when it ends, so a show is built from short files
that can each be run and edited on their own:

```yaml
name: intro
next: wave.yaml      # when intro finishes, wave.yaml starts by itself
steps:
  - pose: "90 90 90 90 90 90 90 90 90 90 T 800"
```

`next` may be a bare name (looked up in `/moves`) or a full path. It runs only
when the sequence actually **ends** — `loop: true` never does, so loop wins.
Chains are limited to 16 files deep, so a file that points back at itself stops
instead of running forever. `MOVE STOP` ends the whole chain.

### Speed per sequence

Every sequence Nong Studio writes starts with its **own** speed:

```yaml
steps:
  - speed: 150       # deg/s for THIS sequence
  - pose: "..."
```

so each file runs at its own pace, and in a chain each hand-over sets the speed
again instead of sequence B inheriting whatever A left the module on. The
editor reads this step back when re-editing, so a sequence keeps its speed.

`speed` applies to any `pose`/`joint` step that carries no `T`. Studio always
writes an explicit `T`, so the speed is what the *times were computed from* —
change it in the editor and every keyframe time is recalculated.

A `speed` step may appear **anywhere**, so one move can run at its own pace:

```yaml
steps:
  - speed: 120
  - pose: "... T 900"
  - speed: 30        # this one gesture is slow
  - pose: "... T 3200"
  - speed: 120       # back to the sequence speed
  - pose: "... T 900"
```

That is what Nong Studio's per-keyframe **°/s** box writes: it re-times only
that move and restores the sequence speed after it. The editor reads these
steps back, so a per-move speed survives a round trip through the file.

Nong Studio writes this from the **"then run…"** box next to the sequence name,
which offers the files already on the card.
| `- pose: "90 45 120 90 90 135 60 90 T 800"` | `POSE ... T 800` | waits until the move finishes |
| `- joint: "L_EL_P 120 T 500"` | `JOINT L_EL_P 120 T 500` | waits until the move finishes |
| `- speed: 150` | `SPEED 150` | no (deg/s on nong, PWM on lift) |
| `- relax: 1` / `- attach: 1` | `RELAX` / `ATTACH` | no |
| `- cmd: "ANY RAW COMMAND"` | as-is | no |

Top-level keys: `name:`, `loop: true|false`, `steps:`. Examples in
`sd_card_example/moves/demo.yaml` (lift), `nong_wave.yaml` (humanoid, as
exported by the pose editor) and `rgb_show.yaml` (looping RGB-only light
show — the strip can be fully scripted from the SD card with no PC).
