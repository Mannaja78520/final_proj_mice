"""Studio shows distances in mm between robot points: click, or hold D (A26-44).

User 2026-09-17: *make i can see the distance between the point that i need to
know in robot too like the elbow and hand or elbow -> elbow when use some key to
see hold that key or can click to open*. The pairs are data (distances.json).

Asserted on numbers computed independently from the model's own balls, so a
label that is drawn but wrong (a unit slip, the wrong arm) fails.

User 2026-10-21 (A45-26): *distance ขอระยะจากหัวไหล่ด้วย* - shoulder to elbow and
shoulder to hand on each side, keeping the four first pairs. The shoulder is
the shrug anchor both shoulder servos turn about. The driver finds it another
way (the parent of joint group 0/4) and checks it against the RIG lengths, a
bent and asymmetric pose, WAIST and SHRUG moves, and a rebuilt longer arm.
"""
import json

import browser
import fake_serial
import qc as F

AREA = "studio"
TITLE = "distances between shoulders, elbows and hands show in mm, by click or held D"
SLOW = True

DRIVER = """
const wait = ms => new Promise(r => setTimeout(r, ms));
const W = o => o.getWorldPosition(new THREE.Vector3());
// Endpoints rebuilt WITHOUT distPoint: shoulder = the parent of shoulder joint
// group 0 (left) / 4 (right), the same anchor fkPoints() uses (A45-26).
function want(){
  const sh = [W(jointGroups[0].parent), W(jointGroups[4].parent)];
  const el = elbowBalls.map(W), wr = wristBalls.map(W);
  const d = (a, b) => Math.round(a.distanceTo(b));
  return [d(el[0], wr[0]), d(el[1], wr[1]), d(el[0], el[1]), d(wr[0], wr[1]),
          d(sh[0], el[0]), d(sh[0], wr[0]), d(sh[1], el[1]), d(sh[1], wr[1])].join(",");
}
const tags = () => [].map.call(document.querySelectorAll("#distLayer .distTag"),
                               t => t.textContent.replace(/[^0-9]/g, "")).join(",");
async function setPose(vals){
  Object.keys(vals).forEach(k => { pose[k] = vals[k]; });
  applyPose();
  await wait(400);                       // tick() redraws the labels
}
async function step(){
  try{
    while (typeof distSet !== "function" || !elbowBalls.length) await wait(200);
    const layer = document.getElementById("distLayer");
    qcMark("before=" + document.querySelectorAll("#distLayer .distTag").length);
    document.getElementById("distBtn").click();
    await wait(600);
    qcMark("clicked=" + tags());
    qcMark("want=" + want());
    qcMark("titles=" + [].map.call(document.querySelectorAll("#distLayer .distTag"), t => t.title).join("|"));
    // labels must stay readable: no two of the eight boxes may sit on top of each other
    const rects = [].map.call(document.querySelectorAll("#distLayer .distTag"), t => t.getBoundingClientRect());
    let over = 0;
    rects.forEach((a, i) => rects.slice(i + 1).forEach(b => {
      const x = Math.min(a.right, b.right) - Math.max(a.left, b.left);
      const y = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top);
      if (x > 0 && y > 0 && x * y > 0.5 * Math.min(a.width * a.height, b.width * b.height)) over++;
    }));
    qcMark("overlap=" + over + "@" + innerWidth + "x" + innerHeight);
    qcMark("dims=" + [RIG.dims.upperLenL, RIG.dims.foreLenL, RIG.dims.upperLenR, RIG.dims.foreLenR].join(","));
    // bent left elbow only: asymmetric, and shoulder->hand must shorten
    await setPose({2: 30, 3: 60});
    qcMark("bent=" + tags()); qcMark("bentwant=" + want());
    // WAIST and SHRUG move the whole shoulder: the arm lengths must not change
    await setPose({8: 130, 9: 105});
    qcMark("body=" + tags()); qcMark("bodywant=" + want());
    await setPose({2: 90, 3: 90, 8: 90, 9: 90});
    // a longer left upper arm, rebuilt: shoulder->elbow follows the model
    RIG.dims.upperLenL = RIG.dims.upperLenL + 25;
    buildRobot(); applyPose();
    await wait(400);
    qcMark("rebuilt=" + tags()); qcMark("rebuiltwant=" + want());
    qcMark("pressed=" + document.getElementById("distBtn").getAttribute("aria-pressed"));
    document.getElementById("distBtn").click();
    await wait(300);
    qcMark("off=" + (layer.hidden ? "hidden" : "shown"));

    // hold D: shown while held, gone on release, ignored while typing
    window.dispatchEvent(new KeyboardEvent("keydown", {key: "d"}));
    await wait(300);
    qcMark("held=" + document.querySelectorAll("#distLayer .distTag").length);
    window.dispatchEvent(new KeyboardEvent("keyup", {key: "d"}));
    await wait(300);
    qcMark("released=" + (layer.hidden ? "hidden" : "shown"));
    const box = document.getElementById("projName");
    box.dispatchEvent(new KeyboardEvent("keydown", {key: "d", bubbles: true}));
    await wait(300);
    qcMark("typing=" + (layer.hidden ? "hidden" : "shown"));
    window.dispatchEvent(new KeyboardEvent("keyup", {key: "d"}));
    // an unknown point name and a missing model draw nothing, without throwing
    qcMark("unknown=" + (distPoint("L_knee") === null && distPoint("L_constructor") === null
                         && distPoint("") === null));
    const keep = shrugAnchors.L; shrugAnchors.L = null;
    qcMark("noanchor=" + (distPoint("L_shoulder") === null));
    shrugAnchors.L = keep;
    qcMark("done");
  }catch(e){ qcFail(e); }
}
window.addEventListener("load", function(){ setTimeout(step, 1200); });
"""


def _mark(marks, tag):
    for m in marks:
        if m.startswith(tag + "="):
            return m[len(tag) + 1:]
    return None


def _nums(v):
    return [int(x) for x in v.split(",")] if v else []


def run(t):
    data = json.loads((F.CODE / "nong/main_python_set_nong/web/distances.json")
                      .read_text(encoding="utf-8"))
    pairs = data.get("pairs", [])
    t.eq(len(pairs), 8, "the four first pairs plus four shoulder pairs are data, not code")
    t.eq([(p["from"], p["to"]) for p in pairs[4:]],
         [("L_shoulder", "L_elbow"), ("L_shoulder", "L_hand"),
          ("R_shoulder", "R_elbow"), ("R_shoulder", "R_hand")],
         "user 2026-10-21: shoulder to elbow and shoulder to hand, each side")
    js = (F.CODE / "nong/main_python_set_nong/web/app_parts/distances.js").read_text(encoding="utf-8")
    t.ok("distances.json" in js and "L_elbow" not in js.replace('"L_elbow"', ""),
         "the page reads the pairs from distances.json")

    if not browser.available():
        t.give_up("headless Edge not found — the source half above still ran")
    fake_serial.reset()
    base, _main = F.start_hub()
    browser.page(DRIVER, query="%s/studio/_qcdriver.html?dev=usb%%3A%s"
                 % (base, fake_serial.PORT), seconds=25)
    marks = fake_serial.qc_marks
    t.ok(not any(m.startswith("ERROR") for m in marks), "the page ran without throwing", marks[-4:])
    t.ok("done" in marks, "the driver reached the end", marks[-4:])
    t.eq(_mark(marks, "before"), "0", "nothing is drawn until asked")
    got, want = _mark(marks, "clicked"), _mark(marks, "want")
    t.ok(got and got == want,
         "clicking Distances shows all eight pairs in mm, matching the model",
         "labels %s, model %s" % (got, want))
    w = _nums(want)
    t.ok(len(w) == 8 and all(v > 0 for v in w), "and none of them is zero", want)
    titles = (_mark(marks, "titles") or "").split("|")
    t.ok(titles[4:] == [p["label"] for p in pairs[4:]],
         "each shoulder line is labelled with its side and end", titles)
    ov = _mark(marks, "overlap") or ""
    t.ok(ov.startswith("0@"), "no two of the eight labels cover each other in the starting view", ov)
    dims = _nums(_mark(marks, "dims"))
    t.ok(len(dims) == 4 and len(w) == 8, "the model lengths and eight distances were read", dims)
    if len(dims) != 4 or len(w) != 8:
        return
    up_l, fore_l, up_r, fore_r = dims
    t.ok(abs(w[4] - up_l) <= 1 and abs(w[6] - up_r) <= 1,
         "shoulder to elbow is the upper arm length of that side",
         "L %s vs %s, R %s vs %s" % (w[4], up_l, w[6], up_r))
    t.ok(abs(w[5] - (up_l + fore_l)) <= 1 and abs(w[7] - (up_r + fore_r)) <= 1,
         "a straight arm: shoulder to hand is upper plus forearm", "L %s R %s" % (w[5], w[7]))
    bent, bw = _mark(marks, "bent"), _nums(_mark(marks, "bentwant"))
    t.ok(bent and bent == _mark(marks, "bentwant"), "a bent pose: labels follow the model",
         "labels %s, model %s" % (bent, _mark(marks, "bentwant")))
    t.ok(len(bw) == 8 and abs(up_l - fore_l) - 1 <= bw[5] < w[5] - 5,
         "bending the left elbow shortens left shoulder to hand, inside the arm triangle",
         "straight %s bent %s" % (w[5], bw))
    t.ok(len(bw) == 8 and abs(bw[7] - w[7]) <= 1 and abs(bw[4] - up_l) <= 1,
         "the right arm and the left upper arm do not change", "bent %s" % bw)
    body, bdw = _mark(marks, "body"), _nums(_mark(marks, "bodywant"))
    t.ok(body and body == _mark(marks, "bodywant"), "WAIST and SHRUG moved: labels follow the model",
         "labels %s, model %s" % (body, _mark(marks, "bodywant")))
    t.ok(len(bdw) == 8 and bdw[4:] == bw[4:],
         "WAIST and SHRUG move both shoulders; the shoulder lengths stay",
         "before %s after %s" % (bw[4:], bdw[4:]))
    rb, rbw = _mark(marks, "rebuilt"), _nums(_mark(marks, "rebuiltwant"))
    t.ok(rb and rb == _mark(marks, "rebuiltwant") and len(rbw) == 8 and abs(rbw[4] - (up_l + 25)) <= 1,
         "a longer upper arm in the model: shoulder to elbow follows it", "labels %s, model %s" % (rb, rbw))
    t.eq(_mark(marks, "pressed"), "true", "the button says it is on")
    t.eq(_mark(marks, "off"), "hidden", "a second click hides them")
    t.eq(_mark(marks, "held"), "8", "holding D shows them")
    t.eq(_mark(marks, "released"), "hidden", "and letting go hides them again")
    t.eq(_mark(marks, "typing"), "hidden", "typing a d in a text box does not show them")
    t.eq(_mark(marks, "unknown"), "true", "a point name not in the list draws nothing")
    t.eq(_mark(marks, "noanchor"), "true", "a shoulder not built yet draws nothing instead of throwing")
