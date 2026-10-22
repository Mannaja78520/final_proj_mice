# Real robot hotspot demonstration

Owner: codex:10221724-9d65
Updated: 2026-10-22 17:25 Asia/Bangkok
Branch: task/A46-2-10221724-9d65
Last commit: 8fc410f
Plan: A46-2

## Goal
Test saved motions, speech gestures/RRT, video copying and skeleton visibly on the real robot over the existing PC hotspot. Preserve original projects/calibration.

## Done
- Deployed software runtime already full QC7547/0, live voice replay50/50 after model readiness.
- User explicitly authorizes real robot playback in this request.
- Opened visible Studio in user browser. Existing unsaved31-keyframe project must be preserved.
- No robot motion sent. Hub modules empty, no hotspot interface in initial inventory.

## Doing now
Read-only hotspot and module discovery; enable existing configured hotspot without changing credentials. PowerShell7 lacks WinRT types; use Windows PowerShell5.1 for OS tethering API. Establish actual WiFi device route and calibrated pose before motion.

## Next
1. Connect robot via hotspot; inspect live info/pose and telemetry.
2. Preserve browser work in a uniquely named copy; show video/skeleton beside robot.
3. Fit gestures to actual rig, validate paths/limits then small real move and stop proof. Expand to all valid saved poses/moves and video/talking tests; record failed/skipped cases honestly.
4. Checkpoint and push each meaningful step. Do not modify calibration, pins or firmware. Physical setup/user input only if read-only diagnostics establish it is missing.

## Blocked
- Connection not established yet; no physical test has run.
