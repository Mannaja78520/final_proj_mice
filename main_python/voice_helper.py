"""The voice helper's process, started by the hub when something needs a voice.

User 2026-10-29: *แก้ ... แอพ voice ที่ค้าง*. On the PC the helper was not
running at all (nothing on 8767): the Voice page waited on "connecting…",
spoken lines on the rig failed, and the Start button's 10 s wait ended with
no word. So (A55-1):

* ONE start at a time: a second press, a page and a spoken line arriving
  together never start two helpers that fight for port 8767 and the GPU;
* the helper's own words go to a log (config/voice_helper.json `log`), not
  to nowhere, and a helper that exits early is reported with its last lines;
* MiceHub.exe has no Python of its own: the interpreter comes from the
  config list, never the Microsoft Store stub;
* callers that need an answer (`call`) start it and wait `waitSeconds`.
"""
import os
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

STORE_STUB = "windowsapps"     # %LOCALAPPDATA%\Microsoft\WindowsApps\python.exe opens the Store


def refused(err):
    """True when nobody listens on the helper's port (not a slow answer)."""
    reason = getattr(err, "reason", err)
    return isinstance(reason, ConnectionRefusedError) or isinstance(err, ConnectionRefusedError)


class VoiceHelper:
    """Start, watch and wait for apps/voice/service.py."""

    def __init__(self, url, settings, root, data, env=None,
                 popen=subprocess.Popen, which=shutil.which, exists=os.path.isfile,
                 clock=time.monotonic, frozen=None):
        self.url = url              # () -> (base, why-not), read per call like the proxy
        self.settings = settings    # () -> dict from config/voice_helper.json
        self.root = Path(root)      # the code folder that holds apps/voice/service.py
        self.data = Path(data)      # the writable folder the log goes under
        self.env = env or (lambda: dict(os.environ))
        self.popen, self.which, self.exists, self.clock = popen, which, exists, clock
        self.frozen = bool(getattr(sys, "frozen", False)) if frozen is None else frozen
        self._lock = threading.Lock()
        self._proc = None
        self._since = None
        self._why = ""

    # -- what is there -------------------------------------------------
    def alive(self, timeout=0.8):
        base, _ = self.url()
        if not base:
            return False
        try:
            with urllib.request.urlopen(base + "/health", timeout=timeout) as r:
                return r.getcode() == 200
        except Exception:                                    # noqa: BLE001
            return False

    def log_path(self):
        return self.data / str(self.settings().get("log") or ".local/voice/helper.log")

    def log_tail(self, lines=12):
        try:
            raw = self.log_path().read_bytes()[-6000:]
        except OSError:
            return ""
        return "\n".join(raw.decode("utf-8", "replace").splitlines()[-lines:])

    def state(self):
        """{running, starting, seconds, exited, why, log}: what the page shows."""
        if self.alive():
            return {"running": True, "starting": False}
        with self._lock:
            proc, since, why = self._proc, self._since, self._why
        out = {"running": False, "starting": False, "why": why, "log": str(self.log_path())}
        if proc is not None and since is not None:
            code = proc.poll()
            secs = round(self.clock() - since, 1)
            if code is None:
                limit = float(self.settings().get("startSeconds") or 60)
                out.update(starting=secs < limit, seconds=secs)
                if secs >= limit:
                    out["why"] = "the voice helper did not answer within %d seconds" % limit
            else:
                out.update(exited=code, why="the voice helper stopped (exit code %s)" % code)
            if not out["starting"]:
                out["tail"] = self.log_tail()
        return out

    # -- starting ------------------------------------------------------
    def python(self):
        """[exe, args...] that runs the helper, or None (why in self._why)."""
        if not self.frozen:
            return [sys.executable]
        for item in self.settings().get("python") or []:
            cmd = [str(x) for x in (item if isinstance(item, list) else [item])]
            exe = os.path.expandvars(cmd[0])
            if "%" in exe:
                continue                          # that variable is not set on this PC
            if not (os.sep in exe or "/" in exe):
                exe = self.which(exe) or ""
            if exe and self.exists(exe) and STORE_STUB not in exe.lower():
                return [exe] + cmd[1:]
        return None

    def _open_log(self):
        path = self.log_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        limit = int(self.settings().get("logBytes") or 1000000)
        try:
            if path.stat().st_size > limit:
                os.replace(path, str(path) + ".1")
        except OSError:
            pass
        out = open(path, "ab")
        out.write(("\n--- started by the hub %s ---\n" % time.strftime("%Y-%m-%d %H:%M:%S")).encode())
        out.flush()
        return out

    def start(self):
        """-> {ok, already_running | starting | started, message|error}."""
        if self.alive():
            return {"ok": True, "already_running": True, "message": "voice service is already running"}
        with self._lock:
            if self._proc is not None and self._proc.poll() is None:
                limit = float(self.settings().get("startSeconds") or 60)
                if self.clock() - self._since < limit:
                    return {"ok": True, "starting": True, "message": "the voice helper is starting"}
            script = self.root / "apps" / "voice" / "service.py"
            if not script.is_file():
                self._why = "apps/voice/service.py not found on disk"
                return {"ok": False, "error": self._why}
            py = self.python()
            if not py:
                self._why = ("no Python found to run the voice helper - add yours to "
                             "config/voice_helper.json `python`")
                return {"ok": False, "error": self._why}
            flags = 0
            if os.name == "nt":
                flags = (subprocess.CREATE_NEW_PROCESS_GROUP | 0x00000008     # DETACHED_PROCESS
                         | 0x08000000)                                         # CREATE_NO_WINDOW
            try:
                log = self._open_log()
                try:
                    self._proc = self.popen(py + ["-u", str(script)], cwd=str(self.root),
                                            env=self.env(), stdin=subprocess.DEVNULL,
                                            stdout=log, stderr=subprocess.STDOUT,
                                            creationflags=flags)
                finally:
                    log.close()              # the child holds its own handle
            except OSError as e:
                self._why = "could not start the voice helper (%s)" % e
                return {"ok": False, "error": self._why}
            self._since = self.clock()
            self._why = ""
            return {"ok": True, "started": True, "message": "voice service started"}

    def ensure(self, wait=None):
        """Start if needed and wait until /health answers. -> (ok, why-not)."""
        if self.alive():
            return True, ""
        if not self.settings().get("autoStart", True):
            return False, "the voice helper is not running and autoStart is off in config/voice_helper.json"
        got = self.start()
        if not got.get("ok"):
            return False, got.get("error") or "the voice helper could not start"
        limit = float(self.settings().get("waitSeconds") or 30) if wait is None else float(wait)
        end = self.clock() + limit
        while self.clock() < end:
            if self.alive():
                return True, ""
            proc = self._proc
            if proc is not None and proc.poll() is not None:
                return False, "the voice helper stopped while starting (see %s)" % self.log_path()
            time.sleep(0.5)
        return False, "the voice helper did not answer within %d seconds" % limit

    def call(self, fn):
        """fn() once; nobody listening -> start the helper, wait, fn() again."""
        try:
            return fn()
        except (urllib.error.URLError, OSError) as e:
            if not refused(e):
                raise
            ok, why = self.ensure()
            if not ok:
                raise ConnectionRefusedError(why) from e
            return fn()
