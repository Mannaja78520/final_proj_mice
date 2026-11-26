---
name: pc-assistant-ensure
description: Run tools/pc_assistant_ensure.py when you start a task; after a PC restart the user's first message means continue
metadata:
  type: feedback
---

User 2026-11-27 (all AIs): whichever AI starts a task (Claude, GPT Codex, Gemini) runs python tools/pc_assistant_ensure.py first (idempotent, no questions): it installs the PC assistant's keep-running check unless the user stopped it with Stop PC Assistant. The check has NO logon trigger and removes itself when the PC shuts down or restarts. After a restart or shutdown the USER's first message to any AI means 'continue the work': read HANDOFF.md and handoff/tasks, resume every task marked Doing now, re-run the ensure step, do not ask. Nothing starts by itself at logon. Why: the user was typing the remote-control command by hand and unfinished work was left after drops. How to apply: docs/pc_assistant.md.
