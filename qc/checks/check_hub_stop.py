"""One click stops the hub AND everything it started (user 2026-11-22).

Asked: starting and stopping must work on another PC. The voice helper, the
face watcher and the friends' parts were left running when the hub closed, so
the next start there met a busy port or two copies fighting for the GPU.

1. children.kill_tree ends a child AND the grandchild it started (the real
   server hides below `cmd /c` / `sh -c`);
2. Children.stop_all ends every adopted program, once, and reports names;
3. the voice helper, the partners and the face watcher are adopted (source);
4. POST /api/quit from a website origin is refused and the hub keeps running;
5. config/children.json can keep them alive for a hub restart (stopWithHub).
"""
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

import qc as F

AREA = "hub"
TITLE = "stopping the hub stops the voice helper, face watcher and partners too"


def _alive(pid):
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    try:                                   # a zombie is not alive
        return "Z" not in open("/proc/%d/stat" % pid).read().split(")")[-1][:3]
    except OSError:
        return True


def run(t):
    sys.path.insert(0, str(F.HUB))
    import children
    if os.name == "nt":
        t.ok(True, "tree kill uses taskkill /T on Windows (not run on this OS)")
    else:
        code = ("import subprocess,sys,time;"
                "p=subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)']);"
                "print(p.pid,flush=True);time.sleep(60)")
        parent = subprocess.Popen([sys.executable, "-c", code], stdout=subprocess.PIPE,
                                  text=True, **children.session_flags())
        grand = int(parent.stdout.readline())
        t.ok(_alive(grand), "grandchild is running before the stop")
        children.CHILDREN.adopt("fake helper", parent)
        t.ok("fake helper" in children.CHILDREN.names(), "adopted program is listed")
        got = children.CHILDREN.stop_all(grace=2.0)
        time.sleep(0.3)
        t.eq(got, ["fake helper"], "stop_all names what it stopped")
        t.ok(parent.poll() is not None, "the child is gone")
        t.ok(not _alive(grand), "and the grandchild it started is gone too",
             "killing only the handle left the real server running")
        t.eq(children.CHILDREN.stop_all(), [], "a second stop finds nothing")

    for p, needle in (("main_python/voice_helper.py", "CHILDREN.adopt"),
                      ("main_python/partner_launch.py", "CHILDREN.adopt"),
                      ("main_python/hub_api_faces.py", "CHILDREN.adopt")):
        src = (F.CODE / p).read_text(encoding="utf-8", errors="replace")
        t.ok(needle in src and "session_flags" in src, p + " records what it starts")

    base, main = F.start_hub()
    req = urllib.request.Request(base + "/api/quit", data=b"{}", method="POST",
                                 headers={"Origin": "http://evil.example",
                                          "Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=5)
        code = 200
    except urllib.error.HTTPError as e:
        code = e.code
    t.eq(code, 403, "a website cannot stop the hub (POST /api/quit with a foreign Origin)")
    try:
        up = urllib.request.urlopen(base + "/api/version", timeout=5).status == 200
    except Exception:                                       # noqa: BLE001
        up = False
    t.ok(up, "the hub is still running after the refused stop")
    cfg = (F.CODE / "config/children.json").read_text(encoding="utf-8")
    t.ok('"stopWithHub"' in cfg, "config/children.json holds the keep-alive switch")
