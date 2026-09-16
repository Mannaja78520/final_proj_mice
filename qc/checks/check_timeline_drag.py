"""The timeline panel in Nong Studio can be dragged taller or shorter.

Asked 2026-09-16: *nong studio now it have the drag of timeline below but
cannot drag to make it smaller or bigger ... make the below can adjust too and
have the scroller to scroll like the right side*. #timeDrag had CSS and no
code, so the handle looked draggable and did nothing.

Driven in a real browser, measuring the panel's actual height:
  * dragging the handle up makes the timeline taller, down makes it shorter;
  * the arrow keys do the same (a touchpad that misses the handle still works);
  * the height is remembered; a double-click puts it back to its own size;
  * the panel scrolls inside itself when its content is taller.
"""
import browser
import fake_serial
import qc as F

AREA = "studio"
TITLE = "the timeline panel drags taller or shorter and scrolls inside"
SLOW = True

DRIVER = """
function report(s){ rawCmd("MOVE QCMARK TDRAG~" + s); }
window.addEventListener("load", function(){ setTimeout(async function(){
  try{
    localStorage.removeItem("nong_timeh");
    var tl = document.getElementById("timeline"), h = document.getElementById("timeDrag");
    // read after any height animation has finished, not mid-transition
    var settle = function(){ return new Promise(function(r){ setTimeout(r, 600); }); };
    function H(){ return Math.round(tl.getBoundingClientRect().height); }
    // start small and known: the headless window is ~440px tall, so the 80%%
    // cap is ~350px and a panel starting at its natural 557px proves nothing
    tl.style.height = "150px";
    await settle();
    var before = H();
    function drag(dy){
      var y = h.getBoundingClientRect().top + 5;
      h.dispatchEvent(new PointerEvent("pointerdown", {clientY: y, pointerId: 7, bubbles: true}));
      h.dispatchEvent(new PointerEvent("pointermove", {clientY: y + dy, pointerId: 7, bubbles: true}));
      h.dispatchEvent(new PointerEvent("pointerup", {clientY: y + dy, pointerId: 7, bubbles: true}));
    }
    drag(-120);
    await settle();
    var taller = H();
    drag(80);
    await settle();
    var shorter = H();
    h.dispatchEvent(new KeyboardEvent("keydown", {key: "ArrowUp", bubbles: true}));
    await settle();
    var keyUp = H();
    var saved = localStorage.getItem("nong_timeh");
    var scroll = getComputedStyle(tl).overflowY;
    h.dispatchEvent(new MouseEvent("dblclick", {bubbles: true}));
    var reset = tl.style.height === "" && !localStorage.getItem("nong_timeh");
    report("before=" + before + "~taller=" + taller + "~shorter=" + shorter +
           "~keyUp=" + keyUp + "~saved=" + saved + "~scroll=" + scroll + "~reset=" + reset);
  }catch(e){ report("ERR-" + String(e).slice(0,60)); }
  setTimeout(function(){ report("done"); }, 300);
}, 1500); });
"""


def run(t):
    if not browser.available():
        t.give_up("headless Edge not found - this needs a real browser")
    fake_serial.reset()
    base, _main = F.start_hub()
    browser.page(DRIVER, query="%s/studio/_qcdriver.html?dev=usb%%3A%s"
                 % (base, fake_serial.PORT), seconds=20)
    marks = [m[6:] for m in fake_serial.qc_marks if m.startswith("TDRAG~")]
    got = next((m for m in marks if m.startswith("before=")), "")
    if not t.ok(got, "the driver measured the timeline", marks):
        return
    v = dict(kv.split("=", 1) for kv in got.split("~"))
    before, taller, shorter, key_up = (int(v[k]) for k in ("before", "taller", "shorter", "keyUp"))
    t.ok(taller >= before + 100, "dragging the handle up makes the timeline taller",
         "before %d, after dragging 120px up %d" % (before, taller))
    t.ok(shorter <= taller - 60, "dragging it down makes it shorter",
         "taller %d, after dragging 80px down %d" % (taller, shorter))
    t.ok(key_up > shorter, "the up arrow key makes it taller too", v)
    t.ok(v.get("saved") not in (None, "", "null"), "the height is remembered", v)
    t.ok(v.get("scroll") in ("auto", "scroll"), "the panel scrolls inside itself", v)
    t.ok(v.get("reset") == "true", "a double-click puts it back to its own size", v)
