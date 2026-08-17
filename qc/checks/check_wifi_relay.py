"""A weak WiFi is not a failed WiFi — a module leans on a nearer one.

Falling back only when the connect FAILS misses the case that actually hurts at
a venue: a module far from the router still *connects*, just badly. Commands
arrive late, status polls time out, and the show stutters. Meanwhile another
module ten metres away has a strong link and is already hosting its own access
point.

So the decision is made on signal strength as well, and the rule lives in
`WifiLink.h` as a pure function with no Arduino in it — because you cannot make
a real -80 dBm signal appear on a bench, and this is precisely the behaviour
that only shows up in a big room. `pio test -e native` runs it for real; this
check makes sure the firmware actually uses it, and uses it safely.

The dangerous failure here is FLAPPING: a module near the threshold swapping
networks forever, dropping its link every time, which at a show looks like the
robot randomly freezing.
"""
import re

import qc as F

AREA = "wifi"
TITLE = "a module on a weak link moves to a stronger neighbour, without flapping"
SLOW = False


def run(t):
    hdr = (F.FIRMWARE / "src/core/WifiLink.h").read_text(encoding="utf-8", errors="replace")

    # ---- the rule is pure, so it can be tested without a venue ---------
    t.ok("Arduino.h" not in hdr and "WiFi.h" not in hdr,
         "the decision has no Arduino in it, so it runs on a PC",
         "it could then only be tested by standing in a big room")

    nums = {k: int(v) for k, v in re.findall(r"const int (\w+) = (-?\d+)", hdr)}
    for k in ("GOOD_RSSI", "WEAK_RSSI", "MARGIN"):
        t.ok(k in nums, "%s is a named threshold" % k)
    if len(nums) >= 3:
        # THE anti-flap property. Without a gap between "weak enough to leave"
        # and "good enough to come back", a module at the boundary swaps
        # networks forever and drops its link on every swap.
        t.ok(nums["GOOD_RSSI"] > nums["WEAK_RSSI"],
             "leaving and returning use DIFFERENT thresholds (%d vs %d)"
             % (nums["WEAK_RSSI"], nums["GOOD_RSSI"]),
             "one threshold for both directions is a module that flaps forever")
        t.ok(nums["GOOD_RSSI"] - nums["WEAK_RSSI"] >= 5,
             "with a real gap between them, not a token one")
        t.ok(nums["MARGIN"] > 0,
             "and a neighbour must be clearly better, not marginally")

    # ---- the firmware actually uses it --------------------------------
    portal = (F.FIRMWARE / "src/core/WebPortal.cpp").read_text(encoding="utf-8", errors="replace")
    t.contains(portal, "wifilink::decide", "the radio code asks it what to do")
    t.contains(portal, "checkLink", "from a scan of what is actually on air")

    m = re.search(r"void WebPortal::checkLink\(.*?\n\}", portal, re.S)
    if t.ok(m, "checkLink exists"):
        body = m.group(0)
        t.contains(body, "homeSsid_",
                   "measuring the SHOW network, not whatever we are joined to")
        t.contains(body, "peers_.find",
                   "and only ever relaying through a module it knows")
        t.ok("appliedHost_" in body,
             "never through its own access point",
             "a module joining itself would strand it completely")

    # the link check must be slow and must not fight the servo loop
    m = re.search(r"LINK_CHECK_MS\s*=\s*(\d+)",
                  (F.FIRMWARE / "src/core/WebPortal.h").read_text(encoding="utf-8", errors="replace"))
    if t.ok(m, "the check has a named interval"):
        t.ok(int(m.group(1)) >= 30000,
             "and is infrequent (%ss) — every switch costs a dropped link"
             % (int(m.group(1)) // 1000),
             "checking often turns a marginal signal into constant reconnects")

    code = re.sub(r"//[^\n]*", "", portal)
    t.ok("delay(" not in code,
         "and nothing in it blocks the loop",
         "this runs in the same loop as the servo interpolation")
    t.contains(portal, "scanNetworks(true)",
               "the scan behind it is asynchronous")

    # ---- home vs current link must be separate ------------------------
    # While relaying we are joined to a neighbour, but the network we WANT is
    # still the show network. Measuring the wrong one means never coming back.
    ph = (F.FIRMWARE / "src/core/WebPortal.h").read_text(encoding="utf-8", errors="replace")
    t.contains(ph, "homeSsid_",
               "the show network is remembered separately from the current link")
    t.contains(ph, "onRelay_", "and the module knows when it is relaying")
    t.contains(portal, 'via=\\"',
               "which the WIFI status line reports, so it is never a mystery")

    # ---- scanning must not damage the link -----------------------------
    # A scan REQUIRES dropping the connection (esp_wifi_scan_start refuses
    # while a connect is in flight), so every scan is a deliberate outage and
    # has to be undone properly. It was not: wstate_ stayed W_ONLINE while the
    # module held no address, and the bench showed
    #     state=online ssid="manny" ip=0.0.0.0
    # with the hub unable to reach it at all.
    # wstate_ is switched on TWICE — once to build the WIFI status line and
    # once to actually drive the radio. Only the second one matters here, so
    # look inside loop() rather than at the file.
    lm = re.search(r"void WebPortal::loop\(\) \{.*", portal, re.S)
    if not t.ok(lm, "loop() exists"):
        return
    loop = lm.group(0)

    m = re.search(r"if \(scanState_\) \{.*?\n    \}", loop, re.S)
    if t.ok(m, "the scan collector exists"):
        body = m.group(0)
        t.contains(body, "beginSta()",
                   "and a scan re-establishes the link through the normal path")
        # comments here TALK about WiFi.begin; only real code counts
        t.ok("WiFi.begin(" not in re.sub(r"//[^\n]*", "", body),
             "not with a bare begin() that leaves the state machine behind",
             "wstate_ stays W_ONLINE and the module lies about being reachable")

    m = re.search(r"case W_ONLINE:(.*?)break;", loop, re.S)
    if t.ok(m, "the online state exists"):
        body = m.group(1)
        t.contains(body, "localIP()",
                   "being online means HOLDING AN ADDRESS, not just being associated")
        t.contains(body, "beginSta()", "and a lost link is fully re-established")

    # The state machine must stand back entirely while a scan runs. Every
    # recovery path in it eventually calls WiFi.begin(), and that ABORTS a
    # scan already in progress — which is why every scan came back "0
    # networks" while the module sat there connected to a network it could
    # not see. The watchdog was helpfully re-joining and killing the scan.
    i = loop.find("if (scanState_) return;")
    j = loop.find("switch (wstate_)")
    t.ok(0 < i < j,
         "the radio state machine stands back while a scan is running",
         "a recovery path will call WiFi.begin() and abort the scan")

    # ...which makes a stuck scan far worse: the whole state machine waits on
    # scanState_, so a scan that never completes parks the radio for good and
    # the module answers "ask again in a moment" for ever. Seen on the bench:
    # two scans out of four never finished right after boot.
    t.contains(loop, "SCAN_TIMEOUT_MS",
               "and a scan that never finishes gives up instead of parking it")

    # With no peers there is nothing to lean on, so a scan could only ever
    # answer "stay" — and it is not free: it fights any scan the user asked
    # for. On a weak network with no neighbours it fired every 60 s for nothing.
    t.contains(loop, "peers_.count()",
               "no known peers means no reason to scan at all")
    # And when it DOES scan, the answer is shared: the two scans share one
    # radio, so a link check running is exactly when a user asks.
    m = re.search(r"if \(n >= 0 && scanState_ == 2\)(.*?)checkLink", loop, re.S)
    if t.ok(m, "the link-check collector exists"):
        t.contains(m.group(1), "scanText_",
                   "a link check also answers a waiting WIFI SCAN",
                   )

    # Disconnecting is not enough on its own: auto-reconnect is ON by default,
    # so the core starts a fresh connect the instant the link drops and
    # esp_wifi_scan_start refuses again. Measured — 4 scans out of 5 still
    # failed until this was held off.
    t.contains(portal, "setAutoReconnect(false)",
               "auto-reconnect is held off while scanning")
    # ...but ONLY when the radio is mid-connect. WiFi.disconnect() is
    # asynchronous, so tearing down an ESTABLISHED link to scan it means the
    # disconnect event lands after the scan has started and aborts it. The
    # board's own log showed exactly that, and every scan returned
    # "ERR scan failed" while the module sat happily on a network it could
    # not see. Both scan sites must guard the disconnect.
    guarded = len(re.findall(
        r"if \(WiFi\.status\(\) != WL_CONNECTED\) \{\s*\n\s*WiFi\.setAutoReconnect\(false\);"
        r"[^\n]*\n\s*WiFi\.disconnect\(", portal))     # a trailing comment is fine
    t.eq(guarded, portal.count("WiFi.disconnect(false, false)"),
         "and a live connection is never torn down just to scan it",
         )
    t.contains(loop, "setAutoReconnect(true)",
               "and put back the moment the scan is collected")
    # Every path that switches it OFF must have one that switches it back on —
    # otherwise a module that loses WiFi some time after a scan would sit there
    # disconnected for ever, with nothing left to notice.
    off = portal.count("setAutoReconnect(false)")
    on = portal.count("setAutoReconnect(true)")
    t.ok(on >= off,
         "and is never left switched off (%d off, %d on)" % (off, on),
         "a module that loses WiFi after a scan would never reconnect")
    m = re.search(r"SCAN_TIMEOUT_MS\s*=\s*(\d+)",
                  (F.FIRMWARE / "src/core/WebPortal.h").read_text(
                      encoding="utf-8", errors="replace"))
    if t.ok(m, "with a named timeout"):
        t.ok(5000 <= int(m.group(1)) <= 30000,
             "long enough for a real scan, short enough to notice (%ss)"
             % (int(m.group(1)) // 1000))
    k = loop.find("SCAN_TIMEOUT_MS")
    t.ok(0 < k < i,
         "and it is checked BEFORE the state machine stands back",
         "the timeout would never run, because the loop returns above it")

    # a mode change must drop back to the show network, not keep a stale relay
    m = re.search(r"void WebPortal::applyMode\(.*?\n\}", portal, re.S)
    if t.ok(m, "applyMode exists"):
        t.contains(m.group(0), "onRelay_ = false",
                   "and any WiFi change starts again from the show network")
