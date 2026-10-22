# Checked RRT* detours for normal Studio movements

Owner: codex:10221724-9d65
Updated: 2026-10-22T17:54:02.056842+07:00
Branch: task/A46-2-10221724-9d65
Last commit: e8d61e4 (design checkpoint follows)
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
Design before code: inspect shared planner and normal motion dispatch,
one outbound queue, latest-goal handling, STOP invalidation, actual settled
start pose vs stale targets, leg timing/easing, preview/export integration.
Candidate E:/final_proj/mice/code/.staging-profiles, same isolated WIP branch.
No source edits or checks yet. Root user dirty files preserved.

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
