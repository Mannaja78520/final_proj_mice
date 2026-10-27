# Tidy the code folder layout

Owner: claude:10271959-0190
Updated: 2026-10-27 20:20 +0000
Branch: claude/project-thread-9y1rwe
Last commit: this checkpoint
Plan: A51-1

## Goal
User 2026-10-27: the code folder is cluttered; put .staging copies in their own
folder so they stop piling up at the root; tidy the other folders; rename
`code` (agreed: `mice_system`, do it LAST); everything dynamic + OOP, with a
header map of what lives where. Plan: /mnt/project-files/layout/layout_plan_2026-10-27.md

## Doing now
Full QC on the layout PR (pio build first), then PR + tell coordinator before merge.

## File status
Baseline: 4c230e0

| File | Change | State | Verification | Commit |
| --- | --- | --- | --- | --- |
| `config/layout.json` | new: layout registry (root map, staging home/books, _out kinds) | done | check_root_tidy (sabotage 4/4) | this checkpoint |
| `tools/layout.py` | new: RepoLayout: real root, trees, books, out, root map, LAYOUT.md build | done | check_root_tidy | this checkpoint |
| `docs/LAYOUT.md` | new, generated map | done | check_root_tidy | this checkpoint |
| `qc/checks/check_root_tidy.py` | new check | done | sabotage 4/4 caught | this checkpoint |
| `promote.py` | trees in .staging/<task>, books via layout, _out skipped | done | promote_* checks pass | this checkpoint |
| `tools/{make_diary,handover,make_app_branch,next_batch,plan,bridge,ai_panel,branch,watch_main,land}.py` | root via RepoLayout; branch/land/watch use new homes | done | quick QC | this checkpoint |
| `qc/lib/qc.py`, `qc/run_qc.py` | F.LAYOUT/F.REAL; --changed compares with real root | done | quick QC | this checkpoint |
| `qc/checks/check_{code_patches,dev_tools,history,parallel_runs,plan_live,promote_ask,promote_pipeline,watch_main}.py` | follow new paths; boxes copy layout.py | done | pass | this checkpoint |
| root one-offs (16 files + .promote-manifest.json) | deleted (in git history) | done | check_root_tidy | this checkpoint |
| `tools/bench/`, `tools/auto_click/`, `docs/archive/` | moved from root | done | check_systems | this checkpoint |
| `tools/build_exe.bat` | new (was PC-only build.bat) | done | not run (Windows) | this checkpoint |
| `HANDOFF.md`, `CLAUDE.md`, `README.md`, `docs/COORDINATION.md`, `.claude/*`, `.gitignore`, `docs/systems.json`, `docs/systems/*` | paths + map link | done | quick QC | this checkpoint |
| `docs/PLAN.html`, `docs/plan_state.js` | A51 heading + A51-1 | done | check_plan_areas | this checkpoint |

## Facts found
- Root detection "parent if name startswith .staging" was copied in 9 tools + qc/run_qc.py:322, qc/checks/check_history.py:40; check_dev_tools.py:112 holds "prefix not exact name".
- promote.py:52 STAGING default, :71 _pick_staging, :176-178 book names, :417/:456 locks; SKIP_DIRS already has dist/build.
- check_code_patches.py:41 and check_promote_ask.py:41 assume `<root>/.staging` is a tree.
- PC root (read-only 2026-10-27): 20 `.staging-*` trees, build.bat untracked, scratch/ _photo_test/ _video_test/ patches_code/ build/ ignored.
- E:\final_proj\mice\Photobooth is the friend's git repo (ChocolateOwO/Photobooth); Photobooth-run/Dummy is run data.

## Done
- Survey + plan posted to the user.
- Quick QC 6400/6: 3 need the pio firmware build (flash/OTA), plan-area heading fixed.

## Next
1. Full QC (`pio run -e mice_nong` in firmware/ first), open PR, tell coordinator before merge.
2. PR 2: per-PC app registry (extensions): hub Add app / remove, hide missing parts, partner folders relative + per-PC override, install guide for client PCs.
3. Later with user OK: rename code -> mice_system, move parent-folder items (plan file section 3).

## Blocked
- Rename code -> mice_system and parent-folder moves: after other threads merge, user OK.
