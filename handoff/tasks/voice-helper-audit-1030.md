# Independent Voice acceptance audit and duplicate-start fix

Owner: codex:voice-1030-01a1891e
Updated: 2026-10-30 05:15 +0700
Branch: codex/voice-helper-audit-1030
Last commit: this checkpoint
Plan: A55-2

## Goal
User: check all Voice features requested from Claude, fix remaining bugs and
verify actual results until complete. Do not disturb other work or live services.

## Doing now
Regression added and confirmed RED on baseline (19 passed, 3 failed).
Next: patch start() ownership guard, update Help in the same step, then rerun.
Use isolated tree only; no changes to live Voice or Claude's deployment task.

## File status
Baseline: 4c25306 (origin/main, PR112); task/test edits only.

| File | Change | State | Verification | Commit |
| --- | --- | --- | --- | --- |
| `handoff/tasks/voice-helper-audit-1030.md` | own audit/checkpoint | active | task claimed | this checkpoint |
| `main_python/voice_helper.py` | retain ownership of an alive timed-out child | pending | baseline fake-clock reproducer: 2 children, expected 1 | uncommitted |
| `qc/checks/check_voice_helper.py` | timeout boundary/concurrency/recovery regression | added | baseline 19/3 as expected; _out/voice-helper-audit/baseline.log | this checkpoint |
| `main_python/web/help/parts/voice.html` | document no duplicate helper while slow | pending | not run | uncommitted |
| `main_python/web/help.html` | rebuild Help from source | pending | not run | uncommitted |
| `docs/systems/app-voice.md` | record lifecycle trap | pending | not run | uncommitted |

## Facts found
- A55-1 is explicitly done in main's plan; PR111 merged8658d42. Its source is stable;
  remaining deployment and real app checks remain separate, not claimed from Claude.
- `main_python/voice_helper.py:139`: after60s start() replaces _proc although
  poll() is still None. Read-only fake Popen+clock at0/61 produced2 alive children.
- Existing1194/0 Voice results do not cover timeout expiry. Full9072/11 is RED,
  attributed to cloud environment by Claude; independent local gate still needed.
- Live helper13744 and Hub26664 belong to Claude's voice-test tree. Do not touch.
- Root main has unrelated RL changes; this isolated worktree starts clean origin/main4c25306.

## Done
- Reproduced duplicate-start failure with fake process/clock only, no ports/models.
- New regression: baseline check_voice_helper 19 passed / 3 expected failures; existing16 assertions pass.
- Rebased task-only branch from local RL history to clean origin/main4c25306 before publishing; no unrelated commits pushed.
- Read project debugging, verification, communication and subsystem instructions.

## Next
1. Regression must fail on baseline; patch, affected checks, sabotage, independent review.
2. Full gate only after QC lease and heavy-job constraints are satisfied; do not skip failures.
3. Continue feature acceptance: packaged launch, authenticated ask/say, STT, fallback,
   conversation/Stop and physical audio evidence; source/fakes are not hardware proof.

## Blocked
- Deployment/authenticated end-to-end and physical microphone/speaker checks are unverified.
- Full gate not started; another chat owns CPU pose extraction. No QC lease takeover.
