"""A board reached several ways is driven over the fastest one.

Asked 2026-09-21: *when we connect rs485 and usb and wifi so use the less
letency as possible*. Measured that day on nong 67: a small command took
~59 ms over the PC hotspot; a 1.2 KB status reply took 138 ms over RS485
and 106 ms over WiFi. So no fixed order is right - the hub has to measure.

The rules below came from a Codex review of the design, and each is here
because breaking it produces a wrong choice nobody would see:

  * only SMALL replies are scored - a big reply is slow on RS485 because of
    its size, not because the route is slow;
  * a route that fails is dropped at once, with no hysteresis, and is not
    tried again while another route is untried (A26-7: WiFi leads the
    fallback order, so a board that left WiFi was sent to the dead address
    on every call while its cable sat untimed);
  * a faster route must win by a margin for several NEW samples before the
    choice moves - the hub asks on every command, and three calls in 30 ms
    prove nothing, so WiFi jitter cannot flip the choice back and forth;
  * a COM port or IP reused by another board starts from zero;
  * the latency probe never counts as a client using the cable, or it would
    hold open a port an outside tool is waiting for;
  * `auto:<board>` is resolved on every call, so a page opened on it follows
    the board when the best route changes.
"""
import json
import sys
import threading
import time

import qc as F

AREA = "connection"
TITLE = "a board reached several ways is driven over the fastest one"


class Answering:
    """A port that answers every command at once."""

    def __init__(self):
        self.pending = b""

    def write(self, b):
        self.pending += b"\nPONG 5 qc nong\n"
        return len(b)

    @property
    def in_waiting(self):
        return len(self.pending)

    def read(self, n=1):
        got, self.pending = self.pending[:n], self.pending[n:]
        if not got:
            time.sleep(0.01)
        return got

    def reset_input_buffer(self):
        pass

    is_open = True


def run(t):
    sys.path.insert(0, str(F.HUB))
    import route_latency  # noqa: PLC0415
    import main  # noqa: PLC0415

    # ---- the choice itself ------------------------------------------------
    L = route_latency.Latency()
    L.cfg.update(switchAfterSamples=3, switchMarginMs=5, switchMarginPct=20)
    a, b = "wifi:10.0.0.5", "usb:COM9:5"
    L.record(a, 60)
    t.eq(L.choose("k", [a, b]), a, "with one route measured, that one is used")
    L.record(b, 10)
    calls = [L.choose("k", [a, b]) for _ in range(4)]
    t.ok(calls == [a] * 4,
         "a faster route does not win on one sample, however often it is asked",
         "got %s" % calls)
    for _ in range(3):
        time.sleep(0.002)
        L.record(b, 10)
        got = L.choose("k", [a, b])
    t.eq(got, b, "after several fresh samples the faster route takes over")

    L.record(a, 9.5)                       # smoothed, a stays well above b
    t.eq(L.choose("k", [a, b]), b, "a small wobble does not move it back")

    L.fail(b)
    t.eq(L.choose("k", [a, b]), a, "a failed route is dropped at once")

    # MEASURED ON NONG 67: RS485 6 ms, WiFi 95 ms - and the first version
    # never switched, because it counted calls to choose() and the samples
    # had all arrived before the first call. Samples are what count.
    L3 = route_latency.Latency()
    L3.record(a, 90)
    L3.choose("k3", [a, b])                # WiFi in use
    for _ in range(15):
        L3.record(b, 6)                    # the cable is timed meanwhile
    t.eq(L3.choose("k3", [a, b]), b,
         "samples gathered between two choices still move the choice")

    L2 = route_latency.Latency()
    L2.record(b, 10)
    L2.choose("k2", [a, b])                # b chosen; a never measured
    L2.fail(b)
    t.eq(L2.choose("k2", [a, b]), a,
         "a failed route is dropped even when nothing else is measured yet")

    # A26-7: a route that just failed is not the fallback while another is
    # untried - WiFi leads the order, and the cable may never have been timed.
    L4 = route_latency.Latency()
    L4.record(a, 60)
    L4.choose("k4", [a, b])                # WiFi in use, the cable untimed
    L4.fail(a)
    t.eq(L4.choose("k4", [a, b]), b,
         "a route that just failed is not tried again while another is untried")
    time.sleep(0.05)                       # Windows' clock ticks every ~16 ms
    L4.fail(b)
    t.eq(L4.choose("k5", [a, b]), a,
         "with every route failed lately, the one that failed longest ago is tried")
    time.sleep(0.05)
    L4.fail(a)                             # the dead WiFi fails again
    t.eq(L4.choose("k5", [a, b]), b,
         "and one cable timeout does not keep sending calls to the dead WiFi")
    L4.record(b, 80, reply_len=5000)       # b answers again, with a big reply
    t.eq(L4.choose("k6", [a, b]), b,
         "a route that answers again, whatever the size, is back in the order")
    L4.cfg["failHoldSec"] = 0
    t.eq(L4.choose("k7", [a, b]), a,
         "and a failure is held only for failHoldSec")

    # A failed route that is still `cur` - a choose() racing fail() writes it
    # back - yields to one that has not failed, and a new board on an address
    # does not inherit the old one's failure.
    L5 = route_latency.Latency()
    L5.choose("k8", [a, b])
    L5.fail(a)
    L5._chosen["k8"] = a                   # noqa: SLF001 - the racing write
    t.eq(L5.choose("k8", [a, b]), b, "a route that just failed does not win by being current")
    L5.bind(a, "board-A")
    L5.fail(a)
    L5.bind(a, "board-B")
    t.eq(L5.choose("k9", [a, b]), a,
         "another board on the same address does not inherit its failure")
    cfg = json.loads((F.CODE / "config" / "route_latency.json").read_text(encoding="utf-8"))
    t.ok(cfg.get("failHoldSec") == route_latency.DEFAULTS["failHoldSec"],
         "the hold is a tunable in config/route_latency.json", cfg)

    L.record("usb:COM1", 5, reply_len=5000)
    t.ok(L.ms("usb:COM1") is None, "a big reply is not scored as a slow route")

    L.record("usb:COM2", 5)
    L.bind("usb:COM2", "board-A")
    L.bind("usb:COM2", "board-B")
    t.ok(L.ms("usb:COM2") is None,
         "another board on the same port starts from zero")

    # ---- the hub stamps and resolves --------------------------------------
    saved = route_latency.LAT
    try:
        _hub(t, main, route_latency)
    finally:
        route_latency.LAT = saved


def _hub(t, main, route_latency):
    route_latency.LAT = route_latency.Latency()
    m = {"key": "chip/QC1", "wifi_mode": "sta", "routes": [
        {"kind": "wifi", "dev": "wifi:10.0.0.9", "ip": "10.0.0.9"},
        {"kind": "rs485", "dev": "usb:COM77:5", "port": "COM77", "bus": 5}]}
    route_latency.LAT.record("usb:COM77:5", 12)
    main._pick_route(m)                                       # noqa: SLF001
    t.eq(m.get("best"), "usb:COM77:5", "the board is stamped with its fastest route")
    t.ok(any(r.get("ms") == 12 for r in m["routes"]),
         "and each measured route carries its ms for the page")
    ip, dev = main.split_hub_dev("auto:chip/QC1")
    t.eq((ip, dev), (None, "usb:COM77:5"),
         "auto:<board> resolves to that route on the call itself")

    off = dict(m, wifi_mode="off", key="chip/QC2")
    main._pick_route(off)                                     # noqa: SLF001
    t.ok("wifi:10.0.0.9" not in main._route_table["chip/QC2"],  # noqa: SLF001
         "a board whose radio is off is never sent over WiFi")

    # ---- the cable path times itself; the probe is not a client -----------
    port = "COM_QC_LAT"
    main._usb_open[port] = {"ser": Answering(), "lock": threading.Lock(),  # noqa: SLF001
                            "last": 0}
    main._usb_touch.pop(port, None)                           # noqa: SLF001
    try:
        main.usb_cmd(port, "PING", 0, wait=1.0, client=False)
        t.ok(port not in main._usb_touch,                     # noqa: SLF001
             "the probe does not mark the cable as in use",
             "it would keep open a port an outside tool is waiting for")
        t.ok(route_latency.LAT.ms("usb:" + port) is not None,
             "a command over the cable records how long the wire took")
        main.usb_cmd(port, "PING", 0, wait=1.0)
        t.ok(port in main._usb_touch,                         # noqa: SLF001
             "while a real client's command still does")
    finally:
        main._usb_open.pop(port, None)                        # noqa: SLF001
        main._usb_touch.pop(port, None)                       # noqa: SLF001

    _dead_wifi(t, main, route_latency)

    # ---- the page uses it -------------------------------------------------
    hub = (F.HUB / "web" / "hub.html").read_text(encoding="utf-8")
    t.ok("'auto:'+m.key" in hub, "Open module uses auto: when there is a choice")
    t.ok("const sdev = auto ? 'auto:'+m.key : dev" in hub,
         "Studio keeps auto:<board>, so an open page follows route changes")


def _dead_wifi(t, main, route_latency):
    """A26-7 on the wire: the board left WiFi, the hub's record still lists the
    address (no sweep has marked it stale) and the cable was never timed."""
    route_latency.LAT = route_latency.Latency()
    port, ip = "COM_QC_LAT2", "10.0.0.99"
    m = {"key": "chip/QC3", "wifi_mode": "sta", "routes": [
        {"kind": "wifi", "dev": "wifi:" + ip, "ip": ip},
        {"kind": "usb", "dev": "usb:" + port, "port": port}]}
    main._pick_route(m)                                       # noqa: SLF001
    t.eq(m.get("best"), "wifi:" + ip, "an untimed board starts on WiFi, the usual order")
    # Only this thread's traffic counts: a hub another check started in this
    # process runs its latency probe, which PINGs these same routes.
    me = threading.get_ident()

    class Cable(Answering):
        got = b""

        def write(self, b):
            if threading.get_ident() == me:
                self.got += b
            return super().write(b)

    cable = Cable()
    main._usb_open[port] = {"ser": cable, "lock": threading.Lock(),  # noqa: SLF001
                            "last": time.time()}
    tried = []

    def gone(addr, path, timeout=None):
        if threading.get_ident() == me:
            tried.append(addr)
        raise OSError("timed out")        # what a vanished address gives

    real = main.Handler.__dict__["robot_get"]
    main.Handler.robot_get = staticmethod(gone)
    try:
        for _ in range(3):
            try:
                reply = main.dev_cmd("auto:chip/QC3", "PING", wait=1.0)
            except Exception as e:                            # noqa: BLE001
                reply = "raised: %s" % e
        t.ok(tried == [ip],
             "the dead WiFi address is tried once, not on every call",
             "tried %s" % tried)
        t.ok(cable.got.count(b"PING") == 2 and "PONG" in reply,
             "the next commands reach the cable", "cable got %r, last reply %r"
             % (cable.got, reply))

        # The page's own status poll is a call too (review 2026-09-29): /mod
        # polls /api/dev/status every 900 ms, and an idle page sends nothing else.
        route_latency.LAT = route_latency.Latency()
        main._pick_route(m)                                   # noqa: SLF001
        del tried[:]
        cable.got = b""
        for _ in range(3):
            try:
                main.dev_status("auto:chip/QC3")
            except Exception:                                 # noqa: BLE001
                pass
        t.ok(tried == [ip],
             "the page's status poll tries the dead WiFi address once, not every time",
             "tried %s" % tried)
        t.ok(cable.got.count(b"INFO") == 2,
             "and then reads the board over the cable", "cable got %r" % cable.got)
    finally:
        main.Handler.robot_get = real
        main._usb_open.pop(port, None)                        # noqa: SLF001
        main._usb_touch.pop(port, None)                       # noqa: SLF001
        main._route_table.pop("chip/QC3", None)               # noqa: SLF001
