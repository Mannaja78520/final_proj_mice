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
- Handing the branch to the coordinator for PR + full QC + merge. Then deploy on the PC.

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

- Bench done (scratch/voice-clear-2026-10-22/README.md, listen/ for the ear). Picked by
  whisper letters wrong: Edge Premwadee -10% 2.9% (new default, `config/voice.json`
  tts.rate -10%), feeling best 6.1% at temperature 0.3 (tune), old feeling 11.2%.
  Splitting at spaces was worse (14%): split stays 0. Other languages already clear
  (en/zh 0-2%, ja 5.6% for every voice): voices unchanged.
- `voice_styles.json` prefer [] (clarity first), a manner may carry its own `prefer`
  (service.speak_order); manner speeds lowered (friendly 0, playful 3, sassy 4).
  check_voice_styles reads expected values from the data now.

## Next
1. Merge (coordinator: cloud PR, full QC).
2. Deploy on PC: `python tools/systems.py build`, rebuild exe with the spec, restart hub +
   voice helper + feeling server (8779 is running the branch file now), set live
   `config/voice.json` tts.rate -10% (live has style friendly), 50-case replay
   (scratch/voice-a45-24-2026-10-21/regress.py), hear one live Thai line: tail present.
3. Optional: bench `raw_baseline` (downloaded) if the feeling voice should become default.

## Blocked
- Nothing. Human ear still needed to judge "sounds less AI".
