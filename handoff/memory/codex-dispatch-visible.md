---
name: codex-dispatch-visible
description: Start Codex jobs with tools/codex_dispatch.py so they show in the Codex app project mice
metadata:
  type: feedback
---

User wants every GPT Codex job visible in the Codex desktop app under project mice, not hidden. Plain codex exec threads have source exec, which the app hides. Use: python tools/codex_dispatch.py --cwd <worktree> --log <logfile> "<prompt>" (start it detached). It sets CODEX_INTERNAL_ORIGINATOR_OVERRIDE=codex_work_desktop, runs codex exec -m gpt-6.2-sol --approve-for-me, and flips the new thread row in ~/.codex/state_5.sqlite to source vscode (DB backup in ~/.codex/backups_visible), then patches the rollout first line after the job ends. The app groups threads by cwd under the project folder (project mice = the mice folder), so use a worktree under that folder when possible; for a worktree elsewhere the thread is listed by its own folder. Restart or reopen the app once if the list does not refresh. Manual fix for an old thread: flip its source to vscode in the threads table. Why: user could not see or steer hidden exec jobs. Related: gpt-overflow-rule.
