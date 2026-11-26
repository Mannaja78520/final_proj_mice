#!/usr/bin/env python3
"""SessionStart hint: which tasks are still marked "Doing now", so a session that was dropped and came
back (or was relaunched by tools/rc_watchdog.ps1) knows what to resume without being told.

Prints the JSON a SessionStart hook returns (hookSpecificOutput.additionalContext), or nothing when no
task is in progress. `claude remote-control` has no initial-prompt option (checked 2026-11-27), so this
hint is what a fresh session sees; it still needs a first message (the project thread's wake) to start.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IDLE = re.compile(r"^(paused|nothing|none|done|-|n/a)", re.I)


def doing_tasks(root=ROOT):
    out = []
    for f in sorted((root / "handoff" / "tasks").glob("*.md")):
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        m = re.search(r"(?ms)^##\s+Doing now\s*\r?\n+([^\r\n]+)", text)
        if m and not IDLE.match(m.group(1).strip()):
            out.append((f.name, m.group(1).strip()[:160]))
    return out


def hint(root=ROOT):
    tasks = doing_tasks(root)
    hb = None
    try:
        hb = json.loads((root / ".local" / "rc_heartbeat.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        pass
    if not tasks:
        return ""
    lines = ["RESUME: this session may be a reconnect. Unfinished work is marked 'Doing now' in handoff/tasks: "
             + "; ".join("%s (%s)" % t for t in tasks[:6]) + "."]
    if hb:
        lines.append("Last heartbeat %s: %s / %s." % (hb.get("time"), hb.get("task"), hb.get("step")))
    lines.append("Read HANDOFF.md and those task files, continue the work, do not ask. Then send ONE line to the "
                 "parent thread (send_message) saying you are back and what you resume.")
    return " ".join(lines)


def main():
    h = hint()
    if h:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": h}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
