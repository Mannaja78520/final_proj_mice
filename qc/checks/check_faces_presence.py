"""Presence mode: take a question only when somebody is standing there (A7-1).

Decided, and not to be re-asked (docs/system_integral.html):
* OPT-IN. Off unless voice.json says presence.on.
* It gates ONLY asking questions - never the nong's own sequences or commands.
* It FAILS OPEN. With the watcher down, or an app that has no camera able to
  say who stands where, the question is taken. A broken camera must never be
  the thing that makes the rig deaf at an event.
* A sighting with no camera (their history) is not somebody standing there.
"""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import types
from datetime import datetime, timedelta
from http.server import ThreadingHTTPServer
from pathlib import Path

import qc as F


AREA = "hub"
TITLE = "presence mode takes questions only when somebody stands there, and fails open"


def _load(name, rel):
    sys.path.insert(0, str(F.CODE / rel.rsplit("/", 1)[0]))
    spec = importlib.util.spec_from_file_location(name, F.CODE / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _ev(camera, ago, has=True):
    return {"who": "Ann", "id": "P1", "known": True, "camera": camera, "hasCamera": has,
            "when": (datetime.now() - timedelta(seconds=ago)).isoformat(timespec="seconds")}


def run(t):
    S = _load("_faces_service_presence", "apps/faces/service.py")
    st = S.State("reconize")
    got = st.presence("", 60)
    t.ok(got["known"] and got["present"] is False, "with nobody seen, nobody is there", got)
    st.people = [_ev("door-1", 5, has=False)]
    t.ok(st.presence("", 60)["present"] is False,
         "a history row (no camera) is not somebody standing there")
    st.people = [_ev("door-1", 5)]
    t.ok(st.presence("", 60)["present"] is True, "somebody seen 5 s ago at a camera is there")
    t.ok(st.presence("door-2", 60)["present"] is False, "but not at a different camera")
    st.people = [_ev("door-1", 300)]
    t.ok(st.presence("", 60)["present"] is False, "and five minutes ago is not now")
    st._live = dict(st.partner(), events=[{"kind": "poll", "hasCamera": False}])
    st._live_at = 10 ** 12
    got = st.presence("", 60)
    t.ok(got["known"] is False, "an app with no camera source says it cannot tell", got)

    # ---- the gate inside the voice helper --------------------------------
    st = S.State("reconize")
    # Their app answering slowly must not slow the answer: the re-probe of
    # where Reconize runs took >1 s on the PC and the gate failed open.
    slow = st.partner
    st.partner = lambda: (time.sleep(1.5), slow())[1]
    S.Handler.state = st
    srv = ThreadingHTTPServer(("127.0.0.1", 0), S.Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    watcher = "http://127.0.0.1:%d/state" % srv.server_port
    V = _load("_voice_presence", "apps/voice/service.py")
    gate = lambda cfg: V.Brain.presence_gate(types.SimpleNamespace(cfg=cfg))  # noqa: E731
    on = {"presence": {"on": True, "seconds": 60}, "face": {"watcher": watcher}}
    t.ok(gate({"face": {"watcher": watcher}})[0], "presence mode is off unless turned on")
    ok, why = gate(on)
    t.ok(not ok and "nobody" in why, "on, with nobody there, the question is not taken", why)
    st.people = [_ev("door-1", 3)]
    t.ok(gate(on)[0], "on, with somebody there, it is taken")
    ok, why = gate({"presence": {"on": True}, "face": {"watcher": "http://127.0.0.1:1/state"}})
    t.ok(ok, "the watcher down: the question is still taken (fails open)", why)
    st.people = []
    st._live = dict(st.partner(), events=[{"kind": "poll", "hasCamera": False}])
    st._live_at = 10 ** 12
    t.ok(gate(on)[0], "an app that cannot see who stands where: taken (fails open)")
    del st._live                                  # back to the app with a camera

    # ---- the real helper refuses one /ask and still says things ----------
    tmp = Path(tempfile.mkdtemp(prefix="mice_presence_"))
    port = F._free_port()
    cfg = tmp / "voice.json"
    cfg.write_text(json.dumps({
        "service": "http://127.0.0.1:%d" % port, "faqThreshold": 0.75,
        "stt": {"enabled": False}, "llm": {"enabled": False}, "tts": {"enabled": False},
        "face": {"watcher": watcher}, "presence": {"on": True, "seconds": 60}}),
        encoding="utf-8")
    faq = tmp / "qa.json"
    faq.write_text('{"faqs": [{"q": "where is the toilet", "a": "on the left"}]}',
                   encoding="utf-8")
    log = open(tmp / "svc.log", "wb")
    proc = subprocess.Popen([sys.executable, "-u", str(F.CODE / "apps" / "voice" / "service.py"),
                             "--config", str(cfg), "--faq", str(faq), "--port", str(port)],
                            stdout=log, stderr=subprocess.STDOUT, env=dict(os.environ))
    base = "http://127.0.0.1:%d" % port
    try:
        deadline = time.time() + 30
        while time.time() < deadline:
            try:
                if json.loads(F.get(base + "/health")[1]).get("ok"):
                    break
            except Exception:                                # noqa: BLE001
                time.sleep(0.3)
        code, body = F.post(base + "/ask", json.dumps({"text": "where is the toilet"}).encode())
        got = json.loads(body or "{}")
        t.ok(code == 409 and got.get("nobodyHere"),
             "the real helper does not take a question with nobody there",
             (code, (body or "")[:200]))
        st.people = [_ev("door-1", 2)]
        code, body = F.post(base + "/ask", json.dumps({"text": "where is the toilet"}).encode())
        t.ok(code != 409 and not json.loads(body or "{}").get("nobodyHere"),
             "and takes it once somebody stands there", (code, (body or "")[:200]))
    finally:
        proc.terminate()
        try:
            proc.wait(5)
        except Exception:                                    # noqa: BLE001
            proc.kill()
        srv.shutdown()
