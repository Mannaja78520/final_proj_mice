#!/usr/bin/env python3
"""Watch every AI worker for usage limits; resume after the reset or hand the work on.

    python tools/ai_watch.py start | stop        turn the watcher ON / OFF (in the background, low priority)
    python tools/ai_watch.py status              ON/OFF, limits, scheduled and running jobs, last events
    python tools/ai_watch.py install | uninstall put / remove the desktop shortcuts AI Watch ON and OFF
    python tools/ai_watch.py run                 the watcher loop itself, in this window (start runs it hidden)
    python tools/ai_watch.py tick                one pass, then exit
    python tools/ai_watch.py parse "<text>" [--provider codex]   what the watcher would read from a message

User 2026-10-29: Codex and Gemini stop at a usage limit and never come back by
themselves; Claude does, but a weekly limit leaves its work stuck for days.
Rules and commands are in config/ai_watch.json; state and logs in _out/ai_watch/.
User 2026-10-29 (later): never start at logon, it costs RAM and heat while
gaming or when no AI runs; the user turns it on and off from the desktop.
The shortcuts run a small launcher (%LOCALAPPDATA%/MiceAIWatch/launch.py) that
tries the renamed repo, the old name, then the copy install ran from, so the
code -> mice_system rename and the merge need no new install.
"""
import argparse
import datetime as dt
import json
import os
import signal
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


def control(cfg):
    return cfg.get("control", {})


# Windows priority class / POSIX nice per config name.
PRIORITY = {"idle": (0x40, 19), "below_normal": (0x4000, 10), "normal": (0x20, 0)}


def lower_priority(name):
    cls, nice = PRIORITY.get(name, PRIORITY["idle"])
    try:
        if os.name == "nt":
            import ctypes
            from ctypes import wintypes
            k = ctypes.windll.kernel32
            k.GetCurrentProcess.argtypes = []
            k.GetCurrentProcess.restype = wintypes.HANDLE
            k.SetPriorityClass.argtypes = [wintypes.HANDLE, wintypes.DWORD]
            k.SetPriorityClass.restype = wintypes.BOOL
            k.SetPriorityClass(k.GetCurrentProcess(), cls)
        elif nice:
            os.nice(nice)
    except Exception:  # a lower priority is a courtesy, never a reason not to watch
        pass


def watcher_pid(w):
    """The running watcher's pid, or 0. The loop touches watcher.pid after every
    pass, so a pid left by a crash or a reboot (and maybe reused by a game)
    goes stale after two passes instead of reading as ON forever."""
    pidf = w.out / "watcher.pid"
    try:
        pid = int(pidf.read_text().strip())
        age = time.time() - pidf.stat().st_mtime
    except (OSError, ValueError):
        return 0
    return pid if pid_alive(pid) and age < 2 * w.cfg["poll_seconds"] + 60 else 0


def wake_in(w):
    """Seconds to the next pass: the poll, or sooner when a resume falls due."""
    wait, now = w.cfg["poll_seconds"], w.now()
    for j in w.state["jobs"]:
        if j["status"] == "pending":
            due = (dt.datetime.fromisoformat(j["due"]) - now).total_seconds() + 1
            wait = min(wait, max(10, due))  # 10 s floor: a job that will not fire is no busy loop
    return wait


def nap(w, stop):
    """Sleep wake_in(), waking every stop_check_seconds only to look for the OFF flag."""
    end = time.time() + wake_in(w)
    step = control(w.cfg).get("stop_check_seconds", 2)
    while time.time() < end and not stop.exists():
        time.sleep(max(0.05, min(step, end - time.time())))


def cmd_run(args):
    w = make(args)
    pidf, stop = w.out / "watcher.pid", w.out / "stop"
    w.out.mkdir(parents=True, exist_ok=True)
    if watcher_pid(w) not in (0, os.getpid()):
        print("already running, pid %d" % watcher_pid(w))
        return 0
    lower_priority(control(w.cfg).get("priority", "idle"))
    stop.unlink(missing_ok=True)
    pidf.write_text(str(os.getpid()))
    w.event("WATCHER START pid=%d" % os.getpid())
    w.save()
    try:
        while not stop.exists():
            try:
                w.tick()
            except Exception as e:  # a bad line must not kill the watcher
                w.event("ERROR %r" % e)
                w.save()
            pidf.touch()
            nap(w, stop)
    finally:
        pidf.unlink(missing_ok=True)
        w.event("WATCHER STOP pid=%d" % os.getpid())
        w.save()
    return 0


def say(args, cfg, key, extra=""):
    """Print; from a desktop shortcut (pythonw, no console) also show a box."""
    text = control(cfg).get("messages", {}).get(key, key) + extra
    try:
        print(text)
    except UnicodeEncodeError:  # a non-UTF-8 console or pipe: the Thai text still goes in the box
        print(text.encode("ascii", "backslashreplace").decode())
    if getattr(args, "popup", False) and os.name == "nt":
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, text, "AI Watch", 0x40 | 0x10000 | 0x40000)


def cmd_start(args):
    w = make(args)
    if watcher_pid(w):
        say(args, w.cfg, "already_on")
        return 0
    w.out.mkdir(parents=True, exist_ok=True)
    (w.out / "stop").unlink(missing_ok=True)
    argv = [_pythonw(), str(Path(__file__).resolve())] + _common(args) + ["run"]
    flags = 0x00000008 | 0x00000200 | 0x08000000 if os.name == "nt" else 0  # detached, no window
    subprocess.Popen(argv, cwd=str(LAYOUT.work), creationflags=flags, start_new_session=os.name != "nt",
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(100):
        if watcher_pid(w):
            say(args, w.cfg, "on")
            return 0
        time.sleep(0.1)
    say(args, w.cfg, "stuck")
    return 1


def cmd_stop(args):
    """Raise the OFF flag; the loop sees it within stop_check_seconds and exits.
    A tick that hangs past stop_wait_seconds is killed. Resumed AI workers keep
    running: they are someone's work, not the watcher."""
    w = make(args)
    pid = watcher_pid(w)
    if not pid:
        say(args, w.cfg, "already_off")
        return 0
    (w.out / "stop").write_text("off", encoding="utf-8")
    end = time.time() + control(w.cfg).get("stop_wait_seconds", 20)
    while time.time() < end and pid_alive(pid):
        time.sleep(0.2)
    if pid_alive(pid):
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            pass
        time.sleep(1)
    if pid_alive(pid):
        say(args, w.cfg, "stuck")
        return 1
    (w.out / "watcher.pid").unlink(missing_ok=True)
    say(args, w.cfg, "off")
    return 0


def _common(args):
    return sum((["--" + k, getattr(args, k)] for k in ("config", "out") if getattr(args, k, None)), [])


def cmd_tick(args):
    make(args).tick()
    return cmd_status(args)


def cmd_status(args):
    w = make(args)
    pid = watcher_pid(w)
    print("AI Watch: %s" % ("ON (pid %d)" % pid if pid else "OFF"))
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
# Written by tools/ai_watch.py install. Runs the first watcher found with the
# shortcut's words (start / stop), so the rename and the merge need no reinstall.
for root in %r:
    script = os.path.join(root, "tools", "ai_watch.py")
    if os.path.isfile(script):
        sys.exit(subprocess.call([sys.executable, script] + sys.argv[1:], cwd=root))
'''
LAUNCH_FILE = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / TASK / "launch.py"


def desktop(cfg):
    """The real desktop (OneDrive moves it), unless config names one."""
    if control(cfg).get("desktop_dir"):
        return Path(os.path.expandvars(os.path.expanduser(control(cfg)["desktop_dir"])))
    if os.name == "nt":
        import ctypes
        buf = ctypes.create_unicode_buffer(260)
        if ctypes.windll.shell32.SHGetFolderPathW(None, 0x10, None, 0, buf) == 0:
            return Path(buf.value)
    return Path.home() / "Desktop"


def make_shortcut(folder, name, action):
    """A .lnk through PowerShell; where that is refused, a .vbs that runs hidden."""
    py, args = _pythonw(), '"%s" %s --popup' % (LAUNCH_FILE, action)
    lnk = folder / (name + ".lnk")
    q = lambda v: "'" + str(v).replace("'", "''") + "'"
    ps = ("$s=(New-Object -ComObject WScript.Shell).CreateShortcut(%s);$s.TargetPath=%s;$s.Arguments=%s;"
          "$s.WorkingDirectory=%s;$s.Description=%s;$s.Save()") % (q(lnk), q(py), q(args), q(LAUNCH_FILE.parent), q(name))
    try:
        ok = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
                            capture_output=True, timeout=60).returncode == 0 and lnk.exists()
    except (OSError, subprocess.TimeoutExpired):
        ok = False
    if ok:
        return lnk
    vbs = folder / (name + ".vbs")
    vbs.write_text('CreateObject("WScript.Shell").Run "%s", 0, False\r\n'
                   % ('"%s" %s' % (py, args)).replace('"', '""'), encoding="utf-8")
    return vbs


def remove_logon():
    """The first version (PR #105) started at logon; take that away."""
    try:
        subprocess.run(["schtasks", "/Delete", "/TN", TASK, "/F"], capture_output=True)
    except OSError:  # no Task Scheduler (not Windows)
        pass
    STARTUP.unlink(missing_ok=True)


def cmd_install(args):
    cfg = load_cfg(args.config)
    remove_logon()
    LAUNCH_FILE.parent.mkdir(parents=True, exist_ok=True)
    LAUNCH_FILE.write_text(LAUNCHER % roots(), encoding="utf-8")
    folder = desktop(cfg)
    folder.mkdir(parents=True, exist_ok=True)
    for sc in control(cfg).get("shortcuts", []):
        print("shortcut: %s" % make_shortcut(folder, sc["name"], sc["action"]))
    print("no logon start: double-click a shortcut to turn AI Watch ON or OFF")
    print("tries, in order: " + " | ".join(roots()))
    return 0


def cmd_uninstall(args):
    cfg = load_cfg(args.config)
    args.popup = False
    cmd_stop(args)
    remove_logon()
    folder = desktop(cfg)
    for sc in control(cfg).get("shortcuts", []):
        for ext in (".lnk", ".vbs"):
            (folder / (sc["name"] + ext)).unlink(missing_ok=True)
    LAUNCH_FILE.unlink(missing_ok=True)
    print("removed the desktop shortcuts and the launcher")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--config")
    ap.add_argument("--out")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("run", "tick", "install", "uninstall", "start", "stop"):
        sub.add_parser(name).add_argument("--popup", action="store_true", help="show a box (desktop shortcut)")
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
