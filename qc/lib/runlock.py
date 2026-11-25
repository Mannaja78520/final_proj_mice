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
# Set by the process that holds the lock, inherited by everything it starts.
# A check that runs QC itself (check_dev_tools -> tools/sabotage.py -> run_qc.py)
# is PART of the holder's run; without this it waited for its own parent's lock
# forever: three scheduled full runs stalled at ~340 of 415 checks, 2026-11-25.
OWNER_ENV = "MICE_QC_LOCK_OWNER"
# First come, first served. Waiters take a numbered ticket in this folder and only
# the lowest LIVE ticket may take the lock. Before, every waiter polled and whoever
# polled at the right instant won: one run waited 40 minutes behind runs that
# arrived after it (2026-11-26).
QUEUE_DIR = Path(tempfile.gettempdir()) / "mice_qc_queue"


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


def inherited(path=LOCK_FILE):
    """True when this process was started by the live process that holds the lock."""
    raw = os.environ.get(OWNER_ENV, "")
    cur = holder(path)
    return bool(raw.isdigit() and cur and str(cur.get("pid")) == raw
                and pid_alive(int(raw)))


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

    def _queue(self):
        """The tickets for THIS lock file (a test lock has its own queue)."""
        return QUEUE_DIR / self.path.name

    def _first_in_line(self, ticket):
        """True when no earlier ticket belongs to a live process. Dead ones are removed."""
        for t in sorted(self._queue().glob("*.ticket")):
            if t == ticket:
                return True
            pid = t.stem.split("_")[-1]
            if pid.isdigit() and pid_alive(int(pid)):
                return False
            try:
                t.unlink()
            except OSError:
                pass
        return True

    @staticmethod
    def _drop(ticket):
        if ticket is not None:
            try:
                ticket.unlink()
            except OSError:
                pass

    def acquire(self, timeout=None):
        """Wait for the lock, in arrival order. True when held, False after `timeout` s."""
        deadline = None if timeout is None else time.time() + timeout
        told = None
        ticket = None
        try:
            self._queue().mkdir(parents=True, exist_ok=True)
            ticket = self._queue() / ("%020d_%d.ticket" % (time.time_ns(), self.pid))
            ticket.write_text("x", encoding="utf-8")
        except OSError:
            ticket = None                 # no queue available: plain polling as before
        try:
            while True:
                if inherited(self.path):
                    return True           # nested run: the parent's lock covers it
                if (ticket is None or self._first_in_line(ticket)) and self._try_create():
                    self.held = True
                    os.environ[OWNER_ENV] = str(self.pid)
                    return True
                cur = holder(self.path)
                if cur is not None and cur.get("pid") == self.pid:
                    self.held = True
                    os.environ[OWNER_ENV] = str(self.pid)
                    return True
                if cur is not None and not pid_alive(cur.get("pid")):
                    self.say("QC lock: holder pid %s is gone, taking over" % cur.get("pid"))
                    try:
                        self.path.unlink()
                    except OSError:
                        pass
                    continue
                if cur is None:
                    time.sleep(0.2)       # half-written or just removed: look again shortly
                else:
                    who = "pid %s since %s in %s" % (cur.get("pid"), cur.get("started"), cur.get("cwd"))
                    if who != told:
                        self.say("QC lock: another QC run holds the machine (%s); waiting. "
                                 "--no-lock skips this." % who)
                        told = who
                    time.sleep(self.poll)
                if deadline is not None and time.time() > deadline:
                    return False
        finally:
            self._drop(ticket)

    def release(self):
        if not self.held:
            return
        cur = holder(self.path)
        if cur is None or cur.get("pid") == self.pid:
            try:
                self.path.unlink()
            except OSError:
                pass
        if os.environ.get(OWNER_ENV) == str(self.pid):
            del os.environ[OWNER_ENV]
        self.held = False
