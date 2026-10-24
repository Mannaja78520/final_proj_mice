# Lab: robot and prize ESP32 transport acceptance

Owner: codex:10231420-85cc
Updated: 2026-10-24 22:17 (Bangkok)
Branch: codex/lab-hardware-1023
Tree: E:/final_proj/mice/code/.staging-lab-1023
Last commit: 0b19c02 before closing evidence checkpoint; closing commit at branch HEAD
Plan: A45-11 expanded nong acceptance; historical A47-19/A47-5/A46-2

## Goal and latest scope
User authorized actual nong/gacha testing with default module wiring; RS485 is
NOT connected. Main chat 01a1689b coordinates; source chat 01a1679e owns gacha
safety fixes. Latest main instruction 24Oct22:xx: close nong evidence metadata
only, inspect active drivers and release QC/build resources; no new physical,
trim, motion, OTA, restart or live fixture operation unless exact owned cleanup
is demonstrably necessary. Current evidence already records cleanup complete.

## Current checkpoint
32-command plus 19-feature matrix reconciled against saved SD/audio/TALK logs
and direct human hearing confirmation. Markdown/JSON/CSV agree, all referenced
evidence files exist; no pending owned cleanup. Full acceptance stays incomplete.
No hardware request, raw COM handle, test child, QC or build is in flight here.
Matrix: scratch/nong-acceptance-1024/nong-acceptance-matrix.{md,json}; command
details: nong-command-acceptance.csv. Private wire logs retained, not committed.

## Actual last device state (historical snapshot, not a fresh live poll)
web-talk-test.json final INFO: nong67/chipB4BFE91C5A74 at WiFi192.168.137.26;
moving=false, seq.running=false, attached=true, audio.playing=false,
stream.on=false, volume=70; TALK? off. Commanded joints/targets:
[90,140,90,90,90,40,90,90,90,90.5]. These are NOT measured physical angles.
Both gacha85/125 last independently recorded idle after STOP in
restore-and-known-hardware-stop.json. No fresh post-gap state claim.

## Elbow diagnosis: USER DEFERRED, not passed
User saw right elbow back/outward despite reported HOME. Two bounded R_EL_P
90->91.5 probes (T3000 and T5000) changed only internal index6. Human could not
distinguish physical movement/direction. Restored R_EL_P90 T2000 plus STOP in
repeat-restore90-before5deg.json, before later non-arm tests. Proposed95 was
NEVER sent. No second axis, HOME/all90, RELAX, trim, neutral or CAL setter.
User canceled diagnosis and will adjust trim manually: preserve newer manual
settings, never restore old calibration automatically. No further arm tests.
PC camera frame showed room/people, no robot; no geometry evidence.

## Independent 24Oct results
Evidence root: E:/final_proj/mice/code/scratch/nong-acceptance-1024.
- Identity/INFO/POSE/limits/gear/pulse/range/frame/offset/CAL queries recorded.
  Board SD module.yaml17bytes and nong_cal.yaml602bytes downloaded read-only.
  INFO lacks invert; CAL saved flag is not a complete NVS blob readback.
  NEUTRAL?/LIMIT? round SHRUG90 while INFO retains90.5; do not change neutral.
- SD unique /moves/lab_wait_only_20261024_0bbd3405.yaml contains waits only.
  FBEGIN/FDATA/FEND, exact FREAD and HTTP download match; 2.5sec wait sequence
  naturally completed (host observed2.75sec), MOVE STOP and STOP cancellation
  passed. Exact fixture content verified before FDEL; deletion ACK recorded.
  No servo steps. sd-wait-only-test.json has all five checks true and cleanup.
- Existing test_tone.wav: mono16bit22050Hz,3sec. PLAY observed active then natural
  end; PLAY STOP ACK. VOL20 verified then original70 restored/verified.
- Actual UDP4210/22050Hz sent50datagrams, device counted50/dropped0; underruns1,
  pads5/max_gap9ms sampled after sender ended. Do not call perfect streaming.
  STREAM TEST3sec active then off; final PLAY STOP/STREAM OFF ACK.
- User answered this chat: "ได้ยินชัดเจน" (heard clearly). This confirms speaker
  sound for the combined short test; not separate subjective proof per route.
  Full transcript audio-stream-test.json; human feedback also web-talk-test.json.
- Direct module /, /api/status, /api/files?dir=/moves all HTTP200 with identity.
  TALK ON -> active -> local HTTPS /talk200 -> TALK OFF -> off. AMP VALID7types;
  FWSTAT idle. No real phone microphone/permissions or post-reboot TALK test.
  Optional WebSocket read not run: local websocket-client missing; not a device
  failure. web-talk-test.json; HTML saved privately alongside logs.
- PERF is an accumulated counter window, not controlled physical timing proof.

## Historical 23Oct and Gemini claims
Own ROM identity confirmed COM9 MAC3076F593B454 and COM10 MACECC9FFFE387C,
ESP32-D0WD-V3 rev3.1,4MB each. Both now gacha85/125; neither proves nong USB.
Whole-chip backup reads failed; user questioned4MB. No more whole-chip loops.
Own reviewed gacha USB flash/provision on COM9 succeeded via sole Hub flasher;
standard writes preserved NVS (no erase-all). Firmware SHA256:
36c6d1d1364f7ff7567c371b6bf33a178f7ac7a2d89f6246ac81815d215172e4.
Gemini later reported COM10 flash/OTA, motor/Hall, GDISPENSE514/972ms, palm/waist/
shrug/show tests. These are inherited claims under main/source audit, not this
chat's independent physical observation. Device completion does not prove a
capsule dropped. Old logs predate newer5sec pause FSM. Quick QC is not full QC.
Reviewed deployed Hub ef590e60cbff came from PR77/a884558 full7910/0 with925
stable source inputs; later dirty Gemini gacha features are not covered by it.

## Coordination and resources
Lab sole physical claim resumed15:16; Gemini conflict resolved by explicit
freeze/release15:38 (historical; later root edits are source owner's audit).
22:12 read-only Windows inventory found no matching QC/native/PlatformIO/
esptool/fake/pocket-loop/nong-acceptance children. This is an inventory snapshot,
not proof against an unseen future actor. Normal services were not stopped.
RELEASED QC/fake/native-build/timing-driver exclusion to source01a1679e in
serialized BRIDGE22:12; ACK sent to source/main. Physical remains reserved/stopped;
this release does NOT authorize flash, motion, live commands or service restart.
No PC camera lease. Hub remains sole normal COM owner. No root source edits.

## Remaining limits / next
1. Metadata checkpoint finished; A45-11 handed back todo/open with exact limits
   and next coordination step via tools/plan.py. Closing commit shared with main/source.
2. A45-11 stays incomplete: physical HOME/axes user-deferred; nong USB/RS485
   absent; broad motion/Studio/RRT/video/RELAX and calibration mutators not run;
   phone mic, OTA/FW update and hotspot outage not independently tested.
3. Gacha source safety candidate (including newer GCALIB/GTEST/GDRAIN) requires
   owner review/gates before any separately coordinated physical acceptance.
4. No automatic hardware continuation. New physical work needs coordinated
   ownership; preserve user's manual trim and existing SD/calibration files.
