# Lab: robot and prize ESP32 transport acceptance

Owner: codex:10231420-85cc (chat 01a167a0-2a75-7c93-89ea-81df71a29ff4)
Updated: 2026-10-23 19:02 (Bangkok)
Branch: codex/lab-hardware-1023
Tree: E:/final_proj/mice/code/.staging-lab-1023
Last commit: d9c97d4 baseline; see git log for checkpoint
Plan: A47-19 (combined), A47-5, A45-11, A46-2; native audit A48-12

## Goal
User at lab authorizes robot motion, gacha testing, one hardware gacha plus
another ESP32/dummy over USB, equal commands/config/status over USB/WiFi/RS485
and firmware updates over those routes. Verify inventory before assumptions.
Latest direct clarification: same board/default wiring as existing module;
RS485 currently NOT wired. User authorizes bounded motor/Hall identification.

## Doing now
Read-only transport/update audit and OS inventory; preserve every user setting.
No COM open/flash/motor/robot HTTP until deployment explicitly releases runtime.
Integration chat 01a1679e-50a4-7e71-9cfb-64b6afa635c1 owns gate/build/restart.

## Done
- Read AGENTS/HANDOFF/CLAUDE/COORDINATION, named lab handoffs, firmware rules,
  fw-gacha/fw-core/hub-flash/app-gacha headers and project contract/verification skills.
- Created isolated branch from origin/main d9c97d4 (#76); no source changes.
- Read-only Windows PnP finds CP210x COM9 (USB serial 0001), COM10 (location
  instance); Win32_SerialPort/Ports query was empty, so use PnPEntity too.
- Hotspot 192.168.137.1; ARP robot MAC B4-BF-E9-1C-5A-74 at .26, another peer .143.
  These are OS inventory, not authenticated board identity or availability proof.

## Facts found
- firmware/config/esp32_hardware_gacha_module.h:17-32: motor25/26, optional EN=-1,
  Hall33 active-low, magnets4/slots4/drop2, PWM600, timeout4000ms, settle0.
- firmware/config/esp32_hardware.h:30-33: shared RS485 RX16/TX17/DE4 at115200.
- firmware/src/main.cpp:151-162: direct USB lines call router.handle; #id lines
  use rs485.bridge. Gacha verbs use the same router as WiFi/RS485.
- firmware/src/core/CommandRouter.cpp:596-617: FWBEGIN/FWDATA/FWEND/FWABORT/FWSTAT
  are common commands (application spare-slot update), not USB ROM flashing.
- firmware/COMMANDS.md:207-246: USB esptool, WiFi HTTP OTA, any-channel FW*;
  bus chunks <=150 bytes with sequence/decoded length + final MD5.
- main_python/hub_flash.py:59-66,90-98: image env derives dynamically from
  module registry (mice_gacha); no separate gacha updater required by design.
- GSPIN is test-only and does not touch stock/counters; GDISPENSE reserves stock
  and counts before rotation. Preserve counts; do not use dispense for mapping.
- Native CAD audit proves geometry only; never use it as channel/direction/horn
  calibration. Parent HOME differs from all90; preserve live robot arrays.

## Next
1. Finish source audit for actual parity gaps; checkpoint before any edits.
2. Wait explicit integration runtime handover, then claim COM9/10, robot and
   gacha flash/motion resources under BRIDGE mutex; no other serial owner.
3. Inspect hub ownership/identity and each board non-mutating first (no DTR/RTS
   reset unless intentionally flashing known board). Back up INFO/pins/config.
4. On identified safe gacha use bounded low-speed GSPIN with STOP + Hall proof;
   distinguish hardware board vs dummy. Stop immediately on unexpected behavior.
5. USB/WiFi commands/config/status + firmware updates; RS485 physical route stays
   unproven without wiring. Then actual dispensing only on hardware board.
6. Robot idle/collision/limits check, bounded per-axis moves and safe stop; then
   saved motions/talk/video tests, coordinate camera with Face chat.

## Blocked
- Integration holds runtime gate/build/restart; no physical commands yet.
- COM identity/chip/type/pins/attached hardware not measured yet.
- RS485 explicitly not wired; dummy cannot prove dispensing or physical bus.

## Coordination
Human authorizes messages to parent 01a16787, integration01a1679e, Face01a1678d,
native audit01a16792 and main coordination01a1689b (full IDs in chat context).
Do not create additional chats. This chat is sole hardware owner; PC camera not
claimed. All real vs simulated evidence kept separate in private scratch.
