"""Studio's side cards fold to their title in a tab that holds more than one.

Asked 2026-09-24 (A31-24): *in nong studio all card in the top right which tab
is more than 1 card or hard to scroll down to setup can hide it like the POSE
tab*. Setup held seven open cards, so the one you wanted meant a long scroll.
Holds:
  * every Setup card starts folded: a list of titles, bodies hidden;
  * Robot link (first Robot card) starts open, Zero position folded;
  * the Pose tab, whose extra cards are already <details>, gets no fold;
  * clicking a title opens it, and the choice is remembered in the browser;
  * clicking the technical-details box inside Robot link's title does not fold.
"""
import re
import browser
import fake_serial
import qc as F

AREA = "studio"
TITLE = "side cards fold to their title in a tab with more than one"
SLOW = True

DRIVER = """
function report(s){ rawCmd("MOVE QCMARK FOLD~" + s); }
function shown(el){ return !!el && getComputedStyle(el).display !== "none"; }
window.addEventListener("load", function(){ qcStudioReady().then(function(){ setTimeout(function(){
  try{
    try { localStorage.removeItem("nong_folded"); } catch(e){}
    var setup = [].slice.call(document.querySelectorAll('#side div.card[data-stab=setup]'));
    var folded = setup.filter(function(c){ return c.classList.contains("folded"); }).length;
    report("setup=" + setup.length + "~folded=" + folded);
    var saving = document.getElementById("askUnsavedChk").closest(".card");
    report("savingBody=" + shown(document.getElementById("askUnsavedChk").closest("label")));
    saving.querySelector("h2").click();
    report("opened=" + !saving.classList.contains("folded")
      + "~body=" + shown(document.getElementById("askUnsavedChk").closest("label"))
      + "~kept=" + ((localStorage.getItem("nong_folded") || "").indexOf("setup:Saving\\":false") >= 0));
    var robot = [].slice.call(document.querySelectorAll('#side div.card[data-stab=robot]'));
    report("robot=" + robot.map(function(c){ return c.classList.contains("folded") ? "F" : "O"; }).join(""));
    // the box itself: a click on its label reaches h2 twice and would hide a bug
    document.getElementById("advOn").click();
    report("advClick~robotOpen=" + !robot[0].classList.contains("folded"));
    document.getElementById("advOn").click();
    report("pose=" + document.querySelectorAll('#side [data-stab=pose].foldable').length);
  }catch(e){ report("ERR-" + String(e).slice(0,60)); }
  setTimeout(function(){ report("done"); }, 300);
}, 150); }); });
"""


def run(t):
    if not browser.available():
        t.give_up("headless Edge not found - this needs a real browser")
    fake_serial.reset()
    base, _main = F.start_hub()
    browser.page(DRIVER, query="%s/studio/_qcdriver.html?dev=usb%%3A%s"
                 % (base, fake_serial.PORT), seconds=30)
    marks = [m[5:] for m in fake_serial.qc_marks if m.startswith("FOLD~")]
    bad = [m for m in marks if m.startswith("ERR-")]
    if not t.ok(marks and not bad, "the driver ran without throwing", marks[-3:]):
        return
    setup = next((m for m in marks if m.startswith("setup=")), "")
    n = setup.split("~")[0][6:]
    t.ok(n.isdigit() and int(n) >= 2 and setup.endswith("~folded=" + n),
         "every Setup card starts folded to its title", setup)
    t.ok("savingBody=false" in marks, "a folded card hides its body", marks)
    t.ok("opened=true~body=true~kept=true" in marks,
         "clicking the title opens it, and the browser remembers it", marks)
    # one open card first, then every other Robot card (Zero position, Dummy...) folded
    t.ok(any(re.fullmatch(r"robot=OF+", m) for m in marks),
         "Robot link starts open, Zero position folded", marks)
    t.ok("advClick~robotOpen=true" in marks,
         "the technical-details box in Robot link's title does not fold the card", marks)
    t.ok("pose=0" in marks, "the Pose tab keeps its own <details>, no second fold", marks)
