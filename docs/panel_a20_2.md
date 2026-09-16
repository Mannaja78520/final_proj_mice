# Panel review - 2026-08-23 13:42

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
Review FINISHED work in .staging before promotion. Change: Nong Studio plays a SAVED sequence without editing it first. nong/main_python_set_nong/web/index.html adds a Play saved button calling playLocalSeq(). app.js adds playSavedSeq(sourceLabel, getText): fetch text, parseSeqYaml + loadParsedSeq, stop a running show first, reset playT=0 and scrub, togglePlay(). playLocalSeq reads /api/loadseq for the picked list entry; playSdSeq feeds sdDownload. Each Robot SD card row gained a Preview button between Run and Edit, wired to playSdSeq(f.n). New check qc/checks/check_play_saved.py seeds sequences/qc_play.yaml (pose 40x2 140x4 ... T 900, wait 150, pose 130x2 60x4 ... T 1100), clicks the REAL button, asserts on fake_serial.wire: segment one leads 40, segment two leads 130 with T within 60 of 1100, exactly two segments total. Claim: it plays exactly like an edited sequence through whichever clock applies, always starts at the top, and cannot inherit playT from a previous show. Check what is NOT true: the keys===before failure guard, the stop-then-restart when already playing, hub-driven mode where hubPlay(playT) seeks, loop:true files, a file with zero poses, and the SD card row layout on a 360px screen. Answer directly, no plan. At most 15 lines.

**Files.** app.js, index.html, style.css, vendor/OrbitControls.js, vendor/STLLoader.js, vendor/three.min.js
**Cost.** 542882 tokens across 3 models

## The head reviewer (gemini-3.1-pro-high)

 - **unchecked** `:` app.js:2698: This is fine.
 - **unchecked** `:` app.js:2724: This is fine.
 - **unchecked** `:` app.js:2777: This is fine.

## What each model said

### gemini-3.1-pro-high  _(613.3s, 186221 tokens)_

 - **FAILED** Error: timeout waiting for response

### gemini-3.7-flash-high  _(313.9s, 273480 tokens)_

 - **unchecked** `:` [app.js:2774](file:///E:/final_proj/mice/code/.staging/nong/main_python_set_nong/web/app.js#L2774): unawaited [`hubStop`](file:///E:/final_proj/mice/code/.staging/nong/main_python_set_nong/web/app.js#L2194-L2196) in [`togglePlay`](file:///E:/final_proj/mice/code/.staging/nong/main_python_set_nong/we
 - **unchecked** `:` [app.js:2777](file:///E:/final_proj/mice/code/.staging/nong/main_python_set_nong/web/app.js#L2775-L2777): `keys === before` fine.
 - **unchecked** `:` [app.js:2778](file:///E:/final_proj/mice/code/.staging/nong/main_python_set_nong/web/app.js#L2778): `hubPlay(playT)` seek fine.
 - **unchecked** `:` [app.js:2698](file:///E:/final_proj/mice/code/.staging/nong/main_python_set_nong/web/app.js#L2698): `loop:true` files fine.
 - **unchecked** `:` [app.js:2724](file:///E:/final_proj/mice/code/.staging/nong/main_python_set_nong/web/app.js#L2724-L2727): zero poses fine.
 - **unchecked** `:` [style.css:48](file:///E:/final_proj/mice/code/.staging/nong/main_python_set_nong/web/style.css#L48): 360px layout fine.
