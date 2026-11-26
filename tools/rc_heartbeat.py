#!/usr/bin/env python3
"""Heartbeat for the PC assistant watchdog (tools/rc_watchdog.ps1).

    python tools/rc_heartbeat.py write --task <task file name> --step "what I am doing"
    python tools/rc_heartbeat.py show

The session writes this at every checkpoint (the same moments it updates "## Doing now" in its task
file). The watchdog reads the file's age: connected but silent for stallMinutes while a task says
"Doing now" = stalled (config/rc_watchdog.json). One small JSON file, git-ignored: .local/rc_heartbeat.json.
"""
import json
import sys
import time
from pathlib import Path

PATH = Path(__file__).resolve().parent.parent / ".local" / "rc_heartbeat.json"


def write(task, step):
    PATH.parent.mkdir(exist_ok=True)
    PATH.write_text(json.dumps({"time": time.strftime("%Y-%m-%d %H:%M:%S"), "epoch": int(time.time()),
                                "task": task, "step": step}, ensure_ascii=False), encoding="utf-8")


def read():
    try:
        return json.loads(PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def main(argv):
    if argv and argv[0] == "write":
        def arg(name):
            return argv[argv.index(name) + 1] if name in argv and argv.index(name) + 1 < len(argv) else ""
        write(arg("--task"), arg("--step"))
        return 0
    got = read()
    print(json.dumps(got, ensure_ascii=False) if got else "no heartbeat yet")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
