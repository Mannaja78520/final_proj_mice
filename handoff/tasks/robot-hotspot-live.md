# Real robot hotspot demonstration

Owner: codex:10221724-9d65
Updated: 2026-10-22 17:25 Asia/Bangkok
Branch: task/A46-2-10221724-9d65
Last commit: 3438033 (connection/browser checkpoint follows)
Plan: A46-2

## Goal
Test saved motions, speech gestures/RRT, video copying and skeleton visibly on the real robot over the existing PC hotspot. Preserve original projects/calibration.

## Done
- Deployed software runtime already full QC7547/0, live voice replay50/50 after model readiness.
- User explicitly authorizes real robot playback in this request.
- Opened visible Studio in user browser. Existing unsaved31-keyframe project must be preserved.
- No robot motion sent. Hub modules empty, no hotspot interface in initial inventory.

## Doing now
User enabled hotspot manny. Robot67 found at192.168.137.66, chip/B4BFE91C5A74; actual WiFi only, no COM21 (only Bluetooth3/4/5/7). Live INFO idle/attached with10 joint arrays saved privately. Existing31-keyframe browser work restored and saved as hotspot_backup_20261022_1728, original files untouched. User extends scope: WiFi reconnect/Auto fallback, real browsers Edge/Chrome/Firefox, default admin+super_admin/admin123. Both hub stores and both actual board logins verified against requested password; stale dist plaintext account mice caused1 rejected Edge login, no reset. Correct saved password main_python/hub_password.txt verified offline. Chrome official winget user-scope failed no installer; default machine install succeeded; Firefox install in flight log root scratch/robot-hotspot-2026-10-22/install-firefox.log. Browser connector Chrome unavailable even after install; dedicated computer-use sky controls actual Chrome/Edge windows. No robot motion sent yet. Chrome first-run setup in progress. No source/firmware/calibration changed.

## Next
1. Connect robot via hotspot; inspect live info/pose and telemetry.
2. Preserve browser work in a uniquely named copy; show video/skeleton beside robot.
3. Fit gestures to actual rig, validate paths/limits then small real move and stop proof. Expand to all valid saved poses/moves and video/talking tests; record failed/skipped cases honestly.
4. Checkpoint and push each meaningful step. Do not modify calibration, pins or firmware. Physical setup/user input only if read-only diagnostics establish it is missing.

## Blocked
- WiFi working. RS485/USB physical failover cannot be measured without cable/COM21. Actual motion tests still pending.
