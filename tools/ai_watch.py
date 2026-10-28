#!/usr/bin/env python3
"""Watch every AI worker for usage limits; resume after the reset or hand the work on.

    python tools/ai_watch.py run                 the watcher loop (one per PC; install starts it)
    python tools/ai_watch.py tick                one pass, then exit
    python tools/ai_watch.py status              limits, scheduled and running jobs, last events
    python tools/ai_watch.py parse "<text>" [--provider codex]   what the watcher would read from a message
    python tools/ai_watch.py install | uninstall start at logon (Task Scheduler, else the Startup folder)

User 2026-10-29: Codex and Gemini stop at a usage limit and never come back by
themselves; Claude does, but a weekly limit leaves its work stuck for days.
Rules and commands are in config/ai_watch.json; state and logs in _out/ai_watch/.
The logon entry runs a small launcher (%LOCALAPPDATA%/MiceAIWatch/launch.py)
that tries the renamed repo, the old name, then the copy install ran from, so
the code -> mice_system rename and the merge need no new install.
"""
import argparse
import datetime as dt
import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from layout import RepoLayout  # noqa: E402  one root rule for every tool (A51-1)
from limitwatch.jobs import pid_alive  # noqa: E402
from limitwatch.watcher import Watcher  # noqa: E402

LAYOUT = RepoLayout(Path(__file__).resolve().parent)
TASK = "MiceAIWatch"
STARTUP = Path(os.environ.get("APPDATA", "")) / r"Microsoft\Windows\Start Menu\Programs\Startup" / (TASK + ".vbs")


def load_cfg(path=None):
    return json.loads(Path(path or LAYOUT.work / "config" / "ai_watch.json").read_text(encoding="utf-8"))


def make(args):
    return Watcher(load_cfg(args.config), Path(args.out or LAYOUT.out("ai_watch")), LAYOUT.real)


def cmd_run(args):
    w = make(args)
    pidf = w.out / "watcher.pid"
    w.out.mkdir(parents=True, exist_ok=True)
    try:
        old = int(pidf.read_text())
    except (OSError, ValueError):
        old = 0
    if old and old != os.getpid() and pid_alive(old):
        print("already running, pid %d" % old)
        return 0
    pidf.write_text(str(os.getpid()))
    w.event("WATCHER START pid=%d" % os.getpid())
    w.save()
    while True:
        try:
            w.tick()
        except Exception as e:  # a bad line must not kill the watcher
            w.event("ERROR %r" % e)
            w.save()
        time.sleep(w.cfg["poll_seconds"])


def cmd_tick(args):
    make(args).tick()
    return cmd_status(args)


def cmd_status(args):
    w = make(args)
    pid = (w.out / "watcher.pid").read_text().strip() if (w.out / "watcher.pid").exists() else ""
    print("watcher: %s" % ("running pid " + pid if pid and pid_alive(pid) else "not running"))
    for p, until in w.state["limited"].items():
        t = dt.datetime.fromisoformat(until)
        if t > w.now():
            print("limited: %s until %s" % (p, t.astimezone().strftime("%Y-%m-%d %H:%M")))
    for j in w.state["jobs"]:
        if j["status"] in ("pending", "running") or args.all:
            print("job %s %-7s %-6s %-8s due %s %s" % (j["id"], j["kind"], j["provider"], j["status"],
                                                   j["due_local"], j.get("log", "")))
    for g in w.state["goals"].values():
        print("goal %s %s from %s -> %s rounds %d %s" % (g["id"], g["repo"], g["from"], g.get("worker"),
                                                       g["rounds"], g.get("finished", "open")))
    for e in w.state["events"][-args.events:]:
        print("  " + e)
    return 0


def cmd_parse(args):
    w = make(args)
    at = dt.datetime.fromisoformat(args.at) if args.at else dt.datetime.now().astimezone()
    reset = w.clock.parse(args.text, at)
    far = dt.timedelta(hours=w.cfg["handoff_if_reset_over_hours"])
    long = w.matcher.is_long(args.provider, args.text) or bool(reset and reset - at > far)
    print(json.dumps({"limit": w.matcher.is_limit(args.provider, args.text),
                      "reset": reset and reset.isoformat(), "long": long,
                      "action": "handoff" if long else
                      ("none (resumes itself)" if w.providers[args.provider].get("auto_resume")
                       else "resume at %s" % (reset + dt.timedelta(seconds=w.cfg["resume_delay_seconds"])
                                              ).isoformat() if reset else "retry later")}, indent=1))
    return 0


def _pythonw():
    pw = Path(sys.executable).with_name("pythonw.exe")
    return str(pw if pw.exists() else sys.executable)


def roots(layout=LAYOUT):
    """Where the watcher may live, best first: the renamed repo, the old name,
    then this copy. The logon entry tries them in order at every start, so the
    code -> mice_system rename, the merge to main and a cleaned .staging need no
    second install (coordinator 2026-10-29)."""
    rename = layout.data.get("pc", {}).get("rename", {})
    parent = layout.real.parent
    bases = [parent / rename[k] for k in ("to", "from") if rename.get(k)] + [layout.real]
    try:  # the copy install ran from, also where it sits after the rename
        rel = Path(layout.work).relative_to(layout.real)
    except ValueError:
        rel = None
    found = bases + ([b / rel for b in bases] if rel and rel.parts else []) + [layout.work]
    return [str(p) for p in dict.fromkeys(found)]


LAUNCHER = '''import os, subprocess, sys
# Written by tools/ai_watch.py install. Starts the first watcher found.
for root in %r:
    script = os.path.join(root, "tools", "ai_watch.py")
    if os.path.isfile(script):
        sys.exit(subprocess.call([sys.executable, script, "run"], cwd=root))
'''
LAUNCH_FILE = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / TASK / "launch.py"


def cmd_install(args):
    LAUNCH_FILE.parent.mkdir(parents=True, exist_ok=True)
    LAUNCH_FILE.write_text(LAUNCHER % roots(), encoding="utf-8")
    line = '"%s" "%s"' % (_pythonw(), LAUNCH_FILE)
    r = subprocess.run(["schtasks", "/Create", "/TN", TASK, "/SC", "ONLOGON", "/RL", "LIMITED",
                        "/TR", line, "/F"], capture_output=True, text=True)
    if r.returncode == 0:
        print("logon task %s: %s" % (TASK, line))
    else:  # ONLOGON needs admin on some PCs: the Startup folder needs nothing
        STARTUP.write_text('CreateObject("WScript.Shell").Run "%s", 0, False\r\n'
                           % line.replace('"', '""'), encoding="utf-8")
        print("Task Scheduler refused (%s); startup entry %s" % (r.stderr.strip()[:120], STARTUP))
    print("tries, in order: " + " | ".join(roots()))
    subprocess.Popen([_pythonw(), str(LAUNCH_FILE)], cwd=str(LAYOUT.work),
                     creationflags=0x00000008 | 0x00000200 if os.name == "nt" else 0)
    print("started")
    return 0


def cmd_uninstall(args):
    subprocess.run(["schtasks", "/Delete", "/TN", TASK, "/F"], capture_output=True)
    for f in (STARTUP, LAUNCH_FILE):
        if f.exists():
            f.unlink()
    print("removed the logon entry (a running watcher keeps going until the PC restarts or it is killed)")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--config")
    ap.add_argument("--out")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("run", "tick", "install", "uninstall"):
        sub.add_parser(name)
    st = sub.add_parser("status")
    st.add_argument("--all", action="store_true")
    st.add_argument("--events", type=int, default=15)
    pa = sub.add_parser("parse")
    pa.add_argument("text")
    pa.add_argument("--provider", default="codex")
    pa.add_argument("--at")
    args = ap.parse_args(argv)
    if args.cmd == "tick":
        args.all, args.events = False, 15
    return globals()["cmd_" + args.cmd](args) or 0


if __name__ == "__main__":
    sys.exit(main())
