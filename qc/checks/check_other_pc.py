"""A module on ANOTHER PC's cable can be driven, from the hub and from Studio.

Asked at the bench 2026-08-20: *we still can't go to open module or command the
module which connect to the other pc*. At a venue that is the normal case - one
laptop by the arm, one at the desk, and the arm reachable only from whichever
machine holds the cable.

`/api/allmods` already asks every hub and returns each module with
`dev = hub:<ip>/<inner>`, and `split_hub_dev` forwards it. The hub page used
that. **Studio did not**, and the way it failed is the dangerous kind: its
`?dev=` parser tested `addr.indexOf("usb:") === 0`, which a `hub:10.0.0.5/usb:COM7`
never matches, and `moduleDev()` rebuilt the address from a bare COM port. So a
module chosen on another PC was driven as a LOCAL port of the same name -
whatever happened to be plugged into this machine's COM7. The wrong robot
moves, and nothing says so.

Held here:

  * the prefix is split off on the way IN, so the usb:/wifi: tests match;
  * `moduleDev()` puts it back on, so every command carries it;
  * both command paths use the unified endpoint when it is present -
    `/api/usb/cmd` only ever means a port on THIS PC;
  * and a forwarded dev cannot be forwarded again, which would let two hubs
    that list each other bounce one command until both ran out of threads.
"""
import re

import qc as F

AREA = "connection"
TITLE = "a module on another PC's cable can be commanded, from the hub and Studio"


def run(t):
    app = (F.CODE / "nong" / "main_python_set_nong" / "web" / "app.js").read_text(
        encoding="utf-8", errors="replace")
    main = (F.HUB / "main.py").read_text(encoding="utf-8")

    # ---- the hub still forwards, and refuses a second hop ------------
    split = main[main.find("def split_hub_dev(dev):"):]
    split = split[:split.find("\ndef ", 1)]
    t.contains(split, 'dev.startswith("hub:")', "the hub understands hub: devs")
    t.contains(split, "cannot be reached through a third PC",
               "and refuses to forward a forwarded one",
               )
    t.ok('inner.startswith("hub:")' in split,
         "checked on the INNER address, which is the one that would loop",
         "two hubs that each list the other would bounce one command back and "
         "forth until both ran out of request threads")

    # ---- Studio splits the prefix off on the way in ------------------
    t.contains(app, "window.HUB_VIA",
               "Studio remembers which PC the module belongs to")
    boot = app[app.find('const dev = qp.get("dev")'):]
    boot = boot[:boot.find("// IK self-test")]
    t.contains(boot, 'inner.indexOf("hub:") === 0',
               "it splits the hub prefix off the dev it was opened with")
    # The tests below it must look at the INNER address. Testing the whole
    # string is how this failed: neither branch matched and Studio silently
    # stayed on whatever was already connected.
    t.contains(boot, 'inner.indexOf("usb:") === 0',
               "and the usb test runs on the inner address")
    t.contains(boot, 'inner.indexOf("wifi:") === 0',
               "as does the wifi test")
    t.ok('addr.indexOf("usb:") === 0' not in boot,
         "never on the whole string",
         "hub:10.0.0.5/usb:COM7 does not start with usb:, so that test fails "
         "and the module is never connected to at all")
    t.ok("bits = inner.slice(4)" in boot,
         "and the port name comes from the inner address",
         "slicing the whole string gives a port called 10.0.0.5/usb:COM7")

    # ---- and it puts the prefix back on every command ----------------
    dev_fn = app[app.find("function moduleDev()"):]
    dev_fn = dev_fn[:dev_fn.find("\n}") + 2]
    t.contains(dev_fn, "window.HUB_VIA",
               "moduleDev puts the hub prefix back on")
    for line in re.findall(r"return via \+ \"(usb|wifi):", dev_fn):
        t.ok(True, "the %s address carries it" % line)
    t.eq(len(re.findall(r"return via \+", dev_fn)), 2,
         "both the cable and the WiFi address carry it")

    # THE ONE THAT MOVES THE WRONG ROBOT. /api/usb/cmd takes a bare port name
    # and can only ever mean a port on this machine.
    for fn_name in ("hubUsbCmd", "httpCmd"):
        fn = app[app.find("async function %s(c)" % fn_name):]
        fn = fn[:fn.find("\n}") + 2]
        t.contains(fn, "window.HUB_VIA",
                   "%s notices a module on another PC" % fn_name)
        t.contains(fn, "moduleDev()",
                   "and sends the whole dev, not a rebuilt one")
        # Comments out first. The comment above this code names the endpoint it
        # is warning about, so an ordering test on the raw text compares a
        # sentence with a line of code - and fails on correct code.
        code = re.sub(r"//.*", "", fn)
        i_via = code.find("window.HUB_VIA")
        i_local = code.find("/api/usb/cmd" if fn_name == "hubUsbCmd"
                            else "/api/robot/cmd")
        t.ok(i_local < 0 or i_via < i_local,
             "with the local endpoint only as the fallback (%s)" % fn_name,
             "/api/usb/cmd names a bare port, which is always a port on THIS "
             "PC - a module on another machine would be answered by whatever "
             "is plugged in here under the same name")

    # ---- the hub page still uses allmods -----------------------------
    hub = (F.HUB / "web" / "hub.html").read_text(encoding="utf-8")
    t.contains(hub, "/api/allmods",
               "the hub page lists every PC's modules")
    t.contains(main, 'm["dev"] = "hub:%s/%s"',
               "and the route stamps each one with the PC it belongs to")
