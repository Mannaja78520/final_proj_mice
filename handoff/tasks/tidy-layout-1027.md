# Tidy the code folder layout

Owner: claude:10271959-0190
Updated: 2026-10-27 20:05 +0000
Branch: claude/project-thread-9y1rwe
Last commit: this checkpoint
Plan: A51-1

## Goal
User 2026-10-27: the code folder is cluttered; put .staging copies in their own
folder so they stop piling up at the root; tidy the other folders; rename
`code` (agreed: `mice_system`, do it LAST); everything dynamic + OOP, with a
header map of what lives where. Plan: /mnt/project-files/layout/layout_plan_2026-10-27.md

## Doing now
Routing promote.py, run_qc.py and the qc checks through tools/layout.py.

## File status
Baseline: 4c230e0

| File | Change | State | Verification | Commit |
| --- | --- | --- | --- | --- |
| `config/layout.json` | new: the layout registry | done | not run | this checkpoint |
| `tools/layout.py` | new: RepoLayout (real root, staging home, out, root map) | done | `layout.py where` ok | this checkpoint |
| `tools/{make_diary,handover,make_app_branch,next_batch,plan,bridge,ai_panel,branch,watch_main}.py` | root via RepoLayout | done | plan.py show ok | this checkpoint |
| `promote.py` | staging trees in .staging/<task>, books via layout | pending | not run | uncommitted |
| `qc/run_qc.py`, `qc/lib/scope.py`, `qc/checks/*` | root/staging via layout | pending | not run | uncommitted |
| root one-off scripts | delete/move | pending | not run | uncommitted |
| `qc/checks/check_root_tidy.py`, `docs/LAYOUT.md` | new | pending | not run | uncommitted |

## Facts found
- Root detection "parent if name startswith .staging" was copied in 9 tools + qc/run_qc.py:322, qc/checks/check_history.py:40; check_dev_tools.py:112 holds "prefix not exact name".
- promote.py:52 STAGING default, :71 _pick_staging, :176-178 book names, :417/:456 locks; SKIP_DIRS already has dist/build.
- check_code_patches.py:41 and check_promote_ask.py:41 assume `<root>/.staging` is a tree.
- PC root (read-only 2026-10-27): 20 `.staging-*` trees, build.bat untracked, scratch/ _photo_test/ _video_test/ patches_code/ build/ ignored.
- E:\final_proj\mice\Photobooth is the friend's git repo (ChocolateOwO/Photobooth); Photobooth-run/Dummy is run data.

## Done
- Survey + plan posted to the user.

## Next
1. promote.py + qc via RepoLayout; update checks that name `.staging`.
2. Root cleanup, check_root_tidy, docs/LAYOUT.md, HANDOFF link, systems.json.
3. Quick QC, full QC, tell coordinator before merge.

## Blocked
- Rename code -> mice_system and parent-folder moves: after other threads merge, user OK.
