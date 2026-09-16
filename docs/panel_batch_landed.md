# Panel review - 2026-08-25 01:27

**Question.** Post-landing review of batch A21-5+A21-6+A24-1, now in the MAIN tree (promoted 2026-08-25 01:10, gate 3595/0). Claims: 1) main_python/main.py - diagnostics() plain half never shows an id/port/IP even when a WiFi module is unnamed (disp_name strips IP-shaped names); /api/report stores one JSON per report under HERE/reports with no secrets and no login; json/uuid imported only at module top after a scoping bug was fixed. 2) main_python/web/hub.html + shared/web/mice.css - report modal opens/closes/submits from any tab, tech pane slices AFTER DIAG_TECH_MARK, styles present for all five states. 3) tools/save_code_patch.py + tools/snapshot.py + tools/land.py - whitelist-only globs, auto-snapshot on every green gate, restore never deletes. Read those files in the main tree. What is NOT true, what breaks, what did we all miss? Short numbered findings.

**Files.** main.py
**Cost.** 672560 tokens across 3 models

## The head reviewer (gemini-3.1-pro-high)

 - **unchecked** `:` `main_python/main.py:2207`: Real, `disp_name()` regex `\d{1,3}(?:\.\d{1,3}){3}` fails on IP:port or forwarded `hub:` prefixes, leaking addresses into plain text.
 - **unchecked** `:` `main_python/web/hub.html:888`: Real, `closeReport()` does not re-enable `reportSend` after success, submit button stays disabled on next modal open.
 - **unchecked** `:` `tools/snapshot.py:136`: Real, `restore()` overwrites existing files but never deletes newer additions, leaving stale files in place.
 - **unchecked** `:` `tools/save_code_patch.py:28`: Real, `main_python/*.py` glob excludes `main_python/web/*`, hub HTML edits are never saved in code patches.
 - **unchecked** `:` `tools/land.py:64`: Real, auto-snapshot is in `land.py` only, running `promote.py` directly lands changes without creating snapshots.
 - **unchecked** `:` `main_python/main.py:3822`: Real, `HERE / 'reports'` resolves to `main_python/reports/` in source tree instead of repo root `reports/`.
 - **unchecked** `:` `shared/web/mice.css:198`: This is fine.
 - **unchecked** `:` `main_python/main.py:24`: This is fine.

## What each model said

### gemini-3.1-pro-high  _(592.3s, 236407 tokens)_

 - **FAILED** Error: timeout waiting for response

### gemini-3.7-flash-high  _(488.3s, 384256 tokens)_

 - **unchecked** `:` 1. `main_python/web/hub.html:888`: `closeReport()` does not re-enable `reportSend` after success; submit button stays disabled on next modal open.
 - **unchecked** `:` 2. `shared/web/mice.css:198`: only four state classes defined (`.state-load`, `.state-empty`, `.state-err`, `.state-stale`), missing fifth `.state-ready`/`.state-ok` class.
 - **unchecked** `:` 3. `tools/save_code_patch.py:28`: `main_python/*.py` glob excludes `main_python/web/*`; hub HTML edits are never saved in code patches.
 - **unchecked** `:` 4. `tools/land.py:64`: auto-snapshot is in `land.py` only; running `promote.py` directly lands changes without creating snapshots.
 - **unchecked** `:` 5. `tools/snapshot.py:136`: `restore()` overwrites existing files but never deletes newer additions, leaving stale files in place.
 - **unchecked** `:` 6. `main_python/main.py:2207`: `disp_name()` regex `\d{1,3}(?:\.\d{1,3}){3}` fails on IP:port or forwarded `hub:` prefixes, leaking addresses into plain text.
 - **unchecked** `:` 7. `main_python/main.py:3822`: `HERE / "reports"` resolves to `main_python/reports/` in source tree instead of repo root `reports/`.
 - **unchecked** `:` 8. `main_python/main.py:24`: imports are fine.
