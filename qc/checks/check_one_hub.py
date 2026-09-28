"""Run as MiceHub.exe runs it, the hub is ONE module - and the show it plays is
the show Studio reads, beats and stops.

Found on the real nong 2026-09-28: a Show stopped by itself about a second
after Play, and GET /api/play said running=false, dev empty, no error. It was
not stopping. MiceHub.exe (and `python main.py`) runs main.py as __main__, and
hub_show.py fetched dev_cmd with `import main` - which loaded main.py a SECOND
time under its own name: a second hub, with its own show player, and every
hub_* helper rebound to it by that copy's bind() calls. So the first show of
every hub process played on player A while /api/play, the heartbeat and Stop
all went to player B, which had never started:

  * Studio saw running=false and stopped following the arm;
  * Timeline Play (watched) got no heartbeat and the hub stopped the arm
    itself after BEAT_TIMEOUT - the "stops by itself";
  * a Shows-tab show could not be stopped from Studio at all;
  * later shows played on B while check_takeover still watched A, so a live
    command no longer stopped the hub's clock: two clocks on one arm.

No check could see it, because qc.start_hub() imports the hub AS `main`, where
`import main` returns the same module. So this one runs the hub the way the
exe does: main.py executed as __main__ in a child process, with the fake
module, asserting on what reached the wire.

Held: the first show is the one /api/play reports; beats keep it alive past
BEAT_TIMEOUT and the hub never stops it by itself; Stop leaves nothing moving;
a late `import main` returns the running hub and rebinds nothing; a live
command stops the hub's show; and no hub helper imports main.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

import qc as F

AREA = "hub"
TITLE = "run as the exe runs it, the hub is one module: Play, beats and Stop reach the show"

# The child: main.py as __main__, exactly as Python runs a script, except that
# the script's own closing `if __name__ == "__main__": main()` runs after the
# port is set - so it never collides with a MiceHub.exe open on 8642.
CHILD = r'''
import ast, json, os, sys, threading, time, types, urllib.parse, urllib.request
HUB, LIB, PORT, PW = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
MAIN = os.path.join(HUB, "main.py")
sys.path[:0] = [HUB, LIB]          # the script folder first, as `python main.py` has it
import fake_serial
fake_serial.install()
import webbrowser
webbrowser.open = lambda *a, **k: None
import hub_auth
from pathlib import Path
hub_auth.Auth(Path(os.environ["MICE_HUB_AUTH"])).set_password(PW)

tree = ast.parse(open(MAIN, encoding="utf-8").read(), MAIN)
last = tree.body[-1]
if not (isinstance(last, ast.If) and "__main__" in ast.dump(last.test)):
    raise SystemExit("main.py no longer ends with its __main__ guard")
tree.body.pop()
hub = types.ModuleType("__main__")
hub.__file__ = MAIN
sys.argv = [MAIN]
sys.modules["__main__"] = hub
exec(compile(tree, MAIN, "exec"), hub.__dict__)
hub.PORT = PORT
threading.Thread(target=hub.main, daemon=True).start()

BASE = "http://127.0.0.1:%d" % PORT
cookie = [""]
def call(path, body=None):
    req = urllib.request.Request(BASE + path, method="GET" if body is None else "POST",
                                 data=None if body is None else json.dumps(body).encode())
    if cookie[0]:
        req.add_header("Cookie", cookie[0])
    with urllib.request.urlopen(req, timeout=20) as r:
        if path == "/api/login":
            cookie[0] = (r.headers.get("Set-Cookie") or "").split(";")[0]
        text = r.read().decode("utf-8", "replace")
    try:
        return json.loads(text)
    except ValueError:
        return text
def pick(st):
    return {k: st.get(k) for k in ("running", "dev", "step", "error")}
def steps(n):
    return ([{"pose": [90] * 10, "t": 200, "hold": 0}] +
            [{"pose": [100 if i % 2 else 80] * 10, "t": 400, "hold": 0} for i in range(n)])
def poses(since):
    return [c for _ms, c in fake_serial.wire[since:] if c.startswith("POSE")]

for _ in range(150):
    try:
        call("/api/version")
        break
    except Exception:
        time.sleep(0.1)
call("/api/login", {"password": PW})
hub.ShowPlayer.BEAT_TIMEOUT = 2.0     # the rule, shortened so this check is quick
rep = {}

# 1. The FIRST show of the process, watched like Timeline Play
w = len(fake_serial.wire)
rep["started"] = pick(call("/api/play", {"dev": "usb:COM99", "steps": steps(16),
                                         "name": "qc_first", "watch": True}))
time.sleep(0.5)
rep["early"] = pick(call("/api/play"))
end = time.monotonic() + 4.0          # twice BEAT_TIMEOUT, beating like Studio
while time.monotonic() < end:
    call("/api/play/beat", {})
    time.sleep(0.2)
rep["late"] = pick(call("/api/play"))
rep["hub_stop"] = [c for _ms, c in fake_serial.wire[w:] if c == "STOP"]
rep["beating_poses"] = len(poses(w))
call("/api/play/stop", {})
w = len(fake_serial.wire)
time.sleep(1.2)
rep["after_stop"] = poses(w)

# 2. A helper that imports main late gets THIS hub and rebinds nothing
import main as late
rep["one_module"] = late is hub
rep["rebound"] = sorted(n for n, m in list(sys.modules.items())
                        if n.startswith("hub_") and hasattr(m, "bind")
                        and getattr(m, "_hub", hub) is not hub)

# 3. A live motion command stops the show the hub is playing
call("/api/play", {"dev": "usb:COM99", "steps": steps(16), "name": "qc_takeover"})
time.sleep(0.7)
live = "POSE " + " ".join(["42"] * 10) + " T 300"
call("/api/usb/cmd?port=COM99&c=" + urllib.parse.quote(live))
at = max(i for i, (_ms, c) in enumerate(fake_serial.wire) if c == live)
time.sleep(1.2)
rep["after_live"] = poses(at + 1)
rep["after_live_status"] = pick(call("/api/play"))
print("QCREPORT " + json.dumps(rep), flush=True)
os._exit(0)
'''


def run(t):
    # ---- no hub helper reaches main.py by importing it -----------------
    # bind() is the one way in. The alias in main.py makes a stray import
    # harmless, but it also stays out of the exe's archive this way.
    for f in sorted(F.HUB.glob("hub_*.py")):
        src = f.read_text(encoding="utf-8", errors="replace")
        hits = re.findall(r"^[ \t]*(?:import main\b|from main import)", src, re.M)
        t.ok(not hits, "%s never does `import main`" % f.name, hits)

    # ---- the hub run as a script -----------------------------------------
    tmp = tempfile.mkdtemp(prefix="qc_one_hub_")
    env = dict(os.environ, MICE_HUB_AUTH=os.path.join(tmp, "auth.json"),
               PYTHONIOENCODING="utf-8")
    port = F._free_port()
    try:
        try:
            r = subprocess.run(
                [sys.executable, "-c", CHILD, str(F.HUB), str(F.QC / "lib"),
                 str(port), F.HUB_PASSWORD],
                cwd=str(F.HUB), env=env, capture_output=True, timeout=120,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        except subprocess.TimeoutExpired as e:
            t.ok(False, "the hub run as a script finished its show checks",
                 "timed out: %s" % (e.stderr or b"")[-600:])
            return
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    out = r.stdout.decode("utf-8", "replace")
    line = [x for x in out.splitlines() if x.startswith("QCREPORT ")]
    if not t.ok(line, "the hub run as a script finished its show checks",
                r.stderr.decode("utf-8", "replace")[-1200:]):
        return
    rep = json.loads(line[-1][len("QCREPORT "):])

    t.eq(rep["started"]["running"], True, "Play started the first show")
    t.ok(rep["early"]["running"] and rep["early"]["dev"] == "usb:COM99",
         "GET /api/play reports the first show playing, on its robot",
         "the hub read a player that never started: %s" % rep["early"])
    t.ok(not rep["hub_stop"] and rep["late"]["running"],
         "Studio's heartbeat reaches the playing show: it is still running "
         "past BEAT_TIMEOUT and the hub never stopped the arm by itself",
         "STOP sent by the hub: %s, status: %s" % (rep["hub_stop"], rep["late"]))
    t.ok(rep["beating_poses"] >= 3, "the show really moved the arm meanwhile",
         "%d POSE on the wire" % rep["beating_poses"])
    t.ok(not rep["after_stop"], "Stop leaves nothing moving the arm",
         "POSE after Stop: %s" % rep["after_stop"][:4])
    t.ok(rep["one_module"], "a late `import main` returns the running hub",
         "it loaded main.py a second time")
    t.ok(not rep["rebound"], "and no helper was rebound to a second hub",
         rep["rebound"])
    t.ok(not rep["after_live"], "a live POSE stops the show the hub is playing",
         "the show kept sending: %s" % rep["after_live"][:4])
    t.ok(not rep["after_live_status"]["running"]
         and "took over" in (rep["after_live_status"]["error"] or ""),
         "and /api/play says a live command took over",
         rep["after_live_status"])
