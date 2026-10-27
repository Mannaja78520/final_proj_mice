# Gachapon over USB, WiFi and RS485: hub QC proof + bare-ESP32 stand-in

Owner: claude:pzzxe0
Updated: 2026-10-27 13:50Z
Branch: claude/project-thread-pzzxe0
Last commit: see branch
Plan: A47-21 (A47-19 = gemini lab session 2026-10-23, real USB/WiFi parity done)

## Goal
User 2026-10-23 (in the lab, one ESP32 on the dispenser): continue what GPT did; gachapon
commanded and updated over WiFi, RS485 and USB like other modules; a second ESP32 on USB
pretends to be another machine. Hub too.

## Doing now
Full QC on the branch, then PR + merge.

## Facts found
- This thread hit the usage limit 2026-10-23 10:18Z; meanwhile gemini:10232000-lab did A47-19
  on the real board (USB/WiFi; RS485 not wired then) and codex merged A47-20 gacha safety.
- firmware/src/main.cpp USB reader + RS485 + WiFi /api/cmd feed one CommandRouter; FW* update
  (core/BusUpdate.h) rides any of them; WebPortal /api/ota for WiFi. No gacha-specific code.
- GachaModule.cpp `GCFG fallback <ms>`: no magnet -> pass counted by time, result "timed".
  That is the bare-ESP32 stand-in; no new firmware needed.
- main_python/gacha.py wait_done logged "timed" as a jam; now config given_results decides.
- hub_flash.py flash_env = "mice_" + type; flash_images lists every modules.json type.
- qc/lib/fake_serial.py GACHA_PORT COM96 / USB_GACHA id 72 (own cable, listed on request);
  fake_wifi MODULE.gacha answers as a dispenser behind the WiFi login gate.

## Done
- check_gacha_routes 19/19: usb:COM96, usb:COM99:70 (bus), wifi:<fake> each get GSTOCK +
  GDISPENSE; timed counts, jam does not; mice_gacha offered for flashing. Sabotage 3/3.
- docs/gacha/README.md: routes + stand-in steps.

## Next
1. Full QC, PR, merge, plan done A47-21, delete this file in the merge.
2. Lab: RS485 wired -> one prize + one FW* update over the bus (handoff/tasks/lab-day.md).

## Blocked
- RS485 on the real gacha board needs the wiring (lab).
