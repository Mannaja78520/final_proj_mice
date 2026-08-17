# Mice Control Hub — the main program

The **first web page of everything**. Start it and it finds all modules by
itself — no typing `nong.local` or IP addresses.

```
MiceHub.exe          Windows: double-click (or run_hub.bat)
python main.py       any OS with Python 3.8+ (Ubuntu: sh run_hub.sh)
```

Opens `http://127.0.0.1:8642/` and also prints a **WiFi URL** that phones and
other laptops on the same network can open.

## What the hub shows

- **Modules on the network** — the hub scans the local WiFi and lists every
  module board it finds (name, id, type, IP, SD). Click **⚙ Open module** to
  open that module's full website. This is dynamic: any new module type added
  to the firmware later appears here automatically.
- **One site over every transport.** The module website is served at
  `/mod?dev=wifi:<ip>` or `/mod?dev=usb:<port>[:<id>]` — it's the module's own
  page (`firmware/src/web/WebUI.h`) with a transport shim, so control, the
  Setup login, Hardware pins, users, sequences and files are **identical over
  WiFi, USB and RS485**. The hub adds an ESP32 **pinout reference image**
  (`/pinout.svg`, served from the PC — not embedded on the ESP32, to save its
  flash) into the Hardware pins card.
- **Nong Studio** (`/studio/`) — the humanoid pose & sequence editor is a
  function of this program. On a `nong` module the hub also shows
  **Studio + monitor**: one click opens the editor already connected — over
  WiFi *or* over the USB cable — with the 3D model live-simulating the real
  robot.
- **USB serial ports** — every COM port on this PC (for USB / RS485
  connections from the module website and Nong Studio).

### One cable, many pages

A COM port can only be opened by **one program at a time**. The hub is that
program: it opens each cable once and **shares** it, running every command
under that port's lock. So the module website (`/mod?dev=usb:COM7`), Nong
Studio's *USB (shared)* link and the hub's own port probe can all be open on
the **same cable at the same time** instead of one of them failing with
*"serial port already in use"*. A port a page is actively driving is not
re-probed (the hub answers from the identity it already knows), so the
12-second auto-check never stutters live commands. The port is released after
~10 s of silence, so `esptool`, a serial monitor or Studio's optional *USB
direct (Web Serial)* mode can still take it — those are outside programs, and
while one of them holds the cable the hub says so and names what to close.

### Flashing a board over its cable

Every port in the USB list has **⚡ flash … as** — pick a module type and the hub
writes that firmware with esptool. It works on a port where nothing answered,
which is when you need it most.

```
GET  /api/flash/images        what this PC can flash, and what is missing
POST /api/flash?port=&type=   start (one cable at a time)
GET  /api/flash               progress, then ok / error
```

The images come from `firmware/.pio/build/mice_<type>/`, so
`pio run -e mice_nong` must have been run at least once — otherwise the page
says exactly that instead of offering a dead button. esptool is not a pip
dependency: PlatformIO already ships one, and `MICE_ESPTOOL` overrides the
command (QC uses that to test the whole path with no board).

**The cable is handed over completely** for the length of the flash: the hub
stops any show it is playing on that port, closes the handle, and refuses to
reopen it until esptool finishes. That is what every `port is busy` failure was.

### The hub is also the show's clock

A browser cannot run a show in a background tab: rAF is stopped and timers are
throttled to about once a minute, by policy. So when Nong Studio plays through
a link that goes through the hub (USB shared, or WiFi via the hub proxy), the
**hub** sends the moves and the page only draws them. Hide the tab, minimise
the window, open something else — the rehearsal keeps going.

| clock | survives | for |
|---|---|---|
| module (`MOVE <file>`) | the PC switched off | the show |
| **hub** (`/api/play`) | the browser closed | editing / rehearsal |
| browser | nothing | preview |

Only one may run at a time. The hub sends `MOVE STOP` before it starts, and any
live **motion** command aimed at the same device stops the hub's playback —
using the same `"motion": true` list the firmware compiles from
`firmware/config/commands.json`, so the hub and the board cannot disagree about
what counts as taking over.

```
POST /api/play       {dev, steps:[{pose[10], t, hold}], loop, name, from_ms}
GET  /api/play       where the show is now (running, at_ms, total_ms, step)
POST /api/play/stop  stop, and tell the module to hold where it is
```

## One .exe — what about Ubuntu / Android?

A Windows `.exe` **cannot run on other systems** — that is normal, it is a
Windows program format. But nothing is lost:

| System | How to run |
|---|---|
| Windows | `MiceHub.exe` (has the robot icon) or `run_hub.bat` |
| Ubuntu / Linux / macOS | `sh run_hub.sh` (plain Python, no installs) |
| Android / iPhone | don't run it — open the hub's **WiFi URL** in the browser; one PC on the network runs the hub for everyone |

## Files

```
main.py          the hub server (stdlib only) + Nong Studio backend + robot proxy
web/hub.html     the hub page
MiceHub.exe      frozen Windows build of main.py (PyInstaller, nong.ico)
run_hub.bat/.sh  launchers
```

Nong Studio's own files (web app, projects, sequences, models) stay in
`../nong/main_python_set_nong/` and are served from here. Command reference
for the modules: `../firmware/COMMANDS.md`.
