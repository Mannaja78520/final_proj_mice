"""The time bar is always there, always findable, and shows the real timing.

Asked 2026-09-10: *make nong studio have the time bar like when start everytime
sometime i need to drag it to some position and then move from that position or
move from stop position*. Asked which Stop was at fault, the user answered **the
bar disappears from the screen**.

Nothing was broken about the SEEK. `#scrub` existed, `scrubTo()` already parked
the clock and moved the arm, and `playT` already survived a pause — so Play
already carried on from where it stopped. The bar simply could not be FOUND:
`#scrub` was 180px wide with no label, inside `.tl-head`, a
`display:flex;flex-wrap:wrap` row carrying fourteen buttons, three inputs and a
select. Wherever that row wrapped, the slider went — usually buried mid-field on
the second or third line. A control nobody can find is a control that is not
there, and the user reported it as missing.

So the assertions are about being FINDABLE, not about seeking:

* `#scrub` is not a descendant of `.tl-head` — it has a row of its own, which is
  the only thing that stops the wrap from moving it;
* it is wide (most of the bar's own width) and tall enough to hit, at a laptop
  width AND at 360px, where the old rule `#scrub{width:100%}` fought the same
  wrapping row;
* it is still all of that AFTER play -> pause -> Back to start, which is the
  exact sequence the user was in when they said the bar was gone;
* the blocks drawn on it match the show's real timing, so the bar is a picture of
  the show and not decoration;
* and `renderTimeBar()` does NOT run per frame. `renderTimeline()` rebuilds every
  chip with `innerHTML = ""`; hanging a playhead off that would rebuild the whole
  strip sixty times a second, which is how a preview starts dropping frames on
  the laptop this is used on.

Geometry is measured in a real browser because that is the only place a wrapped
flex row exists. Everything else — that a seek reaches the robot — is already
held by check_key_clock and check_one_player, so it is not repeated here.
"""
import json

import browser
import fake_serial
import qc as F

AREA = "studio"
TITLE = "the time bar has its own row and cannot go missing"
SLOW = True

# Deliberately uneven, so a bar that draws equal blocks per keyframe (the chip
# strip's shape) cannot pass by accident.
T1, H1, T2, H2, T3 = 2000, 500, 800, 0, 3000
TOTAL = T1 + H1 + T2 + H2 + T3

DRIVER = """
var W = 360;                       // the phone width the old rule fought
function geom(doc, win, sel){
  var el = doc.querySelector(sel);
  if (!el) return null;
  var r = el.getBoundingClientRect();
  var st = win.getComputedStyle(el);
  return {w: Math.round(r.width), h: Math.round(r.height),
          hidden: st.display === "none" || st.visibility === "hidden" ||
                  +st.opacity === 0};
}
function report(tag, doc, win){
  // THREE elements, not one. #scrub carries its own height, so it still measured
  // 28px tall with .tb-track collapsed to zero — the slider overflowing an
  // invisible row, which is the very complaint. The visible bar is the track and
  // the block layer, so both are measured too.
  var s = geom(doc, win, "#scrub"), b = geom(doc, win, "#timebar");
  var tr = geom(doc, win, ".tb-track"), bl = geom(doc, win, "#tbBlocks");
  var inHead = !!(doc.querySelector(".tl-head #scrub"));
  qcMark(tag + "=" + JSON.stringify({s: s, b: b, tr: tr, bl: bl, inHead: inHead}));
}

function step(){
  try{
    if (typeof addKey !== "function" || !document.getElementById("scrub"))
      return setTimeout(step, 200);
    if (!haveUsb()) return setTimeout(step, 300);
    document.getElementById("loopChk").checked = false;

    keys = [];
    pose = pose.map(function(){ return 60; });  addKey();
    pose = pose.map(function(){ return 120; }); addKey();
    pose = pose.map(function(){ return 40; });  addKey();
    pose = pose.map(function(){ return 100; }); addKey();
    keys[1].t = %d; keys[1].hold = %d;
    keys[2].t = %d; keys[2].hold = %d;
    keys[3].t = %d; keys[3].hold = 0;
    bumpKeys(); renderTimeline();

    // ---- A: findable on a laptop, and NOT inside the wrapping button row
    report("A", document, window);

    // ---- B: the blocks are the real timing, read straight off the page
    var blocks = [].map.call(document.querySelectorAll("#tbBlocks .tb-blk"),
      function(el){
        return {left: el.style.left, width: el.style.width,
                hold: el.classList.contains("hold")};
      });
    qcMark("B=" + JSON.stringify(blocks));
    qcMark("Btotal=" + Math.round(totalMs()));

    // ---- C: the bar is not rebuilt per frame. Count real calls across a
    // playthrough; the rAF loop must only move the range value.
    var calls = 0, real = renderTimeBar;
    window.renderTimeBar = function(){ calls++; return real.apply(null, arguments); };
    togglePlay();
    setTimeout(function(){
      if (playing) togglePlay();                 // pause part-way, keep the clock
      qcMark("Ccalls=" + calls);
      window.renderTimeBar = real;
      qcMark("Cpaused=" + Math.round(playT));

      // ---- D: play -> pause -> Back to start. THE USER'S SEQUENCE: after
      // stopping, the bar must still be there and the clock must read zero.
      rewind();
      report("D", document, window);
      qcMark("Dclock=" + Math.round(playT));

      // ---- E: 360px. Media queries inside an iframe answer to the IFRAME's
      // width, so this is a real phone layout without resizing the browser.
      var f = document.createElement("iframe");
      f.width = W; f.height = 780; f.style.border = "0"; f.src = "/studio/";
      document.body.appendChild(f);
      f.onload = function(){
        setTimeout(function(){
          try{
            report("E", f.contentDocument, f.contentWindow);
          }catch(e){ qcMark("E=null"); }
          qcMark("done");
        }, 1800);
      };
    }, 2200);
  }catch(e){ qcFail(e); }
}
window.addEventListener("load", function(){ setTimeout(step, 1200); });
""" % (T1, H1, T2, H2, T3)


def _mark(marks, tag):
    for m in marks:
        if m.startswith(tag + "="):
            return m[len(tag) + 1:]
    return None


def _pct(s):
    """'23.5%' -> 23.5. The blocks are positioned in percent so the bar keeps
    its proportions at any width — a pixel would only be true at one size."""
    return float(str(s).strip().rstrip("%"))


def run(t):
    if not browser.available():
        t.give_up("headless Edge not found — install Edge or run --quick")
    fake_serial.reset()
    base, main = F.start_hub()
    browser.page(DRIVER, query="%s/studio/_qcdriver.html?dev=usb%%3A%s"
                 % (base, fake_serial.PORT), seconds=30)

    marks = fake_serial.qc_marks
    t.ok(not any(m.startswith("ERROR") for m in marks),
         "the page ran without throwing", marks)

    # ---- findable, on a laptop and after stopping -------------------------
    for tag, when in (("A", "on a laptop"), ("D", "after play, pause and Back to start")):
        raw = _mark(marks, tag)
        if not t.ok(raw, "the bar was measured %s" % when, marks[-6:]):
            return
        g = json.loads(raw)
        s, b, tr, bl = g.get("s"), g.get("b"), g.get("tr"), g.get("bl")
        if not t.ok(s and b and tr and bl,
                    "the time bar, its track and its slider all exist %s" % when, g):
            return
        t.ok(not g["inHead"],
             "#scrub is NOT inside the wrapping .tl-head button row (%s)" % when,
             "back inside .tl-head: the wrap can bury it again")
        t.ok(not s["hidden"], "the slider is visible %s" % when, s)
        t.ok(not tr["hidden"] and not bl["hidden"],
             "and so is the bar it sits on %s" % when, tr)
        t.ok(s["w"] >= b["w"] * 0.6,
             "it fills most of the bar %s (%dpx of %dpx)" % (when, s["w"], b["w"]),
             "180px in a field of fourteen buttons is what the user could not find")
        t.ok(s["h"] >= 20,
             "and it is tall enough to grab %s (%dpx)" % (when, s["h"]), s)
        # The VISIBLE bar, measured separately: a collapsed track leaves the
        # slider its own height while the row a person looks for is gone.
        t.ok(tr["h"] >= 20,
             "the bar itself has real height %s (%dpx)" % (when, tr["h"]),
             "a zero-height row is the bar disappearing, whatever the slider says")
        t.ok(bl["h"] >= 20 and bl["w"] >= b["w"] * 0.6,
             "and the blocks fill it %s (%dx%d)" % (when, bl["w"], bl["h"]), bl)
        t.ok(abs(s["h"] - tr["h"]) <= 4,
             "the slider matches the bar's height %s (%d vs %d)"
             % (when, s["h"], tr["h"]),
             "the slider is overflowing its row instead of filling it")

    # The complaint was that stopping lost the position. Back to start is the
    # one control that is SUPPOSED to lose it, so it must really return to zero.
    t.eq(int(_mark(marks, "Dclock") or -1), 0, "Back to start returns the clock to 0")

    # ---- the blocks are the show's real timing ---------------------------
    raw = _mark(marks, "B")
    if not t.ok(raw, "the blocks were measured", marks[-6:]):
        return
    blocks = json.loads(raw)
    total = int(_mark(marks, "Btotal") or 0)
    t.eq(total, TOTAL, "the show is as long as the keyframes say")
    moves = [b for b in blocks if not b["hold"]]
    t.eq(len(moves), 3, "one block per move that plays (keyframe 0 has no move)")
    if len(moves) == 3 and total:
        # keyStartMs(1) is 0 + hold of keyframe 0 = 0 here, so move 1 starts at 0
        want = [(0, T1), (T1 + H1, T2), (T1 + H1 + T2 + H2, T3)]
        for i, (start, dur) in enumerate(want):
            got_l, got_w = _pct(moves[i]["left"]), _pct(moves[i]["width"])
            t.ok(abs(got_l - start / total * 100) < 1,
                 "move %d starts at its real time (%.1f%% for %dms)"
                 % (i + 1, got_l, start),
                 "a bar that ignores timing is the chip strip again")
            t.ok(abs(got_w - dur / total * 100) < 1,
                 "and is as wide as it is long (%.1f%% for %dms)" % (got_w, dur))
        t.ok(_pct(moves[0]["width"]) > _pct(moves[1]["width"]) * 2,
             "a 2s move really is wider than a 0.8s one",
             "equal blocks mean the widths are not coming from the timing")
    holds = [b for b in blocks if b["hold"]]
    t.ok(len(holds) >= 1, "a hold is drawn as its own band", blocks)

    # ---- the bar is not rebuilt per frame --------------------------------
    calls = int(_mark(marks, "Ccalls") or -1)
    t.ok(0 <= calls <= 4,
         "renderTimeBar ran %d times across a 2s playthrough, not per frame" % calls,
         "renderTimeline() rebuilds every chip with innerHTML='' — driving the "
         "playhead through it would do that sixty times a second")
    t.ok(int(_mark(marks, "Cpaused") or 0) > 0,
         "and the clock really advanced while it was playing")

    # ---- 360px: the phone the studio is opened on at the robot -----------
    raw = _mark(marks, "E")
    if raw and raw != "null":
        g = json.loads(raw)
        s, b, tr = g.get("s"), g.get("b"), g.get("tr")
        if t.ok(s and b and tr, "the bar was measured at 360px", g):
            t.ok(not s["hidden"], "it is visible at 360px too", s)
            t.ok(not g["inHead"], "and still out of the .tl-head row at 360px")
            t.ok(s["w"] >= b["w"] * 0.6,
                 "it still fills the bar at 360px (%dpx of %dpx)" % (s["w"], b["w"]))
            t.ok(s["h"] >= 20,
                 "and is still grabbable at 360px (%dpx)" % s["h"], s)
            t.ok(tr["h"] >= 20,
                 "the bar itself is still there at 360px (%dpx)" % tr["h"], tr)
    else:
        t.ok(False, "the 360px measurement arrived", marks[-6:])
