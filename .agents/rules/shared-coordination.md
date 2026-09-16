---
trigger: always_on
---

# Shared Mice workspace

Before any edits, read AGENTS.md, CLAUDE.md, docs/COORDINATION.md and the newest
docs/BRIDGE.md entries from E:/final_proj/mice/code. Follow their ownership,
shared mutex, staging, QC and handoff rules. These paths refer to the real
project root, including when your working tree is a staging copy.

Identify your assistant/session. Claim exact files before writing. Work only
on the current user assignment. Preserve other assistants' uncommitted work.
Use Caveman full, plain-speak and token-thrift. Update the real plan through
tools/plan.py under the coordination mutex. Release claims at handoff.

Use the latest relevant BRIDGE entry for current ownership; old task names
are not permanent reservations. Follow the provider-limit and resume section
of docs/COORDINATION.md in every new prompt and session. Codex helps first;
Gemini or another available provider takes over when Codex is limited.
Record the exact task page, tree, checks, next action and released claims.

An explicit user request to ask Codex is an action to perform now, before
another patch or QC restart. Follow the mandatory consultation procedure in
docs/COORDINATION.md. Do not replace the requested consultation with a claim
that you already solved it, another trial run, or a prompt for the user to relay.
Report the actual response or invocation failure; never invent review evidence.
