"""One press starts Reconize and the rig's face watcher (A11-1).

* THE SAME RULE AS OPEN RECONIZE (user 2026-09-17): POST only, no hub login
  at this PC (start_refused), a login from anywhere else. A website open in
  this PC's browser is refused there too, by its Origin.
* ONE WATCHER. A second press while one runs starts nothing: two watchers
  log in twice and greet everybody twice.
* ON THE PORT THE HUB WILL ASK. The hub starts it with the port from
  config/faces.json, so the two can never disagree about where it is.
"""
import json
import os
import tempfile
import time
import threading
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import qc as F


AREA = "hub"
TITLE = "one press starts Reconize and the rig's watcher, never two watchers"


def run(t):
    tmp = Path(tempfile.mkdtemp(prefix="mice_fstart_"))
    port = F._free_port()
    cfg = tmp / "faces.json"
    cfg.write_text(json.dumps({"service": "http://127.0.0.1:%d" % port}), encoding="utf-8")
    os.environ["MICE_FACES_CONFIG"] = str(cfg)
    base, main = F.start_hub()
    faces = main.hub_api_faces
    _reused_process(t, faces)
    real_watcher = faces.start_watcher
    real_partner = main.partner_launch.start
    launched = []
    completed = threading.Event()
    real_route = main.Handler.route
    def route(handler, method):
        try:
            return real_route(handler, method)
        finally:
            if handler.path.startswith("/api/faces/start"):
                completed.set()
    main.Handler.route = route
    # A denied HTTP response used to continue through the route and start
    # both programs. Record the effects, not just its already-sent status.
    faces.start_watcher = lambda *a, **k: launched.append("watcher") or ("started", "", "")
    main.partner_launch.start = lambda *a, **k: launched.append("partner") or {"ok": True}
    try:
        F.logout_qc()
        real_is_self = main.is_self
        main.is_self = lambda ip: False          # a caller on the venue WiFi
        try:
            code, body = F.post(base + "/api/faces/start")
            t.ok(completed.wait(5), "the denied remote handler finished")
        finally:
            main.is_self = real_is_self
        t.ok(code == 401 and '"need_login"' in body and not faces.watcher_up(),
             "from the network it needs a sign-in, and nothing starts", (code, body[:200]))
        completed.clear()
        code, body = F.get(base + "/api/faces/start")
        t.ok(completed.wait(5), "the denied GET handler finished")
        t.ok(code == 405 and not faces.watcher_up(), "and a plain GET starts nothing",
             (code, body[:200]))

        t.eq(launched, [], "denied remote and GET requests start no program")
        faces.start_watcher = real_watcher
        code, body = F.post(base + "/api/faces/start", timeout=40)
        got = json.loads(body or "{}")
        t.ok("partner" in launched, "the allowed request asks the partner to start", repr(launched))
        t.ok(got.get("watcher") in ("started", "starting"),
             "at this PC, with no hub login, the watcher is started", (code, body[:300]))
        until = time.time() + 20
        while time.time() < until and not faces.watcher_up():
            time.sleep(0.3)
        t.ok(faces.watcher_up(), "and answers on the port config/faces.json names",
             faces.watcher())
        t.ok("reconize" in got and "ok" in got["reconize"],
             "Reconize is asked to start in the same press", got.get("reconize"))
        first = faces._started.get("proc")
        code, body = F.post(base + "/api/faces/start", timeout=40)
        got = json.loads(body or "{}")
        t.ok(got.get("watcher") == "running" and faces._started.get("proc") is first,
             "a second press finds it running and starts no second watcher",
             {"reply": got, "firstPid": getattr(first, "pid", None),
              "nowPid": getattr(faces._started.get("proc"), "pid", None)})
        # Voice asks for OUR watcher only (A42-4): their app is not started
        # by a page that only wanted names to arrive faster.
        asked = []
        real_start = main.partner_launch.start
        main.partner_launch.start = lambda *a, **k: asked.append(a) or {"ok": True}
        try:
            code, body = F.post(base + "/api/faces/start?only=watcher", timeout=40)
        finally:
            main.partner_launch.start = real_start
        got = json.loads(body or "{}")
        t.ok(got.get("ok") and got.get("watcher") == "running" and "reconize" not in got
             and not asked, "Voice's press reaches only the watcher, never the face app",
             (body[:200], asked))
        code, page = F.get(base + "/app/faces/")
        t.contains(page, 'Mice.Api.post("/api/faces/start")',
                   "the Reconize screen has the button")
    finally:
        faces.start_watcher = real_watcher
        main.partner_launch.start = real_partner
        main.Handler.route = real_route
        proc = faces._started.pop("proc", None)
        if proc is not None:
            proc.terminate()
            try:
                proc.wait(5)
            except Exception:                                # noqa: BLE001
                proc.kill()
        os.environ.pop("MICE_FACES_CONFIG", None)


def _reused_process(t, faces):
    """A missed health poll cannot turn a reused watcher into a new launch."""
    keep = faces._started.copy()
    proc = SimpleNamespace(pid=41, poll=lambda: None)
    launch = Mock(side_effect=AssertionError("a live watcher must be reused"))
    try:
        faces._started.clear()
        faces._started["proc"] = proc
        with patch.object(faces, "watcher_up", side_effect=[False, True]), \
             patch.object(faces, "subprocess",
                          SimpleNamespace(Popen=launch, STDOUT=faces.subprocess.STDOUT)):
            state, _why, detail = faces.start_watcher()
        t.eq(state, "running", "an existing watcher is running after a transient health miss")
        t.ok(faces._started.get("proc") is proc,
             "the health retry keeps the exact existing child", detail)
        t.eq(launch.call_count, 0, "the health retry starts no second watcher")
    finally:
        faces._started.clear()
        faces._started.update(keep)
