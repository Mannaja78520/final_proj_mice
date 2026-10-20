# Voice fixes from the real test (Thai/English mix, reply language, read-aloud, new poems)

Owner: PC session (Remote Control)
Updated: 2026-10-21 04:30 (Bangkok)
Branch: (PC session names it)
Last commit: c859601
Plan: A45-24

## Goal
Fix what the user's real voice test found:
- Thai mixed with English is sometimes misheard so the answer is wrong, especially restroom / parking.
- Thai first, then "answer in English": it still answers in Thai.
- "Read this English text exactly": the model inserts the user's name.
- "Write a new poem about <topic>": it answers with a greeting or reuses an old poem.

## Done
- Nothing yet. Sound samples and raw results for regression checks are on the PC only (git-ignored):
  scratch/voice-mixed-acceptance-2026-10-21/README.md and review.json.

## Next
1. Turn each case into a regression check from those samples, prove it red first.
2. Fix; sabotage each fix; review; quick + full QC; PR and merge.

## Blocked
- Nothing. Rule: never loosen a test's pass mark to hide a miss. 7245/0 from before does not cover these cases.
