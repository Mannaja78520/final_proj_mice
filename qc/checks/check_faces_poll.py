"""Reading their history without dropping anybody.

Driven against a FAKE history this check serves itself, so the awkward cases
can be produced on purpose instead of waited for.

WHAT MAKES THIS MORE THAN ONE GET, AND WHY EACH PART EARNS ITS KEEP

  * **Their history pages, newest first, from page 1**
    (their api/history.py:30,68). A rush of arrivals spreads across pages, so
    a poll that reads page one and stops loses the older half of the rush -
    at exactly the moment the rig is meant to be greeting people.

  * **`detected_at` is stamped when the row is BUILT, not when it commits**
    (their models/models.py:64, `default_factory=datetime.now`). A row can
    therefore turn up carrying a time OLDER than one already read. A cursor
    that trusts the newest time it has seen steps straight over that person
    and never mentions it. So the checkpoint only says how far back to look,
    and the window reaches `lagSeconds` behind it.

  * **The window means rows come back twice**, so the SEEN-SET decides what is
    new, not the clock. Their row ids are random, so a range would be
    meaningless - only the set works.

  * **A history row has no camera.** Their row is built at
    api/history.py:71-84 out of id, upload_id, upload_filename, person_id,
    name, participant_id, confidence, status and detected_at. There is no
    node_id in it. Counting one is fine; treating it as somebody standing at a
    particular door is a guess, and the rig must not make it.
"""
import base64
import importlib.util
import json
import os
import socket
import tempfile
import threading
import time

from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import qc as F


AREA = "hub"
TITLE = "their history is read without dropping anybody, and claims no camera"
SOLO = True

USER, PASS = "mice", "correct-horse"
LAG = 120
CFG = "config/partners.json"

# pages[n] -> the rows that page returns. Set by the test.
PAGES = {}


def _jwt(seconds_left=3600):
    def part(obj):
        return base64.urlsafe_b64encode(
            json.dumps(obj).encode("utf-8")).decode("ascii").rstrip("=")
    return "%s.%s.x" % (part({"alg": "HS256"}),
                        part({"sub": 1, "exp": time.time() + seconds_left}))


def row(rid, name, ago_seconds, status="matched"):
    """One history row, shaped exactly like theirs."""
    return {"id": rid, "upload_id": "u1", "upload_filename": None,
            "person_id": ("p-" + rid) if name else None,
            "name": name, "participant_id": ("P" + rid) if name else None,
            "confidence": 0.9, "status": status,
            "detected_at": (datetime.now()
                            - timedelta(seconds=ago_seconds)).isoformat()}


class FakeApp(BaseHTTPRequestHandler):
    unauthorised = False

    def do_POST(self):                                       # noqa: N802
        n = int(self.headers.get("Content-Length") or 0)
        self.rfile.read(n)
        self._send({"access_token": _jwt(), "token_type": "bearer",
                    "username": USER})

    def do_GET(self):                                        # noqa: N802
        u = urlparse(self.path)
        if FakeApp.unauthorised:
            return self._send({"detail": "Not authenticated"}, 401)
        page = int((parse_qs(u.query).get("page") or ["1"])[0])
        self._send({"items": PAGES.get(page, []), "total": 0,
                    "page": page, "page_size": 100})

    def _send(self, obj, code=200):
        raw = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, *a):
        pass


def _service_module():
    spec = importlib.util.spec_from_file_location(
        "_faces_poll_under_test", F.CODE / "apps" / "faces" / "service.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run(t):
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    httpd = ThreadingHTTPServer(("127.0.0.1", port), FakeApp)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()

    cfg_path = F.CODE / CFG
    before = cfg_path.read_bytes()
    box = Path(tempfile.mkdtemp(prefix="qc_faces_poll_"))
    login = box / "faces_login.json"
    login.write_text(json.dumps({"_qc_poll": {"username": USER,
                                              "password": PASS}}),
                     encoding="utf-8")
    old_env = os.environ.get("MICE_FACES_LOGIN")
    os.environ["MICE_FACES_LOGIN"] = str(login)
    try:
        import sys
        sys.path.insert(0, str(F.CODE / "tools"))
        import registry                                      # noqa: E402
        entry = json.loads(registry.strip_jsonc(before.decode("utf-8")))
        entry["_qc_poll"] = {
            "name": "QC fake history", "open": "http://127.0.0.1:%d" % port,
            "api": "http://127.0.0.1:%d" % port, "health": "/health",
            "folder": ".", "login": {"kind": "jwt",
                                     "path": "/api/auth/login"},
            "events": [{
                "kind": "poll",
                "path": "/api/history?page_size=100&page={page}",
                "items": "items", "reports": ["known", "unknown"],
                "hasCamera": False, "lagSeconds": LAG,
                "map": {"who": "name", "id": "participant_id",
                        "when": "detected_at", "status": "status",
                        "row": "id"}}],
        }
        cfg_path.write_text(json.dumps(entry, indent=2), encoding="utf-8")
        svc = _service_module()

        # ---- a rush spread over two pages is read whole -----------------
        PAGES.clear()
        PAGES[1] = [row("a", "Ann", 10), row("b", "Ben", 20)]
        PAGES[2] = [row("c", "Cal", 30), row("d", None, 40, "unknown")]
        state = svc.State("_qc_poll")
        fresh, why = state.poll_once()
        t.eq(why, "", "the first read works")
        t.eq(sorted(e["who"] for e in fresh),
             ["", "Ann", "Ben", "Cal"],
             "every row on BOTH pages is read, not just page one")
        t.eq(len(fresh), 4,
             "four arrivals across two pages")

        # ---- a stranger arrives here, and carries no camera -------------
        stranger = [e for e in fresh if not e["known"]]
        t.eq(len(stranger), 1, "the unknown face is one of them")
        t.eq(stranger[0]["camera"], "",
             "and it carries no camera, because a history row has none")
        for e in fresh:
            t.eq(e["hasCamera"], False,
                 "no history event claims to know which camera saw it")

        # ---- reading again reports nobody twice -------------------------
        again, _ = state.poll_once()
        t.eq(again, [], "the same rows are not reported a second time")

        # ---- A ROW THAT ARRIVES LATE, WITH AN OLDER TIME ----------------
        # This is the one their detected_at causes. `e` is stamped 25 seconds
        # ago - OLDER than rows already read - and only appears now. A cursor
        # that trusted the newest time seen would never mention this person.
        PAGES[1] = [row("e", "Eve", 25)] + PAGES[1]
        late, _ = state.poll_once()
        t.eq([e["who"] for e in late], ["Eve"],
             "a row that lands late with an older time is still caught")

        # ---- but the window is bounded, not unbounded -------------------
        PAGES[1] = [row("old", "Ancient", LAG + 600)] + PAGES[1]
        far, _ = state.poll_once()
        t.ok(all(e["who"] != "Ancient" for e in far),
             "a row far older than the window is left alone",
             "otherwise every poll re-reads the whole day and the rig "
             "greets people who arrived this morning")

        # ---- a session that ends says so, and recovers ------------------
        FakeApp.unauthorised = True
        _none, why = state.poll_once()
        t.contains(why, "session ended",
                   "an expired session is said in words, not as a number")
        t.eq(state.token, "",
             "and the dead token is dropped, so the next read logs in again")
        FakeApp.unauthorised = False
        PAGES[1] = [row("z", "Zoe", 5)] + PAGES[1]
        back, why = state.poll_once()
        t.eq(why, "", "the next read recovers by itself")
        t.eq([e["who"] for e in back], ["Zoe"],
             "and picks up the person who arrived meanwhile")
    finally:
        cfg_path.write_bytes(before)
        t.eq(cfg_path.read_bytes(), before, "partner config restored byte-for-byte")
        FakeApp.unauthorised = False
        httpd.shutdown()
        if old_env is None:
            os.environ.pop("MICE_FACES_LOGIN", None)
        else:
            os.environ["MICE_FACES_LOGIN"] = old_env
