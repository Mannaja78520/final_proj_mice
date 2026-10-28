# Panel review - 2026-08-21 21:19

**Question.** The hub is MiceHub.exe built by PyInstaller from this tree, and it goes stale silently: on 2026-08-21 yesterday exe ran with today fixes missing and nothing said so. Plan: at build time MiceHub.spec writes a per-file sha stamp of the sources into the bundle; at runtime a frozen hub finds the source tree beside the exe, re-hashes it, and /api/selfupdate gains stale, built, changed keys; hub.html shows a banner warn near the existing newVer banner naming up to 3 changed files and the rebuild command. Question 1: what makes this claim WRONG or noisy on a PC that has only the exe and no source. Question 2: is mtime enough instead of content hashes. Answer in at most 20 lines.

**Files.** main.py, MiceHub.spec
**Cost.** 317973 tokens across 3 models

## The head reviewer (gemini-3.1-pro-high)

 - (nothing to report)

## What each model said

### gemini-3.1-pro-high  _(82.4s, 62934 tokens)_

 - **real** `main.py:44` exe runs alone on venue PCs without source files so missing files trigger false warnings
 - **real** `main.py:56` loose files beside exe deliberately override bundled assets without rebuilding
 - **real** `main.py:` git checkouts set file mtimes to checkout time so identical content appears newer and triggers false warnings

### gemini-3.7-flash-high  _(216.0s, 101907 tokens)_

 - **unchecked** `:` [main_python/main.py:59-65](file:///E:/final_proj/mice/code/.staging/main_python/main.py#L59-L65): standalone PC has no source tree beside `sys.executable`; missing source paths cause `FileNotFoundError` or false stale warnings.
 - **unchecked** `:` [main_python/main.py:97-108](file:///E:/final_proj/mice/code/.staging/main_python/main.py#L97-L108): runtime files written in `DATA` (`hub_auth.json`, `projects/`) beside exe get falsely flagged as modified source files.
 - **unchecked** `:` [main_python/web/hub.html:135-139](file:///E:/final_proj/mice/code/.staging/main_python/web/hub.html#L135-L139): rebuild banner displays CLI rebuild commands on venue PC lacking Python and PyInstaller toolchain.
 - **unchecked** `:` [MiceHub.spec:10-18](file:///E:/final_proj/mice/code/.staging/MiceHub.spec#L10-L18): runtime check must verify repo marker like `MiceHub.spec` or `.git` exists before inspecting neighboring files.
 - **unchecked** `:` [main_python/main.py:1767-1773](file:///E:/final_proj/mice/code/.staging/main_python/main.py#L1767-L1773): `mtime` is insufficient because PyInstaller unpacks one-file bundles to `sys._MEIPASS` with new extraction timestamps every run.
 - **unchecked** `:` Git checkouts, branch switches, and file touches change filesystem `mtime` without content changes, triggering false stale flags.
 - **unchecked** `:` Content hashes are required: deterministic across extractions, repository clones, and machines without timestamp drift.
