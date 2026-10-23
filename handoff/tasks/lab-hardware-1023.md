# Lab: robot and prize ESP32 transport acceptance

Owner: codex:10231420-85cc (chat 01a167a0-2a75-7c93-89ea-81df71a29ff4)
Updated: 2026-10-23 19:24 (Bangkok)
Branch: codex/lab-hardware-1023
Tree: E:/final_proj/mice/code/.staging-lab-1023
Last commit: 71d8677 preparation checkpoint; see git log for current
Plan: A47-19 (combined), A47-5, A45-11, A46-2; native audit A48-12

## Goal
User at lab authorizes robot motion, gacha testing, one hardware gacha plus
another ESP32/dummy over USB, equal commands/config/status over USB/WiFi/RS485
and firmware updates over those routes. Verify inventory before assumptions.
Latest direct clarification: same board/default wiring as existing module;
RS485 currently NOT wired. User authorizes bounded motor/Hall identification.

## Doing now
Identity window completed and explicitly RELEASED in BRIDGE19:05. All physical
activity waits integration's post-deployment runtime handover. Preparing bounded
USB diagnosis/test steps; preserve every user setting.
Integration chat 01a1679e-50a4-7e71-9cfb-64b6afa635c1 owns gate/build/restart.
Agreed next window: integration builds to alternate output, stops old Hub,
sends WINDOW OPEN for raw USB identity/backup, then resumes final startup.
No Hub stop/restart by this chat. Motion/flash permission is a separate handover.

## Done
- Read AGENTS/HANDOFF/CLAUDE/COORDINATION, named lab handoffs, firmware rules,
  fw-gacha/fw-core/hub-flash/app-gacha headers and project contract/verification skills.
- Created isolated branch from origin/main d9c97d4 (#76); no source changes.
- Read-only Windows PnP finds CP210x COM9 (USB serial 0001), COM10 (location
  instance); Win32_SerialPort/Ports query was empty, so use PnPEntity too.
- Hotspot 192.168.137.1; ARP robot MAC B4-BF-E9-1C-5A-74 at .26, another peer .143.
  Peer .143 remains OS inventory only, not identified as a board.
- Integration granted bounded identity-only window before gate. Actual existing
  Hub INFO at WiFi192.168.137.26 returned nong id67/chipB4BFE91C5A74, idle/attached,
  seqfalse/audiofalse. Live joints=neutral [90,140,90,90,90,40,90,90,90,90.5].
  Complete INFO/calibration snapshot private root scratch/lab-hardware-1023/identity-first.json.
- Actual Hub INFO on COM9 and COM10 returned502 no reply; one COM10 follow-up
  timed out. Never opened a competing serial handle; no reset/flash/motor/config.
  Hub flash/play both idle. Released identity window immediately, no requests
  in flight. USB chips/types/firmware remain UNKNOWN, not a successful handshake.
- Native source audit found no gacha-specific transport/update omission: common
  router, module busy(), registry-derived image selection and generic hub routes.
  Root has no gacha firmware.bin; integration tree built image1408720bytes14:09.
  Check artifact/source provenance before using; never flash old nong bin.
- Prepared private root scratch/lab-hardware-1023/passive_uart.py (receive-only,
  no TX, DTR/RTSfalse, max5s/port) and rom_identity.py (esptool flash_id only,
  timeout35s/port, no erase/write, after=no_reset). Both syntax checked, NOT RUN.
  Installed tool C:/Users/manma/.platformio/packages/tool-esptoolpy/esptool.py v4.9.0.
- Integration final gate passed7910/0 +925stable; PR77 merged a884558. Under its
  explicit artifact lease, copied bootloader17536/partitions3072/firmware1408720
  to root firmware/.pio/build/mice_gacha. All SHA256 match source; no different
  destination bytes existed. Shared PlatformIO boot_app0.bin8192 exists.
  Firmware SHA25636c6d1d1364f7ff7567c371b6bf33a178f7ac7a2d89f6246ac81815d215172e4.
  Manifest private scratch/lab-hardware-1023/gacha-artifact-manifest.json.
  esptool image checksum/hash valid; firmware source diff d9c97d4..3e4cdd1 empty.
  Explicitly RELEASED artifact lease in BRIDGE19:24. No compile/board write.

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
- firmware/src/core/RS485Bus.cpp:203+: own-id #id frames dispatch locally and
  return @id; other IDs go onto bus. Self-address framing tests over USB do NOT
  prove transceiver/wiring/physical RS485 transport.
- main_python/hub_usb.py is sole port owner. Use Hub routes for shared commands;
  external ROM tools require usb_close + usb_free confirmation, no concurrent handle.
- firmware/src/core/WebPortal.cpp:1128-1135 refuses HTTP OTA during busy/sequence;
  common FW* path lacks the same busy guard, so test updates only after confirmed STOP/idle.
- GSPIN is test-only and does not touch stock/counters; GDISPENSE reserves stock
  and counts before rotation. Preserve counts; do not use dispense for mapping.
- Native CAD audit proves geometry only; never use it as channel/direction/horn
  calibration. Parent HOME differs from all90; preserve live robot arrays.
- Actual robot INFO module.link=true, peer=85. NongModule.cpp:311-316 forwards
  resolved pose commands over RS485. Before motion, verify partner route or
  temporarily CFG link0 with exact backup/finally restore; do not move an unseen peer.
- Identity::begin defaults NVS type to blank, not gacha. A fresh gacha binary
  needs verified SET TYPE gacha + reboot before its motor controls become active;
  incompatible previous type falls back to blank factory. Preserve existing NVS.

## Next
1. Finish source audit for actual parity gaps; checkpoint before any edits.
2. Wait explicit integration runtime handover, then claim COM9/10, robot and
   gacha flash/motion resources under BRIDGE mutex; no other serial owner.
3. WiFi robot identity already read. Diagnose USB boards via passive boot capture
   after Hub releases each port, then bounded ROM chip/read-only backup if needed.
   Identify actual ESP32/chip/flash and back up before any known-board flash.
   Exact when WINDOW OPEN only (root cwd): python scratch/lab-hardware-1023/passive_uart.py
   --window-open --ports COM9 COM10; then rom_identity.py with same arguments.
   ROM helper leaves loader/stub state; record it in release. Adapt full-flash read
   size only after identified model/size; private backups, never commit binaries.
4. On identified safe gacha use bounded low-speed GSPIN with STOP + Hall proof;
   distinguish hardware board vs dummy. Stop immediately on unexpected behavior.
5. USB/WiFi commands/config/status + firmware updates; RS485 physical route stays
   unproven without wiring. Then actual dispensing only on hardware board.
6. Robot idle/collision/limits check, bounded per-axis moves and safe stop; then
   saved motions/talk/video tests, coordinate camera with Face chat.

## Blocked
- Integration holds runtime gate/build/restart; no physical commands yet.
- USB identity/chip/type/pins/attached hardware not measured; INFO gave no reply.
- RS485 explicitly not wired; dummy cannot prove dispensing or physical bus.

## Coordination
Human authorizes messages to parent 01a16787, integration01a1679e, Face01a1678d,
native audit01a16792 and main coordination01a1689b (full IDs in chat context).
Do not create additional chats. This chat is sole hardware owner; PC camera not
claimed. All real vs simulated evidence kept separate in private scratch.
