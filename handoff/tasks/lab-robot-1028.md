# Lab 2026-10-28: real nong tests, RL timing, .staging moves

Owner: claude:lab-robot-1028
Updated: 2026-10-28 19:40 (Bangkok)
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
Nothing. User left 19:35; nong stopped at home (PACE NORMAL), RL stopped by hand.

## File status
Baseline: 14fa8fc (origin/main, fast-forwarded from 023c644).

| File | Change | State | Verification | Commit |
| --- | --- | --- | --- | --- |
| `handoff/tasks/lab-robot-1028.md` | new task file | done | n/a | this checkpoint |
| `docs/experiments/experiment-records.md` | new: raw lab numbers 2026-10-28 | done | hardware (nong #67) + sim | this checkpoint |

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
- `- pace: music N` in a yaml sets the cap for that file; a `next:` chain restarts it per file, so every chained file needs its own pace line.
- BUG: `MOVE` of a ~30 KB show (447 poses) crashes the board (reset=CRASH, no reply in 60 s). SequencePlayer::startAt (firmware/src/core/SequencePlayer.cpp:54) parses the whole file via SDStore::loadYaml (SDStore.cpp:68) in one go. 2 KB files chained with `next:` play fine. Studio "Save to robot" of a v5 dance will hit this.
- POSE/JOINT with T below the physical floor is raised by the board (T 80 -> 330 ms for 40 deg).
- WAIST 50 faces camera 0 (PC webcam index 0, 640x480, ~30 fps); crop [110:350, 100:340] holds the robot.
- Lab scripts (nc.py cmd client, chunk.py splitter, dance2.py runner + recorder, sheet.py contact sheet): .local/lab_1028/logs/ (not in git).

## Done
- Pull, `tools/systems.py build`, MiceHub.exe rebuilt (PyInstaller OK), `pio run -e mice_nong` OK.
- OTA to nong: 200 OK, reboot, `OTA` reports size=1638416 = this build.
- v5 dances in MuJoCo (sim only): left + center, 0 hits, 0 near, 0 s behind music.
- Hardware (camera-watched, raw numbers in docs/experiments/experiment-records.md): joint sweep 30/30 OK; palm-turn proxy (EL_R) and A48-6 3 poses OK; A48-23 ladder left_v5 at 60/90/180/270/servo max and center_v5 at 180/servo max, no knock seen, no reboot; at servo max left_v5 took 136.8 s vs 134.9 s planned.
- RL quick 998 s; full run partial (12/20 rounds of run 1, ~115 s/round).

## Next
1. Fix the large-show MOVE crash in firmware (stream steps or parse per step; QC check with a 30 KB show), then retry `MOVE` of a whole v5 file.
2. User picks `CFG music_dps` (lab: servo max had no knock seen; camera only, no sound check).
3. A48-24 servo delay: film at 240 fps or fix the frame-difference detector (step.py).
4. RL full run: `python -m tools.rl_compare.run` (~8 h; run 1 restarts, no resume). Add resume from round_NN/policy.pt if wanted.
5. pc_steps_A51-1.md sections 2-3 (.staging moves) after the RL run ends - NOT done.
6. Not run: last.yaml from nong.local, TALK ON phone mic, Video tab sound, Studio palm button, gachapon, A26-99/71/92, A16-1, A20-3.
7. Stash `pc-local-2026-10-28-before-pull-14fa8fc`: 7 PC files clashed with main (see File status); owner to reconcile.

## Blocked
- Lab time (user left 19:35), hub browser login for Studio tests.
