# PC 2026-10-28 evening: RL run, visuals, .staging moves

Owner: claude:el6dyy
Updated: 2026-10-28 20:20 (Bangkok)
Branch: claude/project-thread-el6dyy (based on claude/lab-robot-1028)
Last commit: this checkpoint
Plan: A50-1 (rl_compare), A48-23 (pace ladder chart), A51-1 (PC steps 2-3)

## Goal
User 2026-10-28 12:53Z: "อย่าลืมทำ RL ทำอะไรทุกอย่างโชว์ visual อะไรต่างๆที่ค้างของเราทั้งหมดด้วย
อย่าให้ค้างแบบเดิมรอบหน้าถ้าค้างก็สั่ง codex ไม่ก็ gemini ทำให้ก็ได้จะได้ไม่ต้องมีผม".
No robot today. Finish the RL vs planner run with timing, make every pending visual
(sim videos, charts, lab results; private media stays local), then the .staging moves.

## Doing now
RL full run in the background (detached PowerShell, survives this session):
`.local/rl_compare/run_rest.ps1`, log `.local/rl_compare/rl_rest.log` (UTF-16; read with
`Get-Content -Encoding Unicode`). Order: the 11 unfinished sets, then
come_and_cheer_left_v2/firmware_5mm last (restarts from round 1: no resume yet), then `--report`.
Ends with the line `ALL DONE`. Started 19:47 Bangkok, ~40 min per set, expect ~03:30.

## File status
Baseline: origin/claude/lab-robot-1028 0266cec.

| File | Change | State | Verification | Commit |
| --- | --- | --- | --- | --- |
| `handoff/tasks/pc-rl-visuals-1028.md` | new task file | done | n/a | this checkpoint |
| `docs/experiments/figures/lab_1028_pace_ladder.png` | chart of the A48-23 table | done | looked at it | this checkpoint |
| `docs/experiments/figures/rl_curve_come_and_cheer_left_v2_firmware_5mm.png` | partial RL curve (12 rounds) | done, redo after the run | looked at it | this checkpoint |

Local only (never git): `.local/visuals/make_charts.py` (rerun from code/: `python .local/visuals/make_charts.py docs/experiments/figures`),
`.local/rl_compare/run_rest.ps1`, `.local/sim_videos/` (nong_sim record), `.local/rl_compare/**` videos.

## Facts found
- Main tree E:\final_proj\mice\code is on branch claude/lab-robot-1028 with 58 uncommitted files (not mine; see lab-robot-1028.md).
- run.py skips only sets whose round_20/round.json exists; `--dance/--scenario` pick one set.
- Planner on the board at safeDps 60 (left_v2): music variant 475 s, shape variant 646 s for a 158 s song,
  so on the music clock its bone error is ~45 deg while RL is ~19 deg; on shape only the planner wins (8.7-11.2 vs 17.5).

## Done
- A51-1 sections 2-3 (moves only, nothing deleted): flat `.staging` -> `.staging\main`, 21 `.staging-X` -> `.staging\X`,
  landed.jsonl + trees.txt moved, build.bat/scratch/_photo_test/_video_test -> `_out\`. No write in any tree for 3 h before.
  `.staging-watch.lock` left at the root on purpose. `tools/layout.py check`: only local-only items left.
- Sections 1 and 4 (pull, systems build, exe rebuild) were done by the lab session today (b7005d8 is in HEAD).

## Next
1. When `ALL DONE` is in rl_rest.log: `python .local/visuals/make_charts.py docs/experiments/figures`, add the
   training times (per set, per round) and the results table (.local/rl_compare/results.md) to
   docs/experiments/experiment-records.md, commit, push this branch.
2. Sim videos: `.local/sim_videos` (come_and_cheer_left v2 vs v5 with music); add the paths to the summary.
3. If this session is gone: Codex can do 1-2 from this file alone.

## Blocked
- Nothing. Resume-from-checkpoint is a cloud thread's work; until it merges, set 12 restarts from round 1.
