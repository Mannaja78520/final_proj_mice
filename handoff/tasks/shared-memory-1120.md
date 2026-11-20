# Share one memory across Claude, GPT, Gemini

Owner: claude
Updated: 2026-11-20 15:19 +0000
Branch: claude/project-thread-n1bunv
Last commit: see git log
Plan: none (user ask 2026-11-20)

## Goal
เอาให้ Claude, GPT, Gemini แชร์เมมทั้งหมดและเขียนเมมเอง (Facebook post: turn off auto memory, write + maintain memory yourself). Hard/stuck or overflow work goes to GPT Codex to save Claude tokens.

## Doing now
Finishing: quick QC running, then PR. (Added) handoff/memory/ (one fact per file + MEMORY.md index), tools/memory.py (list/add/index/check), qc check_memory, rules in HANDOFF.md + 3 entry files.

## File status
Baseline: <starting SHA; reconcile owned commits, working diff and untracked files>

| File | Change | State | Verification | Commit |
| --- | --- | --- | --- | --- |
| `handoff/memory/*.md` | MEMORY.md index + 5 seed facts | done | check_memory quick PASS | uncommitted |
| `tools/memory.py` | list/add/index/check | done | check_memory PASS | uncommitted |
| `qc/checks/check_memory.py` | new check, proves refusal of key/email/oversize | done | quick PASS | uncommitted |
| `HANDOFF.md`, `CLAUDE.md`, `AGENTS.md`, `GEMINI.md` | memory + GPT overflow rule | done | handoff_first PASS | uncommitted |
| `docs/systems.json`, `docs/systems/*.md` | tools/memory.py owned by agents; rebuilt | done | systems PASS | uncommitted |

<One latest row per owned source/generated/test/config/doc file, including additions,
deletions and renames. Use exact paths; link evidence and label quick/full or
simulated/hardware. Do not attribute other owners' edits. No edits: say so.
For this handoff file itself, Commit may be `this checkpoint`.>

## Facts found
- tools/handoff.py: task files; handoff/ is owned by system `agents` in docs/systems.json, so memory under handoff/memory/ needs no new root entry.
- Facebook post (thaitypecoding): 3 months with Claude Auto Memory OFF, memory written and maintained by hand. Comments not readable without login.

## Done
- Quick targeted QC (memory handoff_first root_tidy systems) 187 pass. Full QC not run (PC-only, ~8 min).

## Next
1. python qc/run_qc.py --quiet memory handoff_first root_tidy systems; then full QC, PR.

## Blocked
- nothing
