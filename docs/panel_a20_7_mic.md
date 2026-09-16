# Panel review - 2026-08-23 15:38

**Question.** ANSWER STYLE. Follow exactly. Going over budget is a failure, not thoroughness.

Terse. All technical substance stays, only fluff dies.

Drop: articles, filler (just/really/basically/simply), pleasantries (sure,
certainly, happy to, great question), hedging, praise, and every sentence that
says what you are about to do. No preamble. No restating my question. No summary
at the end. No headings, no tables, no emoji.

Fragments fine. Short synonyms: big not extensive, fix not implement a solution
for. Pattern: thing, action, reason. Then next step.

Keep exact and unchanged: file paths, line numbers, code, identifiers, CLI
commands, error strings, token and property names.

Never invent an abbreviation. Standard ones are fine: DB, API, HTTP, CSS, UART.

Every sentence must parse on the first read. Keep the subject when dropping it
makes the target unclear. Compression is for filler, never for meaning. Do not
write broken grammar: it costs the same and reads worse.

One finding per line: file:line, what is wrong, why it matters. If a thing is
fine, say fine in three words and move on. Do not list what you checked.

HARD LIMIT. The line budget in the question is a limit, not a target. Answers
over it are trimmed before anyone reads them, so anything past the budget is
work thrown away. Findings first, always: if you are cut off, the cut must land
on padding.

No plan, no checklist, no artifact file. Answer directly in the reply.
Say I do not know rather than guessing. Mark any assumption ASSUME.

WHEN YOU PROPOSE CODE:
Nothing hardcoded. A list belongs in data a person can edit, not in a source
file. If a fact is needed twice, one place reads it from the other. A new thing
should cost one new entry or one new file, never a new branch inside something
long. Prefer plain and obvious over clever: no layer that exists only to be a
layer. Say which file a person edits to add the next one.
DESIGN TASK, answer with FIND and REPLACE blocks only, exact strings from the file, no whole file.
The Voice page apps/voice/index.html has: header with status line, a down-card naming the fix, a ready card holding #parts line + textarea#q + Ask button + #wait span, an answer card. mice.css tokens only (--sp-*, --line, --r-md, --panel, --sunk, --mut), max-width 640px.
Add SPEECH INPUT for visitors: press-to-talk button near the textarea. Browser MediaRecorder, POST /api/voice/transcribe with the raw audio bytes, response {ok,text,language} or {ok:false,error}. On success put text into the textarea ready to send. States needed: idle (press to talk), recording (clearly visible, how to stop), sending (brief), transcript failed (plain words in the existing style). Touch target big, works at 360px, keyboard accessible, aria-live for state. Keep it SMALL - this page already has its look; one button plus minimal glue, no new palette, no icons beyond unicode.
Give FIND/REPLACE pairs for index.html only. Answer in at most 40 lines.

**Files.** index.html
**Cost.** 128037 tokens across 3 models

## The head reviewer (gemini-3.1-pro-high)

 - **fine** `apps/voice/index.html:63` It is fine.

## What each model said

### gemini-3.1-pro-high  _(90.7s, 36438 tokens)_

 - (nothing to report)

### gemini-3.7-flash-high  _(29.9s, 73099 tokens)_

 - **fine** `apps/voice/index.html:63` Speech input FIND/REPLACE provided.
