# Watch every AI for usage limits, resume after reset, hand off long limits

Owner: claude:ai-watch-1029
Updated: 2026-10-29 03:36 +0700
Branch: claude/ai-limit-watch (PC clone: <real root>/.staging/ai-watch)
Last commit: this checkpoint
Plan: none yet (tool task, not a plan row)

## Goal
User 2026-10-29 (via coordinator): a real system on the PC that watches every AI
worker (Codex CLI, Gemini CLI, Claude sessions). On a usage limit: read the reset
time from its output and send the continue command 1 minute after the reset.
Claude already auto-resumes, the others do not. Claude weekly limit, or any limit
whose reset is more than 7 hours away: hand the unfinished work to Codex or Gemini
(HANDOFF.md + handoff/tasks), and they keep working until it is done.
Config-driven (providers, commands, thresholds). Test with a fake limit message and
with the running Codex CAD job. Never edit the friend's folders; never stop RL/YOLO.

## Doing now
Writing config/ai_watch.json and tools/limitwatch/ (parser, sources, actions, watcher).

## File status
Baseline: e4b2069 (origin/main)

| File | Change | State | Verification | Commit |
| --- | --- | --- | --- | --- |
| `handoff/tasks/ai-limit-watch.md` | new task file | done | n/a | this checkpoint |
| `config/ai_watch.json` | providers, patterns, commands, thresholds | pending | not run | uncommitted |
| `tools/limitwatch/` | watcher package | pending | not run | uncommitted |
| `tools/ai_watch.py` | CLI | pending | not run | uncommitted |
| `qc/checks/check_ai_watch.py` | QC check | pending | not run | uncommitted |
| `config/layout.json` | out kind ai_watch | pending | not run | uncommitted |
| `docs/systems.json` | system entry ai-watch | pending | not run | uncommitted |

## Facts found
- Codex limit (real, 2026-10-29): `~/.codex/sessions/YYYY/MM/DD/rollout-*-<session id>.jsonl`,
  line `type=event_msg, payload.type=task_complete, payload.error.codex_error_info=usage_limit_exceeded`,
  message "... try again at 3:26 AM." First line `session_meta` has `cwd`, `session_id`.
- Codex resume: `codex exec --skip-git-repo-check -m gpt-6.1-sol -C <cwd> resume <session id> -` (prompt on stdin); needs CLI >= 0.165 (PC has 0.165.0).
- Claude limit: `~/.claude/projects/*/*.jsonl`, `type=assistant`, `message.model="<synthetic>"`,
  text "You've hit your session limit · resets 11:50am (Asia/Bangkok)"; weekly says "weekly limit".
  `usageLimitNote: wrap_up|release` user lines carry no reset time. Quoted limit text also appears
  inside tool results, so only the synthetic assistant line counts.
- Python 3.12 on the PC has no `tzdata`: `ZoneInfo("Asia/Bangkok")` fails; PC clock is +07.
- Gemini CLI 0.55.1: `gemini -p <prompt> -m <model> --approval-mode yolo`, `-r latest` resumes.

## Done
- Task file made.

## Next
1. Write the code, then `python qc/run_qc.py --quiet check_ai_watch`.

## Blocked
- nothing
