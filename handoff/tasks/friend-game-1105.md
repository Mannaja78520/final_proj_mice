# Use All-Jao-Games win events + gacha.out webhook

Owner:
Updated: 2026-11-05 08:25 +0000
Branch: <branch, or main>
Last commit: <sha>
Plan: <plan ids, e.g. A45-11>

## Goal
<the user's ask, in their words if possible>

## Doing now
<written and pushed BEFORE each step: what you are about to do, the files, the approach>

## File status
Baseline: <starting SHA; reconcile owned commits, working diff and untracked files>

| File | Change | State | Verification | Commit |
| --- | --- | --- | --- | --- |
| `<repo/relative/path>` | <short change> | pending | not run | uncommitted |

<One latest row per owned source/generated/test/config/doc file, including additions,
deletions and renames. Use exact paths; link evidence and label quick/full or
simulated/hardware. Do not attribute other owners' edits. No edits: say so.
For this handoff file itself, Commit may be `this checkpoint`.>

## Facts found
- <file:line - what it does / why it matters; so the next AI does not read it again>

## Done
- <what landed, with PR or commit and how it was verified>

## Next
1. <the next concrete step, with the command if there is one>

## Blocked
- <what it waits on: robot, user account, a person, a decision; or "nothing">

## Doing now
QC full run, then PR. Not done on PC: `git pull --ff-only` + `npm.cmd test` in All-Jao-Games (needs remote control approval).

## Done
- link.js reads friend's `alljao:win` (playerName, result.label/score); old localStorage/text watchers removed from config/partners.json (they would double-fire).
- games rules get min/max score (gacha.py `_score_fits`, Prize machines page columns).
- webhook entry `{url, format:"alljao"}` sends {event,id,item,machines} + Bearer token (env GACHA_WEBHOOK_TOKEN or .local/gacha/game_webhook_token.txt).
- G4 contract drafted in docs/gacha/friend_requests.md.

## Facts found
- game_names (hub_api_gacha.py) now also reads the keys of a watcher's `results`.
- check_extensions fails on Linux before this change (path case); unrelated.

## File status
| File | Change | State | Verification | Commit |
|---|---|---|---|---|
| apps/all-jao/link.js | event results map | done | check_game_prize + sabotage | this branch |
| config/partners.json | one event watcher | done | check_gacha | this branch |
| main_python/gacha.py | score range, alljao webhook | done | check_game_friend_contract + sabotage | this branch |
| main_python/hub_api_gacha.py | game_names | done | check_gacha | this branch |
| apps/gacha/index.html, help parts, help.html | Score columns, help | done | quick | this branch |
| qc/checks/check_game_friend_contract.py (new), check_game_prize.py | tests | done | passed | this branch |
| docs/gacha/*, docs/systems* | contract, README | done | build | this branch |
