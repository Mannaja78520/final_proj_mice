"""Studio number boxes: a blank or out-of-range entry never leaves a wrong number on screen.

2026-11-23 case review (GPT: "joint and timing fields with blanks, negatives, out-of-range"), tried
by hand: typing -50 in a joint box left "-50" showing while the joint sat at its minimum (the box
was only rewritten when the stored value changed), and emptying a box read as 0, which snapped the
joint to its minimum or pinned a move to 80 ms. A blank now keeps the old value; the box always
shows what is really used.
"""
import browser
import fake_serial
import qc as F

AREA = "studio"
TITLE = "Studio: blank and out-of-range numbers keep the box and the joint in agreement"
SLOW = False

DRIVER = """
function ready(f){ return qcWaitFor(function(){ try { var d = f.contentDocument; return d.readyState === "complete" && d.getElementById("jn0") && d.querySelector(".ktime input"); } catch (e) { return false; } }, 25000); }
function sleep(ms){ return new Promise(function(r){ setTimeout(r, ms); }); }
async function type(d, el, v){
  el.value = v; el.dispatchEvent(new Event("change", { bubbles: true })); await sleep(250);
}
async function run(){
  localStorage.setItem("mice.lang", "en");
  var f = document.createElement("iframe");
  f.style.cssText = "width:1440px;height:900px";
  document.body.appendChild(f);
  f.src = "/studio/";
  await ready(f); await sleep(800);
  var d = f.contentDocument;
  await type(d, d.getElementById("jn0"), "60");
  qcMark("J~good~" + d.getElementById("jn0").value + "~" + d.getElementById("js0").value);
  await type(d, d.getElementById("jn0"), "");
  qcMark("J~blank~" + d.getElementById("jn0").value + "~" + d.getElementById("js0").value);
  await type(d, d.getElementById("jn0"), "-50");
  qcMark("J~neg~" + d.getElementById("jn0").value + "~" + d.getElementById("js0").value + "~" + d.getElementById("jn0").min);
  var tb = d.querySelector(".ktime input");
  await type(d, tb, "1500");
  tb = d.querySelector(".ktime input");
  qcMark("T~good~" + tb.value);
  await type(d, tb, "");
  tb = d.querySelector(".ktime input");
  qcMark("T~blank~" + tb.value);
  qcMark("done");
}
window.addEventListener("load", function(){ run(); });
"""


def run(t):
    if not browser.available():
        t.give_up("headless browser not found")
    fake_serial.reset()
    base, _main = F.start_hub()
    browser.raw_page("<h1>wrapper</h1><script>" + DRIVER + "</script>", base, seconds=60)
    m = {x.split("~", 2)[0] + x.split("~", 2)[1]: x.split("~") for x in fake_serial.qc_marks if x[:2] in ("J~", "T~")}
    t.ok(len(m) == 5, "all five entries were tried", sorted(m))
    if len(m) == 5:
        t.ok(m["Jgood"][2:4] == ["60", "60"], "a good joint number is taken", m["Jgood"])
        t.ok(m["Jblank"][2:4] == ["60", "60"], "a blank joint box keeps the joint where it was", m["Jblank"])
        t.ok(m["Jneg"][2] == m["Jneg"][3] == m["Jneg"][4], "-50 is shown as the minimum the joint really took", m["Jneg"])
        t.ok(m["Tgood"][2] == "1500", "a good time is taken", m["Tgood"])
        t.ok(m["Tblank"][2] == "1500", "a blank time keeps the move's time", m["Tblank"])
