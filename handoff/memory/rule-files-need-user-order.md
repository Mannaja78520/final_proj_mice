---
name: rule-files-need-user-order
description: AI edits rule files only when the user orders it
metadata:
  type: feedback
---

Rule files (HANDOFF.md hard rules, CLAUDE.md, AGENTS.md, GEMINI.md, config of the QC gate) are changed only when the user asks, in any message, as before. An AI never edits them on its own initiative: it proposes the change in its reply and waits. This is not a total ban (user 2026-11-20: never-ever is too conservative).

**Why:** rules steer every AI, a silent change spreads to all of them.
**How to apply:** if you learn a durable fact, use tools/memory.py add; if a rule looks wrong, say so and let the user decide.
