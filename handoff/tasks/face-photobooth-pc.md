# PC Face app, watcher and Photobooth integration

Owner: codex:10231359-7280
Updated: 2026-10-24T15:29:03+07:00
Branch: codex/face-pc-1023
Last commit: 7358450 (startup result plus frame request; see git log for final)
Plan: A45-30; remaining real run A45-14/A45-12

## Goal
Finish all PC-only Face app/watcher/Photobooth work without editing friend's sources.
Report to integration codex:10231901-f6cc and main coordinator; Lab alone owns hardware.

## Doing now
24Oct one actual existing PC frame delivered to Lab; no robot/elbow visible.
Camera-read HTTP closed and lease RELEASED; original Hub/watcher capture unchanged.
23Oct PC startup complete and startup lease RELEASED; booth left normally running.
No runtime/camera/COM/QC/hardware resources held; finish own metadata checkpoint only.

## Facts found
- HANDOFF.md: friend sources outside code are read-only/start-only; no edits allowed.
- apps/faces/service.py belongs to app-faces; its system header has been read.
- Initial23Oct baseline: friend8000 PID11376, web5173 PID49656, watcher8769 PID38676,
  hub8642 PID33336 and Voice8767 PID29020 are listening.
- Source branch is HEAD-only for task metadata; dirty main runtime is not assumed equal.

- Inspected23Oct C:/Photobooth/Main/app container.py:1068 uses AllowAllEligibility;
  modules/eligibility/domain.py:3 says Reconize integration is a later phase.
  The E:/final_proj/mice/Photobooth copy has the same gap; its 858f0b6 is remote HEAD.
- Installed Main 41561e3; scripts/run-main.ps1 refuses stale PID records and never
  migrates at start. Official stop script removed dead Oct4 PID40156 record safely.
- Screen opencv.py:102 opens physical camera directly, no hub relay input found.
  Saved camera index=1; shared-camera conflict remains unmeasured, not assumed proven.
- Passive watcher observation: 12 samples / 6.8s, +23 frames, 1 unknown / 0 named;
  latest inference37.8ms, no poll/runtime error. This is NOT camera-to-name latency.
- friend /api/health: model_ready true, dual/CUDA live+background, queues0.
- friend OpenAPI /api/look is stateless. /recognize-central defaults persist=true;
  do not use it for testing real event data. No inference request added here.
- Actual hub /app/photobooth/200 (1768bytes); after startup its health probe up:true.
  Partner entry matches installed Main folder; full hub launch still auto-pairs a browser.
- Hub partner-start route uses official stop-main then run-main and browser pairing.
  Prefer this end-to-end check after resource release; no source change/rebuild needed.
- PID40156 is absent. Official stop-main can discard its matching dead record.
- Protected baseline: Face e8d4a22 has 3 existing dirty entries; All-Jao f9e8ff4,
  Photobooth858f0b6 and installed booth41561e3 are clean. Preserve those existing edits.
- Latest user is at lab and explicitly authorizes real robot/prize ESP32 testing.
  Sole hardware owner is chat 01a167a0-2a75-7c93-89ea-81df71a29ff4.
  Old no-robot-at-lab assumption is superseded; actual readiness/results come from that owner.
- Lab fresh NoBrowser agreement and USB RELEASE19:34 received; sole hardware owner
  keeps camera/video coordination, board identity/motion/flash and all physical tests.
- Main status recipient 01a1689b-5608-7123-b8c2-a6f489b5b675 is human-authorized.
  Deployment now belongs to 01a1679e-50a4-7e71-9cfb-64b6afa635c1 after original
  owner explicit RELEASE19:00. Final exact gate7910/0+925stable accepted, PR77 merged
  a884558, specbuild0 and new executable installed; oldHub stopped19:27 idle.
  Lab rawUSB identity/backup window RELEASE19:34; newHub accepted built19:25/stale:false.
- Before/after startup PIDs unchanged: Hub10448, friend11376, web49656, watcher38676,
  Voice2932. Friend model_ready and watcher watching/error empty both HTTP200.
- BoothStartPage.tsx:10/35 opens frames before capture; camera.open occurs only
  in CapturePage.tsx:171. Health/HTML probes do not start a photo session or camera.

## Done
- Read AGENTS/HANDOFF/CLAUDE, coordination, relevant task files and app-faces header.
- Claimed only this handoff plus private scratch; A45-30 added under shared mutex.
- Parent informed that exclusive resources remain theirs.
- Private evidence in scratch/face-photobooth-pc-1023/: OpenAPI, watcher health/state,
  passive observation, protected baseline, stale PID record and hub routes.
- Read-only preparation added no source edits/inference/QC/capture/hardware commands.
  The one later service action was the explicitly authorized official NoBrowser startup.
- 19:38 official stop-main exit0 then run-main -NoBrowser exit0; DB-check current=head
  0012_policy_per_event, no migration. No browser/pairing/capture/session opened.
- Booth wrapperPID47508/actual listener46504;8121 loopback +8123 LAN active.
  Kiosk /api/health200 {status:ok,instance:main,database:ok}; delivery health404 expected
  because main.py:132-147 mounts only /d delivery routes on the guest listener.
- Root/booth/admin HTML200; JS542427bytes and CSS75622bytes200, SHA matches installed
  frontend/dist assets. Hub page200 + partner health up:true. Installed git remains clean.
- Evidence scratch/face-photobooth-pc-1023/{before-startup,startup-smoke}.json;
  all existing listener PIDs preserved. This proves PC service/HTTP only, not visible UI,
  real camera-name latency, robot recognition or simultaneous Photobooth names.
- 24Oct15:27:39 one actual PC firstJPEG640x360/23989bytes/516ms; private
  scratch/face-photobooth-pc-1023/elbow-frame-1024.jpg plus .json, verified gitignored.
  Existing ffmpeg32872/Hub10448 unchanged, HTTP closed; no new capture/inference.
  View shows desks/windows/people, no robot/elbow; cannot judge right elbow angle.
  Lab received path/result; bounded read lease explicitly RELEASED in BRIDGE.

## Next
1. Leave successful booth service running; no Hub restart during Lab flash/motion/video.
   Existing camera points elsewhere; Lab owner handles any human camera/robot view request.
2. Friend must add configurable Reconize name adapter/display and shared-stream input.
   Never edit friend's code here. After friend ships it, agree camera/person window with
   sole Lab owner, pair actual browser with official run-main -PairOnly if needed, then
   time actual Face app/watcher/Photobooth names. Never reuse stateless32/32 as that proof.
3. Parent applies checklist delta; lab-day.md/friend-face-server.md not edited/claimed here.
4. CLI-only continuation reads this file and live BRIDGE. Codex native chat/handoff
   tools are not assumed available in Gemini CLI. Record a BRIDGE REQUEST under mutex
   for missing lease/coordination; do independent read-only work, never infer release.

## Blocked
- PC startup smoke complete; full simultaneous names remains friend/person blocked.
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
