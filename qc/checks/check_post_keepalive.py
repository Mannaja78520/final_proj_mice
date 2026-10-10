"""A POST body the route never read cannot become the next request.

The hub speaks HTTP/1.1 keep-alive, so one handler object serves every request
on a browser's socket. Found by the PC lab session (2026-09-29, Codex helped):
a POST whose route answers without reading the body (POST /api/whoami, any 401
from the users routes) left those bytes on the socket, and the next request on
the same connection was parsed starting from them - `{"x": 1}GET /api/...` -
and answered 400. drain() existed, but only send_err and the login gate called
it, and its "already read" flag was never cleared, so after one POST that DID
read its body, every later refusal on that socket skipped the drain too.

Fixed: send_bytes and send_redirect drain any unread POST body, do_GET/do_POST
clear the flag per request, and the two routes that read rfile by hand go
through body() so the flag knows. Driven over one raw HTTPConnection, because
urllib opens a fresh socket per call and never shows it.
"""
import http.client
import json

import qc as F

AREA = "hub"
TITLE = "a POST body the route never read cannot become the next request"


def _call(c, method, path, body=None):
    hdrs = {"Content-Type": "application/json"}
    c.request(method, path, body=body, headers=hdrs)
    r = c.getresponse()
    return r.status, r.read()


def run(t):
    base, _main = F.start_hub()
    port = int(base.rsplit(":", 1)[1])
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    try:
        junk = json.dumps({"ignored": "x" * 200}).encode()

        # 1. a POST route that answers without reading what was sent
        st, _ = _call(c, "POST", "/api/whoami", junk)
        t.eq(st, 200, "POST /api/whoami answers")
        st, data = _call(c, "GET", "/api/whoami")
        t.ok(st == 200, "the next request on the same socket is read cleanly",
             "got %s %r - the unread POST body was parsed as its first line"
             % (st, data[:120]))

        # 2. one POST that DID read its body, then one that did not: the flag
        # from the first must not excuse the second
        # (/api/reports reads its body itself; it used to bypass body(), so
        # the drain below would then wait for bytes already consumed)
        st, _ = _call(c, "POST", "/api/reports",
                      json.dumps({"id": "no-such-report", "status": "fixed"}).encode())
        t.ok(st == 200, "a report update that reads its body is answered",
             "status %s" % st)
        st, _ = _call(c, "POST", "/api/whoami", junk)
        st, data = _call(c, "GET", "/api/version")
        t.ok(st == 200, "after a POST that read its body, the next unread one "
             "is still drained",
             "got %s %r - the already-read flag carried over from the "
             "previous request on this socket" % (st, data[:120]))

        # 3. a refusal that goes straight through send_bytes (401, no send_err)
        st, _ = _call(c, "POST", "/api/users/add", junk)
        t.ok(st == 401, "adding a user without a login is refused",
             "status %s" % st)
        st, data = _call(c, "GET", "/api/whoami")
        t.ok(st == 200, "and the refusal's unread body does not break the "
             "next request", "got %s %r" % (st, data[:120]))
    finally:
        c.close()
