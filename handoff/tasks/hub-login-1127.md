# Hub login: default admin/admin123, change prompt, recovery

Owner: claude (project thread, branch claude/hub-login)
Updated: 2026-11-27
Branch: claude/hub-login
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
Starting: untrack, then code.

## Done
(nothing yet)

## Next
1. git rm --cached dist/hub_password.txt + ignore dist/hub_password.txt; stop writing the plain file.
2. config default file + hub_recovery.py + endpoints + UI + reset tool/launcher.
3. Tests, Help x4, lang, systems, changelog, QC, PR, exe, browser check.

## File status
| File | Change | State | Verification | Commit |
|---|---|---|---|---|
| handoff/tasks/hub-login-1127.md | new | uncommitted | n/a | - |
