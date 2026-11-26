#!/usr/bin/env python3
"""Make sure the PC assistant's keep-running check is installed. Idempotent, no questions.

    python tools/pc_assistant_ensure.py            install it if it is not installed (what every AI runs when it starts a task)
    python tools/pc_assistant_ensure.py --status   one plain line: on / off / turned off by the user
    python tools/pc_assistant_ensure.py --off      the user stopped the assistant: AIs must not turn it on again
    python tools/pc_assistant_ensure.py --on       clear that flag (the Start launcher does)

User 2026-11-27: whichever AI starts a task (Claude, GPT Codex, Gemini) turns the check on itself, nobody double-clicks.
The check still has NO logon trigger and removes itself at a shutdown / restart (tools/rc_watchdog.ps1); after a restart the
user's first message to any AI means "continue", and the AI runs this again. "Stop PC Assistant" writes the off flag, so a
stopped assistant is not switched back on behind the user's back.
Tests pass --root, --task-name and --script so nothing real is touched.
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def task_name(root):
    text = (root / "config" / "rc_watchdog.json").read_text(encoding="utf-8")
    return json.loads(re.sub(r"(?m)^\s*//.*$", "", text))["taskName"]


def installed(name):
    r = subprocess.run(["schtasks", "/Query", "/TN", name], capture_output=True, text=True,
                       creationflags=0x08000000 if sys.platform == "win32" else 0)
    return r.returncode == 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--off", action="store_true")
    ap.add_argument("--on", action="store_true")
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--task-name", default="")
    ap.add_argument("--script", default="", help="run this script instead of the real watchdog (tests)")
    a = ap.parse_args(argv)
    root = Path(a.root)
    flag = root / ".local" / "pc_assistant_off.json"
    name = a.task_name or task_name(root)

    if a.off:
        flag.parent.mkdir(exist_ok=True)
        flag.write_text(json.dumps({"why": "the user stopped the PC assistant"}), encoding="utf-8")
        print("The PC assistant is turned off; no AI will turn it on again until you open Start PC Assistant.")
        return 0
    if a.on:
        flag.unlink(missing_ok=True)
        print("The PC assistant may be turned on again.")
        return 0
    if flag.exists():
        print("The PC assistant is turned off by the user (Stop PC Assistant); not installing the keep-running check.")
        return 0
    if sys.platform != "win32":
        print("The keep-running check is a Windows Scheduled Task; nothing to do on this system.")
        return 0
    if a.status:
        print("The keep-running check is %s." % ("on" if installed(name) else "off"))
        return 0
    if installed(name):
        print("The keep-running check is already on.")
        return 0
    cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
           str(HERE / "rc_watchdog_install.ps1"), "-NoStart", "-TaskName", name]
    if a.script:
        cmd += ["-Script", a.script]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120, creationflags=0x08000000)
    if r.returncode != 0:
        print("Could not turn on the keep-running check: %s" % (r.stderr or r.stdout).strip()[-200:])
        return 1
    print("Turned on the keep-running check (low priority, no window; it removes itself when the PC restarts).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
