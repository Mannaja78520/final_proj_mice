"""The hub hands its own program to the PC beside it, and updates from it too.

Asked 2026-08-21, from the right question: *can this hub access the usb from the
pc that connect to the hub?* It cannot, at any address. A browser sends HTTP
requests; it has no way to give a remote server the local machine's serial
ports. Web Serial hands them to the PAGE, and only in a secure context, so from
a LAN address it does not exist either.

So the PC with the cable has to run something itself - and that something is
this program. The two things worth building were therefore not a new protocol
but a way to GET it there and keep it current:

  * **a download link**, so a PC that has just opened this page over WiFi can
    take the app off the hub instead of finding a USB stick or the internet;
  * **updating from a hub on the same network.** GitHub is the right source
    when there is internet and the wrong one on show day, when there is none.
    The hub on the next desk is reachable either way.

What is guarded:

  * a hub with no app to give does NOT offer the link - a download that 404s is
    worse than no download;
  * the version endpoint says a size and a sha and nothing else;
  * the updater fetches from whatever source it CHOSE, so preferring the nearer
    hub is not undone by a hard-coded URL;
  * and a hub never offers itself, which would be a loop with extra steps.
"""
import json
import re

import qc as F

AREA = "hub"
TITLE = "the hub hands its app to another PC, and can update from one"


def run(t):
    src = (F.HUB / "main.py").read_text(encoding="utf-8")
    hub = (F.HUB / "web" / "hub.html").read_text(encoding="utf-8")

    # ---- only offered when there IS one ------------------------------
    fn = src[src.find("def app_here():"):]
    fn = fn[:fn.find("\ndef ", 1)]
    t.contains(fn, 'getattr(sys, "frozen", False)',
               "a hub running from source has no app to hand out")
    t.contains(fn, "exe.is_file()",
               "and a missing file is not offered either")

    import fake_serial
    fake_serial.reset()
    base, _m = F.start_hub()

    code, body = F.get(base + "/api/app/version")
    t.eq(code, 200, "the version endpoint answers")
    d = json.loads(body)
    # QC runs from source, so this is the branch under test here.
    t.eq(d.get("bytes"), 0, "a source checkout reports no app")
    t.contains(d.get("why", ""), "from source", "and says why")

    code, _b = F.get(base + "/api/app")
    t.eq(code, 404, "and the download refuses cleanly rather than serving junk")

    # ---- the page hides the link when there is nothing to give -------
    paint = hub[hub.find("async function paintGetApp()"):]
    paint = paint[:paint.find("\n// ---- updating")]
    t.contains(paint, "a.hidden = true",
               "the page hides the link when the hub has no app")
    t.ok(paint.count("a.hidden = true") >= 2,
         "including when the request itself fails",
         "a link that 404s is worse than no link - it looks like the feature "
         "is broken rather than absent")
    t.contains(hub, 'download="MiceHub.exe"',
               "and the link downloads rather than navigating")

    # ---- updating from a hub on the same network ---------------------
    off = src[src.find("def hub_offers():"):]
    off = off[:off.find("\ndef ", 1)]
    t.contains(off, "scan_hubs(",
               "it asks the hubs this PC can already see")
    t.contains(off, "is_self(ip)",
               "and never offers itself",
               )
    t.ok("continue" in off,
         "a hub that does not answer is skipped, not an error",
         "a closed laptop on the venue WiFi is normal")
    t.contains(off, "/api/app/version",
               "asking each one what build it runs")

    st = src[src.find("def update_state():"):]
    st = st[:st.find("\ndef ", 1)]
    t.contains(st, "hub_offers()",
               "the update check considers the network as well as GitHub")
    i_git = st.find("APP_API")
    i_near = st.find("hub_offers()")
    t.ok(0 < i_git < i_near,
         "GitHub first, then the network as the better source when it is newer")
    t.contains(st, '"from":',
               "and it records WHERE the chosen build comes from")

    # THE ONE THAT WOULD UNDO IT ALL. Choosing a nearer source means nothing if
    # the download ignores the choice.
    do = src[src.find("def do_update():"):]
    do = do[:do.find("\ndef ", 1)]
    t.contains(do, 'st.get("from")',
               "the download uses the source that was chosen")
    t.ok(re.search(r"urlopen\(where", do),
         "and fetches from it, not from a fixed URL",
         "preferring the hub next door is pointless if the fetch still goes to "
         "GitHub - which is exactly the machine that has no internet")
    t.contains(do, "APP_RAW",
               "with GitHub still the fallback when nothing nearer was found")
