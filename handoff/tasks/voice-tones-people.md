# Three tones to click, a fast speed, male and female voices that sound less AI

Owner: claude:xdlrot (PC session, thread "voice clear")
Updated: 2026-10-22 15:12 +0700
Branch: claude/project-thread-xdlrot
Last commit: (see branch)
Plan: A45-28

## Goal
User 2026-10-22: *โทนแบบเลือกได้ คลิกเป็น default ได้ซัก 3 โทน, ขอมีแบบเร็วได้ด้วย,
เลือกเสียงได้ทั้งชายและหญิง; default clear ยังดูเป็น AI; เร็วขึ้นได้แต่ไม่รวบคำ -
ปัญหาคือรวบคำจนฟังไม่ออก ไม่ใช่เร็วไป*. So: do NOT fix by slowing; normal + fast speed,
every word clear at both (measure CER at fast too).

## Doing now
- Handing branch to the coordinator for PR + full QC + merge (main merged in, voice checks
  1104/0 locally). Then deploy on the PC together with PR #50 (gestures).

## Done (branch)
- 6 saved voices in config/voice_people.json (refine bench: women 4.9/6.7/7.2%, men
  7.3/7.7/8.2% letters wrong; Edge Premwadee 5.4%, Niwat 0%). Fast +20%: Edge same CER as +0%.
- server speaker + tempo, providers person/tempo/temperature, service people/person/
  tempo_of/voice_gender/gender_words/agree_text, /say `agree`, style_extra fallback.
- Voice tab quick tiles (tone, speed, voice per language, women/men), click saves.
- check_voice_people (sabotage 10/10); check_voice_answers/styles stub voice_gender.
- User's "characters with own folders + default folder" = codex A45-27, already merged.

## Next
1. After merge, deploy: pull, systems build, exe, restart hub + helper + feeling server,
   live tts.rate +0%, open Studio Sequence once (PR #50 gestures), replay 50, send samples
   `scratch/voice-human-2026-10-22/refine/` to the user.
2. Delete this task file in a follow-up once deployed.

## Blocked
- Nothing. "Sounds less AI" only a human ear can judge.
