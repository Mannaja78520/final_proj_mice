---
name: gpt-overflow-rule
description: When Claude hands hard, stuck or overflow work to GPT Codex
metadata:
  type: feedback
---

Send to GPT Codex (user 2026-11-20, to save Claude tokens): (1) a task failed 2 tries or the theory looks wrong, (2) long mechanical work (many files, bulk edits, test fixing loops, audits), (3) a second opinion on design/UX, (4) Claude usage is low. CAD/SolidWorks always goes to Codex first.
How: write the task file (handoff/tasks), give Codex that file plus tools/ai_brief.txt and a line budget; Codex reads HANDOFF.md via AGENTS.md. Details and model choice: docs/COORDINATION.md (Codex helps first, Gemini 3.8 Flash High is the fallback).
Claude keeps: deciding, reviewing the diff, running QC, merging.

**Why:** Claude's weekly allowance is limited; GPT has its own.
**How to apply:** after Codex returns, treat its answer as a lead and verify against the code; record what it learned under Facts found. See [[token-saving-rules]].
