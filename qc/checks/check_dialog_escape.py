"""Esc closes the Report box and the keyboard goes back to the button that opened it.

2026-11-23 case review (GPT's keyboard-only dialog case, then tried by hand): the Shortcuts list
says Esc "closes whatever is open", but closeAnyOpen() knew the Flash and Shortcuts boxes only,
so Esc left the Report box (the one people open most) on screen, and nothing handed the keyboard
back to the Report button.
"""
import browser
import fake_serial
import qc as F

AREA = "web"
TITLE = "Esc closes the Report box and focus returns to its button"
SLOW = False

DRIVER = """
function ready(f){ return qcWaitFor(function(){ try { var d = f.contentDocument; return d.readyState === "complete" && d.body && d.body.innerText.length > 20; } catch (e) { return false; } }, 20000); }
function sleep(ms){ return new Promise(function(r){ setTimeout(r, ms); }); }
async function run(){
  var f = document.createElement("iframe");
  f.style.cssText = "width:390px;height:700px";
  document.body.appendChild(f);
  f.src = "/";
  await ready(f); await sleep(1200);
  var d = f.contentDocument, w = f.contentWindow;
  var btn = d.querySelector("[onclick*=openReport]");
  btn.focus(); btn.click(); await sleep(300);
  var m = d.getElementById("reportModal");
  qcMark("OPEN~" + (m.hidden ? 0 : 1));
  var ta = d.getElementById("reportText");
  ta.dispatchEvent(new w.KeyboardEvent("keydown", { key: "Escape", bubbles: true })); await sleep(300);
  qcMark("CLOSED~" + (m.hidden ? 1 : 0) + "~" + (d.activeElement === btn ? 1 : 0));
  qcMark("done");
}
window.addEventListener("load", function(){ run(); });
"""


def run(t):
    if not browser.available():
        t.give_up("headless browser not found")
    fake_serial.reset()
    base, _main = F.start_hub()
    browser.raw_page("<h1>wrapper</h1><script>" + DRIVER + "</script>", base, seconds=40)
    marks = list(fake_serial.qc_marks)
    op = [m for m in marks if m.startswith("OPEN~")]
    cl = [m for m in marks if m.startswith("CLOSED~")]
    t.ok(bool(op) and bool(cl), "the page answered", marks[-3:])
    if op and cl:
        t.ok(op[0] == "OPEN~1", "the Report box opens from its button", op[0])
        _, hidden, back = cl[0].split("~")
        t.ok(hidden == "1", "Esc closes the Report box", cl[0])
        t.ok(back == "1", "the keyboard goes back to the Report button", cl[0])
