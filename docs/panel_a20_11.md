# Panel review - 2026-08-24 01:10

**Question.** A20-11 QC-green, review before promote. One voice brain many PCs: apps/voice/service.py listens on the address named by service in config/voice.json (LAN share opt-in, helper has no password - warning printed when shared); /ask caps its body at 1MB and drains a bounded overshoot so the asker still reads the refusal. apps/voice/index.html doMove resolves a qa_data module NAME case-insensitively against GET /api/modules/all (first live route wins), refuses in words when that robot already moves (GET /api/play), never queues. Read apps/voice/service.py, apps/voice/index.html, qc/checks/check_voice_multi.py. What is NOT true? One finding per line.

**Files.** app.json, bench/cases.json, bench/run_bench.py, index.html, qa_data.json, service.py
**Cost.** 502852 tokens across 3 models

## The head reviewer (gemini-3.1-pro-high)

 - **real** `apps/voice/index.html:236` `|| (bot.routes || [])[0]` assigns stale route when no live route exists, breaking first live route wins constraint.

## What each model said

### gemini-3.1-pro-high  _(202.6s, 143211 tokens)_

 - **real** `apps/voice/index.html:236` `|| (bot.routes || [])[0]` assigns stale route when no live route exists, breaking first live route wins constraint.

### gemini-3.7-flash-high  _(482.7s, 332068 tokens)_

 - **FAILED** Error: timeout waiting for response
