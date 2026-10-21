# Voice fixes from the real test (Thai/English mix, reply language, read-aloud, new poems)

Owner: claude:10210423-30cf (PC session)
Updated: 2026-10-21 09:30 (Bangkok)
Branch: claude/project-thread-5ylnwy
Last commit: 94f6571 (feature); branch head see `git log -1`
Plan: A45-24

## Goal
Fix what the user's real voice test found:
- Thai mixed with English is sometimes misheard so the answer is wrong, especially restroom / parking.
- Thai first, then "answer in English": it still answers in Thai.
- "Read this English text exactly": the model inserts the user's name.
- "Write a new poem about <topic>": it answers with a greeting or reuses an old poem.

## Done
- Rules are data: `config/voice_intents.json` (replyLanguage, readAloud, compose, loanwords,
  codeSwitch), read by `apps/voice/intents.py`; wired in `apps/voice/service.py` (/ask, faq_best,
  _code_switch, _language_share, compose). New registry job `compose` (sameAs think) in
  `config/voice_providers.json`, so verse can use a stronger service than answers.
- Real-audio replay on the PC of all 50 audit cases (31 typed, 19 spoken): 50/50, with one
  stricter rule added (a Thai question keeps a Thai answer). Evidence (PC only, git-ignored):
  `scratch/voice-a45-24-2026-10-21/README.md`, `run-8777/verdict.json`.
- `check_voice_intents` 41/0; sabotage 14/14 caught. All voice checks 617/0.

## Next
1. After merge: pull main on the PC, restart the Voice helper (8767) from the main tree,
   rerun `python scratch/voice-a45-24-2026-10-21/regress.py http://127.0.0.1:8767` (50/50 expected).
2. Real microphone test with a person (synthetic clips are not human speech).
3. New verse: the local 0.5B model fails every time and now says sorry honestly. A good Thai
   verse needs a stronger `compose` service (Voice page, Writing verse) = needs a key.

## Blocked
- Keys: the user paused Google/Groq sign-in. Rhyme/meter of a verse is not checked, only shape.
