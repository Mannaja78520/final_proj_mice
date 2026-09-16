# Panel review - 2026-08-26 12:44

**Question.** Batch 5 of the A22 sweep, all in this staging tree. Claims to attack: (1) nong/main_python_set_nong/web/app.js - notice() now fires ONLY on failures; routine progress stays on card status lines; connect-to-the-robot-first guards DO banner; buildYaml writes a per-move speed override even on the FIRST keyframe. (2) main_python/main.py - /api/reports status screen reads report json under _reports_lock; voice_service_url appends default port 8767 to portless helper URLs; voice proxy tells a timeout from not-running. (3) apps/voice/service.py - write_store saves through unique .partN temp names. What is NOT true? Name file and line. Answer in at most 20 lines.

**Files.** app.js, main.py, service.py
**Cost.** 431100 tokens across 3 models

## The head reviewer (gemini-3.1-pro-high)

 - **real** `E:/final_proj/mice/code/.staging/main_python/main.py:3952` GET /api/reports reads without _reports_lock, racing against concurrent writes and background translations.
 - **real** `E:/final_proj/mice/code/.staging/nong/main_python_set_nong/web/app.js:3321` connModeChanged unbracketed else if runs notice() on every non-USB mode change, firing banner on routine actions instead of only failures.
 - **fine** `main_python/main.py:3952` is duplicate finding.

## What each model said

### gemini-3.1-pro-high  _(520.8s, 188614 tokens)_

 - **unchecked** `:` main_python/main.py:3952, GET /api/reports reads without _reports_lock, lock only wraps read-modify-write updates.

### gemini-3.7-flash-high  _(85.6s, 157626 tokens)_

 - **real** `E:/final_proj/mice/code/.staging/nong/main_python_set_nong/web/app.js:3321` connModeChanged unbracketed else if runs notice() on every non-USB mode change, firing banner on routine actions instead of only failures.
 - **real** `E:/final_proj/mice/code/.staging/main_python/main.py:3952` GET /api/reports reads report JSON files without _reports_lock, racing against concurrent writes and background translations.
