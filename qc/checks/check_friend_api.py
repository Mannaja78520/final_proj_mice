"""Our side of what the brief asks Face_Regonize for, against a fake of it (A13).

User 2026-10-10: *ทำเรื่องดึง api หรืออะไรอย่างอื่นที่เคยส่งให้เพื่อนไปทำไว้ก่อน
ได้เลย ... เวลามาจะได้แก้นิดเดียวแล้วใช้ได้เลย* - build our half now, so their
version needs only a small edit. The fake (qc/lib/fake_friend.py) answers the
brief's own examples; its `offers` plays their app today (none of it) and
their app after the brief.

THE PROMISES, each asserted on what reached the fake:
* Nothing new is sent until THEIR /openapi.json lists the route. Today's
  behaviour stays exactly as it is.
* /api/look gets the frame's own bytes, the camera name and the login, one
  frame at a time, and nothing is believed unless the answer says
  "kept": false - one that does not stops that camera.
* Strangers are in the picture but never named; somebody standing there is
  ONE arrival, not one per frame, and a second stranger is a second one.
* call_as is the name said; one that carries its own form of address
  ("พี่บอส") gets no second คุณ in front.
* Who is in front of a camera: our camera's look, else their present, else
  their feed - nearest face first.
Tested against fakes only: their real version does not exist yet.
"""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import qc as F
import fake_friend

AREA = "hub"
TITLE = "our half of the friend's new APIs: used only once they exist, nothing kept"

JPEG = b"\xff\xd8\xff\xe0fake-frame-bytes\xff\xd9"


def _load(name, rel):
    sys.path.insert(0, str(F.CODE / "apps" / "faces"))
    spec = importlib.util.spec_from_file_location(name, F.CODE / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _state(S, fake, login):
    """The real watcher State, pointed at the fake and a throwaway login."""
    os.environ["MICE_FACES_LOGIN"] = str(login)
    st = S.State("reconize")
    entry = dict(st.partners["reconize"], api=fake.url)
    st.partners = {"reconize": entry}
    st._live, st._live_at = entry, 10 ** 12          # no re-probe of a real app
    st.look = {"holdSeconds": 10, "staleSeconds": 5}
    S.friend_api._specs.clear()
    return st


def _frames(jpeg):
    seq = [0]

    def frames(seen, timeout):
        seq[0] += 1
        return seq[0], jpeg
    return frames


def run(t):
    tmp = Path(tempfile.mkdtemp(prefix="mice_friend_api_"))
    login = tmp / "faces_login.json"
    login.write_text(json.dumps({"reconize": {"username": "qc", "password": "qc"}}),
                     encoding="utf-8")
    old_login = os.environ.get("MICE_FACES_LOGIN")
    S = _load("_faces_service_friend", "apps/faces/service.py")
    L = _load("_faces_look_friend", "apps/faces/look.py")
    R = _load("_faces_rules_friend", "apps/faces/rules.py")
    try:
        _today(t, S, L, login)
        _look(t, S, L, login)
        _present(t, S, login)
        _feed(t, S, R, login)
        _history(t, S, login)
        _relay(t, L)
        _voice(t, S, L, tmp, login)
    finally:
        if old_login is None:
            os.environ.pop("MICE_FACES_LOGIN", None)
        else:
            os.environ["MICE_FACES_LOGIN"] = old_login


def _today(t, S, L, login):
    """Their app as it is: nothing new is sent, everything works as before."""
    fake = fake_friend.FakeFriend(offers=())
    try:
        st = _state(S, fake, login)
        pulled = []
        lk = L.Looker(st, "nong-cam-1", lambda s, w: pulled.append(1) or (1, JPEG))
        lk.step(0)
        t.ok(not fake.looks(), "with no /api/look in their app, no frame is sent",
             fake.calls)
        t.ok(not pulled, "and the camera is not even read", pulled)
        t.eq(lk.status["state"], "waiting", "the camera says it is waiting for their app")
        got = st.present("kiosk-1", 10)
        t.eq(got["from"], "feed", "who is at their camera comes from their feed, as before")
        t.ok(not [c for c in fake.calls if c[1].endswith("/present")],
             "their present is not asked before it exists", fake.calls)
    finally:
        fake.stop()


def _look(t, S, L, login):
    fake = fake_friend.FakeFriend(offers=("look",))
    try:
        st = _state(S, fake, login)
        cam = "nong-cam-1"
        lk = L.Looker(st, cam, _frames(JPEG), per_second=4)
        st.lookers = [lk]
        # A name riding along on an unmatched face (their history rows do
        # that shape) must still never be said.
        fake.look_faces[0]["name"] = "a guessed name"
        seen, wait = lk.step(0)
        looks = fake.looks()
        t.eq(len(looks), 1, "one frame, one request")
        form = looks[0][2]["form"] if looks else {}
        t.eq(form.get("photo"), JPEG, "the frame's own bytes reach /api/look, unchanged")
        t.eq(form.get("source"), cam.encode(), "with the camera's name")
        t.eq(form.get("want"), b"faces", "asking for faces")
        t.eq(looks[0][2]["auth"] if looks else "", "Bearer " + fake_friend.TOKEN,
             "logged in first")
        t.ok(0 < wait <= 0.25, "no faster than four a second", wait)
        sc = st.scenes.get(cam) or {}
        faces = sc.get("faces") or []
        t.eq([f["known"] for f in faces], [True, False],
             "the nearest face first, the stranger kept in the picture")
        t.eq(faces[0]["callAs"] if faces else "", "พี่บอส", "with the name they asked to be called")
        t.eq(faces[1]["who"] if len(faces) > 1 else "x", "", "and the stranger has no name")
        arrived = [p for p in st.people if p.get("source") == "look"]
        t.eq(len(arrived), 2, "the first look is two arrivals: Boss and a stranger")
        t.ok(all(p["hasCamera"] for p in arrived),
             "placed at our camera, so the rules may greet them", arrived)
        lk.step(seen)
        t.eq(len([p for p in st.people if p.get("source") == "look"]), 2,
             "the same two still standing there are not new arrivals")
        fake.look_faces = fake.look_faces + [{"box": [0.7, 0.3, 0.75, 0.4], "status": "unknown"}]
        lk.step(seen)
        t.eq(len([p for p in st.people if p.get("source") == "look"]), 3,
             "a second stranger stepping in IS a new arrival")

        got = st.present(cam, 10)
        t.eq((got["from"], got["facesNow"], got["unknownNow"]), ("look", 3, 2),
             "who is in front of our camera comes from its look")
        t.eq([p["callAs"] for p in got["people"]], ["พี่บอส"], "known people only, by call_as")
        t.ok(st.presence(cam, 60)["present"] is True, "presence mode sees them")
        fake.look_faces = []
        lk.step(seen)
        t.ok(st.presence(cam, 60)["present"] is False,
             "and an empty picture is nobody, at once", st.presence(cam, 60))

        # ---- refusals, as the brief lists them -----------------------------
        n = len(fake.looks())
        fake.look_code = 429
        _s, wait = lk.step(seen)
        t.ok(len(fake.looks()) == n + 1 and wait <= 0.25,
             "429 drops that frame and carries on", wait)
        fake.look_code = 503
        _s, wait = lk.step(seen)
        t.ok(wait >= 2, "503 waits for their model", wait)
        fake.look_code = 401
        st.token, st.token_dies = "old-token", time.time() + 3600
        lk.step(seen)
        t.eq(st.token, "", "401 throws the token away, so the next round logs in")
        fake.look_code = 200
        big = L.Looker(st, cam, _frames(b"\xff" * (2 * 1024 * 1024 + 1)))
        n = len(fake.looks())
        big.step(0)
        t.eq(len(fake.looks()), n, "a frame over their 2 MB limit is never sent")

        # ---- THE PROMISE -------------------------------------------------
        fake.kept = True
        lk.step(seen)
        n = len(fake.looks())
        t.ok(lk.stopped and lk.status["state"] == "stopped",
             "an answer that does not say kept: false stops the camera", lk.status)
        lk.step(seen)
        lk.step(seen)
        t.eq(len(fake.looks()), n, "and no further frame is sent")
        fake.kept = None                          # says nothing at all
        lk2 = L.Looker(st, "cam-2", _frames(JPEG))
        lk2.step(0)
        t.ok(lk2.stopped, "silence about keeping is not a promise either", lk2.status)
    finally:
        fake.stop()


def _present(t, S, login):
    fake = fake_friend.FakeFriend(offers=("present",))
    try:
        st = _state(S, fake, login)
        got = st.present("kiosk-1", 10)
        asked = [c for c in fake.calls if c[1] == "/api/node/kiosk-1/present"]
        t.ok(asked and asked[-1][2].get("seconds") == ["10"],
             "their camera is asked through their present, for the last N seconds", fake.calls)
        t.eq(got["from"], "theirs", "and that answer is the one used")
        t.eq([p["who"] for p in got["people"]], ["Boss Somchai", "Far Person"],
             "nearest face first, whatever order they sent")
        t.eq((got["facesNow"], got["unknownNow"]), (2, 1), "their counts come through")
    finally:
        fake.stop()


def _feed(t, S, R, login):
    """Their live feed with the brief's stranger event and call_as."""
    fake = fake_friend.FakeFriend(offers=())
    try:
        st = _state(S, fake, login)
        src = st.ws_source()
        at = datetime.now().isoformat(timespec="seconds")
        got = st.arrive_ws(src, {"node_id": "door-1", "status": "unknown", "faces": 2,
                                 "at": at, "name": "leaked name"})
        t.eq(len(got), 2, "a stranger event for two faces is two arrivals")
        t.ok(all(not e["known"] and not e["who"] for e in got),
             "and neither is given the name that rode along", got)
        again = st.arrive_ws(src, {"node_id": "door-1", "status": "unknown", "faces": 2,
                                   "at": at})
        t.eq(again, [], "their feed repeating the same strangers is not new arrivals")
        reports = [s["reports"] for s in st.snapshot()["sources"] if s["kind"] == "ws"]
        t.ok(reports and "unknown" in reports[0],
             "the screen stops saying the feed cannot see strangers", reports)
        missing = st.contract.get("ws", {}).get("missing")
        t.eq(missing, [], "a stranger is not reported as their names changing")
        known = st.arrive_ws(src, {"node_id": "door-1", "participant_id": "P7",
                                   "name": "Boss Somchai", "at": at, "call_as": "พี่บอส"})
        t.eq([e["callAs"] for e in known], ["พี่บอส"], "a known face keeps its call_as")
        plain = st.arrive_ws(src, {"node_id": "door-1", "participant_id": "P8",
                                   "name": "Ann Lee", "at": at})
        t.ok(plain and plain[0]["known"] and plain[0]["who"] == "Ann Lee",
             "today's feed (no status) still means a known face", plain)

        rules = {"greet": True, "title": "คุณ", "cameras": {"door-1": {"role": "entry"}},
                 "wording": {"entry": {"known": "สวัสดีครับ {title}{name}"}}}
        mem = lambda: {"people": {}, "cameras": {}, "today": {}}  # noqa: E731
        g, _ = R.decide(dict(known[0], hasCamera=True), rules, mem())
        t.eq(g and g["text"], "สวัสดีครับ พี่บอส",
             "a call_as with its own form of address gets no second คุณ")
        g, _ = R.decide(dict(known[0], hasCamera=True, callAs="บอส"), rules, mem())
        t.eq(g and g["text"], "สวัสดีครับ คุณบอส", "a bare nickname still gets คุณ")
        g, _ = R.decide(dict(plain[0], hasCamera=True), rules, mem())
        t.eq(g and g["text"], "สวัสดีครับ คุณAnn Lee", "no call_as: as before")
    finally:
        fake.stop()


def _history(t, S, login):
    """node_id in their history is read only once the registry says so."""
    fake = fake_friend.FakeFriend(offers=())
    now = datetime.now()
    rows = [{"id": "r1", "name": "Ann", "participant_id": "P1", "status": "matched",
             "detected_at": now.isoformat(), "node_id": "door-1"},
            {"id": "r2", "name": "Ben", "participant_id": "P2", "status": "matched",
             "detected_at": (now - timedelta(seconds=60)).isoformat(), "node_id": "door-1"}]
    try:
        st = _state(S, fake, login)
        st._fetch = lambda src, tok, page: (rows if page == 1 else [], "")
        st.token, st.token_dies = "tok", time.time() + 3600
        fresh, _ = st.poll_once()
        t.ok(fresh and not any(e["camera"] for e in fresh),
             "today a history row names no camera, even if one rode along", fresh)
        st = _state(S, fake, login)
        for s in st.partners["reconize"]["events"]:
            if s["kind"] == "poll":
                s["hasCamera"] = True              # the switch, when it lands
                s["map"]["camera"] = "node_id"
        st._fetch = lambda src, tok, page: (rows if page == 1 else [], "")
        st.token, st.token_dies = "tok", time.time() + 3600
        fresh, _ = st.poll_once()
        by = {e["who"]: e for e in fresh}
        t.eq(by.get("Ann", {}).get("hasCamera"), True,
             "switched on, a fresh row is placed at its camera")
        t.eq(by.get("Ben", {}).get("hasCamera"), False,
             "but a catch-up row a minute old is still only counted")
    finally:
        fake.stop()


class _Mjpeg(BaseHTTPRequestHandler):
    """The hub's live view, as /api/dev/cam.stream sends it."""
    asked = []

    def log_message(self, *a):
        pass

    def do_GET(self):                                        # noqa: N802
        _Mjpeg.asked.append(self.path)
        self.send_response(200)
        self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=mice")
        self.end_headers()
        try:
            for _ in range(40):
                self.wfile.write(b"\r\n--mice\r\nContent-Type: image/jpeg\r\nContent-Length: "
                                 + str(len(JPEG)).encode() + b"\r\n\r\n" + JPEG)
                self.wfile.flush()
                time.sleep(0.05)
        except Exception:                                    # noqa: BLE001
            pass


def _relay(t, L):
    srv = ThreadingHTTPServer(("127.0.0.1", 0), _Mjpeg)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        frames = L.hub_frames("http://127.0.0.1:%d" % srv.server_port, "wifi:192.168.4.2")
        t.eq(_Mjpeg.asked, [], "the board is not watched before a frame is wanted")
        seq, jpeg = frames(0, 5)
        t.eq(jpeg, JPEG, "a frame comes through the hub's live view whole")
        t.ok(_Mjpeg.asked and _Mjpeg.asked[0] == "/api/dev/cam.stream?dev=wifi:192.168.4.2",
             "asked of the hub's relay, never of the board itself", _Mjpeg.asked)
    finally:
        srv.shutdown()


def _post(url, data):
    import urllib.request
    req = urllib.request.Request(url, data=data, method="POST",
                                 headers={"Content-Type": "image/jpeg"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.status, r.read().decode("utf-8")


def _voice(t, S, L, tmp, login):
    """The real voice helper: Check who I am uses /api/look; names use call_as."""
    fake = fake_friend.FakeFriend(offers=("look",))
    st = _state(S, fake, login)
    lk = L.Looker(st, "nong-cam-1", _frames(JPEG))
    st.lookers = [lk]
    S.Handler.state = st
    watcher = ThreadingHTTPServer(("127.0.0.1", 0), S.Handler)
    threading.Thread(target=watcher.serve_forever, daemon=True).start()
    partners = tmp / "partners.json"
    sys.path.insert(0, str(F.CODE / "tools"))
    import registry
    entry = dict(registry.load(F.CODE / "config" / "partners.json")["reconize"], api=fake.url)
    partners.write_text(json.dumps({"reconize": entry}), encoding="utf-8")
    port = F._free_port()
    cfg = tmp / "voice.json"
    cfg.write_text(json.dumps({
        "service": "http://127.0.0.1:%d" % port, "faqThreshold": 0.75,
        "stt": {"enabled": False}, "llm": {"enabled": False}, "tts": {"enabled": False},
        "face": {"rememberSeconds": 30, "addressWords": ["คุณ", "พี่"],
                 "watcher": "http://127.0.0.1:%d/state" % watcher.server_port}}),
        encoding="utf-8")
    faq = tmp / "qa.json"
    faq.write_text('{"faqs": []}', encoding="utf-8")
    env = dict(os.environ, MICE_PARTNERS=str(partners), MICE_FACES_LOGIN=str(login))
    log = open(tmp / "voice.log", "wb")
    proc = subprocess.Popen([sys.executable, "-u", str(F.CODE / "apps" / "voice" / "service.py"),
                             "--config", str(cfg), "--faq", str(faq), "--port", str(port)],
                            stdout=log, stderr=subprocess.STDOUT, env=env)
    base = "http://127.0.0.1:%d" % port
    try:
        deadline = time.time() + 30
        while time.time() < deadline:
            try:
                if json.loads(F.get(base + "/health")[1]).get("ok"):
                    break
            except Exception:                                # noqa: BLE001
                time.sleep(0.3)
        code, body = _post(base + "/identify", JPEG)
        got = json.loads(body or "{}")
        looks = fake.looks()
        t.ok(got.get("ok") and got.get("person") == "พี่บอส",
             "Check who I am goes to /api/look and says the name they asked for", got)
        t.ok(looks and looks[-1][2]["form"].get("photo") == JPEG,
             "the frame reached /api/look whole", len(looks))
        t.ok(not [c for c in fake.calls if c[1] == "/api/recognition/upload"],
             "and never their upload, which keeps every frame", fake.calls)
        code, body = F.get(base + "/camera")
        cam = json.loads(body or "{}")
        t.ok((cam.get("look") or {}).get("ok") is True,
             "the Voice page's button turns on by itself once /api/look exists", cam.get("look"))
        t.ok("nong-cam-1" in [s.get("id") for s in cam.get("stations") or []],
             "our own camera is offered beside theirs", cam.get("stations"))

        fake.kept = True
        code, body = _post(base + "/identify", JPEG)
        got = json.loads(body or "{}")
        t.ok(got.get("ok") is False and got.get("wouldKeep"),
             "an answer that kept the picture gives no name and stops the page", got)
        fake.kept = False

        lk.step(0)
        code, body = F.get(base + "/face?camera=nong-cam-1")
        t.eq(json.loads(body or "{}").get("person"), "พี่บอส",
             "a picked camera of ours answers with who its last look saw")
    finally:
        proc.terminate()
        try:
            proc.wait(5)
        except Exception:                                    # noqa: BLE001
            proc.kill()
        watcher.shutdown()
        fake.stop()

    V = _load("_voice_friend_names", "apps/voice/service.py")
    t.eq(V.format_multi_person("พี่บอส", "th", address=("คุณ", "พี่")), "พี่บอส",
         "a name that carries its own form of address gets no คุณ")
    t.eq(V.format_multi_person("บอส", "th", address=("คุณ", "พี่")), "คุณบอส",
         "a plain name still does")
