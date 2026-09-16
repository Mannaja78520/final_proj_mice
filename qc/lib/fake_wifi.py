"""A fake module reachable over HTTP — the WiFi transport, testable on a PC.

`fake_serial` covers USB and RS485. The WiFi path is different code all the way
down: the hub proxies through `/api/robot/*` and `/api/dev/*` to a real HTTP
API on the board, and Nong Studio's file transfer takes a *completely separate*
branch on WiFi (the module's HTTP file API) from the one it takes on a cable
(FBEGIN/FDATA/FEND). Only the cable branch has ever been exercised.

This serves the same endpoints a real module serves, on 127.0.0.1, so the WiFi
half of the hub and of Studio can be driven without a board or a network.

    wifi = fake_wifi.start()        # -> "127.0.0.1:<port>", usable as an IP
    fake_wifi.MODULE.cmds           # every command it was sent
"""
import json
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class _Module:
    """Just enough of a nong to answer the hub and Studio."""

    def __init__(self):
        self.reset()

    def reset(self):
        self.ota = b""                     # firmware received over the air
        self.busy = False                  # mid-move: an OTA must be refused
        self.cmds = []                     # every command line received
        self.joints = [90.0] * 10
        self.files = {"wave.yaml": b"name: wave\nsteps:\n  - pose: \"90 90 90 90 90 90 90 90 90 90 T 500\"\n"}
        self.pins = {"servo1": 32, "servo2": 33}
        # The account a fresh board ships with (UserStore.cpp: manny/12345678)
        # and the session a successful login hands out. Empty session = nobody
        # is logged in, which is how every board starts.
        self.user, self.password = "manny", "12345678"
        self.session = ""
        # Old firmware: no /api/login at all, and no gate on /api/ota either.
        self.no_login_route = False
        # Current firmware gates /api/cmd too: a command that CHANGES needs the
        # session, only queries answer to anyone. Found on the real bench
        # 2026-08-26, where POSE over WiFi answered `401 ERR log in first`
        # while PING sailed through. The real board decides from its generated
        # command table (query/safety flags); this fake keeps the query-ish
        # heads, which is close enough to catch a hub that stopped logging in.
        self.gate_cmd = True
        # The live view. `streaming` is the board's one-watcher rule; the
        # counters let a check see how many connections the hub really made.
        self.streaming = False
        self.stream_lock = threading.Lock()
        self.stream_frames = 40
        self.frames_sent = 0
        self.streams_opened = 0

    # the text command surface, mirroring fake_serial's module
    def cmd(self, c):
        c = c.strip()
        self.cmds.append(c)
        head = c.split(" ", 1)[0].upper()
        if head == "INFO":
            return json.dumps(self.status())
        if head == "PING":
            return "PONG 7 nong-wifi nong"
        if head == "POSE":
            vals = [v for v in c.split()[1:] if v.replace(".", "").lstrip("-").isdigit()]
            for i, v in enumerate(vals[:10]):
                self.joints[i] = float(v)
            return "OK POSE"
        if head in ("PIN", "PIN?", "PINS", "PINS?"):
            up = c.upper()
            if up.startswith("PIN VALID"):
                return json.dumps([{"g": 13, "c": "ok", "pwm": True},
                                   {"g": 6, "c": "flash"}])
            parts = c.split()
            if len(parts) >= 3 and parts[1].upper() not in ("VALID", "CLEAR"):
                self.pins[parts[1].lower()] = int(parts[2])   # PIN <name> <gpio>
                return "OK %s=%s (reboot to apply)" % (parts[1].lower(), parts[2])
            return json.dumps(self.pins)
        if head == "FILES":
            return json.dumps([{"n": n, "s": len(b)} for n, b in self.files.items()])
        if head == "LIMIT?":
            return json.dumps({"min": [30] * 10, "max": [150] * 10,
                               "gear_pinion": [14] * 10, "gear_gear": [19] * 10,
                               "pulse_min": [500] * 10, "pulse_max": [2500] * 10,
                               "max_dps": [375] * 10, "servo_range": [180] * 10,
                               "frame_hz": [50] * 10})
        if head in ("HOME", "ZERO", "RELAX", "ATTACH", "SPEED", "LIMIT", "GEAR",
                    "PULSE", "RANGE", "RATE", "SERVO", "MOVE", "STOP", "JCFG",
                    "AUTH", "SETZERO", "CAL"):
            return "OK " + head
        return "OK"

    def status(self):
        return {
            "id": 7, "name": "nong-wifi", "type": "nong", "fw": "1.0.0", "sd": True,
            # what a real board reports since buildStatus grew it (Identity::chip)
            "chip": CHIP,
            "types": ["lift", "nong", "blank"],
            "caps": ["pins", "sequences", "users", "rs485", "sd",
                     "joints", "servos", "calibration"],
            "seq": {"running": False, "file": ""},
            "wifi": {"mode": "sta", "wmode": "on", "ip": "127.0.0.1",
                     "ssid": "qc", "rssi": -50},
            "module": {"joints": self.joints, "seq": "", "speed": 120},
        }


MODULE = _Module()

# The eFuse MAC a real board reports as `chip` in INFO and /api/status - the
# one identifier nobody can change, and what the hub merges its routes on.
CHIP = "QCWIFICHIP01"


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass                                # QC output stays readable

    def _send(self, body, ctype="application/json", code=200):
        if isinstance(body, str):
            body = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _session(self):
        """The board session the caller presented, '' when none."""
        for part in (self.headers.get("Cookie") or "").split(";"):
            k, _, v = part.strip().partition("=")
            if k == "mice_board":
                return v
        return ""

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(u.query)
        p = u.path
        if p == "/api/status":
            return self._send(json.dumps(MODULE.status()))
        if p == "/api/cmd":
            c = (q.get("c") or [""])[0]
            head = c.split(" ", 1)[0].upper()
            # A query answers to anyone (heads that only report, and the
            # `?`-spelled ones like PIN?); anything that changes needs the
            # session, exactly as the real board's allowedCommand does.
            open_cmd = head in ("PING", "INFO", "HELP", "PEERS", "CFG",
                                "STATUS") or head.endswith("?")
            if (MODULE.gate_cmd and not MODULE.no_login_route and not open_cmd
                    and (not MODULE.session
                         or self._session() != MODULE.session)):
                return self._send("ERR log in first", "text/plain", 401)
            return self._send(MODULE.cmd(c), "text/plain; charset=utf-8")
        if p == "/api/files":
            return self._send(json.dumps(
                [{"n": n, "s": len(b)} for n, b in MODULE.files.items()]))
        if p == "/api/download":
            name = (q.get("path") or [""])[0].rsplit("/", 1)[-1]
            if name not in MODULE.files:
                return self._send("not found", "text/plain", 404)
            return self._send(MODULE.files[name], "text/yaml; charset=utf-8")
        if p == "/api/delete":
            name = (q.get("path") or [""])[0].rsplit("/", 1)[-1]
            MODULE.files.pop(name, None)
            return self._send("OK deleted " + name, "text/plain; charset=utf-8")
        if p == "/api/peers":
            return self._send("[]")
        if p == "/api/cam.stream":
            return self._stream()
        return self._send("no such endpoint " + p, "text/plain", 404)

    def _stream(self):
        """The live view, and it REFUSES A SECOND WATCHER like the board does.

        The board has one frame buffer and take() reclaims the frame already
        on loan, so two streams tear each other's pictures - it answers 503
        *someone is already watching*. A fake that let two in would make the
        hub's relay look unnecessary and prove nothing about it.
        """
        with MODULE.stream_lock:
            if MODULE.streaming:
                return self._send("someone is already watching — one live "
                                  "view at a time", "text/plain", 503)
            MODULE.streaming = True
            MODULE.streams_opened += 1
        try:
            self.send_response(200)
            self.send_header("Content-Type",
                             "multipart/x-mixed-replace; boundary=mice")
            self.end_headers()
            for i in range(MODULE.stream_frames):
                jpeg = b"\xff\xd8FAKEJPEG%04d" % i + b"\xff\xd9"
                self.wfile.write(b"\r\n--mice\r\nContent-Type: image/jpeg\r\n"
                                 b"Content-Length: " + str(len(jpeg)).encode() +
                                 b"\r\n\r\n" + jpeg)
                self.wfile.flush()
                MODULE.frames_sent += 1
                time.sleep(0.05)
        except Exception:                    # noqa: BLE001 - viewer went away
            pass
        finally:
            with MODULE.stream_lock:
                MODULE.streaming = False

    def do_POST(self):
        u = urllib.parse.urlparse(self.path)
        if u.path == "/api/upload":
            n = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(n) if n else b""
            # crude multipart: take the filename and the part after the blank line
            name = "upload.yaml"
            if b'filename="' in body:
                name = body.split(b'filename="', 1)[1].split(b'"', 1)[0].decode()
            if b"\r\n\r\n" in body:
                data = body.split(b"\r\n\r\n", 1)[1]
                data = data.rsplit(b"\r\n--", 1)[0]
            else:
                data = body
            MODULE.files[name] = data
            return self._send("OK wrote /moves/" + name, "text/plain; charset=utf-8")
        if u.path == "/api/login" and MODULE.no_login_route:
            # A BOARD TOO OLD TO KNOW WHAT A LOGIN IS. Set
            # fake_wifi.MODULE.no_login_route to reproduce camera id 77, which
            # answered 404 here and still took an image happily.
            return self._send("no such endpoint", "text/plain", 404)
        if u.path == "/api/login":
            n = int(self.headers.get("Content-Length") or 0)
            body = (self.rfile.read(n) if n else b"").decode(errors="replace")
            form = urllib.parse.parse_qs(body)
            user = (form.get("user") or [""])[0]
            pwd = (form.get("pass") or [""])[0]
            if (user, pwd) != (MODULE.user, MODULE.password):
                return self._send('{"ok":false,"error":"wrong login"}',
                                  "application/json", 401)
            MODULE.session = "qcboardsession"
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Set-Cookie",
                             "mice_board=%s; Path=/; HttpOnly; SameSite=Lax"
                             % MODULE.session)
            body = b'{"ok":true,"mustChange":false}'
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if u.path == "/api/ota":
            # A LOGIN IS REQUIRED BEFORE ANY BYTE IS WRITTEN, exactly as the
            # board does since A18-1 (WebPortal.cpp, in the body handler and
            # not the completion handler). The fake took an unauthenticated
            # image happily, which is why 3158 passing checks said nothing
            # while the hub's WiFi update was refused by every real board:
            # measured 2026-08-21, `401 ERR log in first` from board 42.
            got = self._session()
            if not MODULE.no_login_route and (
                    not MODULE.session or got != MODULE.session):
                return self._send("ERR log in first", "text/plain", 401)
            # New firmware over WiFi. The real board refuses while it is moving
            # or playing — a flash write stalls the servo loop, and a reboot
            # mid-show is worse than an update that waited — so the fake does
            # too, or the hub's handling of that refusal is never exercised.
            n = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(n) if n else b""
            q = urllib.parse.parse_qs(u.query)
            force = (q.get("force") or [""])[0] == "1"
            if MODULE.busy and not force:
                return self._send("ERR the module is moving — stop it first, "
                                  "or add force=1", "text/plain", 500)
            data = body.split(b"\r\n\r\n", 1)[1].rsplit(b"\r\n--", 1)[0] \
                if b"\r\n\r\n" in body else body
            MODULE.ota = data                 # what the check reads back
            return self._send("OK updated, rebooting into the new firmware",
                              "text/plain; charset=utf-8")
        return self._send("no such endpoint", "text/plain", 404)


_server = [None]


def start():
    """Run the fake module and return the "ip:port" the hub should be given."""
    if _server[0] is None:
        srv = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        _server[0] = srv
    return "127.0.0.1:%d" % _server[0].server_address[1]


def reset():
    MODULE.reset()
