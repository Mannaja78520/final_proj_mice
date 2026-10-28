"""Start a worker command in the background and tell whether it still runs.

Every job writes stdout+stderr to its own log under _out/ai_watch/logs, named
<provider>-<job id>.log, which is also what the text_log source watches. The
child is detached from the watcher, so a watcher restart never kills a worker.
"""
import os
import shutil
import subprocess

NO_WINDOW = 0x08000000 | 0x00000200  # CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP


class Launcher:
    def __init__(self, logs_dir):
        self.logs = logs_dir
        self.procs = {}  # job id -> Popen, while this watcher process lives

    def log_path(self, job):
        return str(self.logs / ("%s-%s.log" % (job["provider"], job["id"])))

    def start(self, job):
        self.logs.mkdir(parents=True, exist_ok=True)
        argv = list(job["argv"])
        exe = shutil.which(argv[0])
        if not exe:
            raise FileNotFoundError("%s is not on PATH" % argv[0])
        argv[0] = exe
        job["log"] = self.log_path(job)
        log = open(job["log"], "ab")
        stdin = job.get("stdin")
        p = subprocess.Popen(argv, cwd=job.get("cwd") or None, stdout=log,
                             stderr=subprocess.STDOUT,
                             stdin=subprocess.PIPE if stdin else subprocess.DEVNULL,
                             creationflags=NO_WINDOW if os.name == "nt" else 0)
        if stdin:
            p.stdin.write(stdin.encode("utf-8"))
            p.stdin.close()
        log.close()
        self.procs[job["id"]] = p
        job["pid"] = p.pid
        return p.pid

    def running(self, job):
        """True / False, plus the exit code when this process started it."""
        p = self.procs.get(job["id"])
        if p is not None:
            rc = p.poll()
            return rc is None, rc
        return pid_alive(job.get("pid")), None


def pid_alive(pid):
    if not pid:
        return False
    try:
        import psutil
        return psutil.pid_exists(int(pid))
    except ImportError:
        out = subprocess.run(["tasklist", "/FI", "PID eq %d" % int(pid), "/NH"],
                             capture_output=True, text=True).stdout
        return str(pid) in out


def session_running(session):
    """A worker already resumed this session (someone else did it by hand)."""
    if not session:
        return False
    try:
        import psutil
    except ImportError:
        return False
    for p in psutil.process_iter(["cmdline"]):
        try:
            if session in " ".join(p.info["cmdline"] or []):
                return True
        except Exception:
            continue
    return False
