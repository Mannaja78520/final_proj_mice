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
      qcMark("R|" + r.url + "|" + r.w + "|" + r.over + "|" + r.tallest);
      await new Promise(function(s){ setTimeout(s, 30); });
    }
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

    pages = ["/", "/help", "/studio/", "/mod?dev=usb%3A" + fake_serial.PORT]
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
