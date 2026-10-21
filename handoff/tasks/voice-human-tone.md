# Voice that sounds closer to a person, with a choosable manner

Owner: claude:10210423-30cf (PC session)
Updated: 2026-10-21 15:05 (Bangkok)
Branch: main (PR #45, ed1a215)
Last commit: ed1a215
Plan: A45-25

## Goal
Tones: polite, friendly, playful, sweet (อ้อน), plus real emotion and Thai speech melody (ทำนองเสนาะ).
User 2026-10-21: "ทำจริตเสียงด้วยเลยรออะไร" - do it now, do not wait for a key.

## Done
- Manners are data: `config/voice_styles.json` (polite, friendly, playful, coaxing, recite),
  each with words (instruct), speed/pitch (prosody) and a feeling (emotion). `recommended: friendly`.
- Each speak service's real ability is `styles` in `config/voice_providers.json`:
  feeling (this PC) = emotion, Gemini = instruct (untested, no key), Edge/Azure = prosody, Windows = none.
- NEW speak service `feeling`: SparkTTS-Thai-Emotion-Control (CC BY-NC-SA 4.0) behind
  `apps/voice/tts_spark/server.py`, own venv in `.runtime` (git-ignored), installed by
  `python apps/voice/tts_spark/setup.py` (3.8 GB). Helper starts it at boot / first use; while it
  loads, Edge speaks. `prefer: ["feeling"]` puts it first under a manner. Thai only.
- Speed: one captured CUDA graph per token, 50 -> 5.5 ms; a ~3 s Thai line in 2.5-4.3 s cold,
  0.02-0.06 s cached (helper, PC, 2026-10-21). Edge cold was 4.8-5.2 s for the same lines.
- Words heard back by the Thai whisper: 0.6-1.0 (15 fresh lines; low ones show whisper adding
  text that is not there, and one possibly odd ending: needs a human ear).
- Two automatic emotion judges were no better than chance on labelled THAI-SER clips (19%):
  whether each feeling sounds right is NOT verified by machine.
- Fixed on the way: per-thread manner record (sweep overwrote X-Voice-Style); build stamp and
  exe now skip `.runtime`/`tts_cache` (hub said 6839 files changed; exe would carry 3.8 GB).
- Samples (PC only, git-ignored): `scratch/voice-a45-24-2026-10-21/feeling/`, `feeling-fresh/`,
  `emotion/` (raw server, 5 feelings), `styles/` (Edge speed/pitch only), README there.

- Deployed on the PC 2026-10-21 14:56: exe rebuilt (stale:false, 10.8 MB: tts_cache no longer packed),
  hub + Voice helper restarted, tts.style = friendly in the live voice.json (user delegated the pick;
  backup of the old file in scratch/deploy-a45-2026-10-21). The helper started the feeling voice
  itself. Replay of the 50 audit cases vs 8767: 50/50. Live Thai line 3.6 s by feeling, English by Edge.
- GPU after deploy: 10.8 of 12.2 GB used (friend app + whisper + LLM + feeling): watch for out-of-memory.

## Next
1. A person listens to `feeling-fresh/`, `feeling/`, `emotion/` samples: does each feeling sound right?
   Change the manner on the Voice page (Speaking manner) if not.
2. With a Gemini key: hear the instruct path (A45-10 keys).
3. True ทำนองเสนาะ: no tested service does it; do not claim it.

## Blocked
- Human listening judgement; Gemini key (user paused sign-in) for the instruct path.
