"""`mice.local` answers, so nobody has to read an IP address across a room.

The hub's address changes with the network it is on; its name does not. This
drives the responder over a REAL socket — a query goes out, an answer comes
back, and the packet is taken apart by hand — because a responder that builds
a correct packet and never sends it looks identical from the inside.

Two things are asserted separately, and they fail for different reasons:

  * the PACKET is right. Header flags, the name in DNS label form, type A,
    class IN with the cache-flush bit, and the four address bytes. Parsed here
    with struct rather than with the module's own reader, so a mistake in the
    builder cannot be hidden by the same mistake in the parser.
  * the RESPONDER answers the right question and ignores the rest. A responder
    that replies to everything is a nuisance on a venue network, and one that
    replies to nothing is invisible.

A quirk worth knowing: multicast on a Windows loopback is unreliable, so the
query is sent straight to the responder's own port and the answer is read from
the unicast reply. That is the reply a phone actually uses too — the multicast
copy is the courtesy one.
"""
import socket
import struct
import sys

import qc as F

AREA = "hub"
TITLE = "the hub answers to mice.local"

sys.path.insert(0, str(F.HUB))
import mdns  # noqa: E402


def _query(name):
    """A minimal mDNS query packet for one A record."""
    out = struct.pack(">HHHHHH", 0x1234, 0, 1, 0, 0, 0)
    for part in name.split("."):
        out += bytes([len(part)]) + part.encode()
    return out + b"\x00" + struct.pack(">HH", 1, 1)


def _parse(pkt):
    """The answer, taken apart with struct - not with the module's own reader."""
    ident, flags, qd, an, _ns, _ar = struct.unpack(">HHHHHH", pkt[:12])
    at = 12
    labels = []
    while at < len(pkt) and pkt[at]:
        n = pkt[at]
        labels.append(pkt[at + 1:at + 1 + n].decode())
        at += 1 + n
    at += 1
    rtype, rclass, ttl, rdlen = struct.unpack(">HHIH", pkt[at:at + 10])
    at += 10
    return {"flags": flags, "answers": an, "name": ".".join(labels),
            "type": rtype, "class": rclass, "ttl": ttl, "len": rdlen,
            "ip": socket.inet_ntoa(pkt[at:at + 4]) if rdlen == 4 else ""}


def run(t):
    # ---- 1. the packet says what the standard requires ---------------
    got = _parse(mdns.answer("mice.local", "192.168.1.20"))
    t.eq(got["name"], "mice.local", "the answer names mice.local")
    t.eq(got["ip"], "192.168.1.20", "and gives the address it was asked to give")
    t.eq(got["type"], 1, "as an A record")
    t.ok(got["flags"] & 0x8000, "flagged as an answer, not a question",
         "a resolver ignores a packet whose response bit is not set")
    t.ok(got["flags"] & 0x0400, "and as authoritative")
    t.eq(got["answers"], 1, "carrying exactly one answer")
    t.ok(got["class"] & 0x8000,
         "with the cache-flush bit, so a stale address is replaced",
         "without it a phone keeps yesterday's IP until the TTL expires")
    t.eq(got["class"] & 0x7FFF, 1, "in class IN")
    t.ok(0 < got["ttl"] <= 300, "and a short TTL, because this address moves",
         "ttl=%d" % got["ttl"])

    # ---- 2. it only answers what it is for ---------------------------
    t.eq(mdns.questions(_query("mice.local")), ["mice.local"],
         "a query for mice.local is recognised")
    t.eq(mdns.questions(_query("printer.local")), ["printer.local"],
         "and so is one for something else, so it can be ignored")
    t.eq(mdns.questions(mdns.answer("mice.local", "10.0.0.1")), [],
         "an ANSWER is never treated as a question",
         )
    t.eq(mdns.questions(b"\x00\x01"), [], "and a runt packet does not crash it")

    # ---- 3. it really answers, over a real socket --------------------
    # Bound on an ordinary port rather than 5353: something on this machine
    # usually holds 5353 already, and what is under test is the answering, not
    # the ability to win a race for a well-known port.
    r = mdns.Responder("mice.local", lambda: "192.168.1.20")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("127.0.0.1", 0))
    r.sock = sock
    import threading
    r.thread = threading.Thread(target=r._serve, daemon=True)  # noqa: SLF001
    sock.settimeout(1.0)
    r.thread.start()
    here = sock.getsockname()

    asker = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    asker.settimeout(4.0)
    try:
        asker.sendto(_query("mice.local"), here)
        data, _from = asker.recvfrom(2048)
        back = _parse(data)
        t.eq(back["name"], "mice.local", "a real query gets a real answer back")
        t.eq(back["ip"], "192.168.1.20", "with this hub's address in it")

        # ...and a question for someone else is left alone.
        # Wait for the FIRST answer to be counted before reading the counter:
        # the packet arrives here before the responder thread has finished
        # incrementing it, so a counter read straight away is a race, and it
        # failed a full run exactly that way.
        import time as _t
        until = _t.time() + 2
        while r.answered < 1 and _t.time() < until:
            _t.sleep(0.02)
        before = r.answered
        asker.sendto(_query("printer.local"), here)
        try:
            asker.settimeout(1.0)
            asker.recvfrom(2048)
            spoke = True
        except socket.timeout:
            spoke = False
        t.ok(not spoke, "and it stays quiet about names that are not its own",
             "a responder that answers everything is a nuisance on a venue network")
        t.eq(r.answered, before, "so it counts only the answers it should give")
    except socket.timeout:
        t.ok(False, "a real query gets a real answer back",
             "nothing came back within four seconds")
    finally:
        asker.close()
        r.close()

    # ---- 4. the hub tells the page whether the name works ------------
    import json
    base, main = F.start_hub()
    mine = json.loads(F.get(base + "/api/mine")[1])
    t.ok("name_url" in mine, "the hub reports the name as well as the address",
         "the page cannot print mice.local honestly without being told")
    t.ok("url" in mine and "127.0.0.1" not in mine.get("url", ""),
         "and the address it reports is one a phone could use",
         "got %r - 127.0.0.1 is the one address that cannot work from a phone"
         % mine.get("url"))
    t.eq(main.MDNS_NAME, "mice.local", "the name lives in one place")
