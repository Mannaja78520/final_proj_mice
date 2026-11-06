# Prize machine stock two-way, play only, random box

Owner: claude
Updated: 2026-11-05 10:48 +0000
Branch: claude/project-thread-tnec48 (on top of PR #127 branch)
Last commit: this checkpoint
Plan: A47 (not added to PLAN: plan_state kept out like #127)

## Goal
Prize machine stock two-way (hub tells game what exists, game results back), play-only mode (no real dispense), non-game sources, random box (counts per item entered at load, press random = weighted by remaining). All dynamic, no hardcode.

## Doing now
Waiting on `run_qc.py --quick`; then commit, push, draft PR (base = PR #127 branch).

## File status
Baseline: b7801bd (PR #127 head)

| File | Change | State | Verification | Commit |
|---|---|---|---|---|
| main_python/gacha_stock.py (new) | mixin: stock_view, load, give, play-only, game_event, random box | done | check_gacha_stock + sabotage 3/3 | this checkpoint |
| main_python/gacha.py | Gacha(GachaStock), cfg play_only/sources, settle_draw hook in dispense, push_stock in _after | done | check_gacha* pass | this checkpoint |
| main_python/hub_api_gacha.py, hub_auth.py | /stock /load /random, give(), game_event(), gating | done | check_gacha_stock | this checkpoint |
| apps/gacha/index.html + help part/help.html | Mode column, Stock card, play-only/programs card | done | check_gacha_ui | this checkpoint |
| qc/checks/check_gacha_stock.py (new) | hub-level, fake boards | done | passes | this checkpoint |
| docs/gacha/*.md, docs/friend/friend_requests_all_2026-11-05.md, docs/systems* | friend asks, README, systems map | done | n/a | this checkpoint |

## Done (QC verdict 2026-11-06, full run, PC, fakes only)
- `run_qc.py --quiet` on 07aa634: 9454 passed, 1 failed, 997.8s => QC FAIL (not green).
- Failing: check_faces_count (CRASH ConnectionAbortedError WinError 10053, parallel run). Alone: 16/16 pass, 2 of 2 re-runs.
- Flaky, reported by QC: check_flat_view_drag (parallel fail, alone 8/8 pass).
- No gacha check failed. Exe NOT rebuilt, systems map NOT rebuilt (run was not green). Not merged.

## Facts found
- gacha.py dispense(): one place (after the for/else) calls settle_draw, so every path (route, game_win, give) settles a random box.
- Random box counts live in .local/gacha/boxes.json (hub), the board only counts balls (GSTOCK sum).
- fake_serial has only bus ids 70/71 (GACHA_IDS); a third bus board would change other checks' module census.
- PIO check fails in the cloud (no PlatformIO): unrelated.

## Next
1. PC: full QC, rebuild exe, merge after PR #127.
2. Friend: asks in docs/gacha/friend_requests.md (update 2).

## Blocked
- nothing (untested on real boards and with the real game; fakes only)
