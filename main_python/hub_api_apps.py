"""The hub's routes for the app launcher, page access, partners and the voice helper.

Moved out of main.py's Handler.api() on 2026-09-22 (A26-93). Handler inherits
AppRoutes, and api() asks it before carrying on down its own chain. Names
that live in main.py are read late through _hub, so a check that swaps
main.<name> reaches this code too.
"""
from pathlib import Path
import json
import os
import shutil
import subprocess
import sys
import urllib.request

NOT_MINE = object()   # no route here matched: api() carries on
_hub = None           # the main module, set by bind()


def bind(hub):
    global _hub
    _hub = hub


class AppRoutes:
    def api_apps(self, method, path, q):
        if path == "/api/apps":
            # what the hub page offers to open — rendered from the registry, so
            # a new app appears without editing hub.html
            if not _hub.registry:
                return self.send_json({"ok": False, "apps": [],
                                       "error": "registry unavailable"})
            # A MALFORMED app.json IS THE LIKELY FAULT, and it used to be the
            # worst-reported one: registry.apps() raises RegistryError naming
            # the file and the line, nothing caught it, the request became a
            # 500, and the page said *the hub may have stopped* - which is
            # false, and throws away the only detail that fixes it. Answer with
            # the reason instead, so the screen can print the file and line.
            try:
                out = [{k: a[k] for k in ("id", "name", "blurb", "icon",
                                          "path", "order", "help")}
                       for a in _hub.registry.apps() if a.get("show", True)]
            except Exception as e:                          # noqa: BLE001
                return self.send_json({"ok": False, "apps": [],
                                       "error": str(e)[:300]})
            return self.send_json({"ok": True, "apps": out})

        if path == "/api/access":
            # Which pages work with no login, and which cards on the hub ask
            # first. Open on purpose: a page has to be able to draw itself
            # before anybody has signed in, and this says nothing secret - it
            # is the same list a person can read on the help page.
            #
            # Read per request, never cached: a designer editing the file
            # should see the screen change on the next refresh, not after a
            # restart. That is the same bargain config/voice.json already made.
            return self.send_json(_hub.read_page_access())

        if path == "/api/partners":
            # Where each outside program lives, and what each of its event
            # sources can and cannot report. Open like /api/access and for the
            # same reason: a page shows the tile before anybody has signed in,
            # and there is nothing secret in an address.
            return self.send_json(_hub.read_partners())

        if path == "/api/partners/start":
            # Starts a configured outside program on THIS PC. No hub login
            # from this PC itself (user 2026-09-17: Reconize and Jao have
            # their own logins); from the network it still needs one.
            if not self.logged_in() and not _hub.is_self(self.client_address[0]):
                return self.send_bytes(json.dumps(
                    {"ok": False, "need_login": True,
                     "error": "log in first, or open this on the PC itself"}).encode(),
                    _hub.MIME[".json"], 401)
            pid = (q.get("id") or [""])[0]
            got = _hub.read_partners()
            entry = (got.get("partners") or {}).get(pid)
            if not entry:
                return self.send_json({"ok": False, "error": got.get("error") or
                                       "config/partners.json has no entry called %r" % pid})
            return self.send_json(_hub.partner_launch.start(pid, entry))

        if path == "/api/voice/start" and method == "POST":
            base, _ = _hub.voice_service_url()
            if base:
                try:
                    with urllib.request.urlopen(base + "/health", timeout=0.8) as r:
                        if r.getcode() == 200:
                            return self.send_json({"ok": True, "already_running": True,
                                                   "message": "voice service is already running"})
                except Exception:
                    pass
            py = sys.executable if not getattr(sys, "frozen", False) else (
                shutil.which("python") or shutil.which("python3") or r"C:\Program Files\Python312\python.exe" or "python")
            if getattr(sys, "frozen", False):
                root_dir = Path(sys.executable).parent.parent
            else:
                root_dir = _hub.HERE.parent
            script = root_dir / "apps" / "voice" / "service.py"
            if not script.is_file():
                script = Path("apps/voice/service.py").resolve()
                root_dir = script.parent.parent.parent
            if not script.is_file():
                return self.send_err("apps/voice/service.py not found on disk", 404)
            try:
                flags = 0
                if os.name == "nt":
                    flags = subprocess.CREATE_NEW_PROCESS_GROUP | getattr(subprocess, "DETACHED_PROCESS", 0x00000008)
                subprocess.Popen(
                    [py, str(script)],
                    cwd=str(root_dir),
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=flags)
                return self.send_json({"ok": True, "message": "voice service started"})
            except Exception as e:
                return self.send_err("could not start voice service: %s" % e, 500)

        if path == "/api/voice/stop" and method == "POST":
            base, _ = _hub.voice_service_url()
            if base:
                try:
                    req = urllib.request.Request(base + "/stop", data=b"{}", method="POST")
                    with urllib.request.urlopen(req, timeout=2.0) as r:
                        pass
                except Exception:
                    pass
            if os.name == "nt":
                try:
                    cmd = (
                        "Get-CimInstance Win32_Process | "
                        "Where-Object { $_.CommandLine -like '*apps*voice*service.py*' } | "
                        "ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
                    )
                    subprocess.run(["powershell", "-NoProfile", "-Command", cmd],
                                   capture_output=True, timeout=5,
                                   creationflags=_hub.NO_WINDOW)
                except Exception:
                    pass
            return self.send_json({"ok": True, "message": "voice service stopped"})

        if path == "/api/all-jao/start" and method in ("GET", "POST"):
            try:
                with urllib.request.urlopen("http://127.0.0.1:8080/", timeout=0.6) as r:
                    if r.getcode() in (200, 301, 302, 304):
                        return self.send_json({"ok": True, "already_running": True,
                                               "message": "All-Jao Games server is already running"})
            except Exception:
                pass
            py = sys.executable if not getattr(sys, "frozen", False) else (
                shutil.which("python") or shutil.which("python3") or r"C:\Program Files\Python312\python.exe" or "python")
            all_jao_dir = Path("E:/final_proj/mice/All-Jao-Games")
            if not all_jao_dir.is_dir():
                cand = (_hub.HERE.parent.parent / "All-Jao-Games").resolve()
                if cand.is_dir():
                    all_jao_dir = cand
            if not all_jao_dir.is_dir():
                return self.send_err("All-Jao-Games folder not found at %s" % all_jao_dir, 404)
            try:
                flags = 0
                if os.name == "nt":
                    flags = subprocess.CREATE_NEW_PROCESS_GROUP | getattr(subprocess, "DETACHED_PROCESS", 0x00000008)
                subprocess.Popen(
                    [py, "-m", "http.server", "8080", "--directory", str(all_jao_dir)],
                    cwd=str(all_jao_dir),
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=flags)
                return self.send_json({"ok": True, "message": "All-Jao Games server started on port 8080"})
            except Exception as e:
                return self.send_err("could not start games server: %s" % e, 500)

        if (path == "/api/reconize/start" or path == "/api/partner/reconize/start") and method in ("GET", "POST"):
            # The same starter /api/partners/start uses, so Reconize comes up
            # HIDDEN and its folder and port are read from
            # config/partners.json. It used to run their start.bat, which opens
            # two `cmd /k` windows and a Chrome tab nobody asked for, and it
            # carried its own copy of the folder and the port - two places to
            # disagree with the one list (user 2026-09-18: *make it in background*).
            got = _hub.read_partners()
            entry = (got.get("partners") or {}).get("reconize")
            if not entry:
                return self.send_err(got.get("error") or
                                     "config/partners.json has no reconize entry", 404)
            return self.send_json(_hub.partner_launch.start("reconize", entry))

        if path == "/api/voice" or path.startswith("/api/voice/"):
            return self.voice_proxy(method, path, q)

        return NOT_MINE
