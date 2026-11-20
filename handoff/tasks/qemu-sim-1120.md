# Run the real firmware in an emulator (no lab)

Owner: claude
Updated: 2026-11-20
Branch: claude/project-thread-hbm8h3
Last commit: this checkpoint
Plan: none (user 2026-11-20: "can you simulate the board when uploading, or simulate more things")

## Goal
Boot the compiled firmware on Espressif's QEMU (ESP32) so commands, the
FWBEGIN/FWDATA/FWEND update and NVS persistence run on real code, not fakes.

## Doing now
PR for check_qemu_bus (2-board RS485).

## Done
- qc/lib/qemu_board.py (QemuBoard: boot, cmd, reboot), tools/qemu_esp32.py (install QEMU into .local/qemu).
- qc/checks/check_qemu_firmware.py: nong + gacha firmware. Proven by sabotage (BusUpdate.cpp md5 guard off -> 6 fails).

## Next
- Lift and dummy firmware do NOT run in QEMU: lift stalls in RGB RMT init, dummy answers nothing after boot (ADC mux). Would need a sim build flag; not done.
- Done 2026-11-20: qc/checks/check_qemu_bus.py (Rs485Bus joins UART2 of boards; -serial x3).
- Windows: tools/qemu_esp32.py Windows asset name is a guess, untested.

## Blocked / needs hardware
WiFi, OTA over HTTP, servos, hall pulses, SD: QEMU has no radio/peripherals.

## Facts found
- QEMU needs `-global driver=timer.esp32.timg,property=wdt_disable,value=true` or the bootloader loops on WDT.
- WiFi start crashes (register_chipv7_phy, no PHY): seed NVS wmode=off (qc/data/qemu_nvs_*.bin, made with esp-idf-nvs-partition-gen, namespace "module").
- UART at 115200 caps FWDATA at ~27 chunks/s: full 1.6 MB image = ~7 min, so QC sends a 112-byte sentinel app (qc/data/qemu_sentinel.c) that prints SENTINEL-SLOT-B via ROM ets_printf.
- Cloud pio build works now (registry reachable 2026-11-20): `pio pkg install -g -p https://github.com/platformio/platform-espressif32.git#v6.5.0` then `pio run -e mice_nong` (7 min cold).
- Finding for the lab: a gacha GDISPENSE that ends in `jam` still counts as given and takes one from stock (G? after jam: given 1, stock 2 from 3). Decide if intended.

## File status
| File | Change | State | Verification | Commit |
|---|---|---|---|---|
| qc/lib/qemu_board.py | new | done | quick, emulated | this checkpoint |
| qc/checks/check_qemu_firmware.py | new | done | 42 ok, sabotage proven | this checkpoint |
| qc/data/qemu_* | new NVS seeds + sentinel | done | same | this checkpoint |
| tools/qemu_esp32.py | new | done (installer download not re-run) | not run | this checkpoint |
| docs/systems.json, docs/systems/qc.md, qc/README.md | register + docs | done | docs checks (2 fail on plain main too) | this checkpoint |
| qc/checks/check_qemu_bus.py, qc/lib/qemu_board.py (bus) | new + extended | done | 12 ok; sabotage RS485Bus.cpp id filter -> fails | this checkpoint |
