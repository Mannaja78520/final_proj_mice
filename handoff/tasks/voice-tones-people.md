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
- Inventing speakers with the Thai feeling model (prompt stops at <|start_global_token|>,
  the model writes its own 32 speaker tokens): `scratch/voice-human-2026-10-22/gen2.py`,
  16 female + 16 male, 3 lines each at temperature 0.3, in `cand/`. Then judge CER + pitch
  (`judge.py`) and keep the clearest 3 female + 3 male as `config/voice_people.json`.
- Code done, not committed yet: server.py `speaker` + `tempo` (ffmpeg atempo), providers
  feeling_speak person/tempo, service people()/person()/tempo_of, voices_by_lang lists them,
  say() puts feeling first for a "person:<id>" voice with a same-gender Edge backup.

## Next
1. voice_styles.json `featured` (3 tones) + `speeds` (normal +0%, fast); UI quick block on
   the Voice tab: 3 tone cards (click = default, saved), speed chips, voice list female/male.
2. Bench fast speed CER for Edge and the saved voices; samples to scratch for the user.
3. QC check (check_voice_people), PR via coordinator, deploy.

## Blocked
- Nothing. "Sounds less AI" only a human ear can judge.
