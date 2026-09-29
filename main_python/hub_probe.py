"""Which module is on which cable: list the ports, then ask each one.

Moved out of main.py on 2026-09-22 (A26-93, see docs/systems/hub-usb.md).
Nothing here changed in behaviour; main.py imports these names back. The
probe talks only through hub_usb's shared port table, never its own handle.
"""
import json
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutTimeout

from hub_usb import (_drain_to_line_boundary, _flash_ports, _usb_get, _usb_ident,
                     usb_close, usb_in_use)


def serial_ports():
    """USB serial ports on this PC, WITH their device type — so Bluetooth
    phantom ports (which hang for ~40 s when opened) can be skipped up
    front instead of probed. Returns [{"port","desc","bt"}]."""
    out = []
    try:
        from serial.tools import list_ports
        for p in sorted(list_ports.comports(), key=lambda x: x.device):
            desc = (p.description or "") + " " + (p.hwid or "")
            bt = "bluetooth" in desc.lower() or "BTHENUM" in desc
            out.append({"port": p.device, "desc": p.description or "", "bt": bt})
        return out
    except ImportError:
        pass
    if sys.platform == "win32":
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                 r"HARDWARE\DEVICEMAP\SERIALCOMM")
            i = 0
            while True:
                try:
                    name, val, _ = winreg.EnumValue(key, i)
                    out.append({"port": str(val), "desc": str(name),
                                "bt": "BTHENUM" in str(name)})
                    i += 1
                except OSError:
                    break
        except OSError:
            pass
    else:
        import glob
        for p in sorted(glob.glob("/dev/ttyUSB*") + glob.glob("/dev/ttyACM*")):
            out.append({"port": p, "desc": "", "bt": False})
    return out


# ---------------- USB / RS485 probing (which module is on which port?) ----
# Opens each port briefly, asks INFO (a module plugged in directly answers
# with its identity + WiFi ip), then broadcasts "#* PING" so every module on
# the RS485 bus behind that port answers too — works both through a module
# (it bridges '#' lines onto the bus) and through a bare USB-RS485 dongle.
def _read_lines(ser, seconds, quiet=0.0, at_least=0.0):
    """Lines for `seconds`, or until the port has been quiet for `quiet`.

    The quiet rule exists for the RS485 census. Modules stagger their answers
    to a broadcast by their own id so the replies do not collide, so the LAST
    board to speak is the one with the highest id - which makes a fixed window
    a limit on which boards exist as far as the hub is concerned. Measured on
    the bench 2026-08-19: a nong with id 67 answered 1344 ms after the
    broadcast, while this waited 0.8 s. It was invisible, and reported no
    error, which reads exactly like an empty bus.

    Waiting for quiet instead means one quick board costs a fifth of a second
    and a high id is still found, up to the cap.
    """
    lines, buf = [], b""
    started = time.time()
    end = started + seconds
    last = started
    while time.time() < end:
        chunk = ser.read(256)
        if not chunk:
            # Quiet only counts AFTER the floor. A quick board answers in 20 ms
            # and the next one may be a second behind it, so stopping at the
            # first silence hears the fast boards and calls the rest absent -
            # which is the bug this whole rule exists to fix, moved rather than
            # removed.
            if (quiet and lines
                    and (time.time() - started) >= at_least
                    and (time.time() - last) >= quiet):
                break
            continue
        last = time.time()
        buf += chunk
        while (chr(10).encode()) in buf:
            ln, buf = buf.split(chr(10).encode(), 1)
            t = ln.decode(errors="replace").strip()
            if t and not t.startswith("["):
                lines.append(t)
    return lines


def _wifi_of(st):
    w = st.get("wifi") or {}
    return {"ip": w.get("ip", ""), "wifi_mode": w.get("mode", "")}


def probe_usb_port(port, full=False):
    """Identify the module on a COM port + every RS485 module behind it.

    While a client is DRIVING that cable (module website open, Nong Studio
    connected) the full probe is skipped: it would hold the port's lock for
    ~1.5 s every round and stutter their commands. The identity is already
    known from the first probe, so the cached answer is returned with
    "inuse": True instead.

    `full` forces the bus census anyway: Studio asks for it once, right after
    its own commands on that cable got no reply (an RS485 adapter, 2026-09-17)."""
    out = {"port": port, "module": None, "rs485": [], "error": ""}
    try:
        import serial  # noqa: F401
    except ImportError:
        out["error"] = "pyserial not installed (pip install pyserial)"
        return out
    light = usb_in_use(port) and not full
    # ONE LOOKUP, not a test and then a read. Another thread pops this key the
    # moment a command changes a board's identity (GROUP, SET NAME) - exactly
    # while `light` is true, which is the only case this path is for - so the
    # test could pass and the read raise KeyError, turning a cached answer into
    # a bare 500. Found 2026-08-21.
    cached = _usb_ident.get(port) if light else None
    if cached is not None:
        cached = dict(cached)
        cached["inuse"] = True
        return cached
    try:
        ent = _usb_get(port)  # shared manager: no conflict with the proxy
    except Exception as e:  # held by an outside program, or not a module
        out["error"] = str(e)
        return out
    with ent["lock"]:
        ent["last"] = time.time()
        ser = ent["ser"]
        try:
            _drain_to_line_boundary(ser)
            # 1) directly connected module?
            ser.write(b"INFO\n")
            for ln in _read_lines(ser, 0.6):
                if ln.startswith("{"):
                    try:
                        st = json.loads(ln)
                        out["module"] = {"id": st.get("id"), "name": st.get("name"),
                                         "type": st.get("type"),
                                         "group": st.get("group", ""),
                                         # The chip MAC, when the board runs
                                         # firmware new enough to report it.
                                         # Without it the same board found on a
                                         # cable and on WiFi cannot be told to
                                         # be one board - see modules_here.
                                         "chip": st.get("chip", ""),
                                         # "audio" = a speaker (A4-3)
                                         "caps": st.get("caps") or [],
                                         **_wifi_of(st)}
                        break
                    except ValueError:
                        pass
            if light:  # in use: identify only, never hold the cable for a bus census
                out["inuse"] = True
                if out["module"]:
                    _usb_ident[port] = dict(out)
                return out
            # 2) census of the RS485 bus behind this port
            _drain_to_line_boundary(ser)
            ser.write(b"#* PING\n")
            seen = {}
            # 5.4 s is the worst case an OLD board can take: the stagger
            # was id x 20 ms and ids go to 247. It almost never costs
            # that, because the read stops once the bus has been quiet
            # for 300 ms - one board with a low id is a fifth of a
            # second. Current firmware answers within 240 ms whatever
            # the id (RS485Bus.cpp).
            # 1.6 s floor, then stop when the bus goes quiet, cap 5.4 s.
            #
            # The floor is what makes a late board findable: with the OLD
            # stagger of id x 20 ms it covers every id up to 80, and current
            # firmware answers within 240 ms whatever the id. The cap is the
            # true worst case, id 247 on old firmware.
            #
            # THE LIMIT, said out loud: a board running old firmware with an id
            # above 80 answers after the floor and may be missed if nothing
            # else is talking. Reflashing it fixes that permanently, because
            # the bounded stagger lands every board inside the floor.
            for ln in _read_lines(ser, 5.4, quiet=0.3, at_least=1.6):
                m = re.match(r"^@(\d+)\s+PONG\s+(\d+)\s+(.+)\s+(\S+)$", ln)
                if m:
                    seen[int(m.group(1))] = {"id": int(m.group(1)), "name": m.group(3),
                                             "type": m.group(4), "ip": "", "wifi_mode": ""}
            # ask each bus module for its INFO to learn its WiFi ip (for links)
            #
            # THE LIMIT, said out loud: only the first SIX are asked. Each ask
            # costs up to 0.6 s and the scan walks every port, so a seventh
            # board on one bus keeps an empty group and chip - it is listed
            # and reachable, but reads as "not linked" the way every bus board
            # did before A3-5. Raising this trades a slower Modules screen for
            # correctness on buses that big, and no bench here has one yet.
            for mid in list(seen)[:6]:
                _drain_to_line_boundary(ser)
                ser.write(("#%d INFO\n" % mid).encode())
                for ln in _read_lines(ser, 0.6):
                    if ln.startswith("@%d {" % mid):
                        try:
                            st = json.loads(ln.split(" ", 1)[1])
                            seen[mid].update(_wifi_of(st))
                            # ...and its chip, from the same answer. A module
                            # behind an RS485 bus is reachable over WiFi too,
                            # so it is exactly a board the hub can meet twice.
                            if st.get("chip"):
                                seen[mid]["chip"] = st["chip"]
                            if st.get("caps"):
                                seen[mid]["caps"] = st["caps"]
                            # ...AND ITS GROUP (A3-5). The Network tab and
                            # /api/allmods have always read this field for bus
                            # boards; nothing ever filled it, so a module
                            # behind the bus read "not linked" however it was
                            # grouped — and ticking it to fix that would send
                            # GROUP to a board that already had one.
                            seen[mid]["group"] = st.get("group", "")
                        except ValueError:
                            pass
                        break
            # A board on its OWN cable answers the broadcast too, so "no
            # direct answer, one board in the census" is ambiguous: it is
            # either an RS485 adapter with one module behind it, or a board
            # whose direct probe was simply missed. Ask it plainly once more -
            # an adapter has nothing to answer with, a board does. Without
            # this, a camera on a plain USB cable was listed as a module on a
            # bus, with an addressed dev string it did not need.
            if not out["module"] and len(seen) == 1:
                _drain_to_line_boundary(ser)
                ser.write(b"INFO" + chr(10).encode())
                for ln in _read_lines(ser, 1.2):
                    if ln.startswith("{"):
                        try:
                            st = json.loads(ln)
                            out["module"] = {"id": st.get("id"),
                                             "name": st.get("name"),
                                             "type": st.get("type"),
                                             "group": st.get("group", ""),
                                             "chip": st.get("chip", ""),
                                             "caps": st.get("caps") or [],
                                             **_wifi_of(st)}
                        except ValueError:
                            pass
                        break
            mod_id = out["module"]["id"] if out["module"] else None
            out["rs485"] = [v for k, v in sorted(seen.items()) if k != mod_id]
            if out["module"] or out["rs485"]:
                _usb_ident[port] = dict(out)   # answer to reuse while in use
        except Exception as e:  # noqa: BLE001
            out["error"] = str(e)
            if "hEvent" in out["error"]:  # pyserial's way of saying "not usable"
                out["error"] = "port not usable (Bluetooth or half-open) — skipped"
            usb_close(port)  # reset a wedged port for the next attempt
    return out


_usbscan_lock = threading.Lock()
_usbscan_cache = {"at": 0.0, "usb": []}


def probe_usb_one(port, timeout=8, full=False):
    """Probe a single port with a watchdog (used by the streaming hub UI:
    each port renders the moment IT answers — nobody waits for the slow ones)."""
    ex = ThreadPoolExecutor(max_workers=1)
    f = ex.submit(probe_usb_port, port, full)
    try:
        return f.result(timeout=timeout)
    except FutTimeout:
        return {"port": port, "module": None, "rs485": [],
                "error": "no answer within %d s — skipped" % timeout}
    finally:
        ex.shutdown(wait=False)


def probe_usb_all(force=False):
    # all NON-Bluetooth ports in parallel (Bluetooth phantom ports are known
    # from the device type and never opened) with a shared watchdog
    with _usbscan_lock:
        if not force and time.time() - _usbscan_cache["at"] < 8:
            return _usbscan_cache["usb"]
        infos = serial_ports()
        out = []
        # A port being flashed is not probed: opening it would fight esptool
        # for the cable, and the identity is about to change anyway.
        real = [i["port"] for i in infos
                if not i["bt"] and i["port"] not in _flash_ports]
        for i in infos:
            if i["bt"]:
                out.append({"port": i["port"], "module": None, "rs485": [],
                            "error": "Bluetooth port — skipped", "bt": True})
            elif i["port"] in _flash_ports:
                out.append({"port": i["port"], "module": None, "rs485": [],
                            "error": "being flashed right now", "flashing": True})
        if real:
            ex = ThreadPoolExecutor(max_workers=len(real))
            futs = [(p, ex.submit(probe_usb_port, p)) for p in real]
            # ONE budget for all of them, because they run at the same time -
            # there is a worker per port, so the wall clock is the slowest port
            # and not the sum. What it must cover, measured on four real cables
            # 2026-08-19: an ordinary port answers in about 3 s, and a port with
            # an RS485 bus behind it takes 4.7 s, because the census waits for
            # the bus to go quiet and boards stagger their answers by id.
            #
            # It was 7 s, which was comfortable until the bus census got its
            # floor - then a four-cable bench spent 10.8 s and reported 2 boards
            # of 5, with the bus module among the missing. The ports that lose
            # are simply the ones waited on last, which is why it looked like a
            # bus fault and was not one.
            budget = 20
            deadline = time.time() + budget
            for p, f in futs:
                try:
                    out.append(f.result(timeout=max(0.1, deadline - time.time())))
                except FutTimeout:
                    out.append({"port": p, "module": None, "rs485": [],
                                "error": "no answer within %d s — skipped. A port "
                                         "with an RS485 bus behind it is the "
                                         "slowest thing here" % budget})
            ex.shutdown(wait=False)
        out.sort(key=lambda u: u["port"])
        _usbscan_cache.update(at=time.time(), usb=out)
        return out
