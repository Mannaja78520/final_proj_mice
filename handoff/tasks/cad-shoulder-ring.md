# CAD look: body ring must not turn with shoulder roll; bolts on their axes

Owner: claude:wvmxq5
Updated: 2026-10-27 15:54 +0000
Branch: claude/project-thread-wvmxq5
Last commit: <sha>
Plan: A48-19

## Goal
User 2026-10-27: the ring fixed to the body must not turn with the shoulder roll (roll = lower servo, swings the whole shoulder and the lift axis). Pitch following is right. Bolts must stay locked to their axes. Fix in data; never edit the URDF/SolidWorks.

## Doing now
Code + check done (check_urdf_look 67/67, 9 sabotages caught). Next: PC runs `python tools/urdf_parts.py <real urdf> --assign nong/main_python_set_nong/web/urdf_view.json` to see which real bolts move; tune lock numbers if needed; full QC; PR; merge.

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
- New: app_parts/urdf_pieces.js (urdfSplit/urdfAssign/urdfPieces), called from urdfBuildInto when every mesh is cached; a late last mesh triggers buildRobot once (meshDone). Data urdf_view.json "pieces". Python twin tools/urdf_parts.py assign()/moved_pieces(). Fixture qc_bot6 (write_pieces_cad), driver res12.
- PC run 2026-10-27 (real URDF code/nong/main_python_set_nong/models/nong_description/urdf/nong_description.urdf): links are L_sh_mid/L_el_mid (not L_a); 1 STL per link, visual origins 0. L_sh_mid = 21x21x9 disk on the L_SH_P (roll) axis, moved by L_SH_P. Bolts (~5x8x7 mm, ~11k tris) sit in the PARENT link's STL: waist_link #5-#9 on the shrug axis, shrug_link #3-#10 ~20 mm from SH_P, L_upper #10/#11 next to shrug #7/#8.
- Rig servo1 L_SH_R (roll) drives URDF L_SH_P (first joint, axis -x); servo0 L_SH_P (pitch) drives URDF L_SH_R.
- qc/_urdf_real.json (git-ignored): real chain shrug_link -L_SH_P(axis -x)-> L_a -L_SH_R(same origin)-> L_upper_link. Fit binds rig servo1 (L_SH_R, home 140) to URDF L_SH_P (first joint) and servo0 to URDF L_SH_R.
- urdf_view.js urdfBuildInto ~l.295: each link's visuals hang on linkG[name]; no per-piece reassignment yet.

## Done
- <what landed, with PR or commit and how it was verified>

## Next
1. <the next concrete step, with the command if there is one>

## Blocked
- <what it waits on: robot, user account, a person, a decision; or "nothing">
