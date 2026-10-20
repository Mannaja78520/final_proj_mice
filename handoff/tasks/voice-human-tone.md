# Voice that sounds closer to a person, with a choosable manner

Owner: PC session (Remote Control)
Updated: 2026-10-21 04:30 (Bangkok)
Branch: (PC session names it)
Last commit: c859601
Plan: A45-25

## Goal
Tones: polite, friendly, playful, sweet (อ้อน), plus real emotion and Thai speech melody (ทำนองเสนาะ).

## Done
- baseline / gentle / brighter.mp3 samples exist, but they only change speed and pitch, not real emotion.
- Cache and "backup voice must not override the chosen manner" notes: scratch/voice-human-tone-2026-10-21/HANDOFF.md (PC only).

## Next
1. Check what each provider can really do (Thai with English mixed in, meaning kept) before picking a method.
2. Listen to / check the generated sound itself, not just that a button exists.
3. Time new sound and cached sound.

## Blocked
- The user has not picked a permanent tone; Google/Groq sign-in is paused.
- Keep per-situation provider choice; never lock every job to one provider.
- Do not claim "natural in every case" or "supports ทำนองเสนาะ" without evidence that matches the claim.
