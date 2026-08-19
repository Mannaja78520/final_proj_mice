"""Every web app has to work on a phone at the robot and on a shop monitor.

The failure this guards is the one users actually hit: the page is WIDER than
the screen, so it scrolls sideways and half the controls sit off the edge. That
cannot be checked by reading CSS — it has to be measured after layout.

Each page is loaded in an iframe at a real device width. Media queries inside
an iframe respond to the iframe's own width, so the phone breakpoints fire
exactly as they would on the phone.
"""
import json
import re

import browser
import fake_serial
import qc as F

AREA = "responsive"
TITLE = "web apps fit every screen"
SLOW = True

# width x height, and what it stands for
DEVICES = [
    (360, 780, "small Android phone"),
    (390, 844, "iPhone"),
    (768, 1024, "tablet portrait"),
    (1024, 768, "tablet landscape"),
    (1920, 1080, "desktop"),
]

DRIVER = """
<style>body{margin:0;background:#111}iframe{border:0;display:block}</style>
<script>
var PAGES = %s, DEVS = %s;
function measure(url, w, h){
  return new Promise(function(res){
    var f = document.createElement("iframe");
    f.width = w; f.height = h; f.src = url;
    document.body.appendChild(f);
    f.onload = function(){
      // give layout, fonts and any boot script a moment to settle
      setTimeout(function(){
        var out = {url:url, w:w, over:-1, tallest:""};
        try{
          var d = f.contentDocument, de = d.documentElement;
          out.over = Math.max(de.scrollWidth, d.body ? d.body.scrollWidth : 0) - w;
          if (out.over > 0) {           // name the widest offender, to fix it
            var worst = 0;
            d.querySelectorAll("*").forEach(function(el){
              var r = el.getBoundingClientRect();
              if (r.right > worst) { worst = r.right;
                out.tallest = el.tagName.toLowerCase() +
                  (el.id ? "#" + el.id : "") +
                  (el.className && el.className.baseVal === undefined && el.className
                    ? "." + String(el.className).split(" ")[0] : ""); }
            });
          }
        }catch(e){ out.over = -2; out.tallest = String(e.message||e).slice(0,40); }
        f.remove();
        res(out);
      }, 1400);
    };
  });
}
window.addEventListener("load", async function(){
  try{
    var results = [];
    for (var i = 0; i < PAGES.length; i++)
      for (var j = 0; j < DEVS.length; j++)
        results.push(await measure(PAGES[i], DEVS[j][0], DEVS[j][1]));
    // report in chunks: one command line stays well inside an RS485 frame
    for (var k = 0; k < results.length; k++) {
      var r = results[k];
      // AWAIT each report. These go to the module over one serial port that
      // takes one caller at a time; firing 25 of them 30ms apart built a
      // backlog that timed out under load, and the check then failed with
      // "measurements missing" — pointing at a layout bug that did not exist.
      await qcMark("R|" + r.url + "|" + r.w + "|" + r.over + "|" + r.tallest);
    }
    qcMark("done");
  }catch(e){ qcFail(e); }
});
</script>
"""

# Measured with the panel at its DEFAULT width, which is the width it has when
# a person opens Studio — not a width chosen to make the numbers work.
PANEL = """
<style>html,body{margin:0}#f{width:1440px;height:900px;border:0}</style>
<iframe id="f" src="/studio/"></iframe>
<script>
window.addEventListener("load", async function(){
  try{
    var d = document.getElementById('f').contentDocument;
    var ok = await qcWaitFor(function(){
      return d.querySelector('.jrow input[type=range]'); }, 15000);
    if (!ok){ await qcMark("P over=-1 worst=panel~never~rendered"); return qcMark("done"); }
    var side = d.getElementById('side');
    var right = side.getBoundingClientRect().right, worst = "", by = 0;
    side.querySelectorAll("*").forEach(function(el){
      var o = el.getBoundingClientRect().right - right;
      if (o > by) { by = o; worst = el.tagName.toLowerCase() +
        (el.id ? "#" + el.id : "") +
        (el.className ? "." + String(el.className).split(" ")[0] : ""); }
    });
    await qcMark("P over=" + Math.round(Math.max(by, side.scrollWidth - side.clientWidth)) +
                 " worst=" + (worst || "none"));
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

    # /rgb.html is here because it was NOT, for a long time. It is served by
    # the hub and used at a venue on a phone, and it was in none of the three
    # page lists — no responsive check, no throws check, no token check — so it
    # drifted off the design system unnoticed.
    pages = ["/", "/help", "/studio/", "/mod?dev=usb%3A" + fake_serial.PORT,
             "/rgb.html"]
    devs = [[w, h] for w, h, _ in DEVICES]
    label = {w: name for w, _, name in DEVICES}

    html = DRIVER % (json.dumps(pages), json.dumps(devs))
    # 4 pages x 5 widths x 1.4 s settle, plus load time
    browser.raw_page(html, base, seconds=len(pages) * len(devs) * 2 + 22)

    marks = fake_serial.qc_marks
    t.ok(not any(m.startswith("ERROR") for m in marks), "the measurement ran", marks[:4])
    rows = [m[2:].split("|") for m in marks if m.startswith("R|")]
    if not t.eq(len(rows), len(pages) * len(devs),
                "every page was measured at every width"):
        t.ok(False, "measurements missing", [m for m in marks][:8])
        return

    for url, w, over, worst in rows:
        w, over = int(w), int(over)
        name = "%s at %dpx (%s)" % (url.split("?")[0], w, label.get(w, ""))
        if over == -2:
            t.ok(False, name + " could be measured", worst)
            continue
        # a couple of px is rounding on a scrollbar, not a layout break
        t.ok(over <= 2, "no sideways scrolling — " + name,
             "%dpx wider than the screen; widest element: %s" % (over, worst or "?"))

    # ---- a PANEL must not clip its own controls either ---------------
    # The page can pass everything above while a fixed-width panel inside it
    # hides a control. Studio's side panel is 320px and held a grid of
    # 96px + 1fr + 64px; the 1fr contained a range input, whose automatic
    # minimum size is its intrinsic 131px, so the track refused to shrink and
    # the joint number box sat 17px past the edge behind a scrollbar.
    fake_serial.reset()
    browser.raw_page(PANEL, base, seconds=30)
    got = {}
    for m in fake_serial.qc_marks:
        if m.startswith("P "):
            for kv in m[2:].split(" "):
                k, _, v = kv.partition("=")
                got[k] = v
    if t.ok(got, "the studio panel was measured", fake_serial.qc_marks[-3:]):
        over = int(got.get("over", "-1"))
        t.ok(0 <= over <= 2,
             "studio's side panel does not clip its own controls",
             "%s px of it is off the edge; widest offender: %s"
             % (over, got.get("worst", "?")))

    # ---- and the rules that make it stay that way -------------------
    for path, f in (("hub", F.HUB / "web" / "hub.html"),
                    ("help", F.HUB / "web" / "help.html"),
                    ("studio", F.STUDIO_WEB / "style.css"),
                    ("module site", F.FIRMWARE / "src/web/WebUI.h")):
        src = f.read_text(encoding="utf-8", errors="replace")
        t.ok("@media" in src, "%s has responsive rules at all" % path)
    for path, f in (("hub", F.HUB / "web" / "hub.html"),
                    ("help", F.HUB / "web" / "help.html"),
                    ("studio", F.STUDIO_WEB / "index.html"),
                    ("module site", F.FIRMWARE / "src/web/WebUI.h")):
        src = f.read_text(encoding="utf-8", errors="replace")
        t.ok(re.search(r'name="viewport"', src),
             "%s tells the phone its real width" % path)
