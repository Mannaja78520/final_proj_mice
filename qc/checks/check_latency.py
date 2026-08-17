"""The robot must follow your hand, not trail it.

"It lags" was four separate things, and only one of them was the network. All
four were measured on real boards before and after, so this file guards the
fixes rather than the theory:

  1. A dragged pose was sent with NO time, so the module fell back to its SPEED
     setting: a 20 degree slider move became a 166 ms eased move, the next
     update arrived before it finished, and the arm was permanently easing
     towards where your hand used to be.
  2. The firmware's main loop took the router mutex on every pass and came
     straight back for more, so the web server — which needs that mutex to
     answer — queued behind a loop doing nothing. A POSE took ~90 ms while an
     ICMP ping to the same board took 17 ms. One yield: 30 ms -> 13 ms on USB.
  3. The ESP32 dozes between beacons as a WiFi station (WIFI_PS_MIN_MODEM).
     Ping to the board: 73 ms average with it, 17 ms without.
  4. The camera's live view ran on a fixed 1 s timer while the board delivers a
     frame every ~140 ms. Chained requests: 1 fps -> 7.3 fps.

None of these is visible in a screenshot, and all of them are what "laggy"
means to someone using it.
"""
import re

import fake_serial
import qc as F

AREA = "connection"
TITLE = "live control follows the hand: no eased moves, no starved web task"
SLOW = False


def run(t):
    # ---- 1. a live pose carries the time it has ---------------------
    app = (F.STUDIO_WEB / "app.js").read_text(encoding="utf-8", errors="replace")
    pump = app[app.find("function livePump"):]
    pump = pump[:pump.find("\n}")]
    t.contains(pump, '" T " + liveT()',
               "a dragged pose asks for a time, instead of the module's easing speed")
    t.contains(pump, "liveRtt +=",
               "and the round trip is measured from the traffic itself")
    fn = app[app.find("function liveT()"):]
    fn = fn[:fn.find("\n}")]
    for bound in ("LIVE_T_MIN", "LIVE_T_MAX"):
        t.contains(fn, bound, "the asked-for time is clamped (%s)" % bound)
    # The firmware floors T per joint anyway, so a short request is safe — but
    # asking for less than the physical floor everywhere would be a lie.
    m = re.search(r"LIVE_T_MIN\s*=\s*(\d+)", app)
    if t.ok(m, "the floor is a real number"):
        t.ok(int(m.group(1)) >= 80,
             "and it is not below the move-time floor the firmware uses (80 ms)")

    # ---- 2. the firmware yields, so the web task can be served ------
    main_cpp = (F.FIRMWARE / "src/main.cpp").read_text(encoding="utf-8", errors="replace")
    loop = main_cpp[main_cpp.find("void loop()"):]
    # The comment explaining the yield NAMES delay(1), so a check that reads the
    # comments passes on a loop that no longer yields. It did, first time.
    code = re.sub(r"//.*", "", loop)
    t.contains(code, "delay(1)", "the main loop yields to the other tasks")
    t.ok("mutex" in loop, "and says why, so it is not tidied away as a pointless delay",
         "without the reason, the next reader deletes it and the lag comes back")

    # ---- 3. no modem sleep on a station -----------------------------
    web = (F.FIRMWARE / "src/core/WebPortal.cpp").read_text(encoding="utf-8", errors="replace")
    t.contains(web, "WiFi.setSleep(false)",
               "the radio does not doze between beacons")
    idx = web.find("WiFi.setSleep(false)")
    t.ok("WIFI_PS_MIN_MODEM" in web[max(0, idx - 900):idx],
         "with the reason written next to it")

    # ---- 4. the live view chases the board, not a clock -------------
    ui = (F.FIRMWARE / "src/web/WebUI.h").read_text(encoding="utf-8", errors="replace")
    live = ui[ui.find("function camLiveToggle"):]
    live = live[:live.find("\nfunction camStatus")]
    t.ok("setInterval(camShot" not in live,
         "the live view is not on a fixed timer",
         "a 1 s timer on a board that delivers a frame every 140 ms is 7x slower "
         "than the hardware")
    t.contains(live, "cam.stream",
               "it uses the MJPEG stream, not a request per frame")
    t.contains(live, "removeAttribute('src')",
               "and drops the connection when the live view is turned off")
    web = (F.FIRMWARE / "src/core/WebPortal.cpp").read_text(encoding="utf-8", errors="replace")
    t.contains(web, '"/api/cam.stream"', "the board serves an MJPEG stream")
    t.contains(web, "camStreaming_",
               "one viewer at a time — a second would hold one of four connections")
    hub = (F.HUB / "main.py").read_text(encoding="utf-8", errors="replace")
    t.contains(hub, 'what == "cam.stream"', "and the hub can pipe it through")

    # ---- 5. the hub lets a browser KEEP its connection --------------
    # BaseHTTPRequestHandler is HTTP/1.0 by default, so every response closes
    # the socket and a browser opens a new TCP connection for every page asset,
    # every status poll, every pose and every camera frame. Measured here:
    # 12.1 ms per request with a fresh connection, 1.8 ms reusing one — and on
    # a phone across the room it is far worse than that.
    t.contains(hub, 'protocol_version = "HTTP/1.1"',
               "the hub speaks HTTP/1.1, so connections are reused")
    # ...which is only safe because every response carries a length
    send = hub[hub.find("def send_bytes"):]
    send = send[:send.find("\n    def ", 10)]
    t.contains(send, "Content-Length", "every response has a Content-Length")
    stream = hub[hub.find('what == "cam.stream"'):]
    stream = stream[:stream.find('if what == "cam.jpg"')]
    t.contains(stream, "close_connection = True",
               "except the endless camera stream, which opts out by itself")

    # ---- and the behaviour, end to end through the hub --------------
    fake_serial.reset()
    base, main = F.start_hub()
    port = fake_serial.PORT
    for i in range(4):
        F.cmd(base, "POSE " + " ".join(["90"] * 10) + " T 120", port)
    poses = [c for _, c in fake_serial.wire if c.startswith("POSE")]
    t.ok(poses and all(" T " in p for p in poses),
         "every live pose on the wire carries its own duration", poses[:2])
