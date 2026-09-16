# Panel review - 2026-08-23 15:34

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
The voice helper apps/voice/service.py (FAQ-first HTTP service, hub proxies it) grows LOCAL speech-to-text: faster_whisper, imported lazily like its LLM half, model name from config/voice.json so the bench apps/voice/bench/run_bench.py can measure small vs medium vs large-v3 on the lab PC. Rule from the plan: NOT Thai-only - language comes from the store or is detected, never hardcoded; a second added language must be ONE entry in the store, zero code changes.
Three design choices to judge:
1. Endpoints: add POST /transcribe (audio bytes in, text+detected-language out) BESIDE the existing POST /ask, page calls both - versus one combined /converse doing listen+answer.
2. Language selection: store holds stt.language (empty = auto-detect each utterance) plus per-language bias words (whisper initial_prompt); request may override.
3. Failure honesty: no model installed or no mic audio must return plain words naming what to install, same style as the existing model-off error.
What breaks first? Answer directly, no plan, at most 20 lines.

**Files.** app.json, bench/cases.json, bench/run_bench.py, index.html, qa_data.json, service.py
**Cost.** 221132 tokens across 3 models

## The head reviewer (gemini-3.1-pro-high)

 - **real** `config/voice.json:19` stt hardcodes scalar language: 'th', file needs map of per-language initial_prompt entries.
 - **real** `apps/voice/bench/run_bench.py:104` tokens hardcodes lang == 'th' character split, other unsegmented languages use word split and miscalculate CER.
 - **real** `apps/voice/bench/run_bench.py:253` measure hardcodes ('en', 'WER') and ('th', 'CER'), bench hides error rates for other languages.
 - **real** `apps/voice/bench/run_bench.py:75` load_cases hardcodes ('th', 'en'), adding third language to bench/cases.json fails validation.
 - **fine** `apps/voice/service.py:158` This is fine.

## What each model said

### gemini-3.1-pro-high  _(125.7s, 71322 tokens)_

 - **real** `apps/voice/service.py:133` passing per-language initial_prompt fails when stt.language is empty; selecting correct bias requires mdl.detect_language() first which doubles latency
 - **real** `apps/voice/service.py:195` returning installation instructions for missing audio is wrong; overwrites correct logic asking user to speak again

### gemini-3.7-flash-high  _(50.2s, 100589 tokens)_

 - **real** `apps/voice/service.py:188` do_POST decodes JSON unconditionally; binary audio sent to POST /transcribe throws UnicodeDecodeError
 - **real** `apps/voice/service.py:158` health omits stt in parts; UI cannot show missing faster_whisper state on load
 - **real** `apps/voice/bench/run_bench.py:75` load_cases hardcodes ('th', 'en'); adding third language to bench/cases.json fails validation
 - **real** `apps/voice/bench/run_bench.py:104` tokens hardcodes lang == 'th' character split; other unsegmented languages use word split and miscalculate CER
 - **real** `apps/voice/bench/run_bench.py:253` measure hardcodes ('en', 'WER') and ('th', 'CER'); bench hides error rates for other languages
 - **real** `config/voice.json:19` stt hardcodes scalar language: 'th'; file needs map of per-language initial_prompt entries
