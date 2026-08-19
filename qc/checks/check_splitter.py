"""A control you cannot hit is a control you do not have.

Reported from a real laptop, 2026-08-18: the splitter between the 3D view and
Nong Studio's side panel "is too short and I cannot drag". It was 6px wide,
pointer-only, with no other way to resize the panel — so someone whose touchpad
cannot land on 6px could not widen the panel at all.

Two properties, measured in a real browser rather than read off the CSS:

  * the GRAB area is big enough to hit, while the LINE stays thin. Those are
    different things and treating them as one is what caused this;
  * and there is a way to resize that is not dragging. That is the part that
    matters: a bigger target helps, but a keyboard path means the panel can
    always be recovered, including when it has been dragged to an extreme.
"""
import browser
import fake_serial
import qc as F

AREA = "responsive"
TITLE = "the panel splitter can be hit, and moved without a mouse"
SLOW = True

# Pointer targets below this are the reason the report happened. The visible
# line may stay thin — this is about the part you can grab.
MIN_TARGET = 12

DRIVER = """
<style>html,body{margin:0}#f{width:1440px;height:900px;border:0}</style>
<iframe id="f" src="/studio/"></iframe>
<script>
function say(k, v){ return qcMark("SP " + k + "=" + String(v).replace(/[\\s|]+/g, "~")); }
window.addEventListener("load", async function(){
  try{
    var d = document.getElementById('f').contentDocument;
    var w = d.defaultView;
    await qcWaitFor(function(){ return d.getElementById('sideDrag'); }, 15000);
    var h = d.getElementById('sideDrag'), side = d.getElementById('side');

    await say("grab", Math.round(h.getBoundingClientRect().width));
    await say("role", h.getAttribute('role') || 'none');
    await say("tabindex", h.getAttribute('tabindex') === null ? 'none' : 'yes');
    await say("touchaction", w.getComputedStyle(h).touchAction);

    // Can it be moved with the keyboard alone? Drive it exactly as a person
    // would: focus, then press a key.
    var before = parseInt(side.style.width) || side.getBoundingClientRect().width;
    h.focus();
    await say("focused", d.activeElement === h ? "yes" : "no");
    h.dispatchEvent(new w.KeyboardEvent('keydown',
      {key:'ArrowLeft', bubbles:true, cancelable:true}));
    await qcWaitFor(function(){
      return (parseInt(side.style.width) || 0) !== before; }, 2000);
    var after = parseInt(side.style.width) || side.getBoundingClientRect().width;
    await say("keymoved", (after - before));

    // And a way back: a panel dragged to an extreme must be recoverable.
    h.dispatchEvent(new w.KeyboardEvent('keydown',
      {key:'Home', bubbles:true, cancelable:true}));
    await qcWaitFor(function(){ return (parseInt(side.style.width)||0) !== after; }, 2000);
    await say("home", parseInt(side.style.width) || 0);
    qcMark("done");
  }catch(e){ qcFail(e); }
});
</script>
"""


def run(t):
    if not browser.available():
        t.give_up("headless Edge not found — install Edge or run --quick")
    fake_serial.reset()
    base, main = F.start_hub()
    browser.raw_page(DRIVER, base, seconds=40)

    got = {}
    for m in fake_serial.qc_marks:
        if m.startswith("SP "):
            k, _, v = m[3:].partition("=")
            got[k] = v.replace("~", " ")
    if not t.ok(got, "the splitter reported back", fake_serial.qc_marks[-4:]):
        return

    # ---- big enough to hit -------------------------------------------
    grab = int(got.get("grab", "0") or 0)
    t.ok(grab >= MIN_TARGET,
         "the splitter is big enough to grab (%dpx)" % grab,
         "it was 6px and a laptop touchpad could not land on it; the visible "
         "line may stay thin, the TARGET may not")

    # ---- a drag must not scroll the page instead ---------------------
    t.contains(got.get("touchaction", ""), "none",
               "a drag on it moves the splitter, not the page")

    # ---- and it works without a mouse at all -------------------------
    t.eq(got.get("role"), "separator", "it says what it is")
    t.eq(got.get("tabindex"), "yes", "a keyboard can reach it")
    t.eq(got.get("focused"), "yes", "and it really takes focus")
    moved = int(got.get("keymoved", "0") or 0)
    t.ok(moved != 0,
         "an arrow key resizes the panel",
         "without this, someone who cannot hit the handle cannot resize at all")
    t.ok(int(got.get("home", "0") or 0) == 320,
         "and Home puts it back to the default",
         "a panel dragged to an extreme has to be recoverable")
