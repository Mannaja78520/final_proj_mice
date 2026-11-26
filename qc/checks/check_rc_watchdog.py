"""The PC assistant watchdog decides correctly, and its install / launchers work.

User 2026-11-26/27: the remote-control session dropped, work was left unfinished, and the user had to type the
command by hand each time. tools/rc_watchdog.ps1 (run by a low-priority Scheduled Task) keeps ONE session for this
folder running. Its decision logic is a pure function, tested here with made-up process lists, connection counts,
heartbeat ages and limit times (no real claude process is touched); the Scheduled Task is installed and removed
under a throwaway name with a harmless script; the double-click launchers are checked.
"""
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import qc as F

AREA = "tooling"
TITLE = "the PC assistant watchdog restarts what is down, leaves everything else alone, and installs cleanly"

CFG = {"minConnections": 1, "unhealthyChecksBeforeRestart": 2, "maxRelaunchesPerHour": 3,
       "minLogonAgeSeconds": 90, "stallMinutes": 90, "stallAction": "restart"}
PROFILE = r"C:\Users\someone"
RC = '"%s\\.local\\bin\\claude.exe" remote-control --permission-mode bypassPermissions --spawn same-dir' % PROFILE
NOW = 1_800_000_000


def proc(pid, cmd=RC, name="claude.exe"):
    return {"Id": pid, "Name": name, "CommandLine": cmd}


def decide(box, **kw):
    inp = {"Config": dict(CFG, **kw.pop("cfg", {})), "Now": NOW, "LogonAgeSeconds": 600, "ProfileDir": PROFILE,
           "ExeExists": True, "State": None, "Procs": [], "Connections": {}, "HeartbeatAgeMinutes": None,
           "DoingTasks": 0, "ClaudeLimitedUntil": None, "BootEpochNow": NOW - 5000,
           "LogonEpochNow": NOW - 4000, "Install": None, "ShutdownRecent": False}
    inp.update(kw)
    path = box / "in.json"
    path.write_text(json.dumps(inp), encoding="utf-8")
    r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                        str(F.CODE / "tools" / "rc_watchdog.ps1"), "-DecideJson", str(path)],
                       capture_output=True, text=True, timeout=60)
    try:
        return json.loads(r.stdout)
    except ValueError:
        return {"Action": "ERROR", "Reason": (r.stdout + r.stderr)[-200:]}


def run(t):
    if os.name != "nt":
        t.ok(True, "the watchdog is a Windows PowerShell tool; nothing to run in the cloud")
        return
    box = Path(tempfile.mkdtemp(prefix="qc_rcwd_"))

    d = decide(box, Procs=[proc(10)], Connections={"10": 2})
    t.ok(d["Action"] == "adopt" and d["Pid"] == 10, "the one running session is adopted, not restarted", repr(d))
    d = decide(box, Procs=[proc(10)], Connections={"10": 2}, State={"pid": 10, "unhealthy": 0, "launches": []})
    t.ok(d["Action"] == "ok", "a running, connected session is left alone", repr(d))

    d = decide(box)
    t.ok(d["Action"] == "launch" and len(d["State"]["launches"]) == 1, "nothing running: it is started, and counted", repr(d))
    d = decide(box, ExeExists=False)
    t.ok(d["Action"] == "no-exe", "a missing claude.exe is reported, not retried blindly", repr(d))

    d = decide(box, Procs=[proc(10)], Connections={"10": 0}, State={"pid": 10, "unhealthy": 0, "launches": []})
    t.ok(d["Action"] == "unhealthy", "one check without a connection only warns", repr(d))
    d = decide(box, Procs=[proc(10)], Connections={"10": 0}, State={"pid": 10, "unhealthy": 1, "launches": []})
    t.ok(d["Action"] == "restart" and d["Pid"] == 10, "two in a row stop that one process and start it again", repr(d))

    recent = [NOW - 600, NOW - 1200, NOW - 1800]
    d = decide(box, State={"pid": 0, "unhealthy": 0, "launches": recent})
    t.ok(d["Action"] == "backoff", "three starts in the last hour: it waits instead of looping", repr(d))
    d = decide(box, State={"pid": 0, "unhealthy": 0, "launches": [NOW - 7200, NOW - 8000, NOW - 9000]})
    t.ok(d["Action"] == "launch", "starts older than an hour no longer count", repr(d))

    d = decide(box, Procs=[proc(10), proc(11)], Connections={"10": 1, "11": 1})
    t.ok(d["Action"] == "ambiguous" and d["Pid"] == 0, "two sessions: it touches neither", repr(d))
    others = [proc(20, name="Claude.exe", cmd='"C:\\Program Files\\WindowsApps\\Claude\\app\\Claude.exe"'),
              proc(21, cmd='"%s\\.local\\bin\\claude.exe" --print --sdk-url x' % PROFILE),
              proc(22, cmd='"D:\\other\\claude.exe" remote-control --spawn same-dir')]
    d = decide(box, Procs=others)
    t.ok(d["Action"] == "launch" and d["Pid"] == 0,
         "the desktop app, other claude sessions and another install are never mistaken for it", repr(d))

    d = decide(box, LogonAgeSeconds=10)
    t.ok(d["Action"] == "wait", "it does nothing in the first seconds after logon", repr(d))

    d = decide(box, ClaudeLimitedUntil=NOW + 3600)
    t.ok(d["Action"] == "limited", "at a usage limit it waits for the reset (the AI watcher hands the work on)", repr(d))
    d = decide(box, ClaudeLimitedUntil=NOW - 60)
    t.ok(d["Action"] == "launch", "after the reset time it starts Claude again", repr(d))

    base = dict(Procs=[proc(10)], Connections={"10": 3}, State={"pid": 10, "unhealthy": 0, "launches": []})
    d = decide(box, HeartbeatAgeMinutes=120, DoingTasks=2, **base)
    t.ok(d["Action"] == "restart" and "stalled" in d["Reason"], "no heartbeat for 90+ minutes while tasks are in progress = stalled", repr(d))
    d = decide(box, HeartbeatAgeMinutes=10, DoingTasks=2, **base)
    t.ok(d["Action"] == "ok", "a recent heartbeat is a working session", repr(d))
    d = decide(box, HeartbeatAgeMinutes=500, DoingTasks=0, **base)
    t.ok(d["Action"] == "ok", "an idle session (no task in progress) is not stalled however quiet", repr(d))
    d = decide(box, HeartbeatAgeMinutes=120, DoingTasks=2, cfg={"stallAction": "log"}, **base)
    t.ok(d["Action"] == "stalled", "stallAction log only reports", repr(d))
    d = decide(box, HeartbeatAgeMinutes=120, DoingTasks=2, cfg={"stallAction": "off"}, **base)
    t.ok(d["Action"] == "ok", "stallAction off ignores it", repr(d))

    # it removes itself when the PC shuts down / restarts / the user logs in again (user 2026-11-27)
    inst = {"boot": NOW - 5000, "logon": NOW - 4000, "task": "x"}
    d = decide(box, Install=inst)
    t.ok(d["Action"] == "launch", "installed in this same session: it carries on working", repr(d))
    d = decide(box, Install=inst, ShutdownRecent=True)
    t.ok(d["Action"] == "self-remove" and "shutting down" in d["Reason"], "a shutdown / restart event: it removes itself", repr(d))
    d = decide(box, Install=inst, BootEpochNow=NOW - 100)
    t.ok(d["Action"] == "self-remove", "a different boot time than at install: it removes itself and does nothing else", repr(d))
    d = decide(box, Install=inst, LogonEpochNow=NOW - 100)
    t.ok(d["Action"] == "self-remove",
         "a different logon time (Fast Startup keeps the boot time across Shut down) also removes it", repr(d))
    d = decide(box, Install=inst, BootEpochNow=NOW - 100, Procs=[proc(10)], Connections={"10": 0},
               State={"pid": 10, "unhealthy": 5, "launches": []})
    t.ok(d["Action"] == "self-remove" and d["Pid"] == 0, "and it never restarts anything on its way out", repr(d))
    d = decide(box, Install=None, BootEpochNow=NOW - 100)
    t.ok(d["Action"] == "launch", "without an install record it does not remove itself (a test or manual run)", repr(d))

    # stopping: only the session it manages, and a dry run says so
    r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                        str(F.CODE / "tools" / "rc_watchdog.ps1"), "-StopSession", "-DryRun"],
                       capture_output=True, text=True, timeout=60)
    t.ok(r.stdout.strip().startswith(("would stop pid", "nothing to stop")), "-StopSession -DryRun only says what it would do", r.stdout[:100] + r.stderr[:100])

    # the Scheduled Task, under a throwaway name and a harmless script
    name = "MiceRcWatchdogQC%d" % os.getpid()
    marker = box / "ran.txt"
    dummy = box / "dummy.ps1"
    dummy.write_text("Set-Content -Path '%s' -Value ok" % str(marker).replace("'", "''"), encoding="utf-8")
    ps = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File"]
    inst = F.CODE / "tools" / "rc_watchdog_install.ps1"
    uninst = F.CODE / "tools" / "rc_watchdog_uninstall.ps1"
    try:
        for _ in range(2):                                       # twice: safe to repeat
            r = subprocess.run(ps + [str(inst), "-TaskName", name, "-Script", str(dummy)],
                               capture_output=True, text=True, timeout=90)
        t.ok("installed" in r.stdout, "the task installs, also when it already exists", (r.stdout + r.stderr)[-200:])
        info = subprocess.run(["powershell", "-NoProfile", "-Command",
                               "$t = Get-ScheduledTask -TaskName '%s'; "
                               "'{0} {1} {2} {3}' -f $t.Settings.Priority, $t.Settings.Hidden, $t.Principal.RunLevel, "
                               "(($t.Triggers | ForEach-Object { $_.CimClass.CimClassName }) -join ',')" % name],
                              capture_output=True, text=True, timeout=60).stdout.split()
        t.ok(info[:3] == ["7", "True", "Limited"],
             "it is low priority, hidden and needs no admin", repr(info))
        kinds = info[3] if len(info) > 3 else ""
        t.ok("MSFT_TaskTimeTrigger" in kinds and "MSFT_TaskEventTrigger" in kinds and "Logon" not in kinds,
             "it repeats every few minutes and wakes on the shutdown / restart event, and has NO logon trigger", kinds)
        end = time.time() + 30
        while not marker.exists() and time.time() < end:
            time.sleep(0.5)
        t.ok(marker.exists(), "the task really runs its script")
    finally:
        r1 = subprocess.run(ps + [str(uninst), "-TaskName", name], capture_output=True, text=True, timeout=60)
        r2 = subprocess.run(ps + [str(uninst), "-TaskName", name], capture_output=True, text=True, timeout=60)
    t.ok("removed" in r1.stdout and "not installed" in r2.stdout,
         "uninstall removes it, and running it again is harmless", (r1.stdout + r2.stdout)[-160:])

    # the double-click launchers
    ldir = F.CODE / "main_python" / "launchers"
    start = (ldir / "Start PC Assistant.bat").read_text(encoding="utf-8") if (ldir / "Start PC Assistant.bat").is_file() else ""
    stop = (ldir / "Stop PC Assistant.bat").read_text(encoding="utf-8") if (ldir / "Stop PC Assistant.bat").is_file() else ""
    t.ok("rc_watchdog_install.ps1" in start and "rc_watchdog.ps1" in start and "%~dp0" in start,
         "Start PC Assistant turns on the check and starts the assistant, from its own folder", start[:80])
    t.ok("rc_watchdog_uninstall.ps1" in stop and "-StopSession" in stop and ":\\" not in start + stop,
         "Stop PC Assistant turns the check off and stops only that session; no hardcoded drive paths", stop[:80])
    r = subprocess.run([sys.executable, str(F.CODE / "tools" / "make_launchers.py"), "--check"],
                       capture_output=True, text=True, timeout=60)
    t.ok(r.returncode == 0, "the launchers are generated from data and current", r.stdout[-120:])
