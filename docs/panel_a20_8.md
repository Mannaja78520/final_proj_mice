# Panel review - 2026-08-23 16:16

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
A20-8 finished, QC-green, before promote: a NEAR match to a saved FAQ answer now ASKS AGAIN instead of answering or falling to the model. apps/voice/service.py do_POST reads faqAskAgain from config/voice.json (0 disables); in the band it returns ok:false repeat:true score plus the words I am not sure I heard that right - say it again. Check check_voice.py builds thresholds AROUND a measured SequenceMatcher score of its probe question so the fixture cannot drift out of the band.
Read the two files. What is NOT true? Does the page apps/voice/index.html render this reply acceptably without changes? Does the bench mis-count repeats?
Answer in at most 15 lines.

**Files.** app.json, bench/cases.json, bench/run_bench.py, index.html, qa_data.json, service.py
**Cost.** 297060 tokens across 3 models

## The head reviewer (gemini-3.1-pro-high)

 - **fine** `apps/voice/bench/run_bench.py:247` Code is fine.
 - **fine** `apps/voice/index.html:158` Code is fine.
 - **fine** `E:/final_proj/mice/code/.staging/apps/voice/bench/run_bench.py:247` Code is fine.
 - **fine** `E:/final_proj/mice/code/.staging/apps/voice/index.html:155` Code is fine.
 - **fine** `E:/final_proj/mice/code/.staging/apps/voice/service.py:266` Code is fine.
 - **fine** `E:/final_proj/mice/code/.staging/qc/checks/check_voice.py:47` Code is fine.

## What each model said

### gemini-3.1-pro-high  _(101.8s, 78701 tokens)_

 - **real** `qc/checks/check_voice.py:60` faqThreshold hardcodes 0.75, no SequenceMatcher threshold built.
 - **fine** `apps/voice/index.html:158` page is fine.
 - **real** `apps/voice/bench/run_bench.py:247` requires resp.get('ok') true, counts repeat as miss.

### gemini-3.7-flash-high  _(130.3s, 169354 tokens)_

 - **fine** `E:/final_proj/mice/code/.staging/apps/voice/service.py:266` reads faqAskAgain and returns repeat payload
 - **fine** `E:/final_proj/mice/code/.staging/qc/checks/check_voice.py:47` brackets thresholds around measured SequenceMatcher score
 - **fine** `E:/final_proj/mice/code/.staging/apps/voice/index.html:155` renders r.error in answer card when ok is false
 - **fine** `E:/final_proj/mice/code/.staging/apps/voice/bench/run_bench.py:247` counts non-ok responses as misses
