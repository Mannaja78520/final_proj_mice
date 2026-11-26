---
date: 2026-11-27
kind: improved
prs: -
area: tooling
title: Any AI turns the PC assistant's keep-running check on when it starts a task; after a restart the first message means continue
---
Problem: the PC assistant's keep-running check had to be turned on by a double-click, and after a restart nobody told the AIs to continue.
Method: whichever AI starts a task (Claude, GPT Codex, Gemini) runs python tools/pc_assistant_ensure.py first: it installs the check once (idempotent, no questions) unless the user pressed Stop PC Assistant, which leaves a "turned off" flag. The check has no logon trigger and removes itself when the PC restarts or shuts down; after a restart the user's first message to any AI means continue, and a new session is told to read HANDOFF.md and handoff/tasks, resume and run the ensure step again. The rule is in HANDOFF.md, the shared memory, the Codex and Gemini task-start text and the SessionStart hint.
Numbers: tested with throwaway tasks and a sandbox copy of the launchers; nothing was registered on the real PC. See docs/pc_assistant.md.
