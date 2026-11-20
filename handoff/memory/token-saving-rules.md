---
name: token-saving-rules
description: Token and usage rules that apply to Claude, GPT and Gemini alike
metadata:
  type: feedback
---

Full rules: HANDOFF.md section Save tokens. Short version: heartbeat one line, no polling, grep then line ranges (never whole BRIDGE, PLAN.html, app.js), experiments get a numeric budget plus stop rule (default 3 rounds, stop below 2% gain), QC with --quiet on touched checks and one full run before merge, one task per session, effort high (not max).

**Why:** on 2026-09-29 five parallel max-effort sessions burned a 5-hour window in minutes; every call re-reads the whole conversation.
**How to apply:** parallel sessions are fine when they save time but avoid two touching the same files; see [[gpt-overflow-rule]].
