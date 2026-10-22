# Clear Thai voice, no cut last word, manner per event

Owner: claude:xdlrot (PC session, thread "voice clear")
Updated: 2026-10-22 14:45 +0700
Branch: claude/project-thread-xdlrot
Last commit: (see git log of the branch)
Plan: A45-26

## Goal
User 2026-10-22: *เอาแบบตั้งได้ว่างานแต่ละงานจะเป็นโทนไหน เสียงยังดูเป็น AI เกินไป
เสียงรวบเกินฟังไม่รู้เรื่อง เอาแบบเสียงสำเนียงไทยฟังชัด ภาษาอื่นด้วย* and
*คำสุดท้ายจบไวไป ไม่มีลากเสียง ออกแค่ครึ่งคำแล้วหายไป*.

## Doing now
- Waiting on the Thai bench (`scratch/voice-clear-2026-10-22/bench.py`, 12 candidates x 6
  lines x 2 seeds, heard by the helper's /transcribe on 8767). Then English/Japanese/Chinese
  (`bench_other.py`). Approach: lowest CER with the last word heard wins; clarity beats feeling.
  Files to change after: `config/voice_providers.json` feeling `tune` (temperature, split).
  Early result: temperature 0.3 CER 0.05 vs 0.11 at 0.8 (11 clips).

## Done (on the branch, not merged)
- Cause of the cut last word, measured: feeling-voice clips end right on the last
  sound (16 of 30 under 100 ms after it, one at full volume). `tts_spark/server.py`
  now adds a quiet lead + tail (`to_wav`), can split at Thai spaces with a pause
  (`pieces`), and takes per-request `tune` (TUNE dict). Defaults in
  `config/voice_providers.json` feeling speak job `tune`; `providers.feeling_speak`
  sends it; `service.py` puts the tune in the cache name (old cut clips never replay).
- Each scenario (event) has its own speaking manner: `scenStyle` on the Voice page
  (app.js fillScenarioStyle, add/collect/try). Backend already read scenario.style.
- QC: new `check_voice_tail` (5 sabotages caught). Related checks green.
- The LIVE feeling server on 8779 is currently the BRANCH's server.py (started from
  this worktree for the bench). Deploy restarts it from main.

## Next
1. Bench results: `scratch/voice-clear-2026-10-22/bench.jsonl` (Thai, 12 candidates,
   heard by the helper's own /transcribe) and `bench_other.jsonl` (en/ja/zh Edge
   voices). Pick the clearest Thai default: set `tune` (temperature/split) and/or the
   manner `prefer` order; set per-language voices if one is clearly clearer.
2. Optional: `raw_baseline` checkpoint is downloaded (CER 0.055 vs 0.09 in the model
   card); bench it: restart server with `--checkpoint raw_baseline`, `python bench.py baseline`.
3. Push, send coordinator branch + head for PR/full QC/merge; deploy on PC
   (systems build, exe, restart hub + helper, 50-case replay).

## Blocked
- Nothing. Human ear still needed to judge "sounds less AI".
