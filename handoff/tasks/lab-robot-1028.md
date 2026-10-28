# Lab 2026-10-28: real nong tests, RL timing, .staging moves

Owner: claude:lab-robot-1028
Updated: 2026-10-28 19:10 (Bangkok)
Branch: claude/lab-robot-1028
Last commit: this checkpoint
Plan: A45-11, A46-2, A48-6, A48-23, A48-24, A50 (rl_compare), A51-1 PC steps

## Goal
Coordinator 2026-10-28 (user turned the robot on; lab until 21:00 Thai): pull main,
systems build, flash nong (PR #94 firmware), combined real-robot tests from
robot-tests.md / lab-day.md, slow first then faster; raw numbers in
docs/experiments/experiment-records.md; then RL training with timing; then the
.staging moves of pc_steps_A51-1.md (moves only). Never change servo axes/zero/home.

## Doing now
Waiting for a person beside the robot before any move. RL quick run on the GPU.

## File status
Baseline: 14fa8fc (origin/main, fast-forwarded from 023c644).

| File | Change | State | Verification | Commit |
| --- | --- | --- | --- | --- |
| `handoff/tasks/lab-robot-1028.md` | new task file | done | n/a | this checkpoint |
| `docs/experiments/experiment-records.md` | new: raw lab numbers | in progress | hardware | this checkpoint |

Not mine (pre-existing PC edits, left uncommitted): MiceHub.spec, config/voice.json,
docs/BRIDGE.md, nong projects/sequences my_move*, qc_chain_proj.json, settings_shared.json,
promt.md, qc/checks/check_game_prize.py, check_voice_profiles.py. Full pre-pull diff is in
stash `pc-local-2026-10-28-before-pull-14fa8fc` (also holds 7 files that clashed with main:
config/gacha.json, docs/PLAN.html, plan_state.js, lab-day.md, setup.html, view.html,
web/index.html, style.css - kept at main's version).

## Facts found
- `pio` is not on bash PATH: use `~/.platformio/penv/Scripts/pio.exe`.
- OTA without the hub UI: `hub_flash.Flasher().start_ota(ip,"nong")` after `import main`
  (board_login reads config/board_logins.json, no password typed).
- Board commands over WiFi: GET /api/cmd?c=<line> with cookie `mice_board` from main.board_login.
- Nong #67 is 192.168.137.92 now; its stored `safe_dps=190` (lab-day.md says 60).
- `pace: music` in a yaml uses the board's music cap (PACE MUSIC).

## Done
- Pull, `tools/systems.py build`, MiceHub.exe rebuilt (PyInstaller OK), `pio run -e mice_nong` OK.
- OTA to nong: 200 OK, reboot, `OTA` reports size=1638416 = this build.
- v5 dances in MuJoCo (sim only): left + center, 0 hits, 0 near, 0 s behind music.

## Next
1. With a person watching: slow joint checks, palm flip, A48-6 poses, then A48-23 pace steps.
2. RL: quick run, then full run; record wall time + GPU.
3. pc_steps_A51-1.md sections 2-3 after RL ends.

## Blocked
- Any robot move: a person beside nong (asked in the thread).
