"""The scan candidate is picked by the TESTED helper, not inline again.

checkLink used to keep best/known in three local variables with an
order-dependent tie-break whose own comment said the opposite ("a module we
already know beats a guess of the same strength" — it also beat STRONGER
guesses, or lost to them, depending on scan order). The decision now lives in
wifilink::PeerPick where `pio test -e native` proves it. This check pins that
WebPortal actually routes through the helper — and that the old inline
tie-break is gone.
"""
import qc as F

AREA = "connection"
TITLE = "checkLink picks its candidate through wifilink::PeerPick"


def run(t):
    src = (F.FIRMWARE / "src" / "core" / "WebPortal.cpp").read_text(encoding="utf-8")
    link = src[src.find("void WebPortal::checkLink("):]
    link = link[:link.find("\n}")]

    t.contains(link, "wifilink::PeerPick pick;",
               "the helper is declared and used")
    t.contains(link, "pick.feed(known, rssi, ssid.c_str())",
               "every eligible scan result is fed to it")
    t.contains(link, "pick.best(bestRssi, bestKnown)",
               "the choice comes out of the helper")
    t.ok("if (known && !bestKnown)" not in src,
         "the old order-dependent inline tie-break is gone")

    # A13-7: two lonely group-mates each joined the other's 192.168.4.1
    # hotspot. Every candidate passes the one-way name rule before anything
    # else, and the rule itself is the tested wifilink::mayJoin.
    t.contains(link, "wifilink::mayJoin(WiFi.softAPSSID().c_str(), ssid.c_str())",
               "a hotspot named before ours is never a candidate")
    hdr = (F.FIRMWARE / "src" / "core" / "WifiLink.h").read_text(encoding="utf-8")
    body = hdr[hdr.find("inline bool mayJoin("):]
    body = body[:body.find("\n}")]
    t.ok("std::string(other) > std::string(self)" in body,
         "joins only point to a name that sorts after ours",
         "with >= or <, two group-mates can each join the other again")
