# PC Face app, watcher and Photobooth integration

Owner: codex:10231359-7280
Updated: 2026-10-23T19:34:30+07:00
Branch: codex/face-pc-1023
Last commit: fb84606 (startup readiness; see git log for latest)
Plan: A45-30; remaining real run A45-14/A45-12

## Goal
Finish all PC-only Face app/watcher/Photobooth work without editing friend's sources.
Coordinate results with parent codex:10231353-0401, which owns URDF/QC/build/restart.

## Doing now
Integration explicitly released newHub built19:25 ef590e60cbff/stale:false and startup scope.
Lab fresh agreement allows NoBrowser health; rawUSB window RELEASE19:34 verified.
Own Photobooth8121/8123 startup lease now; run official stop-main then run-main -NoBrowser,
record normal script output + health/HTML + original service PIDs. No camera/inference/COM/
hardware/Hub restart/DB migration/QC. Leave successful booth service running, release afterward.

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
- Actual hub /app/photobooth/200 (1768bytes); its health probe returns up:false,
  correctly matching stopped Main. Partner entry matches the installed Main folder.
- Hub partner-start route uses official stop-main then run-main and browser pairing.
  Prefer this end-to-end check after resource release; no source change/rebuild needed.
- PID40156 is absent. Official stop-main can discard its matching dead record.
- Protected baseline: Face e8d4a22 has 3 existing dirty entries; All-Jao f9e8ff4,
  Photobooth858f0b6 and installed booth41561e3 are clean. Preserve those existing edits.
- Latest user is at lab and explicitly authorizes real robot/prize ESP32 testing.
  Sole hardware owner is chat 01a167a0-2a75-7c93-89ea-81df71a29ff4.
  Old no-robot-at-lab assumption is superseded; actual readiness/results come from that owner.
- Hardware owner reports inventory-only: no camera/COM/motion lease and no serial COM
  detected yet. It permits NoBrowser health smoke after integration runtime release;
  camera use still needs coordination before its video acceptance phase.
- Later hardware BRIDGE19:01 identifies CP210x COM9/COM10, still unidentified boards;
  RS485 is not connected. Only hardware owner may identify/move/flash them.
- Main status recipient 01a1689b-5608-7123-b8c2-a6f489b5b675 is human-authorized.
  Deployment now belongs to 01a1679e-50a4-7e71-9cfb-64b6afa635c1 after original
  owner explicit RELEASE19:00. Final exact gate7910/0+925stable accepted, PR77 merged
  a884558, specbuild0 and new executable installed; oldHub stopped19:27 idle.
  Lab rawUSB identity/backup window RELEASE19:34; integration starts newHub next.
- Passive resume health: friend8000 HTTP200/model_ready, watcher8769 HTTP200/
  watching/error empty, booth8121 connection refused. No new recognition request added.
- BoothStartPage.tsx:10/35 opens frames before capture; camera.open occurs only
  in CapturePage.tsx:171. Health/HTML probes do not start a photo session or camera.

## Done
- Read AGENTS/HANDOFF/CLAUDE, coordination, relevant task files and app-faces header.
- Claimed only this handoff plus private scratch; A45-30 added under shared mutex.
- Parent informed that exclusive resources remain theirs.
- Private evidence in scratch/face-photobooth-pc-1023/: OpenAPI, watcher health/state,
  passive observation, protected baseline, stale PID record and hub routes.
- No source edits, inference, QC, service changes, capture or hardware commands.

## Next
1. Hold startup until parent QC RELEASE plus deployment completion, then agree camera
   window with sole hardware owner. Never restart hub during flash/motion/video tests.
2. After recording own startup lease, recheck ports8121/8123 and dead PID identity.
   Prefer official stop-main then run-main -NoBrowser while hardware tests use camera;
   poll health8121 with a time limit. Full hub launch auto-opens browser pairing, so defer
   that step until hardware owner confirms no camera/video conflict.
   Check booth/admin read-only pages and hub health up:true; record PID, leave it running.
   Preserve friend8000/web5173/watcher8769/Voice and all event data.
   If schema revision refuses startup, report it to friend; never migrate here.
   Do not start TV camera/photo session while hub owns the PC camera.
3. Return exact checklist delta to parent; no direct lab-day.md/friend-face-server.md edits.
4. Friend must add booth name connector before simultaneous names can be measured.
5. CLI-only continuation reads this file and live BRIDGE. Codex native chat/handoff
   tools are not assumed available in Gemini CLI. Record a BRIDGE REQUEST under mutex
   for missing lease/coordination; do independent read-only work, never infer release.

## Blocked
- Startup smoke waits for QC/deployment and hardware-owner camera coordination.
- Friend: booth Reconize adapter/name display is absent, not a hardware blocker.
- Friend: booth TV only takes a physical camera index; shared hub stream unsupported.
- Robot/prize ESP32 tests are now authorized at lab; hardware owner must confirm readiness.
  Enrolled-person camera-to-name still unmeasured; do not substitute unknown-face timing.

## Other open work; do not silently close
- A45-10: user's Google AI Studio/Groq sign-in + keys; provider order stays until keys work.
- A45-12/A45-18/A45-25: enrolled person camera arrival, real mic Thai3/5-10s,
  room echo/robot speaker and human listening to emotion/voice samples.
- A47-5: prize ESP32 now at lab/authorized; sole hardware owner handles inventory,
  flash, motor/hall/magnets, drop/speed/jam and real dispense; no result yet from this chat.
- A45-11/A46-2/A26-99/A26-77: nong now authorized at lab; hardware owner checks manny/COM;
  palm/last.yaml/OTA/TALK/video sound, motion/RRT/video/skeleton, PERF and legacy bench list.
- A48-6/A26-71/A26-92/A16-1: robot home+3poses/CAD, shrug calibration,
  RELAX diagnose-only, ruler measurement of four-bar curve. Parent owns URDF axis work.
- A20-3: two ESP32 boards + RS485 pair. A7-8/A24-10: lift board/RGB/speaker,
  no-encoder limit-switch UP/DOWN and GOTO bottom/top only.
- A13-8: phone WiFi OTA; A13-4: second PC same WiFi; optional A9-2/3: TV at3m/remote.
- Friend: docs/gacha/friend_requests.md game events/player IDs/tags remain optional asks.
- A31-11/A0-33: user's tool settings. Thesis A26-73/A21-17/A31-32 dropped; no thesis work.
- A47-18 gacha PC acceptance returned from codex:10231359-8856 to parent for deployment.
