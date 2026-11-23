"""Every camera the rig can see, as ONE list (user 2026-11-23).

Asked for: *one camera system - ESP32-CAM boards and any other camera used at
the same time by recording, face recognition and, later, a window or stream for
other people*. cam_relay.py already makes ONE connection per camera and feeds
every viewer; what was missing is a single place that knows which cameras exist
and can open any of them the same way.

A camera is named by its `dev`, the string the hub already uses everywhere:

    wifi:<ip>     an ESP32-CAM board (found by the scan)
    pc:<name>     a webcam on this PC (found by ffmpeg)
    cam:<id>      one a person added: a network link, or the demo camera

`relay_for(dev)` gives the shared relay for any of them, so
/api/dev/cam.stream?dev=<dev> works for all, and the face watcher, the watch
window and a recording all read the same relay. What a person added lives in
.local/cameras.json (git-ignored: a link can carry a camera's password);
what KINDS exist is data (config/cameras.json).
"""
import ipaddress
import json
import os
import re
import secrets
import threading
import urllib.parse
from pathlib import Path

import cam_relay

_hub = None
_lock = threading.Lock()


def bind(hub):
    global _hub
    _hub = hub


class UrlCamRelay(cam_relay.PcCamRelay):
    """A camera reached by a link (or the demo): read by one ffmpeg, shared."""
    GONE = "the camera gave no picture - check the link, its password, and that it is switched on"


def config():
    """config/cameras.json, read per call (MICE_CAMERAS_CONFIG points a check at its own)."""
    path = Path(os.environ.get("MICE_CAMERAS_CONFIG") or _hub.asset("config", "cameras.json"))
    try:
        return _hub.registry.load(path) or {}
    except Exception:                                        # noqa: BLE001
        return {}


def store_path():
    return Path(os.environ.get("MICE_CAMERAS_DATA") or
                (Path(_hub.DATA) / ".local" / "cameras")) / "cameras.json"


def load():
    try:
        got = json.loads(store_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        got = {}
    got.setdefault("sources", [])
    got.setdefault("face", [])
    return got


def save(data):
    p = store_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, p)


# ------------------------------------------------------------ validating
def check_link(link, kind):
    """-> (clean link, why-not). Only the schemes the kind allows, and never
    this PC or a link-local address: ffmpeg runs with the hub's rights, so a
    link to 127.0.0.1 (the hub itself, a loop) or 169.254.x (cloud metadata)
    would turn "add a camera" into "read anything on this PC"."""
    link = (link or "").strip()
    if not link or len(link) > 300 or any(c in link for c in " \t\r\n\0"):
        return "", "that link is empty, too long or has spaces in it"
    u = urllib.parse.urlparse(link)
    if u.scheme.lower() not in (kind.get("schemes") or []):
        return "", "the link must start with " + " or ".join(
            s + "://" for s in kind.get("schemes") or [])
    host = (u.hostname or "").lower()
    if not host:
        return "", "that link has no camera address in it"
    try:
        ip = ipaddress.ip_address(host)
        bad = ip.is_loopback or ip.is_link_local or ip.is_unspecified or ip.is_multicast
    except ValueError:
        bad = host == "localhost" or host.endswith(".localhost")
    if bad:
        return "", "that address is this PC itself - give the camera's own address"
    return link, ""


def mask(link):
    """The link without its login: what a page or a log may show."""
    u = urllib.parse.urlparse(link)
    return "%s://%s%s" % (u.scheme, u.hostname or "", (":%d" % u.port) if u.port else "")


def slug(name):
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:20]
    return s or "camera"


# ------------------------------------------------------------ add / remove
def add(name, kind, link=""):
    """-> (source, why-not)."""
    kinds = config().get("kinds") or {}
    spec = kinds.get(kind)
    name = " ".join((name or "").split())[:40]
    if not spec:
        return None, "unknown kind of camera"
    if not name:
        return None, "give the camera a name"
    value = ""
    if spec.get("needs") == "value":
        value, why = check_link(link, spec)
        if why:
            return None, why
    with _lock:
        data = load()
        if len(data["sources"]) >= int(config().get("maxSources") or 32):
            return None, "that is as many added cameras as this hub keeps"
        if any(s["name"].lower() == name.lower() for s in data["sources"]):
            return None, "a camera is already called that"
        src = {"id": "%s-%s" % (slug(name), secrets.token_hex(2)), "name": name,
               "kind": kind, "value": value}
        data["sources"].append(src)
        save(data)
    return src, ""


def remove(sid):
    with _lock:
        data = load()
        keep = [s for s in data["sources"] if s["id"] != sid]
        if len(keep) == len(data["sources"]):
            return False
        data["sources"] = keep
        data["face"] = [d for d in data["face"] if d != "cam:" + sid]
        save(data)
    # let go of the camera now: nobody should keep watching a removed source
    with cam_relay.CamRelay._all_lock:
        cam_relay.CamRelay._all.pop("cam:" + sid, None)
    return True


def set_face(dev, on):
    """Mark a camera as one the face watcher reads (the watcher follows this list)."""
    with _lock:
        data = load()
        faces = [d for d in data["face"] if d != dev]
        if on:
            faces.append(dev)
        data["face"] = faces
        save(data)
    return faces


# ------------------------------------------------------------ opening one
def _expand(spec, link):
    run = []
    scheme = urllib.parse.urlparse(link).scheme.lower() if link else ""
    for a in spec.get("run") or []:
        if a == "{input}":
            run += list((spec.get("extra") or {}).get(scheme, [])) + ["-i", link]
        else:
            run.append(str(a))
    return run


def relay_for(dev, pc_cfg=None):
    """(relay, why-not) for any camera that is read by the hub itself
    (pc: and cam:). A board (wifi:) is the caller's own path."""
    if dev.startswith("pc:"):
        return cam_relay.pc_relay(pc_cfg or {}, dev[3:])
    if dev.startswith("cam:"):
        src = next((s for s in load()["sources"] if s["id"] == dev[4:]), None)
        spec = (config().get("kinds") or {}).get(src["kind"]) if src else None
        if not src or not spec:
            return None, "no camera is added with that name"
        return UrlCamRelay.get(dev, run=_expand(spec, src.get("value", ""))), ""
    return None, "not a camera the hub reads itself"


def is_hub_read(dev):
    return dev.startswith("pc:") or dev.startswith("cam:")


# ------------------------------------------------------------ the list
def _viewers(dev):
    key = dev[5:] if dev.startswith("wifi:") else dev
    with cam_relay.CamRelay._all_lock:
        r = cam_relay.CamRelay._all.get(key)
    return r.viewers if r else 0


def listing(boards, pc_names):
    """Every camera, one shape. `boards` = [{dev,name,id,ip}] of ESP32 cameras
    (the caller's scan), `pc_names` = this PC's webcams."""
    data = load()
    faces = set(data["face"])
    kinds = config().get("kinds") or {}
    out = []

    def row(dev, name, kind, **more):
        d = {"dev": dev, "name": name, "kind": kind,
             "viewers": _viewers(dev), "face": dev in faces,
             "live": True, "removable": False}
        d.update(more)
        out.append(d)

    for b in boards:
        row(b["dev"], b.get("name") or ("camera %s" % b.get("id")), "esp32",
            id=b.get("id"), live=b["dev"].startswith("wifi:"), where=b["dev"].split(":", 1)[-1])
    for n in pc_names:
        row("pc:" + n, n, "usb", where="this PC")
    for s in data["sources"]:
        spec = kinds.get(s["kind"]) or {}
        row("cam:" + s["id"], s["name"], s["kind"], removable=True, id=s["id"],
            where=mask(s["value"]) if s.get("value") else spec.get("label", ""),
            known=bool(spec))
    return out
