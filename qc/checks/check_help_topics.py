"""Help must describe the actual menus and one fixed Receive Hall (human 24 Oct).

Search used to ignore illustrated cards and paragraphs; searching a sentence
shown on the page could report no results. Exercise that behaviour, clearing,
navigation, technical visibility, and phone overflow in the browser.
"""
import re

import browser
import fake_serial
import qc as F

AREA = "hub"
TITLE = "Help topics match app menus, Hall layout and searchable content"
SLOW = True


def run(t):
    parts = F.CODE / "main_python/web/help/parts"
    gacha = (parts / "gacha.html").read_text(encoding="utf-8")
    faces = (parts / "faces.html").read_text(encoding="utf-8")
    t.contains(gacha, "Hall 1 ตัว", "one fixed Hall sensor is documented")
    t.contains(gacha, "ฝั่งปล่อยของไม่มี Hall", "Drop has no sensor")
    t.contains(gacha, "อยู่ด้านเดียวกัน", "Receive and Drop share the same side")
    t.eq(re.findall(r">(M[1-4])</text>", gacha), ["M1", "M2", "M3", "M4"],
         "diagram distinguishes four rotating magnets")
    t.ok(not re.search(r"Hall #[1-4]|100%|180°", gacha),
         "no extra Hall sensors, guaranteed centering or assumed opposite stations", gacha[:200])
    for app, help_text in (("gacha", gacha), ("faces", faces)):
        source = (F.CODE / "apps" / app / "index.html").read_text(encoding="utf-8")
        if app == "gacha":
            tabs = source[source.index("const TABS ="):source.index("const TAB_LOAD")]
            labels = re.findall(r'\["[a-z]+", "([^"]+)"', tabs)
        else:
            labels = re.findall(r'label: "([^"]+)"', source[source.index('new Mice.Tabs("tabs"'):])
        for label in labels:
            t.contains(help_text, label, app + " Help names actual tab: " + label)
    if not t.ok(browser.available(), "browser available for Help search regression", "Edge required"):
        return
    base, _ = F.start_hub()
    fake_serial.qc_marks.clear()
    try:
        browser.raw_page('''
<iframe id="f" src="/help#faces" style="width:390px;height:750px"></iframe>
<script>
window.addEventListener("load", async function(){
  try {
    var f = document.getElementById("f"), d = f.contentDocument, w = f.contentWindow;
    await qcWaitFor(() => d.querySelector(".sec-nav"), 10000);
    var visible = () => Array.from(d.querySelectorAll("main > section"))
      .filter(s => w.getComputedStyle(s).display !== "none").map(s => s.id).join(",");
    var q = d.getElementById("q");
    q.value = d.querySelector("#faces .info-box p").textContent.trim();
    q.dispatchEvent(new w.Event("input", {bubbles:true}));
    await qcMark("card-search=" + visible());
    q.value = "mice-help-no-such-term-1024";
    q.dispatchEvent(new w.Event("input", {bubbles:true}));
    await qcMark("empty=" + (visible() === "" && w.getComputedStyle(d.getElementById("none")).display !== "none"));
    q.value = ""; q.dispatchEvent(new w.Event("input", {bubbles:true}));
    await qcMark("cleared=" + visible());
    d.querySelector('nav a[href="#gacha"]').click();
    await qcWaitFor(() => visible() === "gacha", 3000);
    await qcMark("nav=" + visible());
    await qcMark("phone=" + (d.documentElement.scrollWidth <= d.documentElement.clientWidth + 1));
    await qcMark("tech=" + (w.getComputedStyle(d.querySelector("#gacha .where")).display === "none"));
  } catch(e) { await qcMark("error=" + e.message); }
  finally { qcMark("done"); }
});
</script>''', base, seconds=25)
        marks = fake_serial.qc_marks
        for expected in ("card-search=faces", "empty=true", "cleared=faces", "nav=gacha", "phone=true", "tech=true"):
            t.ok(expected in marks, expected, marks)
    finally:
        browser.kill()
