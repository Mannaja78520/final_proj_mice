"""The watcher answers on this PC only, and refuses anything else.

`apps/faces/service.py` is a separate process because the code that keeps up
with a daily-changing app must not need a PyInstaller rebuild, and because a
login belongs beside the process that uses it. That second reason is what this
check is about.

WHY REFUSING, RATHER THAN WARNING

`apps/voice/service.py` prints a warning when it is shared beyond this PC and
carries on. This one exits. The difference is what it holds: the login for an
outside app, and - once the later steps land - the ability to make the rig move
and speak. A port open to the venue WiFi would be a way to drive the robot with
no password at all, while the hub's own gate sits untouched beside it looking
like it is protecting something.

The refusal also has to SAY THE FIX. A helper that exits silently reads exactly
like a helper that crashed.

AND IT MUST NOT PROMISE WHAT IT CANNOT SEE

`/state` lists each event source with what it can report and whether it carries
a camera, copied from `config/partners.json` rather than restated. Their live
feed carries a camera but never a stranger; their history carries strangers but
no camera (read out of their code 2026-09-10, see that file). A screen built on
an invented list would tell somebody the rig is watching for strangers when
nothing it reads can see one.
"""
import json
import os
import socket
import tempfile
import subprocess
import sys
import time
import urllib.error
import urllib.request

import qc as F


AREA = "hub"
TITLE = "the face watcher answers on this PC only, and says what it cannot see"
# Boots a real subprocess that binds a port. Two of these at once would fight
# over it, and the failure would look like the code rather than the schedule.
SOLO = True

PORT = 8769
BASE = "http://127.0.0.1:%d" % PORT
CFG = "config/faces.json"


def _get(base, path, tries=25):
    """Wait for the helper to come up, then read one answer."""
    last = ""
    for _ in range(tries):
        try:
            with urllib.request.urlopen(base + path, timeout=2) as r:
                return json.loads(r.read().decode("utf-8")), ""
        except urllib.error.HTTPError as e:
            return json.loads(e.read().decode("utf-8")), ""
        except Exception as e:                               # noqa: BLE001
            last = str(e)
            time.sleep(0.25)
    return None, last


def run(t):
    svc = F.CODE / "apps" / "faces" / "service.py"
    t.ok(svc.is_file(), "there is a watcher to run", str(svc))
    if not svc.is_file():
        return

    with socket.socket() as available:
        available.bind(("127.0.0.1", 0))
        port = available.getsockname()[1]
    base = "http://127.0.0.1:%d" % port
    isolated = tempfile.TemporaryDirectory(prefix="mice-faces-qc-")
    child_env = dict(os.environ, MICE_FACES_LOGIN=isolated.name + "/absent.json")

    # ---- it answers, and says it is not watching yet -------------------
    proc = subprocess.Popen([sys.executable, str(svc), "--port", str(port)], env=child_env, cwd=str(F.CODE),
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, encoding="utf-8", errors="replace")
    try:
        health, why = _get(base, "/health")
        t.ok(health, "the watcher answers /health", why)
        if health:
            t.eq(health.get("watching"), False,
                 "and says plainly that it is watching nobody yet")
            t.eq(health.get("partnerKnown"), True,
                 "while knowing which outside app it is for")

        state, why = _get(base, "/state", tries=4)
        t.ok(state, "and answers /state", why)
        if state:
            kinds = {s["kind"]: s for s in state.get("sources") or []}
            t.ok(kinds, "listing where its events would come from", state)
            # The two holes, from the registry - never invented here.
            ws = kinds.get("ws") or {}
            poll = kinds.get("poll") or {}
            t.ok("unknown" not in (ws.get("reports") or []),
                 "the live feed is not claimed to see strangers",
                 "their feed publishes only matched faces, so a rig that "
                 "believed otherwise would wait for a stranger who never comes")
            t.ok(poll.get("hasCamera") is False,
                 "and the history is not claimed to carry a camera",
                 "history rows have no node_id at all, so a greeting placed "
                 "at a door from a history row is a guess about where "
                 "somebody is standing")
            t.eq(state.get("people"), [],
                 "and nobody is reported, because nothing is read yet")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=10)
        isolated.cleanup()

    # ---- and it REFUSES to listen beyond this PC ------------------------
    path = F.CODE / CFG
    before = path.read_bytes()
    try:
        path.write_text('{"service": "http://0.0.0.0:%d"}' % PORT,
                        encoding="utf-8")
        # A helper that IGNORES the rule does not exit - it serves the world
        # and sits there. So the timeout is the interesting outcome, not an
        # accident, and it has to become a named failure rather than a
        # traceback: a sabotage caught by a crash is caught by luck.
        served_anyway = False
        said, code = "", 0
        try:
            r = subprocess.run([sys.executable, str(svc)], env=child_env, cwd=str(F.CODE),
                               capture_output=True, text=True, timeout=25,
                               encoding="utf-8", errors="replace")
            said = (r.stdout or "") + (r.stderr or "")
            code = r.returncode
        except subprocess.TimeoutExpired as e:
            served_anyway = True
            out = e.stdout or b""
            if isinstance(out, bytes):
                out = out.decode("utf-8", "replace")
            said = out
        t.ok(not served_anyway,
             "a non-loopback address does not start a server at all",
             "it kept listening on 0.0.0.0 - it holds a login for the face "
             "app and can drive the rig through the hub, so this is a way to "
             "move the robot from the venue WiFi with no password")
        t.ok(code != 0,
             "sharing it beyond this PC is refused, not warned about",
             "exit was %r, and it said: %r" % (code, said[:300]))
        t.contains(said.lower(), "refusing",
                   "and it says so in words")
        t.contains(said, CFG,
                   "naming the file to fix, not just failing")
    finally:
        path.write_bytes(before)
        t.eq(path.read_bytes(), before, "watcher config restored byte-for-byte")
