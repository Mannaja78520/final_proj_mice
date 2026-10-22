# Checked RRT* detours for normal Studio movements

Owner: codex:10221724-9d65
Updated: 2026-10-22T17:54:02.056842+07:00
Branch: task/A46-2-10221724-9d65
Last commit: 0361ef7 (planner/settings checkpoint follows)
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
Checked dispatch draft added; first combined31/1 exposed faithful fake status
missing min/max/moving. Added firmware-shaped fields; second32/2 exposed
dummy test assuming arrival after a fixed sleep. Test now awaits actual move.
Final integration review blocks unchecked SD/handoff entry, mutable hub
timeline, queued target changes, direct clock drift, Monitor cancellation,
missing motion-state validation. Fixing these before next frozen check.
No runtime deployment or real movement yet. Settings draft remains isolated.
Pure RRT* implemented with checked parent choice, rewiring/descendant costs,
goal reconsideration, quick connect seed and checked shortcuts. Original
path check19/0. Added Settings extra gap in mm, persisted through rig/settings
bundles. Baseline4mm unchanged; extra gap affects body/head/arms/hands.
Initial combined31/3:3 failures were test bundle aliasing (collectSettings
returns live RIG reference); fixed test to serialize before mutating. Recheck
new check15/0. Real RRT* rewires and lower-cost parents observed in QC.
Independent planner review found/fixed corrupt numeric setting bypass,
source-rounding mismatch and async input/rig revision races. Async slicing is
a scheduling target, not a hard per-collision deadline. Need final review.
Remaining main work: normal motion single owner/settled actual source,
checked timeline preview+dispatch, STOP/Live-off/cancel cases. Not deployed;
robot idle onWiFi138. Original user calibration/config not changed.

## Next
1. Apply bounded RRT* algorithm and shared checked-motion integration, keeping
preview and dispatch coherent. Reject colliding endpoints/no path and show
clear route/refusal status. Revalidate all final smoothed legs.
2. Focused fake/browser regressions and deliberate failure proofs; final review.
3. Freeze exact runtime tree for full quiet QC before PR/merge/build/deploy.
4. Resume A46-2 real visible tests only with permitted browser control, actual
rig fit and checked paths. No source-only/fake result is physical proof.

## Blocked
- No source design prerequisite; actual browser URL-confidence policy stopped
prior native UI control, and no COM21 for real RS485 failover. These do not
block isolated implementation, but remain limits on real demonstration.
