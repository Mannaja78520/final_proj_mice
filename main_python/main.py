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

import base64
import itertools
import hashlib
import json
import os
import re
import shutil
import uuid
import socket
import sys
import time
import threading
import urllib.parse
import urllib.error
import urllib.request

import discovery
import mdns
import qr
import webbrowser
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutTimeout
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

# WHERE THE APP IS, and WHERE ITS FILES COME FROM, are two different questions
# once the app is a single file. Asked for 2026-08-19: the second PC should not
# need Python, or Node, or a folder of web pages - just the one exe.
#
#   HERE     the folder the exe sits in. Everything the hub WRITES goes there:
#            the password hash, the known hubs, Studio's saved projects. It has
#            to be a real folder that survives a restart.
#   asset()  a read-only file that SHIPS with the app - a page, the CSS, a
#            registry. In a one-file build PyInstaller unpacks those into a
#            temporary folder (sys._MEIPASS) that is DELETED when the app
#            exits, so nothing writable may ever be looked up through it. That
#            distinction is the whole reason this is two things and not one.
#
# A file next to the exe wins over the bundled copy, so a venue can drop a
# changed palette or a fixed page beside MiceHub.exe and see it immediately,
# without a rebuild and without a Python installed anywhere.
if getattr(sys, "frozen", False):
    HERE = Path(sys.executable).resolve().parent
    _ROOTS = [HERE, Path(getattr(sys, "_MEIPASS", "") or HERE)]
    # Writable trees live next to the exe. An older install kept them one level
    # up; if that layout is there, keep using it, because updating the app must
    # never hide someone's saved work.
    DATA = HERE.parent if (HERE.parent / "nong").is_dir() else HERE
else:
    HERE = Path(__file__).resolve().parent
    _ROOTS = [HERE.parent]
    DATA = HERE.parent


def asset(*parts):
    """A read-only file that ships with the app, wherever it ended up."""
    found = None
    for root in _ROOTS:
        found = root.joinpath(*parts)
        if found.exists():
            return found
    return found          # the last candidate, so errors name a real path

# Registries: data files that describe things, so adding a web app / servo /
# command is one edit in one place. See code/tools/registry.py.
sys.path.insert(0, str(asset("tools")))
try:
    import registry
except Exception as _e:            # a broken registry must not stop the hub
    registry = None
    print("[hub] registries unavailable:", _e)

import build_stamp                                         # noqa: E402
import cam_relay                                           # noqa: E402
import hub_auth                                            # noqa: E402
import hub_pair                                            # noqa: E402
import partner_launch                                      # noqa: E402
import stream_audio                                        # noqa: E402

HUB_WEB = asset("main_python", "web")
# A23-1 comparison versions (brief: docs/a23_brief.md). Additive mounts
# only - the incumbent pages at / are untouched until the user picks a
# winner, and both folders may be absent while the designs are built.
GEMINI_WEB = asset("main_python", "web_gemini")
OX_WEB = asset("main_python", "web_ox")
# Written at runtime, holds a password HASH. Never promoted (promote.py's
# SKIP_FILES): it belongs to the machine, not to the source.
AUTH_STORE = Path(os.environ.get("MICE_HUB_AUTH")
                  or (HERE / "hub_auth.json"))
# The ONE design system, served at /mice.css to every page the hub serves —
# including the module's own website, which links the same URL and gets the
# board's compiled-in copy when it is reached over WiFi instead.
SHARED_WEB = asset("shared", "web")
WEBUI_H = asset("firmware", "src", "web", "WebUI.h")
STUDIO = DATA / "nong" / "main_python_set_nong"
STUDIO_WEB = asset("nong", "main_python_set_nong", "web")
PROJECTS = STUDIO / "projects"
SEQUENCES = STUDIO / "sequences"
MODELS = STUDIO / "models"

HOST = "0.0.0.0"
PORT = 8642

# The gate. Built once, on first use, so importing this module (which QC does)
# does not create a password file as a side effect of the import itself.
_auth = []


def auth():
    if not _auth:
        _auth.append(hub_auth.Auth(AUTH_STORE))
    return _auth[0]


# The pairing code lives in MEMORY, like a session: restarting the hub stops
# showing it. Nothing about a code is worth surviving a restart.
PAIRING = hub_pair.Pairing()
# ...and the accounts this hub fetched, held only until the person answers the
# one question a copy can raise: a name that exists on both PCs.
PAIR_PENDING = hub_pair.Pending()

# The Voice app's helper (apps/voice/service.py) runs as its own process —
# torch can never live inside this stdlib program. The hub only forwards to
# it. WHERE it answers is resolved per call, not at import: both so editing
# config/voice.json needs no restart, and because QC boots several hubs in
# one process, where an import-time path would freeze whichever environment
# existed first.
def voice_service_url():
    """(address, why-not). An empty address means the proxy must refuse — and
    say which of the two reasons it is, because the fix differs: a broken file
    wants repairing, a missing address wants writing."""
    path = Path(os.environ.get("MICE_VOICE_CONFIG")
                or asset("config", "voice.json"))
    try:
        if registry:
            cfg = registry.load(path)
        else:
            cfg = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:                  # noqa: BLE001 - a broken store must
        return "", ("config/voice.json could not be read (%s)" % e)
    url = (cfg.get("service") or "").rstrip("/")
    if url and "://" in url:
        parts = urllib.parse.urlsplit(url)
        try:
            portless = parts.port is None
        except ValueError:                  # malformed netloc: let urlopen say so
            portless = False
        if portless and (parts.hostname or "").strip():
            # A portless address would ask :80 while the helper answers on its
            # own default - the same fallback apps/voice/service.py uses.
            url = "%s://%s:8767" % (parts.scheme or "http", parts.hostname)
    return url, ("" if url else "config/voice.json has no `service` address")


# Which pages work with no login. Read per request, like the voice address
# above and for the same reason: a designer editing the words should see them
# on the next refresh, not after a restart of a frozen exe.
#
# A BROKEN FILE MUST NOT LOCK ANYBODY OUT. This decides what is SHOWN, never
# what is allowed - the gate is hub_auth.GATED - so when the file cannot be
# read the honest answer is the safe one: treat nothing as gated, and say why.
# Failing the other way would hide the whole hub behind a box nobody can pass
# because the file that describes the box is the broken one.
PAGE_ACCESS_FALLBACK = {"openPages": [], "needLogin": [], "words": {}}


def read_page_access():
    path = Path(os.environ.get("MICE_PAGE_ACCESS")
                or asset("config", "page_access.json"))
    try:
        cfg = (registry.load(path) if registry
               else json.loads(path.read_text(encoding="utf-8")))
    except Exception as e:                                  # noqa: BLE001
        out = dict(PAGE_ACCESS_FALLBACK)
        out["ok"] = False
        out["error"] = "config/page_access.json could not be read (%s)" % e
        return out
    return {"ok": True,
            "openPages": list(cfg.get("openPages") or []),
            "needLogin": list(cfg.get("needLogin") or []),
            "words": dict(cfg.get("words") or {})}


# The outside programs the rig follows. One entry each in config/partners.json,
# so the second program is an entry and no code (asked 2026-09-08). Read per
# request for the same reason as the two above: a designer moving an app to
# another port should see it work on the next refresh.
#
# It holds ADDRESSES, never a login. Logins live beside hub_auth.json, out of
# the served tree, out of promotion and out of the exe.
def read_partners():
    path = Path(os.environ.get("MICE_PARTNERS")
                or asset("config", "partners.json"))
    try:
        cfg = (registry.load(path) if registry
               else json.loads(path.read_text(encoding="utf-8")))
    except Exception as e:                                  # noqa: BLE001
        return {"ok": False, "partners": {},
                "error": "config/partners.json could not be read (%s)" % e}
    # Where each one REALLY answered last time it was started - their ports
    # can change with any update of theirs (partner_launch.live).
    cfg = {k: partner_launch.live(k, v) if isinstance(v, dict) else v
           for k, v in cfg.items()}
    return {"ok": True, "partners": cfg}


_reports_lock = threading.Lock()   # one read-modify-write of a report at a time


def _translate_report_later(fname, text):
    """Fill one report file's text_en in place, in the background.

    A complaint saved in any language gains an English twin a minute later:
    submitting must not wait on a first model load, and the list must never
    translate per refresh. Any failure leaves the file exactly as the visitor
    wrote it - untranslated is honest, a wrong guess is not.
    """
    try:
        base, why_not = voice_service_url()
        if not base:
            return
        req = urllib.request.Request(
            base + "/translate",
            data=json.dumps({"text": text}).encode("utf-8"),
            headers={"Content-Type": "application/json"}, method="POST")
        # The model may load on this call - the same long wait /api/voice allows.
        with urllib.request.urlopen(req, timeout=180) as resp:
            vdata = json.loads(resp.read().decode("utf-8"))
        out = (vdata.get("text") or "").strip() if vdata.get("ok") else ""
        if not out or out == text:
            return
        # The status screen edits the same file. One lock around each
        # read-modify-write, or whichever writes second puts back a copy
        # without the other's change (a closed report reopens itself, or the
        # translation silently vanishes).
        with _reports_lock:
            data = json.loads(fname.read_text(encoding="utf-8"))
            data["text_en"] = out
            write_atomic(fname, json.dumps(data, ensure_ascii=False, indent=2))
    except Exception:                       # noqa: BLE001 - the report stands alone
        pass

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


_tmp_seq = itertools.count()      # makes each writer's temp file its own


def write_atomic(dest: Path, text: str, newline=None, keep_backup=True):
    """Write a file so a failure cannot destroy what was already there.

    `Path.write_text` opens in "w", which truncates the target the instant it
    opens — before a single byte of the new content is written. A save that
    then fails (full disk, the process killed, a laptop lid closed mid-write)
    left the user with NEITHER version. These are hand-built projects and
    sequences representing hours of posing, and the editor holds the only other
    copy in RAM.

    So: write beside it, then swap. os.replace is atomic on Windows and POSIX,
    so at every instant the destination is either wholly the old file or wholly
    the new one. The previous version is also kept as <name>.bak, because
    "saved over the wrong name" is the other way this work disappears and the
    editor has no undo for it.
    """
    # The temp name carries the thread id and a counter. A single shared
    # "<name>.tmp" looked atomic and was not: the hub is a ThreadingHTTPServer,
    # so two saves of the same project at once (two tabs, or a double-click)
    # both opened the SAME temp file and interleaved their bytes, and whichever
    # renamed last published the mixture. Per-writer temp files cannot collide,
    # and os.replace is still atomic, so the destination is only ever wholly
    # one version or wholly the other.
    tmp = dest.with_name("%s.%d.%d.tmp" % (dest.name, threading.get_ident(),
                                           next(_tmp_seq)))
    tmp.write_text(text, encoding="utf-8", newline=newline)
    if keep_backup and dest.exists():
        try:
            os.replace(dest, dest.with_name(dest.name + ".bak"))
        except OSError:
            pass                      # a missing backup must not stop the save
    os.replace(tmp, dest)


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
 // The pin drawing, into the Hardware pins card. It comes from the HUB, not
 // from board flash - the WROOM reference is 133 KB and a board cannot spare
 // that. WHICH drawing is the hub's decision (/api/pinout): the 38-pin WROOM
 // is right for a nong or a lift and wrong for a camera, whose GPIOs are
 // nearly all taken by the sensor. Wiring a servo to GPIO 26 because the
 // picture showed it free would put it on the SCCB data line.
 window.addEventListener('load',function(){setTimeout(function(){
  var pg=document.getElementById('pinGroups'); if(!pg)return;
  of('/api/pinout?dev='+D).then(function(r){return r.json();}).then(function(p){
   if(!p||!p.ok)return;
   var d=document.createElement('div'); d.style.margin='6px 0';
   var why=p.why?(' <span class="mini" style="color:var(--mut)">'+p.why+'</span>'):'';
   // A guess says so, in the warning colour, right next to the picture. A
   // diagram presented as certain when it is not is worse than none at all.
   if(p.sure===false)why=' <span class="mini" style="color:var(--warn)">'+p.why+'</span>';
   d.innerHTML='<a href="'+p.url+'" target="_blank" style="color:var(--acc)">\\uD83D\\uDCCD open pinout</a>'+why+
    ' <img src="'+p.url+'" alt="pin map" style="display:block;max-width:100%;margin-top:6px;border:1px solid var(--line);border-radius:8px">';
   pg.parentNode.insertBefore(d, pg);
  }).catch(function(){});
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


def is_self(ip: str) -> bool:
    """Is this address THIS PC?

    Every address in 127.0.0.0/8 is loopback, not just 127.0.0.1 — so
    `hub:127.0.0.2/...` forwards straight back to us and is served as if it came
    from a peer. Harmless but wasteful, and it makes a hop appear where there is
    none. `localhost` and our own LAN address count too.
    """
    ip = (ip or "").strip().split(":")[0]
    if not ip:
        return False
    if ip == "localhost" or ip.startswith("127."):
        return True
    return ip == lan_ip()


# Studio's settings, shared from this PC so another one can pull them over the
# network. Sits with the other user data, not in the code.
SETTINGS_FILE = STUDIO / "settings_shared.json"



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


# Hubs somebody typed in, because a sweep cannot reach them. Data in a file,
# not a constant: the whole point is that it changes without editing code.
KNOWN_HUBS = HERE / "known_hubs.json"


def known_hubs():
    """Addresses a person added by hand, newest last."""
    try:
        d = json.loads(KNOWN_HUBS.read_text(encoding="utf-8"))
        return [str(x) for x in (d.get("hubs") or []) if str(x).strip()]
    except (OSError, ValueError):
        return []


def remember_hub(ip, forget=False):
    """Add or drop a typed-in hub. Returns the list as it now stands."""
    ip = (ip or "").strip()
    if not re.match(r"^[A-Za-z0-9._-]+(:\d+)?$", ip):
        raise ValueError("that is not an address")
    have = [h for h in known_hubs() if h != ip]
    if not forget:
        have.append(ip)
    KNOWN_HUBS.write_text(json.dumps({"hubs": have}, indent=1),
                          encoding="utf-8")
    HUBS.forget()                      # so the next ask really looks
    return have


def scan_hubs(force=False):
    """Other PCs running the hub: found by sweeping, or named by a person.

    The sweep only ever covers THIS PC's own /24, and that is not a bug to fix
    with a wider sweep - 254 addresses already take seconds, and the case that
    matters is not a bigger subnet but a DIFFERENT one. Measured on 2026-08-19:
    two PCs on one venue WiFi, 10.126.226.203 and 10.123.98.148, could reach
    each other perfectly over TCP and neither could ever discover the other,
    because no sweep of one /24 contains the other. mDNS cannot bridge it
    either: multicast is link-local by design.

    So an address a person types is not a fallback here, it is the answer - and
    it is remembered, so it is typed once.
    """
    return HUBS.find(lan_ip(), force, also_ask=known_hubs())


# ---------------------------------------------------------------- discovery


def hub_header():
    """Who this hub is, for the board to remember.

    A board's own website has no way back to the hub otherwise: several PCs at
    a venue run this same program, the addresses move with the network, and a
    link to the wrong one is worse than none. So the hub says who it is on
    every request it makes, and the board offers the way back only while that
    is still true. One place, so the two callers cannot disagree.
    """
    return {"X-Mice-Hub": "%s:%d" % (lan_ip(), PORT)}


def probe_module(ip: str, timeout=0.6):
    """GET /api/status - returns module info dict or None."""
    try:
        req = urllib.request.Request("http://%s/api/status" % ip,
                                     headers=hub_header())
        with urllib.request.urlopen(req, timeout=timeout) as r:
            st = json.loads(r.read().decode())
        if "type" in st and "id" in st:
            return {"ip": ip, "id": st.get("id"), "name": st.get("name", ip),
                    "type": st.get("type", "?"), "sd": st.get("sd", False),
                    # which installation it belongs to — the Network tab shows
                    # this, and it is the whole point of the linking screen
                    "group": st.get("group", ""),
                    # Bench 2026-08-26: dropping the chip keyed one board as
                    # two - cable route under its MAC, WiFi route under
                    # id+type - so the page drew a row per way in.
                    "chip": st.get("chip", "")}
    except Exception:
        pass
    return None


def _probe_patiently(ip):
    """Same probe, but give a module that is KNOWN to exist real time to answer."""
    return probe_module(ip, timeout=2.0)


# The two things this hub looks for. Each is ONE line plus the question it
# asks; the sweeping, the thread pool and the shelf life live in discovery.py
# so a fix reaches both. Adding a third kind of thing is another line here.
# Passed as small wrappers, not as the functions themselves, so the probe is
# looked up WHEN IT RUNS. Handing over probe_module directly binds whatever
# that name meant at import time, and then replacing main.probe_module — which
# is how the QC checks stand in a module that answers slowly, and how anyone
# would try it — silently changes nothing.
# Two speeds, on purpose. Sweeping 254 addresses has to be quick, so the
# ordinary probe waits 0.7 s. An address a PERSON named is different: there is
# one of it, it is known to exist, and the machine at the other end may be busy
# with its own scan - measured 2026-08-19, a hub on another subnet answered in
# 0.03 s when idle and missed the 0.7 s window while scanning its cables, so it
# appeared and disappeared between two refreshes.
# The grace periods are why a row does not blink on a bad link: a thing that
# misses a sweep stays listed, marked late, for this long. Modules get longer
# than hubs because a module on WiFi time-slices between the show network and
# its own hotspot and is the likelier of the two to answer late.
HUBS = discovery.Finder("hubs", lambda ip: probe_hub(ip),
                        patient=lambda ip: probe_hub(ip, timeout=5.0),
                        ttl=20, skip_self=True, grace=90)
MODULES = discovery.Finder("modules", lambda ip: probe_module(ip),
                           patient=lambda ip: _probe_patiently(ip),
                           ttl=10, key=lambda m: m["id"], grace=45)


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
    """Every module board this PC can see on the network.

    Why a second, patient pass exists, and why it is not limited to this
    subnet, is written down in discovery.Finder — it came from a measured
    fault, not a theory, and it must not be tidied away.

    Addresses learned over a CABLE are handed in as well: a board reports its
    own IP, so plugging one in is enough to find it on WiFi afterwards, even
    on a subnet this PC cannot sweep.
    """
    return MODULES.find(lan_ip(), force, also_ask=_ips_from_usb())


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
            # A FRESH HANDLE MAY HAVE JUST RESET THE BOARD. Opening a port
            # toggles the control lines on some adapters however carefully DTR
            # and RTS are cleared first - measured on an FTDI adapter at the
            # bench, 2026-08-20. Let whatever the board says on the way up land
            # here, once, rather than in the middle of the first reply.
            #
            # THE CAP IS NOT OPTIONAL. Every arriving byte pushes `quiet`
            # forward, so a board that never stops talking pushed it forever
            # and this loop never ended - and because the scan walks every
            # port in turn, ONE noisy board hung the whole module list, not
            # just its own cable. Measured on the bench 2026-08-21: a wedged
            # board on COM26 sent 23,395 lines in three seconds and a probe
            # of six ports never returned. No fake had ever flooded, so 3120
            # passing checks said nothing about it.
            #
            # Both clocks start NOW, so 4 s is the TOTAL, not four seconds
            # after the settle: a quiet board is done in 1.2 s and a talking
            # one is cut off at 4. The cost of the cut is small and known - a
            # board still printing boot lines at 4 s has its INFO reply read
            # out of the noise, which works because a reply is identified by
            # the blank line in front of it, and at worst it is found on the
            # next scan instead of this one.
            quiet = time.time() + 1.2
            hard = time.time() + 4.0
            while time.time() < quiet and time.time() < hard:
                if ser.in_waiting:
                    ser.read(ser.in_waiting)
                    quiet = time.time() + 0.25   # still talking; wait again
                else:
                    time.sleep(0.03)
        except Exception as e:  # noqa: BLE001
            raise OSError(usb_busy_hint(port, e))
        ent["ser"] = ser
        ent["last"] = time.time()
        return ent


def usb_close(port=None):
    """Close cables and say which ones really closed.

    The return value matters: a port somebody is mid-command on is deliberately
    NOT closed (see below), and the caller has to be able to tell. The flasher
    could not - it called this, slept 300ms and ran esptool into a handle that
    was still open, which fails at whatever percent it happens to reach and
    leaves the board sitting in the bootloader. Measured at the bench
    2026-08-20: 21%, "the chip stopped responding", and the same flash from a
    command line with the hub stopped worked first try.
    """
    with _usb_mgr_lock:
        ports = [port] if port else list(_usb_open)
        ents = [(p, _usb_open.pop(p)) for p in ports if p in _usb_open]
    shut = []
    for p_name, ent in ents:
        # take the port's own lock first: never close the handle out from
        # under a command that is mid read/write on it
        got = ent["lock"].acquire(timeout=3)
        if not got:
            # Something is STILL mid read/write on this handle after 3 s — a
            # @peer command waits up to 8. Closing anyway pulled the handle out
            # from under it, which on Windows surfaces as a ClearCommError in
            # the reader or a hang. Put the port back and let the next sweep
            # take it; a cable held open a little longer is not a problem, a
            # command dying mid-flight is.
            with _usb_mgr_lock:
                _usb_open.setdefault(p_name, ent)
            continue
        try:
            if ent["ser"] is not None:
                ent["ser"].close()
            shut.append(p_name)
        except Exception:
            pass
        finally:
            ent["lock"].release()
    return shut


def usb_free(port):
    """True when this hub holds no handle on that cable.

    What the flasher actually needs to know. `usb_close` returning is not the
    same as the port being free: a port it could not lock is put back on
    purpose, and esptool then meets a handle that is still open.
    """
    with _usb_mgr_lock:
        return port not in _usb_open


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
            # Look again, immediately before closing. The list above was taken
            # seconds ago and usb_close then waits for the port's own lock, so
            # a command that arrived in between would finish and have its cable
            # shut the instant it let go — the next command failing on a closed
            # port for no reason the user could see.
            with _usb_mgr_lock:
                ent = _usb_open.get(p)
                still_idle = ent and time.time() - ent["last"] > USB_IDLE_CLOSE
            if still_idle and not usb_in_use(p):
                usb_close(p)


# A firmware log line is a bracket tag: "[wifi]", "[sd]", "[  1234][I]" ... —
# only letters/digits/spaces inside the brackets. A JSON reply that starts with
# "[" is always "[{" / "[\"" / "[[" / "[<num>," so it never matches this.
_LOG_LINE = re.compile(r"^\[[\w ]*\]")

# A BOARD THAT JUST REBOOTED, mid-conversation. Opening the port resets some
# boards - measured at the bench 2026-08-20 on an FTDI adapter, where the ESP32
# came up with `ets Jul 29 2019` and `rst:0x1 (POWERON_RESET)` while the hub was
# waiting for a reply. The first-stage ROM log is printed at a different rate
# from the firmware's 115200, so it arrives as NUL bytes and fragments - and
# usb_cmd handed that back as the answer.
#
# That is what made a camera look like a corrupted RS485 module for an hour: the
# same board read DIRECTLY, once the boot log had finished, answered ten times
# out of ten with not one byte lost.
_BOOT_NOISE = re.compile(r"ets [A-Z][a-z]{2} +\d|rst:0x|boot:0x|"
                         r"configsip:|clk_drv:|Brownout detector")


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
        rebooted = [False]      # the board restarted while we were waiting
        boots = [0]             # how many times — more than one is a boot LOOP
        brownout = [False]      # and whether the board said why
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
            while (chr(10).encode()) in buf:
                ln, buf = buf.split(chr(10).encode(), 1)
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
                # Boot output is not an answer. It also means the board has
                # just restarted, so whatever we asked never reached the
                # firmware - the caller gets a timeout and can ask again,
                # rather than a reply built out of a reset.
                if _BOOT_NOISE.search(t):
                    rebooted[0] = True
                    # ONE reset is a coincidence; four in eight seconds is a
                    # power fault. `rst:0x` is printed exactly once per boot, so
                    # counting it separates the two - and they have completely
                    # different fixes, which is the whole point of telling them
                    # apart. Measured on the bench 2026-08-20: a 30-pin board
                    # with a MAX485 attached rebooted every 1.6 s and the hub
                    # called it "no reply", which sent an afternoon into
                    # checking bus wiring that was never wrong.
                    if "rst:0x" in t:
                        boots[0] += 1
                    if "Brownout" in t:
                        brownout[0] = True
                    saw_blank = False
                    continue
                # A LINE WITH NUL BYTES IN IT IS NEVER AN ANSWER.
                #
                # _BOOT_NOISE matches clean ASCII, and the whole reason this
                # exists is that the ROM log arrives at ANOTHER BAUD - so it
                # arrives as NULs and fragments, and a garbled boot line
                # matches none of the patterns above. It then became `fallback`
                # and was handed back as the reply, which is precisely the bug
                # the boot-noise work was written to stop, surviving in the one
                # form it takes most often. Found by a model review 2026-08-20.
                #
                # Nothing the firmware sends contains a NUL: every reply is one
                # line of text written in one call (see main.cpp emitLine), so
                # this cannot throw away a real answer.
                if "\x00" in t:
                    rebooted[0] = True
                    saw_blank = False
                    continue
                if not saw_blank:
                    # A BUS REPLY CARRIES ITS OWN MARKER, and needs no blank
                    # line in front of it. `@<id> ` IS the RS485 frame format,
                    # so it identifies a reply at least as surely as the blank
                    # line does — an orphaned log tail cannot start with it.
                    #
                    # This matters for a plain USB-RS485 dongle, where there is
                    # no board on the cable to re-emit the frame. A bridging
                    # board wraps what it heard on the bus in the usual
                    # "\n<reply>\n" (main.cpp's rs485.onBusLine → emitLine); a
                    # dongle is just wire, and the frame arrives raw. Measured
                    # 2026-08-20: `#1 PING` through a dongle answered
                    # `@1 PONG 1 lift lift` on the wire, and the hub reported
                    # "no reply from COM23 (bus id 1)" — it had read the answer
                    # and thrown it away.
                    if want and t.startswith(want):
                        return t[len(want):]
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
        if fallback is not None and not want and not rebooted[0]:
            return fallback          # older firmware: no blank-line marker
        # SAY THAT IT REBOOTED. "no reply" sends somebody looking at wiring; a
        # board that restarted mid-command is a different problem with a
        # different fix, and the hub can see the difference in the boot log it
        # just read.
        # A BOOT LOOP IS NOT A SLOW BOARD. Three different failures, three
        # different next steps, and the hub can tell them apart from the boot
        # log it just read - so it should, rather than making somebody take a
        # meter to the bus to find out.
        if brownout[0] or boots[0] > 1:
            raise TimeoutError(
                "%s is restarting over and over - %d times while waiting%s. "
                "The board resets before it can answer anything, so this is a "
                "POWER fault, not wiring and not the bus. Check that the RS485 "
                "transceiver is fed from 5V/VIN rather than 3.3V, and that the "
                "USB port can supply the current spike when the radio starts."
                % (port, boots[0],
                   ", saying 'Brownout detector was triggered'"
                   if brownout[0] else ""))
        raise TimeoutError(
            ("%s restarted while answering - the command never reached the "
             "firmware. Ask again." % port) if rebooted[0] else
            ("no reply from " + port +
             ((" (bus id %d)" % bus_id) if bus_id else "")))


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
def split_hub_dev(dev):
    """`hub:<ip>/<inner dev>` -> (ip, inner), else (None, dev).

    How a module on ANOTHER PC's cable is addressed. At a venue that is the
    normal case: one laptop by the arm, one at the desk, and the arm reachable
    only from whichever machine holds the cable.

    The inner part is an ordinary dev string, and the PC named by <ip> is the
    one that finally opens the port. Ownership never moves — that hub is still
    the single owner of its own cables, which is exactly what makes forwarding
    safe rather than a second program fighting for the same serial handle.
    """
    if not dev.startswith("hub:"):
        return None, dev
    rest = dev[4:]
    if "/" not in rest:
        raise ValueError("bad dev (use hub:<ip>/<dev>)")
    ip, inner = rest.split("/", 1)
    if not ip or not inner:
        raise ValueError("bad dev (use hub:<ip>/<dev>)")
    # A forwarded dev may never be forwarded again. Two hubs that each list the
    # other could otherwise bounce one command back and forth until both ran
    # out of request threads.
    if inner.startswith("hub:"):
        raise ValueError("a module on another PC cannot be reached through a third PC")
    return ip, inner


def parse_dev(dev):
    peer = ""
    ip, dev = split_hub_dev(dev)
    if ip:
        raise ValueError("hub: addresses are forwarded whole, not parsed here")
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

# Boards gate what CHANGES over WiFi (A1-1): /api/cmd answers
# `401 ERR log in first` to anyone without a session. Found on the bench
# 2026-08-26: POSE over USB worked while the same POSE over WiFi was refused,
# because only the OTA path ever logged in. The hub logs in once per board and
# reuses that session for its commands; cookies stay in this process's memory.
BOARD_COOKIE = "mice_board"
SHIPPED_BOARD_LOGIN = ("admin", "admin123")   # UserStore.cpp, a board out of the box
_board_cookies = {}                           # board ip -> session value


def board_login(ip, user="", password=""):
    """Log in to a board's own web login. -> (cookie, why); why is for a person."""
    who, pwd = (user, password) if (user or password) else SHIPPED_BOARD_LOGIN
    body = urllib.parse.urlencode({"user": who, "pass": pwd}).encode()
    req = urllib.request.Request(
        "http://%s/api/login" % ip, data=body, method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            for part in (r.headers.get("Set-Cookie") or "").split(";"):
                k, _, v = part.strip().partition("=")
                if k == BOARD_COOKIE and v:
                    return v, None
        return "", "%s let the login through but sent no session" % ip
    except urllib.error.HTTPError as e:
        if e.code == 401:
            return "", (
                "%s refused the login for \"%s\". A board keeps its OWN "
                "accounts: give the one set on that board, or set it back "
                "to the shipped login on its own page." % (ip, who))
        if e.code == 404:
            # A BOARD TOO OLD TO HAVE A LOGIN. Its gates are absent entirely,
            # so it still takes commands - and it is exactly the board that
            # most needs updating. Refusing here would strand every board
            # built before the auth work on whatever firmware it has.
            return "", ""
        return "", "%s answered %d to the login" % (ip, e.code)
    except Exception as e:                      # noqa: BLE001
        return "", "cannot reach %s to log in (%s)" % (ip, type(e).__name__)


def dev_cmd(dev, c, wait=None):
    """One command to a module, over whatever link its `dev` names.

    `wait` is for the rare command that takes the board a long time to answer.
    FWEND is the case that forced it: the board checks the md5 of a 1.3 MB image
    before it will boot into it, and that is many seconds of work — far past the
    2 s a POSE or a PING needs. Timing that out would report a FAILED update for
    one that actually succeeded, which is the worst of the possible wrong
    answers: the operator reflashes a board that was already fine.
    """
    kind, addr, bus, peer = parse_dev(dev)
    if kind == "wifi":
        # A FORWARDED COMMAND IS TWO HOPS ON EVERY TRANSPORT, not just USB.
        # PEER_WAIT was applied only on the cable path, so `wifi:<ip>@<peer>`
        # got the ordinary 6 s while `usb:<port>@<peer>` got the longer budget
        # — for exactly the same journey: over the link, through the module,
        # onto its hotspot, and back. Found by a model review 2026-08-20 and
        # confirmed by reading both branches.
        return Handler.robot_get(
            addr, "/api/cmd?c=" + urllib.parse.quote(_via(c, peer)),
            timeout=wait or (PEER_WAIT if peer else None)).decode(errors="replace")
    return usb_cmd(addr, _via(c, peer), bus,
                   wait=wait or (PEER_WAIT if peer else 2.0))


def pinout_for(dev):
    """Which pin diagram is right for the board on the other end of `dev`.

    Decided HERE rather than in the page, because the page would have to know
    the difference between a camera and an arm, guess a board name, and get it
    wrong quietly. One question, one answer, one place to fix it.

    A camera is asked which board it is - it already knows, from the pin map
    that let its sensor answer at all. If it cannot say, the commonest clone is
    offered WITH a note saying it was a guess: a diagram presented as certain
    when it is not is worse than no diagram, because somebody wires to it.
    """
    kind = ""
    for m in modules_here():
        for r in m.get("routes", []):
            if r.get("dev") == dev:
                kind = (m.get("type") or "").lower()
                break
    if kind and kind != "cam":
        return {"url": "/pinout.svg", "board": "", "sure": True,
                "why": "38-pin ESP32 WROOM, which is what a %s runs on" % kind}

    board, sure = "", False
    try:
        reply = dev_cmd(dev, "CAM") or ""
        m = re.search(r"board=([a-z0-9-]+)", reply)
        if m and m.group(1) in cam_boards():
            board, sure = m.group(1), True
    except Exception:                                        # noqa: BLE001
        pass                          # offline, or not a camera after all
    if not board:
        if kind != "cam":
            # Not a camera and not identified: the general reference is still
            # the honest answer, since every non-camera board here is a WROOM.
            return {"url": "/pinout.svg", "board": "", "sure": True,
                    "why": "38-pin ESP32 WROOM"}
        board = "ai-thinker"
    b = cam_boards().get(board) or {}
    return {"url": "/pinout.svg?board=" + board, "board": board, "sure": sure,
            "why": (b.get("label") or board) if sure else
                   "guessed %s - the board did not say which it is"
                   % (b.get("label") or board)}


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
        if r == "EOF":
            break
        if r.startswith("ERR"):
            # Serving the bytes read so far would hand back a truncated file
            # that looks complete - the route's handler turns this into a
            # visible error instead.
            raise RuntimeError("download of %s stopped: %s" % (name, r))
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
        return _robot_post(addr, "/api/upload?dir=" + urllib.parse.quote(dirp),
                           body, "multipart/form-data; boundary=" + boundary,
                           timeout=20).decode(errors="replace")
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
_CUE_CMDS = {}


def cue_cmds():
    """Step key -> the command line it becomes, e.g. {'play': 'PLAY'}.

    Read from firmware/config/commands.json, the SAME data the firmware's own
    step table is generated from (gen_tables.gen_seqsteps), so a new step key
    costs no hub code. MOTION commands are left out on purpose: while the hub
    is the clock, a step that moves the robot would be a second clock, and
    that is the one rule check_one_player exists to hold. Without a registry
    (a build with no config folder) the map is empty and non-pose steps are
    skipped, which is what the hub did before A24-22.
    """
    if not _CUE_CMDS and registry:
        for c in registry.commands():
            if c.get("motion"):
                continue
            for st in c.get("steps") or []:
                key = str(st.get("key") or "").lower()
                if key:
                    _CUE_CMDS[key] = c["name"] + (
                        (" " + st["sub"]) if st.get("sub") else "")
    return _CUE_CMDS


def cue_lines(cues):
    """Sequence step lines (`play: song.mp3`) -> the commands to send.

    Anything the map does not name is dropped here: a motion step (the hub is
    the clock) and a key this board's firmware does not carry both play only
    from the module's own SD card, exactly as before A24-22.
    """
    out = []
    for line in cues or []:
        key, _, val = str(line).partition(":")
        cmd = cue_cmds().get(key.strip().lower())
        if cmd:
            out.append((cmd + " " + val.strip().strip('"')).strip())
    return out


def seq_steps(text):
    """A saved-show yaml (the bytes /api/loadseq serves) -> play steps.

    One parser, hub-side, so every caller gets identical timing. It mirrors
    what Studio's parseSeqYaml and the firmware agree on: a pose line may
    carry an explicit `T <ms>`; `wait` becomes the previous step's hold; a
    `speed` step sets deg/s for the moves after it; an OLD arms-only pose
    has 8 values and pads to 10 with neutral 90s. Exports always carry T,
    so the computed-T path is for hand-written files only - it is the
    firmware rule, max joint delta over deg/s with the same 80 ms floor.
    Chains (`next:`) are returned but NEVER followed: one answer plays one
    sequence.
    """
    steps, loop = [], False
    cur_speed, seq_speed = 0.0, 0.0
    name, nxt = "", ""
    pending = []                          # cues waiting for the next keyframe
    for raw in text.splitlines():
        s = re.sub(r"#.*$", "", raw).strip()
        m = re.match(r"^name:\s*(.+)$", s)
        if m:
            name = m.group(1).strip()
            continue
        m = re.match(r"^next:\s*(.+)$", s)
        if m:
            nxt = m.group(1).strip()
            continue
        m = re.match(r"^loop:\s*(true|false)", s)
        if m:
            loop = m.group(1) == "true"
            continue
        m = re.match(r"^-\s*speed:\s*([\d.]+)", s)
        if m:
            cur_speed = float(m.group(1))
            if not seq_speed:
                seq_speed = cur_speed
            continue
        m = re.match(r"^-\s*wait:\s*(\d+)", s)
        if m:
            if steps:
                steps[-1]["hold"] = int(m.group(1))
            continue
        m = re.match(r'^-\s*pose:\s*"?([\d.\s]+?)(?:\s+T\s+(\d+))?"?\s*$', s)
        if not m:
            # A non-pose step (`play:`, `vol:`, `rgb:`) is a CUE: it fires when
            # the show reaches this line, exactly where the module's own player
            # would run it. Until A24-22 they were dropped here, so the same
            # file played silently from the hub and with music from the SD card.
            m = re.match(r'^-\s*([A-Za-z_][\w-]*):\s*"?(.*?)"?\s*$', s)
            if m:
                # kept as the FILE's own words (`play: song.mp3`), not as a
                # command: which command a key becomes is decided in one place,
                # ShowPlayer.start, and an editor that round-trips the file
                # then carries steps it does not itself understand.
                pending.append(("%s: %s" % (m.group(1).lower(),
                                            m.group(2))).strip())
            continue                      # unknown keys still play only from
                                          # the module's own SD card
        nums = [float(v) for v in m.group(1).split()]
        if len(nums) == 8:
            nums += [90.0, 90.0]          # WAIST and SHRUG at neutral
        if len(nums) != 10:
            raise ValueError("a pose needs 8 or 10 joints, got %d"
                             % len(nums))
        t = int(m.group(2) or 0)
        if not t:
            if not steps:
                t = 1000                  # time to reach the start pose
            else:
                prev = steps[-1]["pose"]
                delta = max(abs(a - b) for a, b in zip(prev, nums))
                t = max(ShowPlayer.MIN_T,
                        int(delta / (cur_speed or seq_speed or 60.0) * 1000))
        steps.append({"pose": nums, "t": t, "hold": 0, "cues": pending})
        pending = []
    if steps and pending:
        # cues after the last keyframe: they fire when the show ends
        steps[-1]["cues_after"] = pending
    return {"name": name, "next": nxt, "loop": loop, "steps": steps}


class ShowPlayer:
    """One player per hub. Runs a sequence on a real thread, at real times."""

    TICK = 0.02          # how often the thread wakes to check the clock / stop
    MIN_T = 80           # ms, the same floor the firmware and Studio use

    def __init__(self):
        self.lock = threading.Lock()
        # Held across stop-then-start, so two callers cannot each find
        # nothing to stop and each spawn a clock. Separate from `lock`,
        # which the running thread takes constantly - holding that one
        # across a join would deadlock.
        self._starting = threading.Lock()
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
                  "hold": max(0, int(s.get("hold", 0))),
                  # cues travel through the API as the file's own step lines
                  # (`play: song.mp3`), so an editor can carry steps it does
                  # not understand; they become commands here, once.
                  "cues": cue_lines(s.get("cues")),
                  "cues_after": cue_lines(s.get("cues_after"))}
                 for s in steps]
        if len(steps) < 2:
            raise ValueError("a show needs at least two keyframes")
        for s in steps:
            if len(s["pose"]) != 10:
                raise ValueError("every keyframe needs 10 joint angles")
        # STOP AND CLAIM UNDER ONE LOCK. stop() read self.thread outside it, so
        # two POSTs for the same robot could each find nothing to stop and each
        # spawn a clock - two threads sending POSE to one arm, which is the
        # exact fault check_takeover exists to prevent and could never see.
        # Found 2026-08-21.
        with self._starting:
            self.stop()
            with self.lock:
                self.dev, self.steps, self.loop, self.name = dev, steps, bool(loop), name
                self.total_ms = self.total(steps)
                self.at_ms = max(0, min(int(from_ms), self.total_ms))
                self.step, self.last, self.error = -1, "", ""
                self.started_at = time.time()
            # A FRESH EVENT PER RUN. stop_flag is how the old clock hears
            # "stop"; clearing one shared event here would also release a run
            # whose thread stop() gave up waiting for - and two clocks would
            # play one arm. The old thread keeps the old, SET event.
            flag = threading.Event()
            self.stop_flag = flag
            self.thread = threading.Thread(target=self._run, args=(flag,),
                                           daemon=True)
            self.thread.start()
            return self.status()

    def stop(self, freeze=True, why=""):
        """Stop playing. `freeze` also tells the module to hold where it is."""
        th = self.thread
        if th and th.is_alive():
            self.stop_flag.set()
            th.join(timeout=3.0)
            if th.is_alive():
                # Its OWN event is set, so it exits at its next wake-up even
                # though we stopped waiting - but say so; silence would read
                # as stopped when a command is still in flight.
                with self.lock:
                    self.error = "the previous show was still finishing"
            if freeze:
                try:
                    self._say("STOP")
                except Exception as e:      # noqa: BLE001 - a dead cable must
                    self.error = str(e)     # not stop us from marking it stopped
            if self._had_music():
                # A24-18 made the board's own STOP silence the speaker, but the
                # show is stopped here on boards that may still be older, and
                # stopall stops without freezing at all. Music over a robot that
                # has already frozen is what a panic stop must never leave.
                try:
                    self._say("PLAY STOP")
                except Exception:           # noqa: BLE001
                    pass
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

    def _sleep(self, flag, seconds):
        """Wait, but wake up immediately when someone presses stop."""
        return not flag.wait(max(0.0, seconds))

    def _run(self, flag):
        try:
            # Take the robot: a module playing its own sequence would otherwise
            # be a second clock. Newer firmware also does this by itself when
            # the first POSE arrives; saying it explicitly keeps older boards
            # right and makes the intent visible on the wire.
            self._say("MOVE STOP")
            while True:
                if not self._play_once(flag):
                    return
                if not self.loop:
                    return
                with self.lock:
                    self.at_ms = 0
        except Exception as e:              # noqa: BLE001
            with self.lock:
                self.error = str(e)

    def _play_once(self, flag):
        """One pass through the steps, from self.at_ms. False = stopped."""
        # where in the show at_ms lands: which step, and how much of it is left
        start_i, into = 1, 0
        clock = self.steps[0].get("hold", 0)
        at = self.at_ms
        if at <= clock:
            # still at (or before) the start pose — put the robot on it first
            t = max(self.MIN_T, self.steps[0].get("t", 0) or self.MIN_T)
            if flag.is_set():
                return False
            self._mark(0, at)
            self._cues(self.steps[0])
            self._say(self._pose_cmd(self.steps[0]["pose"], t))
            if not self._sleep(flag, t / 1000.0):
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
            if flag.is_set():
                return False
            self._mark(i, self._elapsed_to(i))
            self._cues(s)
            self._say(self._pose_cmd(s["pose"], left))
            if not self._sleep(flag, left / 1000.0):
                return False
            if s["hold"]:
                if not self._sleep(flag, s["hold"] / 1000.0):
                    return False
        self._mark(len(self.steps) - 1, self.total_ms)
        for c in self.steps[-1].get("cues_after") or []:
            self._say(c)
        return True

    def _had_music(self):
        """Did this show start any audio? Only then is PLAY STOP worth sending
        - a board with no speaker answers ERR, and that would be the last thing
        the status line said about a stop that worked."""
        with self.lock:
            steps = list(self.steps)
        return any(c.startswith("PLAY") and not c.upper().startswith("PLAY STOP")
                   for s in steps
                   for c in (s.get("cues") or []) + (s.get("cues_after") or []))

    def _cues(self, step):
        """Fire this keyframe's cues (PLAY, VOL, RGB) before its move starts.

        A cue never blocks the clock: it is sent and the move goes out behind
        it, so music that fails to start cannot freeze the show. Cues on steps
        a resume SKIPPED are not fired - a module cannot seek inside an mp3,
        so restarting the track from the top would be worse than silence.
        """
        for c in step.get("cues") or []:
            try:
                self._say(c)
            except Exception as e:          # noqa: BLE001
                with self.lock:
                    self.error = "cue %s: %s" % (c, e)

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
# One sender per hub, like the show clock: two things streaming to one
# board would interleave datagrams into noise.
streamer = stream_audio.Sender()

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
FIRMWARE_DIR = DATA / "firmware"
BOOT_APP0 = (PIO_HOME / "packages" / "framework-arduinoespressif32" /
             "tools" / "partitions" / "boot_app0.bin")

# offset -> which file, exactly as PlatformIO's own upload does it
FLASH_PARTS = (("0x1000", "bootloader.bin"), ("0x8000", "partitions.bin"),
               ("0xe000", None), ("0x10000", "firmware.bin"))  # None = boot_app0

# How much of an unwanted request body the hub will swallow to be polite
# about the reason it is refusing. 4 MB is more than any page here posts.
DRAIN_LIMIT = 4 * 1048576

# The name this hub answers to on the local network. One place, so the page,
# the console banner and the responder cannot disagree about it.
MDNS_NAME = "mice.local"
NAME_SERVER = [None]

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
    # TWO kinds of ready, because the two ways of writing a board need
    # different things. A cable write runs esptool and needs every part - the
    # bootloader and the partition table included. An OTA sends ONE file, the
    # app image, because that is all a running board can accept. A PC that was
    # handed firmware.bin (rather than building it) can do the second and not
    # the first, and that is a normal, useful state - it was reported as
    # "nothing built here" until 2026-08-19.
    app = any(q.endswith("firmware.bin") for _off, q in parts)
    return {"type": module_type, "env": env, "dir": str(d),
            "ready": not missing, "ota_ready": app,
            "missing": missing, "parts": parts,
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


def pair_with(to, code, replace=False):
    """Take the accounts from the hub showing `code` (A14-1).

    THIS hub asks, not the browser: a POST from the page straight to another
    hub carries no cookie (SameSite=Lax), the same reason send_firmware works
    this way. Nothing is kept afterwards — the accounts are copied once and
    the two hubs never need each other again, which is what makes this work at
    a venue with no internet and a network that drops.
    """
    to = (to or "").strip()
    if not to:
        raise ValueError("which PC? name the one showing the code")

    # A Replace is the SECOND half of one decision, so it spends no second
    # code: the accounts fetched a moment ago are still held here. Walking
    # back to the other PC for a new code would ask the person to prove
    # something they just proved.
    who, accounts = PAIR_PENDING.get(to) if replace else (None, None)
    if accounts is None:
        if len(hub_pair.normalise(code)) != hub_pair.CODE_LEN:
            raise ValueError("type the whole code shown on the other PC")
        answer = claim_accounts(to, code)
        who = answer.get("host") or to
        accounts = answer.get("accounts") or {}
        PAIR_PENDING.hold(to, who, accounts)
    out = auth().import_accounts(accounts, replace=replace)
    auth().note_paired(who, out["added"] + out["replaced"])
    if out["added"] or out["replaced"]:
        try:                 # two PCs that share accounts are one installation
            remember_hub(to)
        except (OSError, ValueError):
            pass
    if not out["clashed"]:                   # nothing left to decide about
        PAIR_PENDING.drop(to)
    out.update({"from": who, "users": auth().users()})
    return out


def claim_accounts(to, code):
    """Spend the code on the far hub and bring back what it hands over."""
    req = urllib.request.Request(
        "http://%s:%d/api/pair/claim" % (to, PORT), method="POST",
        data=json.dumps({"code": code}).encode(),
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read().decode(errors="replace"))
    except urllib.error.HTTPError as e:
        # Say what the OTHER PC said: a wrong code and no code being shown at
        # all need different actions from the person standing here.
        why = ""
        try:
            why = (json.loads(e.read().decode(errors="replace")) or {}).get("error", "")
        except Exception:                     # noqa: BLE001 - a reason is a bonus
            pass
        raise RuntimeError(why or ("%s refused that code" % to)) from e
    except Exception as e:                    # noqa: BLE001
        raise RuntimeError("cannot reach %s (%s)" % (to, type(e).__name__)) from e


def send_firmware(to, port, module_type, user, password):
    """Give this PC's firmware to the hub holding the cable, and let it write.

    The image travels; the command does not. This hub does the sending rather
    than the browser because the session cookie is SameSite=Lax: a POST from
    this page straight to another hub carries no cookie and is refused.

    It logs in as the operator each time and keeps nothing. A hub never stores
    another hub's password — the person typing it is the one authorised on
    that machine, and that is the whole point of the gate.
    """
    import base64
    if not to:
        raise ValueError("which PC? name the hub holding the cable")
    im = flash_image(module_type)
    if not im["ready"]:
        raise RuntimeError(
            "no %s firmware on THIS PC to send (missing %s). Build it first: "
            "pio run -e %s" % (module_type, ", ".join(im["missing"]), im["env"]))
    payload = {"port": port, "type": module_type, "from": socket.gethostname(),
               "parts": [{"off": off, "name": Path(p).name,
                          "b64": base64.b64encode(Path(p).read_bytes()).decode()}
                         for off, p in im["parts"]]}

    base = "http://%s:%d" % (to, PORT)
    cookie = ""
    if user or password:
        req = urllib.request.Request(
            base + "/api/login", method="POST",
            data=json.dumps({"user": user, "password": password}).encode(),
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as r:
            answer = json.loads(r.read().decode(errors="replace"))
            if not answer.get("ok"):
                raise RuntimeError("%s refused that login" % to)
            cookie = (r.headers.get("Set-Cookie") or "").split(";")[0]

    req = urllib.request.Request(
        base + "/api/flash/remote", method="POST",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json",
                 **({"Cookie": cookie} if cookie else {})})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            out = json.loads(r.read().decode(errors="replace"))
    except urllib.error.HTTPError as e:
        if e.code == 401:
            raise RuntimeError(
                "%s wants a login before it will overwrite a board" % to) from e
        # Say what the OTHER PC said. Without this the operator is told the
        # number 400 about a machine they are not sitting at.
        why = ""
        try:
            why = (json.loads(e.read().decode(errors="replace")) or {}).get("error", "")
        except Exception:                     # noqa: BLE001 - a reason is a bonus
            pass
        raise RuntimeError("%s refused it: %s" % (to, why or e.reason)) from e
    out["to"] = to
    out["bytes"] = im["bytes"]
    return out


def board_key(mod):
    """What makes this board THIS board.

    The chip MAC when the board reports one - it cannot be changed, so it is
    the only honest answer. Older firmware does not report it, and then the id
    is all there is: it is used, but qualified with the type, because two blank
    boards from the same box share a default id and are not the same board.

    Returns a tuple so two boards can never collide by accident of formatting.
    """
    chip = (mod.get("chip") or "").strip().upper()
    if chip:
        return ("chip", chip)
    ident = mod.get("id")
    if ident is not None:
        return ("id", str(ident), (mod.get("type") or "").lower())
    return ("addr", mod.get("dev") or mod.get("ip") or repr(mod))


def modules_here(force=False):
    """Every module this PC can reach, once each, with every way to reach it.

    The hub used to hand the page two lists and let it draw both. A board that
    is plugged in AND on the WiFi appeared twice, as two robots, with different
    controls on each row - so which row you happened to click decided whether
    the command went down the cable or over the air.
    """
    out = {}

    def add(mod, route):
        key = board_key(mod)
        seen = out.get(key)
        if not seen:
            # `stale` is deliberately NOT copied here: it belongs to the ROUTE
            # that went quiet, not to the board. A nong on a cable that also
            # missed a WiFi sweep is not late - it is in front of you.
            seen = {k: v for k, v in mod.items() if k not in ("dev", "stale",
                                                              "lastSeen")}
            seen["routes"] = []
            seen["key"] = "/".join(str(p) for p in key)
            out[key] = seen
        # A board answering on WiFi knows its own name and type better than a
        # cable probe that ran a minute ago, so later, richer answers win - but
        # never overwrite something with nothing, and NEVER from a route that
        # has gone quiet. Renaming a board (SET NAME, or the module site) is
        # answered at once on the cable while the WiFi sweep keeps handing back
        # the record it last heard, for the whole grace period: the row then
        # flips between the old name and the new one every few seconds, and
        # the person who just renamed it cannot tell which board they are
        # looking at. A late answer may still ADD a field nothing else knows.
        fresh = not mod.get("stale")
        for field in ("name", "type", "group", "fw", "ip", "id", "chip"):
            if mod.get(field) in (None, "", []):
                continue
            if not fresh and seen.get(field) not in (None, "", []):
                continue
            seen[field] = mod[field]
        if mod.get("stale"):
            route = dict(route, stale=True, lastSeen=mod.get("lastSeen"))
        if route not in seen["routes"]:
            seen["routes"].append(route)

    for u in probe_usb_all(force):
        mod = u.get("module")
        # A port with NO board of its own can still have a bus behind it - that
        # is exactly what an RS485 adapter is. Skipping the port when its direct
        # probe came back empty threw away every module on the bus, so a real
        # rig showed three boards of four and the missing one was the nong.
        # The fake never showed it: its port has both a module AND a bus.
        if mod:
            add(mod, {"kind": "usb", "dev": "usb:" + u["port"], "port": u["port"]})
        for b in (u.get("rs485") or []):
            add(b, {"kind": "rs485", "bus": b.get("id"),
                    "dev": "usb:%s:%s" % (u["port"], b.get("id")),
                    "port": u["port"]})

    for mod in scan_modules(force):
        ip = mod.get("ip")
        if not ip:
            continue
        add(mod, {"kind": "wifi", "dev": "wifi:" + ip, "ip": ip})

    # A board is late only when EVERY way in is late. One live route is enough
    # to call it present, which is the whole point of listing routes at all.
    for seen in out.values():
        rs = seen["routes"]
        if rs and all(r.get("stale") for r in rs):
            seen["stale"] = True
            ago = [r.get("lastSeen") for r in rs if r.get("lastSeen") is not None]
            seen["lastSeen"] = min(ago) if ago else None

    # A stable order, so the list does not shuffle under someone's hand between
    # two scans: named boards first, by name, then by whatever identity there is.
    return sorted(out.values(),
                  key=lambda m: ((m.get("name") or "~").lower(), str(m.get("id"))))


def remote_modules(force=False):
    """What the OTHER PCs on this network are holding. (modules, errors).

    Split out so /api/allmods and the merged list below cannot drift into two
    different ideas of what another hub is offering.
    """
    out, errs = [], []
    for h in scan_hubs(force):
        ip = h.get("ip")
        if not ip:
            continue
        try:
            with urllib.request.urlopen(
                    "http://%s:%d/api/mine" % (ip, PORT), timeout=6) as r:
                d = json.loads(r.read().decode(errors="replace"))
            host = d.get("host") or ip
            for m in (d.get("modules") or []):
                m = dict(m)
                m["dev"] = "hub:%s/%s" % (ip, m["dev"])
                m["host"] = host
                m["hostIp"] = ip
                out.append(m)
        except Exception as e:                                # noqa: BLE001
            # A laptop that has just been closed is normal. Report it per PC
            # rather than failing the whole list.
            errs.append({"ip": ip, "error": str(e)})
    return out, errs


def modules_everywhere(force=False):
    """Every module ANY hub here can reach, once each. (modules, errors).

    Asked for 2026-08-21: *the module make it list the module only once for me
    please... make it list once show which module arviable on the top*. The
    page used to draw two lists - this PC's modules, and other PCs' modules -
    so a board plugged into the laptop next door appeared in one list while the
    same board on the venue WiFi appeared in the other. One robot, two rows,
    and the row you happened to press decided which machine carried the
    command.

    Merged HERE and not in the page, because `board_key` is the answer to *is
    this the same board* and it already lives here. A copy of that rule in
    JavaScript is a second answer to the same question.

    Every way in survives as a route, each saying which PC it goes through, so
    the row can show one module and the detail under it can show all four ways
    to reach it.
    """
    mine = modules_here(force)
    here = socket.gethostname()
    out = {}
    for m in mine:
        key = board_key(m)
        m = dict(m)
        m["mine"] = True
        m["routes"] = [dict(r, host=here, mine=True) for r in (m.get("routes") or [])]
        out[key] = m

    remote, errs = remote_modules(force)
    for m in remote:
        key = board_key(m)
        route = {"kind": "hub", "dev": m.get("dev"), "host": m.get("host"),
                 "hostIp": m.get("hostIp"), "mine": False}
        seen = out.get(key)
        if not seen:
            seen = {k: v for k, v in m.items() if k not in ("dev", "host", "hostIp")}
            seen["routes"] = []
            seen["mine"] = False
            seen["key"] = "/".join(str(p) for p in key)
            out[key] = seen
        # A board this PC can reach directly is still the same board when the
        # laptop next door can reach it too - so the far route is ADDED, never
        # a second row. Never overwrite something with nothing.
        for field in ("name", "type", "group", "fw", "ip", "id", "chip"):
            if m.get(field) not in (None, "", []) and not seen.get(field):
                seen[field] = m[field]
        if route not in seen["routes"]:
            seen["routes"].append(route)

    return sorted(out.values(),
                  key=lambda m: ((m.get("name") or "~").lower(),
                                 str(m.get("id")))), errs


def esc(text):
    """Text that is safe inside SVG/XML. The labels come from a data file, and
    a data file is edited by people - an unescaped & or < there would produce a
    diagram the browser refuses to render at all."""
    return (str(text).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


CAM_BOARDS_JSON = asset("firmware", "config", "cam_boards.json")


def cam_boards():
    """Every camera board, from the file the FIRMWARE is built from.

    Not a copy. `firmware/config/cam_boards.json` becomes CamBoards.h at build
    time and is read here at run time, so a diagram cannot disagree with the
    wiring the board is actually using - which is the whole risk with a picture.
    Asked for on 2026-08-19: *make it compatable with many board sometime when i
    buy the new one maybe i don't know which hardware i got*.
    """
    try:
        import registry
        return json.loads(registry.strip_jsonc(
            CAM_BOARDS_JSON.read_text(encoding="utf-8"))).get("boards", {})
    except Exception as e:                                   # noqa: BLE001
        print("[hub] camera boards unavailable:", e)
        return {}


# The order signals are drawn in: the bus first, then the eight data lines,
# then the timing. It matches how the board is actually read rather than the
# order the struct happens to store them in.
CAM_SIGNALS = [
    ("pwdn", "power down"), ("reset", "reset"), ("xclk", "clock out"),
    ("siod", "SCCB data"), ("sioc", "SCCB clock"),
    ("y9", "data 7"), ("y8", "data 6"), ("y7", "data 5"), ("y6", "data 4"),
    ("y5", "data 3"), ("y4", "data 2"), ("y3", "data 1"), ("y2", "data 0"),
    ("vsync", "frame sync"), ("href", "line valid"), ("pclk", "pixel clock"),
]


def cam_pinout_svg(name):
    """A pin diagram for ONE camera board, drawn from its entry.

    Drawn rather than shipped, for two reasons that are not about elegance:
    a picture has to be found for every board someone might buy, and a picture
    can be wrong - this cannot, because it is rendered from the same numbers the
    firmware compiles. It is also about 3 KB rather than 133 KB, which matters
    because the WROOM reference is too big to come off board flash at all.

    Colours come from the stylesheet, not from literals, so it follows whichever
    theme the page is using - including the light one, where a diagram drawn in
    pale grey on white would be unreadable.
    """
    b = cam_boards().get(name)
    if not b:
        return None
    pins = b.get("pins", {})
    rows, y = [], 78
    for key, label in CAM_SIGNALS:
        gpio = pins.get(key)
        if gpio is None:
            continue
        # A signal the board does not wire is SHOWN, greyed, saying "not wired".
        # Leaving it out would make two boards look identical when the
        # difference is exactly the missing pin - an ESP-EYE has no power-down
        # line, and a reader has to be able to see that.
        wired = gpio >= 0
        rows.append(
            '<text x="14" y="%d" class="sig">%s</text>'
            '<text x="150" y="%d" class="%s">%s</text>'
            '<text x="205" y="%d" class="lbl">%s</text>'
            % (y, key.upper(), y, "gpio" if wired else "off",
               ("GPIO %d" % gpio) if wired else "not wired", y, label))
        y += 21

    extra = b.get("extra") or {}
    if extra:
        y += 8
        rows.append('<text x="14" y="%d" class="head">also on this board</text>' % y)
        y += 20
        for key, gpio in sorted(extra.items()):
            rows.append('<text x="14" y="%d" class="sig">%s</text>'
                        '<text x="150" y="%d" class="gpio">GPIO %d</text>'
                        % (y, key.upper(), y, gpio))
            y += 21

    height = y + 16
    return ("""<svg xmlns="http://www.w3.org/2000/svg" width="380" height="%d"
     viewBox="0 0 380 %d" role="img" aria-label="%s pin map">
  <style>
    /* The page's own tokens: this is embedded in a page that has a theme, and
       a diagram that ignores it is a foreign object on the screen. The
       fallbacks are for the file opened on its own, with no page around it. */
    .bg   { fill: var(--sunk, #0d1117); stroke: var(--line, #2a3442); }
    text  { font-family: ui-monospace, Consolas, monospace; font-size: 12px; }
    .head { fill: var(--acc, #4da3ff); font-weight: 600; font-size: 13px; }
    .sub  { fill: var(--mut, #8b98a8); font-size: 11px; }
    .sig  { fill: var(--txt, #e6edf3); }
    .gpio { fill: var(--ok, #3ecf8e); }
    .off  { fill: var(--mut, #8b98a8); font-style: italic; }
    .lbl  { fill: var(--mut, #8b98a8); }
  </style>
  <rect class="bg" x="1" y="1" width="378" height="%d" rx="10" stroke-width="1"/>
  <text x="14" y="28" class="head">%s</text>
  <text x="14" y="46" class="sub">%s</text>
  <text x="14" y="62" class="sub">drawn from firmware/config/cam_boards.json</text>
  %s
</svg>
""" % (height, height, esc(b.get("label", name)), height - 2,
       esc(b.get("label", name)), esc(b.get("note", "")), chr(10) + "  ".join(rows)))


_web_v = ["", 0.0]


def web_version(ttl=2.0):
    """A short id for the pages this hub is serving RIGHT NOW.

    An open tab keeps the copy of hub.html and the stylesheets it loaded with.
    The data on the page refreshes itself every few seconds, so a board coming
    and going is seen - but a change to the INTERFACE is not, and nothing says
    so. Asked about directly on 2026-08-20: *in web why i need to refresh by my
    self to see the change*.

    Built from the size and mtime of the files actually served, not from a
    version number someone has to remember to bump - a number that has to be
    edited by hand is a number that will be forgotten on the one change that
    mattered. Contents are deliberately NOT hashed: this is polled by every
    open tab, and reading a megabyte of Studio each time to answer a question
    whose answer is nearly always *nothing changed* is a poor trade.

    Cached for a moment because several tabs poll it, and the answer cannot
    meaningfully change between two of their requests.
    """
    now = time.time()
    frozen = bool(getattr(sys, "frozen", False))
    # A ONE-FILE BUILD CANNOT CHANGE WHILE IT RUNS. PyInstaller unpacks the
    # bundle to a fresh temporary folder at every launch, so every file gets a
    # new mtime - and using mtime there made the version differ after a plain
    # restart of the SAME exe, so every open tab announced an update that had
    # not happened. Frozen: size and path only, computed once and kept.
    if _web_v[0] and (frozen or now - _web_v[1] < ttl):
        return _web_v[0]
    h = hashlib.sha1()
    for root in (HUB_WEB, SHARED_WEB, STUDIO_WEB):
        root = Path(root)
        try:
            for f in sorted(root.rglob("*")):
                # Names starting with _ are scratch, not app. QC writes its
                # driver page INTO the studio folder while a browser check
                # runs, and hashing it made the version flap several times a
                # minute - every open tab would have announced an update
                # because a temporary file appeared next to the real ones.
                if f.name.startswith("_") or not f.is_file():
                    continue
                # Pictures count too. Skipping them meant a changed pinout or
                # icon was invisible to an open tab, which is exactly the kind
                # of change somebody makes and then wonders why nothing moved.
                if f.suffix.lower() not in (".html", ".css", ".js", ".svg",
                                            ".png", ".ico", ".webp", ".json"):
                    continue
                st = f.stat()
                # The PATH, not the name: two folders each hold an index.html,
                # and keying on the name alone meant moving a file between them
                # changed nothing at all.
                try:
                    who = f.relative_to(root).as_posix()
                except ValueError:
                    who = f.name
                h.update((root.name + "/" + who).encode("utf-8", "replace"))
                h.update(("%d" % st.st_size).encode())
                if not frozen:
                    h.update((":%d" % int(st.st_mtime)).encode())
        except OSError:
            continue            # a folder that is not there changes nothing
    _web_v[0], _web_v[1] = h.hexdigest()[:12], now
    return _web_v[0]


def shared_css():
    """The design system as one stylesheet: the palette, then the components.

    Split into two files on 2026-08-19 so that changing a colour, or adding a
    theme, means editing shared/web/themes.css and nothing else. They are
    joined here rather than linked separately because every page - including
    the module website served from the board's own flash - links exactly one
    stylesheet, and none of them should have to change for a decision about
    where the colours live.
    """
    parts = []
    nl = chr(10).encode()
    for name in ("themes.css", "mice.css"):
        f = SHARED_WEB / name
        if f.is_file():
            parts.append(b"/* ---- " + name.encode() + b" ---- */" + nl)
            parts.append(f.read_bytes())
            parts.append(nl)
    return b"".join(parts)


# Where the built hub is published. The `app` branch holds MiceHub.exe and
# nothing else; there are no GitHub releases, so this asks the branch.
APP_REPO = "Mannaja78520/final_proj_mice"
APP_BRANCH = "app"
APP_API = "https://api.github.com/repos/%s/commits/%s" % (APP_REPO, APP_BRANCH)
APP_RAW = "https://raw.githubusercontent.com/%s/%s/MiceHub.exe" % (APP_REPO, APP_BRANCH)


def _my_sha_file():
    """Beside the exe, so it travels with the thing it describes."""
    return Path(sys.executable).parent / "MiceHub.sha"


def update_state():
    """What is running, what is offered, and whether it may be replaced now."""
    frozen = getattr(sys, "frozen", False)
    mine = ""
    f = _my_sha_file()
    if f.is_file():
        mine = f.read_text(encoding="utf-8", errors="replace").strip()[:40]

    out = {"ok": True, "frozen": frozen, "running": mine, "offered": "",
           "when": "", "message": "", "can": False, "why": ""}
    # OLDER THAN THE SOURCE BESIDE IT is a different question from *is there a
    # newer build on GitHub*, and it is the one that bit on 2026-08-21. It is
    # answered on every branch below, including the busy ones, because a hub
    # that refuses to update right now still needs to say what it is running.
    st = build_stamp.state()
    out.update({"stale": st["stale"], "staleWhy": build_stamp.why(st),
                "rebuild": build_stamp.REBUILD, "built": st["built"],
                "changed": st["changed"]})
    if not frozen:
        out["why"] = ("this is main.py, not the built app - update it with git "
                      "pull, which also brings the firmware and the checks")
        return out
    # BUSY MEANS NO. Replacing the program mid-flash leaves a board half
    # written, and mid-show stops the installation in front of an audience.
    if flasher.running():
        out["why"] = "a board is being flashed - wait for it to finish"
        return out
    if show.running():
        out["why"] = "a show is playing - stop it first"
        return out
    try:
        req = urllib.request.Request(APP_API, headers={"Accept":
                                     "application/vnd.github+json"})
        with urllib.request.urlopen(req, timeout=10) as r:
            d = json.loads(r.read().decode(errors="replace"))
        out["offered"] = (d.get("sha") or "")[:40]
        out["when"] = ((d.get("commit") or {}).get("committer") or {}).get("date", "")
        out["message"] = ((d.get("commit") or {}).get("message") or "").split("\n")[0][:90]
        out["can"] = bool(out["offered"]) and out["offered"] != mine
        if not out["can"] and out["offered"]:
            out["why"] = "this is already the newest build"
    except Exception as e:                                    # noqa: BLE001
        # No internet is the NORMAL case at a venue, so it is a plain answer
        # and not an error page.
        out["why"] = "cannot reach GitHub (%s)" % str(e)[:60]

    # THE HUB NEXT DOOR. On show day there is no internet, and the newest build
    # a PC can reach is the one on the desk beside it, not GitHub.
    near = hub_offers()
    if near and near.get("sha") and near["sha"] != mine:
        newer = (not out["offered"]) or (near.get("when", "") > out.get("when", ""))
        if newer:
            out.update({"offered": near["sha"], "when": near.get("when", ""),
                        "message": "from %s on this network" % near["host"],
                        "from": "http://%s:%d/api/app" % (near["ip"], PORT),
                        "can": True, "why": ""})
    return out


def app_here():
    """This hub's own program, if it is a built one. (path, bytes, sha) or None.

    A browser can never reach another PC's serial ports, at any address - so the
    only way that PC drives its own cables is to run this program. At a venue
    there is usually no internet, which makes the hub on the next desk the
    nearest place to get it.
    """
    if not getattr(sys, "frozen", False):
        return None
    exe = Path(sys.executable)
    if not exe.is_file():
        return None
    sha = ""
    f = _my_sha_file()
    if f.is_file():
        sha = f.read_text(encoding="utf-8", errors="replace").strip()[:40]
    return exe, exe.stat().st_size, sha


def hub_offers():
    """The newest build any OTHER hub on this network is running.

    Asked 2026-08-21. GitHub is the right source when there is internet and the
    wrong one when there is not - which is the show-day case. A hub on the same
    switch is reachable either way.
    """
    best = None
    for h in scan_hubs(False):
        ip = h.get("ip")
        if not ip or is_self(ip):
            continue
        try:
            with urllib.request.urlopen(
                    "http://%s:%d/api/app/version" % (ip, PORT), timeout=5) as r:
                d = json.loads(r.read().decode(errors="replace"))
        except Exception:                                     # noqa: BLE001
            continue                  # a closed laptop is normal, not an error
        if not d.get("sha") or not d.get("bytes"):
            continue
        d["ip"] = ip
        d["host"] = h.get("host") or ip
        if not best or (d.get("when") or "") > (best.get("when") or ""):
            best = d
    return best


def do_update():
    """Fetch the published exe and put it in place. Returns (ok, message)."""
    st = update_state()
    if not st["can"]:
        return False, st["why"] or "nothing to update"
    # Whatever update_state chose: GitHub, or the hub on the next desk.
    where = st.get("from") or APP_RAW
    try:
        with urllib.request.urlopen(where, timeout=180) as r:
            blob = r.read()
    except Exception as e:                                    # noqa: BLE001
        return False, "download failed: %s" % str(e)[:90]
    # A truncated download that overwrote the app would leave nothing to run.
    if len(blob) < 2_000_000 or blob[:2] != b"MZ":
        return False, ("that download is not a Windows program (%d bytes) - "
                       "nothing was replaced" % len(blob))
    exe = Path(sys.executable)
    old = exe.with_name("MiceHub.old.exe")
    try:
        old.unlink(missing_ok=True)
        # Windows will not overwrite a RUNNING exe, but it will rename one.
        # The old file stays as the way back if the new one will not start.
        exe.rename(old)
        exe.write_bytes(blob)
        _my_sha_file().write_text(st["offered"], encoding="utf-8")
    except OSError as e:
        return False, "could not replace the program: %s" % str(e)[:90]
    return True, ("updated to %s - close this window and start MiceHub.exe "
                  "again. The previous version is MiceHub.old.exe"
                  % st["offered"][:12])


# The line the bundle splits on: everything above it is for the person
# reading, everything below is for support. The page and the check split on
# this exact string - changing it here changes all three or nothing.
DIAG_TECH_MARK = "--- technical detail below, for support ---"


def diagnostics() -> str:
    """Everything anyone asks for first, as one block of plain text.

    "It does not work" is never enough to act on. The answer is always the same
    four questions - which PC, what does it see, what firmware is on the
    boards, and what can this machine even do - and getting them out of
    somebody over chat takes half an hour. This is one button instead.

    TWO HALVES, asked 2026-08-22 (A21-5): IN PLAIN WORDS first - what is
    connected, what needs attention, each with its fix, NO ids, ports or
    addresses - then DIAG_TECH_MARK, then the technical bundle below it,
    which stays complete because support needs every id. The page shows the
    plain half and hides the rest behind the technical switch.

    PLAIN TEXT, NOT JSON. It gets pasted into a message by a person, and JSON
    pasted into a chat window is a wall nobody reads.

    NOTHING SECRET, EVER. This is written to be shared, so a password in it is
    a password published. The hub keeps one in plain text beside itself
    (hub_password.txt), a module's WiFi credentials come back in some status
    replies, and the AP password is derived from the group name. None of them
    belong here, and check_diagnostics exists to keep it that way - a bundle
    that leaks is worse than no bundle, because the leak travels further than
    the problem it was meant to solve.
    """
    import platform                                          # noqa: PLC0415

    def line(k, v):
        return "%-14s %s" % (k, v)

    def pline(k, v):
        return "  %-11s %s" % (k, v)

    def disp_name(m):
        # probe_module defaults an unnamed WiFi module's name to its IP;
        # an address in the plain half breaks the no-addresses promise.
        # search, not fullmatch: a name like 192.168.4.21:8642 or a forwarded
        # hub: prefix still carries an address and must be stripped too
        nm = m.get("name") or ""
        if re.search(r"\b\d{1,3}(?:\.\d{1,3}){3}\b", nm):
            nm = ""
        return nm or ("unnamed %s robot" % (m.get("type") or "?"))

    # Gather once; the plain half and the technical half read the SAME data.
    _st = build_stamp.state()
    esp_cmd, esp_why = esptool_cmd()
    images = flash_images()
    ports = serial_ports()
    mods = modules_here()

    # ASK THE BOARD which firmware it runs. The module list is built from
    # PING, which answers id, name and type and nothing else - so `fw` is
    # simply not in it. One extra command per board, on an explicit button
    # press, with a short wait: a board that has gone quiet says so and does
    # not hold up the rest.
    def ask_fw(m):
        dev = (m.get("routes") or [{}])[0].get("dev")
        if not dev:
            return "?"
        try:
            info = dev_cmd(dev, "INFO", wait=2.0) or ""
            got = json.loads(info[info.find("{"):info.rfind("}") + 1])
            return got.get("fw") or "?"
        except Exception as e:                                # noqa: BLE001
            return "no answer (%s)" % str(e)[:40]

    fws = {m.get("id"): ask_fw(m) for m in mods}

    # ---- the plain half -------------------------------------------------
    plain = ["IN PLAIN WORDS", ""]
    if mods:
        names = ", ".join(disp_name(m) for m in mods)
        plain.append(pline("robots", "%d connected - %s"
                           % (len(mods), names)))
    else:
        plain.append(pline("robots", "none found - are they powered, "
                                     "and on this WiFi?"))

    worry = []
    if _st["built"] and _st["stale"]:
        worry.append("this hub program is older than the files beside it - "
                     "run the updater or get the newest MiceHub.exe")
    if not esp_cmd:
        worry.append("the flashing tool is missing - boards can still be used, "
                     "but new firmware cannot be installed until it is set up")
    for im in images:
        if not im.get("ready") and not im.get("ota_ready"):
            worry.append("no %s firmware is built on this PC yet - build it "
                         "before trying to flash a %s board"
                         % (im.get("type"), im.get("type")))
    if not ports:
        worry.append("no cable is plugged into this PC - boards on a wire "
                     "will not appear until one is")
    for m in mods:
        who = disp_name(m)
        if m.get("stale"):
            worry.append("%s is answering slowly - it may be busy or going "
                         "offline" % who)
        elif str(fws.get(m.get("id"))).startswith("no answer"):
            worry.append("%s did not answer when asked about itself - "
                         "check its power" % who)
    if worry:
        plain.append("")
        plain.append(pline("needs attention:", ""))
        plain.extend("  - " + w for w in worry)
    else:
        plain.append(pline("all good:", "nothing needs attention right now."))

    # ---- the technical half, exactly as it has always been --------------
    out = ["mice diagnostics  " + time.strftime("%Y-%m-%d %H:%M:%S"),
           "=" * 58]
    out += plain
    out += ["", DIAG_TECH_MARK, "", "THIS PC"]
    out.append(line("host", socket.gethostname()))
    out.append(line("os", "%s %s" % (platform.system(), platform.release())))
    out.append(line("python", platform.python_version()))
    out.append(line("hub at", "%s:%d" % (lan_ip(), PORT)))
    out.append(line("web build", str(web_version())))
    out.append(line("frozen", "yes (MiceHub.exe)" if getattr(sys, "frozen", False)
                    else "no (running main.py)"))
    # The first question after any strange report: is this even today's build?
    if _st["built"]:
        out.append(line("exe built", "%s%s" % (
            _st["built"], "  STALE - %s" % build_stamp.why(_st)
            if _st["stale"] else "  (matches the source beside it)")))
    out.append(line("esptool", "yes" if esp_cmd else "NO - %s"
                    % (esp_why or "not found")))

    out += ["", "FIRMWARE BUILT ON THIS PC"]
    for im in images:
        state = "ready" if im.get("ready") else (
            "app only (WiFi/bus, not cable)" if im.get("ota_ready") else "NOT BUILT")
        out.append(line("  " + str(im.get("type")), "%s  %s" % (
            state, ("%.2f MB" % (im["bytes"] / 1048576.0)) if im.get("bytes") else "")))

    out += ["", "SERIAL PORTS"]
    if not ports:
        out.append("  none")
    for p in ports:
        out.append(line("  " + str(p.get("port")), "%s%s" % (
            p.get("desc") or "?", "  (bluetooth)" if p.get("bt") else "")))

    out += ["", "MODULES FOUND"]
    if not mods:
        out.append("  none - are they powered, and on this WiFi?")
    for m in mods:
        ways = ", ".join("%s%s" % (r.get("kind"),
                                   (" " + str(r.get("port"))) if r.get("port") else "")
                         for r in m.get("routes", []))
        out.append(line("  #%s" % m.get("id"), "%s  type=%s  fw=%s  via %s%s" % (
            m.get("name") or "?", m.get("type") or "?",
            fws.get(m.get("id"), "?"), ways,
            "  [LATE]" if m.get("stale") else "")))

    out += ["", "(no passwords are included in this text)"]
    return chr(10).join(out)


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

    def _claim(self, port, module_type, how, target=None, args=(), stage=""):
        """Take the job and START it, or refuse - ALL UNDER ONE LOCK.

        Every start path used to test running() outside the lock and set the
        fields after it. Two POSTs in that window - a double click, or two
        tabs - both passed the test and both spawned a thread, so two writers
        drove one shared job and each overwrote the other's progress. The GET
        showed whichever wrote last and neither caller was told. Found
        2026-08-21. Starting the thread here closes the same gap that remained
        between claim returning and the thread object being assigned.
        """
        with self.lock:
            if self.running():
                raise RuntimeError("already flashing %s - one board at a time"
                                   % (self.port or self.type))
            self.port, self.type, self.how = port, module_type, how
            self.percent, self.stage, self.log = 0, stage or "starting", []
            self.ok, self.error = None, ""
            if target:
                self.thread = threading.Thread(target=target, args=args,
                                               daemon=True)
                self.thread.start()

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
    def start_ota(self, ip, module_type, user="", password=""):
        im = flash_image(module_type)
        # OTA sends ONE file - the app image - because that is all a running
        # board can take: the bootloader and the partition table are written
        # by esptool over a cable and are not part of an over-the-air update.
        # So asking for all four parts here refused a PC that had exactly what
        # this needs, which is the normal case for a machine that was given the
        # images rather than building them.
        app = [q for off, q in im["parts"] if q.endswith("firmware.bin")]
        if not app:
            raise RuntimeError(
                "no %s app image on this PC. Build it with pio run -e %s, or "
                "copy firmware.bin into %s" % (module_type, im["env"], im["dir"]))
        if not ip:
            raise RuntimeError("which module? this needs its WiFi address")
        self._claim(ip, module_type, "wifi", self._run_ota,
                    (ip, im, user, password))
        return self.status()

    # The board wants a session before it will take firmware, and it is right
    # to: /api/ota replaces the program on a machine anyone on the venue WiFi
    # can reach. Measured on board 42 over real WiFi, 2026-08-21:
    # `401 ERR log in first`. Before the gate moved into the body handler
    # (A18-1) the board wrote the image and refused afterwards, so this was
    # broken the whole time and looked like it worked.
    BOARD_COOKIE = BOARD_COOKIE         # one source: the module constant above

    def _board_session(self, ip, user, password):
        """Log in to a board. -> (cookie, why). One body, shared with dev_cmd."""
        return board_login(ip, user, password)

    def _run_ota(self, ip, im, user="", password=""):
        import http.client
        try:
            path = [p for off, p in im["parts"] if p.endswith("firmware.bin")][0]
            data = Path(path).read_bytes()
            cookie, why = self._board_session(ip, user, password)
            # An empty reason with no cookie is the ONE case that goes on: a
            # board too old to have a login at all (see _board_session).
            if not cookie and why:
                with self.lock:
                    self.ok, self.stage, self.error = False, "failed", why
                self._say(why)
                return
            self._say("%s %s; sending %s (%.2f MB) over WiFi"
                      % ("logged in to" if cookie else
                         "no login on (old firmware)", ip,
                         Path(path).name, len(data) / 1048576.0))
            b = "----miceota"
            head = ("--%s\r\nContent-Disposition: form-data; name=\"file\"; "
                    "filename=\"firmware.bin\"\r\nContent-Type: "
                    "application/octet-stream\r\n\r\n" % b).encode()
            tail = ("\r\n--%s--\r\n" % b).encode()
            conn = http.client.HTTPConnection(ip, timeout=90)
            # The board REQUIRES the md5 now: with UPDATE_SIZE_UNKNOWN and
            # nothing registered, its end(true) verified nothing, so a
            # dropped connection booted a half-written image.
            conn.putrequest("POST", "/api/ota?md5=" +
                            hashlib.md5(data).hexdigest())    # noqa: S324
            conn.putheader("Content-Type", "multipart/form-data; boundary=" + b)
            conn.putheader("Content-Length", str(len(head) + len(data) + len(tail)))
            if cookie:
                conn.putheader("Cookie", "%s=%s" % (self.BOARD_COOKIE, cookie))
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

    # ---- over the COMMAND CHANNEL, whatever that channel is --------------
    #
    # The third way, and the only one that works on a two-wire bus. Asked for
    # 2026-08-20: *make it can flash through all this 3 method too if i need to
    # shieft to stm 32 it cannot use wifi it can use only rs485*.
    #
    # Why the other two cannot do it:
    #   * esptool reaches the ROM bootloader by pulling EN and IO0 with DTR and
    #     RTS. RS485 is two differential wires and has neither, so no amount of
    #     work on the hub side gets there;
    #   * the WiFi updater posts to the board's own web server, which a board
    #     with no radio does not have.
    # Both of those are ways of getting an image IN. This one is the board
    # writing its own spare OTA slot from ordinary command lines, so the link
    # underneath stops mattering — and `dev_cmd` already speaks every one of
    # them, including a module behind another module's hotspot and a module on
    # another PC's cable.
    #
    # It is SLOW: 150 bytes a chunk (see BusUpdate.h — an RS485 line is capped
    # at 250 characters and base64 costs a third), so a 1.3 MB image is around
    # nine thousand round trips. Six minutes on a cable, longer on the bus. That
    # is the price of not having a reset line, and it is paid rarely.
    BUS_CHUNK = 150

    def start_bus(self, dev, module_type):
        im = flash_image(module_type)
        app = [q for off, q in im["parts"] if q.endswith("firmware.bin")]
        if not app:
            raise RuntimeError(
                "no %s app image on this PC. Build it with pio run -e %s, or "
                "copy firmware.bin into %s" % (module_type, im["env"], im["dir"]))
        if not dev:
            raise RuntimeError("which module? this needs its dev address")
        self._claim(dev, module_type, "bus", self._run_bus, (dev, app[0]))
        return self.status()

    def _run_bus(self, dev, path):
        try:
            data = Path(path).read_bytes()
            total = len(data)
            digest = hashlib.md5(data).hexdigest()          # noqa: S324
            self._say("sending %s (%.2f MB) to %s as commands"
                      % (Path(path).name, total / 1048576.0, dev))

            # Ask FIRST whether it fits. The board answers from its real
            # partition table, so "no room" arrives before a single byte is
            # written rather than half way through, when the running firmware
            # is already gone.
            # 30 s, for the same reason FWEND gets 60: this is not a question,
            # it is work. Reserving the slot erases it, and erasing most of two
            # megabytes of flash is seconds, not milliseconds. Timing out here
            # would report a failed update before a single byte was sent —
            # while the board was busy doing exactly what it was asked.
            reply = (dev_cmd(dev, "FWBEGIN %d %s" % (total, digest),
                             wait=30) or "").strip()
            if not reply.startswith("OK"):
                raise RuntimeError(reply or "the board did not answer FWBEGIN")
            with self.lock:
                self.stage = "writing"

            seq, sent = 0, 0
            while sent < total:
                piece = data[sent:sent + self.BUS_CHUNK]
                # The LENGTH is on the wire because a truncated line is still
                # legal base64. Measured 2026-08-20 on a 1.29 MB image over a
                # cable: one chunk in nine thousand lost 64 characters, decoded
                # cleanly to 102 bytes instead of 150, and nothing noticed until
                # FWEND counted the image 48 bytes short — four minutes gone,
                # with no way to tell which chunk did it.
                line = "FWDATA %d %d %s" % (seq, len(piece),
                                            base64.b64encode(piece).decode())
                # A LOST LINE IS RETRIED, NOT SKIPPED. The board refuses a chunk
                # that is not the one it expects and says which one it wants, so
                # a dropped reply costs a repeat and never a hole in the image.
                # Silently carrying on is how a board ends up booting rubbish.
                for attempt in range(4):
                    try:
                        ans = (dev_cmd(dev, line) or "").strip()
                    except Exception as e:                    # noqa: BLE001
                        # A LOST REPLY IS THE ORDINARY CASE ON A BUS, and
                        # dev_cmd reports it by raising. Letting that escape
                        # would end the whole update on the first dropped line
                        # — nine thousand chunks means even a rare loss is
                        # near-certain, so retrying has to survive an exception
                        # and not merely an ERR string.
                        ans = "no answer (%s)" % str(e)[:80]
                    if ans.startswith("OK"):
                        break
                    if "expected" in ans:
                        want = re.search(r"expected (\d+)", ans)
                        if want and int(want.group(1)) == seq + 1:
                            break     # it took this one; only the reply was lost
                    # "chunk short" and "not valid base64" both mean the line
                    # was damaged in flight and the board did NOT advance, so
                    # the same chunk goes again — this is the self-healing case
                    # and it must not be mistaken for a hard refusal.
                    if attempt == 3:
                        raise RuntimeError(
                            "chunk %d would not go: %s" % (seq, ans or "no answer"))
                seq += 1
                sent += len(piece)
                # THE BOARD'S OWN RUNNING TOTAL, checked rather than ignored.
                # It is already on the wire in every OK reply, and comparing it
                # turns any remaining drift into an error at the chunk that
                # caused it instead of a mystery at the end of the transfer.
                said = re.match(r"OK \d+ (\d+)", ans)
                if said and int(said.group(1)) != sent:
                    raise RuntimeError(
                        "the board has %s bytes after chunk %d but %d were sent "
                        "— stopping rather than finishing an image that would "
                        "not match" % (said.group(1), seq - 1, sent))
                with self.lock:
                    self.percent = int(sent * 100 / total)

            with self.lock:
                self.stage = "checking the image"
            # FWEND is where a wrong image is caught, while the board is still
            # running firmware that works. Only then does it reboot.
            # 60 s, not the usual 2: the board hashes the whole image before it
            # will boot into it, and reporting a timeout here would mean an
            # operator reflashing a board that had in fact just succeeded.
            reply = (dev_cmd(dev, "FWEND", wait=60) or "").strip()
            with self.lock:
                self.ok = reply.startswith("OK")
                self.percent = 100 if self.ok else self.percent
                self.stage = "restarting the board" if self.ok else "failed"
                if not self.ok:
                    self.error = reply[:200] or "the board did not answer FWEND"
            self._say(reply[:200])
        except Exception as e:            # noqa: BLE001
            try:
                dev_cmd(dev, "FWABORT")   # leave it running what it had
            except Exception:             # noqa: BLE001, S110
                pass
            with self.lock:
                self.ok, self.stage = False, "failed"
                self.error = ("%s — the board keeps the firmware it already "
                              "had; nothing was switched over" % e)

    def start(self, port, module_type):
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
        self._claim(port, module_type, "usb", self._run, (cmd, im))
        return self.status()

    def start_received(self, port, module_type, parts, who):
        """Flash an image that came from another PC over the network.

        Same writer as a local flash — the only difference is where the bytes
        came from, so the progress, the log and the one-cable-at-a-time rule
        are shared rather than reimplemented. The files land in a temp folder
        that is removed when the write finishes, however it finishes: a failed
        flash must not leave a stale firmware on disk for the next one to pick
        up by mistake.
        """
        import base64
        import tempfile
        cmd, why = esptool_cmd()
        if not cmd:
            raise RuntimeError(why)
        if not port:
            raise RuntimeError("which port? name the cable the board is on")
        if not parts:
            raise RuntimeError("no firmware arrived")
        # The port is about to become an argument to esptool. Nothing that
        # is not a port shape gets that far.
        if not re.fullmatch(r"(COM\d+|/dev/[\w./-]+)", port):
            raise ValueError("%s is not a serial port" % port)
        d = Path(tempfile.mkdtemp(prefix="mice_fw_"))
        got = []
        try:
            for i, p in enumerate(parts):
                # A name is a NAME: no folders, and never empty, or the write
                # lands on the temp folder itself.
                name = Path(str(p.get("name", ""))).name or ("part%d.bin" % i)
                f = d / name
                f.write_bytes(base64.b64decode(p.get("b64", "")))
                # Offsets travel as they are written everywhere else here -
                # 0x1000, not 4096 - so they are read in whatever base they
                # arrive in and handed to esptool in the same form.
                got.append((str(p.get("off", "0")), str(f)))
        except Exception:
            # Nothing has been started yet, so the folder is ours to remove.
            # Leaving it behind on a bad payload is a slow disk leak that only
            # shows up on the PC at the venue.
            shutil.rmtree(d, ignore_errors=True)
            raise
        got.sort(key=lambda pair: int(str(pair[0]), 0))   # by address, not by spelling
        im = {"type": module_type, "parts": got, "ready": True,
              "from": who, "tmp": str(d)}
        try:
            self._claim(port, module_type, "usb", self._run, (cmd, im),
                        stage="receiving from " + who)
        except Exception:
            # Usually "already flashing": the write never started, so nobody
            # owns the folder yet - same rule as the bad-payload path above.
            shutil.rmtree(d, ignore_errors=True)
            raise
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
            # WAIT UNTIL THE CABLE IS REALLY OURS TO GIVE UP. usb_close does
            # not close a port somebody is mid-command on - it puts it back, on
            # purpose - so calling it once and sleeping 300ms was a guess.
            # esptool then met a handle that was still open and died at
            # whatever percent it had reached, leaving the board in the
            # bootloader answering nothing. Measured at the bench 2026-08-20:
            # 21%, "the chip stopped responding".
            deadline = time.time() + 12
            while True:
                usb_close(port)
                _usb_touch.pop(port, None)
                _usb_ident.pop(port, None)   # whatever it was, it is about to change
                if usb_free(port):
                    break
                if time.time() > deadline:
                    raise RuntimeError(
                        "%s is still in use by this hub after 12s - something "
                        "is mid-command on it. Close the module page or Studio "
                        "tab using that cable and try again." % port)
                time.sleep(0.5)
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
            # An image that arrived from another PC lives in a temp folder.
            # Remove it whether the write worked or not: leaving firmware on
            # disk invites the next flash to pick up bytes nobody chose.
            if im.get("tmp"):
                import shutil
                shutil.rmtree(im["tmp"], ignore_errors=True)

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
def _read_lines(ser, seconds, quiet=0.0, at_least=0.0):
    """Lines for `seconds`, or until the port has been quiet for `quiet`.

    The quiet rule exists for the RS485 census. Modules stagger their answers
    to a broadcast by their own id so the replies do not collide, so the LAST
    board to speak is the one with the highest id - which makes a fixed window
    a limit on which boards exist as far as the hub is concerned. Measured on
    the bench 2026-08-19: a nong with id 67 answered 1344 ms after the
    broadcast, while this waited 0.8 s. It was invisible, and reported no
    error, which reads exactly like an empty bus.

    Waiting for quiet instead means one quick board costs a fifth of a second
    and a high id is still found, up to the cap.
    """
    lines, buf = [], b""
    started = time.time()
    end = started + seconds
    last = started
    while time.time() < end:
        chunk = ser.read(256)
        if not chunk:
            # Quiet only counts AFTER the floor. A quick board answers in 20 ms
            # and the next one may be a second behind it, so stopping at the
            # first silence hears the fast boards and calls the rest absent -
            # which is the bug this whole rule exists to fix, moved rather than
            # removed.
            if (quiet and lines
                    and (time.time() - started) >= at_least
                    and (time.time() - last) >= quiet):
                break
            continue
        last = time.time()
        buf += chunk
        while (chr(10).encode()) in buf:
            ln, buf = buf.split(chr(10).encode(), 1)
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
    # ONE LOOKUP, not a test and then a read. Another thread pops this key the
    # moment a command changes a board's identity (GROUP, SET NAME) - exactly
    # while `light` is true, which is the only case this path is for - so the
    # test could pass and the read raise KeyError, turning a cached answer into
    # a bare 500. Found 2026-08-21.
    cached = _usb_ident.get(port) if light else None
    if cached is not None:
        cached = dict(cached)
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
                                         # The chip MAC, when the board runs
                                         # firmware new enough to report it.
                                         # Without it the same board found on a
                                         # cable and on WiFi cannot be told to
                                         # be one board - see modules_here.
                                         "chip": st.get("chip", ""),
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
            # 5.4 s is the worst case an OLD board can take: the stagger
            # was id x 20 ms and ids go to 247. It almost never costs
            # that, because the read stops once the bus has been quiet
            # for 300 ms - one board with a low id is a fifth of a
            # second. Current firmware answers within 240 ms whatever
            # the id (RS485Bus.cpp).
            # 1.6 s floor, then stop when the bus goes quiet, cap 5.4 s.
            #
            # The floor is what makes a late board findable: with the OLD
            # stagger of id x 20 ms it covers every id up to 80, and current
            # firmware answers within 240 ms whatever the id. The cap is the
            # true worst case, id 247 on old firmware.
            #
            # THE LIMIT, said out loud: a board running old firmware with an id
            # above 80 answers after the floor and may be missed if nothing
            # else is talking. Reflashing it fixes that permanently, because
            # the bounded stagger lands every board inside the floor.
            for ln in _read_lines(ser, 5.4, quiet=0.3, at_least=1.6):
                m = re.match(r"^@(\d+)\s+PONG\s+(\d+)\s+(.+)\s+(\S+)$", ln)
                if m:
                    seen[int(m.group(1))] = {"id": int(m.group(1)), "name": m.group(3),
                                             "type": m.group(4), "ip": "", "wifi_mode": ""}
            # ask each bus module for its INFO to learn its WiFi ip (for links)
            #
            # THE LIMIT, said out loud: only the first SIX are asked. Each ask
            # costs up to 0.6 s and the scan walks every port, so a seventh
            # board on one bus keeps an empty group and chip - it is listed
            # and reachable, but reads as "not linked" the way every bus board
            # did before A3-5. Raising this trades a slower Modules screen for
            # correctness on buses that big, and no bench here has one yet.
            for mid in list(seen)[:6]:
                _drain_to_line_boundary(ser)
                ser.write(("#%d INFO\n" % mid).encode())
                for ln in _read_lines(ser, 0.6):
                    if ln.startswith("@%d {" % mid):
                        try:
                            st = json.loads(ln.split(" ", 1)[1])
                            seen[mid].update(_wifi_of(st))
                            # ...and its chip, from the same answer. A module
                            # behind an RS485 bus is reachable over WiFi too,
                            # so it is exactly a board the hub can meet twice.
                            if st.get("chip"):
                                seen[mid]["chip"] = st["chip"]
                            # ...AND ITS GROUP (A3-5). The Network tab and
                            # /api/allmods have always read this field for bus
                            # boards; nothing ever filled it, so a module
                            # behind the bus read "not linked" however it was
                            # grouped — and ticking it to fix that would send
                            # GROUP to a board that already had one.
                            seen[mid]["group"] = st.get("group", "")
                        except ValueError:
                            pass
                        break
            # A board on its OWN cable answers the broadcast too, so "no
            # direct answer, one board in the census" is ambiguous: it is
            # either an RS485 adapter with one module behind it, or a board
            # whose direct probe was simply missed. Ask it plainly once more -
            # an adapter has nothing to answer with, a board does. Without
            # this, a camera on a plain USB cable was listed as a module on a
            # bus, with an addressed dev string it did not need.
            if not out["module"] and len(seen) == 1:
                _drain_to_line_boundary(ser)
                ser.write(b"INFO" + chr(10).encode())
                for ln in _read_lines(ser, 1.2):
                    if ln.startswith("{"):
                        try:
                            st = json.loads(ln)
                            out["module"] = {"id": st.get("id"),
                                             "name": st.get("name"),
                                             "type": st.get("type"),
                                             "group": st.get("group", ""),
                                             "chip": st.get("chip", ""),
                                             **_wifi_of(st)}
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
            # ONE budget for all of them, because they run at the same time -
            # there is a worker per port, so the wall clock is the slowest port
            # and not the sum. What it must cover, measured on four real cables
            # 2026-08-19: an ordinary port answers in about 3 s, and a port with
            # an RS485 bus behind it takes 4.7 s, because the census waits for
            # the bus to go quiet and boards stagger their answers by id.
            #
            # It was 7 s, which was comfortable until the bus census got its
            # floor - then a four-cable bench spent 10.8 s and reported 2 boards
            # of 5, with the bus module among the missing. The ports that lose
            # are simply the ones waited on last, which is why it looked like a
            # bus fault and was not one.
            budget = 20
            deadline = time.time() + budget
            for p, f in futs:
                try:
                    out.append(f.result(timeout=max(0.1, deadline - time.time())))
                except FutTimeout:
                    out.append({"port": p, "module": None, "rs485": [],
                                "error": "no answer within %d s — skipped. A port "
                                         "with an RS485 bus behind it is the "
                                         "slowest thing here" % budget})
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
    def send_bytes(self, data: bytes, ctype="application/json", code=200,
                   headers=()):
        self.send_response(code)
        for k, v in headers:
            self.send_header(k, v)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def send_redirect(self, where, code=302):
        """Send the browser somewhere else. 302, not 301: a permanent redirect
        is cached by the browser forever, and a wrong one can only be undone by
        the user clearing their history."""
        self.send_response(code)
        self.send_header("Location", where)
        self.send_header("Content-Length", "0")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

    def send_json(self, obj, code=200):
        self.send_bytes(json.dumps(obj).encode(), code=code)

    def send_err(self, msg, code=400):
        self.drain()          # never reject a POST without reading its body
        self.send_json({"ok": False, "error": str(msg)}, code=code)

    def voice_proxy(self, method, path, q):
        """Hand /api/voice/* to the helper and its answer back, unchanged.

        The helper is a separate process (apps/voice/service.py) because torch
        can never live inside this program; forwarding is all the hub does. A
        first question can wait for the model to load, hence the long timeout.
        When nothing is listening, the words name what to start - that IS the
        fix, and no page has to guess it.
        """
        base, why_not = voice_service_url()
        if not base:
            return self.send_err(
                "the voice helper has no address - %s" % why_not, 500)
        try:
            target = base + (path[len("/api/voice"):] or "/")
            flat = {k: v[0] for k, v in q.items() if v}
            if flat:
                target += "?" + urllib.parse.urlencode(flat)
            # Built INSIDE the try: a bad saved address (no scheme) raises
            # here, and outside it killed the request thread with no answer.
            req = urllib.request.Request(
                target,
                data=self.body() if method == "POST" else None,
                method=method)
            req.add_header("Content-Type",
                           self.headers.get("Content-Type") or "application/json")
            with urllib.request.urlopen(req, timeout=180) as r:
                # The helper names its own type - /say answers audio/wav,
                # everything else json. Forcing a MIME here would turn the
                # sound into a download the browser refuses to play.
                return self.send_bytes(
                    r.read(), r.headers.get("Content-Type") or MIME[".json"])
        except urllib.error.HTTPError as e:
            # The helper's own honest error passes through with its code.
            return self.send_bytes(e.read(), MIME[".json"], e.code)
        except ValueError as e:
            # A saved helper address with no scheme lands here, not in
            # URLError - name the setting rather than dropping the request.
            return self.send_err(
                "the voice helper address is not usable (%s). Check it on "
                "the Voice tab." % e, 500)
        except (urllib.error.URLError, OSError) as e:
            reason = getattr(e, "reason", e)
            if isinstance(reason, TimeoutError) or isinstance(e, TimeoutError):
                # Three minutes gone is NOT the same as nobody listening:
                # sending someone to start the helper would be the wrong fix.
                return self.send_err(
                    "the voice helper did not answer within three minutes - "
                    "it may still be loading a model. Try again in a moment.",
                    504)
            return self.send_err(
                "the voice helper is not running on this PC (%s). Start it "
                "from the code folder:  python apps\\voice\\service.py" % e,
                503)

    def body(self, limit=0) -> bytes:
        """The request body, optionally with a ceiling.

        A firmware image arrives over the network as one POST, and this hub
        reads whatever Content-Length claims. Without a ceiling, one header
        saying two gigabytes is enough to take the hub down from anywhere on
        the venue WiFi — so the route that expects a big body names how big.
        """
        n = max(0, int(self.headers.get("Content-Length") or 0))
        if limit and n > limit:
            self._body_read = True
            raise ValueError("that is too big to accept (%d MB, limit %d MB)"
                             % (n // 1048576, limit // 1048576))
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
        n = max(0, int(self.headers.get("Content-Length") or 0))
        # Politeness has a limit. A refused request still has its body read so
        # the client sees the REASON rather than a dropped connection - but a
        # header claiming half a gigabyte is not politeness, it is the whole
        # hub blocked on one socket, and the gate refuses such a request before
        # anything else looks at it. Past the cap, drop the connection instead:
        # a rude client gets a rude answer, and the hub stays up.
        if n > DRAIN_LIMIT:
            self.close_connection = True
            self._body_read = True
            return
        if n:
            try:
                self.rfile.read(n)
            except Exception:  # noqa: BLE001
                pass
        self._body_read = True

    def log_message(self, fmt, *args):
        # args[0] is the request line for a normal log call — but log_error()
        # passes an HTTPStatus, and `"/api/robot" in HTTPStatus.NOT_IMPLEMENTED`
        # raises TypeError inside send_error(). The handler thread then dies
        # mid-reply and the client gets a reset connection instead of a clean
        # error. A bare `curl -I` (HEAD, which has no handler here) does it.
        first = str(args[0]) if args else ""
        if "/api/robot" in first or "/api/scan" in first:
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

    def dev_route(self, method: str, what: str, q):
        """One call to a module, whichever way it is reached.

        `what` is the part after /api/dev/ - cmd, status, files,
        download, delete or upload - and `q` carries `dev`, which says
        HOW: wifi:IP, usb:COM, usb:COM:busid, or hub:IP/... for a module
        on another PC's cable.

        Split out of route() on 2026-08-20 so /api/robot/* can be a shim
        over it rather than a second implementation. The two had already
        drifted: /api/robot/cmd guarded against a second show clock and
        the rest of /api/robot/* did not, and none of them could reach a
        module through another hub or behind a peer, which this path has
        done since A2-4.
        """
        dev = (q.get("dev") or [""])[0]
        # A module on ANOTHER PC's cable: hand the whole call to the hub
        # that owns it, unchanged. Everything downstream then works exactly
        # as it does locally — the same routes, the same module website,
        # the same Studio — because only the address had to change.
        try:
            hub_ip, inner = split_hub_dev(dev)
        except ValueError as e:
            return self.send_err(str(e))
        if hub_ip and is_self(hub_ip):
            # That address IS this PC. Handle it here rather than making an
            # HTTP round trip to ourselves — which works, but wastes a
            # request thread and hides the real device behind a hop. Caught
            # by check_shared_modules: forwarding to 127.0.0.2 (all of
            # 127.0.0.0/8 is loopback) came back PONG from our own fake.
            dev, hub_ip = inner, None
        if hub_ip:
            if self.headers.get("X-Mice-Forwarded"):
                return self.send_err(
                    "that module is not on this PC's cables", 502)
            try:
                body = self.body() if method == "POST" else None
                args = {k: v[0] for k, v in q.items() if v}
                args["dev"] = inner          # the address as THAT PC sees it
                # `path` does not exist here — dev_route only knows `what`,
                # the part after /api/dev/. Building the URL from a name that
                # is not in scope raised NameError on EVERY hub-to-hub
                # forward, and the except below turned it into "could not
                # reach the PC holding this module". Found by the A22-1 sweep.
                url = "http://%s:%d/api/dev/%s?%s" % (hub_ip, PORT, what,
                                                      urllib.parse.urlencode(args))
                req = urllib.request.Request(
                    url, data=body, method="POST" if body is not None else "GET")
                req.add_header("X-Mice-Forwarded", "1")
                with urllib.request.urlopen(req, timeout=10) as r:
                    out = r.read()
                    ctype = r.headers.get("Content-Type",
                                          "text/plain; charset=utf-8")
                return self.send_bytes(out, ctype)
            except urllib.error.HTTPError as e:
                if e.code == 401:
                    # THAT hub gates its own actions, and a session here is
                    # not a session there — the token is issued by one
                    # process and means nothing to another. Forwarding the
                    # cookie would not help, and letting a forwarded call
                    # through unchecked would mean anyone on the venue WiFi
                    # could set one header and drive the robot. So the
                    # person logs in there too, and is told so plainly.
                    return self.send_bytes(json.dumps({
                        "ok": False, "need_login": True, "hub": hub_ip,
                        "error": "that module is on %s — open http://%s:%d/ "
                                 "and log in there first" % (hub_ip, hub_ip, PORT),
                    }).encode(), MIME[".json"], 401)
                return self.send_err(
                    "the PC holding this module refused (%s): %s" % (hub_ip, e), 502)
            except Exception as e:           # noqa: BLE001
                return self.send_err(
                    "could not reach the PC holding this module (%s) — is it "
                    "still on and running the hub? %s" % (hub_ip, e), 502)
        try:
            if what == "cmd":
                c = (q.get("c") or [""])[0]
                # A motion command from the MODULE WEBSITE has to stop the
                # hub's show, exactly as one over /api/usb/cmd or
                # /api/robot/cmd does. This route was the hole: open
                # "⚙ Open module" on a robot the hub is playing, drag a
                # joint, and the show player kept sending POSE while the
                # page sent JOINT — two clocks on one arm, and the servos
                # fight. Done HERE and not inside dev_cmd(), or the show
                # player's own commands would stop the show.
                try:
                    k, a, b, _peer = parse_dev(dev)
                    check_takeover(k, a, b, c)
                except Exception:            # noqa: BLE001
                    pass                     # a bad dev fails below anyway
                return self.send_bytes(dev_cmd(dev, c).encode(),
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
                # THROUGH THE RELAY, so the board is watched once however many
                # people are looking. Piping each browser straight to the
                # board meant the second viewer opened a second stream and was
                # refused - correctly, because the board has one frame buffer
                # and take() reclaims the frame already on loan.
                relay = cam_relay.CamRelay.get(addr)
                relay.join()
                self.send_response(200)
                self.send_header("Content-Type",
                                 "multipart/x-mixed-replace; boundary=mice")
                self.send_header("Cache-Control", "no-store")
                # No length is possible: it ends when the viewer leaves. So
                # this one response opts out of keep-alive explicitly,
                # rather than leaving the browser waiting for a length.
                self.send_header("Connection", "close")
                self.close_connection = True
                self.end_headers()
                seen = 0
                try:
                    while True:
                        seen, jpeg = relay.next_frame(seen)
                        if jpeg is None:
                            break        # the camera went quiet; end honestly
                        self.wfile.write(
                            b"\r\n--mice\r\nContent-Type: image/jpeg\r\n"
                            b"Content-Length: " + str(len(jpeg)).encode() +
                            b"\r\n\r\n" + jpeg)
                except Exception:            # noqa: BLE001 - the browser
                    pass                      # closed the tab; that is normal
                finally:
                    relay.leave()
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

    def route(self, method: str):
        url = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(url.query)
        path = url.path

        if path.startswith("/api/"):
            # LOGIN FIRST, for anything that changes something. Reading stays
            # open: the module list, the status endpoints and the pages
            # themselves work with no password, because someone glancing at the
            # hub to see whether a board is alive should not have to type.
            if path in ("/api/login", "/api/logout", "/api/whoami",
                        "/api/version",
                        "/api/users", "/api/users/add", "/api/users/remove"):
                return self.auth_route(method, path)
            if hub_auth.gated(path, method) and not self.logged_in():
                self.drain()
                return self.send_bytes(
                    json.dumps({"ok": False, "need_login": True,
                                "error": "log in before doing that"}).encode(),
                    MIME[".json"], 401)
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
        if path == "/module.html":
            # The old USB-only control page is GONE — /mod is the module's own
            # website over every transport. The page that used to live here had
            # already been reduced to a JavaScript redirect, and it had drifted:
            # 8 joint sliders where the real module has 10, so a nong opened
            # through it could not reach WAIST or SHRUG at all.
            #
            # The URL stays, as a redirect, because a bookmark or a printed link
            # from before is not the user's mistake. ?port=COM5&id=2 was that
            # page's addressing; /mod speaks dev=usb:COM5:2.
            port = (q.get("port") or [""])[0]
            if not port:
                return self.send_redirect("/")
            bus = (q.get("id") or [""])[0]
            dev = "usb:" + port + ((":" + bus) if bus else "")
            return self.send_redirect(
                "/mod?" + urllib.parse.urlencode(
                    {"dev": dev, "name": (q.get("name") or [""])[0]}))
        # The one shared script: which theme the page is wearing. Served here
        # and compiled into the board's flash, exactly like the stylesheet, so
        # every surface gets the same behaviour from one file.
        if path == "/mice.js":
            f = SHARED_WEB / "mice.js"
            if f.is_file():
                return self.send_bytes(f.read_bytes(), "text/javascript; charset=utf-8")
            return self.send_err("mice.js is missing", 404)

        if path == "/mice.css":
            # One design system for every surface. This route must stay ABOVE
            # the studio fallback below, which would otherwise look for the
            # file in Studio's web folder and 404.
            # themes.css FIRST, then mice.css: the palette has to be defined
            # before the components that use it, and serving them as one file
            # means no page had to learn about a second stylesheet - and the
            # board, which serves this from flash, still serves one thing.
            return self.send_bytes(shared_css(), MIME[".css"])
        if path == "/rgb.html":     # RGB modes page (WiFi or USB target)
            return self.send_bytes((HUB_WEB / "rgb.html").read_bytes(), MIME[".html"])
        if path == "/pinout.svg":
            # TWO diagrams, and which one is right depends on the board. The
            # 38-pin WROOM reference is correct for nong and lift and simply
            # WRONG for an ESP32-CAM, whose GPIOs are nearly all spoken for by
            # the sensor - somebody wiring a servo to GPIO 26 because the
            # picture showed it free would be wiring it to the SCCB data line.
            #
            # The camera one is DRAWN from firmware/config/cam_boards.json, per
            # board, so it exists for every board the firmware knows and cannot
            # disagree with the wiring the firmware compiled. The WROOM one
            # stays a file: it is a real reference drawing of a real part, and
            # nothing generates that.
            board = (q.get("board") or [""])[0]
            if board:
                svg = cam_pinout_svg(board)
                if not svg:
                    return self.send_bytes(
                        b"", MIME[".svg"], 404)
                return self.send_bytes(svg.encode(), MIME[".svg"])
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
        # A23-1: each version carries its OWN copy of Studio under its mount,
        # so the comparison is whole-page, not a shared engine with two skins.
        if path == "/o/studio" or path == "/o/studio/":
            return self.send_bytes((OX_WEB / "studio" / "index.html").read_bytes(),
                                   MIME[".html"])
        if path == "/g/studio" or path == "/g/studio/":
            return self.send_bytes((GEMINI_WEB / "studio" / "index.html").read_bytes(),
                                   MIME[".html"])
        if path in ("/g", "/g/") or path in ("/o", "/o/"):
            # The two A23-1 versions' entry pages. Missing tree = an honest
            # empty state naming the folder that would hold it.
            base = GEMINI_WEB if path.startswith("/g") else OX_WEB
            idx = base / "hub.html"
            if not idx.is_file():
                return self.send_err("not built yet: %s" % base.name, 404)
            return self.send_bytes(idx.read_bytes(), MIME[".html"])
        if path.startswith("/g/"):
            base, rel = GEMINI_WEB, path[len("/g/"):]
        elif path.startswith("/o/"):
            base, rel = OX_WEB, path[len("/o/"):]
        elif path.startswith("/studio/"):
            base, rel = STUDIO_WEB, path[len("/studio/"):]
        elif path.startswith("/models/"):
            base, rel = MODELS, path[len("/models/"):]
        elif path.startswith("/hubweb/"):
            base, rel = HUB_WEB, path[len("/hubweb/"):]
        elif path.startswith("/docs/"):
            # Reference pages: PLAN.html (plan), ref.html (equations, references)
            base, rel = DATA / "docs", path[len("/docs/"):]
        else:
            # studio's absolute asset paths (/app.js, /style.css, /vendor/..)
            base, rel = STUDIO_WEB, path.lstrip("/")
        f = (base / rel).resolve()
        if base not in f.parents and f != base:
            return self.send_err("forbidden", 403)
        if not f.is_file():
            return self.send_err("not found: " + path, 404)
        self.send_bytes(f.read_bytes(), MIME.get(f.suffix.lower(), "application/octet-stream"))

    # ------------------------------------------------------------ login
    def logged_in(self) -> bool:
        """A forwarded call carries the ORIGINATING hub's cookie, which this
        hub cannot check — see the forwarding block in api(). It is answered
        there, against this hub's own session, so by the time it reaches here
        it has already been through the same gate."""
        return auth().valid(auth().token_of(self.headers.get("Cookie", "")))

    def logged_in_user(self) -> str:
        return auth().user_of(auth().token_of(self.headers.get("Cookie", "")))

    def auth_route(self, method: str, path: str):
        a = auth()
        if path == "/api/version":
            # WHAT THE OPEN TAB IS RUNNING. Asked 2026-08-20: *in web why i
            # need to refresh by my self to see the change*. The data on the
            # page refreshes itself every few seconds, but hub.html and the
            # stylesheets are fetched once, when the tab loads - so a change to
            # the interface is invisible until someone reloads, and nothing
            # says so.
            #
            # It sits with the OPEN routes on purpose: the login screen is one
            # of the pages that can go stale, and a version nobody may read
            # until they log in would not help there.
            #
            # THE EXE ITSELF CAN BE OLD TOO, and until 2026-08-21 nothing said
            # so: a hub built the day before answered every request happily
            # with four fixes missing. This is the endpoint every open tab
            # already polls, so the answer rides along here rather than costing
            # a second request. `build_stamp.state` caches and says nothing at
            # all when there is no source tree to compare against.
            st = build_stamp.state()
            return self.send_json({"ok": True, "version": web_version(),
                                   "stale": st["stale"],
                                   "staleWhy": build_stamp.why(st),
                                   "rebuild": build_stamp.REBUILD,
                                   "built": st["built"]})
        if path == "/api/whoami":
            # Never leaks the password, only whether one has to be typed. The
            # page needs this to decide what to grey out.
            return self.send_json({
                "ok": True,
                "authed": self.logged_in(),
                "users": a.users() if self.logged_in() else [],
                "locked_for": a.locked_for(self.client_address[0]),
                "lock_seconds": hub_auth._LOCK_SECONDS,   # noqa: SLF001
            })
        if path == "/api/users":
            # Names only, never a hash. Behind the login because the list of
            # who can drive a robot is not something a stranger needs.
            if not self.logged_in():
                return self.send_bytes(json.dumps(
                    {"ok": False, "need_login": True,
                     "error": "log in to see the accounts"}).encode(),
                    MIME[".json"], 401)
            return self.send_json({"ok": True, "users": a.users(),
                                   "max": hub_auth.MAX_USERS})

        if method != "POST":
            return self.send_err("POST only", 405)

        if path in ("/api/users/add", "/api/users/remove"):
            if not self.logged_in():
                return self.send_bytes(json.dumps(
                    {"ok": False, "need_login": True,
                     "error": "log in first"}).encode(), MIME[".json"], 401)
            try:
                body = json.loads(self.body().decode() or "{}")
            except ValueError:
                body = {}
            name = str(body.get("user") or "").strip()
            
            if self.logged_in_user() != "super_admin":
                ok, why = False, "only super_admin can manage accounts"
            elif path.endswith("/add"):
                ok, why = a.add_user(name, str(body.get("password") or ""))
            else:
                ok, why = a.remove_user(name)
            return self.send_bytes(
                json.dumps({"ok": ok, "error": why, "users": a.users()}).encode(),
                MIME[".json"], 200 if ok else 400)

        if path == "/api/logout":
            a.logout(a.token_of(self.headers.get("Cookie", "")))
            return self.send_bytes(
                json.dumps({"ok": True}).encode(), MIME[".json"], 200,
                headers=[("Set-Cookie",
                          "%s=; Path=/; Max-Age=0; SameSite=Lax" % hub_auth.COOKIE)])
        # /api/login
        try:
            body = json.loads(self.body().decode() or "{}")
        except ValueError:
            body = {}
        token, why = a.login(str(body.get("password") or ""),
                             self.client_address[0],
                             user=str(body.get("user") or "") or None)
        if not token:
            # 401 with the REASON: wrong password and locked out need different
            # actions from the person, so they must not look the same.
            return self.send_bytes(
                json.dumps({"ok": False, "error": why,
                            "locked_for": a.locked_for(self.client_address[0])}).encode(),
                MIME[".json"], 401)
        return self.send_bytes(
            json.dumps({"ok": True}).encode(), MIME[".json"], 200,
            headers=[("Set-Cookie",
                      "%s=%s; Path=/; HttpOnly; SameSite=Lax" % (hub_auth.COOKIE, token))])

    # ------------------------------------------------------------- API
    def api(self, method: str, path: str, q):
        # ---- unified device API: same for WiFi and USB/RS485 (dev=...) ----
        # These back the one module website served at /mod?dev=... so it is
        # identical over every transport.
        if path.startswith("/api/dev/"):
            return self.dev_route(method, path[len("/api/dev/"):], q)

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
                return self.send_json({"ok": False, "apps": [],
                                       "error": "registry unavailable"})
            # A MALFORMED app.json IS THE LIKELY FAULT, and it used to be the
            # worst-reported one: registry.apps() raises RegistryError naming
            # the file and the line, nothing caught it, the request became a
            # 500, and the page said *the hub may have stopped* - which is
            # false, and throws away the only detail that fixes it. Answer with
            # the reason instead, so the screen can print the file and line.
            try:
                out = [{k: a[k] for k in ("id", "name", "blurb", "icon",
                                          "path", "order", "help")}
                       for a in registry.apps() if a.get("show", True)]
            except Exception as e:                          # noqa: BLE001
                return self.send_json({"ok": False, "apps": [],
                                       "error": str(e)[:300]})
            return self.send_json({"ok": True, "apps": out})

        if path == "/api/access":
            # Which pages work with no login, and which cards on the hub ask
            # first. Open on purpose: a page has to be able to draw itself
            # before anybody has signed in, and this says nothing secret - it
            # is the same list a person can read on the help page.
            #
            # Read per request, never cached: a designer editing the file
            # should see the screen change on the next refresh, not after a
            # restart. That is the same bargain config/voice.json already made.
            return self.send_json(read_page_access())

        if path == "/api/partners":
            # Where each outside program lives, and what each of its event
            # sources can and cannot report. Open like /api/access and for the
            # same reason: a page shows the tile before anybody has signed in,
            # and there is nothing secret in an address.
            return self.send_json(read_partners())

        if path == "/api/partners/start":
            # Starts a program on this PC, so it is gated (hub_auth.GATED).
            # Safe to press repeatedly: a part already up or loading is left be.
            pid = (q.get("id") or [""])[0]
            got = read_partners()
            entry = (got.get("partners") or {}).get(pid)
            if not entry:
                return self.send_json({"ok": False, "error": got.get("error") or
                                       "config/partners.json has no entry called %r" % pid})
            return self.send_json(partner_launch.start(pid, entry))

        if path == "/api/voice" or path.startswith("/api/voice/"):
            if path == "/api/voice/health":
                base, why_not = voice_service_url()
                if base:
                    try:
                        urllib.request.urlopen(base + "/health", timeout=0.5).read()
                    except Exception:
                        import subprocess
                        script = HERE.parent / "apps" / "voice" / "service.py"
                        if script.is_file():
                            subprocess.Popen([sys.executable, str(script)], cwd=str(HERE.parent))
                            # Poll for up to 8 seconds while it imports torch/models
                            for _ in range(16):
                                time.sleep(0.5)
                                try:
                                    if urllib.request.urlopen(base + "/health", timeout=0.5).getcode() == 200:
                                        break
                                except Exception:
                                    pass
            return self.voice_proxy(method, path, q)

        if path == "/api/scan":
            force = (q.get("force") or ["0"])[0] == "1"
            return self.send_json({"ok": True, "lan": lan_ip(),
                                   "modules": scan_modules(force),
                                   "ports": serial_ports()})

        if path == "/api/app/version":
            me = app_here()
            if not me:
                return self.send_json({"ok": True, "sha": "", "bytes": 0,
                                       "why": "this hub runs from source, so "
                                              "it has no app to hand out"})
            exe, size, sha = me
            return self.send_json({"ok": True, "sha": sha, "bytes": size,
                                   "when": time.strftime(
                                       "%Y-%m-%dT%H:%M:%SZ",
                                       time.gmtime(exe.stat().st_mtime)),
                                   "host": socket.gethostname()})
        if path == "/api/app":
            # A browser cannot reach that PC's serial ports at any address, so
            # the PC has to run something that can. This is it.
            me = app_here()
            if not me:
                return self.send_err("this hub runs from source - there is no "
                                     "built app to download", 404)
            exe, _size, _sha = me
            return self.send_bytes(
                exe.read_bytes(), "application/octet-stream",
                headers=(("Content-Disposition",
                          "attachment; filename=MiceHub.exe"),))
        if path == "/api/selfupdate":
            # METHOD FIRST. A plain `if path ==` that answers the GET makes the
            # POST below unreachable, so the button would report state and
            # never update.
            if method == "POST":
                ok, msg = do_update()
                return self.send_json({"ok": ok, "message": msg})
            return self.send_json(update_state())
        if path == "/api/diag":
            # PLAIN TEXT, not JSON: a person pastes this into a message, and
            # they should be able to read what they are handing over before
            # they send it. Open like the rest of reading - and it carries no
            # password, which check_diagnostics enforces rather than trusts.
            return self.send_bytes(diagnostics().encode("utf-8"),
                                   "text/plain; charset=utf-8")
        if path == "/api/report" and method == "POST":
            # A REPORT anyone can send — no login, no password, stored machine-local.
            # The page sends: text, page, module, build, time, attachDiag (bool).
            # We add: client IP, user agent, and if attachDiag, the diagnostics text.
            # Saved as one JSON file per report under HERE/reports/ (never promoted).
            # json/uuid come from the module imports - a local import here made
            # the names local to this WHOLE router function, and every endpoint
            # that reads them earlier (pairing, saves, OTA, play) died with
            # UnboundLocalError. 33 red checks from two lines.
            try:
                length = int(self.headers.get("Content-Length", 0))
                if length > 1048576:
                    # This endpoint is deliberately open, so the cap is not
                    # optional: a lying Content-Length must not become RAM.
                    # Same rudeness rule as drain() - past the cap, drop the
                    # connection instead of reading it.
                    self.close_connection = True
                    self._body_read = True
                    return self.send_json({"ok": False,
                                           "error": "that report is too big"})
                raw = self.rfile.read(length).decode("utf-8") if length else "{}"
                data = json.loads(raw)
            except Exception:
                return self.send_json({"ok": False, "error": "bad json"})
            text = (data.get("text") or "").strip()[:4000]
            if not text:
                return self.send_json({"ok": False, "error": "empty"})
            page = str(data.get("page") or "")[:60]
            module = str(data.get("module") or "")[:60]
            build = str(data.get("build") or "")[:80]
            # The visitor's clock lands in a FILENAME below, so it is stripped
            # to plain characters first - an unfiltered ..\..\ wrote the
            # report wherever it pointed on this PC (A22-1 panel, 2026-08-25).
            t = "".join(ch for ch in str(data.get("time") or "")
                        if ch.isalnum() or ch in "-T:.Z ")[:40]
            attach = bool(data.get("attachDiag"))
            # Build the report record
            report = {
                "id": uuid.uuid4().hex[:12],
                "time": t or time.strftime("%Y-%m-%dT%H:%M:%S"),
                "text": text,
                "page": page,
                "module": module,
                "build": build,
                "attachDiag": attach,
                "client": self.client_address[0] if self.client_address else "",
                "ua": self.headers.get("User-Agent", "")[:200],
            }
            if attach:
                try:
                    report["diag"] = diagnostics()
                except Exception:
                    report["diag"] = "diagnostics unavailable"
            # Write to HERE/reports/ (not SKIP_FILES - those are for promote.py)
            # but a sibling of the hub: machine-local, never in source.
            rep_dir = HERE / "reports"
            rep_dir.mkdir(exist_ok=True)
            fname = rep_dir / (report["time"].replace(":", "-") + "_" + report["id"] + ".json")
            try:
                write_atomic(fname, json.dumps(report, ensure_ascii=False, indent=2))
            except Exception as e:
                return self.send_json({"ok": False, "error": "write failed: " + str(e)})
            # English lands in the file later; the visitor's own words are
            # already saved, so nothing waits on the model here.
            threading.Thread(target=_translate_report_later,
                             args=(fname, text), daemon=True).start()
            return self.send_json({"ok": True, "id": report["id"]})
        if path == "/api/reports" and method == "GET":
            # LIST reports for the complaints screen — no login, anyone can see.
            # Returns: [ {id, time, text, text_en, page, module, build, status, ...} ]
            # text_en was translated ONCE when the report was filed (see
            # _translate_report_later); empty means no translation yet and the
            # pages fall back to the original words. No model call here - a
            # list refresh must be instant even with the helper switched off.
            rep_dir = HERE / "reports"
            if not rep_dir.is_dir():
                return self.send_json({"ok": True, "reports": []})
            out = []
            # Read under the SAME lock the writers hold: on Windows an open
            # read handle makes the writers' os.replace fail, so an unlocked
            # list refresh could eat a just-finished translation.
            with _reports_lock:
                for f in sorted(rep_dir.glob("*.json"), reverse=True):
                    try:
                        data = json.loads(f.read_text(encoding="utf-8"))
                    except Exception:
                        continue          # a corrupt sibling, not ours
                    # Never send diag in the list - only the summary fields.
                    # A closed report keeps its file so the next person finds it.
                    out.append({
                        "id": data.get("id"),
                        "time": data.get("time"),
                        "text": data.get("text") or "",
                        "text_en": data.get("text_en") or "",
                        "page": data.get("page"),
                        "module": data.get("module"),
                        "build": data.get("build"),
                        "status": data.get("status", "open"),
                        "client": data.get("client", ""),
                    })
            return self.send_json({"ok": True, "reports": out})
        if path == "/api/reports" and method == "POST":
            # UPDATE a report status: {id: "...", status: "fixed" | "not-a-problem"}
            # No login — the point is a designer can close it from the screen.
            import json as _json
            try:
                length = int(self.headers.get("Content-Length", 0))
                raw = self.rfile.read(length).decode("utf-8") if length else "{}"
                data = _json.loads(raw)
            except Exception:
                return self.send_json({"ok": False, "error": "bad json"})
            rid = (data.get("id") or "").strip()
            status = (data.get("status") or "").strip()
            if not rid or status not in ("fixed", "not-a-problem", "open"):
                return self.send_json({"ok": False, "error": "bad payload"})
            rep_dir = HERE / "reports"
            if not rep_dir.is_dir():
                return self.send_json({"ok": False, "error": "not found"})
            for f in rep_dir.glob("*.json"):
                try:
                    # Read under the SAME lock as the writer: a copy taken
                    # outside it can put back a version without the other's
                    # change (the translation vanishing again).
                    with _reports_lock:
                        try:
                            j = _json.loads(f.read_text(encoding="utf-8"))
                        except Exception:
                            continue            # a corrupt sibling, not ours
                        if j.get("id") != rid:
                            continue
                        j["status"] = status
                        write_atomic(f, _json.dumps(j, ensure_ascii=False, indent=2))
                except Exception as e:
                    return self.send_json(
                        {"ok": False, "error": "could not save: %s" % e})
                return self.send_json({"ok": True})
                return self.send_json({"ok": True})
            return self.send_json({"ok": False, "error": "not found"})
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

        # ---- what THIS PC holds on its own cables --------------------------
        # Another hub calls this every few seconds, so it is deliberately cheap
        # and cache-backed: probe_usb_all(False) reuses the 8 s cache. Forcing
        # a fresh probe here would let two PCs watching each other keep every
        # cable permanently busy and starve their own users of the port.
        if path == "/api/modules":
            # ONE list, merged on the chip. See modules_here.
            force = (q.get("force") or ["0"])[0] == "1"
            try:
                mods = modules_here(force)
            except Exception as e:               # noqa: BLE001
                return self.send_err(e)
            return self.send_json({"ok": True, "modules": mods,
                                   "lan": lan_ip()})

        if path == "/api/pinout":
            # Which drawing belongs with the board being looked at. Reading it
            # changes nothing, so it needs no login - the pin card is exactly
            # what somebody reads before they touch a wire.
            dev = (q.get("dev") or [""])[0]
            if not dev:
                return self.send_json({"ok": False, "error": "no dev"})
            return self.send_json(dict(pinout_for(dev), ok=True))
        if path == "/api/mine":
            mods = []
            for u in probe_usb_all(False):
                m = u.get("module")
                # A CABLE WITH NO BOARD OF ITS OWN STILL HAS BOARDS BEHIND IT.
                # `continue` here skipped the whole port, and the bus loop
                # below sits inside it - so a plain USB-to-RS485 dongle listed
                # nothing at all, and a module reachable ONLY over the bus was
                # invisible to this screen and to every other hub. Measured
                # 2026-08-21: probe_usb_port(COM23) found board 67 behind the
                # dongle while /api/mine returned four modules without it.
                if m:
                    mods.append({"dev": "usb:" + u["port"],
                                 "name": m.get("name") or u["port"],
                                 "type": m.get("type", ""), "id": m.get("id"),
                                 "group": m.get("group", ""), "via": u["port"]})
                for b in (u.get("rs485") or []):
                    mods.append({"dev": "usb:%s:%s" % (u["port"], b.get("id")),
                                 "name": b.get("name") or ("id %s" % b.get("id")),
                                 "type": b.get("type", ""), "id": b.get("id"),
                                 "group": b.get("group", ""),
                                 "via": "%s #%s" % (u["port"], b.get("id"))})
            # `url` is the address this hub can be reached at from ANOTHER
            # device - the same one the QR encodes, computed in one place. The
            # page cannot work it out itself: the hub is usually opened as
            # 127.0.0.1, and 127.0.0.1 is the single address on the network
            # that a phone cannot use.
            ns = NAME_SERVER[0]
            return self.send_json({"ok": True, "host": socket.gethostname(),
                                   "url": "http://%s:%d/" % (lan_ip(), PORT),
                                   # The NAME, and honestly whether it works.
                                   # Printing mice.local while nothing answers
                                   # it sends people down a hole.
                                   "name_url": ("http://%s:%d/" % (ns.name, PORT)
                                                if ns and not ns.error else ""),
                                   "name_why": (ns.error if ns else "not started"),
                                   "modules": mods})

        # ---- every module on every PC, this one included --------------------
        # scan_hubs() already finds the other hubs on this subnet (it is what
        # the Studio settings transfer uses). This asks each of them what it is
        # holding, and rewrites the address so it means the same module FROM
        # HERE: hub:<their ip>/<their dev>.
        if path == "/api/allmods":
            # The FLAT list of what other PCs hold, one entry per way in. The
            # Firmware tab wants exactly this (it sends an image to a named
            # port on a named PC). The merged one-row-per-board list is
            # /api/modules/all.
            force = (q.get("force") or ["0"])[0] == "1"
            out, errs = remote_modules(force)
            return self.send_json({"ok": True, "modules": out, "errors": errs})

        if path == "/api/modules/all":
            # ONE LIST. Every module any hub here can reach, each board once,
            # carrying every route including which PC it goes through.
            force = (q.get("force") or ["0"])[0] == "1"
            try:
                mods, errs = modules_everywhere(force)
            except Exception as e:               # noqa: BLE001
                return self.send_err(e)
            return self.send_json({"ok": True, "modules": mods, "errors": errs,
                                   "host": socket.gethostname(), "lan": lan_ip()})

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
        # The cable spelling of the same call - see the /api/robot/* note above.
        # Studio uses this one so a module site and Studio can share one cable
        # (usb transport -> cableCmd), and it was the third implementation of
        # "send this command to that module". `usb:COM` and `usb:COM:busid` are
        # exactly what dev_route already understands.
        if path == "/api/usb/cmd":
            port = (q.get("port") or [""])[0]
            c = (q.get("c") or [""])[0]
            bus = (q.get("id") or ["0"])[0] or "0"
            if not port or not c:
                return self.send_err("need port and c")
            dev = "usb:" + port + ((":" + bus) if bus not in ("", "0") else "")
            inner = dict(q)
            inner["dev"] = [dev]
            return self.dev_route(method, "cmd", inner)

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
        # Watching a write that is happening on ANOTHER PC. The page cannot
        # ask that hub directly - it is a different origin, so the browser
        # sends no cookie and the answer is refused - so this hub asks for it.
        if path == "/api/flash/at":
            ip = (q.get("ip") or [""])[0]
            try:
                with urllib.request.urlopen(
                        "http://%s:%d/api/flash" % (ip, PORT), timeout=8) as r:
                    return self.send_bytes(r.read(), MIME[".json"])
            except Exception as e:            # noqa: BLE001
                return self.send_json({"running": False, "ok": False,
                                       "error": "%s is not answering (%s)" % (ip, e)})

        # ---- flashing from ANOTHER PC (see remote_payload) ----
        # The image arrives over the network and esptool runs HERE, because
        # this is the PC holding the cable. Gated: it is the most destructive
        # thing this hub can be asked to do.
        if path == "/api/flash/remote" and method == "POST":
            try:
                d = json.loads(self.body(48 * 1048576).decode())
                return self.send_json(flasher.start_received(
                    d.get("port", ""), d.get("type", ""),
                    d.get("parts") or [], d.get("from", "another PC")))
            except Exception as e:            # noqa: BLE001
                return self.send_err(e)

        # ...and the other half: hand THIS PC's image to the hub that has the
        # cable. The operator names that hub and logs into it here, because a
        # hub does not hold another hub's password.
        if path == "/api/flash/send" and method == "POST":
            try:
                d = json.loads(self.body().decode())
                return self.send_json(send_firmware(
                    d.get("to", ""), d.get("port", ""), d.get("type", ""),
                    d.get("user", ""), d.get("password", "")))
            except Exception as e:            # noqa: BLE001
                return self.send_err(e)

        # ---- the way a phone gets here ----
        # Printed addresses do not survive a venue: someone reads 192.168.137.1
        # off a laptop across the room and types 192.168.13.71. A QR is the
        # only address that cannot be mistyped, and it works where mDNS does
        # not - which is most places, because venue networks block multicast.
        if path == "/api/qr":
            text = (q.get("text") or [""])[0] or ("http://%s:%d/" % (lan_ip(), PORT))
            try:
                return self.send_bytes(qr.svg(text).encode(),
                                       "image/svg+xml; charset=utf-8")
            except ValueError as e:               # too long to encode
                return self.send_err(e)

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
                # The board's OWN login, when it is not the shipped one. Read
                # from the body as well as the query so a password never has
                # to travel in a URL, where it lands in every access log.
                try:
                    d = json.loads(self.body().decode() or "{}")
                except ValueError:
                    d = {}
                return self.send_json(flasher.start_ota(
                    (q.get("ip") or [""])[0], (q.get("type") or [""])[0],
                    user=str(d.get("user") or (q.get("user") or [""])[0]),
                    password=str(d.get("password") or (q.get("password") or [""])[0])))
            except Exception as e:            # noqa: BLE001
                return self.send_err(e)
        # and the same job again over the COMMAND channel, which is the only
        # one an RS485 board has — see Flash.start_bus. `dev` is an ordinary
        # dev address, so this reaches a cable, the bus, WiFi, a module behind
        # another module's hotspot, or a module on another PC, unchanged.
        if path == "/api/flash/bus" and method == "POST":
            try:
                return self.send_json(flasher.start_bus(
                    (q.get("dev") or [""])[0], (q.get("type") or [""])[0]))
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
        # ---- live audio to a module's speaker (A24-32) ----
        # POST /api/stream/start  {dev|ip, port, rate, file}
        # POST /api/stream/feed   raw 16-bit mono PCM, from the browser capture
        # POST /api/stream/stop   |  GET /api/stream  where it is up to
        if path == "/api/stream/start" and method == "POST":
            try:
                d = json.loads(self.body().decode() or "{}")
                dev = str(d.get("dev") or "")
                ip = str(d.get("ip") or "")
                if dev and not ip:
                    kind, addr, _bus, _peer = parse_dev(dev)
                    if kind != "wifi":
                        return self.send_err(
                            "live audio goes over WiFi - open this module over "
                            "WiFi, or give its address", 501)
                    ip = addr.split(":")[0]
                port = int(d.get("port") or stream_audio.DEF_PORT)
                rate = int(d.get("rate") or stream_audio.DEF_RATE)
                # The BOARD is told first: it must be listening before the
                # first datagram, or the start of the sound is simply gone.
                said = dev_cmd(dev or ("wifi:" + ip),
                               "STREAM ON %d %d" % (port, rate))
                if not said.startswith("OK"):
                    return self.send_err("the board refused the stream: " + said)
                st = streamer.start(ip, port, rate, str(d.get("name") or "live"))
                if d.get("file"):
                    pcm = stream_audio.wav_pcm(SEQUENCES.parent / "music"
                                               / safe_name(str(d["file"])), rate)
                    threading.Thread(target=streamer.feed_all, args=(pcm,),
                                     daemon=True).start()
                return self.send_json({"ok": True, "board": said, **st})
            except Exception as e:            # noqa: BLE001
                return self.send_err(e)
        if path == "/api/stream/feed" and method == "POST":
            took = streamer.feed(self.body())
            return self.send_json({"ok": True, "took": took,
                                   "queued": streamer.q.qsize()})
        if path == "/api/stream/stop" and method == "POST":
            st = streamer.stop()
            try:
                if st.get("ip"):
                    dev_cmd("wifi:" + st["ip"], "STREAM OFF")
            except Exception as e:            # noqa: BLE001
                st["error"] = str(e)
            return self.send_json({"ok": True, **st})
        if path == "/api/stream":
            return self.send_json({"ok": True, **streamer.status()})

        if path == "/api/stream/voice" and method == "POST":
            try:
                data = json.loads(self.body().decode())
                text = data.get("text")
                dev = data.get("dev")
                req = urllib.request.Request("http://127.0.0.1:8767/say", data=json.dumps({"text": text, "lang": ""}).encode(), headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=10) as r:
                    wav_bytes = r.read()
                import io, wave
                with wave.open(io.BytesIO(wav_bytes)) as w:
                    pcm = w.readframes(w.getnframes())
                    rate = w.getframerate()
                kind, addr, _, _ = parse_dev(dev)
                ip = addr.split(":")[0]
                dev_cmd(dev, "STREAM ON %d %d" % (stream_audio.DEF_PORT, rate))
                streamer.start(ip, stream_audio.DEF_PORT, rate, "voice")
                threading.Thread(target=streamer.feed_all, args=(pcm,), daemon=True).start()
                return self.send_json({"ok": True})
            except Exception as e:
                return self.send_err(str(e))

        if path == "/api/play/stop":
            return self.send_json(show.stop())

        if path == "/api/stopall" and method == "POST":
            # EVERYTHING, AT ONCE. The show clock first, because it is what
            # keeps sending new positions - stopping the boards while the clock
            # runs means the next tick starts them moving again. Then every
            # board the hub can reach, each one told directly rather than by
            # broadcast: a broadcast reaches whatever is listening, and the
            # answer to "did it stop?" has to be per board or it is not an
            # answer.
            #
            # It never asks first. A stop that needs confirming is a stop that
            # arrives after the thing you were trying to prevent.
            stopped, failed, slow = [], [], []
            try:
                show.stop(freeze=False, why="somebody pressed stop")
            except Exception:                              # noqa: BLE001
                pass
            mods = [m for m in modules_here() if m.get("routes")]

            # ONE THREAD PER BOARD, ALL AT ONCE. Stopping them in a row meant
            # each stop queued behind whatever that cable was already doing -
            # a flash holds its port lock for up to 30s (FWEND) - so the last
            # board waited for every board before it (A22-1 panel, 2026-08-25).
            def _stop_one(m, out):
                who = ("#%s %s" % (m.get("id"), m.get("name") or "")).strip()
                # The first route that answers is enough - the board is one
                # board however many ways in it has.
                for r in m.get("routes") or []:
                    try:
                        dev_cmd(r.get("dev"), "MOVE STOP")
                        out.append((who, True))
                        return
                    except Exception:                      # noqa: BLE001
                        continue
                out.append((who, False))

            # `got` must exist BEFORE the comprehension runs - a tuple
            # assignment evaluates the whole right side first, and the
            # threads' args referenced it while it was still unborn.
            got = []
            threads = [
                threading.Thread(target=_stop_one, args=(m, got), daemon=True)
                for m in mods]
            for th in threads:
                th.start()
            deadline = time.time() + PEER_WAIT + 2
            for th in threads:
                th.join(max(0.1, deadline - time.time()))
            for who, done in got:
                (stopped if done else failed).append(who)
            said = {w for w, _d in got}
            slow = [(" #%s %s" % (m.get("id"), m.get("name") or "")).strip()
                    for m in mods
                    if ("#%s %s" % (m.get("id"), m.get("name") or "")).strip()
                    not in said]
            return self.send_json({"ok": not failed, "stopped": stopped,
                                   "failed": failed, "slow": slow})

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

        if path == "/api/seqsteps":
            # The same file loadseq serves, PARSED for POST /api/play - the
            # voice answer that moves a robot needs steps, not yaml text.
            # Reads only, so it is ungated like loadseq; starting the show
            # still goes through gated /api/play.
            name = safe_name((q.get("name") or [""])[0])
            f = SEQUENCES / name
            if not f.is_file():
                return self.send_err("no sequence " + name, 404)
            try:
                got = seq_steps(f.read_text(encoding="utf-8"))
            except ValueError as e:
                return self.send_err("cannot play %s: %s" % (name, e))
            if len(got["steps"]) < 2:
                return self.send_err(
                    "%s has fewer than two poses - nothing to play" % name)
            return self.send_json({"ok": True, "file": name, **got})

        if path == "/api/save" and method == "POST":
            data = json.loads(self.body().decode())
            name = safe_name(data["name"])
            if not name.endswith(".json"):
                name += ".json"
            existed = (PROJECTS / name).exists()
            write_atomic(PROJECTS / name,
                         json.dumps(data["project"], indent=1))
            # `existed` goes back so the editor can say "replaced my_move.json"
            # rather than letting a name collision pass in silence. The default
            # name in the editor is "my_move", so saving over someone else's
            # project is one careless click.
            return self.send_json({"ok": True, "file": name, "replaced": existed})

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
            # The tuned rig is the most expensive thing in this project to
            # rebuild by hand, so it never gets truncated in place.
            write_atomic(STUDIO / "rig_default.json", json.dumps(rig, indent=1))
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
            write_atomic(SETTINGS_FILE, json.dumps(bundle, indent=1))
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

        # A hub the sweep cannot reach, named by a person. Gated: it changes
        # what this hub talks to.
        if path in ("/api/hubs/add", "/api/hubs/forget") and method == "POST":
            try:
                d = json.loads(self.body().decode() or "{}")
                have = remember_hub(d.get("ip"), forget=path.endswith("forget"))
                return self.send_json({"ok": True, "hubs": have})
            except Exception as e:                 # noqa: BLE001
                return self.send_err(e)

        if path == "/api/hubs":
            # Other mice hubs on this network, so nobody has to type an IP.
            return self.send_json({"ok": True, "known": known_hubs(),
                                   "hubs": scan_hubs(
                                       (q.get("force") or ["0"])[0] == "1")})

        # ---- pairing: one login on every PC (A14-1) ----
        # Three of these are gated like any other change. The fourth cannot be
        # — see /api/pair/claim below.
        if path == "/api/pair/status":
            code, left = PAIRING.showing()
            return self.send_json({"ok": True, "showing": bool(code),
                                   "code": hub_pair.pretty(code),
                                   "seconds": left,
                                   "host": socket.gethostname(),
                                   "users": auth().users()})

        if path == "/api/pair/start" and method == "POST":
            code, secs = PAIRING.start()
            return self.send_json({"ok": True, "showing": True,
                                   "code": hub_pair.pretty(code),
                                   "seconds": secs,
                                   "host": socket.gethostname(),
                                   "users": auth().users()})

        if path == "/api/pair/stop" and method == "POST":
            PAIRING.stop()
            return self.send_json({"ok": True, "showing": False,
                                   "code": "", "seconds": 0})

        if path == "/api/pair/claim" and method == "POST":
            # DELIBERATELY OUTSIDE THE LOGIN (hub_auth.CODE_GATED). The hub
            # asking has no account here — that is the thing being fixed — so
            # the code is the credential. It dies after five wrong tries, so
            # leaving this open costs one guess in 32^8 per code shown.
            try:
                d = json.loads(self.body().decode() or "{}")
            except ValueError:
                d = {}
            ok, why = PAIRING.claim(str(d.get("code") or ""))
            if not ok:
                return self.send_bytes(
                    json.dumps({"ok": False, "error": why}).encode(),
                    MIME[".json"], 401)
            return self.send_json({"ok": True, "host": socket.gethostname(),
                                   "accounts": auth().export_accounts()})

        if path == "/api/pair/link" and method == "POST":
            try:
                d = json.loads(self.body().decode() or "{}")
            except ValueError:
                d = {}
            try:
                return self.send_json(dict({"ok": True}, **pair_with(
                    d.get("ip"), d.get("code"), replace=bool(d.get("replace")))))
            except Exception as e:                 # noqa: BLE001
                return self.send_err(e)

        if path == "/api/export" and method == "POST":
            data = json.loads(self.body().decode())
            name = safe_name(data["name"])
            if not name.endswith(".yaml"):
                name += ".yaml"
            existed = (SEQUENCES / name).exists()
            write_atomic(SEQUENCES / name, data["yaml"], newline="\n")
            return self.send_json({"ok": True, "file": name, "replaced": existed,
                                   "path": str((SEQUENCES / name))})

        # ---- robot proxy (dodges CORS) ----
        # /api/robot/* IS /api/dev/* OVER WIFI. It is the older spelling, still
        # used by Nong Studio and anything that learned the hub before cables
        # were reachable, and it was a SECOND implementation of the same five
        # calls. The two had already drifted: only /api/robot/cmd guarded
        # against a second show clock, and none of these could reach a module
        # through another hub or behind a peer - which the dev path has done
        # since A2-4. So they are shims now: same address, one code path.
        if path.startswith("/api/robot/") and path != "/api/robot/upload":
            what = path[len("/api/robot/"):]
            if what not in ("cmd", "status", "files", "download", "delete"):
                return self.send_err("unknown robot call: " + what)
            ip = (q.get("ip") or [""])[0]
            if not ip:
                return self.send_err("need ip")
            if what == "cmd" and not (q.get("c") or [""])[0]:
                return self.send_err("need ip and c")
            inner = dict(q)
            inner["dev"] = ["wifi:" + ip]
            return self.dev_route(method, what, inner)

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
    def robot_get(ip: str, path: str, timeout=None) -> bytes:
        if not re.match(r"^[A-Za-z0-9._-]+(:\d+)?$", ip):
            raise ValueError("bad module address")

        def once(cookie=None):
            headers = hub_header()
            if cookie:
                headers["Cookie"] = "%s=%s" % (BOARD_COOKIE, cookie)
            req = urllib.request.Request("http://%s%s" % (ip, path),
                                         headers=headers)
            # 6 s suits every ordinary command. FWEND does not: the board
            # verifies the md5 of a whole 1.3 MB image before it will boot into
            # it. See dev_cmd — a timeout there would report a failed update
            # for one that worked.
            with urllib.request.urlopen(req, timeout=timeout or 6) as r:
                return r.read()

        try:
            return once(_board_cookies.get(ip))
        except urllib.error.HTTPError as e:
            if e.code != 401:
                raise
        # The board refused the command as a stranger. Log in — the shipped
        # account unless the caller gave this board its own earlier — and ask
        # once more as a session.
        cookie, why = board_login(ip)
        if not cookie:
            raise RuntimeError(why or ("the module at %s wants its own login"
                                       % ip)) from None
        _board_cookies[ip] = cookie
        return once(cookie)


def _robot_post(ip: str, path: str, body: bytes, ctype: str, timeout=20) -> bytes:
    """POST to a board, logging in if it asks - the twin of robot_get.

    Uploads went out as a STRANGER: robot_get has carried a board session
    since the boards grew a login, and this path never did, so every upload
    through the hub over WiFi died on `HTTP Error 401: Unauthorized` while
    commands to the same board worked. Reported by the user 2026-09-07 with
    that exact line on screen (A24-33).
    """
    def once(cookie=None):
        headers = {"Content-Type": ctype}
        if cookie:
            headers["Cookie"] = "%s=%s" % (BOARD_COOKIE, cookie)
        req = urllib.request.Request("http://%s%s" % (ip, path), data=body,
                                     method="POST", headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()

    try:
        return once(_board_cookies.get(ip))
    except urllib.error.HTTPError as e:
        if e.code != 401:
            raise
    cookie, why = board_login(ip)
    if not cookie:
        raise RuntimeError(why or ("the module at %s wants its own login" % ip))
    _board_cookies[ip] = cookie
    return once(cookie)


def start_short_name(port=80):
    """Answer on port 80 as well, only to send people to the real one.

    Asked for on 2026-08-19: why type mice.local:8642 rather than mice.local.
    Because a bare name means port 80, and the hub is not there.

    Moving the hub TO port 80 would be the obvious fix and the wrong one: on
    Windows something else often holds it - IIS, Skype, another dev server -
    and the hub would then fail to start at all, which reads as the app being
    broken rather than as a port being taken.

    So this is a second, tiny listener whose whole job is a redirect. If the
    port is free the short name works; if it is not, nothing is said and
    nothing breaks - the hub is already running on its own port by the time
    this is tried.
    """
    class Redirect(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def do_GET(self):                       # noqa: N802
            where = "http://%s:%d%s" % (self.headers.get("Host", lan_ip())
                                        .split(":")[0], PORT, self.path)
            body = ("the hub is at " + where).encode()
            self.send_response(302)
            self.send_header("Location", where)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        do_POST = do_GET
        do_HEAD = do_GET

        def log_message(self, *a, **k):
            pass                                # a redirect is not news

    class Polite(ThreadingHTTPServer):
        # NEVER take a port another program is holding. ThreadingHTTPServer
        # sets SO_REUSEADDR, and on Windows that is not the harmless
        # "reuse a socket in TIME_WAIT" it is on Unix - it lets one process
        # bind a port another process is already listening on, and then which
        # of them gets a connection is anyone's guess. Backing off is the whole
        # point of this listener: the hub is already up, and a short name is
        # not worth taking someone else's port for.
        allow_reuse_address = False

    try:
        srv = Polite((HOST, port), Redirect)
    except OSError:
        return None                             # someone else has it: fine
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def main():
    for d in (PROJECTS, SEQUENCES, MODELS):
        d.mkdir(parents=True, exist_ok=True)
    # ONE HUB PER PORT. The listener sets SO_REUSEADDR (ThreadingHTTPServer
    # default), and on Windows that lets a second hub bind the SAME port -
    # connections then land on either process at random and half the pages
    # silently misbehave. Ask before binding: if something here already
    # answers like a hub, open that one instead of fighting it.
    try:
        with urllib.request.urlopen(
                "http://127.0.0.1:%d/api/version" % PORT, timeout=2) as r:
            if "mice" in r.read(200).decode("utf-8", "replace").lower():
                print("a hub is already running on port %d - opening "
                      "http://127.0.0.1:%d/ instead" % (PORT, PORT))
                webbrowser.open("http://127.0.0.1:%d/" % PORT)
                return
    except Exception:                       # noqa: BLE001 - nothing there: bind
        pass
    srv = ThreadingHTTPServer((HOST, PORT), Handler)
    local = "http://127.0.0.1:%d/" % PORT
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except Exception:
        pass
    print("Mice hub running:")
    print("  this PC       ->", local)
    print("  same WiFi     -> http://%s:%d/   (phones / other laptops)" % (lan_ip(), PORT))
    # A NAME as well as an address. It is started here, after the socket is
    # bound, so a hub that cannot get port 5353 (Bonjour or avahi already has
    # it) still runs and simply says the name is unavailable.
    # CLAIM A NAME NOBODY ELSE HAS. Two hubs both answering mice.local do not
    # share it, they race: the same name reaches a different machine from one
    # lookup to the next. So ask first, and if the short name is spoken for,
    # take one of our own - mice-<this pc>.local. Nobody has to remember it,
    # because other hubs are LINKS on the network screen, not names to type.
    # The name THIS PC retreats to when the shared one is spoken for. It is
    # worked out up front and handed to the responder, because a clash can
    # also turn up minutes later - the other PC boots, or comes back after the
    # WiFi dropped it - and by then nothing else knows this machine's name.
    own_name = "mice-%s.local" % re.sub(r"[^a-z0-9-]", "",
                                        socket.gethostname().lower())[:24]
    NAME_SERVER[0] = mdns.Responder(MDNS_NAME, lan_ip, fallback=own_name)
    other = NAME_SERVER[0].taken()
    if other:
        print("  (%s is already answered by %s - taking %s instead)"
              % (MDNS_NAME, other, own_name))
        # Rename the responder we already have rather than building a new one.
        # A fresh Responder(own_name) would WANT the long name, and the reclaim
        # only ever goes back to what it wanted - so a hub that retreated at
        # startup would keep the hostname for ever, while one that retreated a
        # minute later would take mice.local back when the other PC left. Two
        # paths, two different behaviours, and nothing saying so.
        NAME_SERVER[0].name = own_name
    if NAME_SERVER[0].start():
        print("  by name       -> http://%s:%d/   (phones, Macs, Windows)"
              % (NAME_SERVER[0].name, PORT))
    else:
        print("  by name       -> not available:", NAME_SERVER[0].error)
    # ...and the short name, when port 80 is free to take.
    if start_short_name():
        # The name this hub really answers to, not the one it wanted: after a
        # clash those differ, and printing the shared one told the operator to
        # type an address that reaches the OTHER machine.
        print("  short name    -> http://%s/   (no port to type)"
              % NAME_SERVER[0].name)
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
