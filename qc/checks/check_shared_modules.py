"""A module on another PC's cable can be seen and driven from this hub.

At a venue this is the normal setup: one laptop beside the arm, one at the
desk, and the arm reachable only from whichever machine holds the cable. Before
this, the other PC's modules were simply invisible from here.

The rule that makes it safe is that ownership never moves. The hub holding the
cable stays its only owner; this hub forwards the whole request to it, and that
hub opens its own port exactly as it always did. So there is never a second
program fighting for one serial handle — the thing the whole port-sharing
design exists to prevent.

What is asserted here:
  * a hub: address is parsed, and REFUSES to be chained (the loop),
  * parse_dev will not take one apart locally,
  * a forwarded request is marked so it cannot be forwarded again,
  * this hub tells other hubs what it holds, cheaply,
  * a PC that has gone away is reported as UNREACHABLE, never as empty,
  * and the page has all five states for that list.

Note on what is NOT covered: real hub-to-hub forwarding needs two hubs in two
processes, because `main.PORT` is a module global and QC starts both hubs in
one process. The forwarding path is exercised here only against a dead address.
"""
import json
import urllib.error
import urllib.parse
import urllib.request

import fake_serial
import qc as F

AREA = "sharing"
TITLE = "modules on another PC show up here, and cannot loop"


def get(url, timeout=8, headers=None):
    # This check needs custom headers (X-Mice-Forwarded), so it cannot simply
    # call F.get — but it MUST still carry the session, or every gated route
    # answers 401 and the check reads that as the module being unreachable.
    req = urllib.request.Request(url, headers=headers or {})
    F._with_cookie(req)                       # noqa: SLF001 - one place owns the session
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read().decode(errors="replace")


def run(t):
    fake_serial.reset()
    base, main = F.start_hub()
    src = (F.CODE / "main_python/main.py").read_text(encoding="utf-8",
                                                     errors="replace")

    # ---- the address format ---------------------------------------------
    ip, inner = main.split_hub_dev("hub:10.0.0.5/usb:COM7")
    t.eq(ip, "10.0.0.5", "a hub address names the PC that holds the cable")
    t.eq(inner, "usb:COM7", "and carries that PC's own address for the module")

    ip2, inner2 = main.split_hub_dev("usb:COM7")
    t.eq(ip2, None, "an ordinary address is left alone")
    t.eq(inner2, "usb:COM7", "and passes through unchanged")

    # THE loop. Two hubs that each list the other could otherwise bounce one
    # command back and forth until both ran out of request threads.
    try:
        main.split_hub_dev("hub:10.0.0.5/hub:10.0.0.6/usb:COM7")
        t.ok(False, "a hub address cannot be chained through a third PC")
    except ValueError as e:
        t.ok(True, "a hub address cannot be chained through a third PC (%s)"
             % str(e)[:40])

    # A forwarded address must never be taken apart locally, or this hub would
    # try to open a COM port name that belongs to a different machine.
    try:
        main.parse_dev("hub:10.0.0.5/usb:COM7")
        t.ok(False, "parse_dev refuses a forwarded address")
    except ValueError:
        t.ok(True, "parse_dev refuses a forwarded address")

    t.contains(src, "X-Mice-Forwarded",
               "a forwarded request is marked, so it cannot be forwarded again")

    # ---- what this hub holds --------------------------------------------
    st, body = get(base + "/api/mine")
    t.eq(st, 200, "a hub says what it holds on its own cables")
    mine = json.loads(body)
    t.ok(mine.get("ok") is True, "and answers ok")
    t.ok(bool(mine.get("host")), "naming which PC it is, so a row can say where")
    t.ok(isinstance(mine.get("modules"), list), "with a list of modules")
    devs = [m.get("dev", "") for m in mine.get("modules") or []]
    t.ok(any(d.startswith("usb:") for d in devs),
         "the fake cable's module is in it",
         "got %r" % (devs,))
    # It must stay CHEAP: another hub calls this every few seconds, and forcing
    # a fresh probe here would keep every cable permanently busy.
    t.ok("probe_usb_all(False)" in src,
         "it reuses the cached probe rather than re-opening every port")

    # ---- forwarding to OURSELVES is short-circuited ----------------------
    # Every address in 127.0.0.0/8 is loopback, so hub:127.0.0.2 used to travel
    # out over HTTP and come straight back to this same hub, which then served
    # it from the fake cable and answered PONG. It worked, which is exactly why
    # it was worth catching: a hop that is not a hop, burning a request thread.
    # Asserting only that the reply is PONG proves NOTHING here: a forward to
    # ourselves also comes back PONG. To tell "handled locally" from "went out
    # and came back", point the forward port at something nothing listens on.
    # With the short-circuit the request never leaves, so PONG still arrives;
    # without it, the forward is refused. Verified by disabling the fix and
    # watching this fail.
    me = "hub:127.0.0.2/usb:" + fake_serial.PORT
    real_port = main.PORT
    main.PORT = 9   # discard: reserved, nothing serves HTTP there
    try:
        st, reply = get(base + "/api/dev/cmd?dev=" + urllib.parse.quote(me)
                        + "&c=PING", timeout=15)
    except urllib.error.HTTPError as e:
        st, reply = e.code, e.read().decode(errors="replace")
    except Exception as e:                      # noqa: BLE001
        st, reply = 0, str(e)
    finally:
        main.PORT = real_port
    t.ok("PONG" in reply,
         "an address that is really this PC is handled here, not forwarded out",
         "got %s: %r — it left the machine instead of being served locally"
         % (st, reply[:120]))

    # ---- a PC that has gone away ----------------------------------------
    # 192.0.2.0/24 is TEST-NET-1, reserved by RFC 5737 and guaranteed not to be
    # a real host — unlike 127.0.0.2, which is us. "Could not reach that PC" and
    # "that PC holds nothing" are different facts, and showing the second when
    # the first is true is the page stating something untrue.
    dead = "hub:192.0.2.1/usb:COM99"
    try:
        st, reply = get(base + "/api/dev/cmd?dev=" + urllib.parse.quote(dead)
                        + "&c=PING", timeout=25)
    except urllib.error.HTTPError as e:
        st, reply = e.code, e.read().decode(errors="replace")
    except Exception as e:                      # noqa: BLE001
        st, reply = 0, str(e)
    t.ok("could not reach" in reply.lower() or st >= 400,
         "a PC that has gone away is reported as unreachable, not as empty",
         "got %s: %r" % (st, reply[:160]))

    # ---- the list of everything, including other PCs ---------------------
    st, body = get(base + "/api/allmods", timeout=40)
    t.eq(st, 200, "the hub can list modules across every PC it can see")
    allm = json.loads(body)
    t.ok(isinstance(allm.get("modules"), list), "with a module list")
    t.ok(isinstance(allm.get("errors"), list),
         "and a per-PC error list, so one closed laptop does not empty the page")

    # ---- the page, in all five states ------------------------------------
    hub = (F.CODE / "main_python/web/hub.html").read_text(encoding="utf-8",
                                                          errors="replace")
    t.contains(hub, "/api/allmods", "the hub page asks for other PCs' modules")
    i = hub.find("async function loadShared")
    fn = hub[i:hub.find("\n// ----", i)] if i >= 0 else ""
    t.ok(i >= 0, "the hub page has the shared-modules list")
    t.contains(fn, "Looking for other PCs", "loading says what it is doing")
    t.contains(fn, "No other PCs", "empty says what would fill it")
    t.contains(fn, "Could not check", "error says what failed")
    t.contains(fn, "Try again", "and offers the control that retries")
    t.contains(fn, "did not answer",
               "a PC that did not answer is named, not silently dropped")
    t.contains(fn, "sharedBusy",
               "and overlapping sweeps are guarded — this walks the subnet")
