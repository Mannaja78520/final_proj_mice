# Real robot hotspot demonstration

Owner:
Updated: 2026-10-22T17:36:15.352600+07:00
Branch: main (A46-3 merged from claude/project-thread-48oymn)
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
Nothing. Codex stopped here; A46-3 (checked RRT* detours, extra clothing gap)
was finished, full-QC'd and merged by Claude cloud 2026-10-22. Deploy it on the
PC before any real motion.

## Codex notes (2026-10-22 17:36)
WiFi experiment finished. Hotspot was Off80s then On restored. Initial runner
exit1 watched old DHCP66 for140s; actual Hub discovery found same chip at138.
Authenticated INFO/PERF: boots1->2 reset=reboot, idle, all calibration arrays
preserved. Evidence root scratch/robot-hotspot-2026-10-22/wifi-late-result.json,
wifi-late.log and wifi-late-discovered.json. Rejoin observed, not exact latency
or proven hotspot-off-before-boot ordering (Off2.438s after REBOOT ack).
Hotspot left On. Browser URL policy stop from previous work remains unresolved.
User now requests RRT* point-to-point detours+warnings; A46-3 owns source work
in same private branch before further hardware motion. All original live
motion/video/skeleton/browser tasks remain pending; no pose commands sent.

## Next
0. PC: pull main, `python tools/systems.py build`, rebuild MiceHub.exe (spec),
   restart the hub; check /api/version not stale; Setup shows "extra gap" and it
   persists; robot idle. Back up the dirty data/exe first.
1. Restore allowed actual-browser control after runtime policy stop; do not bypass browser security. Log in with verified admin/admin123; actual hotspot connection already works.
2. Preserve browser work in a uniquely named copy; show video/skeleton beside robot.
3. Fit gestures to actual rig, validate paths/limits then small real move and stop proof. Expand to all valid saved poses/moves and video/talking tests; record failed/skipped cases honestly.
4. Checkpoint and push each meaningful step. Do not modify calibration, pins or firmware. Physical setup/user input only if read-only diagnostics establish it is missing.

## Blocked
- Native browser control stopped for URL-confidence enforcement. Real playback/video/skeleton/RRT/fit/reconnect tests pending; no physical motion measured. RS485/USB failover also requires cable/COM21.
