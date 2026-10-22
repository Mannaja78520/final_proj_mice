"""Gestures that match what the robot says, played with the speech (A46-1).

User 2026-10-22: *ขอแบบลองสุ่มท่าทางออกมาให้เข้ากับคำที่พูดแล้วส่งทำพร้อมกัน
... เอาตัวขนาดของหุ่นมาใส่แล้วทำท่าทางได้ อาจจะโคกับ nong studio ดึงข้อมูลจากกันได้*

One library (config/gestures.json), two halves:

* Nong Studio FITS it to the robot (IK on the rig's sizes, every pose and move
  through safe_path.js) and posts the fit to the hub - asserted here by running
  the real fit in a browser on the QC rig;
* the hub picks and times gestures for a sentence (main_python/gestures.py):
  the words bring their gestures, random beats fill the gaps, the manner sets
  the tempo, an event can switch it off, the same seed gives the same plan;
* /api/gestures/play sends it to the robot - and what REACHED the module
  (fake_serial.wire) is checked in Studio again at 1 degree steps for any hit
  on the robot's own body, inside every joint's limits, never faster than
  maxDps; a show already playing is never taken over.
"""
import json

import browser
import fake_serial
import qc as F

AREA = "studio"
TITLE = "talk gestures fit the robot, match the words and play clear of its body"
SLOW = True

SAY = "สวัสดีค่ะ ยินดีต้อนรับทุกคนนะคะ วันนี้มีอะไรให้ช่วยไหมคะ ขอบคุณค่ะ"
# the play test also says the QC gesture that has to go round the body
PLAY = "qcround สวัสดีค่ะ ยินดีต้อนรับทุกคน"

FIT = """
function report(s){ rawCmd("MOVE QCMARK TALK~" + s); }
window.addEventListener("load", function(){ qcStudioReady().then(function(){ setTimeout(async function(){
  try{
    var loaded = await talkLoad();
    var stale = talkStale();
    // two gestures made "on the time bar": one whose pose is clear but whose
    // straight move from the resting hands goes through the body, one that hits
    var home = RIG.home.map(function(v, j){ return clampJ(j, v); });
    var rest0 = talkKeyPose(TALK.lib.rest.keys[0], home, home, false);
    var s = 11, rnd = function(){ s = (s * 16807) % 2147483647; return s / 2147483647; };
    var A = null, H = null;
    for (var n = 0; n < 4000 && !(A && H); n++) {
      var q = home.slice();
      for (var j = 0; j < ARMJ; j++) q[j] = clampJ(j, RIG.min[j] + rnd() * (RIG.max[j] - RIG.min[j]));
      if (collisionAt(q)) { H = H || q; continue; }
      if (!A && pathHit(rest0, q) && pathHit(q, rest0)) A = q;
    }
    await fetch("/api/gestures", {method: "POST", body: JSON.stringify({gestures: {
      qc_round: {label: "QC round", mine: true, words: {any: ["qcround"]}, keys: [{pose: A, t: 600, hold: 200}]},
      qc_hit: {label: "QC hit", mine: true, words: {any: ["qchit"]}, keys: [{pose: H, t: 600}]}}})});
    await talkLoad();
    var t0 = performance.now();
    var ok = await talkFit();
    var ms = Math.round(performance.now() - t0);
    var F = TALK.fit || {};
    report("loaded=" + loaded + "~stale=" + stale + "~fitted=" + ok + "~ms=" + ms +
           "~n=" + Object.keys(F.gestures || {}).length + "~bad=" + Object.keys(F.bad || {}).map(function(b){ return b + "_" + F.bad[b]; }).join("_").replace(/[^\\w]/g, "_") +
           "~direct=" + (F.direct || []).length + "~after=" + talkStale() +
           "~card=" + !document.getElementById("talkCard").hidden + "~A=" + !!A + "~H=" + !!H);
  }catch(e){ report("ERR-" + String(e).slice(0,70).replace(/[^\\w ]/g, "")); }
  setTimeout(function(){ report("done"); }, 300);
}, 150); }); });
"""

CHECK = """
function report(s){ rawCmd("MOVE QCMARK TALK2~" + s); }
window.addEventListener("load", function(){ qcStudioReady().then(function(){ setTimeout(function(){
  try{
    var P = %s, hits = 0, where = "";
    for (var i = 1; i < P.length; i++) {
      var n = Math.max(1, Math.ceil(safeGap(P[i - 1], P[i])));
      for (var s = 1; s <= n; s++) { var h = collisionAt(safeLerp(P[i - 1], P[i], s / n)); if (h) { hits++; where = where || (i + h); break; } }
    }
    report("poses=" + P.length + "~hits=" + hits + "~where=" + where.replace(/[^\\w]/g, "_"));
  }catch(e){ report("ERR-" + String(e).slice(0,70).replace(/[^\\w ]/g, "")); }
  setTimeout(function(){ report("done"); }, 300);
}, 150); }); });
"""


def _marks(prefix):
    got = [m[len(prefix):] for m in fake_serial.qc_marks if m.startswith(prefix)]
    for m in got:
        if "=" in m and "~" in m:
            return dict(kv.split("=", 1) for kv in m.split("~"))
    return {"_raw": str(got)}


def _plan(base, **kw):
    s, b = F.post(base + "/api/gestures/plan", json.dumps(kw).encode())
    return json.loads(b or "{}")


def run(t):
    if not browser.available():
        t.give_up("headless Edge not found - this needs a real browser")
    fake_serial.reset()
    base, main = F.start_hub()
    F.login(base)
    F.post(base + "/api/gestures", json.dumps({"fit": None}).encode())   # no fit from an earlier run
    import gestures as G
    G.mine_path(main.STUDIO).unlink(missing_ok=True)

    s, b = F.get(base + "/api/gestures")
    j = json.loads(b or "{}")
    lib = j.get("lib") or {}
    t.ok(s == 200 and len(lib.get("gestures") or {}) >= 8, "the hub serves the gesture library", b[:200])
    p = _plan(base, text=SAY)
    t.ok(not p.get("ok") and "Studio" in (p.get("why") or ""),
         "with no fit yet, no gestures - and it says Studio fits them", p)

    # ---- 1. Studio fits the library to the QC rig ---------------------------
    browser.page(FIT, query="%s/studio/_qcdriver.html?dev=usb%%3A%s" % (base, fake_serial.PORT), seconds=90)
    v = _marks("TALK~")
    t.ok(v.get("loaded") == "true" and v.get("stale") == "true",
         "Studio reads the library from the hub and sees it is not fitted yet", v)
    t.ok(v.get("bad") == "qc_hit_" + v.get("bad", "")[7:] and v.get("bad", "").startswith("qc_hit_"),
         "every shipped gesture fits the QC rig, clear of its body; the one made to hit is left out", v)
    t.ok(v.get("fitted") == "true" and int(v.get("n") or 0) >= 10,
         "Studio fits the gestures to this robot", v)
    t.ok(v.get("after") == "false", "and then calls the fit current", v)
    t.ok(v.get("card") == "true", "the Moves while talking card shows with the hub", v)
    fit = json.loads(F.get(base + "/api/gestures")[1]).get("fit") or {}
    t.ok(fit.get("rig", {}).get("home") and fit.get("gestures"), "the hub keeps the fit", list(fit)[:6])
    t.ok(not G.mine_path(main.STUDIO).is_relative_to(F.CODE),
         "in QC the fit is written outside the tree", str(G.mine_path(main.STUDIO)))

    t.ok(v.get("A") == "true" and len(((fit.get("gestures") or {}).get("qc_round") or {}).get("in") or []) >= 1,
         "a gesture whose straight move from the resting hands hits the body is fitted with a way round",
         ((fit.get("gestures") or {}).get("qc_round") or {}).get("in"))
    mix = _plan(base, text="qchit hello qcround", lang="en", ms=5000, seed=2)
    t.ok(mix.get("ok") and "qc_round" in [x["id"] for x in mix["picks"]]
         and "qc_hit" not in [x["id"] for x in mix["picks"]],
         "a gesture left out is never played; the one that goes round is", mix.get("picks"))

    # ---- 2. the plan: words, randomness, manner, events ---------------------
    p = _plan(base, text=SAY, lang="th", manner="friendly", ms=6000, seed=3)
    if not t.ok(p.get("ok"), "a Thai answer gets gestures", p):
        return
    words = [x["word"] for x in p["picks"] if x["word"]]
    ids = [x["id"] for x in p["picks"]]
    t.ok("สวัสดี" in words and "wave" in ids, "สวัสดี brings a wave", p["picks"])
    t.ok("ทุกคน" in words or "ขอบคุณ" in words, "and a later word brings its own gesture", p["picks"])
    t.ok("คุณ" not in words, "คุณ inside ขอบคุณ is not taken as a word of its own", p["picks"])
    t.ok(all(0 <= x["at"] <= 6000 for x in p["picks"]), "every gesture starts while the robot talks", p["picks"])
    t.ok(p["picks"] == sorted(p["picks"], key=lambda x: x["at"]), "in the order of the words", p["picks"])
    t.ok(abs(p["total_ms"] - 6000) < 3000, "the moves last about as long as the speech",
         "speech 6000 ms, moves %s ms" % p["total_ms"])
    same = _plan(base, text=SAY, lang="th", manner="friendly", ms=6000, seed=3)
    t.ok(same.get("steps") == p["steps"], "the same seed gives the same plan", "")
    plans = [_plan(base, text=SAY, lang="th", manner="friendly", ms=6000, seed=n) for n in range(6)]
    t.ok(len({json.dumps(x.get("steps")) for x in plans}) >= 3,
         "different seeds give different moves (random, not one fixed routine)",
         [[(y["id"], y["mirrored"]) for y in x.get("picks", [])] for x in plans][:3])
    long = "เรื่องนี้น่าสนใจมาก " * 6
    calm = _plan(base, text=long, lang="th", manner="recite", ms=12000, seed=1)
    lively = _plan(base, text=long, lang="th", manner="playful", ms=12000, seed=1)
    t.ok(len(lively.get("picks", [])) > len(calm.get("picks", [])),
         "a playful manner moves more than a recited one",
         "playful %d, recite %d" % (len(lively.get("picks", [])), len(calm.get("picks", []))))
    home = fit["rig"]["home"]
    st = p["steps"]
    t.ok(st[0]["pose"] == [float(x) for x in home] and st[-1]["pose"] == [float(x) for x in home],
         "it starts and ends at the robot's home pose", (st[0]["pose"], st[-1]["pose"]))
    lo, hi = fit["rig"]["min"], fit["rig"]["max"]
    t.ok(all(lo[j] <= s_["pose"][j] <= hi[j] for s_ in st for j in range(10)),
         "every pose is inside every joint's limits", "")
    dps = float(lib.get("maxDps", 150))
    fast = [i for i in range(1, len(st)) if st[i]["t"] + 1 <
            max(abs(a - b) for a, b in zip(st[i - 1]["pose"], st[i]["pose"])) / dps * 1000]
    t.ok(not fast, "no move is faster than maxDps", fast[:3])

    F.post(base + "/api/gestures", json.dumps({"events": {"QC quiet hall": {"on": False}}}).encode())
    off = _plan(base, text=SAY, event="QC quiet hall")
    t.ok(not off.get("ok") and off.get("off"), "an event switched off gets no gestures", off)
    t.ok(_plan(base, text=SAY, event="another event").get("ok"), "and other events still do", "")
    F.post(base + "/api/gestures", json.dumps({"on": False}).encode())
    t.ok(_plan(base, text=SAY).get("off"), "the main switch turns them all off", "")
    F.post(base + "/api/gestures", json.dumps({"on": True}).encode())

    # ---- 3. play: gated, never over a show, and what reaches the robot -------
    dev = "usb:" + fake_serial.PORT
    F.logout_qc()
    s, _b = F.post(base + "/api/gestures/play", json.dumps({"dev": dev, "text": SAY}).encode())
    t.ok(s in (401, 403), "playing gestures needs a login", s)
    F.login(base)
    main.show.start(dev, [{"pose": home, "t": 0, "hold": 3000}, {"pose": home, "t": 100, "hold": 0}],
                    False, "someone's show")
    s, b = F.post(base + "/api/gestures/play", json.dumps({"dev": dev, "text": SAY}).encode())
    busy = json.loads(b or "{}")
    t.ok(busy.get("busy") and main.show.status().get("name") == "someone's show",
         "gestures never take over a show that is playing", busy)
    main.show.stop()
    fake_serial.reset()
    F.cmd(base, "MOVE QCMARK TALK~PLAY")
    s, b = F.post(base + "/api/gestures/play", json.dumps(
        {"dev": dev, "text": PLAY, "lang": "th", "ms": 5000, "seed": 5}).encode())
    played = json.loads(b or "{}")
    t.ok(s == 200 and played.get("playing"), "the gestures start on the robot", b[:200])
    t.ok("qc_round" in [x["id"] for x in played.get("picks", [])],
         "including the one that has to go round the body", played.get("picks"))
    import time
    end = time.time() + 25
    while main.show.status().get("running") and time.time() < end:
        time.sleep(0.2)
    cmds = [c for _ms, c in fake_serial.wire]
    sent = [[float(x) for x in c.split()[1:11]] for c in cmds if c.upper().startswith("POSE ")]
    t.ok(len(sent) >= len(played.get("steps", [])) - 1 and len(sent) >= 3,
         "the robot received the gestures' poses", "%d poses for %d steps" % (len(sent), len(played.get("steps", []))))
    t.ok(all(lo[j] - 0.05 <= q[j] <= hi[j] + 0.05 for q in sent for j in range(10)),
         "every pose that reached the robot is inside its limits", "")
    browser.page(CHECK % json.dumps([home] + sent),
                 query="%s/studio/_qcdriver.html?dev=usb%%3A%s" % (base, fake_serial.PORT), seconds=40)
    w = _marks("TALK2~")
    t.ok(w.get("hits") == "0" and int(w.get("poses") or 0) >= 3,
         "and no move the robot was sent passes through its body (1 degree steps)", w)
    G.mine_path(main.STUDIO).unlink(missing_ok=True)
