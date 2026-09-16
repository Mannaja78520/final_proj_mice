# Panel review - 2026-08-23 15:53

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
A20-7 finished, QC-green, before promote. Speech-to-text added to the voice helper apps/voice/service.py (listen() lazy-loads faster_whisper under the same GPU lock as the LLM; language = request hint else store stt.language else detected per utterance; per-language bias words from config/voice.json languages map, only when language already known; condition_on_previous_text=False). New POST /transcribe takes raw audio bytes beside /ask. Hub gates /api/voice/transcribe in hub_auth.py and proxies bytes unchanged. Page apps/voice/index.html gained Pro-designed press-to-talk. Bench apps/voice/bench/run_bench.py made language-generic via CHAR_LANGS. Check qc/checks/check_voice_stt.py fakes whisper in-process for kwargs proof.
Read those files. What is NOT true or breaks first? Thread-safety of the shared lock with the generator consumption, temp-file handling on Windows, MediaRecorder blob shape vs helper expectations, health parts consumers, bench CHAR_LANGS correctness.
Answer in at most 25 lines.

**Files.** app.json, bench/cases.json, bench/run_bench.py, index.html, qa_data.json, service.py
**Cost.** 281447 tokens across 3 models

## The head reviewer (gemini-3.1-pro-high)

 - **real** `apps/voice/bench/run_bench.py:164` VOICE_DEFAULTS missing other languages, --prepare crashes on unmapped lang without ttsVoice.
 - **real** `apps/voice/index.html:94` parts display omits p.stt, header status line hides recogniser state.
 - **fine** `apps/voice/service.py:123` lock is fine.
 - **fine** `apps/voice/service.py:131` tempfile is fine.
 - **fine** `apps/voice/index.html:131` blob is fine.
 - **fine** `apps/voice/bench/run_bench.py:45` CHAR_LANGS is fine.

## What each model said

### gemini-3.1-pro-high  _(434.1s, 94923 tokens)_

 - **unchecked** `:` Shared lock fine.
 - **unchecked** `:` Windows temp fine.
 - **unchecked** `:` Blob shape fine.
 - **unchecked** `:` index.html:94, drops p.stt, UI never shows speech-in status.
 - **unchecked** `:` CHAR_LANGS is fine.

### gemini-3.7-flash-high  _(81.2s, 153634 tokens)_

 - **real** `apps/voice/index.html:94` parts display omits p.stt, header status line hides recogniser state.
 - **real** `apps/voice/bench/run_bench.py:164` VOICE_DEFAULTS missing other languages, --prepare crashes on unmapped lang without ttsVoice.
 - **real** `config/voice.json:19` stt lacks languages map, bias words never pass to whisper.
 - **fine** `apps/voice/service.py:123` lock is fine.
 - **fine** `apps/voice/service.py:131` tempfile is fine.
 - **fine** `apps/voice/index.html:131` blob is fine.
 - **fine** `apps/voice/bench/run_bench.py:45` CHAR_LANGS is fine.
