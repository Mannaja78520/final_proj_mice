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
import ipaddress
import json
import os
import re
import shutil
import subprocess
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

# Every child this hub runs carries this, or Windows gives the child its own
# console window - and MiceHub.exe has no console to lend it, so the window
# pops up over whatever the user was doing (user 2026-09-18). It does not
# change the child's stdout, so a pipe still reads its output.
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0

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
    # Built inside the code tree (code/dist/MiceHub.exe): serve pages, CSS and
    # registries LIVE from that tree, so a page change needs a refresh, not a
    # rebuild (user 2026-09-17: make every change fast). A venue install has
    # no code tree beside it and keeps the bundled copies.
    if (HERE.parent / "main_python" / "main.py").is_file() and (HERE.parent / "apps").is_dir():
        _ROOTS.insert(1, HERE.parent)
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

import app_window                                          # noqa: E402
import build_stamp                                         # noqa: E402
import cam_relay                                           # noqa: E402
import hub_auth                                            # noqa: E402
import hub_pair                                            # noqa: E402
import partner_launch                                      # noqa: E402
import route_latency                                       # noqa: E402
import shows as shows_mod                                  # noqa: E402
import stream_audio                                        # noqa: E402

# Which way to each board is fastest (A26-79). ONE instance, held by
# route_latency itself, so hub_usb and this file time the same routes.
route_latency.LAT = route_latency.Latency(asset("config", "route_latency.json"))

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
SHOWS = shows_mod.Shows(STUDIO / "shows", SEQUENCES)   # sequences in series (shows.py)

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
    url = (cfg.get("service") or "http://127.0.0.1:8767").rstrip("/")
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
    return url, ""


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
# .urdf joins the list for A31-7: Studio reads one to place every part instead
# of each STL being nudged into position by hand. It is XML naming meshes, not
# a mesh itself, so the STL files still have to be imported beside it.
UPLOAD_EXT = (".stl", ".png", ".jpg", ".jpeg", ".bmp", ".gif", ".urdf")
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


def lan_ips():
    """Every private IPv4 this PC has, lan_ip() first.

    Bench 2026-09-17: PC on venue WiFi 10.56.15.8 AND running hotspot
    192.168.137.1; the sweep covered only the first, so nong on the hotspot
    was never found. Link-local and VPN (non-private) addresses are skipped.
    """
    out = [lan_ip()]
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            out.append(info[4][0])
    except OSError:
        pass
    keep = []
    for ip in dict.fromkeys(out):
        try:
            a = ipaddress.ip_address(ip)
        except ValueError:
            continue
        if a.is_private and not a.is_loopback and not a.is_link_local:
            keep.append(ip)
    return keep or [lan_ip()]


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
        # RS485 boards behind the cable count too: nong #67 reported its WiFi
        # ip only through the bus (bench 2026-09-17).
        boards = [(ident or {}).get("module") or {}] + list((ident or {}).get("rs485") or [])
        for b in boards:
            ip = (b or {}).get("ip") or ""
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
    return MODULES.find(lan_ips(), force, also_ask=_ips_from_usb())


# Listing ports and asking each which module it is: hub_probe.py (A26-93).
from hub_probe import (  # noqa: E402
    serial_ports, _read_lines, _wifi_of, probe_usb_port, _usbscan_lock,
    _usbscan_cache, probe_usb_one, probe_usb_all)


# The USB serial manager lives in hub_usb.py (A26-76 phase 2): the hub is
# still the ONE owner of every cable, this just names where that code is.
from hub_usb import (  # noqa: E402
    _usb_mgr_lock, _usb_open, _usb_touch, _usb_ident, USB_IDLE_CLOSE,
    USB_INUSE, usb_busy_hint, _usb_get, usb_close, usb_free, usb_in_use,
    _usb_reaper, _LOG_LINE, _BOOT_NOISE, _drain_to_line_boundary, usb_cmd,
    _usb_cmd_raw, _IDENTITY_CHANGING, _usb_cmd_once, _flash_ports)

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
    if dev.startswith("auto:"):
        dev = resolve_auto(dev)       # the fastest local route (A26-79)
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
# The account typed into the hub's login, reused on boards (user 2026-09-17:
# *when login to hub and the log in to the module too*). Memory only, never disk.
_hub_login = {"user": "", "password": ""}


def board_logins():
    """Logins to try on a board, in order: the hub login, then config/board_logins.json.

    Bench 2026-09-17: nong #67 had only manny/12345678, the hub tried only
    admin/admin123, so every WiFi move from Studio was refused while RS485 worked.
    """
    out = []
    if _hub_login["user"] and _hub_login["password"]:
        out.append((_hub_login["user"], _hub_login["password"]))
    path = Path(os.environ.get("MICE_BOARD_LOGINS")
                or asset("config", "board_logins.json"))
    try:
        cfg = json.loads(path.read_text(encoding="utf-8"))
        for e in cfg.get("logins") or []:
            pair = (str(e.get("user") or ""), str(e.get("password") or ""))
            if pair[0] and pair[1]:
                out.append(pair)
    except (OSError, ValueError, AttributeError):
        pass
    out.append(SHIPPED_BOARD_LOGIN)          # a broken file must not lose the default
    return list(dict.fromkeys(out))


def board_login(ip, user="", password=""):
    """Log in to a board's own web login. -> (cookie, why); why is for a person.

    No account given: every login from board_logins() is tried until one works.
    """
    if user or password:
        return _board_login_one(ip, user, password)
    why = ""
    for who, pwd in board_logins():
        cookie, why = _board_login_one(ip, who, pwd)
        if cookie or why == "":              # a session, or a board with no login
            return cookie, why
        if "refused the login" not in why:
            return cookie, why               # unreachable: trying more will not help
    return "", ("%s refused every known login. A board keeps its OWN accounts: "
                "log in to the hub with that board's account, or set it back to "
                "the shipped login on its own page." % ip)


def _board_login_one(ip, who, pwd):
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
        t0 = time.perf_counter()
        try:
            out = Handler.robot_get(
                addr, "/api/cmd?c=" + urllib.parse.quote(_via(c, peer)),
                timeout=wait or (PEER_WAIT if peer else None)).decode(errors="replace")
        except Exception:
            if not peer:
                route_latency.LAT.fail("wifi:" + addr)
            raise
        if not peer:     # a forwarded command times two hops, not this route
            route_latency.LAT.record("wifi:" + addr, (time.perf_counter() - t0) * 1000.0, len(out))
        return out
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
            if r.get("dev") == dev or dev == "auto:" + (m.get("key") or ""):
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


# ONE BACKGROUND UPLOAD AT A TIME. Over a cable a file goes 120 bytes per
# command, so a 4 MB song is ~35,000 commands and a long wait. User
# 2026-09-27: *use the time to send, but show a wheel with how many percent,
# and say nothing else can be done*. So the hub sends it on its own thread and
# Studio polls /api/upload/progress; one HTTP request held open for the whole
# transfer would die long before the song arrived.
UPLOAD = {"running": False, "name": "", "sent": 0, "total": 0,
          "result": "", "error": "", "started": 0.0, "cancel": False}
UPLOAD_LOCK = threading.Lock()


def upload_start(dev, dirp, name, data: bytes):
    """Start dev_upload on a thread. Refuses while one is still running."""
    with UPLOAD_LOCK:
        if UPLOAD["running"]:
            raise ValueError("%s is still being sent - wait for it, or cancel it"
                             % UPLOAD["name"])
        UPLOAD.update(running=True, name=name, sent=0, total=len(data),
                      result="", error="", started=time.time(), cancel=False)

    def run():
        try:
            r = dev_upload(dev, dirp, name, data, job=UPLOAD)
            with UPLOAD_LOCK:
                if r.startswith("OK"):
                    UPLOAD.update(result=r, sent=len(data))
                else:
                    UPLOAD["error"] = r
        except Exception as e:              # noqa: BLE001
            with UPLOAD_LOCK:
                UPLOAD["error"] = str(e)
        finally:
            with UPLOAD_LOCK:
                UPLOAD["running"] = False
    threading.Thread(target=run, daemon=True).start()
    return upload_status()


def upload_status():
    with UPLOAD_LOCK:
        return {k: v for k, v in UPLOAD.items() if k != "cancel"}


def dev_upload(dev, dirp, name, data: bytes, job=None):
    """`job`, when given, is UPLOAD: its `sent` counts up as chunks go, and
    setting its `cancel` stops the transfer and removes the half-written file."""
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
        if job is not None:
            job["sent"] = i
            if job.get("cancel"):
                # close it and take the half-written file back off the card, so
                # a cut-off song is never left there to be picked and played
                dev_cmd(dev, "FEND")
                dev_cmd(dev, "FDEL " + path)
                return "ERR cancelled - nothing was kept on the card"
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
    # `speed` comes back out because a SHOW has to re-time the move into this
    # sequence's first pose, and the only honest speed to do that at is the one
    # the sequence itself was written for (shows.py, A31-1).
    return {"name": name, "next": nxt, "loop": loop, "steps": steps,
            "speed": seq_speed or cur_speed or 0.0}


# The show player lives in hub_show.py (A26-76 phase 2, see docs/systems/hub.md).
from hub_show import ShowPlayer  # noqa: E402


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
# The flashing code lives in hub_flash.py (A26-93, see docs/systems/hub-flash.md).
# The images are read from here; checks swap it for a temp folder.
FIRMWARE_DIR = DATA / "firmware"

# How much of an unwanted request body the hub will swallow to be polite
# about the reason it is refusing. 4 MB is more than any page here posts.
DRAIN_LIMIT = 4 * 1048576

# The name this hub answers to on the local network. One place, so the page,
# the console banner and the responder cannot disagree about it.
MDNS_NAME = "mice.local"
NAME_SERVER = [None]

import hub_flash  # noqa: E402
from hub_flash import (  # noqa: E402
    PIO_HOME, BOOT_APP0, FLASH_PARTS, _flash_lock, flash_env, flash_image,
    flash_images, send_firmware, esptool_cmd, Flasher)
hub_flash.bind(sys.modules[__name__])


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


# One list of modules: every board once, with every route to it, fastest first (A26-93).
import hub_modules  # noqa: E402
from hub_modules import (  # noqa: E402
    _live_devs, _pick_route, _route_table, board_key, modules_everywhere,
    modules_here, remote_modules, resolve_auto, route_probe_loop,
    route_probe_once
)
hub_modules.bind(sys.modules[__name__])


# Read by hub_cam.py; asset() lives here, so the path is worked out here.
CAM_BOARDS_JSON = asset("firmware", "config", "cam_boards.json")


# Camera boards: which board, and its pinout drawn as SVG (A26-93).
import hub_cam  # noqa: E402
from hub_cam import (  # noqa: E402
    CAM_SIGNALS, cam_boards, cam_pinout_svg, esc
)
hub_cam.bind(sys.modules[__name__])


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


# Self-update from the app branch, and the diagnostics text for support (A26-93).
import hub_update  # noqa: E402
from hub_update import (  # noqa: E402
    APP_API, APP_BRANCH, APP_RAW, APP_REPO, DIAG_TECH_MARK, _my_sha_file,
    app_here, diagnostics, do_update, hub_offers, update_state
)
hub_update.bind(sys.modules[__name__])


flasher = Flasher()


# Groups of api() routes, one file per area (A26-93). Handler inherits them.
import hub_api_apps  # noqa: E402
hub_api_apps.bind(sys.modules[__name__])
import hub_api_support  # noqa: E402
hub_api_support.bind(sys.modules[__name__])
import hub_api_flash  # noqa: E402
hub_api_flash.bind(sys.modules[__name__])
import hub_api_play  # noqa: E402
hub_api_play.bind(sys.modules[__name__])
import hub_api_studio  # noqa: E402
hub_api_studio.bind(sys.modules[__name__])


# ---------------------------------------------------------------- handler
class Handler(hub_api_apps.AppRoutes, hub_api_support.SupportRoutes, hub_api_flash.FlashRoutes, hub_api_play.PlayRoutes, hub_api_studio.StudioRoutes, BaseHTTPRequestHandler):
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
                # THE BODY FIRST, then the name. Refusing a bad name before
                # reading a 4 MB body made Windows abort the connection, so a
                # Thai file name reached the page as "Failed to fetch" instead
                # of "bad name" (user 2026-09-27).
                data = self.body()
                name = safe_name((q.get("name") or ["f"])[0])
                dirp = (q.get("dir") or ["/moves"])[0]
                if (q.get("background") or [""])[0] == "1":
                    return self.send_json(upload_start(dev, dirp, name, data))
                return self.send_bytes(dev_upload(dev, dirp, name, data).encode(),
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
                        "/api/users", "/api/users/add", "/api/users/remove",
                        "/api/users/rename", "/api/users/password"):
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
                # who is logged in, their role, and whether they still use the
                # shipped password - the pages show a "please change" banner
                "user": self.logged_in_user() if self.logged_in() else "",
                "role": a.role_of(self.logged_in_user()) if self.logged_in() else "",
                "mustChange": a.must_change(self.logged_in_user()) if self.logged_in() else False,
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
            me = self.logged_in_user()
            # super_admin sees every account; anyone else only their own
            mine = a.accounts() if a.is_super(me) else                 [x for x in a.accounts() if x["name"] == me]
            return self.send_json({"ok": True, "users": [x["name"] for x in mine],
                                   "accounts": mine, "me": me,
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
            
            if not a.is_super(self.logged_in_user()):
                ok, why = False, "only super_admin can add or remove accounts"
            elif path.endswith("/add"):
                ok, why = a.add_user(name, str(body.get("password") or ""),
                                     str(body.get("role") or hub_auth.ROLE_USER))
            else:
                ok, why = a.remove_user(name)
            return self.send_bytes(
                json.dumps({"ok": ok, "error": why, "users": a.users()}).encode(),
                MIME[".json"], 200 if ok else 400)

        if path in ("/api/users/rename", "/api/users/password"):
            # Your OWN account: anyone logged in (a password change also asks
            # for the current one). ANY account: super_admin only.
            if not self.logged_in():
                return self.send_bytes(json.dumps(
                    {"ok": False, "need_login": True,
                     "error": "log in first"}).encode(), MIME[".json"], 401)
            try:
                body = json.loads(self.body().decode() or "{}")
            except ValueError:
                body = {}
            me = self.logged_in_user()
            target = str(body.get("user") or me).strip()
            boss = a.is_super(me)
            if target != me and not boss:
                ok, why = False, "only super_admin can change someone else's account"
            elif path.endswith("/rename"):
                ok, why = a.rename_user(target, str(body.get("new") or "").strip())
            elif target == me and not a.check_password(me, str(body.get("old") or "")):
                ok, why = False, "your current password was not right"
            else:
                ok, why = a.change_password(
                    target, str(body.get("password") or ""),
                    keep_token=a.token_of(self.headers.get("Cookie", "")))
            return self.send_bytes(
                json.dumps({"ok": ok, "error": why,
                            "me": self.logged_in_user()}).encode(),
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
        # Same account goes to the boards next time one asks (board_logins).
        _hub_login.update(user=a.user_of(token) or str(body.get("user") or ""),
                          password=str(body.get("password") or ""))
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
        # the background upload: how far it has got, and stopping it
        if path == "/api/upload/progress":
            return self.send_json(upload_status())
        if path == "/api/upload/cancel" and method == "POST":
            with UPLOAD_LOCK:
                UPLOAD["cancel"] = True
            return self.send_json(upload_status())

        if path == "/api/servos":
            # The ONE servo table, shared with the firmware (which compiles it
            # into a header). Studio reads this instead of keeping a second
            # copy that could drift.
            if not registry:
                return self.send_json({"ok": False, "servos": {}})
            return self.send_json({"ok": True, "servos": registry.servos()})

        r = self.api_apps(method, path, q)   # hub_api_apps.py
        if r is not hub_api_apps.NOT_MINE:
            return r

        if path == "/api/scan":
            force = (q.get("force") or ["0"])[0] == "1"
            return self.send_json({"ok": True, "lan": lan_ip(),
                                   "modules": scan_modules(force),
                                   "ports": serial_ports()})

        r = self.api_support(method, path, q)   # hub_api_support.py
        if r is not hub_api_support.NOT_MINE:
            return r

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
                full = (q.get("full") or ["0"])[0] == "1"
                return self.send_json({"ok": True, "usb": [probe_usb_one(port, full=full)]})
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

        r = self.api_flash(method, path, q)   # hub_api_flash.py
        if r is not hub_api_flash.NOT_MINE:
            return r

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

        r = self.api_play(method, path, q)   # hub_api_play.py
        if r is not hub_api_play.NOT_MINE:
            return r

        r = self.api_studio(method, path, q)   # hub_api_studio.py
        if r is not hub_api_studio.NOT_MINE:
            return r

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


def open_target(argv):
    """What to show when started: the hub page, or ONE app with --open <id>.

    -> (url path, show fn). An unknown id is refused with the real list rather
    than silently opening the hub: a desktop icon pointing at a renamed app
    should say so.
    """
    want = app_window.open_arg(argv)
    if not want:
        return "/", webbrowser.open
    app = registry.app_by_id(want) if registry else None
    if not app:
        known = ", ".join(a["id"] for a in (registry.apps() if registry else []))
        raise SystemExit("no app called %r - the apps are: %s" % (want, known or "(none)"))
    cfg = app_window.load_config(asset("config", "app_window.json"))
    return app["path"], lambda url: app_window.open_window(url, cfg)


def main():
    for d in (PROJECTS, SEQUENCES, MODELS):
        d.mkdir(parents=True, exist_ok=True)
    path, show = open_target(sys.argv[1:])
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
                      "http://127.0.0.1:%d%s instead" % (PORT, PORT, path))
                show("http://127.0.0.1:%d%s" % (PORT, path))
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
    threading.Timer(0.6, lambda: show(local.rstrip("/") + path)).start()
    # warm the module scan so the hub page fills instantly
    threading.Thread(target=scan_modules, daemon=True).start()
    threading.Thread(target=_usb_reaper, daemon=True).start()  # idle port release
    threading.Thread(target=route_probe_loop, daemon=True).start()  # A26-79
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nbye")


if __name__ == "__main__":
    main()
