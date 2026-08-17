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

# Registries: data files that describe things, so adding a web app / servo /
# command is one edit in one place. See code/tools/registry.py.
sys.path.insert(0, str((HERE.parent / "tools")))
try:
    import registry
except Exception as _e:            # a broken registry must not stop the hub
    registry = None
    print("[hub] registries unavailable:", _e)

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


# Studio's settings, shared from this PC so another one can pull them over the
# network. Sits with the other user data, not in the code.
SETTINGS_FILE = STUDIO / "settings_shared.json"

_hub_lock = threading.Lock()
_hub_cache = {"at": 0.0, "hubs": []}


def probe_hub(ip, timeout=0.7):
    """Is another mice hub at this address, and has it shared settings?"""
    try:
        with urllib.request.urlopen("http://%s:%d/api/settings" % (ip, PORT),
                                    timeout=timeout) as r:
            d = json.loads(r.read().decode())
    except Exception:
        return None
    if d.get("ok") is False:
        return {"ip": ip, "name": "", "savedAt": "", "has": False}
    return {"ip": ip, "name": d.get("savedBy", ""),
            "savedAt": d.get("savedAt", ""), "has": True}


def scan_hubs(force=False):
    """Other PCs running the hub on this subnet. Same sweep the module scan
    uses, on the hub's own port — so moving a rig between two laptops needs no
    IP typed in."""
    with _hub_lock:
        if not force and time.time() - _hub_cache["at"] < 20:
            return _hub_cache["hubs"]
        base = lan_ip().rsplit(".", 1)[0]
        found = []
        if base != "127.0.0":
            me = lan_ip()
            hosts = ["%s.%d" % (base, i) for i in range(1, 255) if "%s.%d" % (base, i) != me]
            with ThreadPoolExecutor(max_workers=96) as ex:
                for h in ex.map(probe_hub, hosts):
                    if h:
                        found.append(h)
        _hub_cache.update(at=time.time(), hubs=found)
        return found


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
                    "type": st.get("type", "?"), "sd": st.get("sd", False),
                    # which installation it belongs to — the Network tab shows
                    # this, and it is the whole point of the linking screen
                    "group": st.get("group", "")}
    except Exception:
        pass
    return None


def _probe_patiently(ip):
    """Same probe, but give a module that is KNOWN to exist real time to answer."""
    return probe_module(ip, timeout=2.0)


def _ips_from_usb():
    """WiFi addresses of modules we have identified over a CABLE.

    The subnet sweep only covers the PC's own /24, so a module on a different
    subnet is invisible to it — even when it is perfectly reachable. That is
    not a corner case: seen on a dorm network with the PC on 10.94.163.x and
    both modules on 192.168.100.x, routed and answering fine, while the hub
    listed nothing at all.

    But the hub is already plugged into those modules, and INFO carries their
    IP. So a module we can SEE on USB tells us where to find it on WiFi, and
    the sweep never has to guess which subnet to look at.
    """
    out = []
    for ident in list(_usb_ident.values()):
        ip = ((ident or {}).get("module") or {}).get("ip") or ""
        if ip and ip not in ("0.0.0.0", "192.168.4.1"):   # AP self-address is not routable to us
            out.append(ip)
    return out


def scan_modules(force=False):
    """Scan the local /24 subnet for module boards (parallel, ~3 s).

    Two passes, because one is not honest. A module that shares its WiFi runs
    AP_STA on a single radio: it serves the show network and its own access
    point by time-slicing, so it sometimes answers a touch late. Measured on
    the bench — the lift answered a 0.6 s probe 7 times in 8, and the hub
    consequently LOST it on 2 scans out of 3 while it sat there perfectly
    online and reachable.

    So: sweep the subnet quickly to discover anything new, then go back and
    ask the addresses we have seen before, patiently. That second pass is a
    handful of hosts, costs nothing when they answer, and means a module that
    was found once does not silently vanish from the hub.

    The second pass also covers addresses the sweep can never reach: it only
    walks the PC's own /24, so a module on a different subnet is invisible to
    it however reachable it is. Modules identified over a CABLE report their
    own IP, so plugging one in is enough to find it on WiFi afterwards.
    """
    with _scan_lock:
        if not force and time.time() - _scan_cache["at"] < 10:
            return _scan_cache["modules"]
        base = lan_ip().rsplit(".", 1)[0]
        found = []
        if base != "127.0.0":
            hosts = ["%s.%d" % (base, i) for i in range(1, 255)]
            with ThreadPoolExecutor(max_workers=96) as ex:
                for m in ex.map(probe_module, hosts):
                    if m:
                        found.append(m)

        # Second pass: addresses we already know about. Deliberately NOT
        # limited to the swept subnet — a module can be perfectly reachable
        # from another one (routed dorm/campus networks do this), and the
        # whole point is to stop losing modules that are actually there.
        seen = {m["ip"] for m in found}
        known = [m["ip"] for m in _scan_cache["modules"]] + _ips_from_usb()
        missing = [ip for ip in dict.fromkeys(known) if ip and ip not in seen]
        if missing:
            with ThreadPoolExecutor(max_workers=8) as ex:
                for m in ex.map(_probe_patiently, missing):
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
# A COM port can only be opened by ONE program at a time. So the hub is the
# ONE owner of every cable: it opens the port once and SHARES it between all
# of its clients — the module website (/mod?dev=usb:...), Nong Studio (its
# USB link goes through /api/usb/cmd) and the hub's own port probe. Each
# command runs under that port's lock, so the module page and Studio can be
# open on the same cable at the same time instead of one of them getting
# "serial port already in use".
# The port is auto-released after ~10 s with no traffic, so an external tool
# (Arduino IDE, esptool, Studio's optional direct Web Serial mode) can still
# take it when the hub is not talking.
_usb_mgr_lock = threading.Lock()
_usb_open = {}  # port -> {"ser": Serial, "lock": Lock, "last": time}
_usb_touch = {}  # port -> last time a CLIENT (not the probe) used the port
_usb_ident = {}  # port -> last successful probe result (identity cache)
USB_IDLE_CLOSE = 10   # s with no traffic before the port is released
USB_INUSE = 15        # s a port counts as "a client is working on it"


def usb_busy_hint(port, err):
    """Turn pyserial's open() error into something the user can act on."""
    t = str(err)
    if "PermissionError" in t or "Access is denied" in t or "denied" in t.lower() \
            or "Device or resource busy" in t or "errno 16" in t.lower():
        return ("%s is held by another program — the hub shares the cable "
                "between its own pages, but not with outside apps. Close the "
                "Arduino/PlatformIO serial monitor, esptool, or a Nong Studio "
                "tab left in 'USB direct (Web Serial)' mode, then try again."
                % port)
    return t


def _usb_get(port):
    # A flash owns the cable outright: esptool cannot share a port, and the
    # hub re-opening it mid-write is exactly how an upload dies half way.
    if port in _flash_ports:
        raise OSError("%s is being flashed right now — the cable belongs to "
                      "esptool until it finishes" % port)
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
        try:
            ser.open()
        except Exception as e:  # noqa: BLE001
            raise OSError(usb_busy_hint(port, e))
        ent["ser"] = ser
        ent["last"] = time.time()
        return ent


def usb_close(port=None):
    with _usb_mgr_lock:
        ports = [port] if port else list(_usb_open)
        ents = [(p, _usb_open.pop(p)) for p in ports if p in _usb_open]
    for _, ent in ents:
        # take the port's own lock first: never close the handle out from
        # under a command that is mid read/write on it
        got = ent["lock"].acquire(timeout=3)
        try:
            if ent["ser"] is not None:
                ent["ser"].close()
        except Exception:
            pass
        finally:
            if got:
                ent["lock"].release()


def usb_in_use(port):
    """True while a client (module page / Studio) is actively using the cable."""
    return time.time() - _usb_touch.get(port, 0) < USB_INUSE


def _usb_reaper():
    while True:
        time.sleep(3)
        with _usb_mgr_lock:
            idle = [p for p, ent in _usb_open.items()
                    if time.time() - ent["last"] > USB_IDLE_CLOSE]
        for p in idle:
            usb_close(p)


# A firmware log line is a bracket tag: "[wifi]", "[sd]", "[  1234][I]" ... —
# only letters/digits/spaces inside the brackets. A JSON reply that starts with
# "[" is always "[{" / "[\"" / "[[" / "[<num>," so it never matches this.
_LOG_LINE = re.compile(r"^\[[\w ]*\]")


def _drain_to_line_boundary(ser):
    """Throw away whatever the board said before this command.

    This used to also SPIN for up to 80 ms waiting for a half-written log line
    to finish, because an orphaned tail could be mistaken for the reply. That
    cost is paid on every single command, and it is worst exactly when the
    board is chatty — which is now normal, since every module hosts an access
    point and logs about it. On live pose streaming (~30 commands a second)
    it was most of the latency, and the arm visibly lagged the sliders.

    The wait is no longer needed: the firmware writes every reply as
    "
<reply>
", and the reader below identifies the reply by that leading
    blank line. An orphan tail has no blank line in front of it, so it is
    already discarded on its own merits. Clearing the buffer is enough.
    """
    ser.reset_input_buffer()


def usb_cmd(port, cmd, bus_id=0, wait=2.0):
    """One command line over USB; returns the reply line (RS485-framed when
    bus_id is set, so modules BEHIND this port are controllable too).

    Safe to call from several clients at once (module website + Nong Studio +
    probe): the per-port lock makes each command atomic on the wire, so the
    replies can never interleave."""
    try:
        return _usb_cmd_once(port, cmd, bus_id, wait)
    except TimeoutError:
        raise                  # the module just did not answer — handle is fine
    except OSError:
        # STALE HANDLE. The board was unplugged, reset or re-enumerated while
        # the hub had the port open. pyserial still reports is_open, so the
        # handle never heals itself — Windows fails every write with
        # "The device does not recognize the command" — and the idle reaper
        # never drops it either, because a page polling every ~900 ms keeps the
        # port looking busy. Throw the handle away and open a fresh one, which
        # is all that replugging the cable actually needs.
        usb_close(port)
        try:
            return _usb_cmd_once(port, cmd, bus_id, wait)
        except Exception:
            _usb_ident.pop(port, None)   # cached identity is no longer trusted
            raise


# Commands that change WHO a module is. After one of these the cached identity
# is a lie, and the cache is what the hub shows while a cable is busy — so the
# Network tab happily displayed a module's OLD group straight after linking it,
# which is precisely the screen where stale information misleads you.
_IDENTITY_CHANGING = ("GROUP", "SET NAME", "SET ID", "SET TYPE", "SET WIFI")


def _usb_cmd_once(port, cmd, bus_id=0, wait=2.0):
    _usb_touch[port] = time.time()   # a client is working on this cable
    up = cmd.strip().upper()
    if any(up.startswith(k) for k in _IDENTITY_CHANGING):
        _usb_ident.pop(port, None)   # re-probe rather than repeat a stale answer
    ent = _usb_get(port)
    with ent["lock"]:
        ent["last"] = time.time()
        _usb_touch[port] = time.time()
        ser = ent["ser"]
        _drain_to_line_boundary(ser)
        line = ("#%d %s" % (bus_id, cmd)) if bus_id else cmd
        ser.write((line + "\n").encode())
        want = ("@%d " % bus_id) if bus_id else None
        buf, end = b"", time.time() + wait
        # The firmware writes every reply as "\n<reply>\n" in ONE call, so a
        # reply is always preceded by a blank line. That marker is what makes
        # this reliable while the radio is logging: an orphaned TAIL of a log
        # line (the head lost to the buffer clear) has no blank line in front
        # of it, so it can be told apart from a real reply and dropped.
        #
        # Without this, hammering commands during a WiFi reconnect returned
        # every reply shifted by one — "PING" answered "son=8", the tail of
        # "[wifi] disconnected, reason=8". Measured on the bench: 49 of 60.
        #
        # `fallback` keeps a board running older firmware (no leading newline)
        # working: if the window ends without ever seeing the marker, the
        # first plausible line is used, exactly as before.
        saw_blank, fallback = False, None
        while time.time() < end:
            # read(1) returns the moment a byte arrives; read(256) would wait
            # for 256 bytes OR the full port timeout, and a reply like
            # "OK POSE" is 8 bytes — that put a ~150 ms floor under EVERY
            # command and was most of the latency in live/monitor mode.
            chunk = ser.read(1)
            if not chunk:
                continue
            n = ser.in_waiting          # drain whatever landed with it
            if n:
                chunk += ser.read(n)
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
                    saw_blank = True
                    continue
                if _LOG_LINE.match(t):
                    saw_blank = False   # a log line ended; no marker any more
                    continue
                if not saw_blank:
                    # no blank line in front of this: either an orphan tail, or
                    # a board on older firmware. Remember it and keep looking.
                    if fallback is None:
                        fallback = t
                    continue
                saw_blank = False
                if want:
                    if t.startswith(want):
                        return t[len(want):]
                elif not t.startswith(("#", "@", "->")):
                    return t
        if fallback is not None and not want:
            return fallback          # older firmware: no blank-line marker
        raise TimeoutError("no reply from " + port +
                           ((" (bus id %d)" % bus_id) if bus_id else ""))


# ---------------- unified device access (WiFi or USB/RS485, one API) ------
# A "dev" string names a module and its transport, so the SAME web UI works
# over any link:
#   wifi:<ip>              module on the network
#   usb:<port>             module on a cable
#   usb:<port>:<busid>     module on the RS485 bus behind that cable
#   usb:<port>@<peer>      module behind that one's OWN HOTSPOT   <-- see below
#   wifi:<ip>@<peer>       ...same, reached over the network
#
# The `@peer` form is what makes ONE USB cable enough for a whole installation
# with no venue WiFi at all. Plug into any module; the others join that
# module's own access point; the hub sends `REACH <peer> <command>` down the
# cable and the plugged-in module forwards it. Every page below then works on
# a module the PC has no route to whatsoever — same site, same file transfer,
# same everything, because only this one string changed.
#
# The peer is a module NAME or bus id, not an address, so it keeps working
# when the hotspot hands out a different address.
def parse_dev(dev):
    peer = ""
    if "@" in dev:
        dev, peer = dev.split("@", 1)
    if dev.startswith("wifi:"):
        return ("wifi", dev[5:], 0, peer)
    if dev.startswith("usb:"):
        rest = dev[4:].split(":")
        return ("usb", rest[0], int(rest[1]) if len(rest) > 1 and rest[1] else 0, peer)
    raise ValueError("bad dev (use wifi:<ip> or usb:<port>[:<id>], optionally @<peer>)")


def _via(c, peer):
    """Wrap a command so the module we can reach runs it on one we cannot."""
    return ("REACH %s %s" % (peer, c)) if peer else c


# A forwarded command has TWO hops to make and the far one is retried, so it can
# legitimately take several seconds. The normal 2 s budget cut it off mid-flight
# and the page got a 502 while the module was answering perfectly well.
PEER_WAIT = 8.0


def dev_cmd(dev, c):
    kind, addr, bus, peer = parse_dev(dev)
    if kind == "wifi":
        return Handler.robot_get(
            addr, "/api/cmd?c=" + urllib.parse.quote(_via(c, peer))).decode(errors="replace")
    return usb_cmd(addr, _via(c, peer), bus, wait=PEER_WAIT if peer else 2.0)


def dev_status(dev):
    kind, addr, bus, peer = parse_dev(dev)
    if peer:
        # the far module's own INFO, forwarded — never the middleman's, or
        # every page would show the wrong robot
        return dev_cmd(dev, "INFO").encode()
    if kind == "wifi":
        return Handler.robot_get(addr, "/api/status")
    return usb_cmd(addr, "INFO", bus).encode()


def dev_files(dev, d):
    kind, addr, bus, peer = parse_dev(dev)
    if peer:
        return dev_cmd(dev, "FILES " + d).encode()
    if kind == "wifi":
        return Handler.robot_get(addr, "/api/files?dir=" + urllib.parse.quote(d))
    return usb_cmd(addr, "FILES " + d, bus).encode()


def dev_download(dev, path):
    kind, addr, bus, peer = parse_dev(dev)
    if kind == "wifi" and not peer:
        return Handler.robot_get(addr, "/api/download?path=" + urllib.parse.quote(path))
    # USB: FREAD loop (base64 chunks)
    import base64
    name = path.rsplit("/", 1)[-1]
    out, off = b"", 0
    while True:
        r = usb_cmd(addr, _via("FREAD %s %d 120" % (name, off), peer), bus)             if kind == "usb" else dev_cmd(dev, "FREAD %s %d 120" % (name, off))
        if r == "EOF" or r.startswith("ERR"):
            break
        chunk = base64.b64decode(r)
        out += chunk
        off += len(chunk)
        if len(chunk) < 120:
            break
    return out


def dev_delete(dev, path):
    kind, addr, bus, peer = parse_dev(dev)
    if kind == "wifi" and not peer:
        return Handler.robot_get(addr, "/api/delete?path=" + urllib.parse.quote(path)).decode(errors="replace")
    name = path.rsplit("/", 1)[-1]
    return dev_cmd(dev, "FDEL " + name)


def dev_upload(dev, dirp, name, data: bytes):
    kind, addr, bus, peer = parse_dev(dev)
    if kind == "wifi" and not peer:
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
    r = dev_cmd(dev, "FBEGIN " + path)
    if not r.startswith("OK"):
        return r
    for i in range(0, len(data), 120):
        r = dev_cmd(dev, "FDATA " + base64.b64encode(data[i:i + 120]).decode())
        if not r.startswith("OK"):
            return r
    return dev_cmd(dev, "FEND")


# ---------------- the hub's own show clock --------------------------------
#
# THREE CLOCKS, EACH RIGHT FOR A DIFFERENT JOB
#
#   the module   MOVE <file>   survives the PC being switched off   -> the show
#   THE HUB      this          survives the browser being closed    -> rehearsal
#   the browser  rAF preview   survives nothing                     -> preview
#
# The middle one was missing, and it is the one you need while WORKING. A
# browser cannot be fixed for this: a hidden tab has requestAnimationFrame
# stopped and its timers throttled to roughly once a minute, by policy, in
# every browser. So a show driven from the page froze the moment you clicked
# away — which at a rehearsal is constantly.
#
# The hub is a native process that already owns the serial ports and nothing
# throttles it. It also helps BEFORE a sequence has been uploaded, which the
# module clock cannot: you are still editing.
#
# What it sends is exactly what the browser sent — one whole move at a time,
# `POSE ... T <ms>`, which the module interpolates itself. The hub only decides
# WHEN each move starts, so the motion is identical to a module-played show,
# not merely similar.
class ShowPlayer:
    """One player per hub. Runs a sequence on a real thread, at real times."""

    TICK = 0.02          # how often the thread wakes to check the clock / stop
    MIN_T = 80           # ms, the same floor the firmware and Studio use

    def __init__(self):
        self.lock = threading.Lock()
        self.thread = None
        self.stop_flag = threading.Event()
        self.dev = ""
        self.name = ""
        self.steps = []
        self.loop = False
        self.at_ms = 0
        self.total_ms = 0
        self.step = -1
        self.last = ""       # the module's answer to the most recent command
        self.error = ""
        self.started_at = 0.0

    # ---- what a caller sees ----
    def status(self):
        with self.lock:
            return {
                "running": self.running(),
                "dev": self.dev, "name": self.name, "loop": self.loop,
                "at_ms": int(self.at_ms), "total_ms": int(self.total_ms),
                "step": self.step, "steps": len(self.steps),
                "last": self.last, "error": self.error,
            }

    def running(self):
        return bool(self.thread and self.thread.is_alive())

    @staticmethod
    def total(steps):
        return sum(int(s.get("t", 0)) + int(s.get("hold", 0)) for s in steps)

    def start(self, dev, steps, loop=False, name="", from_ms=0):
        """Take over this device and play. Any previous run is stopped first."""
        parse_dev(dev)                       # raises on a malformed device
        steps = [{"pose": [float(v) for v in s["pose"]],
                  "t": max(0, int(s.get("t", 0))),
                  "hold": max(0, int(s.get("hold", 0)))} for s in steps]
        if len(steps) < 2:
            raise ValueError("a show needs at least two keyframes")
        for s in steps:
            if len(s["pose"]) != 10:
                raise ValueError("every keyframe needs 10 joint angles")
        self.stop()
        with self.lock:
            self.dev, self.steps, self.loop, self.name = dev, steps, bool(loop), name
            self.total_ms = self.total(steps)
            self.at_ms = max(0, min(int(from_ms), self.total_ms))
            self.step, self.last, self.error = -1, "", ""
            self.started_at = time.time()
        self.stop_flag.clear()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        return self.status()

    def stop(self, freeze=True, why=""):
        """Stop playing. `freeze` also tells the module to hold where it is."""
        th = self.thread
        if th and th.is_alive():
            self.stop_flag.set()
            th.join(timeout=3.0)
            if freeze:
                try:
                    self._say("STOP")
                except Exception as e:      # noqa: BLE001 - a dead cable must
                    self.error = str(e)     # not stop us from marking it stopped
        self.thread = None
        if why:
            with self.lock:
                self.error = why
        return self.status()

    # ---- the clock itself ----
    def _say(self, c):
        r = dev_cmd(self.dev, c)
        with self.lock:
            self.last = r
        return r

    def _sleep(self, seconds):
        """Wait, but wake up immediately when someone presses stop."""
        return not self.stop_flag.wait(max(0.0, seconds))

    def _run(self):
        try:
            # Take the robot: a module playing its own sequence would otherwise
            # be a second clock. Newer firmware also does this by itself when
            # the first POSE arrives; saying it explicitly keeps older boards
            # right and makes the intent visible on the wire.
            self._say("MOVE STOP")
            while True:
                if not self._play_once():
                    return
                if not self.loop:
                    return
                with self.lock:
                    self.at_ms = 0
        except Exception as e:              # noqa: BLE001
            with self.lock:
                self.error = str(e)

    def _play_once(self):
        """One pass through the steps, from self.at_ms. False = stopped."""
        # where in the show at_ms lands: which step, and how much of it is left
        start_i, into = 1, 0
        clock = self.steps[0].get("hold", 0)
        at = self.at_ms
        if at <= clock:
            # still at (or before) the start pose — put the robot on it first
            t = max(self.MIN_T, self.steps[0].get("t", 0) or self.MIN_T)
            self._mark(0, at)
            self._say(self._pose_cmd(self.steps[0]["pose"], t))
            if not self._sleep(t / 1000.0):
                return False
        else:
            for i in range(1, len(self.steps)):
                seg = self.steps[i]["t"]
                if at < clock + seg:
                    start_i, into = i, at - clock
                    break
                clock += seg
                if at < clock + self.steps[i].get("hold", 0):
                    start_i, into = i + 1, 0
                    clock += self.steps[i].get("hold", 0)
                    break
                clock += self.steps[i].get("hold", 0)
                start_i = i + 1

        for i in range(start_i, len(self.steps)):
            s = self.steps[i]
            # A resumed move gets the time it has LEFT, not the whole time, or
            # the robot replays a move the editor has already been through.
            left = max(self.MIN_T, s["t"] - into) if into else max(self.MIN_T, s["t"])
            into = 0
            self._mark(i, self._elapsed_to(i))
            self._say(self._pose_cmd(s["pose"], left))
            if not self._sleep(left / 1000.0):
                return False
            if s["hold"]:
                if not self._sleep(s["hold"] / 1000.0):
                    return False
        self._mark(len(self.steps) - 1, self.total_ms)
        return True

    def _pose_cmd(self, pose, t):
        vals = " ".join(("%g" % round(v, 1)) for v in pose)
        return "POSE %s T %d" % (vals, int(t))

    def _elapsed_to(self, i):
        ms = self.steps[0].get("hold", 0)
        for k in range(1, i):
            ms += self.steps[k]["t"] + self.steps[k].get("hold", 0)
        return ms

    def _mark(self, step, at_ms):
        with self.lock:
            self.step, self.at_ms = step, at_ms


show = ShowPlayer()

# Which commands mean "somebody else is moving this robot now".
#
# Read from the SAME registry the firmware compiles its table from
# (firmware/config/commands.json, `"motion": true`), so the hub cannot disagree
# with the board about what counts as taking over.
def motion_commands():
    if registry is None:
        return set()
    try:
        return {c["name"].upper() for c in registry.commands() if c.get("motion")}
    except Exception:                        # noqa: BLE001
        return set()


def check_takeover(kind, addr, bus, cmd):
    """A live motion command aimed at the device the hub is playing STOPS the
    hub's playback — the same rule the firmware applies to its own sequences.
    Two clocks on one robot is the bug this whole path exists to prevent."""
    if not show.running():
        return
    head = (cmd.strip().split(" ", 1)[0] or "").upper()
    if head not in motion_commands():
        return
    try:
        k, a, b, _peer = parse_dev(show.dev)
    except Exception:                        # noqa: BLE001
        return
    if k == kind and a == addr and (kind != "usb" or b == bus):
        show.stop(freeze=False, why="a live %s took over" % head)


# ---------------- flashing a board over its own cable ---------------------
#
# The hub already knows which module is on which cable, and since the firmware
# is built per module type there is a right answer to "which binary does this
# board get". So: pick a type, and the hub writes it.
#
# THE CABLE IS THE WHOLE PROBLEM. A COM port belongs to one program at a time,
# and the hub is normally that program — it holds every port open and shares it
# between its pages. esptool needs the port to ITSELF. Every "port is busy"
# failure on the bench was this. So a flash: stops the hub's show player if it
# is driving that port, closes the handle, and marks the port off-limits until
# esptool is finished (see _flash_ports, honoured by _usb_get and the probe).
#
# Where the images come from: `pio run -e mice_<type>` writes them into
# firmware/.pio/build/<env>/. Nothing is downloaded and nothing is bundled yet,
# so a PC that has never built the firmware is told exactly that instead of
# being offered a button that cannot work.
PIO_HOME = Path.home() / ".platformio"
FIRMWARE_DIR = HERE.parent / "firmware"
BOOT_APP0 = (PIO_HOME / "packages" / "framework-arduinoespressif32" /
             "tools" / "partitions" / "boot_app0.bin")

# offset -> which file, exactly as PlatformIO's own upload does it
FLASH_PARTS = (("0x1000", "bootloader.bin"), ("0x8000", "partitions.bin"),
               ("0xe000", None), ("0x10000", "firmware.bin"))  # None = boot_app0

_flash_ports = set()          # ports esptool is holding right now
_flash_lock = threading.Lock()


def flash_env(module_type):
    return "mice_" + re.sub(r"[^a-z0-9_]", "", (module_type or "").lower())


def flash_image(module_type):
    """What flashing this type would write — and what is missing if it can't."""
    env = flash_env(module_type)
    d = FIRMWARE_DIR / ".pio" / "build" / env
    parts, missing, built, total = [], [], 0, 0
    for off, name in FLASH_PARTS:
        f = BOOT_APP0 if name is None else (d / name)
        if f.is_file():
            parts.append((off, str(f)))
            total += f.stat().st_size
            built = max(built, f.stat().st_mtime)
        else:
            missing.append(name or "boot_app0.bin")
    return {"type": module_type, "env": env, "dir": str(d),
            "ready": not missing, "missing": missing, "parts": parts,
            "bytes": total, "built_at": int(built)}


def flash_images():
    """Every module type this PC could flash right now.

    The list comes from firmware/config/modules.json — the one file that
    declares what a board can be — plus `blank`, which is the fallback built
    into every firmware rather than a module of its own. Adding a module type
    therefore makes it appear here with nothing to change on this side.
    """
    types = list(registry.modules()) if registry else ["nong", "lift"]
    types.append("blank")
    return [{k: v for k, v in im.items() if k != "parts"}
            for im in (flash_image(t) for t in types)]


def esptool_cmd():
    """The command that runs esptool, or None with the reason it cannot.

    Not a pip dependency: the hub stays stdlib-only. PlatformIO already ships
    esptool, so if the firmware can be built on this PC it can also be flashed
    from here. MICE_ESPTOOL overrides it (a full command line), which is also
    how QC drives this path without touching a real board.
    """
    import os
    override = os.environ.get("MICE_ESPTOOL")
    if override:
        import shlex
        # posix=False on Windows, or shlex eats the backslashes in a path and
        # C:\Users\me\esptool.py silently becomes C:Usersmeesptool.py
        parts = shlex.split(override, posix=(os.name != "nt"))
        return [p.strip('"') for p in parts], ""
    esp = PIO_HOME / "packages" / "tool-esptoolpy" / "esptool.py"
    if not esp.is_file():
        return None, ("esptool was not found. It comes with PlatformIO — "
                      "install PlatformIO, or build the firmware once, and it "
                      "will be at %s" % esp)
    # A frozen hub cannot run itself as a python interpreter, so use
    # PlatformIO's own python when there is no real one to hand.
    py = PIO_HOME / "penv" / "Scripts" / "python.exe"
    if not py.is_file():
        py = PIO_HOME / "penv" / "bin" / "python"
    if getattr(sys, "frozen", False):
        if not py.is_file():
            return None, ("no python to run esptool with — PlatformIO's is "
                          "usually at %s" % py)
        return [str(py), str(esp)], ""
    return [str(py if py.is_file() else sys.executable), str(esp)], ""


class Flasher:
    """One flash at a time, on one cable, reported honestly."""

    def __init__(self):
        self.lock = threading.Lock()
        self.thread = None
        self.port = ""
        self.type = ""
        self.percent = 0
        self.stage = ""
        self.how = ""             # "usb" (esptool) or "wifi" (OTA)
        self.log = []
        self.ok = None            # None = running, True/False = finished
        self.error = ""

    def running(self):
        return bool(self.thread and self.thread.is_alive())

    def status(self):
        with self.lock:
            return {"running": self.running(), "port": self.port,
                    "type": self.type, "percent": self.percent,
                    "stage": self.stage, "ok": self.ok, "error": self.error,
                    "how": self.how, "log": self.log[-14:]}

    # ---- over WiFi (OTA) -------------------------------------------------
    #
    # Same job, no cable. The board has two app slots (min_spiffs.csv gives
    # app0 and app1, 1.875 MB each), so the update is written to the one that
    # is NOT running: an update that fails, or a PC that walks away half way,
    # leaves the board booting the firmware it already had.
    #
    # Only firmware.bin travels. The bootloader and the partition table are the
    # parts that would brick a board if they went wrong, they almost never
    # change, and OTA cannot write them anyway — that is the point of OTA.
    def start_ota(self, ip, module_type):
        if self.running():
            raise RuntimeError("already flashing %s — one board at a time"
                               % (self.port or self.type))
        im = flash_image(module_type)
        if not im["ready"]:
            raise RuntimeError(
                "no %s firmware on this PC (missing %s). Build it first: "
                "pio run -e %s" % (module_type, ", ".join(im["missing"]), im["env"]))
        if not ip:
            raise RuntimeError("which module? this needs its WiFi address")
        with self.lock:
            self.port, self.type, self.how = ip, module_type, "wifi"
            self.percent, self.stage, self.log = 0, "connecting", []
            self.ok, self.error = None, ""
        self.thread = threading.Thread(target=self._run_ota, args=(ip, im), daemon=True)
        self.thread.start()
        return self.status()

    def _run_ota(self, ip, im):
        import http.client
        try:
            path = [p for off, p in im["parts"] if p.endswith("firmware.bin")][0]
            data = Path(path).read_bytes()
            self._say("sending %s (%.2f MB) to %s over WiFi"
                      % (Path(path).name, len(data) / 1048576.0, ip))
            b = "----miceota"
            head = ("--%s\r\nContent-Disposition: form-data; name=\"file\"; "
                    "filename=\"firmware.bin\"\r\nContent-Type: "
                    "application/octet-stream\r\n\r\n" % b).encode()
            tail = ("\r\n--%s--\r\n" % b).encode()
            conn = http.client.HTTPConnection(ip, timeout=90)
            conn.putrequest("POST", "/api/ota")
            conn.putheader("Content-Type", "multipart/form-data; boundary=" + b)
            conn.putheader("Content-Length", str(len(head) + len(data) + len(tail)))
            conn.endheaders()
            conn.send(head)
            with self.lock:
                self.stage = "writing"
            CH = 4096
            for i in range(0, len(data), CH):
                conn.send(data[i:i + CH])
                with self.lock:
                    self.percent = int((i + CH) * 100 / max(1, len(data)))
            conn.send(tail)
            resp = conn.getresponse()
            body = resp.read().decode(errors="replace").strip()
            self._say("%d %s" % (resp.status, body[:200]))
            with self.lock:
                self.ok = (resp.status == 200)
                self.percent = 100 if self.ok else self.percent
                self.stage = "restarting the board" if self.ok else "failed"
                if not self.ok:
                    # the board's own words: it says "the module is moving",
                    # "a sequence is playing" or what the flash write hit
                    self.error = body[:200] or ("the module answered %d" % resp.status)
        except Exception as e:            # noqa: BLE001
            with self.lock:
                self.ok, self.stage = False, "failed"
                self.error = ("%s — is it on WiFi, and does its firmware have "
                              "OTA? (OTA over the cable first, once)" % e)

    def start(self, port, module_type):
        if self.running():
            raise RuntimeError("already flashing %s — one cable at a time" % self.port)
        im = flash_image(module_type)
        if not im["ready"]:
            raise RuntimeError(
                "no %s firmware on this PC (missing %s). Build it first: "
                "pio run -e %s" % (module_type, ", ".join(im["missing"]), im["env"]))
        cmd, why = esptool_cmd()
        if not cmd:
            raise RuntimeError(why)
        if not port:
            raise RuntimeError("which port? pick the cable the board is on")
        with self.lock:
            self.port, self.type, self.how = port, module_type, "usb"
            self.percent, self.stage, self.log = 0, "starting", []
            self.ok, self.error = None, ""
        self.thread = threading.Thread(target=self._run, args=(cmd, im), daemon=True)
        self.thread.start()
        return self.status()

    def _say(self, line):
        with self.lock:
            self.log.append(line)
            m = re.search(r"\((\d+)\s*%\)", line)
            if m:
                self.percent = int(m.group(1))
            low = line.lower()
            for word, stage in (("connecting", "connecting to the board"),
                                ("erasing", "erasing"), ("writing at", "writing"),
                                ("hash of data verified", "verified"),
                                ("hard resetting", "restarting the board")):
                if word in low:
                    self.stage = stage

    def _run(self, cmd, im):
        port = self.port
        try:
            # Give the cable up completely. The hub is the port's owner, so
            # nothing else can do this for us — and esptool cannot share.
            if show.running():
                try:
                    k, a, b, _p = parse_dev(show.dev)
                    if k == "usb" and a == port:
                        show.stop(freeze=False, why="the board is being flashed")
                except Exception:      # noqa: BLE001
                    pass
            with _flash_lock:
                _flash_ports.add(port)
            usb_close(port)
            _usb_touch.pop(port, None)
            _usb_ident.pop(port, None)     # whatever it was, it is about to change
            time.sleep(0.3)                # let Windows actually release the handle

            args = list(cmd) + ["--chip", "esp32", "--port", port,
                                "--baud", "460800", "write_flash", "-z",
                                "--flash_mode", "dio", "--flash_freq", "40m",
                                "--flash_size", "detect"]
            for off, path in im["parts"]:
                args += [off, path]
            self._say("$ esptool " + " ".join(args[2:]))
            import subprocess
            p = subprocess.Popen(args, stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT, text=True,
                                 errors="replace", bufsize=1)
            for line in p.stdout:
                line = line.rstrip()
                if line:
                    self._say(line)
            code = p.wait()
            with self.lock:
                self.ok = (code == 0)
                self.percent = 100 if self.ok else self.percent
                self.stage = "done" if self.ok else "failed"
                if not self.ok:
                    self.error = self._why_failed()
        except Exception as e:            # noqa: BLE001
            with self.lock:
                self.ok, self.error, self.stage = False, str(e), "failed"
        finally:
            with _flash_lock:
                _flash_ports.discard(port)

    def _why_failed(self):
        """The one line worth reading, in words that say what to do."""
        text = "\n".join(self.log).lower()
        if "failed to connect" in text or "no serial data" in text:
            return ("the board did not answer. Hold its BOOT/IO0 button while "
                    "the flash starts, or check the cable is a data cable.")
        if "access is denied" in text or "could not open" in text or "busy" in text:
            return ("%s is held by another program — close any serial monitor, "
                    "Arduino IDE or Studio 'USB direct' tab, then try again"
                    % self.port)
        for line in reversed(self.log):
            if "error" in line.lower() or "fatal" in line.lower():
                return line.strip()[:200]
        return "esptool failed — see the log"


flasher = Flasher()


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
    """Identify the module on a COM port + every RS485 module behind it.

    While a client is DRIVING that cable (module website open, Nong Studio
    connected) the full probe is skipped: it would hold the port's lock for
    ~1.5 s every round and stutter their commands. The identity is already
    known from the first probe, so the cached answer is returned with
    "inuse": True instead."""
    out = {"port": port, "module": None, "rs485": [], "error": ""}
    try:
        import serial  # noqa: F401
    except ImportError:
        out["error"] = "pyserial not installed (pip install pyserial)"
        return out
    light = usb_in_use(port)
    if light and port in _usb_ident:
        cached = dict(_usb_ident[port])
        cached["inuse"] = True
        return cached
    try:
        ent = _usb_get(port)  # shared manager: no conflict with the proxy
    except Exception as e:  # held by an outside program, or not a module
        out["error"] = str(e)
        return out
    with ent["lock"]:
        ent["last"] = time.time()
        ser = ent["ser"]
        try:
            _drain_to_line_boundary(ser)
            # 1) directly connected module?
            ser.write(b"INFO\n")
            for ln in _read_lines(ser, 0.6):
                if ln.startswith("{"):
                    try:
                        st = json.loads(ln)
                        out["module"] = {"id": st.get("id"), "name": st.get("name"),
                                         "type": st.get("type"),
                                         "group": st.get("group", ""),
                                         **_wifi_of(st)}
                        break
                    except ValueError:
                        pass
            if light:  # in use: identify only, never hold the cable for a bus census
                out["inuse"] = True
                if out["module"]:
                    _usb_ident[port] = dict(out)
                return out
            # 2) census of the RS485 bus behind this port
            _drain_to_line_boundary(ser)
            ser.write(b"#* PING\n")
            seen = {}
            for ln in _read_lines(ser, 0.8):
                m = re.match(r"^@(\d+)\s+PONG\s+(\d+)\s+(.+)\s+(\S+)$", ln)
                if m:
                    seen[int(m.group(1))] = {"id": int(m.group(1)), "name": m.group(3),
                                             "type": m.group(4), "ip": "", "wifi_mode": ""}
            # ask each bus module for its INFO to learn its WiFi ip (for links)
            for mid in list(seen)[:6]:
                _drain_to_line_boundary(ser)
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
            if out["module"] or out["rs485"]:
                _usb_ident[port] = dict(out)   # answer to reuse while in use
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
        # A port being flashed is not probed: opening it would fight esptool
        # for the cable, and the identity is about to change anyway.
        real = [i["port"] for i in infos
                if not i["bt"] and i["port"] not in _flash_ports]
        for i in infos:
            if i["bt"]:
                out.append({"port": i["port"], "module": None, "rs485": [],
                            "error": "Bluetooth port — skipped", "bt": True})
            elif i["port"] in _flash_ports:
                out.append({"port": i["port"], "module": None, "rs485": [],
                            "error": "being flashed right now", "flashing": True})
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
    # HTTP/1.1, so a browser can KEEP ITS CONNECTION.
    #
    # BaseHTTPRequestHandler defaults to HTTP/1.0, which means every response
    # closes the socket — so a browser opens a fresh TCP connection for every
    # page asset, every status poll, every pose sent by a slider, and every
    # camera frame. Python measurements never showed it, because they opened a
    # new connection each time anyway; a browser doing dozens of requests per
    # interaction pays the setup cost on every one, and the whole app feels
    # like it is dragging.
    #
    # This is safe only because every response here sends a Content-Length
    # (see send_bytes) — with keep-alive, a response without one leaves the
    # browser waiting forever for an end that never comes. The one endpoint
    # that cannot have a length is the camera stream, and it says
    # `Connection: close` for itself.
    protocol_version = "HTTP/1.1"
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
        self.drain()          # never reject a POST without reading its body
        self.send_json({"ok": False, "error": str(msg)}, code=code)

    def body(self) -> bytes:
        n = int(self.headers.get("Content-Length") or 0)
        self._body_read = True
        return self.rfile.read(n) if n else b""

    def drain(self):
        """Swallow an unread request body.

        Answering a POST without reading what the client sent makes Windows
        abort the connection, so the caller sees a network error instead of the
        message explaining what was wrong. That is how a rejected model upload
        looked like a broken hub rather than 'allowed: .stl .png ...'.
        """
        if getattr(self, "_body_read", False):
            return
        n = int(self.headers.get("Content-Length") or 0)
        if n:
            try:
                self.rfile.read(n)
            except Exception:  # noqa: BLE001
                pass
        self._body_read = True

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
        # Registered web apps. An app is a folder with an app.json (see
        # code/apps/), so a NEW tool is served and listed without touching this
        # file at all. Studio and the help page declare their historic URLs and
        # keep their own long-standing branches below — they are listed from
        # the registry but still served by the code that has always served
        # them, so no existing link or QC driver changes behaviour.
        if path.startswith("/app/") and registry:
            rest = path[len("/app/"):]
            app_id, _, rel = rest.partition("/")
            app = registry.app_by_id(app_id)
            if not app:
                return self.send_err("no such app: " + app_id, 404)
            base = Path(app["dir"]).resolve()
            f = (base / (rel or app["entry"])).resolve()
            if base not in f.parents and f != base:
                return self.send_err("forbidden", 403)
            if not f.is_file():
                return self.send_err("not found: " + path, 404)
            return self.send_bytes(f.read_bytes(),
                                   MIME.get(f.suffix.lower(), "application/octet-stream"))

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
        if path == "/rig_default.js":
            # The tuned rig, as a plain script so app.js can read it
            # SYNCHRONOUSLY before it builds DEFAULT_RIG. Missing file = an
            # empty script, and the app falls back to its built-in constants.
            f = STUDIO / "rig_default.json"
            body = f.read_text(encoding="utf-8") if f.is_file() else "null"
            js = "window.NONG_RIG_DEFAULT = " + body + ";\n"
            return self.send_bytes(js.encode(), MIME[".js"])
        if path in ("/help", "/help.html"):
            # Every feature of the whole system, offline. Served from the PC so
            # it works with no internet and no account — see the "docs" QC
            # check, which fails when a new command or module type is missing.
            return self.send_bytes((HUB_WEB / "help.html").read_bytes(), MIME[".html"])
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
                    kind, addr, bus, peer = parse_dev(dev)
                    if kind == "wifi" and not peer:
                        return self.send_bytes(Handler.robot_get(addr, "/api/peers"),
                                               "application/json")
                    # Over a cable this is the whole point: with no venue WiFi
                    # the other modules sit on THIS module's own hotspot, and
                    # the PEERS command is the only way anything upstream can
                    # learn they exist. It used to answer [] and the fleet was
                    # invisible from the one cable that could reach it.
                    try:
                        return self.send_bytes(dev_cmd(dev, "PEERS").encode(),
                                               "application/json")
                    except Exception:
                        return self.send_json([])
                if what == "cam.stream":
                    # The live view, piped straight through. An <img> cannot go
                    # through the fetch shim, so the page addresses this URL
                    # itself; the hub copies the module's multipart body to the
                    # browser until one of them goes away.
                    kind, addr, bus, peer = parse_dev(dev)
                    if kind != "wifi" or peer:
                        return self.send_err(
                            "a live view cannot come down the USB/RS485 cable — "
                            "open this module over WiFi", 501)
                    import http.client
                    up = http.client.HTTPConnection(addr, timeout=20)
                    up.request("GET", "/api/cam.stream")
                    r = up.getresponse()
                    if r.status != 200:
                        up.close()
                        return self.send_err(r.read().decode(errors="replace")[:200],
                                             r.status)
                    self.send_response(200)
                    self.send_header("Content-Type", r.getheader("Content-Type"))
                    self.send_header("Cache-Control", "no-store")
                    # No length is possible: it ends when the viewer leaves. So
                    # this one response opts out of keep-alive explicitly,
                    # rather than leaving the browser waiting for a length.
                    self.send_header("Connection", "close")
                    self.close_connection = True
                    self.end_headers()
                    try:
                        while True:
                            chunk = r.read(2048)
                            if not chunk:
                                break
                            self.wfile.write(chunk)
                    except Exception:            # noqa: BLE001 - the browser
                        pass                      # closed the tab; that is normal
                    finally:
                        up.close()
                    return
                if what == "cam.jpg":
                    # A camera frame, for the module site served BY the hub.
                    # The page asks for /api/cam.jpg; the shim rewrites it to
                    # here, and this fetches it from the board.
                    kind, addr, bus, peer = parse_dev(dev)
                    if kind != "wifi" or peer:
                        # Not a limitation worth hiding: a JPEG cannot travel on
                        # a one-line command channel, which is all a cable is.
                        return self.send_err(
                            "a picture cannot come down the USB/RS485 cable — "
                            "open this module over WiFi to see the camera", 501)
                    return self.send_bytes(
                        Handler.robot_get(addr, "/api/cam.jpg"), "image/jpeg")
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
        if path == "/api/servos":
            # The ONE servo table, shared with the firmware (which compiles it
            # into a header). Studio reads this instead of keeping a second
            # copy that could drift.
            if not registry:
                return self.send_json({"ok": False, "servos": {}})
            return self.send_json({"ok": True, "servos": registry.servos()})

        if path == "/api/apps":
            # what the hub page offers to open — rendered from the registry, so
            # a new app appears without editing hub.html
            if not registry:
                return self.send_json({"ok": False, "apps": [], "error": "registry unavailable"})
            out = [{k: a[k] for k in ("id", "name", "blurb", "icon", "path", "order")}
                   for a in registry.apps() if a.get("show", True)]
            return self.send_json({"ok": True, "apps": out})

        if path == "/api/scan":
            force = (q.get("force") or ["0"])[0] == "1"
            return self.send_json({"ok": True, "lan": lan_ip(),
                                   "modules": scan_modules(force),
                                   "ports": serial_ports()})

        if path == "/api/ports":
            # just the typed port list (no WiFi scan, no port opening) — the
            # streaming USB probe uses this, then probes each port on its own.
            # "inuse" = the hub is already talking on that cable for another
            # page; that is fine (the hub shares it), it is shown so the UI
            # can say so. "who" names the module when it is already known.
            ports = serial_ports()
            for p in ports:
                p["inuse"] = usb_in_use(p["port"])
                known = (_usb_ident.get(p["port"]) or {}).get("module")
                p["who"] = ("%s (%s)" % (known.get("name"), known.get("type"))) if known else ""
            return self.send_json({"ok": True, "ports": ports})

        if path == "/api/scanusb":
            # ?port=COMx probes ONE port (streaming UI: results render as
            # each port answers); no port = all non-Bluetooth ports at once
            port = (q.get("port") or [""])[0]
            if port:
                return self.send_json({"ok": True, "usb": [probe_usb_one(port)]})
            force = (q.get("force") or ["0"])[0] == "1"
            return self.send_json({"ok": True, "usb": probe_usb_all(force)})

        # ---- USB command proxy: full module control over the cable, no
        # WiFi needed. This is THE way every hub page reaches a cable —
        # /module.html, and Nong Studio's "USB (shared)" link — so they can
        # all be open on the same port at once. Optional id = RS485 address
        # of a module BEHIND this port.
        if path == "/api/usb/cmd":
            port = (q.get("port") or [""])[0]
            c = (q.get("c") or [""])[0]
            bus = int((q.get("id") or ["0"])[0] or 0)
            if not port or not c:
                return self.send_err("need port and c")
            check_takeover("usb", port, bus, c)   # never two clocks on one robot
            try:
                return self.send_bytes(usb_cmd(port, c, bus).encode(),
                                       "text/plain; charset=utf-8")
            except Exception as e:  # noqa: BLE001
                return self.send_err(e, 502)

        if path == "/api/usb/close":
            # hand the cable back to an outside program (esptool, a serial
            # monitor). Hub pages do NOT need this to share a port.
            port = (q.get("port") or [None])[0]
            usb_close(port)
            for p in ([port] if port else list(_usb_touch)):
                _usb_touch.pop(p, None)
            return self.send_json({"ok": True})

        # ---- flashing a board over its own cable (see Flasher) ----
        # GET  /api/flash/images   what this PC could flash, and what is missing
        # POST /api/flash?port=&type=   start (the cable is taken for the job)
        # GET  /api/flash          progress, then ok/error
        if path == "/api/flash/images":
            cmd, why = esptool_cmd()
            return self.send_json({"images": flash_images(),
                                   "esptool": bool(cmd), "why": why})
        if path == "/api/flash" and method == "POST":
            try:
                return self.send_json(flasher.start(
                    (q.get("port") or [""])[0], (q.get("type") or [""])[0]))
            except Exception as e:            # noqa: BLE001
                return self.send_err(e)
        if path == "/api/flash":
            return self.send_json(flasher.status())
        # the same job, over WiFi: no cable, and the board keeps the firmware
        # it already has if the update does not complete
        if path == "/api/ota" and method == "POST":
            try:
                return self.send_json(flasher.start_ota(
                    (q.get("ip") or [""])[0], (q.get("type") or [""])[0]))
            except Exception as e:            # noqa: BLE001
                return self.send_err(e)

        # ---- the hub as the show clock (see ShowPlayer) ----
        # POST /api/play   {dev, steps:[{pose[10], t, hold}], loop, name, from_ms}
        # GET  /api/play   where the show is right now
        # POST /api/play/stop
        if path == "/api/play" and method == "POST":
            try:
                d = json.loads(self.body().decode())
                return self.send_json(show.start(
                    d["dev"], d["steps"], d.get("loop"), d.get("name", ""),
                    d.get("from_ms", 0)))
            except Exception as e:            # noqa: BLE001
                return self.send_err(e)
        if path == "/api/play":
            return self.send_json(show.status())
        if path == "/api/play/stop":
            return self.send_json(show.stop())

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

        if path == "/api/rigdefault" and method == "POST":
            # "Make this the factory default": the browser is the ONLY place the
            # live rig exists, so it posts it here to be written into the repo.
            # Every fresh browser then starts on it, and Reset returns to it.
            data = json.loads(self.body().decode())
            rig = data.get("rig")
            if not isinstance(rig, dict) or "min" not in rig:
                return self.send_err("that does not look like a rig")
            (STUDIO / "rig_default.json").write_text(
                json.dumps(rig, indent=1), encoding="utf-8")
            return self.send_json({"ok": True, "file": "rig_default.json",
                                   "keys": len(rig)})

        if path == "/api/settings" and method == "POST":
            # Studio's whole setup, parked on THIS hub so another PC can pull
            # it. The browser is the only place these settings live (they are
            # localStorage keys), so the page has to hand them over.
            data = json.loads(self.body().decode())
            bundle = data.get("bundle")
            if not isinstance(bundle, dict) or "rig" not in bundle:
                return self.send_err("that does not look like a settings bundle")
            bundle["savedAt"] = time.strftime("%Y-%m-%d %H:%M:%S")
            bundle["savedBy"] = socket.gethostname()
            SETTINGS_FILE.write_text(json.dumps(bundle, indent=1), encoding="utf-8")
            return self.send_json({"ok": True, "savedAt": bundle["savedAt"]})

        if path == "/api/settings":
            if not SETTINGS_FILE.is_file():
                return self.send_json({"ok": False,
                                       "why": "no settings have been shared from this PC yet"})
            return self.send_bytes(SETTINGS_FILE.read_bytes(), MIME[".json"])

        if path == "/api/settings/peer":
            # Fetch another PC's settings THROUGH this hub, not from the
            # browser. A page served by this hub cannot read another hub's
            # response directly — that is a cross-origin request and the
            # browser blocks it. The hub has no such rule, so it does the
            # fetching and hands the result back same-origin.
            host = (q.get("host") or [""])[0].strip()
            if not host:
                return self.send_err("need host=<ip or name of the other PC>")
            if ":" not in host:
                host += ":%d" % PORT
            try:
                with urllib.request.urlopen("http://%s/api/settings" % host, timeout=6) as r:
                    body = r.read()
            except Exception as e:  # noqa: BLE001
                return self.send_err("cannot reach %s (%s)" % (host, type(e).__name__))
            return self.send_bytes(body, MIME[".json"])

        if path == "/api/hubs":
            # Other mice hubs on this network, so nobody has to type an IP.
            return self.send_json({"ok": True, "hubs": scan_hubs(
                (q.get("force") or ["0"])[0] == "1")})

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
            check_takeover("wifi", ip, 0, c)      # never two clocks on one robot
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
