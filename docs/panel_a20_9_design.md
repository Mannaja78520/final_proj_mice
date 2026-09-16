# Panel review - 2026-08-23 16:36

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
A20-9: LOCAL text-to-speech for the voice helper apps/voice/service.py. edge-tts (Microsoft cloud) and mpg123 playback both go away. Venue PC may have no internet; visitors speak Thai. MEASURED on this PC: classic SAPI has only en-US David+Zira, but Windows OneCore has MSTTS_V110_thTH_Pattara - a Thai voice, reachable via WinRT Windows.Media.SpeechSynthesis.
Plan says: voices come from the store config/voice.json, the md5 cache and FAQ pre-build stay (prototype llm/test.py had both), the PAGE plays the audio until the nong gets a speaker (A20-4). MMS voices are non-commercial - licence note wanted.
My proposal: helper ships apps/voice/tts.ps1 (PowerShell WinRT synth, text+lang in, wav bytes out; zero pip deps; the clunky async-await lives in one editable file); service gains POST /say text in, audio/wav out, cache keyed md5(text+voice), pre-build thread at startup; store maps language to voice name; hub proxies with real Content-Type and gates /api/voice/say; page autoplays the answer audio.
Judge: engine choice right for this PC? /say shape right? pre-build at startup vs lazy? cache invalidation traps? Anything that breaks the FAQ-instant story?
Answer in at most 20 lines.

**Files.** app.json, bench/cases.json, bench/run_bench.py, index.html, qa_data.json, service.py
**Cost.** 219003 tokens across 3 models

## The head reviewer (gemini-3.1-pro-high)

 - **real** `E:/final_proj/mice/code/.staging/apps/voice/bench/run_bench.py:150` --prepare calls edge_tts. Internet requirement breaks local synthesis.
 - **maybe** `E:/final_proj/mice/code/.staging/apps/voice/service.py:56` faqs() reads disk on each request. Synchronous read delays response.
 - **fine** `apps/voice/service.py:243` API shape fine.

## What each model said

### gemini-3.1-pro-high  _(90.9s, 59284 tokens)_

 - **fine** `apps/voice/tts.ps1:1` Engine choice fine.
 - **fine** `apps/voice/service.py:243` API shape fine.
 - **real** `apps/voice/service.py:54` startup pre-build ignores live edits, visitors hit slow lazy fallback.
 - **real** `apps/voice/tts.ps1:1` sequential pre-build delays readiness, concurrent spawn melts CPU.
 - **real** `apps/voice/tts.ps1:1` lazy fallback spawns PowerShell, startup latency ruins instant FAQ.
 - **maybe** `apps/voice/service.py:57` cache md5(text+voice) leaves orphaned WAVs, disk leaks when answers change.
 - **fine** `config/voice.json:1` Voice map fine.
 - **fine** `index.html:160` Page autoplay fine.

### gemini-3.7-flash-high  _(56.6s, 101415 tokens)_

 - **real** `E:/final_proj/mice/code/config/voice.json:39` tts.voice holds cloud edge-tts name th-TH-PremwadeeNeural instead of local WinRT voice map
 - **maybe** `E:/final_proj/mice/code/llm/test.py:168` cache sync purged all non-FAQ files which would wipe cached dynamic LLM audio
 - **maybe** `E:/final_proj/mice/code/.staging/apps/voice/service.py:56` faqs() reads disk on each request so pre-build must trigger on file modification to keep edited FAQ instant
 - **fine** `E:/final_proj/mice/code/.staging/apps/voice/index.html:150` sequential /ask and /say calls work fast when audio is pre-built in cache
 - **real** `E:/final_proj/mice/code/.staging/apps/voice/bench/run_bench.py:150` --prepare calls edge_tts requiring internet rather than local WinRT synthesis
