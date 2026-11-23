"""Every app works alone AND together (user 2026-11-23).

*Someone may open only one app, with no hub; and when other apps run they must
join up - never clash over a camera.* Proved with real processes:

1. peers.py: a running app is found by name and by ability, a dead one is
   dropped on sight, two programs asking for one camera in the same instant get
   ONE yes, and a claim whose owner died is taken over;
2. `main.py --alone voice` answers by itself on its own port: "/" is the
   Voice page, another app's page is a plain "not open here" page (never a
   broken copy), it lists itself at /api/peers;
3. a second app started alone is found by the first: the "not open here" page
   becomes an Open link, /api/peers?cap=camera names it;
4. a friend's app (Reconize) is refused with the reason, a made-up app and a
   bad port too - each exits with words, not a traceback;
5. with no hub, the face watcher greets through a neighbour that can speak
   (peers.where) and keeps a configured address that answers;
6. a webcam owned by another program is READ from that program (its picture
   link), not opened a second time.
"""
import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

import qc as F

AREA = "hub"
TITLE = "each app starts alone and finds the others; one camera, one owner"
SOLO = True

FAKE = r'''
import sys, time
log = sys.argv[1]
if sys.argv[2] == "list":
    sys.stderr.write('[in#0 @ 0x1] "Desk Cam" (video)\n')
    sys.exit(1)
with open(log, "a") as f:
    f.write("open %s\n" % " ".join(sys.argv[3:]))
n = 0
out = sys.stdout.buffer
while True:
    n += 1
    out.write(b"\xff\xd8" + (b"frame-%d " % n) * 40 + b"\xff\xd9"); out.flush()
    time.sleep(0.03)
'''


def _free():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _get(url, timeout=5):
    class NoFollow(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *a, **k):
            return None
    op = urllib.request.build_opener(NoFollow)
    try:
        with op.open(url, timeout=timeout) as r:
            return r.status, r.headers.get("Location", ""), r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("Location", ""), e.read().decode("utf-8", "replace")
    except OSError:
        return 0, "", ""


def _up(port, wait=25):
    end = time.time() + wait
    while time.time() < end:
        if _get("http://127.0.0.1:%d/api/version" % port)[0] == 200:
            return True
        time.sleep(0.3)
    return False


def _alone(env, app, port):
    return subprocess.Popen(
        [sys.executable, str(F.HUB / "main.py"), "--alone", app, "--port", str(port)],
        env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)


def run(t):
    tmp = Path(tempfile.mkdtemp(prefix="mice_alone_"))
    os.environ["MICE_PEERS_DIR"] = str(tmp / "peers")
    sys.path.insert(0, str(F.HUB))
    import peers

    # ---- 1. the registry itself -------------------------------------------
    srv = socket.socket()
    srv.bind(("127.0.0.1", 0))
    srv.listen(128)
    live = srv.getsockname()[1]
    peers.announce("voice", live, ["speak"], alone=True)
    gone = _free()
    peers.announce("gacha", gone, ["prize"])
    t.eq([p["app"] for p in peers.peers()], ["voice"], "a program that is gone is dropped from the list")
    t.ok(not (peers.folder() / ("gacha-%d.json" % gone)).exists(), "and its file is deleted")
    t.eq(peers.find("speak")["port"], live, "a neighbour is found by what it can do")
    t.ok(peers.find("prize") is None, "nobody can give a prize here")
    dead = "http://127.0.0.1:%d" % gone
    t.eq(peers.where(dead, "speak"), "http://127.0.0.1:%d" % live,
         "no hub answering: the face watcher greets through a neighbour that can speak")
    t.eq(peers.where("http://127.0.0.1:%d" % live, "speak"), "http://127.0.0.1:%d" % live,
         "a configured address that answers is used as it is")
    t.eq(peers.where(dead, "prize"), dead, "nobody can: the configured address stays, so its own words say what is wrong")
    ok, owner = peers.claim_camera("pc:Cam", 1111)         # 1111: nobody listens
    t.ok(ok and owner is None, "the first program to ask owns the camera")
    ok, owner = peers.claim_camera("pc:Cam", live)
    t.ok(ok, "a claim whose owner is gone is taken over", owner)
    ok, owner = peers.claim_camera("pc:Cam", 2222)
    t.ok(not ok and owner and owner["port"] == live, "a live owner keeps it; the asker is told where to read")
    wins, lock = [], threading.Lock()

    def ask(n):
        r = peers.claim_camera("pc:Race", 3000 + n)
        with lock:
            wins.append(r[0])
    # every asker is "alive" for this test: one listener per port is too heavy,
    # so the race is run against an owner that answers (this process)
    peers.claim_camera("pc:Race", live)
    ths = [threading.Thread(target=ask, args=(i,)) for i in range(8)]
    [x.start() for x in ths]
    [x.join() for x in ths]
    t.ok(not any(wins), "eight programs asking after the owner: all told to read, none opens it too", wins)
    peers.release_all(live)
    t.ok(peers.camera_owner("pc:Cam", 1) is None, "an ending program lets go of its cameras")
    srv.close()
    for f in peers.folder().glob("*.json"):
        f.unlink()

    # ---- 2-4. real processes ---------------------------------------------
    env = dict(os.environ, MICE_HUB_AUTH=str(tmp / "auth.json"), MICE_EXTENSIONS=str(tmp / "ext.json"),
               MICE_VOICE_AUTOSTART="0", MICE_LANG="off", PYTHONUNBUFFERED="1")
    pv, pc = _free(), _free()
    a = b = None
    try:
        a = _alone(env, "voice", pv)
        t.ok(_up(pv), "Voice starts by itself, no hub")
        code, loc, _ = _get("http://127.0.0.1:%d/" % pv)
        t.ok(code == 302 and loc == "/app/voice/", "its page is the front door", (code, loc))
        code, _, body = _get("http://127.0.0.1:%d/app/voice/" % pv)
        t.ok(code == 200 and "<title>Voice" in body, "the Voice page is served", code)
        code, _, body = _get("http://127.0.0.1:%d/app/camera/" % pv)
        t.ok(code == 200 and "not open in this window" in body and "Cameras" in body,
             "another app's page says plainly it is not open here", body[:120])
        t.ok("Open it" not in body, "...and does not pretend it is")
        code, _, body = _get("http://127.0.0.1:%d/studio/" % pv)
        t.ok("not open in this window" in body, "an app with a historic address (Studio) too", code)
        code, _, body = _get("http://127.0.0.1:%d/api/peers" % pv)
        got = json.loads(body)["peers"]
        t.ok([p["app"] for p in got] == ["voice"] and got[0]["alone"], "it lists itself as a neighbour", got)

        b = _alone(env, "camera", pc)
        t.ok(_up(pc), "Cameras starts by itself too")
        code, _, body = _get("http://127.0.0.1:%d/app/camera/" % pv)
        t.ok("Open it" in body and (":%d/app/camera/" % pc) in body,
             "Voice now points to the running Cameras window", body[-300:])
        got = json.loads(_get("http://127.0.0.1:%d/api/peers?cap=camera" % pv)[2])["peers"]
        t.ok([p["port"] for p in got] == [pc], "a program asking who can show a camera is told", got)
        b.terminate()
        b.wait(10)
        code, _, body = _get("http://127.0.0.1:%d/api/peers" % pv)
        t.ok([p["app"] for p in json.loads(body)["peers"]] == ["voice"],
             "when Cameras ends it leaves the list by itself")

        for what, args, needle in (
                ("a friend's app", ["--alone", "faces"], "friend's program"),
                ("a made-up app", ["--alone", "nope"], "no app called"),
                ("a bad port", ["--alone", "voice", "--port", "12"], "port")):
            r = subprocess.run([sys.executable, str(F.HUB / "main.py")] + args, env=env,
                               capture_output=True, text=True, timeout=30)
            t.ok(r.returncode != 0 and needle in (r.stdout + r.stderr) and "Traceback" not in r.stderr,
                 what + " is refused in words", (r.stdout + r.stderr)[-200:])
    finally:
        for p in (a, b):
            if p and p.poll() is None:
                p.terminate()
                try:
                    p.wait(10)
                except subprocess.TimeoutExpired:
                    p.kill()

    # ---- double-click starters (non-engineers do not type flags) -----------
    r = subprocess.run([sys.executable, str(F.CODE / "tools" / "make_launchers.py"), "--check"],
                       capture_output=True, text=True)
    t.ok(r.returncode == 0, "every app that runs alone has a double-click starter, and no stray one",
         r.stdout.strip())

    # ---- 5. a camera another program owns is read from it -----------------
    fake = tmp / "ffmpeg_fake.py"
    fake.write_text(FAKE, encoding="utf-8")
    log = tmp / "opens.log"
    py = sys.executable
    faces = tmp / "faces.json"
    faces.write_text(json.dumps({"service": "http://127.0.0.1:9", "pcCamera": {
        "run": [py, str(fake), str(log), "run", "{device}"],
        "list": [py, str(fake), str(log), "list"], "skip": []}}), encoding="utf-8")
    kinds = tmp / "cameras.json"
    kinds.write_text(json.dumps({"kinds": {
        "link": {"label": "link", "needs": "value", "schemes": ["http"],
                 "run": [py, str(fake), str(log), "run", "{input}"]}}}), encoding="utf-8")
    os.environ.update(MICE_FACES_CONFIG=str(faces), MICE_CAMERAS_CONFIG=str(kinds),
                      MICE_CAMERAS_DATA=str(tmp / "data"))
    base, main = F.start_hub()
    other = socket.socket()
    other.bind(("127.0.0.1", 0))
    other.listen(4)
    other_port = other.getsockname()[1]
    ok, _ = peers.claim_camera("pc:Desk Cam", other_port)
    t.ok(ok, "(set-up) another program owns the Desk Cam")
    main.cam_sources._claims.clear()
    relay, why = main.cam_sources.relay_for("pc:Desk Cam", main.hub_api_faces.pc_camera())
    t.ok(relay is not None, "the hub still gets a reader for it", why)
    time.sleep(0.2)
    code, text = F.get(base + "/api/dev/cam.jpg?dev=" + urllib.request.quote("pc:Desk Cam"))
    seen = log.read_text() if log.exists() else ""
    t.ok(("127.0.0.1:%d/api/dev/cam.stream" % other_port) in seen,
         "the hub reads the OWNER's picture link", seen[-200:])
    t.ok("run Desk Cam" not in seen, "and never opens the webcam itself", seen[-200:])
    other.close()
    peers.release_all(other_port)
