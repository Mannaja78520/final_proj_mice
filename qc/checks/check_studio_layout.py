"""Studio's screen gives the 3D view its room, and wears the shared head.

Asked 2026-10-14 (A41): *the web pages are buggy and each goes its own way*.
The audit that day opened Studio at 1280x800 and measured:

* the 3D view only ~200 px tall: the timeline's button row wrapped to four
  lines (two name boxes, two Saves, the saved-file list, a paragraph of hint)
  and the timeline grew to fit them, ~500 px of an 800 px window;
* the side tab "Sequence" cut to "Sequen" - equal-width tabs in a 320 px panel;
* on a phone the view buttons (Top/Left/Front...) covered half the 3D view;
* the empty time bar's note lost its first letter under the playhead;
* its own head: "🏠 Hub" as a button, the technical switch inside the Robot
  card, no status line - every other hub page now has `header.topbar`.

Stage 3 (A41-4) moved the name box and Save to the head only, the saved-file
list and the chain into the Sequence tab, capped the timeline until its handle
is dragged, folded the view buttons behind one "Views" button on a phone, and
mounted Mice.TopBar. Each of those is measured here, in a real browser,
because a wrapped flex row only exists in one. The widths are iframes: media
queries answer to the iframe's width, so the phone layout is real.
"""
import json

import browser
import fake_serial
import qc as F

AREA = "studio"
TITLE = "Studio's 3D view has room; one head, one name, one Save"
SLOW = True

DRIVER = """
function frame(w, h, then){
  var f = document.createElement("iframe");
  f.width = w; f.height = h; f.style.border = "0"; f.src = "/studio/";
  document.body.appendChild(f);
  f.onload = function(){ setTimeout(function(){
    try { then(f.contentDocument, f.contentWindow); } catch(e){ qcFail(e); }
  }, 2200); };
}
function box(doc, sel){
  var el = doc.querySelector(sel);
  if (!el) return null;
  var r = el.getBoundingClientRect();
  return {w: Math.round(r.width), h: Math.round(r.height)};
}
function laptop(doc, win){
  var head = doc.querySelector("header.topbar");
  var first = head && head.firstElementChild;
  var cut = [].filter.call(doc.querySelectorAll("#sideTabs .tab"), function(t){
    return t.scrollWidth > t.clientWidth + 1; }).map(function(t){ return t.textContent; });
  var note = doc.querySelector(".tb-blk.note");
  qcMark("A=" + JSON.stringify({
    view: box(doc, "#viewport"), tl: box(doc, "#timeline"),
    home: !!(first && first.classList.contains("topbar-home")),
    adv: !!(head && head.querySelector("#advOn")),
    advs: doc.querySelectorAll("#advOn").length,
    stat: !!(head && head.querySelector("#stat")),
    names: doc.querySelectorAll("#projName,#seqName").length,
    saves: doc.querySelectorAll('[onclick="saveAll()"]').length,
    cut: cut,
    notePad: note ? parseFloat(win.getComputedStyle(note).paddingLeft) : -1
  }));
  // the head's status line follows the work: two new poses are not saved
  // `pose` is a top-level let: in the page's scope, not on its window
  win.eval("[40, 140].forEach(function(v){ pose = pose.map(function(){ return v; }); addKey(); })");
  setTimeout(function(){
    qcMark("Astat=" + doc.getElementById("stat").textContent);
    frame(390, 844, phone);
  }, 1600);
}
function phone(doc, win){
  var vp = box(doc, "#viewport");
  qcMark("B=" + JSON.stringify({view: vp, cube: box(doc, "#viewCube")}));
  doc.getElementById("viewCubeBtn").click();
  qcMark("Bopen=" + JSON.stringify(box(doc, "#viewCube")));
  win.setView("top");
  qcMark("Bpicked=" + JSON.stringify(box(doc, "#viewCube")));
  qcMark("done");
}
window.addEventListener("load", function(){ setTimeout(function(){ frame(1280, 800, laptop); }, 800); });
"""


def _mark(marks, tag):
    for m in marks:
        if m.startswith(tag + "="):
            return m[len(tag) + 1:]
    return None


def run(t):
    if not browser.available():
        t.give_up("headless Edge not found — install Edge or run --quick")
    fake_serial.reset()
    base, main = F.start_hub()
    browser.page(DRIVER, query="%s/studio/_qcdriver.html?dev=usb%%3A%s"
                 % (base, fake_serial.PORT), seconds=40)
    marks = fake_serial.qc_marks
    t.ok(not any(m.startswith("ERROR") for m in marks),
         "the page ran without throwing", marks[-6:])

    raw = _mark(marks, "A")
    if not t.ok(raw, "Studio was measured at 1280x800", marks[-6:]):
        return
    a = json.loads(raw)
    vh = (a.get("view") or {}).get("h", 0)
    t.ok(vh >= 340, "the 3D view is %dpx tall at 1280x800" % vh,
         "it was ~200px: the timeline grew to fit a four-line button row")
    t.ok(a["home"], "the head starts with the shared way back to the hub",
         "header.topbar's first child is not .topbar-home")
    t.ok(a["adv"] and a["advs"] == 1,
         "the technical switch is in the head, once", a)
    t.ok(a["stat"], "the head has the shared status line", a)
    t.ok(a["names"] == 1, "one name box on the page (%d)" % a["names"],
         "the timeline's second name box is back")
    t.ok(a["saves"] == 1, "one Save on the page (%d)" % a["saves"],
         "a second Save is back")
    t.ok(not a["cut"], "no side tab is cut short", a["cut"])
    t.ok(a["notePad"] >= 8,
         "the empty time bar's note starts clear of the playhead (%spx)" % a["notePad"],
         "its first letter sat under the 8px playhead")
    t.ok((_mark(marks, "Astat") or "").startswith("not saved"),
         "the head says the new poses are not saved",
         _mark(marks, "Astat"))

    raw = _mark(marks, "B")
    if not t.ok(raw, "Studio was measured on a phone", marks[-6:]):
        return
    b = json.loads(raw)
    view, cube = b.get("view") or {}, b.get("cube") or {}
    area = view.get("w", 0) * view.get("h", 0)
    share = (cube.get("w", 0) * cube.get("h", 0)) / area if area else 1
    t.ok(share < 0.12,
         "on a phone the view buttons cover %d%% of the 3D view" % (share * 100),
         "they covered about half of it before they folded")
    opened = json.loads(_mark(marks, "Bopen") or "{}")
    t.ok(opened.get("h", 0) > cube.get("h", 0) * 2,
         "the Views button opens them", opened)
    picked = json.loads(_mark(marks, "Bpicked") or "{}")
    t.ok(picked.get("h", 999) <= cube.get("h", 0) + 2,
         "and picking a view folds them again", picked)
