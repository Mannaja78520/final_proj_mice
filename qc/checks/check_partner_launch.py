"""Open Reconize starts Reconize - the Main copy, never the Dummy.

Asked 2026-09-16: *make Reconize have the open the app reconize when click
Open Reconize too i cannot go to use reconize now and run only main not dummy*.

WHAT THIS HOLDS
  * `partner_launch.start` really starts a part that is silent, and the part
    then answers - proved with a throwaway `python -m http.server`, never with
    Reconize itself;
  * pressing again while it is up or still loading starts NOTHING new. A face
    model takes ~15 s, and a second uvicorn on the same port dies and leaves a
    confusing log;
  * a folder with a `refuseFolders` word in it (Dummy) is refused before
    anything runs;
  * no hub login from this PC (the apps have their own), a login from the
    network;
  * the real registry entry names Main, refuses dummy, and says how to start;
  * the page's button calls the route rather than only opening a tab.
"""
import json
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import qc as F


AREA = "hub"
TITLE = "Open Reconize starts the Main copy, never twice, never Dummy"


def _port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def run(t):
    sys.path.insert(0, str(F.CODE / "main_python"))
    import partner_launch as PL                             # noqa: E402

    # ---- the real entry ------------------------------------------------
    sys.path.insert(0, str(F.CODE / "tools"))
    import registry                                         # noqa: E402
    parts = registry.load(F.CODE / "config/partners.json")
    rec = parts.get("reconize") or {}
    t.ok(rec.get("launch"), "Reconize says how to start it", rec.keys())
    t.ok("dummy" in [w.lower() for w in rec.get("refuseFolders") or []],
         "and refuses a Dummy folder", rec.get("refuseFolders"))
    t.ok(not PL.refused(rec.get("folder"), rec.get("refuseFolders")),
         "and its folder is the Main copy", rec.get("folder"))

    # ---- a Dummy folder is refused before anything runs ----------------
    got = PL.start("qc_dummy", {"folder": "E:/x/Reconize_Dummy",
                                "refuseFolders": ["dummy"],
                                "launch": [{"run": ["nope"], "check": ""}]})
    t.ok(not got.get("ok") and "main" in (got.get("error") or ""),
         "a Dummy folder is refused", got)

    # ---- a silent part is started, once --------------------------------
    # The fake is started from ITS OWN start.bat on a port our config does not
    # know - that is the auto-route: their app changes, our file does not.
    port = _port()
    tmp = Path(tempfile.mkdtemp(prefix="qc_launch_"))
    (tmp / "srv").mkdir()
    # Loads slowly on purpose, like a face model, so the second press really
    # lands while it is loading. Prints its URL the way uvicorn and vite do.
    (tmp / "srv" / "srv.py").write_bytes((
        "import time, http.server as h\n"
        "time.sleep(3)\n"
        "print('running on http://127.0.0.1:%d', flush=True)\n"
        "h.HTTPServer(('127.0.0.1', %d), h.SimpleHTTPRequestHandler).serve_forever()\n"
        % (port, port)).encode())
    (tmp / "start.bat").write_bytes((
        '@echo off\r\necho Starting...\r\n'
        'start "QC Fake" cmd /k "cd srv && "%s" srv.py"\r\n'
        'start chrome http://localhost:1/\r\n' % sys.executable).encode())
    entry = {"name": "QC fake", "folder": str(tmp), "start": "start.bat",
             "open": "http://127.0.0.1:1", "launch": [{"run": ["nope"]}]}
    pid = "qc_fake_%d" % port
    parts, source = PL.parts_of(entry)
    t.ok(len(parts) == 1 and parts[0][0] == "srv" and "their" in source,
         "the commands are read from their own start file", (parts, source))

    # PHONES (user 2026-09-17): Reconize's screen must listen on the network,
    # added from our data, never by editing their start file.
    real_parts, _src = PL.parts_of(rec)
    screen = [c for _cwd, c in real_parts if "npm run dev" in c]
    t.ok(screen and "--host 0.0.0.0" in screen[0],
         "Reconize's screen starts listening for phones on the same WiFi", real_parts)
    t.ok("--host" not in (Path(rec.get("folder") or "") / (rec.get("start") or "x")).read_text(
             encoding="utf-8", errors="replace") if (Path(rec.get("folder") or "") / (rec.get("start") or "x")).is_file() else True,
         "and their own start.bat is left untouched")
    try:
        first = PL.start(pid, entry)
        t.ok(first.get("ok") and first.get("starting") == ["srv"],
             "a silent part is started", first)
        proc = PL._procs.get((pid, parts[0][1]))
        again = PL.start(pid, entry)
        t.ok(proc is not None and PL._procs.get((pid, parts[0][1])) is proc
             and again.get("ok") and again.get("starting") == ["srv"],
             "pressing again while it loads starts nothing new", again)
        ready = {}
        for _ in range(60):
            ready = PL.start(pid, entry)
            if ready.get("ready") or not ready.get("ok"):
                break
            time.sleep(0.25)
        t.ok(ready.get("ready") and ready.get("up") == ["srv"],
             "once it answers the button is told it is ready", ready)
        t.eq(ready.get("open"), "http://127.0.0.1:%d" % port,
             "and opens where it really printed, not the address in config")
    finally:
        proc = PL._procs.pop((pid, parts[0][1] if parts else ""), None)
        if proc is not None:
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                           capture_output=True)
            proc.wait(10)
        PL._memo_path(pid).unlink(missing_ok=True)

    # ---- the route is gated, and the page uses it ----------------------
    # WHO MAY START ONE (user 2026-09-17: *why need to login first, it own app
    # have it own login*): anyone at this PC, with no hub login; a caller on
    # the network still logs in. The hub runs in-process here, so "on the
    # network" is simulated by making is_self() say no.
    base, main = F.start_hub()
    F.logout_qc()
    code, body = F.post(base + "/api/partners/start?id=nobody")
    t.ok(code == 200 and '"need_login"' not in body,
         "at this PC, opening an outside app needs no hub login", (code, body[:200]))
    real_is_self = main.is_self
    main.is_self = lambda ip: False
    try:
        code, body = F.post(base + "/api/partners/start?id=nobody")
        t.ok(code == 401 and '"need_login"' in body,
             "from the network it still needs a login", (code, body[:200]))
    finally:
        main.is_self = real_is_self
    F.login(base)
    code, body = F.post(base + "/api/partners/start?id=nobody")
    t.ok(code == 200 and not json.loads(body).get("ok"),
         "logged in, an unknown partner is a plain error", (code, body[:200]))

    path = next(a["path"] for a in registry.apps() if a["id"] == "faces")
    code, page = F.get(base + path)
    t.contains(page, 'fetch("/api/partners/start?id="',
               "Open Reconize asks the hub to start Reconize")
