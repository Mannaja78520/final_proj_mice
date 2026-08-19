"""A tab looks the same in all three apps, measured after layout.

The hub, the module website and Nong Studio each had their own tab bar, all
driven by a function called showTab, and they disagreed:

    hub           active = OUTLINE — accent border and accent text
    module site   active = FILLED  — accent background
    studio        active = FILLED

So the hub looked like a different product from the two screens it opens, and
a fourth screen would have had to guess which to copy.

This does not read the CSS. It opens all three in a real browser, finds the
tab that is currently ON, and compares the colours the browser actually
computed — the only way to catch a fourth copy of the rule appearing in one
app's own stylesheet and quietly winning.

Filled is the one that survives: an outlined tab differs from an unselected
one only by colour, which fails a screenshot and fails a colourblind reader.
"""
import urllib.parse

import browser
import fake_serial
import qc as F

AREA = "design"
TITLE = "one kind of tab, in every app"
SLOW = True

DRIVER = """
<style>html,body{margin:0}iframe{width:1200px;height:800px;border:0;display:block}</style>
<iframe id="hub" src="/"></iframe>
<iframe id="mod" src="%s"></iframe>
<iframe id="studio" src="/studio/"></iframe>
<script>
function say(k, v){ return qcMark("TB " + k + "=" + String(v).replace(/[\\s|]+/g, "~")); }
async function look(id, sel){
  var f = document.getElementById(id);
  var d = f.contentDocument, w = f.contentWindow;
  var ok = await qcWaitFor(function(){ return d.querySelector(sel); }, 15000);
  if (!ok) return say(id, "missing");
  var on = d.querySelector(sel);
  var off = d.querySelector(sel.replace(".on", "") + ":not(.on)");
  var cs = w.getComputedStyle(on);
  var co = off ? w.getComputedStyle(off) : null;
  // The colours the browser really used, not what any stylesheet says — and
  // the UNSELECTED tab too, because "they all match" is satisfied by three
  // apps that are all equally wrong.
  await say(id + "off", co ? co.backgroundColor : "none");
  // "!" survives the sanitiser; a pipe does not — it collapses [\s|]+
  return say(id, cs.backgroundColor + "!" + cs.color + "!" + cs.fontWeight);
}
window.addEventListener("load", async function(){
  try{
    await look("hub", "#tabs .tab.on");
    await look("mod", "#modTabs .tab.on");
    await look("studio", "#sideTabs .tab.on");
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
    url = "/mod?dev=usb%3A" + urllib.parse.quote(fake_serial.PORT)
    browser.raw_page(DRIVER % url, base, seconds=50)

    got = {}
    for m in fake_serial.qc_marks:
        if m.startswith("TB "):
            k, _, v = m[3:].partition("=")
            got[k] = v.replace("~", " ")
    if not t.ok(got, "the three apps reported their tabs",
                fake_serial.qc_marks[-4:]):
        return

    for app in ("hub", "mod", "studio"):
        t.ok(got.get(app) and got[app] != "missing",
             "%s has a tab that is switched on" % app, got)

    seen = {app: got.get(app, "") for app in ("hub", "mod", "studio")}
    same = len(set(v for v in seen.values() if v and v != "missing")) == 1
    t.ok(same,
         "the ACTIVE tab is identical in all three apps",
         "three different answers to the same question: %s" % seen)

    # ...and the selected tab is really distinguishable from an unselected one.
    # "All three match" is satisfied by three apps that are all equally wrong,
    # which was proven by breaking it: dropping the fill from the shared rule
    # changed all three together and this check still passed.
    for app in ("hub", "mod", "studio"):
        on_bg = got.get(app, "").split("!")[0]
        off_bg = got.get(app + "off", "")
        if not on_bg or off_bg in ("", "none"):
            continue
        t.ok(on_bg != off_bg,
             "in %s the selected tab has a different BACKGROUND, not just text"
             % app,
             "selected and unselected are both %r — that difference disappears "
             "in a screenshot and for a colourblind reader" % on_bg)
