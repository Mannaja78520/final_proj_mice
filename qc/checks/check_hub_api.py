"""The hub's own surface: the pages it serves and the endpoints Studio needs.

Includes the one text-parsing rule that broke pin config over USB while WiFi
worked — a class of bug that is invisible unless you assert on it.
"""
import json
import re

import qc as F

AREA = "hub"
TITLE = "hub pages and API"
SLOW = False


def run(t):
    base, main = F.start_hub()

    # ---- the OLD USB page is gone, and its URL still works ----------
    # main_python/web/module.html was a second module page: 295 lines, six
    # cards duplicated from the module's real website, and 8 joint sliders
    # where a nong has 10 — WAIST and SHRUG were unreachable through it. It had
    # already been reduced to a JavaScript redirect that nothing linked to.
    #
    # Deleting a page is only safe if the links people kept still land
    # somewhere. ?port=/&id= was its addressing; /mod speaks dev=usb:PORT:ID.
    t.ok(not (F.HUB / "web" / "module.html").exists(),
         "there is no second module page",
         "two pages for one module is how they drifted apart the first time")

    conn = F.raw_get(base + "/module.html?port=COM99&id=2&name=arm")
    t.eq(conn[0], 302, "an old /module.html link still answers")
    t.eq(conn[1], "/mod?dev=usb%3ACOM99%3A2&name=arm",
         "and lands on the module's real website, on the same port and id")
    # ...and with no port there is nothing to open, so it goes home rather
    # than to a page addressed at nothing — which is what the old file did.
    t.eq(F.raw_get(base + "/module.html")[1], "/",
         "a bare /module.html goes to the hub, not to an empty module page")

    # ---- the pages a user actually opens ----------------------------
    # `must` is looked for anywhere in the body — app.js opens with a long
    # comment header, so checking only the first bytes proves nothing
    for path, must in (("/", "<html"),
                       ("/mod?dev=usb:COM99", "<html"),
                       ("/studio/", "<html"),
                       ("/studio/app.js", "function applyPose"),
                       ("/pinout.svg", "<svg")):
        s, b = F.get(base + path)
        t.eq(s, 200, "serves %s" % path)
        t.contains(b.lower(), must.lower(), "%s has real content" % path)

    # the module site is the ESP32's OWN html plus the transport shim, so the
    # same page works over WiFi and USB — if the shim is missing, /api/* calls
    # from that page go nowhere
    s, b = F.get(base + "/mod?dev=usb:COM99")
    t.contains(b, "/api/dev/", "the module page carries the transport shim")

    # ---- studio storage endpoints -----------------------------------
    s, b = F.get(base + "/api/list?kind=projects")
    t.eq(s, 200, "/api/list answers")
    t.ok(json.loads(b).get("ok"), "/api/list is well-formed", b[:150])

    # ---- LOG-LINE FILTER. A firmware log line is a bracket TAG, but a JSON
    # array reply also starts with "[". Treating those the same made pin
    # config say "unsupported" over USB while WiFi worked, and the same bug
    # existed in three places. Assert the rule directly.
    log = main._LOG_LINE
    for line in ("[wifi] connected", "[sd] mounted", "[  1234][I] boot"):
        t.ok(log.match(line), "log line skipped: %r" % line)
    for line in ('[{"gpio":13}]', '["wave.yaml"]', "[[1,2]]", '[1,2]'):
        t.ok(not log.match(line), "JSON kept, not mistaken for a log: %r" % line)

    # the same rule must hold in Studio's own serial reader
    app = (F.STUDIO_WEB / "app.js").read_text(encoding="utf-8", errors="replace")
    t.ok(re.search(r"\^\\\[\[\\w \]\*\\\]", app) or "[\\w ]*\\]" in app,
         "studio's serial reader uses the same bracket-TAG rule",
         "a bare line.startsWith('[') would eat JSON array replies")

    # ---- dev API covers every transport the module page needs -------
    for what in ("cmd", "status", "files"):
        s, b = F.get("%s/api/dev/%s?dev=usb:COM99&c=INFO&dir=/moves" % (base, what))
        t.eq(s, 200, "/api/dev/%s works over USB" % what)

    # ---- a bad dev string must not 500 ------------------------------
    s, b = F.get(base + "/api/dev/status?dev=nonsense:1")
    t.ok(s >= 400, "a bad dev string is rejected cleanly")
    t.ok("error" in b.lower(), "and explains itself", b[:150])
