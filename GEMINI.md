# Mice shared session instructions

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
