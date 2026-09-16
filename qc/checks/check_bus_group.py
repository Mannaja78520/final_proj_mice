"""A module behind the RS485 bus reports the group it belongs to (A3-5).

Modules only link to modules in the SAME group: the fallback access point's
password is derived from the group name, so two companies on one site never
join each other's installation by accident. The hub's Network tab is where a
person sets that, and it reads `group` for every module it can reach.

For a board behind the bus that field was ALWAYS EMPTY, so it read *not
linked* however carefully it had been grouped. The page was right to say what
it was given; nothing ever filled it in. The hub already asks each bus module
for INFO — to learn its WiFi address and its chip — and INFO has carried the
group all along (CommandRouter::buildStatus). Two fields were kept out of that
answer and the third was dropped on the floor.

WHY IT IS WORTH A CHECK. The wrong reading was not cosmetic. Seeing *not
linked* on a board that IS grouped invites someone to tick it and press the
button, which sends GROUP to a module that already had one — and since the AP
password is derived from the group name, getting that wrong takes a board out
of the installation until somebody notices.

The fake board behind the bus (id 67) now accepts GROUP and reports it in
INFO, exactly as the firmware does, so this is driven end to end: set the
group over the bus, then read it back the way the page does.
"""
import json

import fake_serial
import qc as F

AREA = "network"
TITLE = "a module behind the RS485 bus carries the group it belongs to"
SLOW = False

BUS_ID = fake_serial.BUS_SLOW_ID          # the board with no cable of its own


def _fresh_probe(main, port):
    """A full probe, bus census included.

    Two things have to be cleared or this check quietly tests nothing. The
    cached identity is from before the GROUP. And the cable counts as IN USE
    for a few seconds after any command, which makes probe_usb_port identify
    the near board and RETURN — deliberately, so a live page is not stalled by
    a 5 s census (main.py, `if light:`). Left alone, the bus list comes back
    empty and every assertion below would be about nothing.
    """
    _forget(main, port)
    return main.probe_usb_port(port)


def _forget(main, port):
    """Every cache between a command and what the page is told.

    Three of them, and each one on its own is enough to make this check pass
    while proving nothing: the identity cached before the GROUP, the in-use
    marker that skips the census, and the 8-second scan cache that /api/allmods
    answers from.
    """
    main._usb_ident.pop(port, None)        # noqa: SLF001
    main._usb_touch.pop(port, None)        # noqa: SLF001
    main._usbscan_cache["at"] = 0          # noqa: SLF001


def run(t):
    fake_serial.reset()
    base, main = F.start_hub()
    port = fake_serial.PORT

    # ---- group it OVER THE BUS, the way the Network tab does ----------
    reply = F.cmd(base, "GROUP mice-show", port=port, bus=BUS_ID)
    t.contains(str(reply), "mice-show",
               "a board behind the bus accepts GROUP")

    # ---- and the hub reports it -----------------------------------------
    # Read through probe_usb_port, which is what /api/scanusb and the Network
    # tab are built on, rather than asking the fake what it thinks it is.
    got = _fresh_probe(main, port)
    bus = {b.get("id"): b for b in (got.get("rs485") or [])}
    if not t.ok(BUS_ID in bus,
                "the board behind the bus is still found (id %d)" % BUS_ID,
                "census: %r" % (sorted(bus),)):
        return
    t.eq(bus[BUS_ID].get("group"), "mice-show",
         "and the hub reports the group it was given")

    # The near board is a different module and must not inherit it: one board
    # reporting another's group is how a module gets moved between
    # installations by accident.
    near = got.get("module") or {}
    t.eq(near.get("group"), "",
         "while the board on the cable keeps its own (empty) group")

    # ---- the page's own route says the same ---------------------------
    # /api/mine is this hub's own modules — what the Modules screen reads, and
    # what another hub pulls through /api/allmods. (allmods itself aggregates
    # only OTHER hubs, so a lone hub answers it with an empty list.)
    _forget(main, port)
    code, body = F.get(base + "/api/mine")
    rows = {m.get("dev"): m for m in (json.loads(body).get("modules") or [])}
    dev = "usb:%s:%s" % (port, BUS_ID)
    if not t.ok(dev in rows, "the bus board is listed as %s" % dev,
                "listed: %r" % (sorted(rows),)):
        return
    t.eq(rows[dev].get("group"), "mice-show",
         "with its group, so the page can say linked instead of not linked")

    # ---- a DONGLE has no board of its own, and still has boards -------
    # The real rig is exactly this: a CH340+MAX485 on its own cable with the
    # nong behind it, and that board is reachable no other way. The module
    # list skipped the whole port when the cable had no module answering
    # directly, so the one board that needs the bus was the one board nobody
    # could see. Measured on hardware 2026-08-21: probe_usb_port found board
    # 67 behind COM23 while /api/mine listed four modules without it.
    fake_serial.dongle_listed[0] = True
    _forget(main, fake_serial.DONGLE_PORT)
    dongle = main.probe_usb_port(fake_serial.DONGLE_PORT)
    t.ok(dongle.get("module") is None,
         "a dongle answers nothing on its own cable",
         "if the fake answers here it is not a dongle and this proves nothing")
    kids = {b.get("id"): b for b in (dongle.get("rs485") or [])}
    t.ok(BUS_ID in kids, "but the bus board behind it is found",
         "behind the dongle: %r" % (sorted(kids),))

    _forget(main, fake_serial.DONGLE_PORT)
    _forget(main, port)
    code, body = F.get(base + "/api/mine")
    listed = {m.get("dev") for m in (json.loads(body).get("modules") or [])}
    t.ok("usb:%s:%s" % (fake_serial.DONGLE_PORT, BUS_ID) in listed,
         "and the module list shows it, though its cable holds no board",
         "a port with no direct module used to be skipped whole, bus children "
         "and all — listed: %r" % (sorted(listed),))

    # ---- and CLEAR really clears --------------------------------------
    # A group that cannot be removed is a board that cannot leave an
    # installation without a reflash.
    F.cmd(base, "GROUP CLEAR", port=port, bus=BUS_ID)
    after = {b.get("id"): b for b in
             (_fresh_probe(main, port).get("rs485") or [])}
    t.eq(after.get(BUS_ID, {}).get("group"), "",
         "ungrouping it over the bus is reported too")
