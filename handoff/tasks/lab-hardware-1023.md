# Lab: robot and prize ESP32 transport acceptance

Owner: codex:10231420-85cc (resumed by human24Oct)
Updated: 2026-10-24 15:18 (Bangkok)
Branch: codex/lab-hardware-1023
Tree: E:/final_proj/mice/code
Last commit: checkpoint hardware results
Plan: A47-19 (combined), A47-5, A45-11, A46-2; native audit A48-12

## Goal
User at lab authorizes robot motion, gacha testing, one hardware gacha plus
another ESP32/dummy over USB, equal commands/config/status over USB/WiFi/RS485
and firmware updates over those routes. Verify inventory before assumptions.
Latest direct clarification: same board/default wiring as existing module;
RS485 currently NOT wired. User authorizes bounded motor/Hall identification.

## Inherited Gemini summary (claims awaiting evidence audit)
- **Gacha 1 on COM9 (ID 85)**:
  - 4-phase safety agitation and dead-center Hall stopping (`SETTLE_ROCK_FWD`, `SETTLE_ROCK_BACK`, `SETTLE_CENTER`, `SETTLE_PAUSE` 5000ms).
  - Flashed `mice_gacha` to COM9 (chip MAC `3076F593B454`).
  - Motor and GPIO33 Hall sensor verified via `GSPIN 1 MAG` (hits incremented accurately per magnet).
  - Real dispensing verified: `GDISPENSE test-lab` completed in 514 ms over USB (`seq=1`, `given=1`). `GDISPENSE wifi-test` completed in 972 ms over WiFi `192.168.137.148` (`seq=2`, `given=2`).
- **Gacha 2 on COM10 (ID 125, IP 192.168.137.139)**:
  - Flashed `mice_gacha` via Hub in 20.5 s (chip MAC `ECC9FFFE387C`).
  - Configured as `gacha-2`, WiFi successfully joined hotspot `manny` at IP `192.168.137.139`.
  - USB vs WiFi parity verified (`GCFG drop 1`).
  - WiFi OTA firmware update verified (1.34 MB uploaded, HTTP 200 OK, rebooted cleanly).
- **Robot Nong on WiFi 192.168.137.26 (ID 67)**:
  - Servos neutral verified: `[90, 140, 90, 90, 90, 40, 90, 90, 90, 90.5]`.
  - Bounded moves verified on `WAIST` (90 -> 93 -> 90), `SHRUG` (90.5 -> 85 -> 95 -> 90.5), and both elbow rolls / palm flips (`L_EL_R` / `R_EL_R` joints 4 & 8: 90 -> 95 -> 90).
  - Speaker audio verified: `PLAY test_tone.wav` played on speaker and stopped cleanly.
  - Show playback & PERF? verified: `MOVE LhongMarePing.show.yaml` started, `PERF?` sampled (`loop_avg_us=2010`, `work_max_us=99856`, `passes=56170`, `heap=146816`), stopped cleanly and returned home.
  - A26-92 RELAX diagnosis: `NongModule.cpp` `RELAX` drives GPIOs to `OUTPUT LOW`; digital servos like TD8135MG with internal MCUs require high-Z / float or power-cut to go limp.
- **Photobooth & Face server**:
  - CUDA Dual inference active (13-14 ms compute).
  - MiceHub 8642 (`ef590e60cbff`), Face backend 8000 (CUDA dual mode), Watcher 8769, Voice 8767, Photobooth 8121/8123 and Hub apps (`/app/gacha/`, `/app/all-jao/`, `/app/photobooth/`) verified running and healthy.

## Doing now
Broad motion/OTA paused: human observes RIGHT elbow slightly back/outward despite
controller reporting HOME. STOP/MOVE STOP/PLAY STOP all ACK; attached hold remains.
Human confirms watcher + arms clear. Main explicitly authorizes only narrow
right-elbow diagnosis DONE: JOINT R_EL_P 91.5 T3000 ACK, controller completed in3s,
onlyindex6 changed. CURRENT HELD [90,140,90,90,90,40,91.5,90,90,90.5], attached,
movingfalse. Physical direction/center feedback PENDING async question in thischat.
ReturnR_EL_P90 slowly before nextaxis only afterfeedback; no persistentwrites.

## Prior Gemini recorded work (audit pending)
- Flashed mice_gacha to COM9 (id 85) and blank COM10 (id 125, gacha-2).
- COM9 (Dispenser): GSPIN 1 MAG verified motor and GPIO33 Hall sensor (hits incremented accurately per magnet).
- COM9 real dispensing: GDISPENSE test-lab completed in 514 ms over USB (seq=1, given=1). GDISPENSE wifi-test completed in 972 ms over WiFi 192.168.137.148 (seq=2, given=2).
- COM10 (Second Gacha Machine): Flashed via Hub in 20.5 s, configured as gacha-2, joined hotspot manny at 192.168.137.139. USB vs WiFi parity verified (GCFG drop 1). WiFi OTA firmware update verified (1.34 MB uploaded, 200 OK, rebooted cleanly).
- Robot 67 (WiFi 192.168.137.26): Neutral joints verified [90, 140, 90, 90, 90, 40, 90, 90, 90, 90.5]. Small bounded motions verified on WAIST (90->93->90), SHRUG (90.5->85->95->90.5), and both elbow rolls / palm flips (joints 4 & 8: 90->95->90).
- Robot audio: PLAY test_tone.wav verified on speaker and stopped cleanly.
- Robot show & PERF: MOVE LhongMarePing.show.yaml started, PERF? sampled (loop_avg_us=2010, work_max_us=99856, passes=56170, heap=146816), stopped cleanly and returned home.
- A26-92 diagnosed: NongModule.cpp RELAX drives GPIOs to OUTPUT LOW; digital servos like TD8135MG with internal MCUs require high-Z / float or power-cut to go limp.
- Read AGENTS/HANDOFF/CLAUDE/COORDINATION, named lab handoffs, firmware rules, fw-gacha/fw-core/hub-flash/app-gacha headers and project contract/verification skills.
- Windows PnP inventory and Hub routes verified.
- Raw actual ROM ID succeeded: COM9 ESP32-D0WD-V3 rev3.1 / MAC 3076F593B454, flash 4MB manufacturer 5e/device 4016; COM10 same chip / MAC ECC9FFFE387C, 4MB / a1 / 4016.
- QC quick suite green, system documentation verified (`python code/tools/systems.py verify`).

## Facts found
- Fresh24Oct INFO/POSE/NEUTRAL values match prior command state, NOT physical
  angle feedback. INFO neutral SHRUG90.5 while text NEUTRAL?/LIMIT? rounds90.
- Fresh OFFSET all0; CAL chip=saved/sd=yes; gear/pulse/range/frame queries saved.
  Board SD configs read only to scratch/nong-acceptance-1024/sd-before; module.yaml
  17bytes, nong_cal.yaml602bytes. Existing CFG safe_dps190 only. No edits.
- Current exact evidence: scratch/nong-acceptance-1024/{nong-readonly-preflight,
  nong-calibration-sd-queries,physical-home-stop,sd-config-read-manifest}.json.
- Stop transcript15:22: INFO before/after movingfalse/attachedtrue/seqfalse/
  audiofalse; joints=target[90,140,90,90,90,40,90,90,90,90.5]. No HOME/RELAX.
- First narrow probe: right-elbow-pitch-diagnostic.json records fulltranscript,
  JOINT R_EL_P91.5T3000 + time-series INFO. Only commanded state verified;
  no encoder/physicalanglefeedback. Humanhasnotansweredobserveddirectionyet.
- Root source audit flags unsafe gacha centering timeout bypass. No further
  gacha motion/dispense tests allowed during this nong diagnostic.
- firmware/config/esp32_hardware_gacha_module.h:17-32: motor 25/26, optional EN=-1, Hall 33 active-low, magnets 4 / slots 4 / drop 2, PWM 600, timeout 4000ms, settle 0.
- 4-phase safety agitation and dead-center Hall stopping: `SETTLE_ROCK_FWD`, `SETTLE_ROCK_BACK`, `SETTLE_CENTER`, `SETTLE_PAUSE` 5000ms.
- firmware/config/esp32_hardware.h:30-33: shared RS485 RX16/TX17/DE4 at 115200.
- firmware/src/main.cpp:151-162: direct USB lines call router.handle; #id lines use rs485.bridge. Gacha verbs use the same router as WiFi/RS485.
- firmware/src/core/CommandRouter.cpp:596-617: FWBEGIN/FWDATA/FWEND/FWABORT/FWSTAT are common commands (application spare-slot update), not USB ROM flashing.
- firmware/COMMANDS.md:207-246: USB esptool, WiFi HTTP OTA, any-channel FW*; bus chunks <=150 bytes with sequence/decoded length + final MD5.
- main_python/hub_flash.py:59-66,90-98: image env derives dynamically from module registry (mice_gacha); no separate gacha updater required by design.
- main_python/hub_usb.py is sole port owner.
- GSPIN is test-only and does not touch stock/counters; GDISPENSE reserves stock and counts before rotation. Preserve counts.
- Robot INFO module.link=true, peer=85. NongModule.cpp:311-316 forwards resolved pose commands over RS485.

## Next
1. Fresh identity/idle/calibration/limits snapshot; build full nong feature matrix.
2. Test safe queries, then bounded motion/stop/SD/audio/show routes that are ready.
3. Label controller reports vs physical observation separately; no source/QC or
   service restart without coordination. Record blocked transports/phone/camera.

## Blocked
- Fresh audit in progress; do not inherit all-tested declaration.
- No nong USB/RS485 route currently discovered; both USB boards are gacha.

## Coordination
Previous Gemini hardware release remains historical. This chat reacquired sole nong hardware claim24Oct15:16; no PC camera lease yet.
