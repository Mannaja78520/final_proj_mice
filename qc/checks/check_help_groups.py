"""Help's list of topics is in groups that open and close (A47-18, user 2026-10-23).

"help ดีแล้วแต่ทำ group ให้หน่อย ... โชว์ได้หรือเก็บได้ตาม group เผื่อมีแอพและ
อย่างอื่นเพิ่มในอนาคต". The list is HELP_GROUPS in
main_python/web/help/parts/topics.js (one topic at a time and Previous / Next
are search.js, held by check_help_topics). In a real browser:

  * every section of the page is named in HELP_GROUPS once (a new app's
    section with no line there would be unreachable) and nothing names a
    missing one;
  * a group shut by a click stays shut after a reload, the others stay open;
  * opening a topic whose group is shut opens that group again.
"""
import re

import browser
import fake_serial
import qc as F

AREA = "hub"
TITLE = "help: the list of topics is in groups that open, close and are remembered"
SLOW = True

DRIVER = """
<style>html,body{margin:0}iframe{width:1280px;height:800px;border:0}</style>
<iframe id="h" src="/help#gacha"></iframe>
<script>
function say(k, v){ return qcMark("HG " + k + "=" + String(v).replace(/[\\s|]+/g, "~")); }
function shut(d, g){ return d.querySelector('[data-grp="' + g + '"]').classList.contains("shut"); }
window.addEventListener("load", async function(){
  try{
    var f = document.getElementById("h"), d = f.contentDocument, w = f.contentWindow;
    await qcWaitFor(function(){ return d.querySelector("#helpNav .grp-box"); }, 15000);
    d.querySelector('[data-grp="wrong"] .grp').click();
    await say("click", shut(d, "wrong"));
    // Only the #part would differ, so setting src would not reload: reload for real.
    var back = new Promise(r => f.onload = r);
    w.location.hash = "#hub"; w.location.reload();
    await back;
    d = f.contentDocument;
    await qcWaitFor(function(){ return d.querySelector("#helpNav .grp-box"); }, 15000);
    await say("kept", shut(d, "wrong") + "!" + shut(d, "use"));
    w.location.hash = "#qc";
    await qcWaitFor(function(){ return !shut(d, "wrong"); }, 3000);
    await say("reopen", shut(d, "wrong"));
    qcMark("done");
  }catch(e){ qcFail(e); }
});
</script>
"""


def run(t):
    html = (F.CODE / "main_python" / "web" / "help.html").read_text(encoding="utf-8")
    js = (F.CODE / "main_python" / "web" / "help" / "parts" / "topics.js").read_text(encoding="utf-8")
    sections = set(re.findall(r'<section id="([a-z0-9-]+)"', html))
    listed = re.findall(r'\["([a-z0-9-]+)", "', js[js.index("HELP_GROUPS"):js.index("];")])
    t.ok(sections == set(listed) and len(listed) == len(set(listed)),
         "every help section is in the grouped list once, and the list names no missing one",
         {"no line in the list": sorted(sections - set(listed)), "listed but no section": sorted(set(listed) - sections)})
    if not browser.available():
        t.give_up("headless Edge not found - install Edge or run --quick")
    fake_serial.reset()
    base, main = F.start_hub()
    browser.raw_page(DRIVER, base, seconds=40)
    got = {}
    for m in fake_serial.qc_marks:
        if m.startswith("HG "):
            k, _, v = m[3:].partition("=")
            got[k] = v
    t.ok(got.get("click") == "true", "a click on a group's name shuts it", got)
    t.ok(got.get("kept") == "true!false", "a shut group stays shut after a reload, the others stay open", got)
    t.ok(got.get("reopen") == "false", "opening a topic in a shut group opens that group", got)
