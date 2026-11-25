# QC speed on the PC

Owner: claude (project thread, branch claude/qc-speed-pc)
Updated: 2026-11-25
Branch: claude/qc-speed-pc
Last commit: see git log
Plan: none (measurement task from the owner: why 25-60 min on the PC vs 8.6 min in the cloud)

## Goal
User 2026-11-25: full QC is slow on the PC, run as much as possible in parallel. Never weaken a test.

## Doing now
SOLO move on claude/qc-solo-pool; watchdog next on a new branch. (PR #260/#262 merged) (full QC equal to main still to run when the PC is free).

## Done
- Two full runs measured (1524 s, 1541 s); numbers in docs/experiments/experiment-records.md (2026-11-25 PC).
- check_build_split shares one PlatformIO object cache across checkouts: 5-env build 474 s -> 42 s warm.
- qc/last_timing.json rows now carry `end` (seconds into the run).

- runlock (PC-wide QC lock) + check_run_lock; fw_cache (build-artifact cache) + check_fw_cache; both sabotage-proven.

## Next
- Give starved-margin SOLO checks a readiness signal, then move them to the pool one at a time (3 green crowded runs each).
- QC SILENT pages: find why a page never reports under load (190-478 s wasted per case).

## File status
| File | Change | State | Verification | Commit |
|---|---|---|---|---|
| qc/checks/check_build_split.py | shared pio cache + assertion | committed | sabotage by hand: FAIL when removed, PASS restored | see git log |
| qc/run_qc.py | `end` stamp in timing | committed | full run 2 wrote it | see git log |
| docs/experiments/experiment-records.md | PC numbers | committed | n/a | see git log |
| qc/lib/runlock.py, qc/checks/check_run_lock.py | PC-wide run lock | committed | 2 sabotages caught | see git log |
| qc/lib/fw_cache.py, qc/checks/check_fw_cache.py, check_build_split.py | artifact cache | committed | 3 sabotages caught; hit 31 s vs 136 s | see git log |
| qc/run_qc.py, qc/checks/check_qc_parallel.py, check_chatty_board.py | 12 checks out of SOLO | committed | 3 crowded full runs green | see git log |
