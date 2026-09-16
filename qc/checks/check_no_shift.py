"""A module going stale must not move everything below it.

Asked for 2026-08-21: *when the module it lost connection now it add the line
and make below shift down make it not shift down it make user headace*.

A row that misses a sweep is marked LATE and gains `· last answered 12s ago` in
its meta span. That span is a flex child with `flex:1`, so the extra words
wrapped, the row grew a line taller, and every row below it jumped down the
page — while the operator was reading them. The design rules of this project
put that in the never list: *layout that shifts when data arrives (reserve the
space)*.

MEASURED, NOT READ. The fix is three CSS properties, and asserting that CSS
text appears proves only that somebody typed it: whether a row grows depends on
the width it is rendered at, the font, and which other text is in the row. So
this drives a real browser, measures each row's height with a live module,
marks the same module stale, measures again, and compares. That is also why it
catches the reverse mistake — clipping so hard that the stale note itself
disappears, which would trade a jumping page for a lying one.
"""
import json
import re

import browser
import fake_serial
import qc as F

AREA = "ui"
TITLE = "a module going stale does not push the page around"
SLOW = True

PAGE = """
<style>html,body{margin:0}#f{width:900px;height:800px;border:0}</style>
<iframe id="f" src="/"></iframe>
<script>
function done(s){ qcMark("SHIFT " + s); qcMark("done"); }
window.addEventListener("load", async function(){
  var out = [];
  try{
    var d = document.getElementById("f").contentDocument;
    // SHOW THE TAB THE LIST LIVES IN. Measured while it was hidden, every
    // height came back 0 — and 0 == 0 passed the comparison happily, which is
    // a check that proves nothing at all.
    // #mods sits in the MODULES tab, and every other tab is display:none.
    await qcWaitFor(function(){
      return d.querySelector('#tabs .tab[data-go="modules"]'); }, 30000);
    d.querySelector('#tabs .tab[data-go="modules"]').click();
    // A row to measure. The page draws these from the module list, so wait for
    // one rather than guessing how long a scan takes.
    var ok = await qcWaitFor(function(){
      return d.querySelectorAll("#mods .mod, #usbmods .mod").length > 0; }, 40000);
    out.push("rows=" + (ok ? "yes" : "no"));
    if (!ok) return done(out.join(" "));

    var row = d.querySelector("#mods .mod, #usbmods .mod");
    var list = row.parentNode;
    var before = 0, after = 0;
    var listBefore = list.getBoundingClientRect().height;

    // THE PAGE'S OWN ROW BUILDER, not markup this check invents. Hand-written
    // markup put the note after the technical tail, which is not where the
    // page puts it, and the check then measured a layout the product never
    // produces.
    var w = d.defaultView;
    out.push("builder=" + (typeof w.modRow === "function" ? "yes" : "no"));
    if (typeof w.modRow !== "function") return done(out.join(" "));
    var live = w.modRow({id: 42, name: "lab-pair", type: "nong",
                         ip: "10.94.163.220",
                         routes: [{kind: "wifi"}, {kind: "usb", port: "COM29"}]},
                        "", "", "", null);
    var gone = w.modRow({id: 42, name: "lab-pair", type: "nong",
                         ip: "10.94.163.220", stale: true, lastSeen: 41,
                         routes: [{kind: "wifi"}, {kind: "usb", port: "COM29"}]},
                        "", "", "", null);
    // IN PLACE, the way it really happens: the same row is redrawn stale on
    // the next sweep. Appending both and comparing the LIST measured my own
    // two extra rows instead of the change under test.
    // AT A PHONE WIDTH TOO. On a wide screen nothing wraps whatever the CSS
    // says, so a wide-only measurement passed with the wrapping guard removed.
    // 360 is where the row is actually tight, and where this bug is felt.
    var fr = document.getElementById("f");
    async function settle(){
      await new Promise(function(r){ requestAnimationFrame(function(){ requestAnimationFrame(r); }); });
    }
    async function measure(px){
      fr.style.width = px + "px";
      await settle();
      list.appendChild(live);
      await settle();
      var h1 = live.getBoundingClientRect().height;
      var l1 = list.getBoundingClientRect().height;
      list.replaceChild(gone, live);
      await settle();
      var h2 = gone.getBoundingClientRect().height;
      var l2 = list.getBoundingClientRect().height;
      list.replaceChild(live, gone);      // put it back for the next width
      await settle();
      return [h1, h2, l1, l2];
    }
    var wide = await measure(900);
    var narrow = await measure(360);
    out.push("narrowbefore=" + Math.round(narrow[0]));
    out.push("narrowafter=" + Math.round(narrow[1]));
    list.appendChild(gone);
    await settle();
    before = wide[0]; after = wide[1];
    listBefore = wide[2];
    row = gone;
    // let the browser lay it out again
    await new Promise(function(r){ requestAnimationFrame(function(){ requestAnimationFrame(r); }); });

    var listAfter = wide[3];
    out.push("rowbefore=" + Math.round(before));
    out.push("rowafter=" + Math.round(after));
    out.push("listbefore=" + Math.round(listBefore));
    out.push("listafter=" + Math.round(listAfter));
    // ...and the note is really on the page, not clipped out of existence
    var note = row.querySelector(".state-stale");
    out.push("noteshown=" + (note && note.getBoundingClientRect().width > 8 ? "yes" : "no"));
    done(out.join(" "));
  } catch (e) { done(out.join(" ") + " ERR=" + String(e).slice(0, 60)); }
});
</script>
"""


def run(t):
    if not browser.available():
        t.ok(False, "headless Edge is available for browser checks")
        return
    fake_serial.reset()
    base, main = F.start_hub()
    real = main.scan_modules
    main.scan_modules = lambda force=False: []      # only the fake cable
    try:
        # 85, not 70: the waits inside add up to 70s and check_browser_budget
        # wants headroom on top, because a window that ends mid-wait reports a
        # slow machine as a broken page.
        browser.raw_page(PAGE, base, seconds=85)
    finally:
        main.scan_modules = real

    marks = [m for m in fake_serial.qc_marks if m.startswith("SHIFT ")]
    if not t.ok(marks, "the page reported back",
                "never ran: %r" % (fake_serial.qc_marks[-3:],)):
        return
    got = dict(kv.split("=", 1) for kv in marks[-1][6:].split(" ") if "=" in kv)
    if "ERR" in got:
        t.ok(False, "the page ran without throwing", "%s (got %r)" % (got["ERR"], got))
        return
    if not t.eq(got.get("rows"), "yes", "there is a module row to measure"):
        return

    before, after = int(got.get("rowbefore", 0)), int(got.get("rowafter", -1))
    # A ZERO IS NOT A PASS. The list sits in a tab, and measured while that tab
    # was hidden every height was 0 — so "same height" was true and meant
    # nothing. Found by reading the marks, not by the check failing.
    if not t.ok(before > 10, "the rows were really on screen when measured "
                "(%dpx)" % before,
                "a hidden tab measures 0 and every comparison below passes"):
        return
    t.eq(after, before,
         "the row is the same height once it goes stale (%dpx)" % before)
    lb, la = int(got.get("listbefore", 0)), int(got.get("listafter", -1))
    t.eq(la, lb,
         "so nothing below it moves (%dpx list)" % lb)
    t.eq(got.get("noteshown"), "yes",
         "and the stale note is still visible, not clipped away")

    # THE ONE THAT MATTERS ON A PHONE. A wide screen has room to spare, so it
    # stayed the same height even with the wrapping guard removed — the
    # sabotage passed unnoticed until this was measured at 360.
    nb, na = int(got.get("narrowbefore", 0)), int(got.get("narrowafter", -1))
    t.ok(nb > 10, "the narrow measurement really rendered (%dpx)" % nb)
    t.eq(na, nb,
         "and at a phone width the row still does not grow (%dpx)" % nb)

    # ---- and the meta line stays one line ------------------------------
    # A SOURCE assertion, deliberately, and it is honest about what it covers.
    # The measurement above proves the STALE case: both rows carry the same
    # technical tail, so if that tail wraps they grow together and the
    # comparison stays equal. What keeps a row one line tall when the tail
    # itself is long is this rule, and nothing above can see it — removing it
    # passed every measurement here.
    page = (F.HUB / "web" / "hub.html").read_text(encoding="utf-8",
                                                  errors="replace")
    rule = re.search(r"\.mod \.ip\{[^}]*\}", page, re.S)
    t.ok(rule, "the row's meta line has a rule of its own")
    if rule:
        for prop in ("white-space:nowrap", "overflow:hidden", "min-width:0"):
            t.contains(rule.group(0), prop,
                       "and keeps it to one line (%s)" % prop)
