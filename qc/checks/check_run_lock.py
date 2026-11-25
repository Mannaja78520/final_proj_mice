"""Only one QC run at a time: a second run waits, a dead holder is taken over.

2026-11-25: two full runs on the PC clashed on the fake serial port and port 80
(WinError 10048) and each failed the other's timing checks. qc/lib/runlock.py is
the lock run_qc.py takes before it runs anything.
"""
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

    src = (F.QC / "run_qc.py").read_text(encoding="utf-8")
    t.ok("RunLock" in src and "--no-lock" in src,
         "run_qc.py takes the lock and offers --no-lock")
