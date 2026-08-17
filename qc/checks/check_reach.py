"""A module the PC cannot see is still reachable through one it can.

This is the last step of "a module is always reachable". A board parked out of
router range joins a nearby module's own AP — proven on real hardware: the nong
sat on the lift's hotspot at 192.168.4.2 while still hosting its own. But it is
then on that module's private subnet, where the PC has no route to it.

So the module it joined forwards for it:

    PC --USB--> lift-test --its own AP--> nong

`REACH <ip|name|id> <command>` runs one command over there and hands back
exactly what that module answered. Deliberately the same shape as the RS485
bridge (`#3 GOTO 2`) — one command in, one reply line out — so the hub's dev=
routing and the module website's console need no changes at all.

The one thing it must never do is stall a moving joint: it blocks waiting for
the far module, so it refuses while this module is mid-move.
"""
import json
import re

import fake_serial
import qc as F
import registry

AREA = "reach"
TITLE = "a module behind another module's hotspot is still controllable"
SLOW = False


def run(t):
    fake_serial.reset()
    base, main = F.start_hub()

    # ---- what can this module see? -------------------------------------
    s, b = F.cmd(base, "PEERS")
    t.eq(s, 200, "PEERS answers")
    try:
        peers = json.loads(b)
    except ValueError:
        t.ok(False, "PEERS returns JSON", b)
        return
    t.ok(any(p.get("self") for p in peers), "the list names this module first")
    far = [p for p in peers if not p.get("self")]
    if not t.ok(far, "and the module on the far side of its AP", b):
        return
    t.eq(far[0]["ip"], "192.168.4.2",
         "with the address it got from that AP")

    # ---- and talk to it ------------------------------------------------
    for who in ("far-nong", "7", "192.168.4.2"):
        s, b = F.cmd(base, "REACH %s PING" % who)
        t.ok(b.startswith("PONG"),
             "REACH by %s reaches it" % ("name" if who == "far-nong"
                                         else ("id" if who == "7" else "ip")),
             "got %r" % b)

    # the reply is the FAR module's, not this one's
    s, b = F.cmd(base, "REACH far-nong POSE 25 155 90 90 90 90 90 90 90 90")
    t.contains(b, "OK", "a command runs over there")
    t.eq(fake_serial.NONG.far_joints[0], 25.0,
         "and it really moved the FAR module")
    t.ok(fake_serial.NONG.joints[0] == 90.0,
         "while the module we are plugged into did not move",
         "the command was executed locally instead of being forwarded")

    # ---- it refuses rather than stall a moving joint --------------------
    fake_serial.NONG.busy = True
    s, b = F.cmd(base, "REACH far-nong PING")
    t.ok(b.startswith("ERR") and "busy" in b.lower(),
         "and it refuses while this module is mid-move",
         "REACH blocks for up to 800 ms; doing that during a move stops a "
         "joint dead. Got %r" % b)
    fake_serial.NONG.busy = False

    # ---- a module that is not there is a clear error, not a hang -------
    s, b = F.cmd(base, "REACH nowhere PING")
    t.ok(b.startswith("ERR"), "an unknown module is an error", b)
    t.contains(b, "PEERS", "that says how to find the right name")

    # ---- the firmware really does this ---------------------------------
    portal = (F.FIRMWARE / "src/core/WebPortal.cpp").read_text(
        encoding="utf-8", errors="replace")
    m = re.search(r"String WebPortal::reach\(.*?\n\}", portal, re.S)
    if not t.ok(m, "the firmware has reach()"):
        return
    body = m.group(0)
    t.contains(body, "busy()",
               "which refuses while the module is moving")
    t.contains(body, "HTTPClient", "forwards over HTTP to the far module")
    t.contains(body, "REACH_TIMEOUT_MS",
               "with a bounded timeout, so a dead peer cannot hold the loop")
    t.ok("indexOf('\\n')" in body or "indexOf(10)" in body,
         "and never returns more than one line",
         "a multi-line body would break 'one command, one reply line' and "
         "poison the NEXT command - exactly the HELP bug all over again")

    # One attempt is not enough over a shared hotspot: a module in AP_STA has
    # one radio serving the show network AND its own AP, so it time-slices and
    # drops packets. Measured — one attempt at 800 ms scored 1 of 6, while the
    # far module answered the PC 6 of 6 throughout, so the far module was never
    # at fault. Over a direct module AP (one hop) one attempt was 7 of 7.
    t.contains(body, "REACH_TRIES", "it retries rather than give up on one lost packet")
    t.contains(body, "setReuse(false)",
               "with a fresh connection each attempt, never a half-open one")

    hdr = (F.FIRMWARE / "src/core/WebPortal.h").read_text(encoding="utf-8", errors="replace")
    m = re.search(r"REACH_TIMEOUT_MS\s*=\s*(\d+)", hdr)
    mt = re.search(r"REACH_TRIES\s*=\s*(\d+)", hdr)
    if t.ok(m and mt, "the budget is named constants, not magic numbers"):
        worst = int(m.group(1)) * int(mt.group(1))
        t.ok(worst <= 2500,
             "and the WORST case is still bounded (%d ms)" % worst,
             "retries must not turn a bounded wait into an open-ended one")

    # ---- the module must SEE the boards leaning on it -------------------
    # mDNS only asks on the station interface, so a host module never found
    # the very boards sitting on its own AP. On the bench PEERS came back with
    # only the module itself in it, and REACH by name failed while REACH by ip
    # worked — which is exactly what that gap looks like.
    peer = (F.FIRMWARE / "src/core/PeerDiscovery.cpp").read_text(
        encoding="utf-8", errors="replace")
    t.contains(peer, "scanAp", "the module also looks for peers on its own AP")
    t.contains(peer, "softAPgetStationNum",
               "and only when something is actually connected to it")
    m = re.search(r"void PeerDiscovery::taskLoop\(.*?\n\}", peer, re.S)
    if t.ok(m, "the discovery task exists"):
        loop = m.group(0)
        i, j = loop.find("scanAp"), loop.find("WL_CONNECTED")
        t.ok(i > 0, "which the background task runs")
        t.ok(j < 0 or not re.search(
            r"WL_CONNECTED.*?scanAp.*?\n        \}", loop, re.S),
            "outside the 'STA connected' test",
            "in AP mode there is no station, and those are precisely the "
            "modules that have nobody else to be found by")

    # peers must have ONE implementation, or the command and the website drift
    t.ok(portal.count("peers_.peersJson(") == 1,
         "the fleet list has a single implementation",
         "PEERS and /api/peers each build their own list and can disagree")

    # ---- declared, documented, discoverable ----------------------------
    cmds = {c["name"]: c for c in registry.commands()}
    for name in ("REACH", "PEERS"):
        t.ok(name in cmds, "%s is declared in config/commands.json" % name)
    docs = (F.CODE / "firmware/COMMANDS.md").read_text(encoding="utf-8", errors="replace")
    t.contains(docs, "REACH", "and COMMANDS.md documents it")
    t.contains(docs, "Reaching a module through another one",
               "with the reason it exists, not just the syntax")
