# RL: follow the dancer's lifts + smooth, all four dances (2026-10-30)

## Doing now
Final run done (04:01). Board files done (.local/robot_1030). Next: the queued deploy step 5.

## Resume (if the PC or the session dies)
Rounds save to .local/rl_final_1030/<dance>/servo_5mm/rl/round_NN. Re-run WITHOUT --fresh to resume:
`bash .local/cheer_rig_1029_30fps/final_all.sh` (from E:/final_proj/mice/mice_system). It runs from .local/main_run.

## Next
1. DONE 2026-10-30 04:01. When all four finish: compare (.local/cheer_rig_1029_30fps/compare_reach.py <dance> .local/rl_final_1030 rl,hybrid,rl_smooth).
2. DONE (.local/robot_1030). Board files per dance: `python -m tools.rl_compare.to_sequence --dance <d> --data-dir <abs data> --out <abs .local/rl_final_1030> --contender hybrid` (rl if hybrid touches) from .local/main_run; then smooth_sequence.py --source rl for moves_pass; collision-check (check_pass.py).
3. DONE. watch.html: add the rl_final_1030 sets.
4. Append final numbers to docs/experiments/experiment-records.md; full QC; push; cloud thread merges.
5. Queued by the coordinator 2026-10-30 (after the RL job, do not interrupt it): in E:/final_proj/mice/mice_system
   commit the local work, merge origin/main (voice fix PR #111/#112; 12 files overlap the RL-compare edits;
   resolve by hand, never discard edits), rebuild `python -m PyInstaller --clean --noconfirm MiceHub.spec`, then
   stop hub PID 26664 + helper 13744 and remove the worktree .claude/worktrees/voice-test.
   See handoff/tasks/voice-fix-all-1029.md Next 1.

## Facts found
- Shoulder pitch stops at 25 deg (servo 180 deg via 14:19 gears); user declined a gear change -> reach fitting.
- Sending commands early (lead) hurts lift follow. Shrug-free and 2 s gap fill do not help.
- Six RL runs at once: RAM is the limit (3 GB free of 31), GPU 4.7/12 GB at 83 %.
- The PC working tree has other threads' uncommitted edits: never pull/checkout there; commit with a temp index.

## File status
| File | Change | State | Verification | Commit |
|---|---|---|---|---|
| tools/rl_compare/env.py | lift reward term, shrugFree | done | check_rl_compare 33/33, sabotage 1/1 | this |
| tools/rl_compare/run.py | --set overrides | done | used by all A-E runs | this |
| qc/checks/check_rl_compare.py | lift reward checks | done | 33/33 | this |
| docs/experiments/experiment-records.md | lift study A-E + lead | done | numbers from compare_reach.py | this |
| handoff/tasks/rl-lift-1030.md | this file | done | - | this |
| docs/experiments/experiment-records.md (final) | four-dance final table | done | compare_reach.py on .local/rl_final_1030 | this |
