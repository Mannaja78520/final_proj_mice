# Panel review - 2026-08-24 22:40

**Question.** A24-1: extend the numbered patch-snapshot system beyond Nong Studio. Engine already exists: tools/snapshot.py - Snapshots(root, globs, patches dir, PATCHES.md index, restore by number), format-compatible consumers today are nong/main_python_set_nong/save_patch.py (web app) and firmware/save_fw_patch.py. Need the same rollback safety for hub Python (main_python/main.py + hub_auth.py), shared/web, qc/, tools/. Decide: ONE new consumer covering all remaining source vs one consumer per area? Where do its patches live (suggest code/patches_hub)? Which globs cover it without ever touching runtime files (docs/PLAN.html, MiceHub.exe, promt.md, cookies, reports)? Should land.py take a snapshot automatically right before promote so every landed change has a number? What breaks if restore runs while a gate is promoting? Answer as numbered recommendations, at most 25 lines.

**Files.** snapshot.py
**Cost.** 154975 tokens across 3 models

## The head reviewer (gemini-3.1-pro-high)

 - **real** `snapshot.py:67` name[:4] truncates patch numbers over 9999, breaks sequence
 - **real** `snapshot.py:154` missing length check for argv[1], crashes on empty restore
 - **real** `snapshot.py:128` restore leaves untracked files intact, tree is not exact version
 - **maybe** `snapshot.py:120` int(n) raises ValueError on non-numeric input, crashes script
 - **maybe** `snapshot.py:100` desc newlines not escaped, breaks markdown table
 - **maybe** `snapshot.py:93` missing parent directory creation for index, crashes if missing
 - **maybe** `snapshot.py:83` overlapping globs yield duplicate files, wastes IO

## What each model said

### gemini-3.1-pro-high  _(44.4s, 28481 tokens)_

 - (nothing to report)

### gemini-3.7-flash-high  _(34.3s, 82144 tokens)_

 - (nothing to report)
