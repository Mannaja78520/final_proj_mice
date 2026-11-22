"""Every program the hub starts, and the one place that stops them all.

User 2026-11-22: start and stop must also work on another PC. Before this the
voice helper (detached on purpose), the face watcher and the friends' parts
kept running after the hub window was closed: the next start on that PC hit a
busy port, or two copies fought for the GPU, and the only cure was Task
Manager. Now each start is recorded here and one call ends them all, with
their own children (a Windows `cmd /c` or a `sh -c` hides the real server one
level down, so killing only the handle left it running).

* Windows: `taskkill /T /F` walks the child tree. POSIX: the child is started
  in its own session (`session_flags()`), so the whole group gets the signal.
* `config/children.json` `stopWithHub` (default true) keeps them alive on
  purpose for a hub that is only being restarted.
"""
import os
import signal
import subprocess
import threading
import time

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0


def session_flags():
    """Popen kwargs that put a child in its own process group, per platform."""
    if os.name == "nt":
        return {}                       # callers pass their own creationflags
    return {"start_new_session": True}


def kill_tree(proc, grace=3.0):
    """Stop proc and everything it started. True when it is gone."""
    if proc is None or proc.poll() is not None:
        return True
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                       capture_output=True, check=False, creationflags=NO_WINDOW)
    else:
        for sig in (signal.SIGTERM, signal.SIGKILL):
            try:
                os.killpg(proc.pid, sig)
            except (ProcessLookupError, PermissionError, OSError):
                try:
                    proc.send_signal(sig)
                except OSError:
                    pass
            end = time.time() + (grace if sig == signal.SIGTERM else 1.0)
            while time.time() < end and proc.poll() is None:
                time.sleep(0.05)
            if proc.poll() is not None:
                break
    try:
        proc.wait(timeout=1.0)
    except Exception:                                        # noqa: BLE001
        pass
    return proc.poll() is not None


class Children:
    """name -> Popen of what this hub started."""

    def __init__(self):
        self._lock = threading.Lock()
        self._items = {}

    def adopt(self, name, proc):
        with self._lock:
            self._items[name] = proc
        return proc

    def names(self):
        with self._lock:
            return sorted(n for n, p in self._items.items() if p.poll() is None)

    def stop_all(self, grace=3.0):
        """Stop every live child in parallel. -> names that were stopped."""
        with self._lock:
            items = list(self._items.items())
            self._items.clear()
        live = [(n, p) for n, p in items if p.poll() is None]
        done, threads = [], []

        def one(n, p):
            if kill_tree(p, grace):
                done.append(n)

        for n, p in live:
            th = threading.Thread(target=one, args=(n, p), daemon=True)
            th.start()
            threads.append(th)
        for th in threads:
            th.join(grace + 4.0)
        return sorted(done)


CHILDREN = Children()
