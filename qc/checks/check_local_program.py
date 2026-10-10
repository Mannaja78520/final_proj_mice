"""A program on this PC may ask the rig to speak; a web page on this PC may not (A6-3).

Asked for in A6-3: a foreign Python program needs one address and one verb -
POST /api/speak with JSON, no login, from this PC. That opens a door, and a
page open in this PC's browser comes from 127.0.0.1 exactly like a program.
So what goes through it is held here:

  * a program at this PC (JSON, no Origin, no Sec-Fetch-*) is let in;
  * a web page open on this PC is refused like a stranger - every browser
    request carries Origin or Sec-Fetch-*, a DNS-rebinding page included,
    and even the hub's own page must log in;
  * a form post is refused: a website can send one without asking first;
  * from the network it still needs a login, and reading stays gated.

The same weakness sat in the routes that start an outside program (Reconize,
All-Jao): any website could start one with an <img> GET. They now take POST
only, and at this PC a page counts only when its Origin is THIS hub - an IP
literal or one of our names with our port, never a prefix test
(is_self("127.evil.example") is true).
"""
import json
import urllib.error
import urllib.request

import qc as F

AREA = "auth"
TITLE = "a program on this PC may ask to speak, a web page on it may not"


def _post(url, body=b"", headers=None, method="POST"):
    req = F._with_cookie(urllib.request.Request(url, data=body if method == "POST" else None,
                                                method=method))
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, r.read().decode(errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace")


def run(t):
    base, main = F.start_hub()
    port = base.rsplit(":", 1)[1]
    speak = main.hub_speak
    # Never a real voice: on a Windows PC "pc" is a working speaker, and a QC
    # run must not talk through it.
    speak.SPEECH.tts = lambda *a: (None, "qc: no voice here")
    js = {"Content-Type": "application/json"}
    say = json.dumps({"text": "hello from a program", "to": "pc"}).encode()
    F.logout_qc()
    try:
        code, body = _post(base + "/api/speak", say, js)
        t.ok(code == 200 and json.loads(body).get("ok"),
             "a program on this PC asks the rig to speak with no login", (code, body[:200]))

        for why, extra in (
                ("the hub's own page, not logged in", {"Origin": "http://127.0.0.1:" + port}),
                ("another website open on this PC", {"Origin": "https://evil.example"}),
                ("a DNS-rebinding page, same-origin with its own name",
                 {"Origin": "http://evil.example:" + port}),
                ("a browser request without Origin (Sec-Fetch)", {"Sec-Fetch-Site": "same-origin"})):
            code, body = _post(base + "/api/speak", say, dict(js, **extra))
            t.ok(code == 401 and "need_login" in body,
                 "refused without a login: %s" % why, (code, body[:160]))

        code, body = _post(base + "/api/speak", say, {"Content-Type": "text/plain"})
        t.ok(code == 401, "a form-like post is refused - a website can send one unasked",
             (code, body[:160]))
        code, body = _post(base + "/api/speak", headers=js, method="GET")
        t.ok(code == 401, "reading the queue is never open, even to a program at this PC",
             (code, body[:160]))

        real_is_self = main.is_self
        main.is_self = lambda ip: False
        try:
            code, body = _post(base + "/api/speak", say, js)
            t.ok(code == 401 and "need_login" in body,
                 "from the network the same program needs a login", (code, body[:160]))
            code, body = _post(base + "/api/partners/start?id=nobody", b"",
                               {"Origin": "http://127.0.0.1:" + port})
            t.ok(code == 401, "and so does starting an outside program", (code, body[:160]))
        finally:
            main.is_self = real_is_self

        # ---- starting an outside program ---------------------------------
        for route in ("/api/partners/start?id=nobody", "/api/all-jao/start",
                      "/api/reconize/start"):
            code, body = _post(base + route, method="GET")
            t.ok(code == 405, "%s takes POST only - an <img> on any website used to "
                              "start it" % route.split("?")[0], (code, body[:160]))
            code, body = _post(base + route, b"", {"Origin": "https://evil.example"})
            t.ok(code == 401 and "need_login" in body,
                 "%s refuses a website open on this PC" % route.split("?")[0],
                 (code, body[:160]))
        for origin in ("http://127.0.0.1:" + port, "http://localhost:" + port, None):
            code, body = _post(base + "/api/partners/start?id=nobody", b"",
                               {"Origin": origin} if origin else {})
            t.ok(code == 200 and "nobody" in body,
                 "the hub's own page at %s (or a program) still starts one with no login"
                 % (origin or "no Origin"), (code, body[:160]))
        for origin in ("http://127.0.0.1:1", "http://127.evil.example:" + port,
                       "http://localhost.evil.example:" + port):
            code, body = _post(base + "/api/partners/start?id=nobody", b"",
                               {"Origin": origin})
            t.ok(code == 401, "a page from %s is not this hub" % origin, (code, body[:160]))
    finally:
        speak.SPEECH.silence()
        speak.SPEECH.tts = None
