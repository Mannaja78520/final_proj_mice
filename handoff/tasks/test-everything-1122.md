# Test and simulate every case across all apps (round 2, PC)

Owner: claude
Updated: 2026-11-22 15:00 +0000
Branch: claude/project-thread-4fv5bo
Last commit: see git log
Plan: none (user 2026-11-22: "test everything, every case, simulate everything")

## Goal
Test every case from docs/test_cases/*.md, find bugs, fix them with a QC check each (sabotage proven), Help in 4 languages. Friend repos are never edited. Do not merge.

## Doing now
Round 2 step 1: firmware SIM cases on QEMU (`tools/sim_sweep.py`), pio builds of 4 envs.
Order after: 2 Studio browser, 3 many boards, 4 voice/faces, 5 TV Chrome 75, full QC, push.

## File status
Baseline: 0b5870a

| File | Change | State | Verification | Commit |
| --- | --- | --- | --- | --- |
| `handoff/tasks/test-everything-1122.md` | task file | in progress | n/a | this checkpoint |

## Facts found
- pio is `python -m platformio`; QEMU installs with `python tools/qemu_esp32.py install` (.local/qemu).

## Done
- Round 1 (PR #204): case lists, 4 fixes.

## Next
1. Run steps 1-5 from the brief; append sections to docs/test_cases/results_2026-11-22.md.

## Blocked
- nothing
