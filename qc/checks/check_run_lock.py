"""Only one QC run at a time: a second run waits, a dead holder is taken over.

2026-11-25: two full runs on the PC clashed on the fake serial port and port 80
(WinError 10048) and each failed the other's timing checks. qc/lib/runlock.py is
the lock run_qc.py takes before it runs anything.
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import qc as F

AREA = "tooling"
TITLE = "a second QC run waits for the first; a dead holder's lock is taken over"


def run(t):
    import runlock
    d = Path(tempfile.mkdtemp(prefix="qc_lock_"))
    path = d / "run.lock"
    notes = []
    first = runlock.RunLock(path, say=notes.append)
    t.ok(first.acquire(timeout=1), "the first run gets the lock")

    # a second run, as a different live process, must not get it
    second = runlock.RunLock(path, pid=1, say=notes.append, poll=0.1)
    t.ok(runlock.pid_alive(first.pid), "the holder pid reads as alive")
    # pid=1 is not our pid, so it is a rival; holder is us (alive) -> waits
    os.environ.pop(runlock.OWNER_ENV, None)      # a rival is not a child of the holder
    got = second.acquire(timeout=0.6)
    t.ok(not got, "a second run does not get it while the first is alive", str(got))
    t.ok(any("waiting" in n and str(first.pid) in n for n in notes),
         "the waiting run says who holds the lock", repr(notes))

    first.release()
    t.ok(not path.exists(), "release removes the lock file")
    t.ok(second.acquire(timeout=1), "the waiting run gets it once released")
    second.release()

    # stale: a holder whose process has ended
    p = subprocess.Popen([sys.executable, "-c", "pass"])
    p.wait()
    path.write_text('{"pid": %d, "started": "x", "cwd": "x"}' % p.pid, encoding="utf-8")
    t.ok(not runlock.pid_alive(p.pid), "an ended process reads as dead")
    third = runlock.RunLock(path, say=notes.append)
    t.ok(third.acquire(timeout=1), "a dead holder's lock is taken over")
    third.release()

    # A run started BY the holder (a check that runs QC, e.g. sabotage.py) must
    # not wait for its own parent: 2026-11-25 three scheduled runs hung that way.
    holder_lock = runlock.RunLock(path, say=notes.append)
    t.ok(holder_lock.acquire(timeout=1), "a holder takes the lock again for the next case")
    code = ("import sys; sys.path.insert(0, r'%s'); import runlock; "
            "from pathlib import Path; "
            "l = runlock.RunLock(Path(r'%s'), say=print, poll=0.1); "
            "sys.exit(0 if l.acquire(timeout=3) else 7)" % (F.QC / "lib", path))
    child = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                           timeout=60)
    t.ok(child.returncode == 0, "a run started by the holder does not wait for its lock",
         "rc %s %s" % (child.returncode, child.stdout[-200:]))
    env = dict(os.environ)
    env.pop(runlock.OWNER_ENV, None)
    outsider = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                              timeout=60, env=env)
    t.ok(outsider.returncode == 7, "an unrelated run still waits for it",
         "rc %s" % outsider.returncode)
    holder_lock.release()

    src = (F.QC / "run_qc.py").read_text(encoding="utf-8")
    t.ok("RunLock" in src and "--no-lock" in src,
         "run_qc.py takes the lock and offers --no-lock")
