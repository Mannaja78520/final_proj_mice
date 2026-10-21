# Voice that sounds closer to a person, with a choosable manner

Owner: claude:10210423-30cf (PC session)
Updated: 2026-10-21 09:30 (Bangkok)
Branch: claude/project-thread-5ylnwy
Last commit: dcb1412 (feature); branch head see `git log -1`
Plan: A45-25

## Goal
Tones: polite, friendly, playful, sweet (อ้อน), plus real emotion and Thai speech melody (ทำนองเสนาะ).

## Done
- Manners are data: `config/voice_styles.json` (polite, friendly, playful, coaxing, recite).
  Each speak service's real ability is `styles` in `config/voice_providers.json`:
  Gemini = instruct (told in words, Thai supported per Google docs 2026-10-21),
  Edge/Azure = prosody (speed + pitch only), Windows voice = none.
- Request > scenario > tts.style; empty = as before. Manner is in the cache name; the page's
  fast device voice is off while a manner is chosen; /say sends X-Voice-Style; GET /styles.
- Voice page: Speaking manner picker + plain note on what the current service can do.
- `check_voice_styles` 28/0 (7/7 sabotages), fast-voice modes in voice_conversation (1/1).
- Real Edge samples of every manner, cold/cached timing, pitch: PC only,
  `scratch/voice-a45-24-2026-10-21/styles/` + README table. They are speed/pitch only.

## Next
1. The user listens to `styles/*.mp3` and picks a permanent manner (or none) -> set tts.style.
2. With a Gemini key: listen to each manner via Gemini; until then Gemini manner is UNTESTED.
3. True ทำนองเสนาะ is not supported by any tested service; do not claim it.

## Blocked
- User decision (permanent manner) and keys (Google/Groq sign-in paused by the user).
