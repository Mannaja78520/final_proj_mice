"""The USB serial manager: the hub's one owner of every cable.

Moved out of main.py on 2026-09-21 (A26-76 phase 2, see docs/systems/hub.md).
Nothing here changed in behaviour - the same port table, the same per-port
lock, the same reply reader. main.py imports these names back, so every
caller and every check that used main.usb_cmd still reaches this code.

Only this file opens a COM port. Route timing goes to route_latency.LAT.
"""
import re
import threading
import time

import route_latency

# Ports esptool is holding right now: the flasher adds and removes them, and
# _usb_get refuses to open one while it is here.
_flash_ports = set()
_lat_tls = threading.local()   # when this thread's last command hit the wire


# ---------------- USB serial manager: talk to modules over the cable -----
# A COM port can only be opened by ONE program at a time. So the hub is the
# ONE owner of every cable: it opens the port once and SHARES it between all
# of its clients — the module website (/mod?dev=usb:...), Nong Studio (its
# USB link goes through /api/usb/cmd) and the hub's own port probe. Each
# command runs under that port's lock, so the module page and Studio can be
# open on the same cable at the same time instead of one of them getting
# "serial port already in use".
# The port is auto-released after ~10 s with no traffic, so an external tool
# (Arduino IDE, esptool, Studio's optional direct Web Serial mode) can still
# take it when the hub is not talking.
_usb_mgr_lock = threading.Lock()
_usb_open = {}  # port -> {"ser": Serial, "lock": Lock, "last": time}
_usb_touch = {}  # port -> last time a CLIENT (not the probe) used the port
_usb_ident = {}  # port -> last successful probe result (identity cache)
USB_IDLE_CLOSE = 10   # s with no traffic before the port is released
USB_INUSE = 15        # s a port counts as "a client is working on it"


def usb_busy_hint(port, err):
    """Turn pyserial's open() error into something the user can act on."""
    t = str(err)
    if "PermissionError" in t or "Access is denied" in t or "denied" in t.lower() \
            or "Device or resource busy" in t or "errno 16" in t.lower():
        return ("%s is held by another program — the hub shares the cable "
                "between its own pages, but not with outside apps. Close the "
                "Arduino/PlatformIO serial monitor, esptool, or a Nong Studio "
                "tab left in 'USB direct (Web Serial)' mode, then try again."
                % port)
    return t


def _usb_get(port):
    # A flash owns the cable outright: esptool cannot share a port, and the
    # hub re-opening it mid-write is exactly how an upload dies half way.
    if port in _flash_ports:
        raise OSError("%s is being flashed right now — the cable belongs to "
                      "esptool until it finishes" % port)
    # the global lock only guards the dict — the (possibly slow) open()
    # happens under the PER-PORT lock, so one stuck Bluetooth port can
    # never block the other ports
    import serial
    with _usb_mgr_lock:
        ent = _usb_open.get(port)
        if ent is None:
            ent = {"ser": None, "lock": threading.Lock(), "last": time.time()}
            _usb_open[port] = ent
    with ent["lock"]:
        if ent["ser"] is not None and ent["ser"].is_open:
            ent["last"] = time.time()
            return ent
        ser = serial.Serial()
        ser.port = port
        ser.baudrate = 115200
        ser.timeout = 0.15
        ser.dtr = False   # never pulse the ESP32 reset/boot straps
        ser.rts = False
        try:
            ser.open()
            # A FRESH HANDLE MAY HAVE JUST RESET THE BOARD. Opening a port
            # toggles the control lines on some adapters however carefully DTR
            # and RTS are cleared first - measured on an FTDI adapter at the
            # bench, 2026-08-20. Let whatever the board says on the way up land
            # here, once, rather than in the middle of the first reply.
            #
            # THE CAP IS NOT OPTIONAL. Every arriving byte pushes `quiet`
            # forward, so a board that never stops talking pushed it forever
            # and this loop never ended - and because the scan walks every
            # port in turn, ONE noisy board hung the whole module list, not
            # just its own cable. Measured on the bench 2026-08-21: a wedged
            # board on COM26 sent 23,395 lines in three seconds and a probe
            # of six ports never returned. No fake had ever flooded, so 3120
            # passing checks said nothing about it.
            #
            # Both clocks start NOW, so 4 s is the TOTAL, not four seconds
            # after the settle: a quiet board is done in 1.2 s and a talking
            # one is cut off at 4. The cost of the cut is small and known - a
            # board still printing boot lines at 4 s has its INFO reply read
            # out of the noise, which works because a reply is identified by
            # the blank line in front of it, and at worst it is found on the
            # next scan instead of this one.
            quiet = time.time() + 1.2
            hard = time.time() + 4.0
            while time.time() < quiet and time.time() < hard:
                if ser.in_waiting:
                    ser.read(ser.in_waiting)
                    quiet = time.time() + 0.25   # still talking; wait again
                else:
                    time.sleep(0.03)
        except Exception as e:  # noqa: BLE001
            raise OSError(usb_busy_hint(port, e))
        ent["ser"] = ser
        ent["last"] = time.time()
        return ent


def usb_close(port=None):
    """Close cables and say which ones really closed.

    The return value matters: a port somebody is mid-command on is deliberately
    NOT closed (see below), and the caller has to be able to tell. The flasher
    could not - it called this, slept 300ms and ran esptool into a handle that
    was still open, which fails at whatever percent it happens to reach and
    leaves the board sitting in the bootloader. Measured at the bench
    2026-08-20: 21%, "the chip stopped responding", and the same flash from a
    command line with the hub stopped worked first try.
    """
    with _usb_mgr_lock:
        ports = [port] if port else list(_usb_open)
        ents = [(p, _usb_open.pop(p)) for p in ports if p in _usb_open]
    shut = []
    for p_name, ent in ents:
        # take the port's own lock first: never close the handle out from
        # under a command that is mid read/write on it
        got = ent["lock"].acquire(timeout=3)
        if not got:
            # Something is STILL mid read/write on this handle after 3 s — a
            # @peer command waits up to 8. Closing anyway pulled the handle out
            # from under it, which on Windows surfaces as a ClearCommError in
            # the reader or a hang. Put the port back and let the next sweep
            # take it; a cable held open a little longer is not a problem, a
            # command dying mid-flight is.
            with _usb_mgr_lock:
                _usb_open.setdefault(p_name, ent)
            continue
        try:
            if ent["ser"] is not None:
                ent["ser"].close()
            shut.append(p_name)
        except Exception:
            pass
        finally:
            ent["lock"].release()
    return shut


def usb_free(port):
    """True when this hub holds no handle on that cable.

    What the flasher actually needs to know. `usb_close` returning is not the
    same as the port being free: a port it could not lock is put back on
    purpose, and esptool then meets a handle that is still open.
    """
    with _usb_mgr_lock:
        return port not in _usb_open


def usb_in_use(port):
    """True while a client (module page / Studio) is actively using the cable."""
    return time.time() - _usb_touch.get(port, 0) < USB_INUSE


def _usb_reaper():
    while True:
        time.sleep(3)
        with _usb_mgr_lock:
            idle = [p for p, ent in _usb_open.items()
                    if time.time() - ent["last"] > USB_IDLE_CLOSE]
        for p in idle:
            # Look again, immediately before closing. The list above was taken
            # seconds ago and usb_close then waits for the port's own lock, so
            # a command that arrived in between would finish and have its cable
            # shut the instant it let go — the next command failing on a closed
            # port for no reason the user could see.
            with _usb_mgr_lock:
                ent = _usb_open.get(p)
                still_idle = ent and time.time() - ent["last"] > USB_IDLE_CLOSE
            if still_idle and not usb_in_use(p):
                usb_close(p)


# A firmware log line is a bracket tag: "[wifi]", "[sd]", "[  1234][I]" ... —
# only letters/digits/spaces inside the brackets. A JSON reply that starts with
# "[" is always "[{" / "[\"" / "[[" / "[<num>," so it never matches this.
_LOG_LINE = re.compile(r"^\[[\w ]*\]")

# A BOARD THAT JUST REBOOTED, mid-conversation. Opening the port resets some
# boards - measured at the bench 2026-08-20 on an FTDI adapter, where the ESP32
# came up with `ets Jul 29 2019` and `rst:0x1 (POWERON_RESET)` while the hub was
# waiting for a reply. The first-stage ROM log is printed at a different rate
# from the firmware's 115200, so it arrives as NUL bytes and fragments - and
# usb_cmd handed that back as the answer.
#
# That is what made a camera look like a corrupted RS485 module for an hour: the
# same board read DIRECTLY, once the boot log had finished, answered ten times
# out of ten with not one byte lost.
_BOOT_NOISE = re.compile(r"ets [A-Z][a-z]{2} +\d|rst:0x|boot:0x|"
                         r"configsip:|clk_drv:|Brownout detector")


def _drain_to_line_boundary(ser):
    """Throw away whatever the board said before this command.

    This used to also SPIN for up to 80 ms waiting for a half-written log line
    to finish, because an orphaned tail could be mistaken for the reply. That
    cost is paid on every single command, and it is worst exactly when the
    board is chatty — which is now normal, since every module hosts an access
    point and logs about it. On live pose streaming (~30 commands a second)
    it was most of the latency, and the arm visibly lagged the sliders.

    The wait is no longer needed: the firmware writes every reply as
    "
<reply>
", and the reader below identifies the reply by that leading
    blank line. An orphan tail has no blank line in front of it, so it is
    already discarded on its own merits. Clearing the buffer is enough.
    """
    ser.reset_input_buffer()


def usb_cmd(port, cmd, bus_id=0, wait=2.0, client=True):
    """One command line over USB; returns the reply line (RS485-framed when
    bus_id is set, so modules BEHIND this port are controllable too).

    Safe to call from several clients at once (module website + Nong Studio +
    probe): the per-port lock makes each command atomic on the wire, so the
    replies can never interleave. Every answer is timed for route_latency."""
    dev = ("usb:%s:%s" % (port, bus_id)) if bus_id else ("usb:" + port)
    _lat_tls.sent = None
    try:
        reply = _usb_cmd_raw(port, cmd, bus_id, wait, client)
    except Exception:
        if not cmd.startswith("REACH "):
            route_latency.LAT.fail(dev)
        raise
    sent = _lat_tls.sent        # per thread: another caller cannot overwrite it
    if sent and not cmd.startswith("REACH "):   # a forwarded hop is not this route
        route_latency.LAT.record(dev, (time.perf_counter() - sent) * 1000.0, len(reply or ""))
    return reply


def _usb_cmd_raw(port, cmd, bus_id=0, wait=2.0, client=True):
    try:
        return _usb_cmd_once(port, cmd, bus_id, wait, client)
    except TimeoutError:
        raise                  # the module just did not answer — handle is fine
    except OSError:
        # STALE HANDLE. The board was unplugged, reset or re-enumerated while
        # the hub had the port open. pyserial still reports is_open, so the
        # handle never heals itself — Windows fails every write with
        # "The device does not recognize the command" — and the idle reaper
        # never drops it either, because a page polling every ~900 ms keeps the
        # port looking busy. Throw the handle away and open a fresh one, which
        # is all that replugging the cable actually needs.
        usb_close(port)
        try:
            return _usb_cmd_once(port, cmd, bus_id, wait, client)
        except Exception:
            _usb_ident.pop(port, None)   # cached identity is no longer trusted
            raise


# Commands that change WHO a module is. After one of these the cached identity
# is a lie, and the cache is what the hub shows while a cable is busy — so the
# Network tab happily displayed a module's OLD group straight after linking it,
# which is precisely the screen where stale information misleads you.
_IDENTITY_CHANGING = ("GROUP", "SET NAME", "SET ID", "SET TYPE", "SET WIFI")


def _usb_cmd_once(port, cmd, bus_id=0, wait=2.0, client=True):
    # client=False is the latency probe: it must not keep the port looking
    # busy, or it would hold open a cable an outside tool is waiting for.
    if client:
        _usb_touch[port] = time.time()   # a client is working on this cable
    up = cmd.strip().upper()
    if any(up.startswith(k) for k in _IDENTITY_CHANGING):
        _usb_ident.pop(port, None)   # re-probe rather than repeat a stale answer
    ent = _usb_get(port)
    with ent["lock"]:
        if client:
            ent["last"] = time.time()
            _usb_touch[port] = time.time()
        ser = ent["ser"]
        _drain_to_line_boundary(ser)
        line = ("#%d %s" % (bus_id, cmd)) if bus_id else cmd
        ser.write((line + "\n").encode())
        # the wire time starts here: opening the port and waiting for the
        # lock are not the route's latency (route_latency.py)
        _lat_tls.sent = time.perf_counter()
        want = ("@%d " % bus_id) if bus_id else None
        buf, end = b"", time.time() + wait
        # The firmware writes every reply as "\n<reply>\n" in ONE call, so a
        # reply is always preceded by a blank line. That marker is what makes
        # this reliable while the radio is logging: an orphaned TAIL of a log
        # line (the head lost to the buffer clear) has no blank line in front
        # of it, so it can be told apart from a real reply and dropped.
        #
        # Without this, hammering commands during a WiFi reconnect returned
        # every reply shifted by one — "PING" answered "son=8", the tail of
        # "[wifi] disconnected, reason=8". Measured on the bench: 49 of 60.
        #
        # `fallback` keeps a board running older firmware (no leading newline)
        # working: if the window ends without ever seeing the marker, the
        # first plausible line is used, exactly as before.
        saw_blank, fallback = False, None
        rebooted = [False]      # the board restarted while we were waiting
        boots = [0]             # how many times — more than one is a boot LOOP
        brownout = [False]      # and whether the board said why
        while time.time() < end:
            # read(1) returns the moment a byte arrives; read(256) would wait
            # for 256 bytes OR the full port timeout, and a reply like
            # "OK POSE" is 8 bytes — that put a ~150 ms floor under EVERY
            # command and was most of the latency in live/monitor mode.
            chunk = ser.read(1)
            if not chunk:
                continue
            n = ser.in_waiting          # drain whatever landed with it
            if n:
                chunk += ser.read(n)
            buf += chunk
            while (chr(10).encode()) in buf:
                ln, buf = buf.split(chr(10).encode(), 1)
                t = ln.decode(errors="replace").strip()
                # skip blank lines and firmware LOG lines only. A log line is a
                # bracket TAG like "[wifi] ...", "[sd] ...", "[  1234][I]...".
                # A JSON ARRAY reply (PIN VALID -> "[{...}]") also starts with
                # "[" but must NOT be skipped — that was the bug that made pin
                # config work over WiFi but come back empty over USB. Treat as a
                # log line only when the "[...]" holds a plain tag (letters,
                # digits, spaces), never "[{" / "[\"" / "[[" which start JSON.
                if not t:
                    saw_blank = True
                    continue
                if _LOG_LINE.match(t):
                    saw_blank = False   # a log line ended; no marker any more
                    continue
                # Boot output is not an answer. It also means the board has
                # just restarted, so whatever we asked never reached the
                # firmware - the caller gets a timeout and can ask again,
                # rather than a reply built out of a reset.
                if _BOOT_NOISE.search(t):
                    rebooted[0] = True
                    # ONE reset is a coincidence; four in eight seconds is a
                    # power fault. `rst:0x` is printed exactly once per boot, so
                    # counting it separates the two - and they have completely
                    # different fixes, which is the whole point of telling them
                    # apart. Measured on the bench 2026-08-20: a 30-pin board
                    # with a MAX485 attached rebooted every 1.6 s and the hub
                    # called it "no reply", which sent an afternoon into
                    # checking bus wiring that was never wrong.
                    if "rst:0x" in t:
                        boots[0] += 1
                    if "Brownout" in t:
                        brownout[0] = True
                    saw_blank = False
                    continue
                # A LINE WITH NUL BYTES IN IT IS NEVER AN ANSWER.
                #
                # _BOOT_NOISE matches clean ASCII, and the whole reason this
                # exists is that the ROM log arrives at ANOTHER BAUD - so it
                # arrives as NULs and fragments, and a garbled boot line
                # matches none of the patterns above. It then became `fallback`
                # and was handed back as the reply, which is precisely the bug
                # the boot-noise work was written to stop, surviving in the one
                # form it takes most often. Found by a model review 2026-08-20.
                #
                # Nothing the firmware sends contains a NUL: every reply is one
                # line of text written in one call (see main.cpp emitLine), so
                # this cannot throw away a real answer.
                if "\x00" in t:
                    rebooted[0] = True
                    saw_blank = False
                    continue
                if not saw_blank:
                    # A BUS REPLY CARRIES ITS OWN MARKER, and needs no blank
                    # line in front of it. `@<id> ` IS the RS485 frame format,
                    # so it identifies a reply at least as surely as the blank
                    # line does — an orphaned log tail cannot start with it.
                    #
                    # This matters for a plain USB-RS485 dongle, where there is
                    # no board on the cable to re-emit the frame. A bridging
                    # board wraps what it heard on the bus in the usual
                    # "\n<reply>\n" (main.cpp's rs485.onBusLine → emitLine); a
                    # dongle is just wire, and the frame arrives raw. Measured
                    # 2026-08-20: `#1 PING` through a dongle answered
                    # `@1 PONG 1 lift lift` on the wire, and the hub reported
                    # "no reply from COM23 (bus id 1)" — it had read the answer
                    # and thrown it away.
                    if want and t.startswith(want):
                        return t[len(want):]
                    # no blank line in front of this: either an orphan tail, or
                    # a board on older firmware. Remember it and keep looking.
                    if fallback is None:
                        fallback = t
                    continue
                saw_blank = False
                if want:
                    if t.startswith(want):
                        return t[len(want):]
                elif not t.startswith(("#", "@", "->")):
                    return t
        if fallback is not None and not want and not rebooted[0]:
            return fallback          # older firmware: no blank-line marker
        # SAY THAT IT REBOOTED. "no reply" sends somebody looking at wiring; a
        # board that restarted mid-command is a different problem with a
        # different fix, and the hub can see the difference in the boot log it
        # just read.
        # A BOOT LOOP IS NOT A SLOW BOARD. Three different failures, three
        # different next steps, and the hub can tell them apart from the boot
        # log it just read - so it should, rather than making somebody take a
        # meter to the bus to find out.
        if brownout[0] or boots[0] > 1:
            raise TimeoutError(
                "%s is restarting over and over - %d times while waiting%s. "
                "The board resets before it can answer anything, so this is a "
                "POWER fault, not wiring and not the bus. Check that the RS485 "
                "transceiver is fed from 5V/VIN rather than 3.3V, and that the "
                "USB port can supply the current spike when the radio starts."
                % (port, boots[0],
                   ", saying 'Brownout detector was triggered'"
                   if brownout[0] else ""))
        raise TimeoutError(
            ("%s restarted while answering - the command never reached the "
             "firmware. Ask again." % port) if rebooted[0] else
            ("no reply from " + port +
             ((" (bus id %d)" % bus_id) if bus_id else "")))
