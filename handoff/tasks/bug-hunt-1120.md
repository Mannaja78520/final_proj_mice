# Bug hunt 2026-11-20 (claude, thread "Hunt and fix remaining project bugs")

Owner: claude:t1hnh5   Updated: 2026-11-20

## Doing now
Merging PR #122 content (untrack faces_login.json) + new guard check; then red-team pass on auth/safety.

## Done
- Quick QC on main (cloud): 6741 pass, 7 fail = environment only (no torch/mujoco/pio build; Windows-case path check on Linux).
- #122 rebased onto main, checks faces_login friend_api no_data_loss voice_identify faces_poll pass.
- New check_no_ignored_secrets: git-tracked-but-ignored files fail QC (proven by tracking a dummy ignored file).

## Facts found
- main_python/faces_login.json was tracked despite .gitignore:65 (password in public history; user must change it on Reconize side).
- Pulling this change DELETES the local faces_login.json on the PC (git removes untracked-in-new-commit files): back it up first.
- dist/hub_password.txt is tracked (346 bytes); contents not reviewed here. User should check it holds only the default test password.
- plan.py show rewrites docs/PLAN.html timestamps: do not run it in a bug-hunt branch.

## File status
| File | Change | State | Verification | Commit |
|---|---|---|---|---|
| main_python/faces_login.json | untracked (from #122) | done | faces_login qc quick | merge of #122 |
| main_python/faces_login.example.json | added (from #122) | done | same | merge of #122 |
| docs/friend_requests_admin_2026-11-04.md | added (from #122) | done | n/a | merge of #122 |
| qc/checks/check_no_ignored_secrets.py | new guard | done | quick, sabotage proven | this checkpoint |
| handoff/tasks/bug-hunt-1120.md | this file | done | n/a | this checkpoint |
