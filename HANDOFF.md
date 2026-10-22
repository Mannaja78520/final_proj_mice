# HANDOFF — read this first

The one place any AI (Claude, Codex/GPT, Gemini) starts from. This file is
stable: rules, where things are, how to hand off. Open work lives in one file
per task under `handoff/tasks/`, so agents working in parallel never edit the
same file. History is in `docs/BRIDGE.md` and the STATE block of
`docs/PLAN.html`; you do not need to read them to start.

## How to pick up

1. Open work = the files in `handoff/tasks/` on main, plus open PRs and
   unmerged branches (each branch carries its own task file).
   `python tools/handoff.py list` shows both; no tool needed to read the files.
2. Take the task the user named. Otherwise take a file whose `Owner:` line is
   empty or whose `Updated:` is old and has no open PR; write your agent id in
   `Owner:` first.
3. Read that one task file, then work.

## How to hand off (every AI, every time)

- Your task, your file: `handoff/tasks/<task-or-branch>.md`
  (`python tools/handoff.py new <name> "<title>"`, or copy `handoff/TEMPLATE.md`;
  `take <name> <agent>` claims it). Edit only your own file, on your own branch.
- WHILE you work, not only at the end (user 2026-10-22: any AI can run out
  mid-task). BEFORE each step write `## Doing now` (what you are about to do,
  the files, the approach) and push; AFTER it move that to Done, update Next,
  Blocked, Last commit and Updated, and push a WIP commit to your branch.
  Before you end, stop for any reason, or when usage runs low: the same.
- Task fully done: delete its file in the PR that merges the work.
- Do not create other handoff files. Edit this file only when a rule or a
  path below changes, or a big feature lands (Built so far).
- Plan rows still apply: `python tools/plan.py doing|done|note <id> ...`.

## Save tokens (user 2026-10-21)

Every line printed stays in the context and is paid again on every later call.
- QC: `python qc/run_qc.py --quiet <check names>` while working (only the
  checks for the files you touched; failures + one summary line on screen,
  full log in `qc/last_run.log`, read it with grep/tail). Full
  `python qc/run_qc.py --quiet` once, right before merge.
- Reading: never whole big or generated files (docs/BRIDGE.md, docs/PLAN.html,
  app.js, reports/*.json, logs). grep/rg, then a line range; `head`/`tail`.
  Status: `python tools/handoff.py list`, `python tools/plan.py show`.
- Size: this file and each task file stay under 150 lines
  (check_handoff_first holds it). BRIDGE over ~400 lines: move old entries to
  docs/bridge_archive/.
- Sessions: a new task starts a fresh session; effort high, medium for small
  tasks. Wide searches go to a subagent so the results stay out of the main
  context.

## Several agents in one tree at once (the PC)

Claims, the shared mutex and "one QC driver at a time" are in
`docs/COORDINATION.md`. `docs/BRIDGE.md` is the claim log (CLAIM / RELEASE),
not the state: the state is your task file.

## Where things are


- Repo: https://github.com/Mannaja78520/final_proj_mice (PUBLIC). PC copy: `E:\final_proj\mice\code`.
- Hub (MiceHub) http://127.0.0.1:8642, log in as admin yourself. Exe: `python -m PyInstaller --clean --noconfirm MiceHub.spec` (always the spec). After a pull: `python tools/systems.py build`.
- Nong Studio http://127.0.0.1:8642/studio/. Web sources `nong/main_python_set_nong/web/app_parts/*.js` -> `python tools/build_web.py`.
- Voice helper port 8767, our faces watcher 8769 (`python -u apps/faces/service.py --partner reconize --port 8769`).
- Friend's Face_Regonize: backend 8000 (start with `E:\final_proj\mice\Face_Regonize\Start Reconize.vbs`), web 5173.
- Robot nong: ESP32, RS485 on COM21 (bus id 67), joins the PC hotspot "manny", flashed over WiFi. Firmware `pio run -e mice_nong`. Module page http://nong.local/ (type the http://).
- QC: `pip install pyserial psutil platformio`, `pio run -e mice_nong`, then `python qc/run_qc.py --quick` / full `python qc/run_qc.py`. QC rewrites reports/*.json: never `git add -A` after QC.

## Hard rules

1. Never edit anything under `E:\final_proj\mice` except `code`. Face_Regonize and All-Jao-Games are the friend's repos: read, `git pull --ff-only`, run their start scripts only. Their problems go on a list for the friend.
2. Public repo: never commit API keys (`main_python/voice_keys.json` stays git-ignored), passwords, thesis files, model files, videos or the friend's code.
3. No thesis work (dropped).
4. No manual steps for the user: log in, rebuild, start the friend's backend yourself.
5. Never skip or disable a test. Branch, PR, merge only when full QC is green. Say what was not tested on real hardware.
6. Leave the PC's git stashes and the friend's backup branch/stash alone. Never delete `E:\final_proj\mice\_to_delete_2026-10-10` unless the user writes "ลบ".
7. No service fixed to one provider: hear/think/speak each choose cloud or local per situation; the next is used only when the chosen one fails. Thai first, main language changeable per event.
8. Dynamic and easy to change (user 2026-10-21): settings, lists and choices
   live in config/data files (`config/*.json`, registries), not in code, so the
   next one is added or changed without a code edit. One source, no copies.
   Applies to new work; do not refactor old code only for this.

## Built so far

As of main c859601 (2026-10-21): all merged, PRs #1-#40. Verified on the PC:
- Faces: photo test 16/16; face history follows the friend's node_id/seq cursor (A45-16); friend's server now runs dual/CUDA concurrent inference (A45-17).
- Studio: save to robot, robot settings, palm/back per hand (fake robot only); Video tab (YouTube, public Google Drive, Dropbox, direct links) makes moves; real dance video checked (A45-19).
- Voice (PR #39, #40): login on every voice route, no name blink on 429, 30 s speech, Thai/English/Japanese/Chinese hearing and answers, a fast installed-voice option that races server speech after 650 ms. Cached answer-to-audio 0.2-0.4 s; new Thai phrasing can take ~5 s. Detail: `docs/voice-validation-2026-10-20.md`.
- Show/timeline/music/SD upload played on the real nong 2026-10-12.
