# Three tones to click, a fast speed, male and female voices that sound less AI

Owner: claude:xdlrot (PC session, thread "voice clear")
Updated: 2026-10-22 15:12 +0700
Branch: claude/project-thread-xdlrot
Last commit: (see branch)
Plan: A45-27

## Goal
User 2026-10-22: *โทนแบบเลือกได้ คลิกเป็น default ได้ซัก 3 โทน, ขอมีแบบเร็วได้ด้วย,
เลือกเสียงได้ทั้งชายและหญิง; default clear ยังดูเป็น AI; เร็วขึ้นได้แต่ไม่รวบคำ -
ปัญหาคือรวบคำจนฟังไม่ออก ไม่ใช่เร็วไป*. So: do NOT fix by slowing; normal + fast speed,
every word clear at both (measure CER at fast too).

## Doing now
- `scratch/voice-human-2026-10-22/refine.py` (running): shortlist 4 women + 4 men invented
  voices x temperature 0.3/0.15, fast tempo 1.1/1.2, and Edge Premwadee/Niwat at +0/+10/+20%,
  5 lines each, CER by the helper's whisper -> refine.jsonl. Then write
  `config/voice_people.json` (3 women + 3 men, clearest), set `speeds.fast` and tune temperature.

## Done so far (branch, WIP commits)
- server.py speaker per request + tempo (ffmpeg atempo); providers person/tempo; service
  people()/person()/tempo_of, voices_by_lang lists "person:<id>", say() feeling first + backup.
- voice_styles.json `featured` [friendly, polite, sassy] + `speeds`; config/voice.json rate back
  to +0% (user: the problem was slurring, not speed). styles_view sends featured/speeds/default.
- Voice tab quick block (toneTiles / speedTiles / voiceTiles, click saves): app.js fillQuick etc,
  style.css .tiles/.tile. New check qc/checks/check_voice_people.py (needs voice_people.json).

## Next
1. voice_people.json from refine results; run checks voice_people, voice_styles, voice_tail.
2. Sabotage-prove check_voice_people; web-page-check the Voice tab at 360/768/1440.
3. Push, coordinator PR + full QC + merge; deploy (exe, hub, helper, feeling server, replay).

## Blocked
- Nothing. "Sounds less AI" only a human ear can judge.
