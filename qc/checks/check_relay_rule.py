"""A far board leans on a hotspot that is itself online, not on one whose NAME sorts later.

Model (tools/bench/wifi_topology_model.py, which compiles the firmware's own
WifiLink.h): with the old name-order rule a line of 10 boards leaving the router
stranded 9 when names rose outward, and chains of 2+ hops formed that cannot
route (every hotspot is 192.168.4.1/24). Boards reachable in the model, old to
new rule: 30 boards 14 to 24, 100 boards 12 to 29, 255 boards 7 to 25.

The pieces, all in source because the radio is not testable here:
  * WifiLink.h hostState/mayJoinRule (unit-tested natively, test_main.cpp)
  * checkLink uses mayJoinRule unless `SET RELAY NAME` switched the old rule back
  * a relaying module hides its hotspot; a module with clients never relays
"""
import re

import qc as F

AREA = "wifi"
TITLE = "relay hosts are chosen by being online; the old name rule stays selectable"
SLOW = False

CORE = F.FIRMWARE / "src" / "core"


def run(t):
    hdr = (CORE / "WifiLink.h").read_text(encoding="utf-8", errors="replace")
    web = (CORE / "WebPortal.cpp").read_text(encoding="utf-8", errors="replace")
    cmd = (CORE / "CommandRouter.cpp").read_text(encoding="utf-8", errors="replace")
    ident = (CORE / "Identity.cpp").read_text(encoding="utf-8", errors="replace")
    tests = (F.FIRMWARE / "test" / "test_logic" / "test_main.cpp").read_text(encoding="utf-8", errors="replace")

    t.ok("inline HostState hostState(" in hdr and "inline bool mayJoinRule(" in hdr,
         "the online-host rule lives in the unit-tested header", "")
    t.ok("test_online_host_follows_router_channel" in tests and "test_online_rule_ignores_name_order" in tests,
         "and the native tests exist", "")
    t.ok(re.search(r"mayJoinRule\(false,[^;]*routerCh_", web, re.S) is not None,
         "checkLink asks the rule with the router's channel", "")
    t.ok('relayRule() == "name"' in web and "wifilink::mayJoin(WiFi.softAPSSID().c_str(), ssid.c_str())" in web,
         "the old name rule is still there when switched back", "")
    t.ok('what == "RELAY"' in cmd and "setRelayRule" in cmd and '"relayrule"' in ident,
         "SET RELAY ONLINE|NAME is stored on the board", "")
    t.ok("hideAp(true)" in web and "softAPgetStationNum() > 0" in web,
         "a relay hides its hotspot, and a module with clients never relays", "")
