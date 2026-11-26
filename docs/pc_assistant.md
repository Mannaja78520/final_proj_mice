# The PC assistant (remote control) that keeps itself running

Plain words, for whoever sits at the PC.

**You do not have to start it.** Whichever AI starts a task (Claude, GPT Codex or Gemini) runs
`python tools/pc_assistant_ensure.py` first (idempotent, no questions) and that turns the keep-running check on, unless you stopped
the assistant with "Stop PC Assistant". **After you restart or shut down the PC, just send any message to Claude, GPT or Gemini:**
it reads `HANDOFF.md` and `handoff/tasks`, continues every task marked "Doing now" without asking, and turns the check on again.
Nothing starts by itself when you log in.

**Start it by hand:** open `main_python/launchers/Start PC Assistant.bat` (double-click). It starts the assistant now, turns on a small
automatic check that looks every 3 minutes, and turns on the AI watcher. Opening it twice is harmless.

**Stop it:** open `Stop PC Assistant.bat`. It turns off the automatic check, the AI watcher and the assistant session (only that one),
and leaves a "turned off" flag (`.local/pc_assistant_off.json`) so no AI switches it on again until you open "Start PC Assistant".

**What the automatic check does** (`tools/rc_watchdog.ps1`, settings in `config/rc_watchdog.json`)
- If the assistant is not running, it starts it again. If it is running but has lost its connection on two checks in a row, it stops
  that one process and starts it again. It never starts it more than 3 times an hour, and never touches any other Claude window.
- If the assistant is connected but has written no heartbeat (`python tools/rc_heartbeat.py write ...`, done at every checkpoint)
  for 90 minutes while a task file says "Doing now", it counts as stalled and is restarted the same way.
- A new session is shown which tasks are still marked "Doing now" (`tools/resume_hint.py`, a SessionStart hook in
  `.claude/settings.json`). `claude remote-control` has no option to send it a first message, so it starts working when the next
  message arrives; the session then says it is back in one line.
- **It removes itself when the PC shuts down, restarts, or you log in again.** After that it does nothing until an AI starts a task
  (or you open "Start PC Assistant"); there is no start at logon.

**When a usage limit is reached** (`tools/ai_watch.py`, rules in `config/ai_watch.json`)
Claude -> GPT Codex -> Gemini 4 Argon (may do hard and long work) -> the regular Gemini models (small safe steps only, notes and
tracking) -> if all are limited, it waits and checks the reset times. Only one AI edits at a time (`.local/ai_active.lock`); when
Claude is free again no new fallback round starts and the task files carry the hand-over. Nothing in the chain edits the friend's
repositories.

**Turn it off without the .bat:** `powershell -File tools/rc_watchdog_uninstall.ps1` (or in Task Scheduler, disable
"Mice PC Assistant Watchdog"). The log is `.local/rc_watchdog.log`.
