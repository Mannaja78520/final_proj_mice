"""The USB cable: one port, several clients, and a board that gets replugged.

Every assertion here is a bug that actually happened. The cable is the single
shared resource in the system, so it breaks the module website and Nong Studio
at the SAME time — which is the signature to look for when a user says
"nothing works".
"""
import threading
import time

import fake_serial
import qc as F

AREA = "connection"
TITLE = "USB cable sharing, recovery and latency"
SLOW = False

PORT = fake_serial.PORT


def run(t):
    fake_serial.reset()
    base, main = F.start_hub()

    # ---- the cable is visible at all -------------------------------
    s, b = F.get(base + "/api/ports")
    t.contains(b, PORT, "the hub lists the module's cable")

    # ---- THE headline bug: "serial already in use" -------------------
    # The module website (/api/dev/*) and Nong Studio (/api/usb/*) must be
    # able to drive one cable at the same time. Windows COM ports are
    # exclusive, so the hub has to own the handle and share it.
    errs, page_hits, studio_hits = [], [], []

    def module_page():
        for _ in range(15):
            s, b = F.get("%s/api/dev/status?dev=usb:%s" % (base, PORT))
            (page_hits if s == 200 and '"type"' in b else errs).append(b[:120])
            time.sleep(0.02)

    def studio():
        for _ in range(30):
            s, b = F.cmd(base, "POSE " + " ".join(["90"] * 10))
            (studio_hits if s == 200 else errs).append(b[:120])
            time.sleep(0.01)

    th = [threading.Thread(target=module_page), threading.Thread(target=studio)]
    [x.start() for x in th]
    [x.join() for x in th]

    t.eq(errs, [], "module page + Studio drive one cable together")
    t.eq(len(page_hits), 15, "every module-page poll answered")
    t.eq(len(studio_hits), 30, "every Studio command answered")

    # replies must never be handed to the wrong client
    t.ok(all('"type": "nong"' in h or '"type":"nong"' in h for h in page_hits),
         "no reply crossed between clients")

    # ---- one handle, not one per client -----------------------------
    t.under(len(fake_serial.opens), 3,
            "the port is opened once and shared, not per client", " opens")

    # ---- LATENCY. This guards a real regression: replies were read with
    # read(256), and pyserial waits for 256 bytes OR the port timeout, so
    # every command cost ~150 ms and live mode felt like stepping.
    lat = []
    for _ in range(10):
        t0 = time.time()
        F.cmd(base, "POSE " + " ".join(["90"] * 10))
        lat.append((time.time() - t0) * 1000)
    lat.sort()
    t.under(lat[5], 90, "a pose command stays well under the live-mode budget", " ms")

    # ---- RS485 framing: reaching a module BEHIND another one ---------
    s, b = F.cmd(base, "INFO", bus=2)
    t.contains(b, '"type"', "a bus-framed command round-trips and is unwrapped")
    t.ok(not b.startswith("@"), "the @id frame is stripped from the reply", b[:80])

    # ---- a busy cable must say what to close, not spew a traceback ---
    held = fake_serial.Serial(port=PORT)
    F.get(base + "/api/usb/close?port=" + PORT)
    time.sleep(0.2)
    try:
        held.open()                      # something else grabs the cable
        s, b = F.cmd(base, "INFO")
        t.ok(s != 200, "a busy cable is reported as an error")
        low = b.lower()
        t.ok(any(w in low for w in ("close", "using", "in use", "another")),
             "the busy message says what to close", b[:200])
    finally:
        held.close()

    # ---- replug: the handle goes stale and must heal itself ----------
    # Windows keeps the handle "open" after the board re-enumerates, and the
    # idle reaper never drops it because a polling page keeps it looking busy.
    F.cmd(base, "INFO")                                  # hub holds a handle
    n_before = len(fake_serial.opens)
    fake_serial.dead[0] = True                           # board goes away
    s, b = F.cmd(base, "INFO")
    t.contains(b, '"type"', "a command still answers after a replug")
    t.ok(len(fake_serial.opens) > n_before,
         "it reopened the cable instead of writing to a dead handle")
    s, b = F.get("%s/api/dev/status?dev=usb:%s" % (base, PORT))
    t.contains(b, '"type"', "the module website recovers from a replug too")
    fake_serial.dead[0] = False

    # ---- a silent module must fail FAST, not retry forever ----------
    t0 = time.time()
    F.get("%s/api/usb/cmd?port=COM_NOPE&c=INFO" % base)
    t.under(time.time() - t0, 12, "an absent port gives up quickly", " s")
