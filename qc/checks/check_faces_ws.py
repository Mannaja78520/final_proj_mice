"""The live feed: a hand-written WebSocket client, and what it refuses.

There is no `websockets` library here and there never will be - the hub is one
stdlib program frozen into an exe. So `apps/faces/wsclient.py` is the part of
RFC 6455 their feed actually uses, and this check is what makes that safe to
rely on. It runs a small server of its own so the awkward cases can be
produced on purpose rather than waited for.

WHAT IT HOLDS, AND WHY EACH ONE IS HERE

  * **The handshake is verified, not assumed.** A plain HTTP server answering
    200 must not be mistaken for a feed. The `Sec-WebSocket-Accept` hash is
    the only thing that proves the far end speaks WebSocket at all.

  * **A refused login is not a network problem.** Their feed closes with 4401,
    and because it closes BEFORE upgrading (their api/nodes.py:486) that
    arrives as a 403 on the handshake. Retrying faster can never fix it; the
    answer is a new token. A client that treats it as a drop spins for ever
    while the screen says *reconnecting*.

  * **Half a message is worse than none.** Their feed sends one JSON line per
    face and never splits it. If that ever changes, this raises rather than
    quietly handing on a fragment - a greeting built from half a payload names
    the wrong person.

  * **A server may never mask a frame.** If one does, we are not talking to
    what we think we are.

  * **And a live event goes through the SAME door as the poll.** Their feed
    carries a camera; their history does not. Both end up in `accept()`, so
    one person seen by both is still one arrival.
"""
import base64
import hashlib
import importlib.util
import json
import socket
import struct
import threading

import qc as F


AREA = "hub"
TITLE = "the live feed is read safely, and a refused login is told apart"
SOLO = True                       # binds a port for the fake feed

GUID = "258EAFA5-E914-47DA-95CA-5AB0DC85B39A"


def _mod(name):
    spec = importlib.util.spec_from_file_location(
        "_%s_under_test" % name, F.CODE / "apps" / "faces" / ("%s.py" % name))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def frame(payload, opcode=0x1, mask=False):
    """A server frame. `mask` is for proving we refuse a masked one."""
    body = payload.encode("utf-8") if isinstance(payload, str) else payload
    head = bytes([0x80 | opcode])
    n = len(body)
    flag = 0x80 if mask else 0
    if n < 126:
        head += bytes([flag | n])
    else:
        head += bytes([flag | 126]) + struct.pack(">H", n)
    if mask:
        key = b"\x01\x02\x03\x04"
        body = bytes([b ^ key[i % 4] for i, b in enumerate(body)])
        head += key
    return head + body


class Fake(threading.Thread):
    """A one-connection WebSocket server that does exactly what it is told."""

    def __init__(self, script, upgrade=True, status="101", bad_key=False):
        super().__init__(daemon=True)
        self.script = script            # bytes to send after the handshake
        self.upgrade = upgrade
        self.status = status
        self.bad_key = bad_key          # answer 101 with the WRONG proof
        self.sock = socket.socket()
        self.sock.bind(("127.0.0.1", 0))
        self.sock.listen(1)
        self.port = self.sock.getsockname()[1]
        self.got_pong = threading.Event()

    def run(self):
        try:
            conn, _ = self.sock.accept()
        except OSError:
            return
        try:
            req = b""
            while b"\r\n\r\n" not in req:
                chunk = conn.recv(4096)
                if not chunk:
                    return
                req += chunk
            key = ""
            for ln in req.decode("latin-1").split("\r\n"):
                if ln.lower().startswith("sec-websocket-key:"):
                    key = ln.split(":", 1)[1].strip()
            if not self.upgrade:
                conn.sendall(("HTTP/1.1 %s Forbidden\r\n"
                              "Content-Length: 0\r\n\r\n" % self.status)
                             .encode("ascii"))
                return
            acc = base64.b64encode(
                hashlib.sha1(((key if not self.bad_key else "wrong") + GUID)
                             .encode()).digest()).decode()
            conn.sendall(("HTTP/1.1 101 Switching Protocols\r\n"
                          "Upgrade: websocket\r\nConnection: Upgrade\r\n"
                          "Sec-WebSocket-Accept: %s\r\n\r\n" % acc).encode())
            conn.sendall(self.script)
            # anything the client sends back (a pong) arrives here
            conn.settimeout(3)
            try:
                if conn.recv(64):
                    self.got_pong.set()
            except (socket.timeout, OSError):
                pass
        finally:
            try:
                conn.close()
            except OSError:
                pass

    def url(self):
        return "ws://127.0.0.1:%d/api/node/events-feed?token=x" % self.port

    def stop(self):
        try:
            self.sock.close()
        except OSError:
            pass


def run(t):
    ws = _mod("wsclient")

    # ---- a real event, read whole ------------------------------------
    body = json.dumps({"node_id": "door-in", "participant_id": "P7",
                       "name": "Ann", "checkin": "new", "at": "2026-09-10T10:00:00"})
    srv = Fake(frame(body))
    srv.start()
    try:
        feed = ws.connect(srv.url())
        got = feed.read_message()
        t.eq(got.get("name"), "Ann", "a live frame is read and handed back")
        t.eq(got.get("node_id"), "door-in", "with the camera it names")
        feed.close()
    finally:
        srv.stop()

    # ---- a ping is answered, and is not an event ---------------------
    srv = Fake(frame(b"hi", opcode=0x9) + frame(body))
    srv.start()
    try:
        feed = ws.connect(srv.url())
        first = feed.read_message()
        t.eq(first, None, "a ping is housekeeping, not a person arriving")
        t.ok(srv.got_pong.wait(3), "and it is answered with a pong",
             "a feed that stops hearing from us is one that hangs up")
        t.eq(feed.read_message().get("name"), "Ann",
             "and the real event right behind it still arrives")
        feed.close()
    finally:
        srv.stop()

    # ---- THEIR REFUSED LOGIN, which is not a drop --------------------
    srv = Fake(b"", upgrade=False, status="403")
    srv.start()
    try:
        failed = ""
        try:
            ws.connect(srv.url())
        except ws.FeedClosed as e:
            failed = str(e)
        t.ok("403" in failed,
             "a feed that refuses the login says so, with their status",
             "their api/nodes.py:486 closes before upgrading, so a bad token "
             "arrives as a 403 here - retrying faster can never fix it, and "
             "the caller has to know to get a new token instead: %r" % failed)
    finally:
        srv.stop()

    # ---- something that is not a feed at all -------------------------
    plain = socket.socket()
    plain.bind(("127.0.0.1", 0))
    plain.listen(1)

    def be_http():
        try:
            conn, _ = plain.accept()
            conn.recv(4096)
            conn.sendall(b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\nhi")
            conn.close()
        except OSError:
            pass

    threading.Thread(target=be_http, daemon=True).start()
    try:
        why = ""
        try:
            ws.connect("ws://127.0.0.1:%d/x" % plain.getsockname()[1])
        except ws.FeedClosed as e:
            why = str(e)
        t.ok(why, "a plain web server is not mistaken for a feed", why)
    finally:
        plain.close()

    # ---- 101, but with the wrong proof -------------------------------
    # A server that upgrades and cannot prove it hashed our key is not one.
    # Asserting only that SOMETHING was refused missed this: the plain-HTTP
    # test above never reaches the hash, because it fails on the status line
    # first. Sabotage found the hole.
    srv = Fake(frame(body), bad_key=True)
    srv.start()
    try:
        why = ""
        try:
            ws.connect(srv.url())
        except ws.FeedClosed as e:
            why = str(e)
        t.contains(why.lower(), "not a websocket",
                   "a 101 without the right proof is refused, and named")
    finally:
        srv.stop()

    # ---- a masked frame, and a split message, refused FOR THE RIGHT REASON
    # `why` being non-empty is not enough: with the mask rule removed the
    # client read masked bytes as JSON and failed with "not JSON", which
    # looked like a pass. The reason has to be the one that matters.
    for script, want, what in (
            (frame(body, mask=True), "masked", "a masked server frame"),
            (bytes([0x01, len(body)]) + body.encode(), "split",
             "half a message")):
        srv = Fake(script)
        srv.start()
        try:
            why = ""
            try:
                feed = ws.connect(srv.url())
                feed.read_message()
            except ws.FeedClosed as e:
                why = str(e)
            t.contains(why.lower(), want,
                       "%s is refused, and says which rule it broke" % what)
        finally:
            srv.stop()

    # ---- a live event goes through the same door as the poll ---------
    svc = _mod("service")
    state = svc.State("reconize")
    src = state.ws_source()
    t.ok(src, "the registry describes a live feed to listen to")
    event = state.from_ws(src, {"node_id": "kiosk", "participant_id": "P9",
                                "name": "Bea", "checkin": "new",
                                "at": "2026-09-10T10:00:00"})
    t.eq(event["who"], "Bea", "a live frame becomes one of our arrivals")
    t.eq(event["source"], "ws", "that says where it came from")
    kept = state.note(event)
    t.ok(kept is not None, "and it is reported the first time")
    t.eq(kept["hasCamera"], False,
         "while 'kiosk' still does not count as a door, even live")
    again = state.note(state.from_ws(src, {
        "node_id": "door-in", "participant_id": "P9", "name": "Bea",
        "checkin": "already", "at": "2026-09-10T10:00:01"}))
    t.eq(again, None,
         "the same person a second later is not a second arrival")
    t.eq(kept["camera"], "door-in",
         "and the copy that knew a real door improved the one we kept")
