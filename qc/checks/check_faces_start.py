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
from pathlib import Path

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
    try:
        F.logout_qc()
        real_is_self = main.is_self
        main.is_self = lambda ip: False          # a caller on the venue WiFi
        try:
            code, body = F.post(base + "/api/faces/start")
        finally:
            main.is_self = real_is_self
        t.ok(code == 401 and '"need_login"' in body and not faces.watcher_up(),
             "from the network it needs a sign-in, and nothing starts", (code, body[:200]))
        code, body = F.get(base + "/api/faces/start")
        t.ok(code == 405 and not faces.watcher_up(), "and a plain GET starts nothing",
             (code, body[:200]))

        code, body = F.post(base + "/api/faces/start", timeout=40)
        got = json.loads(body or "{}")
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
             "a second press finds it running and starts no second watcher", body[:200])
        code, page = F.get(base + "/app/faces/")
        t.contains(page, 'fetch("/api/faces/start", {method: "POST"',
                   "the Reconize screen has the button")
    finally:
        proc = faces._started.pop("proc", None)
        if proc is not None:
            proc.terminate()
            try:
                proc.wait(5)
            except Exception:                                # noqa: BLE001
                proc.kill()
        os.environ.pop("MICE_FACES_CONFIG", None)
