"""The hub can flash a board over its own cable — and gives the cable up to do it.

The hub owns every COM port and shares it between its pages. esptool cannot
share: it needs the port to itself. Every `port is busy` failure on the bench
was that. So the interesting part of flashing is not "did it run", it is
whether the hub really let go of the cable and took it back afterwards.

Since the firmware is built per module type, "flash this board as a nong" is a
real instruction. What must hold:

  * the hub says honestly what it can flash, and what is missing when it can't
  * while esptool holds the cable, nothing else on the hub may open it
  * a failure is reported in words that say what to do, not swallowed
  * the cable works again afterwards

A fake esptool stands in for the real one (MICE_ESPTOOL), so this runs with no
board plugged in and never writes to hardware.
"""
import json
import os
import sys
import time
import urllib.error

import fake_serial
import qc as F

AREA = "firmware"
TITLE = "the hub flashes a board, and hands the cable over to do it"
SLOW = False

# A stand-in esptool: prints what the real one prints, exits with the code the
# check asks for. `--qc-fail` makes it fail the way a board that is not there
# does, so the error path is exercised, not imagined.
FAKE = '''import sys, time
fail = "--qc-fail" in sys.argv
print("esptool.py v4.9.0")
print("Serial port %s" % (sys.argv[sys.argv.index("--port") + 1] if "--port" in sys.argv else "?"))
print("Connecting........_____....._____")
if fail:
    print("A fatal error occurred: Failed to connect to ESP32: No serial data received.")
    sys.exit(2)
print("Chip is ESP32-D0WD-V3 (revision v3.0)")
for p in (0, 25, 50, 75, 100):
    print("Writing at 0x00010000... (%d %%)" % p)
    sys.stdout.flush()
    time.sleep(0.06)
print("Hash of data verified.")
print("Hard resetting via RTS pin...")
'''


def _fake(tmp, fail=False):
    f = tmp / "fake_esptool.py"
    f.write_text(FAKE, encoding="utf-8")
    cmd = '"%s" "%s"' % (sys.executable, f)
    return cmd + (" --qc-fail" if fail else "")


def _json(r):
    return json.loads(r[1])


def _wait_done(base, limit=20.0):
    end = time.time() + limit
    while time.time() < end:
        s = _json(F.get(base + "/api/flash"))
        if not s["running"]:
            return s
        time.sleep(0.05)
    return _json(F.get(base + "/api/flash"))


def run(t):
    import tempfile
    from pathlib import Path
    tmp = Path(tempfile.mkdtemp(prefix="qc_flash_"))
    os.environ["MICE_ESPTOOL"] = _fake(tmp)
    try:
        fake_serial.reset()
        base, main = F.start_hub()
        port = fake_serial.PORT

        # ---- 1. what can this PC flash, honestly --------------------
        info = _json(F.get(base + "/api/flash/images"))
        t.ok(info.get("esptool") is True, "the hub found esptool", info.get("why"))
        by = {i["type"]: i for i in info.get("images", [])}
        t.ok(set(by) >= {"nong", "lift"},
             "it offers a build per module type", sorted(by))
        for ty in ("nong", "lift"):
            im = by.get(ty, {})
            t.contains(im.get("env", ""), "mice_" + ty,
                       "%s comes from its own env" % ty)
            if im.get("ready"):
                t.ok(im["bytes"] > 500000,
                     "%s image is a real firmware (%d bytes)" % (ty, im["bytes"]))
            else:
                # not a failure: this PC may simply never have built it. But it
                # must SAY so, and name what to build.
                t.ok(im.get("missing"),
                     "%s is not offered without saying what is missing" % ty)

        # Use whatever this PC has actually built. Pinning it to one type made
        # the check fail for a reason that is not a regression: PlatformIO
        # clears stale env folders whenever platformio.ini changes, so the type
        # that happens to be built moves around.
        ready = [ty for ty, im in by.items() if im.get("ready")]
        if not ready:
            t.give_up("no firmware built on this PC — run pio run -e mice_nong")
        use = "nong" if "nong" in ready else ready[0]

        # ---- 2. a bad request is refused, with a reason -------------
        r = _json(F.post(base + "/api/flash?port=%s&type=nope" % port))
        t.ok(r.get("ok") is False, "an unknown module type is refused")
        t.contains(r.get("error", ""), "pio run -e mice_nope",
                   "and it says how to make that firmware exist")
        r = _json(F.post(base + "/api/flash?type=nong"))
        t.ok(r.get("ok") is False, "a flash with no port is refused")

        # ---- 3. the cable is REALLY handed over ---------------------
        F.cmd(base, "PING", port)                 # the hub is holding it now
        st = _json(F.post(base + "/api/flash?port=%s&type=%s" % (port, use)))
        t.ok(st.get("port") == port and st.get("ok") is None,
             "the flash starts", st)
        seen_guard = False
        end = time.time() + 5
        while time.time() < end:
            s = _json(F.get(base + "/api/flash"))
            code, body = F.cmd(base, "PING", port, timeout=5)
            if code != 200 and "flash" in body.lower():
                seen_guard = True
                break
            if not s["running"]:
                break
            time.sleep(0.05)
        t.ok(seen_guard,
             "while esptool holds the cable, nothing else on the hub may open it",
             "the hub re-opening the port mid-write is how an upload dies")

        s = _wait_done(base)
        t.ok(s["ok"] is True, "the flash finishes", s.get("error"))
        t.eq(s["percent"], 100, "and reports 100%")
        t.contains(" ".join(s["log"]), "Hash of data verified",
                   "the log carries what esptool actually said")
        # every image goes down, at the offsets a full ESP32 flash needs
        cmdline = s["log"][0]
        for off in ("0x1000", "0x8000", "0xe000", "0x10000"):
            t.contains(cmdline, off, "it writes the %s image" % off)
        t.contains(cmdline, "mice_" + use, "from the %s build, not another type" % use)

        # ---- 4. and the hub takes the cable back --------------------
        code, body = F.cmd(base, "PING", port)
        t.ok(code == 200, "the cable works again afterwards", body)
        t.contains(body, "PONG", "the module answers on it")

        # ---- 5. a failure is reported, in words you can act on ------
        os.environ["MICE_ESPTOOL"] = _fake(tmp, fail=True)
        F.post(base + "/api/flash?port=%s&type=%s" % (port, use))
        s = _wait_done(base)
        t.ok(s["ok"] is False, "a board that does not answer is a FAILURE")
        t.contains(s["error"].lower(), "boot",
                   "and the message says to hold BOOT/IO0")
        code, body = F.cmd(base, "PING", port)
        t.ok(code == 200, "the cable is released even when the flash fails", body)

        # ---- 6. the page offers it where it is useful ---------------
        hub = (F.HUB / "web" / "hub.html").read_text(encoding="utf-8", errors="replace")
        t.contains(hub, "/api/flash", "the hub page can flash")
        t.contains(hub, "confirm(",
                   "and asks before overwriting a board's firmware")
        box = hub[hub.find("function flashBox"):]
        box = box[:box.find("\n  return box;")]
        t.contains(box, "esptool", "it explains when esptool is missing")
        t.contains(box, "no firmware built", "and when nothing has been built yet")
        t.contains(box, "aria-live", "progress is announced, not just painted")
    finally:
        os.environ.pop("MICE_ESPTOOL", None)

    # ---- a type you cannot flash YET must still be visible --------------
    # The picker used to list only what was built and drop the rest in
    # silence. On a PC where only `cam` had been built that showed ONE choice
    # and no hint that nong or lift existed, let alone how to get them. A
    # disabled option has to say what would enable it.
    #
    # Assert INSIDE flashBox(), not against the whole page: the words "pio run
    # -e" and "not built" also appear in the all-empty message further down, so
    # a file-wide search passed against every sabotage of this.
    hub = (F.HUB / "web/hub.html").read_text(encoding="utf-8", errors="replace")
    i = hub.find("function flashBox(")
    j = hub.find("\nfunction ", i + 10)
    body = hub[i:j if j > 0 else len(hub)]
    t.ok(i >= 0, "the flash picker exists")

    t.contains(body, "filter(i=>!i.ready)",
               "the picker looks at the types it CANNOT flash, not only the ready ones")
    k = body.find("filter(i=>!i.ready)")
    tail = body[k:k + 700] if k >= 0 else ""
    t.contains(tail, "disabled=true",
               "and lists them disabled, so they cannot be picked by mistake")
    t.contains(tail, "not built on this PC yet",
               "saying plainly why each one is unavailable")
    t.contains(tail, "notBuilt.map(i=>i.env)",
               "and naming the exact build command for those types",
               )
