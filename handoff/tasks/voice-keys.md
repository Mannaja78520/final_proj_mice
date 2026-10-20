# Gemini and Groq keys for voice

Owner:
Updated: 2026-10-21 04:20 (Bangkok)
Branch: main
Last commit: c859601
Plan: A45-10

## Goal
Use Gemini to think and Groq to hear, with local as the backup.

## Done
- Voice page "Who does it" tab takes the keys; they are saved in the git-ignored main_python/voice_keys.json (PR #35).

## Next
1. User signs in to Google AI Studio and Groq and makes the keys (only the user can).
2. Enter them on the Voice page, put gemini first for think and groq first for hear.
3. Ask 3 questions by voice; check each answer says by=gemini / by=groq.

## Blocked
- The user's own Google/Groq sign-in. Do not change the provider order before the keys work.
