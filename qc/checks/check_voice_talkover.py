"""The Voice page does not answer the rig's own voice (A4-4).

Conversation mode listens, answers, and listens again. Its answer through a
robot now waits in the rig's ONE speaking queue (hub_speak.py), and a face
greeting can start at any moment - both play outside this browser, so the
page cannot hear them end. Listening straight away then records the rig
itself, and the page answers its own words: a loop that talks to itself.

So the page asks the hub (GET /api/speak): it waits while the rig talks
before it listens, and throws away a recording made while the rig spoke. An
older hub, or a page that is not logged in, answers nothing useful - and the
page must then carry on as before rather than wait forever. This runs the
page's own conversation loop in node, with the microphone and the hub faked.
"""
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

import qc as F

AREA = "tools"
TITLE = "conversation mode waits for the rig and never answers its own voice"

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
// The hub's speaking queue, as a script: one answer per GET /api/speak.
const rig = {script: [], polls: 0, refuse: false};
const seen = {transcribed: 0, recordings: 0, lines: []};
let app;
globalThis.fetch = async (u) => {
  if (String(u).startsWith("/api/speak")) {
    rig.polls++;
    if (rig.refuse) return {ok: false, status: 401, json: async () => ({need_login: true})};
    const st = rig.script.length ? rig.script.shift() : {speaking: false, quietFor: 99};
    return {ok: true, status: 200, json: async () => st};
  }
  if (String(u).startsWith("/api/voice/transcribe")) {
    seen.transcribed++;
    app.stopConv();                           // one answer is enough to judge
    return {ok: true, json: async () => ({ok: true, text: "hello", language: "en"})};
  }
  return {ok: true, json: async () => ({ok: true, config: {tts: {}, stt: {}, llm: {}},
                                        faqs: [], parts: {}, modules: [], sequences: []})};
};
globalThis.window = globalThis;
globalThis.miceLogin = {mount() {}};
eval(js);
app = globalThis.voiceApp;
app.convListenOnce = async () => { seen.recordings++; return {size: 100}; };
const say = app.say.bind(app);
app.say = (t) => { seen.lines.push(String(t)); return say(t); };

// 1. The rig is talking when the loop would listen: it waits, then listens.
//    The first recording overlapped the rig's speech: it is thrown away.
rig.script = [{speaking: true}, {speaking: true}, {speaking: false, quietFor: 0.1},
              {speaking: false, quietFor: 0.2},      // after recording 1: rig spoke
              {speaking: false, quietFor: 0.5},      // before recording 2
              {speaking: false, quietFor: 30}];      // after recording 2: quiet
const t0 = Date.now();
await app.startConv();
const one = {recordings: seen.recordings, transcribed: seen.transcribed,
             polls: rig.polls, waited: Date.now() - t0,
             dropped: seen.lines.some(l => /robot was talking/.test(l))};

// 2. A hub that will not say (older, or not logged in): no waiting forever.
seen.recordings = 0; seen.transcribed = 0; rig.polls = 0; rig.refuse = true;
const t1 = Date.now();
await app.startConv();
const two = {recordings: seen.recordings, transcribed: seen.transcribed,
             waited: Date.now() - t1};
console.log(JSON.stringify({one, two}));
process.exit(0);
"""


def run(t):
    node = shutil.which("node")
    if not node:
        t.give_up("node is not installed - the page's own loop cannot run here")
    src = str(F.CODE / "apps" / "voice" / "app.js").replace("\\", "/")
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "talkover.mjs"
        f.write_text(_HARNESS % json.dumps(src), encoding="utf-8")
        r = subprocess.run([node, str(f)], capture_output=True, text=True, timeout=120)
    line = [x for x in (r.stdout or "").splitlines() if x.startswith("{")]
    if not t.ok(line, "the page's conversation loop runs",
                "node said: %s %s" % (r.stdout[-200:], r.stderr[-400:])):
        return
    got = json.loads(line[-1])
    one, two = got["one"], got["two"]
    t.ok(one["waited"] >= 500 and one["polls"] >= 3,
         "while the rig talks, the page waits before it listens (%d ms, %d asks)"
         % (one["waited"], one["polls"]))
    t.ok(one["recordings"] == 2 and one["transcribed"] == 1 and one["dropped"],
         "a recording made while the rig spoke is thrown away, and the next is answered",
         json.dumps(one))
    t.ok(two["recordings"] == 1 and two["transcribed"] == 1 and two["waited"] < 3000,
         "a hub that will not say is not waited on: the page carries on as before",
         json.dumps(two))
