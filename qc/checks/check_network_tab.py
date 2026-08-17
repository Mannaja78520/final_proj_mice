"""The hub's Network tab, driven in a real browser.

`check_groups` reads the source and proves the RULES are right. This proves the
PAGE works: that clicking Network really shows it, that it lists the modules it
can find, and that ticking one and naming a group sends `GROUP <name>` to that
module — and to nothing else.

That last part is the whole point of the screen. Two companies can be working
the same site; linking a module you did not pick is the failure this exists to
catch, and no amount of source-reading can tell you which checkbox a click
acted on.

The hub page is loaded in an iframe from the hub's own origin (same trick
check_responsive uses), so its relative /api calls work, and what reached the
module is read off the WIRE rather than off the page's opinion of itself.
"""
import browser
import fake_serial
import qc as F

AREA = "network"
TITLE = "the hub's Network tab links only the modules you pick"
SLOW = True

PAGE = """
<style>html,body{margin:0}#f{width:1100px;height:900px;border:0}</style>
<iframe id="f" src="/"></iframe>
<script>
function done(s){ qcMark("NET " + s); qcMark("done"); }
setTimeout(function(){
  try{
    var d = document.getElementById('f').contentDocument;
    var out = [];
    var btn = d.querySelector('#tabs .tab[data-go="network"]');
    out.push("tabbtn=" + (btn ? "yes" : "no"));
    var card = d.querySelector('[data-tab="network"]');
    out.push("hiddenfirst=" + (card && card.style.display === "none" ? "yes" : "no"));
    if (btn) btn.click();
    setTimeout(function(){
      out.push("shown=" + (card && card.style.display !== "none" ? "yes" : "no"));
      // switching tabs may only HIDE — the module lists are live and must survive
      out.push("modskept=" + (d.getElementById("mods") ? "yes" : "no"));
      out.push("usbkept=" + (d.getElementById("usbmods") ? "yes" : "no"));
      setTimeout(function(){
        var boxes = d.querySelectorAll("#netlist input[type=checkbox]");
        out.push("rows=" + boxes.length);
        if (boxes.length) {
          boxes[0].checked = true;
          boxes[0].dispatchEvent(new Event("change", {bubbles:true}));
          var f = d.getElementById("grpname");
          out.push("form=" + (f ? "yes" : "no"));
          if (f) {
            f.value = "qcgroup";
            d.querySelector("#netact button").click();
          }
        }
        setTimeout(function(){ done(out.join(" ")); }, 5000);
      }, 6000);
    }, 800);
  } catch (e) { done("ERR=" + String(e).slice(0, 60)); }
}, 3500);
</script>
"""


def run(t):
    if not browser.available():
        t.ok(False, "headless Edge is available for browser checks")
        return
    fake_serial.reset()
    base, main = F.start_hub()
    # Silence the REAL network sweep for this check. Without it the tab lists
    # whatever modules happen to be on the developer's LAN, the click lands on
    # one of THOSE, and the check both flakes and reconfigures real hardware.
    # Everything here must come from the fake module on COM99.
    # The WiFi sweep is silenced so the tab lists the fake module on COM99 and
    # not whatever is on the developer's LAN. Stubbing the CABLE side as well
    # was tried and made it worse: the stubbed port list has no identity, so
    # the tab found nothing to link and the check proved less, not more.
    real_scan = main.scan_modules
    main.scan_modules = lambda force=False: []
    try:
        browser.raw_page(PAGE, base, seconds=32)
    finally:
        main.scan_modules = real_scan

    marks = [m for m in fake_serial.qc_marks if m.startswith("NET ")]
    if not t.ok(marks, "the Network tab reported back",
                "the page never ran: %r" % (fake_serial.qc_marks[-3:],)):
        return
    got = dict(kv.split("=", 1) for kv in marks[-1][4:].split(" ") if "=" in kv)
    if "ERR" in got:
        t.ok(False, "the page ran without throwing", got["ERR"])
        return

    t.eq(got.get("tabbtn"), "yes", "there is a Network tab to click")
    t.eq(got.get("shown"), "yes", "clicking it shows the Network area")
    t.eq(got.get("modskept"), "yes",
         "and does not destroy the module list")
    t.eq(got.get("usbkept"), "yes", "nor the USB list")
    t.ok(int(got.get("rows", "0")) >= 1,
         "it lists the modules it can find (%s)" % got.get("rows"),
         "the tab found nothing, so nothing could be linked")
    t.eq(got.get("form"), "yes", "picking a module offers a group name")

    # ---- what actually went down the wire ------------------------------
    sent = [c for _, c in fake_serial.wire if c.upper().startswith("GROUP")]
    if t.ok(sent, "a GROUP command reached the module",
            "the Link button did nothing at all"):
        t.contains(sent[-1], "qcgroup", "carrying the group that was typed")
    # exactly one box was ticked, so exactly one module may have been told.
    # Linking one you did not pick is how another company's board would end up
    # inside the installation.
    t.ok(len(sent) == 1,
         "and ONLY the module that was ticked was linked",
         "%d modules were told to join, but one was selected" % len(sent))
