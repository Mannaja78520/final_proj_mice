# Panel review - 2026-08-24 00:44

**Question.** A20-11 design, BEFORE code. One voice brain many PCs: today apps/voice/service.py binds 127.0.0.1 only; plan is remote hubs point their config/voice.json service at the brain PC address and the helper binds what the URL names - opting INTO lan sharing is an explicit edit, and the tradeoff is written down: the helper itself has no password, so lan exposure lets anyone ask or make it speak; moving a robot still needs the page login at whichever hub. Robot chosen BY NAME: qa_data entries say module NAME (eg Nong); the voice page resolves it against GET /api/modules/all at play time, so the robot can be plugged into any PC; no match = plain words naming what was not found. Moves serialised per module: the page checks GET /api/play first - if that module already moves, the SECOND request is answered in words (never queued, never silently taken over); the hub takeover stays untouched for Studio rehearsals. STOP stays ungated (already true). QUESTIONS: 1) name match - exact case-insensitive on the module name field enough, or also allow id? 2) busy words - refuse with what exact visitor sentence? 3) any trap in binding the helper wider than localhost that the tradeoff note misses? Answer in at most 12 lines.

**Files.** app.json, bench/cases.json, bench/run_bench.py, index.html, qa_data.json, service.py
**Cost.** 268032 tokens across 3 models

## The head reviewer (gemini-3.1-pro-high)

 - **real** `apps/voice/service.py:408` ThreadingHTTPServer reads concurrent /transcribe payloads into RAM before _lock applies, LAN exposure crashes helper. Read inside _lock.
 - **real** `apps/voice/index.html:230` doMove omits GET /api/modules/all name lookup and GET /api/play check, robot target fails or clobbers active motion. Add checks before POST.

## What each model said

### gemini-3.1-pro-high  _(116.3s, 58289 tokens)_

 - **fine** `apps/voice/index.html:168` Name match, use exact case-insensitive, ID breaks portability.
 - **maybe** `config/voice.json:1` Busy words, use "The robot is already moving.", read from config/voice.json. Person edits config/voice.json to change it.
 - **real** `apps/voice/service.py:408` LAN exposure, crashes helper, ThreadingHTTPServer reads concurrent /transcribe payloads into RAM before _lock applies.

### gemini-3.7-flash-high  _(56.7s, 160205 tokens)_

 - **real** `apps/voice/index.html:230` doMove omits GET /api/modules/all name lookup and GET /api/play check; robot target fails or clobbers active motion.
