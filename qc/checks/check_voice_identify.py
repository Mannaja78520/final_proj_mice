"""Check who I am - one frame, a name back, and NOTHING written.

A26-61 (user 2026-09-18): *do not save the picture of it because it took my
rom just open and check who am i can you?* Reconize's own camera page stores
every frame it scans, plus a history row and an attendance row, which is what
filled the disk. So the Voice page takes ONE frame from the device it is open
on and asks the face app with `?persist=false`, which their recognition.py
reads: no stored image, no rows, no events entry.

The whole path is driven here against a FAKE face app: the real helper
process, the real HTTP route, the real multipart body. The fake records what
arrived, so the two things that can silently rot are assertions:

  * the query really says persist=false - drop it and every check writes a
    frame to their disk again, which is the bug this task exists to stop;
  * the name is REMEMBERED for two minutes. With nothing persisted there is
    no history row to read back, so the first version lost the name two
    seconds later, when the next poll of /face found an empty history.

Measured 2026-09-18 against the real Reconize: one enrolled photo through
/api/voice/identify returned the person, the answer greeted them by name, and
Reconize's history stayed at 0 rows with no file written under storage/.
"""
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import qc as F

AREA = "tools"
TITLE = "the Voice page can ask who you are without keeping the picture"

SEEN = {"paths": [], "auth": ""}


class _FakeFaceApp(BaseHTTPRequestHandler):
    """Stands in for Reconize: a login, and one recognition that matches."""

    def log_message(self, *a):                          # quiet
        pass

    def do_GET(self):                                   # noqa: N802
        SEEN["paths"].append(self.path)
        if self.path.startswith("/api/settings"):
            return self._send({"camera_label": "HD Webcam (5986:211b)"})
        if self.path.startswith("/api/node/status"):
            # A camera the face app is already watching - the thing that
            # makes one camera serve both apps.
            return self._send({"nodes": [{"node_id": "CAM-Door", "online": True,
                                          "camera_label": "Front door"}]})
        if self.path.startswith("/state"):              # the mice faces watcher
            from datetime import datetime
            if SEEN.get("quiet"):                      # nobody in front of anything
                return self._send({"ok": True, "people": []})
            now = datetime.now().isoformat()
            return self._send({"ok": True, "people": [
                {"who": "Door Person", "known": True, "when": now, "camera": "CAM-Door"},
                {"who": "Hall Person", "known": True, "when": now, "camera": "CAM-Hall"}]})
        return self._send({})

    def do_POST(self):                                  # noqa: N802
        n = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(n)
        SEEN["paths"].append(self.path)
        if self.path.startswith("/api/auth/login"):
            return self._send({"access_token": "tok-123"})
        SEEN["auth"] = self.headers.get("Authorization") or ""
        SEEN["bytes"] = len(body)
        if SEEN.get("quiet"):                          # an empty frame
            return self._send({"faces_total": 0, "results": []})
        return self._send({"faces_total": 1,
                           "results": [{"status": "matched", "name": "Manny Ha"}]})

    def _send(self, obj):
        raw = json.dumps(obj).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


def _helper(tmp, face_port):
    """The REAL apps/voice/service.py, pointed at the fake face app."""
    partners = tmp / "partners.json"
    partners.write_text(json.dumps({"reconize": {
        "name": "Reconize", "open": "http://localhost:5173",
        "api": "http://127.0.0.1:%d" % face_port, "camera": "/recognition"}}),
        encoding="utf-8")
    # A THROWAWAY login, not the real one: the real faces_login.json holds a
    # password and never leaves the real tree (promote.py SKIP_FILES), so this
    # whole check used to stop at its first line when run from .staging - and
    # nothing said so. The fake face app accepts anything.
    login = tmp / "faces_login.json"
    login.write_text(json.dumps({"reconize": {"username": "qc", "password": "qc"}}),
                     encoding="utf-8")
    cfg = tmp / "voice.json"
    port = F._free_port()
    cfg.write_text(json.dumps({
        "service": "http://127.0.0.1:%d" % port,
        "faqThreshold": 0.75, "faqAskAgain": 0,
        "stt": {"enabled": False}, "llm": {"enabled": False},
        "tts": {"enabled": False},
        "face": {"autoSeconds": 2, "rememberSeconds": 3,
                 "watcher": "http://127.0.0.1:%d/state" % face_port},
    }), encoding="utf-8")
    faq = tmp / "qa.json"
    faq.write_text('{"faqs": []}', encoding="utf-8")
    env = dict(os.environ, MICE_PARTNERS=str(partners), MICE_FACES_LOGIN=str(login))
    log = open(tmp / "svc.log", "wb")
    proc = subprocess.Popen(
        [sys.executable, "-u", str(F.CODE / "apps" / "voice" / "service.py"),
         "--config", str(cfg), "--faq", str(faq), "--port", str(port)],
        stdout=log, stderr=subprocess.STDOUT, env=env)
    deadline = time.time() + 30
    while time.time() < deadline:
        try:
            if json.loads(F.get("http://127.0.0.1:%d/health" % port)[1]).get("ok"):
                break
        except Exception:                               # noqa: BLE001
            time.sleep(0.3)
    return proc, port, login.is_file()


def run(t):
    srv = HTTPServer(("127.0.0.1", F._free_port()), _FakeFaceApp)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    tmp = Path(tempfile.mkdtemp(prefix="mice_who_qc_"))
    proc, port, have_login = _helper(tmp, srv.server_port)
    base = "http://127.0.0.1:%d" % port
    try:
        st, body = F.post_raw(base + "/identify", b"\xff\xd8not-really-a-jpeg",
                              "image/jpeg") if hasattr(F, "post_raw") else _post(
            base + "/identify", b"\xff\xd8not-really-a-jpeg")
        got = json.loads(body)
        if not have_login:                              # no saved face login here
            return t.ok(got.get("ok") is False and "login" in (got.get("error") or ""),
                        "without a saved face login it says so in plain words",
                        "answer was %r" % got)
        t.ok(got.get("ok") and got.get("person") == "Manny",
             "the name comes back from one frame", "answer was %r" % got)
        asked = [p for p in SEEN["paths"] if "recognition" in p]
        t.ok(bool(asked) and "persist=false" in asked[-1],
             "the face app is told to keep nothing",
             "it was asked for %r" % (asked[-1] if asked else None))
        t.eq(SEEN.get("auth", ""), "Bearer tok-123",
             "it logs in to the face app first")
        t.ok(SEEN.get("bytes", 0) > len(b"\xff\xd8not-really-a-jpeg"),
             "the frame is sent as a form upload, like their own camera does",
             "only %d bytes arrived" % SEEN.get("bytes", 0))

        st, body = F.get(base + "/face")
        t.eq(json.loads(body).get("person"), "Manny",
             "the name is remembered after the frame is gone")

        # Which camera is not a second setting: the face app already keeps one.
        st, body = F.get(base + "/camera")
        cam = json.loads(body)
        t.eq(cam.get("label"), "HD Webcam (5986:211b)",
             "the camera the face app already saved is offered here")
        t.ok(float(cam.get("seconds") or 0) >= 2,
             "how often to look is data, not a number in the page",
             "seconds came back as %r" % cam.get("seconds"))
        names = [s.get("name") for s in (cam.get("stations") or [])]
        t.ok("Front door" in names,
             "the cameras the face app already watches are offered too",
             "stations came back as %r" % (cam.get("stations"),))

        # Picking one of those reads THAT camera - no second camera opened,
        # and not some other camera's faces either.
        st, body = F.get(base + "/face?camera=CAM-Door")
        t.eq(json.loads(body).get("person"), "Door",
             "a picked camera answers with who IT saw")
        st, body = F.get(base + "/face?camera=CAM-Hall")
        t.eq(json.loads(body).get("person"), "Hall",
             "another camera answers with its own people, not the first one's")
        _forgetting(t, base)
        _their_side(t)
        _the_button(t)
        _the_camera_logic(t)
        _face_app_off(t, base, srv)         # shuts the fake face app down
    finally:
        proc.terminate()
        srv.shutdown()


def _forgetting(t, base):
    """The name must not outlive the person.

    A26-65 (user 2026-09-18): *in face detect when don't have face why it
    still said phuthiphong*. Two separate promises, both broken before:
      * a look that sees nobody drops the name AT ONCE - it used to keep
        showing the last one while the same look reported an empty frame;
      * and a name with nobody looking again expires after the time the
        USER sets (face.rememberSeconds), not a 120 written in the code.
    """
    SEEN["quiet"] = True                                # nobody in the room now
    try:
        st, body = _post(base + "/identify", b"\xff\xd8empty-frame")
        got = json.loads(body)
        t.ok(got.get("ok") is False and "no face" in (got.get("error") or ""),
             "an empty frame is answered in plain words", "answer was %r" % got)
        st, body = F.get(base + "/face")
        t.eq(json.loads(body).get("person"), "",
             "a look that sees nobody drops the name at once")

        SEEN["quiet"] = False                           # the person is back
        _post(base + "/identify", b"\xff\xd8a-face")
        st, body = F.get(base + "/face")
        t.eq(json.loads(body).get("person"), "Manny", "and it is picked up again")
        SEEN["quiet"] = True                            # then walks away
        time.sleep(3.4)                                 # cfg face.rememberSeconds = 3
        st, body = F.get(base + "/face")
        t.eq(json.loads(body).get("person"), "",
             "the name is forgotten after the time the user set")
    finally:
        SEEN["quiet"] = False


def _face_app_off(t, base, srv):
    """A face app that is NOT RUNNING must say so, and offer to start itself.

    User 2026-09-18, with the face app stopped: *the face app did not accept
    the saved login (<urlopen error [WinError 10061] No connection could be
    made because the target machine actively refused it>)*. 10061 is a refused
    CONNECTION - nothing was listening - and the sentence sent them looking
    for a password that was never wrong. The two cases have opposite fixes, so
    they are told apart by the exception: HTTPError means the face app
    answered and said no, any other OSError means it was not there.

    The fake is really shut here (server_close, not only shutdown - a bound
    socket would accept the connection and hang instead of refusing it).
    """
    srv.shutdown()
    srv.server_close()
    st, body = _post(base + "/identify", b"\xff\xd8a-face")
    got = json.loads(body)
    t.ok(got.get("ok") is False and "not running" in (got.get("error") or ""),
         "a face app that is off is reported as off, not as a bad password",
         "answer was %r" % got)
    t.ok(got.get("canStart") is True,
         "and the page is told it can be started from here",
         "canStart came back as %r" % got.get("canStart"))
    t.ok(bool(got.get("detail")) and "login" not in (got.get("error") or ""),
         "the WinError is kept as technical detail, out of the plain sentence",
         "answer was %r" % got)

    src = (F.CODE / "apps" / "voice" / "service.py").read_text(encoding="utf-8")
    at = src.find("    def identify(self, jpeg):")
    block = src[at:src.find("\n    def _query_reconize_direct", at)] if at >= 0 else ""
    t.ok("except urllib.error.HTTPError" in block and "except OSError" in block,
         "a refused password and a silent face app are told apart",
         "identify catches them with one except again")

    js = (F.CODE / "apps" / "voice" / "app.js").read_text(encoding="utf-8")
    t.ok("r.canStart" in js and "async startFaceApp()" in js
         and "/api/partners/start?id=reconize" in js,
         "the page turns that sentence into a Start button",
         "app.js has no start button for a silent face app")
    page = (F.CODE / "apps" / "voice" / "index.html").read_text(encoding="utf-8",
                                                                errors="replace")
    t.ok("startFaceApp" in page, "and the built page carries it",
         "index.html was not rebuilt from the template")


def _the_button(t):
    """The button on the built page, and the camera it must let go of."""
    page = (F.CODE / "apps" / "voice" / "index.html").read_text(
        encoding="utf-8", errors="replace")
    t.ok('id="btnWhoAmI"' in page and 'onclick="whoAmI()"' in page
         and "window.whoAmI" in page,
         "the Voice page has a Check who I am button, wired up",
         "button, onclick or the window.whoAmI bridge is missing")
    t.ok('id="faceForget"' in page and 'id="faceEvery"' in page
         and "collectFaces" in page,
         "the forget time and the look interval can be set on the page",
         "the Faces settings card is missing a field")
    t.ok('id="autoFace"' in page and 'id="camPick"' in page
         and "window.toggleAutoFace" in page and "window.pickCamera" in page,
         "the page can also look by itself, on a camera you pick",
         "the Check by itself switch or the camera list is missing")
    js = (F.CODE / "apps" / "voice" / "app.js").read_text(encoding="utf-8")
    a = js.find("async whoAmI(){")
    body = js[a:js.find("\n  autoFaceOn(){", a)] if a >= 0 else ""
    t.ok("finally" in body and "this.closeCam()" in body,
         "one look puts the camera away again, even when it fails",
         "whoAmI has no finally that closes the camera")
    lo = js.find("  async lookOnce(){")
    look = js[lo:js.find("\n  // The button:", lo)] if lo >= 0 else ""
    t.ok('this.updateFace("")' in look,
         "a look that found nobody clears the badge, not just the line under it",
         "lookOnce leaves the old name on the badge")
    p = js.find("  async pollFace(){")
    poll = js[p:js.find("\n  updateFace(", p)] if p >= 0 else ""
    t.ok("camera=" in poll and "this.camStation" in poll,
         "a picked camera is what the page asks about",
         "pollFace never names the station")
    k = js.find("  pickCamera(){")
    pick = js[k:js.find("\n  // Opens the chosen camera", k)] if k >= 0 else ""
    t.ok("this.closeCam()" in pick and "station:" in pick,
         "picking a watched camera opens none of its own",
         "pickCamera does not handle a station")
    c = js.find("  async toggleAutoFace(){")
    loop = js[c:js.find("\n  // What the helper says", c)] if c >= 0 else ""
    # The looking stops either way, because the timer's body checks the
    # stream - but an uncleared timer stacks up one more per switch-on, so
    # the timer itself has to go.
    t.ok("clearInterval(this.camLoop)" in loop,
         "switching it off clears the timer, not just the pictures",
         "toggleAutoFace never clears camLoop")
    b = js.find("  closeCam(){")
    shut = js[b:js.find("\n  // Grabs one frame", b)] if b >= 0 else ""
    t.ok("getTracks().forEach(t => t.stop())" in shut,
         "closing the camera really releases it",
         "closeCam does not stop the tracks")


_HARNESS = r"""
import fs from "fs";
const js = fs.readFileSync(%s, "utf8");
const calls = {identify: 0, opened: [], stopped: 0};
const el = (id) => ({id, style: {}, hidden: true, textContent: "", checked: false,
  innerHTML: "", value: "", srcObject: null, videoWidth: 640, videoHeight: 480,
  classList: {toggle() {}, add() {}, remove() {}, contains: () => false},
  dataset: {}, children: [], options: [],
  appendChild() {}, prepend() {}, remove() {}, focus() {}, blur() {},
  setAttribute() {}, removeAttribute() {}, scrollIntoView() {},
  querySelector: () => null, querySelectorAll: () => [],
  play: async () => {}, pause() {}, addEventListener() {}});
const els = {}; const store = {};
globalThis.localStorage = {getItem: k => (k in store ? store[k] : null),
  setItem: (k, v) => { store[k] = String(v); }, removeItem: k => { delete store[k]; }};
globalThis.document = {hidden: false, body: el("body"), querySelector: () => null,
  querySelectorAll: () => [], getElementById: id => (els[id] = els[id] || el(id)),
  createElement: (tag) => (tag === "canvas"
    ? {width: 0, height: 0, getContext: () => ({drawImage() {}}),
       toBlob: (cb) => cb(Buffer.from("jpeg"))} : el(tag)),
  createTextNode: () => el("text"), addEventListener() {}};
const track = {stop: () => { calls.stopped++; }};
Object.defineProperty(globalThis, "navigator", {configurable: true, writable: true, value: {
  mediaDevices: {
    enumerateDevices: async () => ([
      {kind: "videoinput", deviceId: "cam-a", label: "Laptop Camera"},
      {kind: "videoinput", deviceId: "cam-b", label: "HD Webcam (5986:211b)"}]),
    getUserMedia: async (c) => { calls.opened.push(JSON.stringify(c.video));
                                 return {getTracks: () => [track]}; }}}});
globalThis.fetch = async (u) => {
  if (u.endsWith("/api/voice/identify")) { calls.identify++;
    return {json: async () => ({ok: true, person: "Manny"})}; }
  if (u.endsWith("/api/voice/camera"))
    return {json: async () => ({ok: true, label: "HD Webcam (5986:211b)", seconds: 2})};
  return {json: async () => ({ok: true, config: {tts: {}, stt: {}, llm: {}}, faqs: [],
                              parts: {}, modules: [], sequences: []})};
};
globalThis.window = globalThis;
globalThis.miceLogin = {mount() {}};
eval(js);
const app = globalThis.voiceApp;
await app.loadCamera();                       // the face app's default arrives here
await app.openCam();
els.autoFace.checked = true;
await app.toggleAutoFace();
const first = calls.identify;
await new Promise(r => setTimeout(r, 2600));
const second = calls.identify;
els.autoFace.checked = false;
await app.toggleAutoFace();
await new Promise(r => setTimeout(r, 2600));
console.log(JSON.stringify({opened: calls.opened[0], first, second,
                            after_off: calls.identify, stopped: calls.stopped}));
process.exit(0);
"""


def _the_camera_logic(t):
    """Runs the page's own camera code in node, with a fake camera.

    Two promises are easy to break and invisible in a screenshot: that the
    camera it opens is the one the face app already names, and that "Check by
    itself" really stops - both the looking AND the camera - when it is
    switched off. A camera left running is a light on somebody's laptop.
    """
    import shutil
    import subprocess
    node = shutil.which("node")
    if not node:
        return
    src = str(F.CODE / "apps" / "voice" / "app.js").replace("\\", "/")
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "camera.mjs"
        f.write_text(_HARNESS % json.dumps(src), encoding="utf-8")
        r = subprocess.run([node, str(f)], capture_output=True, text=True, timeout=120)
    line = [x for x in (r.stdout or "").splitlines() if x.startswith("{")]
    if not line:
        return t.ok(False, "the page's camera code runs",
                    "node said: %s %s" % (r.stdout[-200:], r.stderr[-300:]))
    got = json.loads(line[-1])
    t.eq(got["opened"], '{"deviceId":{"exact":"cam-b"}}',
         "it opens the camera the face app already named")
    t.ok(got["first"] >= 1 and got["second"] > got["first"],
         "Check by itself keeps looking without anyone pressing anything",
         "looks went %r then %r" % (got["first"], got["second"]))
    t.eq(got["after_off"], got["second"], "switching it off stops the looking")
    t.ok(got["stopped"] >= 1, "switching it off releases the camera",
         "no track was stopped")


def _their_side(t):
    """Reconize is another program, and persist=false only works while THEIR
    code still reads it. An update of theirs that drops the flag would make
    the Voice page quietly fill the disk again, so the one line that matters
    is checked where it lives - and skipped when the folder is not here."""
    import re
    sys.path.insert(0, str(F.CODE / "tools"))
    import registry
    got = registry.load(F.CODE / "config" / "partners.json")
    folder = str((got.get("reconize") or {}).get("folder") or "")
    f = Path(folder) / "backend" / "app" / "api" / "recognition.py" if folder else None
    if not f or not f.is_file():
        return                                          # their code is not on this PC
    src = f.read_text(encoding="utf-8", errors="replace")
    t.ok(re.search(r"persist:\s*bool\s*=\s*True", src) is not None
         and re.search(r"if persist:\s*\n\s*background_tasks\.add_task", src) is not None,
         "the face app still honours persist=false",
         "their recognition.py no longer guards the persist background task")


def _post(url, data):
    import urllib.request
    req = urllib.request.Request(url, data=data, method="POST",
                                 headers={"Content-Type": "image/jpeg"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.status, r.read().decode("utf-8")
