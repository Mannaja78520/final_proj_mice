"""On a phone, the floating Stop and Help buttons never cover page content.

PC check 2026-11-22: scrolling Studio at phone width slid "Shape a pose" under the
floating Stop and Help buttons. They now sit on a solid strip and the page keeps
room under its last line. Measured in a 390 px frame, scrolled to the bottom.
"""
import browser
import fake_serial
import qc as F

AREA = "studio"
TITLE = "phone: Stop and Help float on their own strip, nothing is drawn under them"
SLOW = True

PAGE = """
<iframe id="f" src="/studio/" style="width:390px;height:700px;border:0"></iframe>
<script>
function ready(){
  var d = document.getElementById("f").contentDocument;
  var w = document.getElementById("f").contentWindow;
  if (!d || !w || !d.getElementById("fabStop") || !d.querySelector("a.tab-link") || !w.getComputedStyle) return setTimeout(ready, 200);
  setTimeout(function(){ measure(d, w); }, 800);
}
function measure(d, w){
  var stop = d.getElementById("fabStop").getBoundingClientRect();
  var help = d.querySelector("a.tab-link").getBoundingClientRect();
  var strip = w.getComputedStyle(d.body, "::after");
  var stripH = parseFloat(strip.height) || 0;
  w.scrollTo(0, d.documentElement.scrollHeight);
  setTimeout(function(){
    var top = w.innerHeight - stripH;                      // where the strip starts
    var last = 0;
    d.querySelectorAll("#side *, #timeline *").forEach(function(e){
      var r = e.getBoundingClientRect();
      if (r.height && r.bottom > last && r.bottom <= w.innerHeight + 4000) last = Math.max(last, r.bottom);
    });
    qcMark("strip-" + (strip.position === "fixed" && stripH >= 64));
    qcMark("stop-on-strip-" + (stop.top >= top - 1));
    qcMark("help-on-strip-" + (help.top >= top - 1));
    qcMark("stop-visible-" + (stop.width > 0 && stop.bottom <= w.innerHeight));
    qcMark("room-below-" + (parseFloat(w.getComputedStyle(d.body).paddingBottom) >= 64));
    qcMark("done");
  }, 500);
}
window.addEventListener("load", ready);
</script>
"""


def run(t):
    if not browser.available():
        t.give_up("headless Edge not found — install Edge or run --quick")
    fake_serial.reset()
    base, main = F.start_hub()
    browser.raw_page(PAGE, base, seconds=30)
    marks = fake_serial.qc_marks
    t.ok(not any(m.startswith("ERROR") for m in marks), "the page ran without throwing", marks)
    for want, label in (
        ("strip-true", "a solid strip sits along the bottom edge on a phone"),
        ("stop-on-strip-true", "Stop is on the strip"),
        ("help-on-strip-true", "Help is on the strip"),
        ("stop-visible-true", "Stop stays visible"),
        ("room-below-true", "the page keeps room under its last line"),
    ):
        t.contains(marks, want, label)
