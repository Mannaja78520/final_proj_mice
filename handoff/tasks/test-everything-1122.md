# Test and simulate every case across all apps (round 2, PC)

Owner: claude
Updated: 2026-11-22 15:00 +0000
Branch: claude/project-thread-4fv5bo
Last commit: see git log
Plan: none (user 2026-11-22: "test everything, every case, simulate everything")

## Goal
Test every case from docs/test_cases/*.md, find bugs, fix them with a QC check each (sabotage proven), Help in 4 languages. Friend repos are never edited. Do not merge.

## Doing now
Round 2 finished; waiting for coordinator merge. Nothing running.

## File status
Baseline: 0b5870a

| File | Change | State | Verification | Commit |
| --- | --- | --- | --- | --- |
| `handoff/tasks/test-everything-1122.md` | task file | done | n/a | this checkpoint |
| `firmware/src/core/CommandRouter.cpp`, `firmware/src/core/WebPortal.cpp`, `firmware/COMMANDS.md` | SET ID digits only; PEERS with WiFi off | done | QEMU check_qemu_firmware 37 ok, sabotaged | pushed |
| `main_python/bus_ids.py`, `qc/checks/check_bus_scale.py` | stuck chip listed once | done | sabotage caught | pushed |
| `apps/voice/service.py`, `qc/checks/check_voice_guard.py` | /ask odd body shapes | done | sabotage caught | pushed |
| `tools/{sim_sweep,studio_sweep,many_boards_probe,helpers_probe,legacy_probe}.py`, `docs/systems.json` | sweep scripts | done | run, see results file | pushed |
| `docs/test_cases/results_2026-11-22.md` | round 2 section | done | n/a | pushed |

## Facts found
- pio is `python -m platformio`; QEMU installs with `python tools/qemu_esp32.py install` (.local/qemu).

## Done
- Round 1 (PR #204): case lists, 4 fixes.
- Round 2: 4 more bugs fixed (PEERS panic, SET ID 1.5, bus fix duplicates list, voice /ask body shape). Full QC 10019 pass, 3 fail (2 fixed after, 1 env-only).

## Next
1. Coordinator merges PR #204. Then TV VM restore by a person (see results file, section 5).

## Blocked
- nothing
