"""The Voice page starts the talk gestures when the SOUND starts (A46-1).

User 2026-10-22: gestures that fit the words, *ส่งทำพร้อมกัน* - done together
with the speech. The hub picks and times the gestures over the speech's
length (check_gestures); this page only says WHEN and HOW LONG. So, run in
node with the hub and the sound faked:

* nothing is sent before this answer's sound plays, and a different answer's
  sound does not start it;
* when the sound plays, POST /api/gestures/play carries this answer's text,
  its length in ms (from the audio), the robot's route, the manner and event;
* the hooks in speakAndWait() are what call it - a real speakAndWait run with
  a fake Audio element ends in a play request with that audio's length;
* the 👋 switch off sends nothing; Stop ends gestures that are playing.
"""
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

import qc as F

AREA = "tools"
TITLE = "the Voice page starts gestures with the sound, timed to its length"

_HARNESS = r"""
import fs from "fs";
const js = fs.readFileSync(%s, "utf8");
const el = (id) => ({id, style: {}, hidden: true, textContent: "", checked: false,
  innerHTML: "", value: "", dataset: {}, children: [], options: [],
  classList: {toggle() {}, add() {}, remove() {}, contains: () => false},
  appendChild() {}, prepend() {}, remove() {}, focus() {}, blur() {},
  setAttribute() {}, removeAttribute() {}, scrollIntoView() {},
  querySelector: () => null, querySelectorAll: () => [], addEventListener() {}});
const els = {}; const store = {};
globalThis.localStorage = {getItem: k => (k in store ? store[k] : null),
  setItem: (k, v) => { store[k] = String(v); }, removeItem: k => { delete store[k]; }};
globalThis.document = {hidden: false, body: el("body"), querySelector: () => null,
  querySelectorAll: () => [], getElementById: id => (els[id] = els[id] || el(id)),
  createElement: (tag) => el(tag), createTextNode: () => el("text"), addEventListener() {}};
Object.defineProperty(globalThis, "navigator", {configurable: true, writable: true,
  value: {mediaDevices: {enumerateDevices: async () => []}}});
const sent = [];
let app;
globalThis.URL = {createObjectURL: () => "blob:x", revokeObjectURL() {}};
globalThis.Audio = class {
  constructor() { this.l = {}; this.duration = 2.5; }
  addEventListener(e, f) { this.l[e] = f; }
  play() { setTimeout(() => { this.onplaying && this.onplaying(); setTimeout(() => this.onended && this.onended(), 20); }, 30); return Promise.resolve(); }
  pause() {}
};
globalThis.fetch = async (u, o) => {
  u = String(u);
  if (u.startsWith("/api/gestures/play")) { sent.push(JSON.parse(o.body)); return {ok: true, json: async () => ({ok: true, playing: true, picks: [{label: "Wave"}]})}; }
  if (u.startsWith("/api/play/stop")) { sent.push({stop: true}); return {ok: true, json: async () => ({ok: true})}; }
  if (u.startsWith("/api/play")) return {ok: true, json: async () => ({running: true, name: "gestures"})};
  if (u.startsWith("/api/modules/all")) return {ok: true, json: async () => ({ok: true, modules: [
      {name: "Lift", type: "lift", routes: [{dev: "usb:COM7"}]},
      {name: "Nong", type: "nong", routes: [{dev: "usb:COM99:67", stale: false}]}]})};
  if (u.startsWith("/api/voice/say")) return {ok: true, headers: {get: () => "audio/mpeg"}, blob: async () => ({size: 10})};
  return {ok: true, json: async () => ({ok: true, config: {tts: {}, stt: {}, llm: {}}, faqs: [], parts: {}, modules: [], sequences: []})};
};
globalThis.window = globalThis;
globalThis.miceLogin = {mount() {}};
eval(js);
app = globalThis.voiceApp;
app.cfg = Object.assign(app.cfg || {}, {scenario: "Mall greeter", tts: {style: "polite"}, scenarios: [{name: "Mall greeter"}]});
const wait = ms => new Promise(r => setTimeout(r, ms));
document.getElementById("gestOn").checked = true;
document.getElementById("sound").checked = true;
const out = {};
// 1. waits for its own sound
let ac = new AbortController();
const p1 = app.doGestures("สวัสดีค่ะ", "th", ac.signal);
await wait(60);
out.before = sent.length;
app.spoke("another answer", 9);
await wait(30);
out.otherSound = sent.length;
app.spoke("สวัสดีค่ะ", 3.2);
await p1;
out.first = sent[0] || null;
// 2. Stop ends them
ac.abort();
await wait(40);
out.stopped = sent.some(x => x.stop);
// 3. the real speakAndWait hook
sent.length = 0;
const p2 = app.doGestures("hello there", "en");
await app.speakAndWait("hello there", "en");
await p2;
out.hooked = sent[0] || null;
// 4. switched off
sent.length = 0;
document.getElementById("gestOn").checked = false;
await app.doGestures("hello", "en");
out.off = sent.length;
console.log(JSON.stringify(out));
process.exit(0);
"""


def run(t):
    node = shutil.which("node")
    if not node:
        t.give_up("node is not installed - the page's own code cannot run here")
    src = str(F.CODE / "apps" / "voice" / "app.js").replace("\\", "/")
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "gestures.mjs"
        f.write_text(_HARNESS % json.dumps(src), encoding="utf-8")
        r = subprocess.run([node, str(f)], capture_output=True, text=True, timeout=60)
    line = [x for x in (r.stdout or "").splitlines() if x.startswith("{")]
    if not t.ok(line, "the page's gesture code runs", "node said: %s %s" % (r.stdout[-200:], r.stderr[-400:])):
        return
    v = json.loads(line[-1])
    t.ok(v["before"] == 0, "nothing is sent before the answer's sound plays", v)
    t.ok(v["otherSound"] == 0, "another answer's sound does not start it", v)
    f1 = v.get("first") or {}
    t.ok(f1.get("text") == "สวัสดีค่ะ" and f1.get("ms") == 3200 and f1.get("lang") == "th",
         "when the sound plays, the hub gets this answer, its language and the sound's length", f1)
    t.ok(f1.get("dev") == "usb:COM99:67", "on the nong robot's live route", f1)
    t.ok(f1.get("manner") == "polite" and f1.get("event") == "Mall greeter",
         "with the voice's manner and the event", f1)
    t.ok(v["stopped"], "Stop ends gestures that are playing", v)
    h = v.get("hooked") or {}
    t.ok(h.get("text") == "hello there" and h.get("ms") == 2500,
         "speakAndWait's own sound starts them, with the audio's real length", h)
    t.ok(v["off"] == 0, "with the Gestures switch off nothing is sent", v)
