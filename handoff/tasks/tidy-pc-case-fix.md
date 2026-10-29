# Fix folder move script for same-name folders

Owner: claude:16wdox
Updated: 2026-10-29 08:05 +0000
Branch: claude/project-thread-16wdox
Last commit: this checkpoint
Plan: A51-4

## Goal
2026-10-29 on the PC: tools/tidy_pc.py moving Photobooth -> photobooth/Photobooth
(same name on Windows) made os.rename fail; shutil.move fell back to copy+rmtree
and half-deleted the friend's repo (recovered, nothing lost). Make same-name moves
safe, os.rename only, stop and name the folder on any failure.

## Doing now
Full QC (run_qc.py --quiet), then PR + merge.

## File status
Baseline: 1283955 (origin/main)

| File | Change | State | Verification | Commit |
| --- | --- | --- | --- | --- |
| `tools/tidy_pc.py` | move_all: temp-name route for dst inside src, nested first, _clash stop, MoveStopped, os.rename seam (_exists/_mkdir/_rename), fnmatchcase | done | check_tidy_pc 25/0, sabotage 4/4 | this checkpoint |
| `qc/checks/check_tidy_pc.py` | NoCase fake disk (Windows case rules): both orders, failed rename, run-only clash, no copy-then-delete | done | sabotage 4/4 | this checkpoint |
| `docs/PLAN.html` | A51-4 added/doing | done | plan.py | this checkpoint |

## Facts found
- tools/tidy_pc.py move_all: pairs sorted so a move into a folder of its own name goes first; _clash walks dst's parents with os.listdir to find a same-name-other-case folder.
- Windows fnmatch ignores case: matches() now uses fnmatchcase so "Photobooth" never matches the new photobooth/ folder.

## Done
- Fix + check, sabotage 4/4 caught (temp route, order, clash, shutil.move).

## Next
1. Full QC, PR, merge. Then the PC can run `python code/tools/tidy_pc.py apply --yes` again (Photobooth state on the PC after recovery: check with `plan` first).

## Blocked
- nothing
