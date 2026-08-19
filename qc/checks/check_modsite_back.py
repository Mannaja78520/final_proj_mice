"""A board's own page can get back to the hub - when it knows where the hub is.

Opening a module's website is otherwise a one-way trip. Through the hub there
is at least a browser Back button; typed straight into a phone there is nothing
at all, and the hub is the only screen that shows the other modules.

The trap is guessing. Several PCs at a venue run this same hub, addresses move
with the network, and a link to the WRONG one is worse than no link: it lands
someone on a stranger's control panel and they start pressing things. So the
link only ever appears when the address is known to be right, and there are
exactly two such cases:

  * reached THROUGH the hub, where the page is already being served by it, so
    `/` is right by construction;
  * reached directly, where the board offers the hub that last identified
    itself - the hub sends X-Mice-Hub on every request it makes - and offers
    nothing at all when none has.

The third case is the one worth having a check for: no hub has been in touch,
and the page must show nothing rather than a hopeful guess.
"""
import urllib.parse

import browser
import fake_serial
import qc as F

AREA = "modsite"
TITLE = "the board page can get back to the hub"
SLOW = True

DRIVER = """
<style>html,body{margin:0}#f{width:1100px;height:900px;border:0}</style>
<iframe id="f" src="%s"></iframe>
<script>
function done(s){ qcMark("BK " + s); qcMark("done"); }
setTimeout(async function(){
  try{
    var w = document.getElementById('f').contentWindow;
    var d = document.getElementById('f').contentDocument;
    if (typeof w.showHubLink !== 'function') return done("missing=showHubLink");
    var a = d.getElementById('hubBack');
    if (!a) return done("missing=hubBack");
    var out = [];

    // As the page really is right now: opened through the hub.
    out.push("hub_shown=" + (a.hidden ? "no" : "yes"));
    out.push("hub_href=" + (a.getAttribute('href') || 'none'));

    // Now pretend it was typed straight into a browser. viaHub() reads the
    // query string, so it is replaced rather than the URL rewritten.
    var realVia = w.viaHub;
    w.viaHub = function(){ return false; };

    w.showHubLink({});                       // no hub has ever spoken to it
    out.push("alone=" + (a.hidden ? "hidden" : "shown"));

    w.showHubLink({hub: '10.0.0.4:9203'});   // a hub has
    out.push("direct=" + (a.hidden ? "hidden" : "shown"));
    out.push("dhref=" + (a.getAttribute('href') || 'none'));
    out.push("says=" + (a.textContent || '').replace(/[^A-Za-z0-9.:]+/g, "_"));

    w.viaHub = realVia;
    done(out.join(" "));
  } catch (e) { done("ERR=" + String(e).replace(/[^A-Za-z0-9=]+/g, "_").slice(0,50)); }
}, 6000);
</script>
"""


def run(t):
    if not browser.available():
        t.give_up("headless Edge not found - install Edge or run --quick")
    fake_serial.reset()
    base, _main = F.start_hub()
    url = "/mod?dev=usb%3A" + urllib.parse.quote(fake_serial.PORT)
    browser.raw_page(DRIVER % url, base, seconds=35)

    got = {}
    for m in fake_serial.qc_marks:
        if m.startswith("BK "):
            for part in m[3:].split(" "):
                k, _, v = part.partition("=")
                got[k] = v
    if not t.ok(got, "the board page reported back",
                "%r" % (fake_serial.qc_marks[-3:],)):
        return

    t.eq(got.get("hub_shown"), "yes",
         "opened through the hub, the way back is offered")
    t.eq(got.get("hub_href"), "/",
         "and it points at the hub serving the page, which cannot be wrong")

    t.eq(got.get("alone"), "hidden",
         "a board no hub has spoken to offers no way back")
    t.eq(got.get("direct"), "shown",
         "one that a hub HAS spoken to offers it")
    t.eq(got.get("dhref"), "http://10.0.0.4:9203/",
         "pointing at that hub, on the address it gave")
    t.contains(got.get("says", ""), "10.0.0.4",
               "and it names the PC, because several run this same hub")

    # ---- the two halves that make the address trustworthy -----------
    # The hub says who it is on every request it makes...
    main_py = (F.HUB / "main.py").read_text(encoding="utf-8")
    t.contains(main_py, "X-Mice-Hub",
               "the hub identifies itself when it talks to a board")
    t.contains(main_py, "def hub_header",
               "from one place, so its two callers cannot disagree")
    for caller in ("def probe_module", "def robot_get"):
        i = main_py.find(caller)
        t.contains(main_py[i:i + 500], "hub_header",
                   "and %s carries it" % caller.split()[1])

    # ...and the board keeps it only while it is still true. This part runs on
    # the ESP32 and cannot be driven from a PC, so it is held to the source.
    portal = (F.FIRMWARE / "src" / "core" / "WebPortal.cpp").read_text(encoding="utf-8")
    t.contains(portal, "noteHub", "the board records the hub that spoke to it")
    i = portal.find("String WebPortal::lastHub")
    t.contains(portal[i:i + 300], "HUB_TTL_MS",
               "and forgets it after a while, so a PC that left is not linked to")
    j = portal.find("void WebPortal::noteHub")
    t.contains(portal[j:j + 700], "isalnum",
               "what arrives in that header is checked before it becomes a link")
