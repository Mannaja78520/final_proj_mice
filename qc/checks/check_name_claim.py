"""Two hubs never both answer to `mice.local` - the second takes its own name.

Asked on 2026-08-19, once a second PC was on the same WiFi: what happens when
two hubs are up? Nothing good, and nothing loud. mDNS has no arbitration - both
machines answer the same lookup and the FIRST reply back wins that one lookup.
So `mice.local` reaches one PC now and the other in a minute, with no error
anywhere. Adding the port does not help; the port was never the ambiguous part.

The fix is the standard one: ask before claiming. A hub probes for its own name
first, and a hub that hears an answer takes `mice-<this-pc>.local` instead and
says so. Every hub is still a front door - it forwards to whichever one owns the
cable - so a name that lands on the "wrong" hub costs nothing.

This check drives the probe for real over the network rather than reading the
source, because the first version of this feature PASSED a source check while
being completely inert: the query was leaving on the Radmin VPN adapter, so
nobody ever answered it and every hub cheerfully claimed the same name. What
had to be tested was that a name someone else holds is actually SEEN to be held.
"""
import os
import sys
import time

import qc as F

AREA = "hub"
TITLE = "a second hub takes its own name instead of fighting for mice.local"


def run(t):
    sys.path.insert(0, str(F.HUB))
    import main   # noqa: PLC0415 - the modules under test
    import mdns   # noqa: PLC0415

    ip = main.lan_ip()
    if not t.ok(ip and not ip.startswith("127."),
                "this PC is on a network the probe can use",
                "lan_ip() said %r - mDNS needs a real address" % (ip,)):
        return

    # A name nothing else can be holding, so a real hub on this machine or on
    # the venue WiFi cannot make this pass or fail by accident.
    name = "mice-qc-%d-%d.local" % (os.getpid(), int(time.time()) % 10000)
    probe = mdns.Responder(name, lambda: ip)

    # ---- nobody holds it -------------------------------------------
    t.ok(not probe.taken(wait=0.9),
         "a name nobody answers is reported free",
         "taken() said %r for a name invented one line ago; if this is ever "
         "true every hub renames itself for no reason" % (probe.taken(wait=0.2),))

    # ---- somebody holds it -----------------------------------------
    holder = mdns.Responder(name, lambda: ip)
    if not t.ok(holder.start(), "a responder can hold the name",
                "port 5353 may be held by Bonjour: %s" % holder.error):
        return
    try:
        time.sleep(0.3)
        who = probe.taken(wait=2.0)
        t.ok(who, "a name that IS answered is seen to be taken",
             "taken() returned %r while a responder was answering that exact "
             "name on %s - this is the whole feature, and it silently returned "
             "nothing until the socket was pinned to the right adapter"
             % (who, ip))
    finally:
        holder.stop.set()
        if holder.sock:
            holder.sock.close()

    # ---- and the hub acts on the answer -----------------------------
    src = (F.HUB / "main.py").read_text(encoding="utf-8")
    i = src.find("    own_name = ")
    block = src[i:i + 1600]
    code = "".join(l for l in block.splitlines(True) if not l.strip().startswith("#"))
    t.contains(code, ".taken()",
               "the hub asks before it claims the shared name")
    t.contains(code, "gethostname",
               "and falls back to a name made from THIS PC")
    t.ok("already answered by" in code,
         "it says out loud which name it ended up with",
         "a hub that quietly renames itself is worse than one that clashes - "
         "the operator types the name that was printed at startup")

    # The banner and /api/mine must report the name actually claimed. Printing
    # the constant would tell the operator to type a name this hub does not
    # answer to, which is the same bug wearing a different hat.
    t.ok("NAME_SERVER[0].name" in src or "ns.name" in src,
         "the startup banner shows the name this hub really answers to")
    t.ok('"%s.local"' not in src.split("def hub_banner")[-1][:600]
         if "def hub_banner" in src else True,
         "and does not hardcode the shared one")

    # ---- a hub that retreats at STARTUP can still come back ---------
    # Found 2026-08-19 while checking a panel finding. The startup path used to
    # build a SECOND responder for the long name, and a fresh responder WANTS
    # the name it was made with - so that hub could never reclaim mice.local,
    # while a hub that retreated a minute later could. Two paths, two
    # behaviours, nothing saying so.
    r = mdns.Responder(main.MDNS_NAME, lambda: ip, fallback="mice-x.local")
    r.name = "mice-x.local"                  # what the startup retreat does
    t.eq(r.wanted, main.MDNS_NAME,
         "a hub that stepped aside still WANTS the short name")
    j = src.find("is already answered by")
    after = src[j:j + 700]
    t.ok("mdns.Responder(" not in after,
         "and the startup retreat renames the responder it already has",
         "building a new one resets what it wants, so the short name is never "
         "taken back when the other PC leaves")

    # ---- a deaf hub never reclaims -----------------------------------
    # All five panel models raised this on 2026-08-19 and they were right: a
    # probe silenced by a firewall or by client isolation looks exactly like a
    # name nobody holds. Reclaiming on that evidence takes a name the other hub
    # is still answering, on the one network where the clash rule is also deaf.
    deaf = mdns.Responder(main.MDNS_NAME, lambda: ip, fallback="mice-y.local")
    deaf.name = "mice-y.local"
    deaf.heard = 0                     # nothing has ever arrived on 5353
    deaf._quiet = 5                    # and it has been quiet a long time
    deaf._reclaim()
    t.eq(deaf.name, "mice-y.local",
         "a hub that hears no mDNS at all keeps its own name")
    t.eq(deaf._quiet, 0,
         "and its run of silence is not allowed to accumulate")

    # ---- the interface pin, which is what made it work --------------
    m = (F.HUB / "mdns.py").read_text(encoding="utf-8")
    t.eq(m.count("IP_MULTICAST_IF"), 2,
         "both the probe and the responder go out the hub's own adapter")
    j = m.find("def taken")
    t.ok("who[0] != mine" not in m[j:j + 2000],
         "any answer counts as taken, not only one from another address",
         "two hubs on ONE machine share an IP - filtering by address made the "
         "only reproducible test of this feature pass while doing nothing")

    # ---- a clash that turns up LATER is settled the same way ---------
    # The startup probe cannot see a PC that is switched off, and on this WiFi
    # both machines drop in turn (reported 2026-08-19). So the responder also
    # listens: an ANSWER carrying our name from another address is a clash, and
    # the lower address keeps the name. Both sides run the same comparison on
    # the same two numbers, so they agree without talking.
    r = mdns.Responder("mice.local", lambda: "10.0.0.20", fallback="mice-pc.local")
    r._clash("10.0.0.9")                     # they are lower - we yield
    t.eq(r.name, "mice-pc.local", "the higher address gives up the shared name")

    r2 = mdns.Responder("mice.local", lambda: "10.0.0.9", fallback="mice-pc.local")
    r2._clash("10.0.0.20")                   # we are lower - we keep it
    t.eq(r2.name, "mice.local", "and the lower address keeps it")

    # The comparison is on the four BYTES, not on the text. As strings
    # "10.0.0.9" > "10.0.0.20", so a text compare makes both machines think
    # they lost - or both think they won - and the name swaps forever.
    a = mdns.Responder("mice.local", lambda: "10.0.0.9", fallback="mice-a.local")
    b = mdns.Responder("mice.local", lambda: "10.0.0.20", fallback="mice-b.local")
    a._clash("10.0.0.20")
    b._clash("10.0.0.9")
    t.ok((a.name == "mice.local") != (b.name == "mice.local"),
         "exactly one of two hubs ends up holding the shared name",
         "a=%s b=%s - both sides must reach the SAME verdict, and comparing "
         "addresses as text is the way to make them disagree"
         % (a.name, b.name))

    # Our own announcement echoes back off the multicast group. Treating that
    # as a clash would make a lone hub rename itself for company that is not
    # there.
    solo = mdns.Responder("mice.local", lambda: "10.0.0.20", fallback="mice-x.local")
    solo._clash("10.0.0.20")
    t.eq(solo.name, "mice.local", "and a hub does not clash with its own echo")

    m2 = (F.HUB / "mdns.py").read_text(encoding="utf-8")
    j2 = m2.find("def _serve")
    t.contains(m2[j2:j2 + 1400], "_answered",
               "the serve loop reads answers, not only questions")
