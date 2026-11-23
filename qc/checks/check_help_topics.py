"""Help must describe the actual menus and one fixed Receive Hall (human 24 Oct).

Search used to ignore illustrated cards and paragraphs; searching a sentence
shown on the page could report no results. Exercise that behaviour, clearing,
navigation, technical visibility, and phone overflow in the browser.
"""
import re
from pathlib import Path
from tempfile import TemporaryDirectory

import browser
import fake_serial
import qc as F

AREA = "hub"
TITLE = "Help topics match app menus, Hall layout and searchable content"
SLOW = True


def run(t):
    apps = F.CODE / "apps"
    gacha = (apps / "gacha/help/th.html").read_text(encoding="utf-8")
    faces = (apps / "faces/help/en.html").read_text(encoding="utf-8")
    t.contains(gacha, "Hall 1 ตัว", "one fixed Hall sensor is documented")
    t.contains(gacha, "ฝั่งปล่อยของไม่มี Hall", "Drop has no sensor")
    t.contains(gacha, "อยู่ด้านเดียวกัน", "Receive and Drop share the same side")
    t.eq(re.findall(r">(M[1-4])</text>", gacha), ["M1", "M2", "M3", "M4"],
         "diagram distinguishes four rotating magnets")
    t.ok(not re.search(r"Hall #[1-4]|100%|180°", gacha),
         "no extra Hall sensors, guaranteed centering or assumed opposite stations", gacha[:200])
    gacha_en = (apps / "gacha/help/en.html").read_text(encoding="utf-8")
    for app, help_text in (("gacha", gacha_en), ("faces", faces)):
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
    base, main = F.start_hub()
    # This browser regression covers Reconize even on PCs without a partner install.
    with TemporaryDirectory(prefix="mice-help-reconize-") as tmp:
        (Path(tmp) / "installed").touch()
        original = main._partner_templates
        templates = original()
        templates["reconize"].update(folder=tmp, detect=["installed"])
        try:
            main._partner_templates = lambda: templates
            check_browser(t, base)
        finally:
            main._partner_templates = original


def check_browser(t, base):
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
    // Mimic a translated heading that arrives after the navigator starts.
    var late = d.querySelector("#modsite .shead h2");
    late.textContent += " 9283471";
    q.value = late.textContent.trim();
    q.dispatchEvent(new w.Event("input", {bubbles:true}));
    await qcMark("late-search=" + visible());
  } catch(e) { await qcMark("error=" + e.message); }
  finally { qcMark("done"); }
});
</script>''', base, seconds=25)
        marks = fake_serial.qc_marks
        for expected in ("card-search=faces", "empty=true", "cleared=faces", "nav=gacha", "phone=true", "tech=true", "late-search=modsite"):
            t.ok(expected in marks, expected, marks)
    finally:
        browser.kill()
