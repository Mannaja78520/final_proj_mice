"""The hub's door to the face watcher's rules (system A8-1).

    GET  /api/faces/rules     the words, cameras and milestones, as the watcher has them
    POST /api/faces/rules     {rules}: save them (login - hub_auth GATED_POST)
    POST /api/faces/start     start Reconize (their start file) AND our watcher (A11-1)

The watcher (apps/faces/service.py) listens on this PC only and is the ONE
writer of apps/faces/rules.json: it checks the rules before it writes, and it
reads them again on the next arrival, so a save needs no restart. A page
anywhere on the WiFi saves through here, where the login is, and never talks
to the watcher itself.
"""
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

NOT_MINE = object()
_hub = None


def bind(hub):
    global _hub
    _hub = hub


def watcher():
    """Where the watcher answers: config/faces.json, read per call (MICE_FACES_CONFIG
    points a check at its own watcher)."""
    path = Path(os.environ.get("MICE_FACES_CONFIG") or _hub.asset("config", "faces.json"))
    try:
        cfg = _hub.registry.load(path)
    except Exception:                                        # noqa: BLE001
        cfg = {}
    return str((cfg or {}).get("service") or "http://127.0.0.1:8769").rstrip("/")


def ask(method, body=None):
    """(answer, http code). The hub is a program on this PC to the watcher:
    JSON, and no Origin, which is exactly what the watcher lets in."""
    req = urllib.request.Request(watcher() + "/rules", method=method,
                                 data=json.dumps(body).encode("utf-8") if body is not None else None,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return json.loads(r.read().decode("utf-8")), 200
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read().decode("utf-8")), e.code
        except Exception:                                    # noqa: BLE001
            return {"ok": False, "error": "the face helper refused (%s)" % e.code}, 502
    except Exception as e:                                   # noqa: BLE001
        return {"ok": False, "watcherDown": True,
                "error": "the face helper is not running on this PC, so the rules "
                         "cannot be read or saved. Start it: python apps/faces/service.py",
                "detail": str(e)}, 503


def watcher_up(timeout=0.8):
    try:
        with urllib.request.urlopen(watcher() + "/health", timeout=timeout) as r:
            return r.getcode() == 200
    except Exception:                                        # noqa: BLE001
        return False


_started = {}


def start_watcher(wait=15.0):
    """(state, why, detail). Our watcher, hidden, on the port config/faces.json
    names - so the hub and the watcher can never disagree about where it is.
    One at a time: a second press while it is starting does not start two
    (two would log in twice and greet everybody twice)."""
    if watcher_up():
        return "running", "", ""
    proc = _started.get("proc")
    if proc is None or proc.poll() is not None:
        root = Path(sys.executable).parent.parent if getattr(sys, "frozen", False) else _hub.HERE.parent
        script = root / "apps" / "faces" / "service.py"
        if not script.is_file():
            return "missing", "the face helper is not on this PC (%s)" % script, ""
        # The exe has no python of its own to lend; the PC's python runs it.
        py = sys.executable if not getattr(sys, "frozen", False) else (
            shutil.which("python") or shutil.which("python3") or "python")
        port = watcher().rsplit(":", 1)[-1]
        log = _hub.partner_launch.TMP / "mice_faces_watcher.log"
        with open(log, "ab") as out:
            proc = subprocess.Popen([py, str(script), "--port", port], cwd=str(root),
                                    stdout=out, stderr=subprocess.STDOUT,
                                    creationflags=_hub.NO_WINDOW)
        _started.update(proc=proc, log=str(log))
    until = time.time() + wait
    while time.time() < until:
        if watcher_up(0.5):
            return "started", "", "pid %d" % proc.pid
        if proc.poll() is not None:
            return "failed", "the face helper stopped as soon as it started", _started.get("log", "")
        time.sleep(0.3)
    return "starting", "", "pid %d" % proc.pid


class FacesRoutes:
    def api_faces(self, method, path, q):
        if path == "/api/faces/start":
            # The same rule as Open Reconize (user 2026-09-17): no hub login at
            # this PC from the hub's own page, a login from anywhere else, POST only.
            refused = self.start_refused(method)
            if refused is not None:
                return refused
            entry = (_hub.read_partners().get("partners") or {}).get("reconize") or {}
            theirs = (_hub.partner_launch.start("reconize", entry) if entry else
                      {"ok": False, "error": "config/partners.json has no entry called reconize"})
            state, why, detail = start_watcher()
            ours = state in ("running", "started", "starting")
            return self.send_json({"ok": ours and bool(theirs.get("ok")),
                                   "watcher": state, "watcherError": why, "detail": detail,
                                   "reconize": theirs})
        if path != "/api/faces/rules":
            return NOT_MINE
        if method == "POST":
            try:
                d = json.loads(self.body().decode() or "{}")
            except ValueError:
                return self.send_err("that request was not readable")
            got, code = ask("POST", d if isinstance(d, dict) else {})
        else:
            got, code = ask("GET")
        return self.send_json(got, code)
