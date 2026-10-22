# Real robot hotspot demonstration

Owner: codex:10221724-9d65
Updated: 2026-10-22T17:36:15.352600+07:00
Branch: task/A46-2-10221724-9d65
Last commit: 2485fe7 (WiFi-late test checkpoint follows)
Plan: A46-2

## Goal
Test saved motions, speech gestures/RRT, video copying and skeleton visibly on the real robot over the existing PC hotspot. Preserve original projects/calibration.

## Done
- Deployed software runtime already full QC7547/0, live voice replay50/50 after model readiness.
- User explicitly authorizes real robot playback in this request.
- Opened visible Studio in user browser. Existing unsaved31-keyframe project must be preserved.
- No robot motion sent. Hub modules empty, no hotspot interface in initial inventory.

## Doing now
Resumed A46-2 for independent non-UI WiFi-late test after user asks actual proof.
Browser URL-policy stop remains respected; no further browser input.
Robot67 chip/B4BFE91C5A74 at192.168.137.66 and hub both idle; all joints at
configured neutral. Existing hotspot manny On. Real PERF before: boots1,
up_s1365. Plan: authenticated REBOOT (source default800ms), stop existing
hotspot through official Windows tethering API, hold80s, restore hotspot,
measure actual rejoin up to140s. Record reboot counter, uptime-derived boot
interval and off timestamp to distinguish proven cold boot from ordinary rejoin.
Always restore hotspot in finally; no pose, credentials, calibration or firmware changes.
Private runner root scratch/robot-hotspot-2026-10-22/wifi-late-test.py;
result wifi-late-result.json, console wifi-late.log. No run started before checkpoint.

## Next
1. Restore allowed actual-browser control after runtime policy stop; do not bypass browser security. Log in with verified admin/admin123; actual hotspot connection already works.
2. Preserve browser work in a uniquely named copy; show video/skeleton beside robot.
3. Fit gestures to actual rig, validate paths/limits then small real move and stop proof. Expand to all valid saved poses/moves and video/talking tests; record failed/skipped cases honestly.
4. Checkpoint and push each meaningful step. Do not modify calibration, pins or firmware. Physical setup/user input only if read-only diagnostics establish it is missing.

## Blocked
- Native browser control stopped for URL-confidence enforcement. Real playback/video/skeleton/RRT/fit/reconnect tests pending; no physical motion measured. RS485/USB failover also requires cable/COM21.
