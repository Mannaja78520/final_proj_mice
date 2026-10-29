# Shared smoother never raises jerk (RL keyed rougher than policy)

Owner: claude:yinmmk
Updated: 2026-10-30 (cloud thread "Merge RL lift work and fix smoother jerk")
Branch: claude/project-thread-yinmmk
Last commit: this checkpoint
Plan: A54-2

## Goal
Coordinator 2026-10-30: the shared smoother RAISES jerk on dense RL motion (rl 25033 -> rl_smooth
33168; witsawa center 29813 -> 39922). Find why, fix so smoothing never increases jerk for any source,
keep music timing and real flicks, config-driven; before/after numbers in docs/experiments; regression
test, full QC, merge. Say what is untested on hardware (board PASS).

## Doing now
Code, test and records written; waiting for the rl-lift PR's full QC to finish (one QC at a time),
then quick checks + sabotage, full QC, PR, merge.

## File status
Baseline: 69898b5 (claude/rl-lift-1030 merged with main 4c25306)

| File | Change | State | Verification | Commit |
| --- | --- | --- | --- | --- |
| `main_python/motion_smooth.py` | DensePath, path speeds/check in vias, jerk guard, move_jerk | done | direct test run OK; check_motion_smooth not run | this checkpoint |
| `nong/main_python_set_nong/web/app_parts/motion_smooth.js` | jerk guard + moveJerk (parity) | done | not run | this checkpoint |
| `nong/main_python_set_nong/web/app.js` | built from parts | done | build_web.py | this checkpoint |
| `nong/main_python_set_nong/web/motion_smooth.json` | jerkGuard, jerkFrameMs, followDensePath | done | json loads | this checkpoint |
| `tools/rl_compare/smooth.py` | vias(dense=...) from CommandSmoother | done | synthetic run | this checkpoint |
| `tools/rl_compare/to_sequence.py` | board files pass at the sim motion's speeds | done | not run | this checkpoint |
| `qc/checks/check_motion_smooth.py` | test_guard, test_dense, JS guard parity | done | test_guard/test_dense direct OK | this checkpoint |
| `main_python/web/help/parts/studio.html` + `main_python/web/help.html` | help: jerkGuard, followDensePath | done | build_web.py | this checkpoint |
| `docs/systems/motion-smooth.md` | rules and traps | done | - | this checkpoint |
| `docs/experiments/2026-10-30_smoother_jerk.md` | cause, fix, numbers, refs | done | - | this checkpoint |
| `docs/PLAN.html`, `docs/plan_state.js` | A54-2 doing | done | plan.py | this checkpoint |

## Facts found
- main_python/motion_smooth.py vias(): with touches=None the off-line limit is uncheckedOffLineDeg (1 deg);
  rl_compare/smooth.py and to_sequence.py pass no touches, so 98 % of via speeds were shrunk to 0 -> cosine stops.
- motion_smooth.py _bad(): any joint breaking a rule shrinks ALL joints' speeds of both keys of that move.
- tools/rl_compare/metrics.py:100 jerk = third difference of the servo-model output at 50 Hz (frameHz).
- Cloud QC needs `pip install torch --index-url https://download.pytorch.org/whl/cpu opencv-python-headless mujoco`
  for check_rl_compare / sim checks; PlatformIO native test fails here (registry download limit).

## Done
- Cause measured (docs/experiments/2026-10-30_smoother_jerk.md); fix + tests + help + records written.

## Next
1. run_qc --quiet check_motion_smooth check_rl_compare; sabotage followDensePath and jerkGuard.
2. Full QC, PR, merge; tell the coordinator so the PC pulls + rebuilds.
3. PC: re-run rl_compare (rl_smooth) and to_sequence on the four dances for the real before/after.

## Blocked
- Nothing. Hardware: PASS untested on a board.
