"""The screen that edits what the rig says, saved with no restart (A8-1).

* ONE WRITER. The page saves through the hub (where the login is) to the
  watcher, and only the watcher writes apps/faces/rules.json. A page that
  wrote the file itself, or a second writer, would race the watcher's reads.
* SAVING NEEDS A LOGIN, even at this PC: it changes what a robot says aloud
  to a guest. Reading stays open, like every other status.
* CHECKED BEFORE WRITTEN. A stranger's words with {name} in them, or a
  misspelt blank, are refused on save and the file on disk is left as it was.
* NO RESTART. The very next arrival uses the words just saved.
* THE FILE'S OWN NOTES (keys starting with _) come back with the rules and go
  out again with the save, so a save from the screen never strips them.
"""
import json
import os
import shutil
import tempfile
import threading
import time
from http.server import ThreadingHTTPServer
from pathlib import Path

import importlib.util
import sys

import qc as F


AREA = "hub"
TITLE = "the greeting words are edited on the screen and used at once"


def _load(name, rel):
    sys.path.insert(0, str(F.CODE / "apps" / "faces"))
    spec = importlib.util.spec_from_file_location(name, F.CODE / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def ev(who, pid, camera="door-1"):
    return {"who": who, "id": pid, "known": True, "camera": camera,
            "hasCamera": True, "source": "ws"}


def run(t):
    tmp = Path(tempfile.mkdtemp(prefix="mice_rules_"))
    path = tmp / "rules.json"
    shutil.copyfile(F.CODE / "apps" / "faces" / "rules.json", path)
    os.environ["MICE_FACES_RULES"] = str(path)
    R = _load("_faces_rules_edit", "apps/faces/rules.py")
    S = _load("_faces_service_edit", "apps/faces/service.py")
    st = S.State("reconize")
    sent = []
    st.greeter = R.Greeter(rules_path=path, post=lambda g: (sent.append(g), ("queued", ""))[1])
    st.people = [dict(ev("Ann", "P1"), when=time.strftime("%Y-%m-%dT%H:%M:%S"))]
    S.Handler.state = st
    srv = ThreadingHTTPServer(("127.0.0.1", 0), S.Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    cfg = tmp / "faces.json"
    cfg.write_text(json.dumps({"service": "http://127.0.0.1:%d" % srv.server_port}),
                   encoding="utf-8")
    os.environ["MICE_FACES_CONFIG"] = str(cfg)
    try:
        base, main = F.start_hub()
        F.logout_qc()
        code, body = F.get(base + "/api/faces/rules")
        got = json.loads(body or "{}")
        t.ok(code == 200 and got.get("ok") and "wording" in got.get("rules", {}),
             "reading the words needs no login", (code, body[:200]))
        t.ok("_why" in got.get("rules", {}), "the file's own notes come back with them",
             sorted(got.get("rules", {}))[:5])
        t.ok(got.get("camerasSeen") == ["door-1"]
             and got.get("peopleSeen") == [{"id": "P1", "who": "Ann"}],
             "the screen is offered the cameras and people the app has seen",
             (got.get("camerasSeen"), got.get("peopleSeen")))

        new = json.loads(json.dumps(got["rules"]))
        new["greet"] = True
        new["cameras"] = {"door-1": {"role": "entry"}}
        new["wording"]["entry"]["known"] = "Welcome to the lab {title}{name}"
        body = json.dumps({"rules": new}).encode()
        before = path.read_bytes()
        code, ans = F.post(base + "/api/faces/rules", body)
        t.ok(code == 401 and '"need_login"' in ans and path.read_bytes() == before,
             "saving needs a login, even at this PC, and writes nothing", (code, ans[:200]))

        F.login(base)
        bad = json.loads(json.dumps(new))
        bad["wording"]["entry"]["unknown"] = "Hello {name}"
        code, ans = F.post(base + "/api/faces/rules", json.dumps({"rules": bad}).encode())
        t.ok(code == 400 and "stranger" in ans and path.read_bytes() == before,
             "a stranger's words with a name blank are refused, the file untouched",
             (code, ans[:200]))

        code, ans = F.post(base + "/api/faces/rules", body)
        t.ok(code == 200 and json.loads(ans).get("ok"), "logged in, the words are saved",
             (code, ans[:200]))
        on_disk = json.loads(path.read_text(encoding="utf-8"))
        t.ok(on_disk["wording"]["entry"]["known"] == "Welcome to the lab {title}{name}"
             and "_why" in on_disk, "the file holds the new words and keeps its notes",
             on_disk.get("wording"))
        st.greeter.consider(ev("Ann", "P1"))
        t.ok(sent and sent[-1]["text"].startswith("Welcome to the lab"),
             "the next arrival uses them, with no restart", sent[-1:])

        srv.shutdown()
        code, ans = F.get(base + "/api/faces/rules")
        got = json.loads(ans or "{}")
        t.ok(code == 503 and got.get("watcherDown") and "not running" in got.get("error", ""),
             "with the face helper stopped the screen is told so in plain words",
             (code, ans[:200]))

        code, page = F.get(base + "/app/faces/")
        t.contains(page, 'fetch("/api/faces/rules", {method: "POST"',
                   "the page saves through the hub, never to the watcher itself")
    finally:
        os.environ.pop("MICE_FACES_RULES", None)
        os.environ.pop("MICE_FACES_CONFIG", None)
