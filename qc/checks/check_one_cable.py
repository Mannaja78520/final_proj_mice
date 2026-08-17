"""One USB cable is enough for the whole installation, with no venue WiFi.

The real situation at a venue: there is no usable WiFi. Plug the PC into ONE
module; every other module joins that module's own hotspot. Nothing on the PC
has any route to those other modules — they are on a private 192.168.4.x behind
a board.

They still have to be fully controllable, and not by typing REACH commands by
hand: the module website, Nong Studio, file upload, sequences — all of it, on
each of them, down that one cable.

That is what the `@peer` device form is for. `usb:COM11@nong` means "over the
cable to COM11, then through it to the module called nong", and the hub wraps
every call in REACH. Proven on real hardware first: with the lift on USB in
hotspot mode and the nong joined to it, a JOINT command sent to the lift moved
the nong's servo.

Asserted here: the hub finds them, addresses them, and every page-level
operation lands on the RIGHT module.
"""
import json

import fake_serial
import qc as F

AREA = "connection"
TITLE = "one USB cable controls modules behind that module's own hotspot"
SLOW = False

FAR = "usb:%s@far-nong" % fake_serial.PORT
NEAR = "usb:%s" % fake_serial.PORT


def run(t):
    fake_serial.reset()
    base, main = F.start_hub()

    # ---- the dev string ------------------------------------------------
    kind, addr, bus, peer = main.parse_dev(FAR)
    t.eq(kind, "usb", "a peer device is still a USB device")
    t.eq(addr, fake_serial.PORT, "on the cable we are plugged into")
    t.eq(peer, "far-nong", "naming the module on the far side")
    t.eq(main.parse_dev(NEAR)[3], "", "and a plain cable has no peer")
    # a NAME, not an address — a hotspot hands out different ones over time
    t.ok("@" in FAR and "192.168" not in FAR,
         "peers are addressed by name, not by an address that can change")

    # ---- the hub can SEE what is behind the cable -----------------------
    s, raw = F.get(base + "/api/dev/peers?dev=" + NEAR)
    t.eq(s, 200, "the hub can ask what is behind a cable")
    try:
        b = json.loads(raw)
    except ValueError:
        b = []
    names = [p.get("name") for p in b] if isinstance(b, list) else []
    t.ok("far-nong" in names,
         "and lists the module on that module's hotspot",
         "with no venue WiFi this list is the ONLY way to find it: %r" % b)

    # ---- and every operation reaches the RIGHT module -------------------
    s, b = F.get(base + "/api/dev/cmd?dev=%s&c=PING" % FAR)
    t.contains(b, "PONG", "a command reaches the far module")
    t.ok(any(c.startswith("REACH far-nong") for _, c in fake_serial.wire),
         "by being forwarded through the module on the cable",
         "the hub sent it to the near module instead: %r"
         % [c for _, c in fake_serial.wire][-3:])

    # status must be the FAR module's, or every page shows the wrong robot
    s, b = F.get(base + "/api/dev/status?dev=" + FAR)
    t.eq(s, 200, "status comes back")
    t.ok(any(c == "REACH far-nong INFO" for _, c in fake_serial.wire),
         "and it is the far module's own status, not the middleman's",
         "the site would show the wrong robot's joints and type")

    # a move must land on the far module and NOT on the near one
    far_before = list(fake_serial.NONG.far_joints)
    near_before = list(fake_serial.NONG.joints)
    F.get(base + "/api/dev/cmd?dev=%s&c=%s" % (FAR, "POSE+25+155+90+90+90+90+90+90+90+90"))
    t.ok(fake_serial.NONG.far_joints != far_before,
         "a move lands on the far module")
    t.eq(fake_serial.NONG.joints, near_before,
         "and the module on the cable does not move")

    # ---- file transfer, which is what makes a show runnable ------------
    seq = b'name: viacable\nsteps:\n  - pose: "90 90 90 90 90 90 90 90 90 90 T 500"\n'
    r = main.dev_upload(FAR, "/moves", "viacable.yaml", seq)
    t.contains(r, "OK", "a sequence uploads to the far module")
    t.eq(fake_serial.NONG.far_held, seq.decode(),
         "byte for byte, through the cable and the hotspot")
    # every chunk must have been FORWARDED. A bare FBEGIN/FDATA on the wire
    # means the hub wrote the sequence into the module on the cable instead —
    # the show would load onto the wrong robot and nobody would notice until
    # it ran.
    outer = [c for _, c in fake_serial.wire if not c.startswith("REACH ")]
    t.ok(not any(c.startswith(("FBEGIN", "FDATA", "FEND")) for c in outer),
         "with every chunk forwarded, not written to the near module",
         "the sequence landed on the wrong robot: %r" % outer[-5:])
    t.ok(any(c.startswith("FBEGIN") for _, c in fake_serial.far_wire),
         "and the far module is what actually received them")
    t.eq(fake_serial.NONG.held, "",
         "and the module on the cable holds nothing")

    s, b = F.get(base + "/api/dev/files?dev=%s&dir=/moves" % FAR)
    t.eq(s, 200, "its file list comes back too")

    # ---- a forwarded command gets time for BOTH hops -------------------
    # It travels the cable, then the hotspot, and the far hop is retried. The
    # normal 2 s budget cut it off mid-flight, and the page got a 502 while
    # the module was answering perfectly — seen on real hardware the moment
    # the first status was fetched.
    src = (F.CODE / "main_python/main.py").read_text(encoding="utf-8", errors="replace")
    t.contains(src, "PEER_WAIT", "a forwarded command has its own time budget")
    m = __import__("re").search(r"PEER_WAIT\s*=\s*([\d.]+)", src)
    if t.ok(m, "which is a named constant"):
        t.ok(float(m.group(1)) >= 4.0,
             "long enough for two hops and a retry (%ss)" % m.group(1),
             "the page gives up while the module is still answering")
    t.contains(src, "wait=PEER_WAIT if peer else",
               "and a local command is NOT slowed down by it")

    # ---- the hub page offers them, or none of this is reachable --------
    hub = (F.CODE / "main_python/web/hub.html").read_text(encoding="utf-8", errors="replace")
    # It must be CALLED, not merely defined. Deleting the one call leaves the
    # function sitting there looking correct while the page silently stops
    # listing anything — which is how this assertion was written the first
    # time, and it passed against exactly that break.
    t.ok(hub.count("addHotspotPeers") >= 2,
         "the hub page lists modules on a module's hotspot",
         "addHotspotPeers is defined but never called: the peers never appear")
    t.contains(hub, "addHotspotPeers(slot,",
               "for the module actually plugged into the cable")
    t.contains(hub, "'usb:'+port+'@'+peer",
               "and links them with the @peer device form")
    t.ok("Studio" in hub and "peer" in hub,
         "so they get the same site and Studio buttons as any other module")
