"""The Voice page shows the camera it looks with, and sends none of it.

A42-2, user 2026-10-15: *voice does not show the camera?* The picker chose a
camera, but its picture appeared only for the second of a "Check who I am".
Now "Show the camera" keeps a live view:

  * this device's camera - opened here, shown here, no frame sent anywhere;
  * a rig camera (config/faces.json look.cameras) - the hub's live view of
    that board (/api/dev/cam.stream), the same relay the watcher reads, so a
    second viewer costs the board nothing;
  * a camera only the face app knows - it has no address we can show, so the
    line under it says where its picture is.

Easy to break unseen: the view must stop with the switch AND with a hidden
tab (a board streaming to nobody holds the hub's relay open), and showing a
picture must never post one to /api/voice/identify - the no-photo rule of
2026-09-29 is about what leaves the page.
"""
import json
import os
import shutil
import subprocess
import tempfile
import threading
from pathlib import Path

import qc as F

AREA = "tools"
TITLE = "the Voice page shows the chosen camera live, and stops it when hidden"


def _stations(t):
    """The helper hands the page a rig camera's address, from data."""
    import importlib.util
    import sys
    path = F.CODE / "apps" / "voice" / "service.py"
    spec = importlib.util.spec_from_file_location("voice_view_check", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["voice_view_check"] = mod
    spec.loader.exec_module(mod)
    b = mod.Brain.__new__(mod.Brain)                 # no files, no threads
    b.cfg = {"face": {"watcher": "http://127.0.0.1:9/state"}}
    b._tts_lock = threading.Lock()
    b._reconize_api = lambda: ""                     # no face app here
    b._watcher_present = lambda *a, **k: {"cameras": ["door"]}
    with tempfile.TemporaryDirectory() as d:
        cfg = Path(d) / "faces.json"
        cfg.write_text('{"look": {"cameras": [\n'
                       '  {"name": "door", "dev": "wifi:192.168.4.2"},  // watched\n'
                       '  {"name": "stage", "dev": "wifi:192.168.4.3"}\n]}}',
                       encoding="utf-8")
        old = os.environ.get("MICE_FACES_CONFIG")
        os.environ["MICE_FACES_CONFIG"] = str(cfg)
        try:
            got = b.face_stations()
        finally:
            if old is None:
                os.environ.pop("MICE_FACES_CONFIG", None)
            else:
                os.environ["MICE_FACES_CONFIG"] = old
    by = {s["id"]: s for s in got}
    t.ok(by.get("door", {}).get("dev") == "wifi:192.168.4.2",
         "a rig camera the watcher reads carries its board's address", repr(got))
    t.ok(by.get("stage", {}).get("dev") == "wifi:192.168.4.3",
         "a rig camera is listed to show even while the watcher is off", repr(got))
    t.eq(len(got), 2, "each camera is listed once")


_HARNESS = r"""
import fs from "fs";
const js = fs.readFileSync(%s, "utf8");
const calls = {identify: 0, opened: 0, stopped: 0};
const el = (id) => { const e = {id, style: {}, hidden: true, textContent: "", checked: false,
  innerHTML: "", value: "", srcObject: null, videoWidth: 640, videoHeight: 480,
  attrs: {}, classList: {toggle() {}, add() {}, remove() {}, contains: () => false},
  dataset: {}, children: [], options: [],
  appendChild() {}, prepend() {}, remove() {}, focus() {}, blur() {},
  setAttribute(k, v) { this.attrs[k] = v; }, removeAttribute(k) { delete this.attrs[k]; },
  scrollIntoView() {}, querySelector: () => null, querySelectorAll: () => [],
  play: async () => {}, pause() {}, addEventListener() {}};
  Object.defineProperty(e, "src", {get() { return this.attrs.src || ""; },
                                   set(v) { this.attrs.src = String(v); }});
  return e; };
const els = {}; const store = {}; const docEvents = {};
globalThis.localStorage = {getItem: k => (k in store ? store[k] : null),
  setItem: (k, v) => { store[k] = String(v); }, removeItem: k => { delete store[k]; }};
globalThis.document = {hidden: false, body: el("body"), querySelector: () => null,
  querySelectorAll: () => [], getElementById: id => (els[id] = els[id] || el(id)),
  createElement: (tag) => el(tag), createTextNode: () => el("text"),
  addEventListener(k, f) { (docEvents[k] = docEvents[k] || []).push(f); }};
const track = {stop: () => { calls.stopped++; }};
Object.defineProperty(globalThis, "navigator", {configurable: true, writable: true, value: {
  mediaDevices: {
    enumerateDevices: async () => ([{kind: "videoinput", deviceId: "cam-a", label: "Laptop Camera"}]),
    getUserMedia: async () => { calls.opened++; return {getTracks: () => [track]}; }}}});
globalThis.fetch = async (u) => {
  if (String(u).endsWith("/api/voice/identify")) calls.identify++;
  if (String(u).endsWith("/api/voice/camera"))
    return {json: async () => ({ok: true, label: "", seconds: 2, stations: [
      {id: "door", name: "door", online: true, dev: "wifi:192.168.4.2"},
      {id: "kiosk", name: "Kiosk", online: true}]})};
  return {json: async () => ({ok: true, config: {tts: {}, stt: {}, llm: {}}, faqs: [],
                              parts: {}, modules: [], sequences: [], person: ""})};
};
globalThis.window = globalThis;
globalThis.miceLogin = {mount() {}};
eval(js);
const app = globalThis.voiceApp;
const wait = (ms) => new Promise(r => setTimeout(r, ms));
await app.loadCamera();
const out = {};
// 1: this device - shown, then let go with the switch
els.camShow.checked = true;
await window.toggleView();
out.dev_opened = calls.opened; out.dev_box = !els.camBox.hidden; out.dev_vid = !els.camVid.hidden;
els.camShow.checked = false;
await window.toggleView();
out.dev_stopped = calls.stopped; out.dev_box_off = els.camBox.hidden;
// 2: a rig camera - the hub's live view, no camera opened here
els.camShow.checked = true;
await window.toggleView();
const opened = calls.opened, stopped = calls.stopped;
els.camPick.value = "station:door";
window.pickCamera();
await wait(50);
out.rig_src = els.camImg.src; out.rig_img = !els.camImg.hidden;
out.rig_vid_hidden = els.camVid.hidden; out.rig_opened = calls.opened - opened;
out.rig_let_go = calls.stopped - stopped;
// 3: a hidden tab ends the stream, coming back starts it again
document.hidden = true; (docEvents.visibilitychange || []).forEach(f => f());
out.hidden_src = els.camImg.src;
document.hidden = false; (docEvents.visibilitychange || []).forEach(f => f());
await wait(20);
out.back_src = els.camImg.src;
// 4: a camera only the face app knows - words, no picture
els.camPick.value = "station:kiosk";
window.pickCamera();
await wait(50);
out.kiosk_src = els.camImg.src; out.kiosk_say = els.camSay.textContent;
// 5: switched off
els.camPick.value = "station:door";
window.pickCamera();
await wait(20);
els.camShow.checked = false;
await window.toggleView();
out.off_src = els.camImg.src; out.off_box = els.camBox.hidden;
out.identify = calls.identify;
console.log(JSON.stringify(out));
process.exit(0);
"""


def _the_page(t):
    node = shutil.which("node")
    if not node:
        return
    src = str(F.CODE / "apps" / "voice" / "app.js").replace("\\", "/")
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "view.mjs"
        f.write_text(_HARNESS % json.dumps(src), encoding="utf-8")
        r = subprocess.run([node, str(f)], capture_output=True, text=True, timeout=120)
    line = [x for x in (r.stdout or "").splitlines() if x.startswith("{")]
    if not line:
        return t.ok(False, "the page's camera view code runs",
                    "node said: %s %s" % (r.stdout[-200:], r.stderr[-300:]))
    g = json.loads(line[-1])
    t.ok(g["dev_opened"] == 1 and g["dev_box"] and g["dev_vid"],
         "Show the camera shows this device's camera", repr(g))
    t.ok(g["dev_stopped"] >= 1 and g["dev_box_off"],
         "switching it off lets this device's camera go", repr(g))
    t.eq(g["rig_src"], "/api/dev/cam.stream?dev=wifi%3A192.168.4.2",
         "a rig camera is shown through the hub's live view of its board")
    t.ok(g["rig_img"] and g["rig_vid_hidden"] and g["rig_opened"] == 0 and g["rig_let_go"] >= 1,
         "...and this device's camera is let go, none opened for it", repr(g))
    t.ok(g["hidden_src"] == "" and g["back_src"].startswith("/api/dev/cam.stream"),
         "a hidden tab ends the stream and coming back starts it again", repr(g))
    t.ok(g["kiosk_src"] == "" and "Open Reconize" in g["kiosk_say"],
         "a face-app camera says where its picture is", repr(g))
    t.ok(g["off_src"] == "" and g["off_box"],
         "switching the view off ends the board's stream", repr(g))
    t.eq(g["identify"], 0, "showing the picture sends no picture anywhere")


def run(t):
    _stations(t)
    _the_page(t)
    page = (F.CODE / "apps" / "voice" / "index.html").read_text(encoding="utf-8")
    t.ok('id="camShow"' in page and 'id="camImg"' in page and "window.toggleView" in page,
         "the built page has the Show the camera switch and its picture",
         "camShow, camImg or the window.toggleView bridge is missing")
