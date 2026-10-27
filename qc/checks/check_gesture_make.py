"""Talk gestures: Show speaks, a short line still moves, new moves are made (A46-4).

User 2026-10-27, Studio's Moves while talking: *ใช้แล้วไม่เห็นมีเสียงเลย มีการ
เจนท่าขึ้นมาเองสำหรับคำและท่าที่ไม่เคยใส่ไว้ไหม เช่น ด้านขวาครับ ด้านซ้ายครับ*.
"ด้านขวาครับ" gave "No word asked for a gesture and no beat fitted": the line is
1 s long, the manner asks round(0.35 * 1) = 0 beats and none had room. So:

* plan() moves at least `atLeast` gestures, however short the line;
* config/gesture_makers.json MAKES moves for words no gesture has: direction
  words point that way with that side's arm (ด้านขวา = the robot's right
  arm out to its right), body parts put a hand there, neighbours join;
* Studio fits a made move like any gesture (IK, limits, poseHit, safeKeys +
  planSafe) and refuses one that cannot be made safe; plan() takes the
  unsaved fit as `extra`, and "Keep" saves it to the library;
* the AI path asks the voice helper's think chain (faked here) and the hub
  cleans the reply to known fields in range; it needs a login;
* Show fetches /api/voice/say with the chosen manner, plans over the sound's
  length and plays the preview with it, never driving the robot;
* "Standing straight (Home)" rests the hands at the rig's Home exactly
  (user 2026-10-27: Home/Neutral is standing straight).
"""
import io
import json
import threading
import wave
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import browser
import fake_serial
import qc as F

AREA = "studio"
TITLE = "talk gestures: Show speaks, short lines move, new moves are made and checked"
SLOW = True

SOUND_S = 2.0
HELPER = {"say": [], "gesture": []}

DRIVE = """
function report(s){ rawCmd("MOVE QCMARK MADE~" + s); }
// a save refits in the background: wait for it, then make sure it is current
async function settle(){
  for (var i = 0; i < 3; i++) { while (TALK.busy) await new Promise(function(r){ setTimeout(r, 100); }); await talkCheckFit(); }
}
window.addEventListener("load", function(){ qcStudioReady().then(function(){ setTimeout(async function(){
  try{
    await talkLoad();
    var fitted = await talkFit();
    var mk = await talkMake("ด้านขวาครับ");
    var right = mk.made.filter(function(m){ return m.id === "made_right"; })[0] || {};
    // a made move that hits the body is refused, not shown
    var home = RIG.home.map(function(v, j){ return clampJ(j, v); });
    var bad = talkFitDef("qc_bad", [{R: [-0.6, -0.2, -0.3], L: [-0.6, -0.2, -0.3], t: 400}], false);
    $("talkText").value = "ด้านขวาครับ";
    $("talkManner").value = "polite";
    await talkTry();
    var picks = $("talkPicks").textContent;
    var heard = !!TALK.audio, wasPlaying = playing, prev = previewOnly;
    if (playing) await togglePlay();
    // keep it, then rest standing straight
    var kept = right.fit ? (await talkSave({gestures: {made_right: {label: right.label, mine: true, made: "rules",
      mirror: right.mirror, words: right.words, keys: right.keys}}}), !!TALK.lib.gestures.made_right) : false;
    await settle();
    var keptFit = !!(TALK.fit.gestures || {}).made_right;
    await talkSave({restStyle: "straight"});
    await settle();
    var rp = TALK.fit.rest.keys[TALK.fit.rest.keys.length - 1].pose;
    var straight = rp.every(function(v, j){ return Math.abs(v - home[j]) < 0.01; });
    report("fitted=" + fitted + "~made=" + mk.made.map(function(m){ return m.id; }).join("_") +
           "~rightFit=" + Object.keys(right.fit || {}).join("_").replace(/[^\\w]/g, "_") +
           "~bad=" + !!bad.bad + "~heard=" + heard + "~playing=" + wasPlaying + "~preview=" + prev +
           "~picked=" + (picks.indexOf("Point right") >= 0) + "~kept=" + kept + "~straight=" + straight +
           "~keptFit=" + keptFit);
  }catch(e){ report("ERR-" + String(e).slice(0,70).replace(/[^\\w ]/g, "")); }
  setTimeout(function(){ report("done"); }, 300);
}, 150); }); });
"""


def _wav(seconds):
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(8000)
        w.writeframes(b"\0\0" * int(8000 * seconds))
    return buf.getvalue()


class _Helper(BaseHTTPRequestHandler):
    """The voice helper, faked: /say answers SOUND_S seconds of silence,
    /gesture answers a model-like reply with junk around and out of range."""
    def log_message(self, *a):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
        if self.path == "/say":
            HELPER["say"].append(body)
            out, kind = _wav(SOUND_S), "audio/wav"
        else:
            HELPER["gesture"].append(body)
            out = json.dumps({"ok": True, "text": 'Sure! {"label": "Point up high", "word": "ฟ้า", "keys": ['
                              '{"R": [0.2, 3, 0.4], "palmR": "sideways", "t": 99999, "hold": -5, "x": 1}]}'}).encode()
            kind = "application/json"
        self.send_response(200)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)


def _post(base, path, **kw):
    s, b = F.post(base + path, json.dumps(kw).encode())
    return s, json.loads(b or "{}")


def run(t):
    if not browser.available():
        t.give_up("headless Edge not found - this needs a real browser")
    fake_serial.reset()
    base, main = F.start_hub()
    helper = ThreadingHTTPServer(("127.0.0.1", 0), _Helper)
    threading.Thread(target=helper.serve_forever, daemon=True).start()
    real_url = main.voice_service_url
    main.voice_service_url = lambda: ("http://127.0.0.1:%d" % helper.server_port, "")
    import gestures as G
    try:
        F.login(base)
        G.mine_path(main.STUDIO).unlink(missing_ok=True)

        # ---- rules, open to Studio with no login ---------------------------
        s, j = _post(base, "/api/gestures/make", text="ด้านขวาครับ แล้วก็ด้านซ้ายนะ ข้างบนขวามือ ขอบคุณ")
        made = {m["id"]: m for m in j.get("made") or []}
        r = made.get("made_right") or {}
        t.ok(s == 200 and r.get("keys") and list(r["keys"][0])[0] == "R" and r["keys"][0]["R"][0] > 0.6,
             "ด้านขวา makes a move: the right arm out to its right", made)
        lf = made.get("made_left") or {}
        t.ok(lf.get("keys") and "L" in lf["keys"][0] and not lf.get("mirror"),
             "ด้านซ้าย the left arm, never mirrored to the other side", lf)
        ur = made.get("made_up_right") or {}
        t.ok(ur.get("keys") and ur["keys"][0]["R"][1] > 0.3 and ur["keys"][0]["R"][0] > 0.3,
             "words side by side join into one move (up + right)", ur)
        t.ok(not any("thank" in m.get("label", "").lower() for m in made.values()) and len(made) == 3,
             "a word a gesture already has makes nothing", list(made))

        # ---- AI: gated, and its reply cleaned ------------------------------
        F.logout_qc()
        s, _j = _post(base, "/api/gestures/think", text="บนฟ้ามีดาว")
        t.ok(s in (401, 403) and not HELPER["gesture"], "asking the AI needs a login", s)
        F.login(base)
        s, j = _post(base, "/api/gestures/think", text="บนฟ้ามีดาว")
        a = (j.get("made") or [{}])[0]
        k = (a.get("keys") or [{}])[0]
        t.ok(HELPER["gesture"] and "JSON" in HELPER["gesture"][-1].get("prompt", "")
             and HELPER["gesture"][-1].get("text") == "บนฟ้ามีดาว",
             "the helper is asked with the prompt from config/gesture_makers.json", HELPER["gesture"][-1:])
        t.ok(j.get("ok") and abs(sum(x * x for x in k.get("R", [9])) ** 0.5 - 1) < 0.01
             and k.get("t") == 1500 and k.get("hold") == 0 and "palmR" not in k and "x" not in k,
             "the AI's move is cleaned: in reach, times in range, unknown fields dropped", a)

        # ---- a short line still moves ----------------------------------------
        browser.page(DRIVE, query="%s/studio/_qcdriver.html?dev=usb%%3A%s" % (base, fake_serial.PORT), seconds=120)
        v = {}
        for m in fake_serial.qc_marks:
            if m.startswith("MADE~") and "=" in m:
                v = dict(kv.split("=", 1) for kv in m[5:].split("~"))
        t.ok(v.get("fitted") == "true" and v.get("made") == "made_right" and v.get("rightFit") == "made_right",
             "Studio makes ด้านขวา's move and fits it to this robot (right arm only)", v)
        t.ok(v.get("bad") == "true", "a made move through the body is refused", v)
        t.ok(HELPER["say"] and HELPER["say"][-1].get("text") == "ด้านขวาครับ" and HELPER["say"][-1].get("style") == "polite",
             "Show asks the voice for the sentence in the chosen manner", HELPER["say"][-1:])
        t.ok(v.get("heard") == "true" and v.get("playing") == "true" and v.get("preview") == "true",
             "and plays the moves with the sound, as a preview only", v)
        t.ok(v.get("picked") == "true", "ด้านขวาครับ now points right", v)
        t.ok(v.get("kept") == "true" and v.get("keptFit") == "true",
             "a made move kept is a gesture, fitted like the rest", v)
        t.ok(v.get("straight") == "true", "standing straight rests the hands at Home exactly", v)
        fit = json.loads(F.get(base + "/api/gestures")[1]).get("fit") or {}
        lib = json.loads(F.get(base + "/api/gestures")[1]).get("lib") or {}
        p = G.plan(lib, fit, "ด้านขวาครับ", "th", "", "", 0, 3)
        t.ok(p.get("ok") and "made_right" in [x["id"] for x in p["picks"]],
             "and the Voice page's plan uses the kept move for its word", p.get("picks"))
        q = G.plan(lib, fit, "ครับ", "th", "", "", 0, 3)
        t.ok(q.get("ok") and len(q["picks"]) >= 1, "a line with no gesture word still gets a beat", q.get("picks"))
    finally:
        main.voice_service_url = real_url
        helper.shutdown()
        G.mine_path(main.STUDIO).unlink(missing_ok=True)
