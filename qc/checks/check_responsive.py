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

# Width x height, and what it stands for. The list used to stop at 1920, which
# left out both ends of what this is actually opened on: a cheap phone narrower
# than 360, and the big screen a robot installation is usually shown on. A
# layout that is only ever measured in the middle breaks at the edges, and the
# edges are where an audience sees it.
#
# 320 is the narrowest phone still sold. 1280x800 is the commonest laptop.
# 2560x1440 and 3840x2160 are the desktops in the lab, and a wall screen at a
# venue is one of those two - where a max-width layout can end up as a column
# of text down the middle of three metres of glass.
DEVICES = [
    (320, 658, "cheapest phone still sold"),
    (360, 780, "small Android phone"),
    (390, 844, "iPhone"),
    (768, 1024, "tablet portrait"),
    (1024, 768, "tablet landscape"),
    (1280, 800, "laptop"),
    (1920, 1080, "desktop, and the smaller wall screen"),
    (2560, 1440, "1440p desktop"),
    (3840, 2160, "4K desktop, and the big wall screen"),
]

DRIVER = """
<style>body{margin:0;background:#111}iframe{border:0;display:block}</style>
<script>
var PAGES = %s, DEVS = %s, LANES = %d;
function measure(url, w, h){
  return new Promise(function(res){
    var f = document.createElement("iframe");
    f.width = w; f.height = h; f.src = url;
    document.body.appendChild(f);
    f.onload = function(){
      // give layout, fonts and any boot script a moment to settle
      setTimeout(function(){
        var out = {url:url, w:w, over:-1, tallest:"", used:-1,
                   small:-1, tiny:-1, tinyWhat:""};
        try{
          var d = f.contentDocument, de = d.documentElement;
          out.over = Math.max(de.scrollWidth, d.body ? d.body.scrollWidth : 0) - w;
          // HOW MUCH OF THE SCREEN THE PAGE ACTUALLY FILLS. Overflow is the
          // fault at 320px; the opposite is the fault at 4K, where a
          // max-width layout leaves a column of text down the middle of three
          // metres of glass. Measured as the widest visible block, because a
          // centred column's own width is what a person sees.
          var right = 0, left = w;
          d.querySelectorAll("body *").forEach(function(el){
            var r = el.getBoundingClientRect();
            if (r.width < 40 || r.height < 10) return;   // ignore slivers
            var st = f.contentWindow.getComputedStyle(el);
            if (st.display === "none" || st.visibility === "hidden") return;
            if (r.right > right) right = r.right;
            if (r.left < left) left = r.left;
          });
          out.used = Math.max(0, Math.round(right - Math.max(0, left)));
          // TWO MORE THINGS A SCREENSHOT AT ONE WIDTH CANNOT SHOW.
          // The smallest text somebody has to READ, and the smallest control
          // they have to HIT. Both are per width: a page can be fine on a
          // laptop and unusable on the phone it is opened on at the venue.
          var small = 99, tiny = 999, tinyWhat = "", smallWhat = "";
          d.querySelectorAll("body *").forEach(function(el){
            var r = el.getBoundingClientRect();
            if (r.width < 1 || r.height < 1) return;
            var st = f.contentWindow.getComputedStyle(el);
            if (st.display === "none" || st.visibility === "hidden") return;
            var txt = (el.textContent || "").trim();
            var own = el.children.length === 0 && txt.length > 3;
            if (own) {
              var px = parseFloat(st.fontSize) || 99;
              if (px < small) {
                small = px;
                // NAME IT. Chasing a size through four stylesheets by hand is
                // how an afternoon goes; the measurement already knows.
                smallWhat = el.tagName.toLowerCase() +
                  (el.id ? "#" + el.id : "") +
                  (el.className && typeof el.className === "string" && el.className
                    ? "." + el.className.split(" ")[0] : "");
              }
            }
            // A CONTROL, not any link. An <a> inside a paragraph is text
            // that happens to be clickable, and holding prose to a 36px touch
            // target would mean no prose. Links that are dressed as controls -
            // .tab, .btn - count, because they are aimed at like buttons.
            var isCtl = /^(button|select|input|textarea)$/i.test(el.tagName) ||
                        (el.tagName === "A" &&
                         /(tab|btn|primary)/.test(el.className || ""));
            if (isCtl) {
              var h = Math.round(r.height);
              if (h > 0 && h < tiny) {
                tiny = h;
                tinyWhat = el.tagName.toLowerCase() + (el.id ? "#" + el.id : "");
              }
            }
          });
          out.small = Math.round(small);
          out.smallWhat = smallWhat;
          out.tiny = (tiny === 999) ? -1 : tiny;
          out.tinyWhat = tinyWhat;
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
    // SEVERAL IFRAMES AT ONCE. One at a time was 169 s of an 540 s gate
    // (2026-09-17). Each iframe has its own width and its own layout, so they
    // do not disturb each other's measurement; results keep their order.
    var jobs = [];
    for (var i = 0; i < PAGES.length; i++)
      for (var j = 0; j < DEVS.length; j++) jobs.push([PAGES[i], DEVS[j][0], DEVS[j][1]]);
    var results = new Array(jobs.length), next = 0;
    async function lane(){
      while (next < jobs.length){
        var k = next++;
        results[k] = await measure(jobs[k][0], jobs[k][1], jobs[k][2]);
      }
    }
    var lanes = [];
    for (var n = 0; n < LANES; n++) lanes.push(lane());
    await Promise.all(lanes);
    // report in chunks: one command line stays well inside an RS485 frame
    for (var k = 0; k < results.length; k++) {
      var r = results[k];
      // AWAIT each report. These go to the module over one serial port that
      // takes one caller at a time; firing 25 of them 30ms apart built a
      // backlog that timed out under load, and the check then failed with
      // "measurements missing" — pointing at a layout bug that did not exist.
      await qcMark("R|" + r.url + "|" + r.w + "|" + r.over + "|" + r.tallest +
                   "|" + r.used + "|" + r.small + "|" + r.tiny + "|" + r.tinyWhat +
                   "|" + r.smallWhat);
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
             "/rgb.html",
             # A23-1: both competitor versions answer the same floor.
             "/o/", "/o/rgb.html", "/o/studio/",
             "/g/", "/g/rgb.html", "/g/studio/"]
    devs = [[w, h] for w, h, _ in DEVICES]
    label = {w: name for w, _, name in DEVICES}

    # 6 iframes at once: measured, see the driver comment
    html = DRIVER % (json.dumps(pages), json.dumps(devs), 6)
    # 4 pages x 5 widths x 1.4 s settle, plus load time
    browser.raw_page(html, base, seconds=len(pages) * len(devs) * 2 + 22)

    marks = fake_serial.qc_marks
    t.ok(not any(m.startswith("ERROR") for m in marks), "the measurement ran", marks[:4])
    rows = [m[2:].split("|") for m in marks if m.startswith("R|")]
    if not t.eq(len(rows), len(pages) * len(devs),
                "every page was measured at every width"):
        t.ok(False, "measurements missing", [m for m in marks][:8])
        return

    for row in rows:
        url, w, over, worst = row[0], row[1], row[2], row[3]
        used = int(row[4]) if len(row) > 4 else -1
        small = int(row[5]) if len(row) > 5 else -1
        tiny = int(row[6]) if len(row) > 6 else -1
        tiny_what = row[7] if len(row) > 7 else ""
        small_what = row[8] if len(row) > 8 else ""
        w, over = int(w), int(over)
        name = "%s at %dpx (%s)" % (url.split("?")[0], w, label.get(w, ""))
        if over == -2:
            t.ok(False, name + " could be measured", worst)
            continue
        # a couple of px is rounding on a scrollbar, not a layout break
        t.ok(over <= 2, "no sideways scrolling — " + name,
             "%dpx wider than the screen; widest element: %s" % (over, worst or "?"))

        # ---- and it uses the screen it was given ---------------------
        # Only on the big ones: a max-width layout is RIGHT to stop growing at
        # some point - text a metre wide is unreadable - but a page that fills
        # a third of a wall screen has stopped being a layout and become a
        # column. A quarter is the floor: generous enough that a deliberate
        # reading width passes, mean enough to catch a page that never grew.
        # ---- readable, and hittable, at THIS width -------------------
        # A screenshot at one width proves one width. These are the two things
        # that go wrong at the ends: text too small to read on the screen it is
        # actually on, and a control too short to hit with a thumb.
        if 0 < small < 11:
            t.ok(False, "text is readable — " + name,
                 "the smallest text with words in it is %dpx (%s). Below 11px "
                 "it is not a size, it is a hint that something is there"
                 % (small, small_what or "?"))
        else:
            t.ok(True, "text is readable — " + name)

        # NOT ASSERTED HERE, ON PURPOSE. Touch sizing lives behind
        # @media (pointer:coarse), and a headless DESKTOP browser never matches
        # that however narrow the window is - so this measurement is the
        # mouse-sized rendering at a phone width, which is a different thing.
        # Asserting on it said the module website failed on a phone when what
        # it had measured was a desktop. The coarse rules are checked against
        # the stylesheet instead, below.
        if w <= 430 and tiny > 0 and tiny < 20:
            print("      (%s: shortest control %dpx as a DESKTOP renders it - %s)"
                  % (name, tiny, tiny_what or "?"))

        if w >= 2560 and used >= 0:
            t.ok(used >= w // 4,
                 "uses the screen — " + name,
                 "the widest thing on the page is %dpx on a %dpx screen. On a "
                 "wall screen that is a column down the middle of the glass; "
                 "if the narrow width is deliberate, the container it sits in "
                 "should still fill the screen" % (used, w))

    # ---- what a desktop browser cannot answer -----------------------
    # Touch targets are a media query away, and this browser never matches it.
    # So the rules are held to the stylesheet: every control kind a finger has
    # to hit must be sized for one somewhere in the coarse-pointer block.
    css = (F.CODE / "shared" / "web" / "mice.css").read_text(encoding="utf-8")
    coarse = ""
    for m in re.finditer(r"@media \(pointer:coarse\)\s*\{", css):
        depth, i = 1, m.end()
        while i < len(css) and depth:
            depth += (css[i] == "{") - (css[i] == "}")
            i += 1
        coarse += css[m.end():i]
    t.ok(coarse, "the design system sizes controls for a finger somewhere")

    # And the big-screen rule, for the same reason: the used-width measurement
    # only bites at the very largest size, so removing the 2560 block alone
    # slipped through. It is ONE rule now, in the shared stylesheet, so it can
    # be held there.
    for w_at in ("2560", "3840"):
        t.contains(css, "min-width:%spx" % w_at,
                   "the shared stylesheet scales at %spx" % w_at)
    t.contains(css, "body:not(.app){zoom",
               "by scaling the page, not by widening a column of small text")
    # The RULE, not the word. "input" also appears in the checkbox rule, so
    # asserting the word passed with the min-height line deleted - the sabotage
    # tool caught that.
    sized = [l.strip() for l in coarse.splitlines() if "min-height" in l]
    t.ok(sized, "there is a minimum height for controls",
         "the coarse block sizes nothing: %s" % coarse.strip()[:100])
    for kind, why in (("button", "the commonest control of all"),
                      ("input", "typed into as often as anything is pressed"),
                      ("select", "a dropdown is hit as often as a button")):
        t.ok(any(kind in l for l in sized),
             "%s has a minimum height - %s" % (kind, why),
             "the rules with a minimum are: %s" % sized)
    # A CHECKBOX IS NOT COVERED BY min-height. It has an intrinsic box, so the
    # input,select,textarea rule never reached it and it stayed 13px - measured
    # on the module website at phone widths, input#nlink.
    t.contains(coarse, "input[type=checkbox]",
               "and a checkbox is given a real size of its own")
    m = re.search(r"min-height:(\d+)px", coarse)
    if t.ok(m, "and there is a minimum height"):
        t.ok(int(m.group(1)) >= 36,
             "of at least 36px (%s)" % m.group(1),
             "36px is about a thumb; below that the miss rate is what people "
             "call the app being fiddly")

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
