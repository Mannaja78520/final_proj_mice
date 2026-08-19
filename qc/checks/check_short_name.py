"""`http://mice.local` reaches the hub, and a taken port 80 changes nothing.

Asked on 2026-08-19: why type `mice.local:8642` rather than `mice.local`.
Because a bare name means port 80 and the hub is not there.

The obvious fix is to move the hub to port 80, and it is the wrong one. On
Windows something else often already holds it - IIS, Skype, another dev
server - and the hub would then fail to start AT ALL. A machine where the
control panel refuses to run is far worse than one where a convenience URL
does not.

So there are two properties here and the second matters more than the first:

  * when port 80 is free, it is taken by a listener whose only job is to
    redirect to the real one;
  * when it is NOT free, the hub starts exactly as before and says nothing.
    Losing a short name is a shrug. Losing the hub is a show.

Both are driven for real - a socket is bound to port 80 to take it away, which
is the only way to test the case that matters.
"""
import socket
import sys
import threading

import qc as F

AREA = "hub"
TITLE = "the short name works, and never blocks the hub"


def run(t):
    sys.path.insert(0, str(F.HUB))
    import main  # noqa: PLC0415 - the module under test

    t.ok(hasattr(main, "start_short_name"),
         "the hub can answer on the short name")
    src = (F.HUB / "main.py").read_text(encoding="utf-8")
    i = src.find("def start_short_name")
    # Wide enough to reach the bind past its explanation: the comment IS
    # the reason the listener backs off, so it will only grow.
    body = src[i:i + 3200]
    t.contains(body, "except OSError",
               "a port it cannot have is caught, not raised")
    t.contains(body, "allow_reuse_address = False",
               "and it never takes a port another program is holding")
    t.contains(body, "302", "the second listener only redirects")
    t.ok("PORT" in body and "start_short_name(port=80)" in src,
         "it sends callers to the port the hub is really on")

    # ---- it takes the port when the port is free --------------------
    srv = main.start_short_name(port=0)      # 0 = any free port, same code path
    if not t.ok(srv, "it binds a free port"):
        return
    took = srv.server_address[1]
    try:
        c = _get(took, "/")
        t.eq(c[0], 302, "and answers with a redirect")
        t.contains(c[1] or "", str(main.PORT),
                   "pointing at the port the hub actually listens on")
    finally:
        srv.shutdown()

    # ---- and it gives up quietly when the port is taken -------------
    # The case that matters. A socket is bound first, so the hub meets exactly
    # what IIS or Skype would do to it.
    hostage = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # No SO_REUSEADDR, and the wildcard address - exactly how another server
    # holds a port. With SO_REUSEADDR set on BOTH sides, Windows lets the
    # second bind succeed and the two processes then fight over connections,
    # which is why the hub's redirect listener sets allow_reuse_address False.
    hostage.bind(("0.0.0.0", 0))
    hostage.listen(1)
    port = hostage.getsockname()[1]
    try:
        again = main.start_short_name(port=port)
        t.ok(again is None,
             "a port that is already taken is given up on, not fought over",
             "start_short_name returned %r - if this raises instead, the hub "
             "does not start on any PC that has IIS or Skype" % (again,))
    finally:
        hostage.close()


def _get(port, path):
    """Status and Location, without following the redirect."""
    import http.client
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=8)
    try:
        c.request("GET", path)
        r = c.getresponse()
        out = (r.status, r.getheader("Location"))
        r.read()
        return out
    finally:
        c.close()
