"""One QC run at a time on this PC.

Two full runs at once clash on machine-wide things (fake serial port, port 80,
mDNS 5353, WinError 10048 "address already in use") and each makes the other's
timing checks fail. The lock is a file in the system temp dir holding the
holder's pid and start time. A second run WAITS and says who holds it. A lock
whose pid is no longer alive (a run that crashed or was killed) is taken over.
`--no-lock` on run_qc.py skips it, for a deliberate second run.
"""
import json
import os
import tempfile
import time
from pathlib import Path

LOCK_FILE = Path(tempfile.gettempdir()) / "mice_qc_run.lock"


def pid_alive(pid):
    """True if a process with this pid exists. Never raises."""
    if not isinstance(pid, int) or pid <= 0:
        return False
    if os.name == "nt":
        import ctypes
        k32 = ctypes.windll.kernel32
        h = k32.OpenProcess(0x1000, False, pid)      # QUERY_LIMITED_INFORMATION
        if not h:
            return False                              # no such process
        try:
            code = ctypes.c_ulong()
            if not k32.GetExitCodeProcess(h, ctypes.byref(code)):
                return True
            return code.value == 259                  # STILL_ACTIVE
        finally:
            k32.CloseHandle(h)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except OSError:
        return True
    return True


def holder(path=LOCK_FILE):
    """The lock's content as a dict, or None if absent or unreadable."""
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


class RunLock:
    def __init__(self, path=LOCK_FILE, pid=None, say=None, poll=2.0):
        self.path = Path(path)
        self.pid = pid or os.getpid()
        self.say = say or (lambda msg: None)
        self.poll = poll
        self.held = False

    def _try_create(self):
        try:
            fd = os.open(str(self.path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            return False
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump({"pid": self.pid, "started": time.strftime("%Y-%m-%d %H:%M:%S"),
                       "cwd": os.getcwd()}, f)
        return True

    def acquire(self, timeout=None):
        """Wait for the lock. True when held, False if `timeout` seconds passed."""
        deadline = None if timeout is None else time.time() + timeout
        told = None
        while True:
            if self._try_create():
                self.held = True
                return True
            cur = holder(self.path)
            if cur is not None and cur.get("pid") == self.pid:
                self.held = True
                return True
            if cur is not None and not pid_alive(cur.get("pid")):
                self.say("QC lock: holder pid %s is gone, taking over" % cur.get("pid"))
                try:
                    self.path.unlink()
                except OSError:
                    pass
                continue
            if cur is None:
                # half-written or just removed: look again shortly, never spin
                time.sleep(0.2)
            else:
                who = "pid %s since %s in %s" % (cur.get("pid"), cur.get("started"), cur.get("cwd"))
                if who != told:
                    self.say("QC lock: another QC run holds the machine (%s); waiting. "
                             "--no-lock skips this." % who)
                    told = who
                time.sleep(self.poll)
            if deadline is not None and time.time() > deadline:
                return False

    def release(self):
        if not self.held:
            return
        cur = holder(self.path)
        if cur is None or cur.get("pid") == self.pid:
            try:
                self.path.unlink()
            except OSError:
                pass
        self.held = False
