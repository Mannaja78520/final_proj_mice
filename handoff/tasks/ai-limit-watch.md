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
Waiting for the user to start the watcher (see Blocked).

## File status
Baseline: e4b2069 (origin/main)

| File | Change | State | Verification | Commit |
| --- | --- | --- | --- | --- |
| `handoff/tasks/ai-limit-watch.md` | task file | done | n/a | this checkpoint |
| `config/ai_watch.json` | providers, patterns, commands, thresholds | done | check_ai_watch quick PASS | this checkpoint |
| `tools/limitwatch/__init__.py` | package doc | done | check_ai_watch | this checkpoint |
| `tools/limitwatch/reset_time.py` | reset time parser | done | check_ai_watch (5 real wordings) | this checkpoint |
| `tools/limitwatch/sources.py` | Claude/Codex/text log readers | done | check_ai_watch; sabotage of the synthetic filter caught | this checkpoint |
| `tools/limitwatch/jobs.py` | detached launcher | done | check_ai_watch (fake workers) | this checkpoint |
| `tools/limitwatch/brief.py` | handoff task discovery, done/stall test | done | check_ai_watch | this checkpoint |
| `tools/limitwatch/watcher.py` | decision loop + state | done | check_ai_watch; sabotage of +60 s caught | this checkpoint |
| `tools/ai_watch.py` | CLI; install writes a launcher that tries mice_system, code, then the copy | done | check_ai_watch 19 PASS; install not run (blocked) | this checkpoint |
| `qc/checks/check_ai_watch.py` | QC check, 18 asserts | done | PASS (quick, simulated) | this checkpoint |
| `config/layout.json` | out kind ai_watch | done | check_root_tidy PASS | this checkpoint |
| `docs/systems.json`, `docs/systems/ai-watch.md`, `docs/systems/{README,agents,qc}.md`, `docs/LAYOUT.md` | system entry + generated | done | check_systems PASS | this checkpoint |

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
- Watcher, config, CLI, QC check (quick run: check_ai_watch check_systems check_root_tidy check_handoff_first, 116 PASS, simulated).

## Next
1. `python tools/ai_watch.py install` (logon start) and `status`; the launcher survives the rename and the merge; no second install.
2. Full QC + PR/merge: cloud thread.

## Blocked
- Starting the watcher (`install` = logon entry, or `run`) was refused by Claude's auto-mode safety check
  (persistence / starting autonomous agents). The user runs `python tools/ai_watch.py install` once, or allows it.
- Dry tick on the real logs 2026-10-29 03:50: found the CAD Codex limit (session 01a1842a-5b15..., reset 03:26 local, right)
  and skipped it because that session was already resumed by hand. No Claude limit in the last 12 h.
