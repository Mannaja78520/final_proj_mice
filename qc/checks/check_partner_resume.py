"""Their page comes back when a hub restart took it down.

The hub starts the friend's page (Vite) as its own child, while their backend
is started by their own .bat. A hub restart took the page down and left the
backend running: the app half up, no page, and the PC session could not start
it again (PC, 2026-10-19). Now the new hub starts again what a hub started,
using their own start lines as before, never touching their folder.

Held here with two throwaway web servers standing in for their two parts:
  * a part a hub started and lost is started again while another part runs;
  * a closed app (nothing answering) stays closed;
  * a part the hub never started (their backend) is never started by it.
"""
import json
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

import qc as F

AREA = "hub"
TITLE = "the friend's page comes back after a hub restart, a closed app stays closed"


def _port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def _up(port, wait=15.0):
    end = time.time() + wait
    while time.time() < end:
        try:
            with urllib.request.urlopen("http://127.0.0.1:%d/" % port, timeout=1):
                return True
        except Exception:                                   # noqa: BLE001
            time.sleep(0.2)
    return False


def _kill(proc):
    if proc is None:
        return
    if sys.platform == "win32":
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True)
    else:                                 # the shell's child, then the shell
        subprocess.run(["pkill", "-KILL", "-P", str(proc.pid)], capture_output=True)
        proc.kill()
    proc.wait(10)


def run(t):
    sys.path.insert(0, str(F.CODE / "main_python"))
    import partner_launch as PL                             # noqa: E402
    back, page = _port(), _port()
    tmp = Path(tempfile.mkdtemp(prefix="qc_resume_"))
    serve = '"%s" -m http.server %%d --bind 127.0.0.1' % sys.executable
    entry = {"name": "QC two parts", "folder": str(tmp), "launch": [
        {"run": [serve % back], "check": "http://127.0.0.1:%d/" % back},
        {"run": [serve % page], "check": "http://127.0.0.1:%d/" % page}]}
    pid = "qc_resume_%d" % page
    parts, _src = PL.parts_of(entry)
    backend = None
    try:
        # Their backend, started by them - not by a hub.
        backend = subprocess.Popen(parts[0][1], shell=sys.platform != "win32", cwd=str(tmp),
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        t.ok(_up(back), "their backend runs on its own")
        PL.start(pid, entry)
        t.ok(_up(page), "the hub starts their page")
        memo = json.loads(PL._memo_path(pid).read_text(encoding="utf-8"))
        t.eq(memo.get("started"), [parts[1][1]], "and remembers it started the page, only")

        # The hub restarts: its child goes with it, the new hub has no handle.
        _kill(PL._procs.pop((pid, parts[1][1]), None))
        t.ok(not _up(page, 1), "a hub restart takes the page down")
        got = PL.resume(pid, entry)
        t.ok(got and _up(page), "the next hub starts the page again", got)

        # The whole app closed: nothing is started behind anyone's back.
        _kill(PL._procs.pop((pid, parts[1][1]), None))
        _kill(backend)
        backend = None
        t.ok(PL.resume(pid, entry) is None and not _up(page, 2) and not _up(back, 0.5),
             "a closed app stays closed")
    finally:
        _kill(PL._procs.pop((pid, parts[1][1]), None))
        _kill(backend)
        PL._memo_path(pid).unlink(missing_ok=True)
