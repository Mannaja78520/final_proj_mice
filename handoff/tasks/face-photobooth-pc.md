# PC Face app, watcher and Photobooth integration

Owner: codex:10231359-7280
Updated: 2026-10-23T14:04:35.748731+07:00
Branch: codex/face-pc-1023
Last commit: 7298ab4 (inspection-start checkpoint; see git log for latest)
Plan: A45-30; remaining real run A45-14/A45-12

## Goal
Finish all PC-only Face app/watcher/Photobooth work without editing friend's sources.
Coordinate results with parent codex:10231353-0401, which owns URDF/QC/build/restart.

## Doing now
Prepare official Photobooth startup + health/hub-page smoke after parent QC release.
No extra four-source benchmark: it was already done and the booth connector is absent.

## Facts found
- HANDOFF.md: friend sources outside code are read-only/start-only; no edits allowed.
- apps/faces/service.py belongs to app-faces; its system header has been read.
- Live baseline: friend 8000 PID11376, web5173 PID49656, watcher8769 PID38676,
  hub8642 PID33336 and Voice8767 PID29020 are listening.
- Source branch is HEAD-only for task metadata; dirty main runtime is not assumed equal.

- C:/Photobooth/Main/app container.py:1068 instantiates AllowAllEligibility;
  modules/eligibility/domain.py:3 says Reconize integration is a later phase.
  The E:/final_proj/mice/Photobooth copy has the same gap; its 858f0b6 is remote HEAD.
- Installed Main 41561e3; scripts/run-main.ps1 refuses stale PID records and never
  migrates at start. data/run/main-processes.json still records Oct4 PID40156.
- Screen opencv.py:102 opens physical camera directly, no hub relay input found.
  Saved camera index=1; shared-camera conflict remains unmeasured, not assumed proven.
- Passive watcher observation: 12 samples / 6.8s, +23 frames, 1 unknown / 0 named;
  latest inference37.8ms, no poll/runtime error. This is NOT camera-to-name latency.
- friend /api/health: model_ready true, dual/CUDA live+background, queues0.
- friend OpenAPI /api/look is stateless. /recognize-central defaults persist=true;
  do not use it for testing real event data. No inference request added here.

## Done
- Read AGENTS/HANDOFF/CLAUDE, coordination, relevant task files and app-faces header.
- Claimed only this handoff plus private scratch; A45-30 added under shared mutex.
- Parent informed that exclusive resources remain theirs.

## Next
1. Parent explicitly says hold startup until QC RELEASE in BRIDGE (~full gate pending).
2. Then official stop-main.ps1 (stale record cleanup), run-main.ps1 -NoBrowser,
   health8121, hub Photobooth entry/read-only pages; preserve original services/data.
3. Return exact checklist delta to parent; no direct lab-day.md/friend-face-server.md edits.
4. Friend must add booth name connector before simultaneous names can be measured.

## Blocked
- Startup/runtime smoke waits for explicit parent resource release; no QC run here.
- Friend: booth Reconize adapter/name display is absent, not a hardware blocker.
- Friend: booth TV only takes a physical camera index; shared hub stream unsupported.
- Real robot source and enrolled-person camera-to-name measurement require robot/person.

## Other open work; do not silently close
- A45-10: user's Google AI Studio/Groq sign-in + keys; provider order stays until keys work.
- A45-12/A45-18/A45-25: enrolled person camera arrival, real mic Thai3/5-10s,
  room echo/robot speaker and human listening to emotion/voice samples.
- A47-5: gacha board/motor/hall sensor + magnets, flash, drop/speed/jam and real dispense.
- A45-11/A46-2/A26-99/A26-77: real nong, hotspot manny, COM21/RS485;
  palm/last.yaml/OTA/TALK/video sound, motion/RRT/video/skeleton, PERF and legacy bench list.
- A48-6/A26-71/A26-92/A16-1: robot home+3poses/CAD, shrug calibration,
  RELAX diagnose-only, ruler measurement of four-bar curve. Parent owns URDF axis work.
- A20-3: two ESP32 boards + RS485 pair. A7-8/A24-10: lift board/RGB/speaker,
  no-encoder limit-switch UP/DOWN and GOTO bottom/top only.
- A13-8: phone WiFi OTA; A13-4: second PC same WiFi; optional A9-2/3: TV at3m/remote.
- Friend: docs/gacha/friend_requests.md game events/player IDs/tags remain optional asks.
- A31-11/A0-33: user's tool settings. Thesis A26-73/A21-17/A31-32 dropped; no thesis work.
- A47 gacha PC acceptance lives with codex:10231359-8856, not a hardware-only wait.
