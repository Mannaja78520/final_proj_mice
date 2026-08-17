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
            "types": ["lift", "nong", "blank"],
            "caps": ["pins", "sequences", "users", "rs485", "sd",
                     "joints", "servos", "calibration"],
            "seq": {"running": False, "file": ""},
            "wifi": {"mode": "sta", "wmode": "on", "ip": "127.0.0.1",
                     "ssid": "qc", "rssi": -50},
            "module": {"joints": self.joints, "seq": "", "speed": 120},
        }


MODULE = _Module()


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

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(u.query)
        p = u.path
        if p == "/api/status":
            return self._send(json.dumps(MODULE.status()))
        if p == "/api/cmd":
            return self._send(MODULE.cmd((q.get("c") or [""])[0]),
                              "text/plain; charset=utf-8")
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
        return self._send("no such endpoint " + p, "text/plain", 404)

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
        if u.path == "/api/ota":
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
