#!/usr/bin/env python3
"""A WebSocket client small enough to read, because it cannot be a dependency.

The hub is one stdlib program frozen into an exe, and this helper has to keep
up with an app that changes about daily. `websockets` and `websocket-client`
are both fine libraries and neither is available here, so this is the part of
RFC 6455 their feed actually uses, and nothing else.

WHAT THEIR FEED DOES, read from their code on 2026-09-10
  * `ws://<api>/api/node/events-feed?token=<jwt>` (their api/nodes.py:482)
  * a bad token is CLOSED WITH 4401 before the handshake completes
    (api/nodes.py:486), so a wrong token must send us back to the login rather
    than into a reconnect loop that can never succeed;
  * it then sends one JSON text frame per matched face, and NEVER READS from
    the socket. So nothing we send is consumed - which is fine, because the
    only thing we ever send is a pong.

WHAT THIS DELIBERATELY DOES NOT DO
  No extensions, no compression, no continuation frames, no fragmentation on
  send. Their frames are single JSON lines. If any of that changes, this
  raises and says so rather than quietly reading half a message - a greeting
  built on half a message is worse than no greeting.
"""
import base64
import hashlib
import json
import os
import socket
import struct
import time

from urllib.parse import urlsplit

# RFC 6455 section 1.3: the server proves it spoke WebSocket by hashing the
# key we send with this, so a plain HTTP server answering 200 cannot be
# mistaken for a feed.
GUID = "258EAFA5-E914-47DA-95CA-5AB0DC85B39A"

OP_TEXT, OP_BINARY, OP_CLOSE, OP_PING, OP_PONG = 0x1, 0x2, 0x8, 0x9, 0xA

# Their close code for a token the feed will not accept.
CLOSE_BAD_TOKEN = 4401


class FeedClosed(Exception):
    """The far end went away. Carries the close code when there was one."""

    def __init__(self, message, code=0):
        super().__init__(message)
        self.code = code


class Feed:
    """One connection to one feed. Not a reconnect loop - see service.py.

    Kept deliberately dumb: connect, read frames, hand back dicts. Deciding
    what to do about a drop belongs with the thing that knows whether the
    login still works.
    """

    def __init__(self, url, timeout=30.0):
        self.url = url
        self.timeout = timeout
        self.sock = None
        self.buf = b""

    # ---- connecting --------------------------------------------------

    def connect(self):
        parts = urlsplit(self.url)
        if parts.scheme not in ("ws", "http"):
            # No wss here on purpose: this talks to a program on THIS PC.
            raise FeedClosed("only ws:// is supported, not %r" % parts.scheme)
        host = parts.hostname or "127.0.0.1"
        port = parts.port or 80
        path = parts.path or "/"
        if parts.query:
            path += "?" + parts.query

        key = base64.b64encode(os.urandom(16)).decode("ascii")
        req = (
            "GET %s HTTP/1.1\r\n"
            "Host: %s:%d\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            "Sec-WebSocket-Key: %s\r\n"
            "Sec-WebSocket-Version: 13\r\n"
            "\r\n" % (path, host, port, key)
        )
        self.sock = socket.create_connection((host, port), timeout=self.timeout)
        self.sock.sendall(req.encode("ascii"))

        head = self._read_until(b"\r\n\r\n")
        line = head.split(b"\r\n", 1)[0].decode("latin-1")
        if " 101" not in line:
            # A 4xx here is the useful case: their feed refuses a bad token
            # before upgrading, so this is where a wrong login shows up.
            raise FeedClosed("the feed did not upgrade: %s" % line.strip())

        want = base64.b64encode(
            hashlib.sha1((key + GUID).encode("ascii")).digest()).decode("ascii")
        got = ""
        for ln in head.decode("latin-1").split("\r\n"):
            if ln.lower().startswith("sec-websocket-accept:"):
                got = ln.split(":", 1)[1].strip()
        if got != want:
            # Something answered, but it is not speaking WebSocket. Saying so
            # beats waiting for frames that will never come.
            raise FeedClosed("the far end is not a WebSocket feed")
        return self

    def close(self):
        if self.sock:
            try:
                self.sock.close()
            except OSError:
                pass
            self.sock = None

    # ---- reading -----------------------------------------------------

    def _read_until(self, marker):
        while marker not in self.buf:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise FeedClosed("the feed closed while connecting")
            self.buf += chunk
        head, self.buf = self.buf.split(marker, 1)
        return head + marker

    def _read_exact(self, n):
        while len(self.buf) < n:
            chunk = self.sock.recv(max(4096, n - len(self.buf)))
            if not chunk:
                raise FeedClosed("the feed closed mid-frame")
            self.buf += chunk
        out, self.buf = self.buf[:n], self.buf[n:]
        return out

    def _send_frame(self, opcode, payload=b""):
        """Every client frame is masked. A server may drop an unmasked one."""
        mask = os.urandom(4)
        masked = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
        header = bytes([0x80 | opcode])
        n = len(payload)
        if n < 126:
            header += bytes([0x80 | n])
        elif n < (1 << 16):
            header += bytes([0x80 | 126]) + struct.pack(">H", n)
        else:
            header += bytes([0x80 | 127]) + struct.pack(">Q", n)
        self.sock.sendall(header + mask + masked)

    def read_message(self):
        """The next JSON message, or None when the frame was housekeeping.

        Returning None rather than looping keeps the caller in charge of how
        long it is willing to wait - which is what makes a heartbeat possible
        without a second thread.
        """
        b0, b1 = self._read_exact(2)
        try:
            fin, opcode = b0 & 0x80, b0 & 0x0F
            masked, length = b1 & 0x80, b1 & 0x7F
            if length == 126:
                length = struct.unpack(">H", self._read_exact(2))[0]
            elif length == 127:
                length = struct.unpack(">Q", self._read_exact(8))[0]
            if masked:
                # A server must never mask. If one does, we are not talking to
                # what we think we are talking to.
                raise FeedClosed("the far end masked a frame, which a server may not")
            data = self._read_exact(length) if length else b""
        except socket.timeout as exc:
            # The header is consumed; restarting here would parse payload as a header.
            raise FeedClosed("the feed timed out mid-frame") from exc

        if opcode == OP_PING:
            self._send_frame(OP_PONG, data)
            return None
        if opcode == OP_PONG:
            return None
        if opcode == OP_CLOSE:
            code = struct.unpack(">H", data[:2])[0] if len(data) >= 2 else 0
            raise FeedClosed("the feed closed (%d)" % code, code)
        if not fin:
            # Their feed sends one JSON line per event and never splits it.
            # Guessing at reassembly would risk handing half a message on.
            raise FeedClosed("the feed split a message, which this cannot read")
        if opcode != OP_TEXT:
            return None
        try:
            return json.loads(data.decode("utf-8"))
        except ValueError:
            raise FeedClosed("the feed sent something that is not JSON")

    def messages(self, idle_timeout=None):
        """Every message, until the far end goes away."""
        if idle_timeout:
            self.sock.settimeout(idle_timeout)
        while True:
            try:
                got = self.read_message()
            except socket.timeout:
                yield None                 # still connected, nothing to say
                continue
            if got is not None:
                yield got


def connect(url, timeout=30.0):
    feed = Feed(url, timeout=timeout)
    try:
        return feed.connect()
    except Exception:
        feed.close()
        raise


def ws_url(api, path, token):
    """Their http address plus the feed path from the registry, as a ws:// one.

    The registry path carries `{token}` where the token belongs
    (config/partners.json), because WHERE it goes is their business and may
    change; a path without one gets it appended as a query.
    """
    parts = urlsplit(api)
    host = parts.hostname or "127.0.0.1"
    port = parts.port or 80
    if "{token}" in path:
        path = path.replace("{token}", token)
    else:
        path += ("&" if "?" in path else "?") + "token=" + token
    return "ws://%s:%d%s" % (host, port, path)


if __name__ == "__main__":                                   # a hand check
    import sys
    feed = connect(sys.argv[1])
    print("connected; reading. Ctrl+C to stop.")
    started = time.time()
    for msg in feed.messages(idle_timeout=5):
        print("%6.1fs  %s" % (time.time() - started, msg if msg else "..."))
