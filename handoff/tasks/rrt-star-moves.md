# Checked RRT* detours for normal Studio movements

Owner: claude:cloud-48oymn
Updated: 2026-10-22 12:23 +0000
Branch: claude/project-thread-48oymn (from task/A46-2-10221724-9d65 @4c362a9)
Last commit: 239711d (final source checkpoint follows)
Plan: A46-3

## Goal
User: normal point-to-point moves that would self-collide should use RRT*,
warn the user, and move smoothly without self-collision. Cover normal Studio
pose/live and timeline preview+dispatch through shared geometry/rig limits.
No unsafe override when no checked route; do not claim physical safety from
simulation alone. Broader real browser/robot demonstration stays A46-2.

## Done
- Located current RRT-Connect+shortcuts used only by video/dummy/talk.
- Located unsafe ordinary sendPose/livePump and timeline crash override paths.
- Official OMPL RRTstar design reference consulted (parent choice, rewiring,
child cost updates, bounded solve time). No external runtime dependency needed.
- Requested independent Codex gpt-6-astra/high design review rrt_guard_review;
read-only reviewer, <=650words, exact candidate and critical dispatch risks.
- Real robot67 idle, hotspot manny On, newIP192.168.137.138 after DHCP renewal;
no motion commands issued. Preserve existing browser31-keyframe backup and
all real calibration. No firmware changes.

## Doing now
Claude (cloud) took over from Codex 2026-10-22 19:25 Bangkok: set up cloud QC,
run the A46-3 focused checks, then full quiet QC, then PR + merge.

## Codex state at hand-off (4c362a9)
RRT* plus checked source/rounded legs, one dispatch owner and actual reported
arrival, immutable native/hub startup, captured target/serial port/bus, Stop
barrier and Monitor/follow cancellation implemented. No force override.
Extra gap defaults0, adds to base4mm across body/head/arms/hands, persists in
browser/rig/settings bundles. Original geometry/calibration unchanged.
Focused72/0 (58.4s), expanded dispatch12/0. Eight deliberate mutations caught:
gap ignored, rig revision ignored, no RRT rewiring, ACK-as-arrival, queued
target adoption, Stop race, partial-loop jump, and detour clock backtracking.
Private evidence scratch/rrt-*-sabotage.log; sources restored and green.
Fake status now matches motion-state/limit contract; opt-in timed fake for
seek/playback. Legacy fixtures now use valid poses/physical durations and
await Play/arrival instead of assuming sleeps. Patch0056/0057 saved.
Accidental unsupported --help started a second QC; stopped its verified own
process tree/orphan, restored its equivalent ai_panel test mutation. Final
isolated targeted72/0 afterward; full frozen gate still required.
Final independent review requested from same rrt_guard_review on exact tree.
Not deployed; real robot remains idle onWiFi138. No physical movement proof.

## Next
1. Resolve final review, freeze exact tree and run full quiet QC.
2. PR/merge/build/deploy with fresh backups of main's dirty data/exe.
3. Verify installed actual UI/version, clothing gap persistence, hardware idle.
4. Resume A46-2 real visible tests only with permitted browser control, actual
rig fit and checked paths. No source-only/fake result is physical proof.

## Blocked
- No source design prerequisite; actual browser URL-confidence policy stopped
prior native UI control, and no COM21 for real RS485 failover. These do not
block isolated implementation, but remain limits on real demonstration.
