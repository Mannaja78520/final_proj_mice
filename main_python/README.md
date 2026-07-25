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
  **Studio + monitor**: one click opens the editor already connected, with
  the 3D model live-simulating the real robot.
- **USB serial ports** — every COM port on this PC (for USB / RS485
  connections from Nong Studio).

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
