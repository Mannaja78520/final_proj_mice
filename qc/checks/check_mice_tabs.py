"""Mice.Tabs: a page in sections, one on screen at a time (A47-14, user 2026-10-23).

User: "ทำ tab ของแอพต่างๆเอาให้ใช้งานง่ายแบบตัวของ facereg" - the friend's
Reconize app lists its sections down the side and shows one. Every hub page
that has sections builds on shared/web/mice-ui.js Mice.Tabs + the `.tabbed`
rule in mice.css, so this opens a real page that uses it (Prize machines) in
a real browser, wide and phone-narrow, and measures what the browser did:

  * opened with #rules, only the rules card shows and that tab is ON;
  * a click on another tab shows only its cards and writes the address (#sheet),
    so a reload or a shared link lands there;
  * every page in qc/data/tabbed_pages.json uses the shared frame (Voice too);
  * wide: the list is BESIDE the content (left of it); phone: ABOVE it, and
    the page has no sideways scroll.
"""
import json

import browser
import fake_serial
import qc as F

AREA = "design"
TITLE = "a page in sections: one section shown, the list beside it (wide) or above (phone)"
SLOW = True

DRIVER = """
<style>html,body{margin:0}iframe{height:800px;border:0;display:block}</style>
<iframe id="wide" src="/app/gacha/#rules" style="width:1280px"></iframe>
<iframe id="narrow" src="/app/gacha/#rules" style="width:390px"></iframe>
<script>
function say(k, v){ return qcMark("MT " + k + "=" + String(v).replace(/[\\s|]+/g, "~")); }
function shown(d){ return [...d.querySelectorAll("[data-tab]")].filter(c => !c.hidden).map(c => c.dataset.tab).join(","); }
async function look(id){
  var f = document.getElementById(id), d = f.contentDocument, w = f.contentWindow;
  var ok = await qcWaitFor(function(){ return d.querySelector("#tabs .tab.on"); }, 15000);
  if (!ok) return say(id + "_start", "missing");
  await say(id + "_start", shown(d) + "!" + d.querySelector("#tabs .tab.on").dataset.t);
  d.querySelector('#tabs .tab[data-t="sheet"]').click();
  await say(id + "_click", shown(d) + "!" + w.location.hash);
  var nav = d.getElementById("tabs").getBoundingClientRect();
  var card = [...d.querySelectorAll("[data-tab]")].find(c => !c.hidden).getBoundingClientRect();
  await say(id + "_place", (nav.right <= card.left + 1 ? "beside" : nav.bottom <= card.top + 1 ? "above" : "over"));
  await say(id + "_wide", d.documentElement.scrollWidth <= w.innerWidth ? "fits" : d.documentElement.scrollWidth);
}
window.addEventListener("load", async function(){
  try{ await look("wide"); await look("narrow"); qcMark("done"); }catch(e){ qcFail(e); }
});
</script>
"""


def run(t):
    # Every page listed in qc/data/tabbed_pages.json is built the shared way:
    # the .tabbed frame with its list, and Mice.Tabs (not a page's own copy).
    pages = json.loads((F.CODE / "qc" / "data" / "tabbed_pages.json").read_text(encoding="utf-8"))["pages"]
    for p in pages:
        html = (F.CODE / p["file"]).read_text(encoding="utf-8")
        js = (F.CODE / p["script"]).read_text(encoding="utf-8")
        t.ok('<div class="tabbed"><nav id=' in html and "new Mice.Tabs(" in js
             and "/mice-ui.js" in html,
             "%s is built on the shared Mice.Tabs" % p["file"], p)
    if not browser.available():
        t.give_up("headless Edge not found - install Edge or run --quick")
    fake_serial.reset()
    base, main = F.start_hub()
    browser.raw_page(DRIVER, base, seconds=50)
    got = {}
    for m in fake_serial.qc_marks:
        if m.startswith("MT "):
            k, _, v = m[3:].partition("=")
            got[k] = v
    for size, place in (("wide", "beside"), ("narrow", "above")):
        t.ok(got.get(size + "_start") == "rules!rules",
             "%s: opened at #rules, only the rules section shows and its tab is on" % size, got)
        t.ok(got.get(size + "_click") == "sheet!#sheet",
             "%s: a click shows only that section and puts it in the address" % size, got)
        t.ok(got.get(size + "_place") == place,
             "%s: the list of sections is %s the content" % (size, place), got)
        t.ok(got.get(size + "_wide") == "fits", "%s: no sideways scroll" % size, got)
