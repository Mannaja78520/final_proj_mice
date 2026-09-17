"""Studio shows distances in mm between robot points: click, or hold D (A26-44).

User 2026-09-17: *make i can see the distance between the point that i need to
know in robot too like the elbow and hand or elbow -> elbow when use some key to
see hold that key or can click to open*. The pairs are data (distances.json).

Asserted on numbers computed independently from the model's own balls, so a
label that is drawn but wrong (a unit slip, the wrong arm) fails.
"""
import json

import browser
import fake_serial
import qc as F

AREA = "studio"
TITLE = "distances between elbows and hands show in mm, by click or held D"
SLOW = True

DRIVER = """
const wait = ms => new Promise(r => setTimeout(r, ms));
async function step(){
  try{
    while (typeof distSet !== "function" || !elbowBalls.length) await wait(200);
    const layer = document.getElementById("distLayer");
    qcMark("before=" + document.querySelectorAll("#distLayer .distTag").length);
    document.getElementById("distBtn").click();
    await wait(600);
    const tags = [].map.call(document.querySelectorAll("#distLayer .distTag"),
                             t => t.textContent.replace(/[^0-9]/g, ""));
    qcMark("clicked=" + tags.join(","));
    const d = (a, b) => Math.round(a.getWorldPosition(new THREE.Vector3())
                         .distanceTo(b.getWorldPosition(new THREE.Vector3())));
    qcMark("want=" + [d(elbowBalls[0], wristBalls[0]), d(elbowBalls[1], wristBalls[1]),
                      d(elbowBalls[0], elbowBalls[1]), d(wristBalls[0], wristBalls[1])].join(","));
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


def run(t):
    data = json.loads((F.CODE / "nong/main_python_set_nong/web/distances.json")
                      .read_text(encoding="utf-8"))
    t.eq(len(data.get("pairs", [])), 4, "the four pairs the user named are data, not code")
    js = (F.CODE / "nong/main_python_set_nong/web/app_parts/distances.js").read_text(encoding="utf-8")
    t.ok("distances.json" in js and "L_elbow" not in js.replace('"L_elbow"', ""),
         "the page reads the pairs from distances.json")

    if not browser.available():
        t.give_up("headless Edge not found — the source half above still ran")
    fake_serial.reset()
    base, _main = F.start_hub()
    browser.page(DRIVER, query="%s/studio/_qcdriver.html?dev=usb%%3A%s"
                 % (base, fake_serial.PORT), seconds=20)
    marks = fake_serial.qc_marks
    t.ok(not any(m.startswith("ERROR") for m in marks), "the page ran without throwing", marks[-4:])
    t.eq(_mark(marks, "before"), "0", "nothing is drawn until asked")
    got, want = _mark(marks, "clicked"), _mark(marks, "want")
    t.ok(got and got == want,
         "clicking Distances shows elbow-hand, elbow-elbow and hand-hand in mm, matching the model",
         "labels %s, model %s" % (got, want))
    t.ok(want and all(int(v) > 0 for v in want.split(",")), "and none of them is zero", want)
    t.eq(_mark(marks, "pressed"), "true", "the button says it is on")
    t.eq(_mark(marks, "off"), "hidden", "a second click hides them")
    t.eq(_mark(marks, "held"), "4", "holding D shows them")
    t.eq(_mark(marks, "released"), "hidden", "and letting go hides them again")
    t.eq(_mark(marks, "typing"), "hidden", "typing a d in a text box does not show them")
