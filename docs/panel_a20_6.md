# Panel review - 2026-08-23 15:13

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
A20-6 voice test bench, just built, QC-green: apps/voice/bench/cases.json (25 questions, expected text + expected saved answer) and apps/voice/bench/run_bench.py (prepare via edge-tts, measure WER/CER + answer-hit rate + latency against the helper apps/voice/service.py, honest degradation when faster_whisper or audio missing). Check qc/checks/check_voice_bench.py boots the real helper FAQ-only and asserts an exact 24/25 hit count with one answer deliberately swapped.
Read those four files. What is NOT true or will break first? Wrong numbers, encoding traps on Windows, timing pitfalls, cases that cannot ever pass?
Answer in at most 25 lines.

**Files.** cases.json, run_bench.py
**Cost.** 427617 tokens across 3 models

## The head reviewer (gemini-3.1-pro-high)

 - **unchecked** `:` apps/voice/bench/run_bench.py:124 | real | `model` is undefined, raises `NameError` crashing execution when STT runs.
 - **unchecked** `:` qc/checks/check_voice_bench.py:118 | real | `finally` block calls `proc.terminate()` unconditionally, raises `AttributeError` if `boot_helper` returns `None`.
 - **unchecked** `:` apps/voice/bench/run_bench.py:209 | real | `if got:` evaluates false on empty STT output, recording a perfect typed run instead of STT failure.
 - **unchecked** `:` apps/voice/bench/run_bench.py:172 | real | `ask` sets `timeout=200`, causing 25 socket requests to hang up to 5000s before failing.
 - **unchecked** `:` apps/voice/bench/run_bench.py:110 | real | `err_rate` compares case and punctuation exactly, inflating English WER for accurate transcripts.
 - **unchecked** `:` apps/voice/service.py:53 | real | `faqs()` reads JSON synchronously, blocking execution multiple times per HTTP request.
 - **unchecked** `:` qc/checks/check_voice_bench.py:71 | real | hardcodes substring `'25 cases'`, breaking QC when cases are added to `cases.json`.
 - **unchecked** `:` qc/checks/check_voice_bench.py:32 | real | `PORT` and `DEAD` sample at module load, risking collision before `boot_helper` binds.

## What each model said

### gemini-3.1-pro-high  _(233.6s, 121364 tokens)_

 - **real** `apps/voice/bench/run_bench.py:124` `model` is undefined, raises NameError crashing execution when STT runs.
 - **real** `apps/voice/bench/run_bench.py:209` `if got:` evaluates false on empty STT output, recording a perfect typed run instead of STT failure.
 - **real** `apps/voice/bench/run_bench.py:110` `err_rate` compares case and punctuation exactly, inflating English WER for accurate Whisper transcripts.
 - **real** `apps/voice/bench/run_bench.py:61` `registry.load(CASES)` uses system default encoding, mangling Thai text on Windows and breaking FAQ matching.
 - **real** `qc/checks/check_voice_bench.py:90` mock FAQ writes the same mangled data, matching identical mojibake and falsely passing the test.
 - **real** `apps/voice/service.py:53` `faqs()` reads JSON from disk synchronously, blocking execution multiple times per HTTP request.

### gemini-3.7-flash-high  _(320.2s, 237878 tokens)_

 - **unchecked** `:` [`run_bench.py:124`](file:///E:/final_proj/mice/code/.staging/apps/voice/bench/run_bench.py#L124): [`make_stt`](file:///E:/final_proj/mice/code/.staging/apps/voice/bench/run_bench.py#L113) passes undefined variable `model` to `WhisperModel`, raises `NameError` as soon as STT is enabled and `faster_w
 - **unchecked** `:` [`check_voice_bench.py:118`](file:///E:/final_proj/mice/code/.staging/qc/checks/check_voice_bench.py#L118): `finally` block calls `proc.terminate()` unconditionally, raises `AttributeError` if [`boot_helper`](file:///E:/final_proj/mice/code/.staging/qc/checks/check_voice_bench.py#L46) returns `None`
 - **unchecked** `:` [`run_bench.py:172`](file:///E:/final_proj/mice/code/.staging/apps/voice/bench/run_bench.py#L172): [`ask`](file:///E:/final_proj/mice/code/.staging/apps/voice/bench/run_bench.py#L162) sets `timeout=200` per request, causing 25 unresponsive socket requests to hang up to 5000s before failing.
 - **unchecked** `:` [`check_voice_bench.py:71`](file:///E:/final_proj/mice/code/.staging/qc/checks/check_voice_bench.py#L71): hardcodes substring `"25 cases"` in assertion, breaking QC when additional cases are added to [`cases.json`](file:///E:/final_proj/mice/code/.staging/apps/voice/bench/cases.json).
 - **unchecked** `:` [`run_bench.py:213`](file:///E:/final_proj/mice/code/.staging/apps/voice/bench/run_bench.py#L213): prints `SKIP <id> no recording` on missing audio but falls through and queries helper with typed text.
 - **unchecked** `:` [`run_bench.py:127`](file:///E:/final_proj/mice/code/.staging/apps/voice/bench/run_bench.py#L127): `WhisperModel.transcribe` crashes on Windows if system `PATH` lacks `ffmpeg` for MP3 audio generated by [`prepare`](file:///E:/final_proj/mice/code/.staging/apps/voice/bench/run_bench.py#L133).
 - **unchecked** `:` [`cases.json:17`](file:///E:/final_proj/mice/code/.staging/apps/voice/bench/cases.json#L17): comment specifies audio path `bench/wavs/`, but [`run_bench.py:37`](file:///E:/final_proj/mice/code/.staging/apps/voice/bench/run_bench.py#L37) saves to and loads from `bench/audio/`.
 - **unchecked** `:` [`check_voice_bench.py:32`](file:///E:/final_proj/mice/code/.staging/qc/checks/check_voice_bench.py#L32): `PORT` and `DEAD` are sampled once at module load, risking collision before [`boot_helper`](file:///E:/final_proj/mice/code/.staging/qc/checks/check_voice_bench.py#L46) binds.
