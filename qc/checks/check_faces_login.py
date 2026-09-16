"""The watcher logs in, renews before the session dies, and leaks neither half.

Driven against a FAKE Reconize that this check starts itself, so it proves the
real client code without needing their app, their database or a real account.

THE THREE THINGS THIS IS PAYING FOR

  * **The password never reaches a page.** `/health` and `/state` are read by a
    screen. Neither may contain the password or the token - the whole reason
    the credentials live in `main_python/faces_login.json` rather than under
    `apps/`, where every file is served with no login at all.

  * **The expiry is read from the token, not assumed.** Their lifetime is an
    environment setting: `JWT_EXPIRE_MINUTES`, default 480, in their
    `backend/app/config.py:96`. Anyone may change it. A client that assumes
    eight hours keeps using a token that died hours ago and finds out during a
    greeting, in front of a room. The token's own `exp` is the only honest
    source, so a token that expires in a minute must be treated as expiring in
    a minute.

  * **A refusal says which file to fix.** A wrong password and a stopped app
    need different actions, so they must not produce the same sentence.

QC MUST NEVER TOUCH THE REAL LOGIN. The service reads `MICE_FACES_LOGIN` when
it is set, the same way the hub reads `MICE_HUB_AUTH`, and this check points it
at a throwaway file. A check that overwrote somebody's credentials while
proving they are safe would be its own joke.
"""
import base64
import importlib.util
import json
import os
import socket
import tempfile
import threading
import time

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import qc as F


AREA = "hub"
TITLE = "the watcher logs in, renews in time, and never shows the password"
SOLO = True                       # binds a port for the fake app

GOOD_USER, GOOD_PASS = "mice", "correct-horse"
CFG = "config/partners.json"


def _jwt(seconds_left):
    """A token shaped like theirs, dying in `seconds_left`."""
    def part(obj):
        raw = json.dumps(obj).encode("utf-8")
        return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")
    return "%s.%s.%s" % (part({"alg": "HS256", "typ": "JWT"}),
                         part({"sub": 1, "username": GOOD_USER,
                               "exp": time.time() + seconds_left}),
                         "not-a-real-signature")


class FakeReconize(BaseHTTPRequestHandler):
    logins = 0
    token_life = 3600

    def do_POST(self):                                       # noqa: N802
        length = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
        FakeReconize.logins += 1
        if body.get("password") != GOOD_PASS:
            return self._send({"detail": "Invalid username or password."}, 401)
        self._send({"access_token": _jwt(FakeReconize.token_life),
                    "token_type": "bearer", "username": GOOD_USER})

    def _send(self, obj, code=200):
        raw = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, *a):
        pass


def _free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _service_module():
    spec = importlib.util.spec_from_file_location(
        "_faces_service_under_test", F.CODE / "apps" / "faces" / "service.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run(t):
    port = _free_port()
    httpd = ThreadingHTTPServer(("127.0.0.1", port), FakeReconize)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()

    cfg_path = F.CODE / CFG
    before = cfg_path.read_bytes()
    box = Path(tempfile.mkdtemp(prefix="qc_faces_login_"))
    login_file = box / "faces_login.json"
    old_env = os.environ.get("MICE_FACES_LOGIN")
    os.environ["MICE_FACES_LOGIN"] = str(login_file)
    try:
        import sys
        sys.path.insert(0, str(F.CODE / "tools"))
        import registry                                      # noqa: E402
        entry = json.loads(registry.strip_jsonc(before.decode("utf-8")))
        entry["_qc_login"] = {
            "name": "QC fake app", "open": "http://127.0.0.1:%d" % port,
            "api": "http://127.0.0.1:%d" % port, "health": "/health",
            "folder": ".", "login": {"kind": "jwt",
                                     "path": "/api/auth/login",
                                     "expires_min": 480},
            "events": [{"kind": "poll", "path": "/x", "items": "items",
                        "reports": ["known"], "hasCamera": False,
                        "map": {"who": "name"}, "lagSeconds": 60}],
        }
        cfg_path.write_text(json.dumps(entry, indent=2), encoding="utf-8")

        svc = _service_module()

        # ---- no login file yet: say what to write, and where ------------
        state = svc.State("_qc_login")
        tok, why = state.token_now()
        t.eq(tok, "", "with no credentials there is no token")
        t.contains(why, "faces_login.json", "and it says which file to write")
        t.contains(why, "apps/",
                   "and warns where NOT to put it - every file under apps/ is "
                   "served with no login at all")

        # ---- a wrong password is not the same as a stopped app ----------
        login_file.write_text(json.dumps(
            {"_qc_login": {"username": GOOD_USER, "password": "wrong"}}),
            encoding="utf-8")
        state = svc.State("_qc_login")
        tok, why = state.token_now()
        t.eq(tok, "", "a wrong password gets no token")
        t.contains(why, "faces_login.json",
                   "and the refusal names the file to fix")
        t.ok("not answering" not in why,
             "and does not blame the app for being stopped",
             "a wrong password and a stopped app need different actions, so "
             "they must not read the same: %r" % why)

        # ---- the right password logs in --------------------------------
        login_file.write_text(json.dumps(
            {"_qc_login": {"username": GOOD_USER, "password": GOOD_PASS}}),
            encoding="utf-8")
        FakeReconize.logins = 0
        state = svc.State("_qc_login")
        tok, why = state.token_now()
        t.ok(tok, "the right password gets a token", why)
        t.eq(FakeReconize.logins, 1, "with one login, not several")

        # ---- neither half ever reaches a page ---------------------------
        for name, body in (("health", state.health()),
                           ("state", state.snapshot())):
            flat = json.dumps(body)
            t.ok(GOOD_PASS not in flat,
                 "/%s never carries the password" % name,
                 "a screen reads this: %s" % flat[:200])
            t.ok(tok not in flat,
                 "/%s never carries the token either" % name,
                 "a token is a password that already worked")
        t.eq(state.health().get("loggedIn"), True,
             "while still saying plainly that it is logged in")

        # ---- the expiry comes from the TOKEN, not from a guess ----------
        # 480 minutes is what the registry says. This token says 30 seconds.
        # A client that trusts the setting would report eight hours and keep
        # using a dead token.
        FakeReconize.token_life = 30
        state = svc.State("_qc_login")
        state.token_now()
        left = state.health().get("tokenExpiresIn")
        t.ok(0 < left <= 31,
             "a short-lived token is reported as short-lived (%ss)" % left,
             "their JWT_EXPIRE_MINUTES is an environment setting, so the "
             "registry's 480 is a fallback and never the truth")

        # ---- and it renews before the session dies ----------------------
        # This token dies inside the renew margin, so the very next ask must
        # fetch a new one rather than hand back the old one.
        FakeReconize.logins = 0
        state.token_now()
        t.ok(FakeReconize.logins >= 1,
             "a token inside its renew margin is replaced, not reused",
             "otherwise the first greeting after eight hours is the thing "
             "that discovers the session ended")

        # ---- a healthy token is NOT re-fetched every time ---------------
        FakeReconize.token_life = 3600
        state = svc.State("_qc_login")
        state.token_now()
        FakeReconize.logins = 0
        for _ in range(3):
            state.token_now()
        t.eq(FakeReconize.logins, 0,
             "a token with hours left is reused, not asked for again")
    finally:
        cfg_path.write_bytes(before)
        t.eq(cfg_path.read_bytes(), before, "partner config restored byte-for-byte")
        httpd.shutdown()
        if old_env is None:
            os.environ.pop("MICE_FACES_LOGIN", None)
        else:
            os.environ["MICE_FACES_LOGIN"] = old_env
