"""Who else is running on this PC - so every app works alone AND together.

User 2026-11-23: every app must work fully on its own (someone may open only
the face app, or only Voice, with no hub), and when other apps are running
they join up: Voice + the face app greets the person it sees, a game + a prize
machine gives prizes, two programs never open one camera twice.

HOW. There is no server to start first. Each running app writes one tiny file
(`<app>-<port>.json`) into a folder every program on the PC can reach, and
removes it when it ends. To find a friend an app reads the folder and checks
each file really answers (a crashed app never cleaned up; a file whose port is
dead is deleted on sight). The folder is the system temp dir, so a moved or
renamed checkout, a second copy of the exe and a QC run all see the same
neighbours, and no file ever lands in the repo (public).

CAMERA CLAIMS. A webcam can be opened by one program. `claim_camera` creates
one file with O_EXCL: the first program to ask owns the camera and others get
the owner's address to READ its picture from, instead of opening it again
(measured 2026-10: a second open gives black frames). A claim whose owner no
longer answers is taken over.

Stdlib only. A program that is not ours (the friend's apps) is not in the
folder; it is found the old way, by the addresses in config/partners.json.
"""
import json
import os
import re
import socket
import tempfile
import time
from pathlib import Path

HOST = "127.0.0.1"


def folder():
    """Where the files live. MICE_PEERS_DIR moves it (QC uses a throwaway)."""
    p = Path(os.environ.get("MICE_PEERS_DIR")
             or (Path(tempfile.gettempdir()) / "mice-peers"))
    p.mkdir(parents=True, exist_ok=True)
    return p


def _slug(text):
    return re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-")[:60] or "x"


def answers(port, timeout=0.4):
    """True when something listens on this PC's port (a dead app does not)."""
    try:
        with socket.create_connection((HOST, int(port)), timeout=timeout):
            return True
    except (OSError, ValueError):
        return False


def _write(path, rec, exclusive=False):
    """Whole file or nothing: a reader never sees half a record."""
    data = json.dumps(rec).encode("utf-8")
    if exclusive:
        fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        return
    tmp = Path(str(path) + ".%d.tmp" % os.getpid())
    tmp.write_bytes(data)
    os.replace(str(tmp), str(path))


def _read(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


# ------------------------------------------------------------------ apps
def announce(app, port, caps=(), name="", alone=False):
    """I am `app`, answering on this PC at `port`; I can do `caps`.

    `alone` = started by itself, not inside the full hub. -> the record."""
    rec = {"app": app, "port": int(port), "pid": os.getpid(), "caps": list(caps),
           "name": name or app, "alone": bool(alone), "at": int(time.time()),
           "url": "http://%s:%d/" % (HOST, int(port))}
    _write(folder() / ("%s-%d.json" % (_slug(app), int(port))), rec)
    return rec


def withdraw(app, port):
    try:
        (folder() / ("%s-%d.json" % (_slug(app), int(port)))).unlink()
    except OSError:
        pass


def peers(app=None, cap=None, skip_port=None):
    """Live neighbours, optionally only one app or one ability.

    A file whose port no longer answers is removed here, so the list is true
    the moment it is read and nobody has to run a cleaner."""
    out = []
    for f in sorted(folder().glob("*.json")):
        if f.name.startswith("cam-"):
            continue
        rec = _read(f)
        if not isinstance(rec, dict) or "port" not in rec:
            continue
        if not answers(rec["port"]):
            try:
                f.unlink()
            except OSError:
                pass
            continue
        if skip_port and rec["port"] == skip_port:
            continue
        if app and rec.get("app") != app:
            continue
        if cap and cap not in rec.get("caps", []):
            continue
        out.append(rec)
    return out


def find(cap, skip_port=None):
    """The first live neighbour that can do `cap` (e.g. "prize"), or None."""
    got = peers(cap=cap, skip_port=skip_port)
    return got[0] if got else None


def where(configured, cap):
    """Where to ask for `cap`: the configured address while it answers, else
    the first live neighbour that can do it, else the configured one anyway
    (so the caller's own "not answering" words still say what is wrong)."""
    configured = (configured or "").rstrip("/")
    try:
        port = int(configured.rsplit(":", 1)[1].split("/")[0])
    except (IndexError, ValueError):
        port = 0
    if port and answers(port):
        return configured
    other = find(cap)
    return other["url"].rstrip("/") if other else configured


# --------------------------------------------------------------- cameras
def _claim_file(dev):
    return folder() / ("cam-%s.json" % _slug(dev))


def claim_camera(dev, port):
    """Ask to be the one program that opens camera `dev`.

    -> (True, None) you own it now; (False, owner record) read the owner's
    picture instead (owner["url"] is its address). Race-safe: two programs
    asking in the same instant get one yes."""
    path = _claim_file(dev)
    mine = {"dev": dev, "port": int(port), "pid": os.getpid(),
            "url": "http://%s:%d/" % (HOST, int(port)), "at": int(time.time())}
    for _ in range(3):
        try:
            _write(path, mine, exclusive=True)
            return True, None
        except FileExistsError:
            rec = _read(path)
            if rec and rec.get("port") == int(port):
                return True, None                      # my own claim, again
            if rec and answers(rec.get("port", 0)):
                return False, rec
            try:                                       # owner is gone: take over
                path.unlink()
            except OSError:
                pass
    return False, _read(path)


def release_camera(dev, port):
    rec = _read(_claim_file(dev))
    if rec and rec.get("port") == int(port):
        try:
            _claim_file(dev).unlink()
        except OSError:
            pass


def release_all(port):
    """I am ending: let go of every camera I own and say goodbye."""
    for f in folder().glob("cam-*.json"):
        rec = _read(f)
        if rec and rec.get("port") == int(port):
            try:
                f.unlink()
            except OSError:
                pass


def camera_owner(dev, my_port=None):
    """The live program that owns `dev`, or None (free, or I own it)."""
    rec = _read(_claim_file(dev))
    if not rec or rec.get("port") == my_port or not answers(rec.get("port", 0)):
        return None
    return rec
