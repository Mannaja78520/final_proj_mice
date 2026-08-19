"""Finding things on the network is ONE piece of code, whatever is being found.

The hub looked for two things on the same subnet — modules and other hubs —
with two copies of one loop: same address range, same thread pool, same
cache-with-a-shelf-life, different only in the question asked. Two copies means
a fix landing in one and not the other, and that had already happened: the
module scan learned to be patient with a board that answers late, and the hub
scan never did.

So the loop lives once, in discovery.py, and a kind of thing to look for is a
Finder. This proves the three claims that makes:

  * the sweep exists once — nothing else walks a subnet on its own;
  * a NEW kind of thing really costs one line, driven here by adding one and
    watching it find something;
  * and the patient second pass, which came from a measured fault rather than
    a theory, still happens.
"""
import re
import sys

import qc as F

AREA = "discovery"
TITLE = "one way to find things on the network, whatever the thing is"
SLOW = False

sys.path.insert(0, str(F.HUB))


def run(t):
    import discovery

    src = (F.HUB / "main.py").read_text(encoding="utf-8", errors="replace")
    src = re.sub(r"#.*", "", src)

    # ---- the loop is not written twice --------------------------------
    # A subnet sweep is a range of addresses and a thread pool. If main.py
    # grows another one, the fix that reaches discovery.py stops reaching
    # everything.
    ranges = re.findall(r"range\(1,\s*255\)", src)
    t.ok(not ranges,
         "main.py does not walk a subnet itself any more",
         "found %d hand-rolled sweeps — they belong in discovery.Sweep" % len(ranges))

    # ---- what the hub looks for ---------------------------------------
    # Asserted on the OBJECT, not on how the line is spelled. An earlier
    # version matched the text `NAME = discovery.Finder(` and failed on a
    # harmless edit that still produced a Finder — the same brittleness this
    # suite has been caught by twice before.
    import main
    for want in ("HUBS", "MODULES"):
        got = getattr(main, want, None)
        t.ok(isinstance(got, discovery.Finder),
             "the hub's %s is a Finder" % want,
             "got %r — everything the hub looks for goes through one layer" % (got,))

    # ---- a new kind of thing is ONE line ------------------------------
    # Driven, not asserted from the shape of the code: make one, point it at a
    # fake network, and see it find something. If this ever needs a second
    # edit somewhere else, this check is where that shows up.
    seen = []

    def probe(ip):
        seen.append(ip)
        return {"ip": ip, "id": 7, "what": "kettle"} if ip.endswith(".9") else None

    kettles = discovery.Finder("kettles", probe, ttl=60)
    found = kettles.find("192.168.50.4")
    t.eq(len(seen), 254, "it asked the whole subnet")
    t.eq([f["ip"] for f in found], ["192.168.50.9"],
         "and a brand new kind of thing was found with no other change")

    # the shelf life is real: a second call must not sweep again
    del seen[:]
    kettles.find("192.168.50.4")
    t.eq(len(seen), 0, "an answer inside its shelf life is reused, not re-swept")
    kettles.forget()
    kettles.find("192.168.50.4")
    t.ok(len(seen) == 254, "and forget() really makes it look again")

    # ---- no network, no pretending ------------------------------------
    # 127.0.0.x means there is no usable interface. Sweeping loopback finds
    # this PC answering as everyone, which is worse than finding nothing.
    del seen[:]
    lonely = discovery.Finder("lonely", probe, ttl=60)
    t.eq(lonely.find("127.0.0.1"), [],
         "with no network it finds nothing, rather than sweeping loopback")
    t.eq(len(seen), 0, "and does not probe at all")

    # ---- the patient pass, which a real fault paid for ----------------
    slow_seen = []

    def flaky(ip):
        slow_seen.append(("fast", ip))
        return None                      # never answers the quick probe

    def patiently(ip):
        slow_seen.append(("slow", ip))
        return {"ip": ip, "id": 1, "what": "late"}

    late = discovery.Finder("late", flaky, ttl=0, patient=patiently)
    late._found = [{"ip": "10.0.0.5", "id": 1}]      # noqa: SLF001 - seen before
    got = late.find("192.168.50.4")
    t.ok(("slow", "10.0.0.5") in slow_seen,
         "an address that answered before is asked again, patiently",
         "a board sharing its WiFi answers late and was being dropped")
    t.eq([g["ip"] for g in got], ["10.0.0.5"],
         "so a module that is really there stays on the list")

    # and that pass is NOT limited to the swept subnet — 10.0.0.5 is not on
    # the 192.168.50 range that was swept, and it still had to be asked
    t.ok(any(w == "slow" and ip.startswith("10.") for w, ip in slow_seen),
         "including addresses outside this PC's own subnet",
         "a module can be reachable on another subnet, and a board found over "
         "a cable reports an address the sweep may never reach")
