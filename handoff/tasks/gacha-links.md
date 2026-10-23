# Gachapon over USB, WiFi and RS485 (commands + firmware update) and GPT's open branches

Owner: claude:pzzxe0
Updated: 2026-10-23 10:25Z
Branch: claude/project-thread-pzzxe0
Last commit: (base d9c97d4)
Plan: A47-19

## Goal
User 2026-10-23 (in the lab, one ESP32 wired to the dispenser): check how far GPT got and
continue it. Gachapon must be commanded and updated (OTA) over WiFi, RS485 AND USB like the
other modules; a second ESP32 on USB pretends to be another machine. Hub too, all three.

## Doing now
Adding a "practice" setting (GCFG sim <ms>) to GachaModule so a bare ESP32 with no motor or
hall counts pretend magnets; then QC check that the hub drives a gacha over usb:, wifi:, bus.

## Facts found
- firmware/src/main.cpp:151-171 USB serial lines go to the same router as RS485/WiFi
  (`#id ...` lines bridge onto the bus): every module, gacha included, takes commands on all 3.
- firmware/src/core/BusUpdate.h: FWBEGIN/FWDATA/FWEND/FWABORT = firmware update by commands,
  so the same update rides USB, RS485 or WiFi; WebPortal.cpp:1095 /api/ota = WiFi HTTP OTA.
- main_python/hub_flash.py:59 env = "mice_" + type; :90 flash_images lists every type in
  firmware/config/modules.json (gacha included); start_bus :371 sends FW* to any dev address.
- main_python/main.py:869 dev_cmd(dev): wifi:<ip> -> /api/cmd, else usb_cmd (usb:<port>, bus).
- main_python/hub_api_gacha.py:78 find_dev = module name -> its fastest live route ("best").
- qc/lib/fake_serial.py:619-712 fake gacha boards 70/71 exist only ON THE BUS.
- GPT (codex) branches 2026-10-23: codex/continue-urdf-1023 has real code (A48-11 CAD HOME
  fallback for joints without forearm meshes + late floor config); face-pc-1023,
  gacha-reconcile-1023, native-axis-1023 are task-file-only (PC work: startup smoke,
  SolidWorks audit, A47-18 deploy).

## Done
- (none yet)

## Next
1. GCFG sim, build mice_gacha, check, PR, full QC, merge, tell coordinator (PC flashes).
2. Review + QC + merge codex/continue-urdf-1023 and the three task-file branches.

## Blocked
- Real flash/spin is the PC Remote Control session's job (user is in the lab now).
