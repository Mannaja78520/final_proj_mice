"""QC leaves no browser behind, even when the runner is killed hard.

2026-11-26: 119 headless Edge processes from QC runs were still alive on the PC (up
to 67 h old, ~4 GB). A browser is started through PowerShell, so it is not a child of the
check; a killed runner, a check killed at its hard limit or a Ctrl+C left it running.
This proves the layers in qc/lib/jobguard.py with REAL processes: (1) a runner killed
hard takes its children and a detached grandchild with it (job object); (2) the startup
sweep kills a browser whose owner is dead and never one whose owner is alive; (3) the
sweep ignores processes that are not QC browsers; (4) too-old browsers are listed.
"""
import os
import subprocess
import sys
import time

import qc as F

AREA = "tooling"
TITLE = "QC leaves no browser behind: a killed runner takes its children along, stale ones are swept"

SLEEP = "import time; time.sleep(300)"


def _alive(pid):
    import runlock
    return runlock.pid_alive(pid)


def _wait_gone(pid, secs=15):
    end = time.time() + secs
    while time.time() < end:
        if not _alive(pid):
            return True
        time.sleep(0.25)
    return not _alive(pid)


def run(t):
    import jobguard
    lib = str(F.QC / "lib")

    # ---- (1) hard-killed runner: children and a detached grandchild die with it ----
    if os.name == "nt":
        runner_src = (
            "import subprocess, sys, time\n"
            "sys.path.insert(0, %r)\n"
            "import jobguard\n"
            "assert jobguard.install(), 'job object not available'\n"
            "child = subprocess.Popen([sys.executable, '-c', %r])\n"
            # a grandchild whose parent exits at once: exactly how Start-Process leaves Edge
            "mid = subprocess.Popen([sys.executable, '-c', \"import subprocess, sys; "
            "p = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(300)'], "
            "creationflags=0x00000008); print(p.pid, flush=True)\"], stdout=subprocess.PIPE, text=True)\n"
            "gpid = int(mid.stdout.readline())\n"
            "print(child.pid, gpid, flush=True)\n"
            "time.sleep(300)\n" % (lib, SLEEP))
        runner = subprocess.Popen([sys.executable, "-c", runner_src], stdout=subprocess.PIPE, text=True)
        try:
            line = runner.stdout.readline().split()
            ok = len(line) == 2
            t.ok(ok, "the runner started a child and a detached grandchild", repr(line))
            if ok:
                child, grand = int(line[0]), int(line[1])
                t.ok(_alive(child) and _alive(grand), "both are alive while the runner lives")
                runner.kill()                                  # TerminateProcess: no atexit, no finally
                runner.wait(timeout=30)
                t.ok(_wait_gone(child), "a hard-killed runner takes its child with it",
                     "child %d survived" % child)
                t.ok(_wait_gone(grand), "and a grandchild whose parent had already exited",
                     "grandchild %d survived (an orphaned browser)" % grand)
                for p in (child, grand):
                    if _alive(p):
                        subprocess.run(["taskkill", "/F", "/PID", str(p)], capture_output=True)
        finally:
            if runner.poll() is None:
                runner.kill()
    else:
        t.ok(True, "job objects are Windows-only: the cloud run has no PowerShell-launched browsers")

    # ---- (2)(3)(4) the startup sweep, on fake browsers (python.exe carrying the QC tag) ----
    image = os.path.basename(sys.executable)
    gone = subprocess.Popen([sys.executable, "-c", "pass"])
    gone.wait()
    me = os.getpid()

    def fake(owner):
        return subprocess.Popen([sys.executable, "-c", SLEEP, "--MICEQCBROWSER%dEND" % owner])
    dead_owner, live_owner = fake(gone.pid), fake(me)
    plain = subprocess.Popen([sys.executable, "-c", SLEEP])          # not a QC browser at all
    try:
        time.sleep(1.0)
        if os.name == "nt":
            listed = {p for p, _o, _a in jobguard.stale_browsers(image)}
            t.ok(dead_owner.pid in listed, "a browser whose owner is dead is listed as stale")
            t.ok(live_owner.pid not in listed and plain.pid not in listed,
                 "a live owner's browser and unrelated processes are not", repr(sorted(listed)))
            old = {p for p, _o, _a in jobguard.stale_browsers(image, max_age=-5)}
            t.ok(live_owner.pid in old and plain.pid not in old,
                 "a browser older than the age limit is stale whoever owns it", repr(sorted(old)))
            jobguard.kill_stale(image)
            t.ok(_wait_gone(dead_owner.pid), "the sweep kills the dead owner's browser")
            t.ok(_alive(live_owner.pid), "and leaves the live owner's browser running")
            t.ok(_alive(plain.pid), "and any process that is not a QC browser")
        else:
            t.ok(True, "process listing by PowerShell is Windows-only")
    finally:
        for p in (dead_owner, live_owner, plain):
            if p.poll() is None:
                p.kill()

    src = (F.QC / "run_qc.py").read_text(encoding="utf-8")
    t.ok("jobguard.install(" in src and "jobguard.kill_stale()" in src and "jobguard.left_behind(" in src,
         "run_qc.py joins the job at start, sweeps at start and checks at the end")
