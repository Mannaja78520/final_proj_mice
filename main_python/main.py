#!/usr/bin/env python3
"""Mice control hub - THE main program of the installation.

  python main.py        -> opens http://127.0.0.1:8642/  (hub)

The hub is the first page: it FINDS every module by itself (scans the local
WiFi for module boards and lists the PC's USB serial ports) and links to:
  * each module's own website (lift, nong, ... any future type - dynamic,
    whatever type a module reports is shown),
  * Nong Studio (the humanoid pose/sequence editor) at /studio/, optionally
    pre-connected to a discovered nong module (live 3D simulation of the
    real robot via its monitor mode).

Nong Studio is a function of this program: its web app, projects, sequences
and models stay in code/nong/main_python_set_nong/ and are served from here.
Other devices on the same WiFi can open the hub too (phones, laptops).

Stdlib only - no pip installs. Command reference: code/firmware/COMMANDS.md
"""

import json
import re
import socket
import sys
import time
import threading
import urllib.parse
import urllib.request
import webbrowser
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutTimeout
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

# When frozen into an executable (PyInstaller), folders live next to the exe.
if getattr(sys, "frozen", False):
    HERE = Path(sys.executable).resolve().parent
else:
    HERE = Path(__file__).resolve().parent

HUB_WEB = HERE / "web"
WEBUI_H = HERE.parent / "firmware" / "src" / "web" / "WebUI.h"
STUDIO = HERE.parent / "nong" / "main_python_set_nong"
STUDIO_WEB = STUDIO / "web"
PROJECTS = STUDIO / "projects"
SEQUENCES = STUDIO / "sequences"
MODELS = STUDIO / "models"

HOST = "0.0.0.0"
PORT = 8642

MIME = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json",
    ".yaml": "text/yaml; charset=utf-8",
    ".stl": "application/octet-stream",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".bmp": "image/bmp",
    ".gif": "image/gif",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
}
UPLOAD_EXT = (".stl", ".png", ".jpg", ".jpeg", ".bmp", ".gif")
SAFE_NAME = re.compile(r"^[A-Za-z0-9._ -]{1,80}$")


def safe_name(name: str) -> str:
    name = name.strip()
    if not SAFE_NAME.match(name) or name.startswith("."):
        raise ValueError(f"bad name: {name!r}")
    return name


# The module website is the ESP32's own WebUI.h HTML (single source of truth).
# The hub serves that SAME html at /mod with a small transport shim injected,
# so /api/* calls route through the hub's /api/dev/* (WiFi or USB/RS485) — the
# site is then identical whichever way the module is reached. A PC pinout
# image is injected into the Hardware pins card (kept off the ESP32 to save
# flash).
_webui_cache = {"mtime": 0, "html": ""}
SHIM = """<script>
(function(){
 var P=new URLSearchParams(location.search), dev=P.get('dev'); if(!dev) return;
 var D=encodeURIComponent(dev), of=window.fetch.bind(window);
 window.fetch=function(u,opt){
  if(typeof u==='string' && u.indexOf('/api/')===0){
   if(u.indexOf('/api/upload')===0 && opt && opt.body instanceof FormData){
    var f=opt.body.get('file'), dir=(u.split('dir=')[1]||'/moves');
    return f.arrayBuffer().then(function(b){return of('/api/dev/upload?dev='+D+'&dir='+dir+'&name='+encodeURIComponent(f.name),{method:'POST',body:b});});
   }
   var q=u.slice(5), s=q.indexOf('?'), path=s<0?q:q.slice(0,s), rest=s<0?'':('&'+q.slice(s+1));
   return of('/api/dev/'+path+'?dev='+D+rest, opt);
  }
  return of(u,opt);
 };
 document.addEventListener('click',function(e){
  var a=e.target.closest&&e.target.closest('a[href*="/api/download"]');
  if(a){e.preventDefault();var p=a.href.split('path=')[1]||'';window.open('/api/dev/download?dev='+D+'&path='+p,'_blank');}
 },true);
 window.WebSocket=function(){
  var ws={readyState:1}; setTimeout(function(){ws.onopen&&ws.onopen();},50);
  var t=setInterval(function(){of('/api/dev/status?dev='+D).then(function(r){return r.text();}).then(function(x){ws.onmessage&&ws.onmessage({data:x});}).catch(function(){});},900);
  ws.send=function(c){of('/api/dev/cmd?dev='+D+'&c='+encodeURIComponent(c)).then(function(r){return r.text();}).then(function(x){ws.onmessage&&ws.onmessage({data:'> '+x});}).catch(function(){});};
  ws.close=function(){clearInterval(t);};
  return ws;
 };
 // PC pinout image into the Hardware pins card (served from the hub, not the ESP32)
 window.addEventListener('load',function(){setTimeout(function(){
  var pg=document.getElementById('pinGroups'); if(!pg)return;
  var d=document.createElement('div'); d.style.margin='6px 0';
  d.innerHTML='<a href="/pinout.svg" target="_blank" style="color:var(--acc)">\\uD83D\\uDCCD open ESP32 pinout reference</a>'+
   ' <img src="/pinout.svg" alt="ESP32 pinout" style="display:block;max-width:100%;margin-top:6px;border:1px solid var(--line);border-radius:8px">';
  pg.parentNode.insertBefore(d, pg);
 },600);});
})();
</script>"""


def module_ui_html():
    """WebUI.h HTML + shim (cached, reloads if the header changes)."""
    try:
        st = WEBUI_H.stat().st_mtime
        if st != _webui_cache["mtime"]:
            src = WEBUI_H.read_text(encoding="utf-8", errors="replace")
            m = re.search(r'R"rawliteral\((.*)\)rawliteral"', src, re.S)
            html = m.group(1) if m else "<h1>module UI not found</h1>"
            html = html.replace("<head>", "<head>" + SHIM, 1)
            _webui_cache.update(mtime=st, html=html)
        return _webui_cache["html"]
    except Exception as e:  # noqa: BLE001
        return "<h1>cannot load module UI: %s</h1>" % e


def lan_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return "127.0.0.1"


# ---------------------------------------------------------------- discovery
_scan_lock = threading.Lock()
_scan_cache = {"at": 0.0, "modules": []}


def probe_module(ip: str, timeout=0.6):
    """GET /api/status - returns module info dict or None."""
    try:
        with urllib.request.urlopen("http://%s/api/status" % ip, timeout=timeout) as r:
            st = json.loads(r.read().decode())
        if "type" in st and "id" in st:
            return {"ip": ip, "id": st.get("id"), "name": st.get("name", ip),
                    "type": st.get("type", "?"), "sd": st.get("sd", False)}
    except Exception:
        pass
    return None


def scan_modules(force=False):
    """Scan the local /24 subnet for module boards (parallel, ~3 s)."""
    with _scan_lock:
        if not force and time.time() - _scan_cache["at"] < 10:
            return _scan_cache["modules"]
        base = lan_ip().rsplit(".", 1)[0]
        found = []
        if base != "127.0.0":
            hosts = ["%s.%d" % (base, i) for i in range(1, 255)]
            with ThreadPoolExecutor(max_workers=64) as ex:
                for m in ex.map(probe_module, hosts):
                    if m:
                        found.append(m)
        found.sort(key=lambda m: m["id"])
        _scan_cache.update(at=time.time(), modules=found)
        return found


def serial_ports():
    """USB serial ports on this PC, WITH their device type — so Bluetooth
    phantom ports (which hang for ~40 s when opened) can be skipped up
    front instead of probed. Returns [{"port","desc","bt"}]."""
    out = []
    try:
        from serial.tools import list_ports
        for p in sorted(list_ports.comports(), key=lambda x: x.device):
            desc = (p.description or "") + " " + (p.hwid or "")
            bt = "bluetooth" in desc.lower() or "BTHENUM" in desc
            out.append({"port": p.device, "desc": p.description or "", "bt": bt})
        return out
    except ImportError:
        pass
    if sys.platform == "win32":
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                 r"HARDWARE\DEVICEMAP\SERIALCOMM")
            i = 0
            while True:
                try:
                    name, val, _ = winreg.EnumValue(key, i)
                    out.append({"port": str(val), "desc": str(name),
                                "bt": "BTHENUM" in str(name)})
                    i += 1
                except OSError:
                    break
        except OSError:
            pass
    else:
        import glob
        for p in sorted(glob.glob("/dev/ttyUSB*") + glob.glob("/dev/ttyACM*")):
            out.append({"port": p, "desc": "", "bt": False})
    return out


# ---------------- USB serial manager: talk to modules over the cable -----
# The hub keeps a port open while it is being used (fast consecutive
# commands) and auto-releases it after ~10 s idle so the browser's Web
# Serial (Nong Studio) or a re-probe can take it again.
_usb_mgr_lock = threading.Lock()
_usb_open = {}  # port -> {"ser": Serial, "lock": Lock, "last": time}


def _usb_get(port):
    # the global lock only guards the dict — the (possibly slow) open()
    # happens under the PER-PORT lock, so one stuck Bluetooth port can
    # never block the other ports
    import serial
    with _usb_mgr_lock:
        ent = _usb_open.get(port)
        if ent is None:
            ent = {"ser": None, "lock": threading.Lock(), "last": time.time()}
            _usb_open[port] = ent
    with ent["lock"]:
        if ent["ser"] is not None and ent["ser"].is_open:
            ent["last"] = time.time()
            return ent
        ser = serial.Serial()
        ser.port = port
        ser.baudrate = 115200
        ser.timeout = 0.15
        ser.dtr = False   # never pulse the ESP32 reset/boot straps
        ser.rts = False
        ser.open()
        ent["ser"] = ser
        ent["last"] = time.time()
        return ent


def usb_close(port=None):
    with _usb_mgr_lock:
        ports = [port] if port else list(_usb_open)
        ents = [(p, _usb_open.pop(p)) for p in ports if p in _usb_open]
    for _, ent in ents:
        try:
            if ent["ser"] is not None:
                ent["ser"].close()
        except Exception:
            pass


def _usb_reaper():
    while True:
        time.sleep(3)
        with _usb_mgr_lock:
            idle = [p for p, ent in _usb_open.items()
                    if time.time() - ent["last"] > 10]
        for p in idle:
            usb_close(p)


# A firmware log line is a bracket tag: "[wifi]", "[sd]", "[  1234][I]" ... —
# only letters/digits/spaces inside the brackets. A JSON reply that starts with
# "[" is always "[{" / "[\"" / "[[" / "[<num>," so it never matches this.
_LOG_LINE = re.compile(r"^\[[\w ]*\]")


def usb_cmd(port, cmd, bus_id=0, wait=2.0):
    """One command line over USB; returns the reply line (RS485-framed when
    bus_id is set, so modules BEHIND this port are controllable too)."""
    ent = _usb_get(port)
    with ent["lock"]:
        ent["last"] = time.time()
        ser = ent["ser"]
        ser.reset_input_buffer()
        line = ("#%d %s" % (bus_id, cmd)) if bus_id else cmd
        ser.write((line + "\n").encode())
        want = ("@%d " % bus_id) if bus_id else None
        buf, end = b"", time.time() + wait
        while time.time() < end:
            chunk = ser.read(256)
            if not chunk:
                continue
            buf += chunk
            while b"\n" in buf:
                ln, buf = buf.split(b"\n", 1)
                t = ln.decode(errors="replace").strip()
                # skip blank lines and firmware LOG lines only. A log line is a
                # bracket TAG like "[wifi] ...", "[sd] ...", "[  1234][I]...".
                # A JSON ARRAY reply (PIN VALID -> "[{...}]") also starts with
                # "[" but must NOT be skipped — that was the bug that made pin
                # config work over WiFi but come back empty over USB. Treat as a
                # log line only when the "[...]" holds a plain tag (letters,
                # digits, spaces), never "[{" / "[\"" / "[[" which start JSON.
                if not t:
                    continue
                if _LOG_LINE.match(t):
                    continue
                if want:
                    if t.startswith(want):
                        return t[len(want):]
                elif not t.startswith(("#", "@", "->")):
                    return t
        raise TimeoutError("no reply from " + port +
                           ((" (bus id %d)" % bus_id) if bus_id else ""))


# ---------------- unified device access (WiFi or USB/RS485, one API) ------
# A "dev" string names a module and its transport, so the SAME web UI works
# over any link: "wifi:<ip>"  or  "usb:<port>"  or  "usb:<port>:<busid>".
# The hub dispatches each call to HTTP (WiFi) or serial (USB/RS485). This is
# what lets the module website be identical whichever way it is reached.
def parse_dev(dev):
    if dev.startswith("wifi:"):
        return ("wifi", dev[5:], 0)
    if dev.startswith("usb:"):
        rest = dev[4:].split(":")
        return ("usb", rest[0], int(rest[1]) if len(rest) > 1 and rest[1] else 0)
    raise ValueError("bad dev (use wifi:<ip> or usb:<port>[:<id>])")


def dev_cmd(dev, c):
    kind, addr, bus = parse_dev(dev)
    if kind == "wifi":
        return Handler.robot_get(addr, "/api/cmd?c=" + urllib.parse.quote(c)).decode(errors="replace")
    return usb_cmd(addr, c, bus)


def dev_status(dev):
    kind, addr, bus = parse_dev(dev)
    if kind == "wifi":
        return Handler.robot_get(addr, "/api/status")
    return usb_cmd(addr, "INFO", bus).encode()


def dev_files(dev, d):
    kind, addr, bus = parse_dev(dev)
    if kind == "wifi":
        return Handler.robot_get(addr, "/api/files?dir=" + urllib.parse.quote(d))
    return usb_cmd(addr, "FILES " + d, bus).encode()


def dev_download(dev, path):
    kind, addr, bus = parse_dev(dev)
    if kind == "wifi":
        return Handler.robot_get(addr, "/api/download?path=" + urllib.parse.quote(path))
    # USB: FREAD loop (base64 chunks)
    import base64
    name = path.rsplit("/", 1)[-1]
    out, off = b"", 0
    while True:
        r = usb_cmd(addr, "FREAD %s %d 120" % (name, off), bus)
        if r == "EOF" or r.startswith("ERR"):
            break
        chunk = base64.b64decode(r)
        out += chunk
        off += len(chunk)
        if len(chunk) < 120:
            break
    return out


def dev_delete(dev, path):
    kind, addr, bus = parse_dev(dev)
    if kind == "wifi":
        return Handler.robot_get(addr, "/api/delete?path=" + urllib.parse.quote(path)).decode(errors="replace")
    name = path.rsplit("/", 1)[-1]
    return usb_cmd(addr, "FDEL " + name, bus)


def dev_upload(dev, dirp, name, data: bytes):
    kind, addr, bus = parse_dev(dev)
    if kind == "wifi":
        boundary = "----micehub%d" % int(time.time())
        body = (
            ("--%s\r\nContent-Disposition: form-data; name=\"file\"; "
             "filename=\"%s\"\r\nContent-Type: application/octet-stream\r\n\r\n" % (boundary, name)).encode()
            + data + ("\r\n--%s--\r\n" % boundary).encode())
        req = urllib.request.Request(
            "http://%s/api/upload?dir=%s" % (addr, urllib.parse.quote(dirp)), data=body,
            method="POST", headers={"Content-Type": "multipart/form-data; boundary=" + boundary})
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode(errors="replace")
    # USB: FBEGIN / FDATA (base64) / FEND
    import base64
    path = (dirp.rstrip("/") + "/" + name) if dirp else name
    r = usb_cmd(addr, "FBEGIN " + path, bus)
    if not r.startswith("OK"):
        return r
    for i in range(0, len(data), 120):
        r = usb_cmd(addr, "FDATA " + base64.b64encode(data[i:i + 120]).decode(), bus)
        if not r.startswith("OK"):
            return r
    return usb_cmd(addr, "FEND", bus)


# ---------------- USB / RS485 probing (which module is on which port?) ----
# Opens each port briefly, asks INFO (a module plugged in directly answers
# with its identity + WiFi ip), then broadcasts "#* PING" so every module on
# the RS485 bus behind that port answers too — works both through a module
# (it bridges '#' lines onto the bus) and through a bare USB-RS485 dongle.
def _read_lines(ser, seconds):
    lines, buf, end = [], b"", time.time() + seconds
    while time.time() < end:
        chunk = ser.read(256)
        if not chunk:
            continue
        buf += chunk
        while b"\n" in buf:
            ln, buf = buf.split(b"\n", 1)
            t = ln.decode(errors="replace").strip()
            if t and not t.startswith("["):
                lines.append(t)
    return lines


def _wifi_of(st):
    w = st.get("wifi") or {}
    return {"ip": w.get("ip", ""), "wifi_mode": w.get("mode", "")}


def probe_usb_port(port):
    """Identify the module on a COM port + every RS485 module behind it."""
    out = {"port": port, "module": None, "rs485": [], "error": ""}
    try:
        import serial  # noqa: F401
    except ImportError:
        out["error"] = "pyserial not installed (pip install pyserial)"
        return out
    try:
        ent = _usb_get(port)  # shared manager: no conflict with the proxy
    except Exception as e:  # busy (Studio connected?) or not a module
        out["error"] = str(e)
        return out
    with ent["lock"]:
        ent["last"] = time.time()
        ser = ent["ser"]
        try:
            ser.reset_input_buffer()
            # 1) directly connected module?
            ser.write(b"INFO\n")
            for ln in _read_lines(ser, 0.6):
                if ln.startswith("{"):
                    try:
                        st = json.loads(ln)
                        out["module"] = {"id": st.get("id"), "name": st.get("name"),
                                         "type": st.get("type"), **_wifi_of(st)}
                        break
                    except ValueError:
                        pass
            # 2) census of the RS485 bus behind this port
            ser.reset_input_buffer()
            ser.write(b"#* PING\n")
            seen = {}
            for ln in _read_lines(ser, 0.8):
                m = re.match(r"^@(\d+)\s+PONG\s+(\d+)\s+(.+)\s+(\S+)$", ln)
                if m:
                    seen[int(m.group(1))] = {"id": int(m.group(1)), "name": m.group(3),
                                             "type": m.group(4), "ip": "", "wifi_mode": ""}
            # ask each bus module for its INFO to learn its WiFi ip (for links)
            for mid in list(seen)[:6]:
                ser.reset_input_buffer()
                ser.write(("#%d INFO\n" % mid).encode())
                for ln in _read_lines(ser, 0.6):
                    if ln.startswith("@%d {" % mid):
                        try:
                            seen[mid].update(_wifi_of(json.loads(ln.split(" ", 1)[1])))
                        except ValueError:
                            pass
                        break
            mod_id = out["module"]["id"] if out["module"] else None
            out["rs485"] = [v for k, v in sorted(seen.items()) if k != mod_id]
        except Exception as e:  # noqa: BLE001
            out["error"] = str(e)
            if "hEvent" in out["error"]:  # pyserial's way of saying "not usable"
                out["error"] = "port not usable (Bluetooth or half-open) — skipped"
            usb_close(port)  # reset a wedged port for the next attempt
    return out


_usbscan_lock = threading.Lock()
_usbscan_cache = {"at": 0.0, "usb": []}


def probe_usb_one(port, timeout=8):
    """Probe a single port with a watchdog (used by the streaming hub UI:
    each port renders the moment IT answers — nobody waits for the slow ones)."""
    ex = ThreadPoolExecutor(max_workers=1)
    f = ex.submit(probe_usb_port, port)
    try:
        return f.result(timeout=timeout)
    except FutTimeout:
        return {"port": port, "module": None, "rs485": [],
                "error": "no answer within %d s — skipped" % timeout}
    finally:
        ex.shutdown(wait=False)


def probe_usb_all(force=False):
    # all NON-Bluetooth ports in parallel (Bluetooth phantom ports are known
    # from the device type and never opened) with a shared watchdog
    with _usbscan_lock:
        if not force and time.time() - _usbscan_cache["at"] < 8:
            return _usbscan_cache["usb"]
        infos = serial_ports()
        out = []
        real = [i["port"] for i in infos if not i["bt"]]
        for i in infos:
            if i["bt"]:
                out.append({"port": i["port"], "module": None, "rs485": [],
                            "error": "Bluetooth port — skipped", "bt": True})
        if real:
            ex = ThreadPoolExecutor(max_workers=len(real))
            futs = [(p, ex.submit(probe_usb_port, p)) for p in real]
            deadline = time.time() + 7
            for p, f in futs:
                try:
                    out.append(f.result(timeout=max(0.1, deadline - time.time())))
                except FutTimeout:
                    out.append({"port": p, "module": None, "rs485": [],
                                "error": "no answer within 7 s — skipped"})
            ex.shutdown(wait=False)
        out.sort(key=lambda u: u["port"])
        _usbscan_cache.update(at=time.time(), usb=out)
        return out


# ---------------------------------------------------------------- handler
class Handler(BaseHTTPRequestHandler):
    def send_bytes(self, data: bytes, ctype="application/json", code=200):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def send_json(self, obj, code=200):
        self.send_bytes(json.dumps(obj).encode(), code=code)

    def send_err(self, msg, code=400):
        self.send_json({"ok": False, "error": str(msg)}, code=code)

    def body(self) -> bytes:
        n = int(self.headers.get("Content-Length") or 0)
        return self.rfile.read(n) if n else b""

    def log_message(self, fmt, *args):
        if "/api/robot" in (args[0] if args else "") or "/api/scan" in (args[0] if args else ""):
            return
        sys.stderr.write("[web] " + fmt % args + "\n")

    def do_GET(self):
        try:
            self.route("GET")
        except Exception as e:  # noqa: BLE001
            self.send_err(e, 500)

    def do_POST(self):
        try:
            self.route("POST")
        except Exception as e:  # noqa: BLE001
            self.send_err(e, 500)

    def route(self, method: str):
        url = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(url.query)
        path = url.path

        if path.startswith("/api/"):
            return self.api(method, path, q)

        if method != "GET":
            return self.send_err("POST only on /api/*", 405)

        # ---- static routing: hub at /, studio app at /studio/ ----
        if path == "/" or path == "/hub":
            f = HUB_WEB / "hub.html"
            return self.send_bytes(f.read_bytes(), MIME[".html"])
        if path == "/mod" or path == "/mod.html":
            # the module's OWN website (WebUI.h) served with a transport shim —
            # identical over WiFi/USB/RS485 (?dev=wifi:<ip> | usb:<port>[:<id>])
            return self.send_bytes(module_ui_html().encode(), MIME[".html"])
        if path == "/module.html":  # legacy USB control page (kept as fallback)
            return self.send_bytes((HUB_WEB / "module.html").read_bytes(), MIME[".html"])
        if path == "/rgb.html":     # RGB modes page (WiFi or USB target)
            return self.send_bytes((HUB_WEB / "rgb.html").read_bytes(), MIME[".html"])
        if path == "/pinout.svg":   # ESP32 pinout reference (served from the PC)
            return self.send_bytes((HUB_WEB / "pinout.svg").read_bytes(), MIME[".svg"])
        if path == "/studio" or path == "/studio/":
            return self.send_bytes((STUDIO_WEB / "index.html").read_bytes(), MIME[".html"])
        if path.startswith("/studio/"):
            base, rel = STUDIO_WEB, path[len("/studio/"):]
        elif path.startswith("/models/"):
            base, rel = MODELS, path[len("/models/"):]
        elif path.startswith("/hubweb/"):
            base, rel = HUB_WEB, path[len("/hubweb/"):]
        else:
            # studio's absolute asset paths (/app.js, /style.css, /vendor/..)
            base, rel = STUDIO_WEB, path.lstrip("/")
        f = (base / rel).resolve()
        if base not in f.parents and f != base:
            return self.send_err("forbidden", 403)
        if not f.is_file():
            return self.send_err("not found: " + path, 404)
        self.send_bytes(f.read_bytes(), MIME.get(f.suffix.lower(), "application/octet-stream"))

    # ------------------------------------------------------------- API
    def api(self, method: str, path: str, q):
        # ---- unified device API: same for WiFi and USB/RS485 (dev=...) ----
        # These back the one module website served at /mod?dev=... so it is
        # identical over every transport.
        if path.startswith("/api/dev/"):
            dev = (q.get("dev") or [""])[0]
            what = path[len("/api/dev/"):]
            try:
                if what == "cmd":
                    return self.send_bytes(dev_cmd(dev, (q.get("c") or [""])[0]).encode(),
                                           "text/plain; charset=utf-8")
                if what == "status":
                    return self.send_bytes(dev_status(dev), "application/json")
                if what == "files":
                    return self.send_bytes(dev_files(dev, (q.get("dir") or ["/moves"])[0]),
                                           "application/json")
                if what == "peers":
                    kind = parse_dev(dev)[0]
                    if kind == "wifi":
                        return self.send_bytes(Handler.robot_get(parse_dev(dev)[1], "/api/peers"),
                                               "application/json")
                    return self.send_json([])  # over USB, peer list isn't shown
                if what == "download":
                    return self.send_bytes(dev_download(dev, (q.get("path") or [""])[0]),
                                           "application/octet-stream")
                if what == "delete":
                    return self.send_bytes(dev_delete(dev, (q.get("path") or [""])[0]).encode(),
                                           "text/plain; charset=utf-8")
                if what == "upload" and method == "POST":
                    return self.send_bytes(dev_upload(dev, (q.get("dir") or ["/moves"])[0],
                                                      safe_name((q.get("name") or ["f"])[0]),
                                                      self.body()).encode(),
                                           "text/plain; charset=utf-8")
                return self.send_err("unknown dev endpoint " + what, 404)
            except Exception as e:  # noqa: BLE001
                return self.send_err(e, 502)

        # ---- hub: discovery ----
        if path == "/api/scan":
            force = (q.get("force") or ["0"])[0] == "1"
            return self.send_json({"ok": True, "lan": lan_ip(),
                                   "modules": scan_modules(force),
                                   "ports": serial_ports()})

        if path == "/api/ports":
            # just the typed port list (no WiFi scan, no port opening) — the
            # streaming USB probe uses this, then probes each port on its own
            return self.send_json({"ok": True, "ports": serial_ports()})

        if path == "/api/scanusb":
            # ?port=COMx probes ONE port (streaming UI: results render as
            # each port answers); no port = all non-Bluetooth ports at once
            port = (q.get("port") or [""])[0]
            if port:
                return self.send_json({"ok": True, "usb": [probe_usb_one(port)]})
            force = (q.get("force") or ["0"])[0] == "1"
            return self.send_json({"ok": True, "usb": probe_usb_all(force)})

        # ---- USB command proxy: full module control over the cable, no
        # WiFi needed (used by /module.html). Optional id = RS485 address of
        # a module BEHIND this port.
        if path == "/api/usb/cmd":
            port = (q.get("port") or [""])[0]
            c = (q.get("c") or [""])[0]
            bus = int((q.get("id") or ["0"])[0] or 0)
            if not port or not c:
                return self.send_err("need port and c")
            try:
                return self.send_bytes(usb_cmd(port, c, bus).encode(),
                                       "text/plain; charset=utf-8")
            except Exception as e:  # noqa: BLE001
                return self.send_err(e, 502)

        if path == "/api/usb/close":
            usb_close((q.get("port") or [None])[0])
            return self.send_json({"ok": True})

        # ---- studio: local storage ----
        if path == "/api/list":
            kind = (q.get("kind") or ["projects"])[0]
            folder = {"projects": PROJECTS, "sequences": SEQUENCES, "models": MODELS}.get(kind)
            if folder is None:
                return self.send_err("kind must be projects|sequences|models")
            files = sorted(p.name for p in folder.iterdir() if p.is_file())
            return self.send_json({"ok": True, "files": files})

        if path == "/api/load":
            name = safe_name((q.get("name") or [""])[0])
            f = PROJECTS / name
            if not f.is_file():
                return self.send_err("no project " + name, 404)
            return self.send_bytes(f.read_bytes())

        if path == "/api/loadseq":
            name = safe_name((q.get("name") or [""])[0])
            f = SEQUENCES / name
            if not f.is_file():
                return self.send_err("no sequence " + name, 404)
            return self.send_bytes(f.read_bytes(), "text/yaml; charset=utf-8")

        if path == "/api/save" and method == "POST":
            data = json.loads(self.body().decode())
            name = safe_name(data["name"])
            if not name.endswith(".json"):
                name += ".json"
            (PROJECTS / name).write_text(
                json.dumps(data["project"], indent=1), encoding="utf-8")
            return self.send_json({"ok": True, "file": name})

        if path == "/api/model/upload" and method == "POST":
            name = safe_name((q.get("name") or [""])[0])
            if not name.lower().endswith(UPLOAD_EXT):
                return self.send_err("allowed: " + " ".join(UPLOAD_EXT))
            (MODELS / name).write_bytes(self.body())
            return self.send_json({"ok": True, "file": name})

        if path == "/api/export" and method == "POST":
            data = json.loads(self.body().decode())
            name = safe_name(data["name"])
            if not name.endswith(".yaml"):
                name += ".yaml"
            (SEQUENCES / name).write_text(data["yaml"], encoding="utf-8", newline="\n")
            return self.send_json({"ok": True, "file": name,
                                   "path": str((SEQUENCES / name))})

        # ---- robot proxy (dodges CORS) ----
        if path == "/api/robot/cmd":
            ip = (q.get("ip") or [""])[0]
            c = (q.get("c") or [""])[0]
            if not ip or not c:
                return self.send_err("need ip and c")
            r = self.robot_get(ip, "/api/cmd?c=" + urllib.parse.quote(c))
            return self.send_bytes(r, "text/plain; charset=utf-8")

        if path == "/api/robot/status":
            ip = (q.get("ip") or [""])[0]
            return self.send_bytes(self.robot_get(ip, "/api/status"))

        if path == "/api/robot/files":
            ip = (q.get("ip") or [""])[0]
            d = (q.get("dir") or ["/moves"])[0]
            return self.send_bytes(self.robot_get(ip, "/api/files?dir=" + urllib.parse.quote(d)))

        if path == "/api/robot/download":
            ip = (q.get("ip") or [""])[0]
            p = (q.get("path") or [""])[0]
            return self.send_bytes(
                self.robot_get(ip, "/api/download?path=" + urllib.parse.quote(p)),
                "text/yaml; charset=utf-8")

        if path == "/api/robot/delete":
            ip = (q.get("ip") or [""])[0]
            p = (q.get("path") or [""])[0]
            return self.send_bytes(
                self.robot_get(ip, "/api/delete?path=" + urllib.parse.quote(p)),
                "text/plain; charset=utf-8")

        if path == "/api/robot/upload" and method == "POST":
            data = json.loads(self.body().decode())
            ip = data["ip"]
            name = safe_name(data["name"])
            payload = data["yaml"].encode()
            boundary = "----micehub%d" % int(time.time())
            body = (
                ("--%s\r\nContent-Disposition: form-data; name=\"file\"; "
                 "filename=\"%s\"\r\nContent-Type: text/yaml\r\n\r\n" % (boundary, name)).encode()
                + payload + ("\r\n--%s--\r\n" % boundary).encode())
            req = urllib.request.Request(
                "http://%s/api/upload?dir=/moves" % ip, data=body, method="POST",
                headers={"Content-Type": "multipart/form-data; boundary=" + boundary})
            with urllib.request.urlopen(req, timeout=10) as resp:
                return self.send_json({"ok": resp.status == 200,
                                       "reply": resp.read().decode(errors="replace")})

        return self.send_err("unknown endpoint " + path, 404)

    @staticmethod
    def robot_get(ip: str, path: str) -> bytes:
        if not re.match(r"^[A-Za-z0-9._-]+(:\d+)?$", ip):
            raise ValueError("bad module address")
        with urllib.request.urlopen("http://%s%s" % (ip, path), timeout=6) as r:
            return r.read()


def main():
    for d in (PROJECTS, SEQUENCES, MODELS):
        d.mkdir(parents=True, exist_ok=True)
    srv = ThreadingHTTPServer((HOST, PORT), Handler)
    local = "http://127.0.0.1:%d/" % PORT
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except Exception:
        pass
    print("Mice hub running:")
    print("  this PC       ->", local)
    print("  same WiFi     -> http://%s:%d/   (phones / other laptops)" % (lan_ip(), PORT))
    print("The hub finds all modules by itself; Nong Studio is at /studio/.")
    print("Ctrl+C to stop.")
    threading.Timer(0.6, lambda: webbrowser.open(local)).start()
    # warm the module scan so the hub page fills instantly
    threading.Thread(target=scan_modules, daemon=True).start()
    threading.Thread(target=_usb_reaper, daemon=True).start()  # idle port release
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nbye")


if __name__ == "__main__":
    main()
