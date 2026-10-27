# CAD look: body ring must not turn with shoulder roll; bolts on their axes

Owner: claude:wvmxq5
Updated: 2026-10-27 15:54 +0000
Branch: claude/project-thread-wvmxq5
Last commit: <sha>
Plan: A48-19

## Goal
User 2026-10-27: the ring fixed to the body must not turn with the shoulder roll (roll = lower servo, swings the whole shoulder and the lift axis). Pitch following is right. Bolts must stay locked to their axes. Fix in data; never edit the URDF/SolidWorks.

## Doing now
Wrote tools/urdf_parts.py (lists every mesh piece per link + distance to each joint axis). Next: run it on the PC's real URDF (Remote Control, read only) to see which link holds the ring and bolts.

## File status
Baseline: <starting SHA; reconcile owned commits, working diff and untracked files>

| File | Change | State | Verification | Commit |
| --- | --- | --- | --- | --- |
| `<repo/relative/path>` | <short change> | pending | not run | uncommitted |

<One latest row per owned source/generated/test/config/doc file, including additions,
deletions and renames. Use exact paths; link evidence and label quick/full or
simulated/hardware. Do not attribute other owners' edits. No edits: say so.
For this handoff file itself, Commit may be `this checkpoint`.>

## Facts found
- qc/_urdf_real.json (git-ignored): real chain shrug_link -L_SH_P(axis -x)-> L_a -L_SH_R(same origin)-> L_upper_link. Fit binds rig servo1 (L_SH_R, home 140) to URDF L_SH_P (first joint) and servo0 to URDF L_SH_R.
- urdf_view.js urdfBuildInto ~l.295: each link's visuals hang on linkG[name]; no per-piece reassignment yet.

## Done
- <what landed, with PR or commit and how it was verified>

## Next
1. <the next concrete step, with the command if there is one>

## Blocked
- <what it waits on: robot, user account, a person, a decision; or "nothing">
