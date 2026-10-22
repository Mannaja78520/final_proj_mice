# Real robot hotspot demonstration

Owner: codex:10221724-9d65
Updated: 2026-10-22T17:36:15.352600+07:00
Branch: task/A46-2-10221724-9d65
Last commit: 5eea2a2 (runtime-stop checkpoint follows)
Plan: A46-2

## Goal
Test saved motions, speech gestures/RRT, video copying and skeleton visibly on the real robot over the existing PC hotspot. Preserve original projects/calibration.

## Done
- Deployed software runtime already full QC7547/0, live voice replay50/50 after model readiness.
- User explicitly authorizes real robot playback in this request.
- Opened visible Studio in user browser. Existing unsaved31-keyframe project must be preserved.
- No robot motion sent. Hub modules empty, no hotspot interface in initial inventory.

## Doing now
STOPPED by native computer-use runtime URL-confidence policy on Chrome Return navigation action. Exact error: could not determine the current browser URL on Windows with enough confidence to enforce policy. No further UI action after stop. Navigation outcome unconfirmed. No robot motion ever sent in this task.

Chrome and Firefox official winget installations succeeded. Native Chrome first-run completed signed-out; default browser unchanged. URL entered for Auto Studio auto:chip/B4BFE91C5A74&monitor=1. CUA Chrome unavailable even after install; native sky then stopped. Edge login1 failed due stale dist plaintext user mice; corrected source verified privately, no password reset. Both hub stores and actual board admin/super_admin accounts accept admin123. Actual WiFi robot67 connected manny at192.168.137.66; status idle/attached saved root scratch/robot-hotspot-2026-10-22. Only Bluetooth COM3/4/5/7, no COM21. Existing31 unsaved browser keyframes preserved via hotspot_backup_20261022_1728.json/yaml.

## Next
1. Restore allowed actual-browser control after runtime policy stop; do not bypass browser security. Log in with verified admin/admin123; actual hotspot connection already works.
2. Preserve browser work in a uniquely named copy; show video/skeleton beside robot.
3. Fit gestures to actual rig, validate paths/limits then small real move and stop proof. Expand to all valid saved poses/moves and video/talking tests; record failed/skipped cases honestly.
4. Checkpoint and push each meaningful step. Do not modify calibration, pins or firmware. Physical setup/user input only if read-only diagnostics establish it is missing.

## Blocked
- Native browser control stopped for URL-confidence enforcement. Real playback/video/skeleton/RRT/fit/reconnect tests pending; no physical motion measured. RS485/USB failover also requires cable/COM21.
