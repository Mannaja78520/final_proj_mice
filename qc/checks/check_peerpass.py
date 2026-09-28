"""Module WiFi passwords: a default to get in, the owner's choice, and the hub
handing group-mates' passwords round (user 2026-09-28).

The user asked for three things about the hotspot every module raises:

  * a default password, so the first visit always works - 12345678 when the
    module is in no group (the group-derived one once it is);
  * the owner can change it (APPASS), and that choice wins over the group's;
  * modules in one group can still link after an owner changed a password:
    no module can know a password someone else chose, but the hub talks to
    every board, so it reads each one's (GROUP) and hands the others' out
    (PEERPASS). A module looking for a neighbour tries the handed-over
    password for THAT neighbour first.

The hub half runs here against fake boards; the firmware half is read from
source, since the chip is not on this bench.
"""
import sys

import qc as F

AREA = "hub"
TITLE = "module WiFi passwords: default, owner's choice, shared in a group"


def run(t):
    sys.path.insert(0, str(F.HUB))
    import hub_appass                                      # noqa: E402

    # ---- three boards: two in "show", one on its own ----------------------
    boards = {
        "usb:COM1": {"group": "show", "ap": "nong", "pass": "owner-chose-this"},
        "wifi:10.0.0.9": {"group": "show", "ap": "lift-2", "pass": "3f9a1c0b7e2d4a55"},
        "usb:COM2": {"group": "", "ap": "lonely", "pass": "12345678"},
    }
    got = {d: {} for d in boards}

    def cmd(dev, c):
        b = boards[dev]
        if c == "GROUP":
            g = '"%s"' % b["group"] if b["group"] else "(none)"
            return "GROUP %s appass=%s" % (g, b["pass"])
        if c == "WIFI":
            return 'WIFI mode=on state=online ssid="manny" ap="%s" apip=192.168.4.1' % b["ap"]
        if c.startswith("PEERPASS "):
            _, ssid, pw = c.split(" ")
            got[dev][ssid] = pw
            return "OK peer " + ssid
        return "ERR"

    mods = [{"key": d, "best": d} for d in boards]
    hub_appass._sent.clear()
    groups, sent = hub_appass.share_once(mods, cmd)
    t.eq(groups, {"show": ["lift-2", "nong"]}, "the hub groups boards by their group")
    t.eq(got["usb:COM1"], {"lift-2": "3f9a1c0b7e2d4a55"},
         "nong is handed lift-2's password")
    t.eq(got["wifi:10.0.0.9"], {"nong": "owner-chose-this"},
         "and lift-2 is handed the one nong's owner chose")
    t.eq(got["usb:COM2"], {}, "a board in no group is handed nothing")

    _, again = hub_appass.share_once(mods, cmd)
    t.eq(again, 0, "a second round with nothing changed writes nothing")
    boards["usb:COM1"]["pass"] = "changed-again-1"
    _, third = hub_appass.share_once(mods, cmd)
    t.ok(third == 1 and got["wifi:10.0.0.9"]["nong"] == "changed-again-1",
         "when an owner changes a password, only the mates are told, once",
         "sent %d" % third)

    # ---- the firmware half -------------------------------------------------
    fw = F.FIRMWARE
    ident = (fw / "src/core/Identity.cpp").read_text(encoding="utf-8", errors="replace")
    body = ident[ident.find("String Identity::apPassword()"):]
    t.ok(0 <= body.find("appass_") < body.find("AP_FALLBACK_PASS"),
         "the owner's password wins over the group one and the default")
    net = (fw / "config/conf_network.h").read_text(encoding="utf-8", errors="replace")
    t.contains(net, 'AP_FALLBACK_PASS = "12345678"', "the default hotspot password is 12345678")
    wp = (fw / "src/core/WebPortal.cpp").read_text(encoding="utf-8", errors="replace")
    t.contains(wp, "staPass_ = id_->peerPass(bestName);",
               "a module leaning on a neighbour tries that neighbour's handed-over password")
    router = (fw / "src/core/CommandRouter.cpp").read_text(encoding="utf-8", errors="replace")
    for c in ("APPASS", "PEERPASS"):
        t.contains(router, 'cmd == "%s"' % c, "the board answers %s" % c)

    # ---- a board with no group-mate is never asked anything ---------------
    # The Network tab check caught a bare GROUP question reaching a lone board
    # (2026-09-28): harmless, but traffic on a bus that has none to spare.
    asked = []
    def quiet(dev, c):
        asked.append(c)
        return "ERR"
    hub_appass.share_once([{"key": "a", "best": "usb:COM1", "group": "show"},
                           {"key": "b", "best": "usb:COM2", "group": ""}], quiet)
    t.eq(asked, [], "a lone board in a group, and an ungrouped one, get no questions")
