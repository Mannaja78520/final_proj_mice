# Panel review - 2026-08-24 22:20

**Question.** Review finished work A21-5 in .staging (unpromoted). Claims: 1) diagnostics() in main_python/main.py now returns a plain-words summary first - robots connected by NAME only, then either a needs-attention list where every line carries its own fix, or all-good - with no ids, COM ports, IPs or ports above the marker line DIAG_TECH_MARK; 2) below the marker the technical bundle is byte-for-byte what it always was; 3) hub.html renders the plain half into diagPlain always and the technical rest inside diagTechWrap class tech (page-wide technical switch), while Copy button AND the no-clipboard textarea fallback still carry the WHOLE bundle; 4) qc/checks/check_diagnostics.py splits on the same marker string and fails if any id/port/ip appears above it. Read the three files. What is NOT true, what breaks, what did I miss? Short numbered findings.

**Files.** main.py
**Cost.** 467205 tokens across 3 models

## The head reviewer (gemini-3.1-pro-high)

 - **real** `main_python/web/hub.html:197` reportBtn calls undefined openReport, feature is broken
 - **real** `main_python/main.py:404` probe_module defaults name to IP, leaks IP into plain summary
 - **real** `qc/checks/check_diagnostics.py:77` leak regex omits POSIX paths, misses non-Windows leaks
 - **real** `main_python/main.py:2270` title sits above DIAG_TECH_MARK, technical bundle lacks timestamp
 - **real** `main_python/web/hub.html:2238` showDiag slice includes DIAG_MARK, duplicates UI header
 - **fine** `main_python/web/hub.html:460` This is fine.
 - **fine** `qc/checks/check_diagnostics.py:66` This is fine.

## What each model said

### gemini-3.1-pro-high  _(611.0s, 161236 tokens)_

 - **FAILED** Error: timeout waiting for response

### gemini-3.7-flash-high  _(410.2s, 211252 tokens)_

 - **unchecked** `:` 1. main_python/main.py:404: probe_module defaults name to IP address, leaking IP into plain summary and worry list above DIAG_TECH_MARK when module is unnamed.
 - **unchecked** `:` 2. main_python/main.py:2270: title and timestamp sit above DIAG_TECH_MARK, so technical half below marker lacks bundle header and is not byte-for-byte original.
 - **unchecked** `:` 3. main_python/web/hub.html:460: diagPlain renders only after copyDiag click, not always on page load.
 - **unchecked** `:` 4. main_python/web/hub.html:2238: showDiag includes DIAG_MARK in diagTechText, duplicating support header.
 - **unchecked** `:` 5. main_python/web/hub.html:197: reportBtn, submitReport, and closeReport invoke undefined JS functions.
 - **unchecked** `:` 6. qc/checks/check_diagnostics.py:66: MARK hardcodes marker string instead of reading DIAG_TECH_MARK from main_python/main.py.
 - **unchecked** `:` 7. qc/checks/check_diagnostics.py:77: leak regex checks only COM\d, skipping POSIX paths /dev/tty* and non-4-digit ports.
