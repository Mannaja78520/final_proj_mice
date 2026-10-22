"""A move that would go through the body goes ROUND it instead (A46-1).

User 2026-10-22: *ก็เพราะกลัวชนตัวเอง* - the arm must not hit itself when it
copies a person (video, dummy) or gestures while talking. A move is a straight
line in joint space; safe_path.js checks that line with collisionAt() on the
rig's own sizes and only when it hits looks for a way round (RRT-Connect from
both ends, then shortcuts - close to what RRT* gives, far cheaper).

Measured here on the QC rig, not assumed:

* pairs of clear poses whose straight move HITS are found by search, so the
  check never depends on one hand-picked pose that a rig change makes clear;
* every way round starts and ends on the asked poses and is clear at 1 degree
  steps - finer than the planner's own checkDeg, so a too-coarse check fails;
* a pose that itself hits is refused, never "planned";
* safeKeys() leaves a key list that Studio's own checkCollisions() (the eased
  path the robot really drives) calls clean, and keeps the move's time;
* the planner set to "straight" refuses instead of going round.
"""
import browser
import fake_serial
import qc as F

AREA = "studio"
TITLE = "a move through the body goes round it, and a hitting pose is refused"
SLOW = True

DRIVER = """
function report(s){ rawCmd("MOVE QCMARK SAFE~" + s); }
function wait(ms){ return new Promise(function(r){ setTimeout(r, ms); }); }
function rnd0(seed){ var s = seed; return function(){ s = (s * 16807) % 2147483647; return s / 2147483647; }; }
function denseHit(a, b){
  var n = Math.max(1, Math.ceil(safeGap(a, b) / 1));
  for (var s = 1; s <= n; s++) { var h = collisionAt(safeLerp(a, b, s / n)); if (h) return h; }
  return null;
}
window.addEventListener("load", function(){ qcStudioReady().then(function(){ setTimeout(async function(){
  try{
    var r = rnd0(7), pairs = [], hitPose = null, tries = 0;
    var randPose = function(){
      var p = Array(NJ).fill(90);
      for (var j = 0; j < ARMJ; j++) p[j] = RIG.min[j] + r() * (RIG.max[j] - RIG.min[j]);
      return p.map(function(v, j){ return clampJ(j, v); });
    };
    while (pairs.length < 4 && tries < 4000) {
      tries++;
      var a = randPose(), b = randPose();
      if (collisionAt(a)) { hitPose = hitPose || a; continue; }
      if (collisionAt(b)) { hitPose = hitPose || b; continue; }
      if (pathHit(a, b)) pairs.push([a, b]);
    }
    var found = 0, clean = 0, ends = 0, ms = [], fails = [];
    for (var i = 0; i < pairs.length; i++) {
      var p = planSafe(pairs[i][0], pairs[i][1], 4000, 11 + i);
      if (p.fail) { fails.push(p.fail.slice(0, 30)); continue; }
      found++; ms.push(Math.round(p.ms));
      if (p.how === "around" && p.path.length > 2) {
        var ok = true;
        for (var k = 1; k < p.path.length; k++) if (denseHit(p.path[k - 1], p.path[k])) ok = false;
        if (ok) clean++;
      }
      var pa = p.path[0], pb = p.path[p.path.length - 1];
      if (safeGap(pa, pairs[i][0]) < 0.11 && safeGap(pb, pairs[i][1]) < 0.11) ends++;
    }
    var refused = hitPose ? !!planSafe(Array(NJ).fill(90).map(function(v, j){ return clampJ(j, RIG.home ? RIG.home[j] : v); }), hitPose, 500).fail : false;
    // safeKeys on the first pair + a hitting key in between
    var keysOut = "none", timeKept = false, studioClean = false;
    if (pairs.length) {
      var K = [{pose: pairs[0][0], t: 1000, hold: 0}, {pose: hitPose, t: 700, hold: 0},
               {pose: pairs[0][1], t: 1500, hold: 0}];
      var s = safeKeys(K, 4000);
      keysOut = "n" + s.keys.length + "_drop" + s.dropped + "_round" + s.around + "_fail" + s.failed;
      var tIn = 700 + 1500, tOut = s.keys.slice(1).reduce(function(x, k){ return x + k.t + (k.hold || 0); }, 0) + s.keys[0].hold;
      // never shorter than asked: the servos' own minimum may add to a leg
      timeKept = tOut >= tIn - 2 * s.keys.length && tOut <= tIn + s.keys.length * 1500;
      keys = s.keys; bumpKeys();
      studioClean = checkCollisions(false).length === 0;
    }
    // ---- a video of a person whose arm passes through where the robot's body is
    // (check_video_moves' skeleton maker, cut down): the moves go round
    var vid = "none", vidKeys = [];
    if (pairs.length) {
      var bones = function(p, arm){
        var keep = pose; pose = p.slice(); applyPose(); robot.updateMatrixWorld(true);
        var L = function(o){ return bodyGroup.worldToLocal(o.getWorldPosition(new THREE.Vector3())); };
        var S = L(jointGroups[arm ? 4 : 0]), E = L(elbowBalls[arm]), H = L(wristBalls[arm]);
        pose = keep; applyPose();
        return [E.clone().sub(S).normalize().toArray(), H.clone().sub(E).normalize().toArray()];
      };
      var person = function(p){
        var w = []; for (var i = 0; i < 33; i++) w.push({x:0, y:0, z:0, v:1});
        var put = function(i, q){ w[i] = {x: q[0], y: -q[1], z: -q[2], v: 1}; };
        [[11, 13, 15, bones(p, 0), 1], [12, 14, 16, bones(p, 1), -1]].forEach(function(a){
          var sh = [0.18 * a[4], 0.45, 0], u = a[3][0], f = a[3][1];
          var el = [sh[0] + u[0]*0.28, sh[1] + u[1]*0.28, sh[2] + u[2]*0.28];
          put(a[0], sh); put(a[1], el); put(a[2], [el[0] + f[0]*0.25, el[1] + f[1]*0.25, el[2] + f[2]*0.25]);
        });
        put(23, [0.1, 0, 0]); put(24, [-0.1, 0, 0]);
        return w;
      };
      var fr = [];
      for (var i = 0; i < 20; i++) fr.push({t: i / 10, w: person(i < 10 ? pairs[0][0] : pairs[0][1])});
      var made = movesFromFrames(fr, {tol: 4, mirror: false, waist: false, hand: [0, 0], force: [false, false], music: false});
      vid = made ? (made.safe.around + "_" + made.safe.dropped + "_" + made.safe.failed + "_" + made.keys.length) : "null";
      vidKeys = made ? made.keys.map(function(k){ return k.pose; }) : [];
    }
    var vidHits = 0;
    for (var i = 1; i < vidKeys.length; i++) if (denseHit(vidKeys[i - 1], vidKeys[i])) vidHits++;
    vid += "_hits" + vidHits;

    // ---- the robot follows a simulated dummy, live -------------------------
    var holdSaid = false, recSaid = "";
    if (pairs.length && hitPose) {
      window.confirm = function(){ return true; };
      if (typeof setAskUnsaved === "function") setAskUnsaved(false);
      var A = pairs[0][0], B = pairs[0][1];
      var sim = function(p){ for (var j = 0; j < NJ; j++) dummySim[j] = p[j]; };
      document.getElementById("dummySrc").value = "sim"; dummySrcChanged();
      sim(A);
      document.getElementById("dummyFollow").value = "robot"; dummyFollowChanged();
      await wait(900);
      await rawCmd("MOVE QCMARK SAFE~FOLLOW");
      sim(B); await wait(1200);
      await rawCmd("MOVE QCMARK SAFE~HIT");
      sim(hitPose); await wait(900);
      holdSaid = document.getElementById("dummyStat").textContent.indexOf("holds its last safe pose") >= 0;
      await rawCmd("MOVE QCMARK SAFE~REC");
      // ---- and records it: A, then B through the body ----------------------
      document.getElementById("dummyFollow").value = "studio"; dummyFollowChanged();
      sim(A); await wait(500);
      dummyRecToggle(); await wait(300);
      sim(B); await wait(600);
      await dummyRecToggle();
      recSaid = (document.getElementById("dummyStat").textContent.indexOf("go round") >= 0) + "_" + savedName;
      document.getElementById("dummyFollow").value = "off"; dummyFollowChanged();
    }
    SAFE.planner = "straight";
    var straightRefuses = pairs.length ? !!planSafe(pairs[0][0], pairs[0][1], 500).fail : false;
    SAFE.planner = "rrt-connect";
    report("pairs=" + pairs.length + "~tries=" + tries + "~found=" + found + "~clean=" + clean +
           "~ends=" + ends + "~ms=" + ms.join("_") + "~fails=" + fails.join("_").replace(/[^\\w_]/g, "") +
           "~refused=" + refused + "~hitPose=" + !!hitPose + "~keys=" + keysOut +
           "~timeKept=" + timeKept + "~studioClean=" + studioClean +
           "~straightRefuses=" + straightRefuses + "~holdSaid=" + holdSaid + "~rec=" + recSaid +
           "~vid=" + vid + "~A=" + (pairs.length ? pairs[0][0].map(fmtA).join(",") : ""));
  }catch(e){ report("ERR-" + String(e).slice(0,70).replace(/[^\\w ]/g, "")); }
  setTimeout(function(){ report("done"); }, 300);
}, 150); }); });
"""


CHECK = """
function report(s){ rawCmd("MOVE QCMARK SAFE2~" + s); }
window.addEventListener("load", function(){ qcStudioReady().then(function(){ setTimeout(function(){
  try{
    var runs = %s, out = [];
    runs.forEach(function(P){
      var hits = 0;
      for (var i = 1; i < P.length; i++) {
        var n = Math.max(1, Math.ceil(safeGap(P[i - 1], P[i])));
        for (var s = 1; s <= n; s++) if (collisionAt(safeLerp(P[i - 1], P[i], s / n))) { hits++; break; }
      }
      out.push(P.length + "_" + hits);
    });
    report("runs=" + out.join(","));
  }catch(e){ report("ERR-" + String(e).slice(0,70).replace(/[^\\w ]/g, "")); }
  setTimeout(function(){ report("done"); }, 300);
}, 150); }); });
"""


def _poses(wire, start, end):
    """The POSE commands that reached the robot between two driver marks."""
    cmds = [c for _ms, c in wire]
    try:
        a = cmds.index("MOVE QCMARK SAFE~" + start)
        b = cmds.index("MOVE QCMARK SAFE~" + end) if end else len(cmds)
    except ValueError:
        return None
    return [[float(v) for v in c.split()[1:11]] for c in cmds[a + 1:b]
            if c.upper().startswith("POSE ")]


def run(t):
    if not browser.available():
        t.give_up("headless Edge not found - this needs a real browser")
    fake_serial.reset()
    base, _main = F.start_hub()
    browser.page(DRIVER, query="%s/studio/_qcdriver.html?dev=usb%%3A%s"
                 % (base, fake_serial.PORT), seconds=60)
    marks = [m[5:] for m in fake_serial.qc_marks if m.startswith("SAFE~")]
    got = next((m for m in marks if m.startswith("pairs=")), "")
    if not t.ok(got, "the driver planned", marks):
        return
    v = dict(kv.split("=", 1) for kv in got.split("~"))
    n = int(v["pairs"])
    t.ok(n >= 3, "the QC rig has clear poses whose straight move hits the body",
         "found %d in %s tries - nothing to go round: %s" % (n, v["tries"], got))
    t.ok(int(v["found"]) == n, "a way round is found for every one of them", got)
    t.ok(int(v["clean"]) == n,
         "every way round is clear at 1 degree steps (finer than the planner checks)",
         "a leg of the path still goes through the body: %s" % got)
    t.ok(int(v["ends"]) == n, "and starts and ends on the asked poses", got)
    t.ok(v["hitPose"] == "true" and v["refused"] == "true",
         "a pose that itself hits the body is refused, not planned", got)
    t.ok(v["keys"].startswith("n") and "_drop1_" in v["keys"] and "_round1_" in v["keys"],
         "safeKeys drops the hitting key and goes round the other move", got)
    t.ok(v["timeKept"] == "true", "the moves keep at least the time they had (the rhythm of a video)", got)
    t.ok(v["studioClean"] == "true",
         "Studio's own crash check (the eased path the robot drives) finds no hit", got)
    t.ok(v["straightRefuses"] == "true",
         "with the planner set to straight, a hitting move is refused instead", got)

    vid = v.get("vid", "").split("_")
    t.ok(len(vid) == 5 and vid[4] == "hits0" and int(vid[3]) >= 2,
         "moves made from a video never pass through the robot's body (1 degree steps)",
         "around_dropped_failed_keys_hits: %s" % v.get("vid"))
    t.ok(len(vid) == 5 and int(vid[0]) + int(vid[1]) + int(vid[2]) >= 1,
         "a person's move the robot cannot copy straight is sent round or held",
         "the safety pass found nothing to do on a move that hits: %s" % v.get("vid"))

    # ---- live follow, asserted on what reached the robot ---------------------
    t.ok(v["holdSaid"] == "true",
         "following a dummy into a pose that hits, the robot holds and Studio says so", got)
    wire = list(fake_serial.wire)
    follow = _poses(wire, "FOLLOW", "HIT") or []
    held = _poses(wire, "HIT", "REC")
    t.ok(held == [], "and no pose reached the robot while it held",
         "%s poses were sent after the dummy took a hitting pose" % (held and len(held)))
    t.ok(len(follow) >= 2,
         "the dummy's move through the body reached the robot as a way round",
         "%d poses: a straight follow sends one" % len(follow))
    start = [float(x) for x in v["A"].split(",")] if v.get("A") else None
    rec = v.get("rec", "")
    t.ok(rec.startswith("true_dummy_"), "a recording is kept, and the line says it went round", rec)
    saved = []
    name = rec.split("_", 1)[1] if "_" in rec else ""
    yml = _main.SEQUENCES / (name + ".yaml")
    if name and yml.is_file():
        saved = [s["pose"] for s in _main.seq_steps(yml.read_text(encoding="utf-8"))["steps"]]
    t.ok(len(saved) >= 3, "the recording is saved as a move with the way round in it",
         "%s: %d poses" % (yml.name, len(saved)))
    for f in (yml, _main.PROJECTS / (name + ".json")):
        if name:
            f.unlink(missing_ok=True)
    if not (follow and start):
        return
    import json
    browser.page(CHECK % json.dumps([[start] + follow, saved]),
                 query="%s/studio/_qcdriver.html?dev=usb%%3A%s" % (base, fake_serial.PORT),
                 seconds=30)
    m2 = [m[6:] for m in fake_serial.qc_marks if m.startswith("SAFE2~runs=")]
    runs = m2[-1][5:].split(",") if m2 else []
    t.ok(len(runs) == 2 and runs[0].endswith("_0"),
         "every move the robot was sent while following misses its body (1 degree steps)",
         "length_hits: %s" % runs)
    t.ok(len(runs) == 2 and runs[1].endswith("_0"),
         "and so does every move of the saved recording", "length_hits: %s" % runs)
