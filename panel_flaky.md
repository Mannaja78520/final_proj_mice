# Panel review - 2026-08-20 19:46

**Question.** QC suite problem. qc/run_qc.py runs checks in parallel with a browser lane. Browser checks drive headless Edge and report by calling qcMark, which fetches a hub URL; the python side then reads fake_serial.qc_marks. Symptom: in the parallel gate a DIFFERENT browser check fails each run - check_flash_confirm, then check_network_tab, then check_modsite_back - and every value is None, meaning NO marks arrived at all. Each one passes alone every time. Question: in qc/lib/browser.py and qc/run_qc.py, what makes marks vanish entirely under parallel load? Name file and line. Ignore style.

> **NO REVIEW HAPPENED.** All 2 models failed, so nothing below is a judgement about the code — it is a list of outages. Do not read the absence of findings as approval.

> - Error: Agent execution terminated due to error.
> - Error: timeout waiting for response

**Files.** browser.py, fake_serial.py, fake_wifi.py, qc.py, run_qc.py
**Cost.** 676387 tokens across 3 models

## The head reviewer (gemini-3.1-pro-high)

 - **unchecked** `:` real: run_qc.py:220, returns "" instead of buf.getvalue(), drops check print output
 - **unchecked** `:` real: run_qc.py:275, Windows spawn gets _generated_done=False, causes concurrent gen_tables.py builds
 - **unchecked** `:` real: browser.py:372, sweep misses _qcdriver_*.html and _qcraw_*.html, leaks files in web directory
 - **unchecked** `:` maybe: fake_serial.py:412, read returns immediately on partial data, diverges from blocking pyserial
 - **unchecked** `:` maybe: qc.py:184, throwaway password file never deleted, leaks in temp directory
 - **unchecked** `:` maybe: fake_serial.py:99, split uses uppercase T, fails if time uses lowercase t
 - **unchecked** `:` fine: fake_wifi.py flawless.

## What each model said

### gemini-3.1-pro-high  _(611.5s, 124373 tokens)_

 - **FAILED** Error: timeout waiting for response

### gemini-3.7-flash-high  _(559.8s, 444991 tokens)_

 - **FAILED** Error: Agent execution terminated due to error.
