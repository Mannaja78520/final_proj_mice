# Hub login: default admin/admin123, change prompt, recovery

Owner: claude (project thread, branch claude/hub-login)
Updated: 2026-11-27
Branch: claude/hub-login
Last commit: see git log
Plan: A58-1 (user ask 2026-11-27, relayed by the coordinator)

## Goal
- Know what dist/hub_password.txt is; untrack it (public repo).
- Factory login admin/admin123 from a tracked default file; the owner's changed password lives only in the gitignored store, hashed (PBKDF2).
- First login on the default: plain-words prompt to change it (skippable, remind me later).
- Forgot password: recovery code shown ONCE (stored hashed, single use, replaced after use, attempt limit with growing lockout), and a double-click
  "Reset Hub Password.bat" that only works on the hub PC itself.
- Help in th/en/zh/ja, lang files, systems map, changelog, tests with sabotage proof, QC, PR, exe rebuild, real-browser check.

## Findings (hub_password.txt)
- 357 bytes, written 2026-08-25 by an old version of hub_auth.py: a RANDOM 12-char password in plain text, NOT a test value.
- Tracked since commit 3645816 (the big "checkpoint" commit) although main_python/hub_password.txt is gitignored: dist/ is a separate path, so the
  ignore rule never matched it. It is in public history, so that password counts as leaked.
- Current code no longer generates a random one (DEFAULT_PASSWORD admin123) but still writes the plain file; nothing in the hub READS it for login.

## Doing now
Paused 2026-11-27 (user moving the PC). Nothing is running. PR #293 (draft) head is the last pushed commit.

## Done
- Untracked dist/hub_password.txt (+ ignore); the hub no longer writes a plain file and deletes an old one.
- main_python/hub_login.default.json (shipped admin/super_admin, admin123); hub_recovery.py (code + Throttle); Auth recovery/reset methods;
  /api/recovery/code and /api/recovery/use; whoami hasRecovery + shippedHint (hub PC only); no old-password box while on the shipped one.
- shared/web/mice-password.js (choose / code once / forgot / new code), Home + miceLogin hooks, lang th/ja/zh, Help part accounts in 4 languages.
- tools/hub_reset_password.py + "Reset Hub Password.bat" (local file edit, no network route).
- check_hub_login (77 asserts, 10 breaks caught) and check_hub_login_page (real browser 360 px, 20 asserts, 5 breaks caught).

## Next
0. EXACT NEXT STEP: run `python qc/run_qc.py --quiet` in the hub-login worktree (the last full run was cut off; the earlier full run failed only on 5 things, all fixed: check_accounts, api_index, task template, driver_waits, flakes from a stray account name).
1. Full QC, PR (draft -> ready, label auto-merge), rebuild MiceHub.exe (spec, polite), restart hub from dist, real-browser check.
2. A58-2 KV cache round 2.

## File status
| File | Change | State | Verification | Commit |
|---|---|---|---|---|
| main_python/hub_auth.py, hub_recovery.py, main.py | recovery, reset, no plain file | committed | check_hub_login, check_hub_auth | pushed |
| shared/web/mice-password.js, mice.js, mice-ui.js, home parts | dialogs | committed | check_hub_login_page | pushed |
| tools/hub_reset_password.py, launcher, config/extra_launchers.json | local reset | committed | check_hub_login | pushed |
| docs, lang, help, systems, changelog | docs | committed | check_systems, check_changelog, help checks | pushed |
