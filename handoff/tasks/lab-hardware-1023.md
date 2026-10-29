# Lab: robot and prize ESP32 transport acceptance

Owner: codex:10231420-85cc
Updated: 2569-10-25 15:49 (Bangkok)
Branch: codex/lab-hardware-1023
Tree: E:/final_proj/mice/code/.staging-lab-1023
Last commit: this checkpoint (pause-note baseline70ebb7d)
Plan: A45-11 expanded nong acceptance; historical A47-19/A47-5/A46-2

## Goal and latest scope
Human25Oct explicitly says not ready to test robot (main01a1689b relay).
Actual hardware testing is USER-PAUSED/unavailable until human explicitly says
ready in a later coordinated window. No readiness retries, motion, flash,
calibration, network or service changes. All Lab resources remain RELEASED for
software gates. Preserve newer manualtrim and existing partial evidence.

## Doing now
Record explicit human hardware pause in metadata only; no live request,
process or resource lease remains. No product source edits; baseline70ebb7d.

## Done
25Oct bounded read-only readiness: Hub responds but no nong identity confirmed;
one INFO attempt HTTP502, then no further device requests/downloads. Exact
readiness JSON/Markdown saved. ALL physical/command/testdriver reservations
explicitly released before source gate; A45-11 handoff todo/open with limits.
Later human not-ready instruction recorded; no additional readiness attempt.

## File status
| File | Change | State | Verification | Commit |
|---|---|---|---|---|
| handoff/tasks/lab-hardware-1023.md | Preserve readiness; record explicit human hardware pause | done | metadata diff/line count/root copy checked; no live test | this checkpoint |
| scratch/nong-acceptance-1025/readiness.json | Exact Hub replies/host inventory; failed INFO | done | actual read-only; identity blocked HTTP502; no mutations | uncommitted (private) |
| scratch/nong-acceptance-1025/readiness.md | Readiness and missing-test prerequisites | done | cross-checked against readiness.json; no new functional pass | uncommitted (private) |
| docs/BRIDGE.md | Only own serialized claim/release; others preserved | done | own entries read back; all Lab resources released | uncommitted (shared root metadata) |
| docs/PLAN.html | A45-11 handoff plus human-pause note; other rows preserved | done | plan.py note successful | uncommitted (shared root metadata) |
| docs/plan_state.js | Generated plan publication | done | plan.py published; A45-11 todo/open | uncommitted (shared root metadata) |

## Facts found
readiness.json: Hub5c3513666e8d/stale:false, modules[]/LAN192.168.100.36;
play/flash.running false (flash success log is history, not this test).
Host has no192.168.137.x interface; serial inventory BluetoothCOM3/4/5/7 only.
Oldnong.137.26 INFO502 does not identify power/network/firmware cause. Current
manualtrim/config unread; do not claim unchanged or restore yesterday's values.

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
Source25Oct08:14/08:16 explicitly released softwaredriver; main authorized this
bounded read-only window. Initial driver inventory matching0, source ACK held.
After one failed INFO, process exited0; ALL Lab command/testdriver/physical
reservations explicitly RELEASED in BRIDGE and ACK to main/source. No active
COM/camera/QC/fake/build/timing lease. Release transfers no motion/flash/restart
authority. Existing Hub/services/network untouched. Retain metadata only until
this checkpoint; no root product source edits or other-owner changes claimed.

## Next
1. WAIT for human explicitly ready. Only then coordinate a new hardware window,
   restore an actual route and read fresh identity/current config; preserve trim.
2. A45-11 stays incomplete: physical HOME/axes user-deferred; nong USB/RS485
   absent; broad motion/Studio/RRT/video/RELAX and calibration mutators not run;
   phone mic, OTA/FW update and hotspot outage not independently tested.
3. Gacha source safety candidate (including newer GCALIB/GTEST/GDRAIN) requires
   owner review/gates before any separately coordinated physical acceptance.
4. Main/source may continue software review/gates with resources already released.
   Hardware remains USER-PAUSED; connection appearing alone is not resume consent.
