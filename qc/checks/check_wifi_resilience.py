"""WiFi must never be able to stall the robot.

`WebPortal::loop()` runs in the SAME loop as the servo interpolation. One
blocking call in there — a `delay()`, a `while (WiFi.status() != …)`, a
synchronous scan — and a joint stops mid-move whenever the network is slow or
absent. That is the worst kind of failure here: it only happens at the venue,
where the WiFi is worst.

The state machine is already polled and non-blocking. This keeps it that way,
because the natural way to write "wait for WiFi" is exactly the blocking way.
"""
import re

import qc as F

AREA = "wifi"
TITLE = "a bad network cannot stall the servo loop"
SLOW = False

PORTAL = F.FIRMWARE / "src/core/WebPortal.cpp"


def _strip_comments(s):
    """Code only. A comment SAYING "delay()" is documentation, not a stall —
    the first version of this check failed on the comment explaining the fix."""
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
    return re.sub(r"//.*", "", s)


def run(t):
    src = _strip_comments(PORTAL.read_text(encoding="utf-8", errors="replace"))

    # ---- nothing in the WiFi path may block -------------------------
    # begin() runs once at boot, before any servo is moving, so a delay there
    # is harmless. Everything reachable from loop() is not.
    body = _after(src, "void WebPortal::loop()")
    for bad, why in (
        (r"\bdelay\s*\(", "delay() freezes the servo interpolation with it"),
        (r"while\s*\([^)]*WiFi\.status", "a busy-wait on the radio blocks the loop"),
        (r"WiFi\.waitForConnectResult", "waitForConnectResult blocks until it gives up"),
        (r"WiFi\.scanNetworks\s*\(\s*\)", "a synchronous scan blocks for seconds"),
    ):
        hits = re.findall(bad, body)
        t.ok(not hits, "loop() has no %s" % bad.replace("\\", ""), why)

    # applyHostname is reached FROM loop() — it used to delay(150) between
    # powering the radio down and back up.
    rename = _fn(src, "void WebPortal::applyHostname")   # already comment-free
    t.ok("delay(" not in rename,
         "renaming the module does not block either",
         "applyHostname runs from loop(); a delay here stops a move")
    t.contains(rename, "staRestartAt_",
               "it defers the restart instead of waiting for it")

    # ---- the connect path is a state machine with timeouts ----------
    hdr = _strip_comments(
        (F.FIRMWARE / "src/core/WebPortal.h").read_text(encoding="utf-8", errors="replace"))
    for state in ("W_CONNECTING", "W_DIAGNOSING", "W_ONLINE", "W_AP"):
        t.contains(hdr, state, "the WiFi path has a %s state" % state)
    t.contains(body, "WIFI_CONNECT_TIMEOUT_MS",
               "connecting gives up on a timeout instead of waiting forever")
    t.contains(body, "scanComplete",
               "the diagnostic scan is polled, not waited on")

    # ---- WiFi off must cost nothing --------------------------------
    # A board wired only to USB/RS485 should not pay for a radio it never uses.
    t.ok(re.search(r'wifiModeCfg_ == "off"\s*\)\s*return', body),
         "with WiFi off, loop() returns immediately",
         "a board on USB only should do no radio work at all")

    # ---- AP+STA: a connected module can host one that is out of range
    t.contains(src, "WIFI_AP_STA",
               "a module can join a network AND host an AP at the same time")

    # ---- the retry keeps trying, so a hotspot switched on later works
    t.contains(body, "lastStaRetry_",
               "in AP fallback it keeps retrying the real network")
    # It used to be WiFi.reconnect(). That was not enough: after a scan the
    # link can come back associated but with NO address, and reconnect() left
    # wstate_ at W_ONLINE so the module reported itself reachable while
    # holding 0.0.0.0. A full beginSta() re-arms DHCP and puts the state
    # machine back to W_CONNECTING, so either call satisfies the INTENT here —
    # what matters is that a dropped link is picked up and re-established.
    t.ok("WiFi.reconnect" in body or "beginSta()" in body,
         "and reconnects if the network drops later",
         "nothing re-establishes the link once it goes away")


def _after(src, sig):
    i = src.find(sig)
    return src[i:] if i >= 0 else ""


def _fn(src, sig):
    """One function body, brace-matched."""
    i = src.find(sig)
    if i < 0:
        return ""
    j = src.index("{", i)
    d = 0
    k = j
    while k < len(src):
        if src[k] == "{":
            d += 1
        elif src[k] == "}":
            d -= 1
            if d == 0:
                return src[i:k + 1]
        k += 1
    return src[i:]
