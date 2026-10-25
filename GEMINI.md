# Mice shared session instructions

## Start here: HANDOFF.md (user 2026-10-21)

Read `HANDOFF.md` first, then your one task file in `handoff/tasks/`.
Mandatory Handoff-First & Force-Queue Reconciliation (user 2026-10-25, all AIs):
never write code without an active task in `handoff/tasks/` (`tools/handoff.py take/new`).
Update `## Doing now` before each step, `## Done`/`## Next` after each step, and
commit WIP around EVERY step. If interrupted or force-queued, check the task file,
compare and pair old work with the new demand — never blindly abandon in-flight tasks.
Per-file handoff (all AIs, user 2026-10-25): maintain `## File status` in your
task with one latest row per owned changed file: File | Change | State |
Verification | Commit. Include generated/tests/config/docs; mark uncommitted
and not run explicitly. Reconcile owned Git changes before each checkpoint;
keep it short and link evidence. Read HANDOFF.md for the full contract.
Tokens: run QC as `python qc/run_qc.py --quiet <check names>` for the files
you touched (full log in qc/last_run.log), full QC once before merge; grep or
tail big files (BRIDGE, PLAN.html, app.js, reports/), never read them whole.

## Find the subsystem first (A26-76, user 2026-09-21)

Before reading code: `python tools/systems.py which <file>` (or open
`docs/systems/README.md`) and read that ONE header in `docs/systems/`. Stay in
that system's files; its header lists the checks to run. A new file or system:
add it to `docs/systems.json`, then `python tools/systems.py build`.
`check_systems` fails on a file nobody owns or a stale header.

## How to read (tokens are paid; user 2026-09-22, A26-93)

- `python tools/systems.py which <file>` -> read that ONE header first.
- `rg` the name, then read 40-100 lines around the hit. Never a whole file
  over 300 lines (main.py is ~38k tokens; one function is ~1k).
- Never re-read a file already read or just edited.
- Logs: print the failing line only (tail / grep), never the full run.
- Moving code: write a script that moves exact lines; do not retype it.
- Strict OOP & modularity (user 2026-10-24, all AIs): code MUST follow OOP and modularity. Never dump features into monolithic main files (e.g. main.py) — create small, focused classes and modules (token-friendly). Never edit built web files (hub.html, help.html, app.js) directly; edit their sources in parts/ and run `tools/build_web.py`.
- Rule 11 Mandatory Help Parity & Sync (user 2026-10-25, all AIs): whenever any feature, UI, or setting is modified, `help.html` and its sources in `main_python/web/help/parts/` MUST be updated in the exact same step.

Read AGENTS.md, CLAUDE.md, docs/COORDINATION.md and the latest relevant
docs/BRIDGE.md entries before editing. Use the named robot/system plan task.
Follow shared claims, mutex, staging, QC and provider-limit takeover rules.
Codex helps first; use Gemini when Codex is limited or unavailable. Preserve
existing work. Before stopping, record evidence, next action and claim releases.
Use Caveman full, plain-speak and token-thrift.

## Explicit requests for Codex advice are mandatory

When the user says to ask Codex, actually request Codex advice before another
fix or QC restart. Do not substitute your own diagnosis, promise to ask after
one more attempt, or make the user relay a prompt you can send yourself.
Follow docs/COORDINATION.md's consultation procedure. Record the invocation,
requested model/effort, result or exact failure, and the resulting decision.
Never say Codex reviewed something unless a completed response exists.
If Codex is unavailable, report the actual error and use the authorized fallback.

## Plan ownership, every agent and session (user 2026-09-16)

Every task goes into the plan the moment it is asked, owned by
provider:session (`python tools/plan.py session <provider>`, then
`--agent` or MICE_AGENT). Never a provider alone. Before a limit or stop,
`python tools/plan.py handoff <id> "<next step>"` so any agent can continue.
Full rule: docs/COORDINATION.md, *Every task is in the plan*.
