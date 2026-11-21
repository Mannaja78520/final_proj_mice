"""A command reaches a board behind a bridge by its path: usb:COM:>100>7.

The hub's usb_cmd frames the line `#>100>7 CMD` and waits for `@>100>7 ...`
(not any other board's reply). Uses the real usb_cmd and parse_dev over a
simulated two-cable rig; asserts what the target board did and what came back.
"""
import sys
import threading
import time
from pathlib import Path

import qc as F

AREA = "connection"
TITLE = "commands reach a board behind a bridge by path (usb:COM:>100>7)"

ROOT = Path(F.__file__).resolve().parents[2]


class SimSer:
    """Just enough of a pyserial port to sit between hub_usb and a bus_sim Bus."""

    def __init__(self, bus):
        self.bus, self.out, self.sent = bus, b"", []

    def reset_input_buffer(self):
        self.out = b""

    def write(self, data):
        line = data.decode().strip()
        self.sent.append(line)
        reply = [t for d, t in sorted(self.bus.frames(line)) if t.startswith("@")]
        self.out += "".join("\n%s\n" % r for r in reply).encode()

    def read(self, n=1):
        chunk, self.out = self.out[:n], self.out[n:]
        if not chunk:
            time.sleep(0.002)
        return chunk

    @property
    def in_waiting(self):
        return len(self.out)


def run(t):
    for p in (ROOT / "qc" / "lib", ROOT / "main_python"):
        if str(p) not in sys.path:
            sys.path.insert(0, str(p))
    import hub_usb
    from bus_sim import Board, Bus, Gateway
    import main as hub

    back = Bus([Board("B0000000%04X" % i, i) for i in range(1, 11)])
    top = Bus([Board("A0000000%04X" % i, i) for i in range(1, 6)] + [Gateway("A1000000AAAA", 100, down=back)])
    ser = SimSer(top)
    real_get = hub_usb._usb_get
    hub_usb._usb_get = lambda port: {"lock": threading.RLock(), "ser": ser, "last": 0}
    try:
        kind, port, bus, peer = hub.parse_dev("usb:COM77:>100>7")
        t.ok((kind, port, bus, peer) == ("usb", "COM77", ">100>7", ""), "usb:COM77:>100>7 parses to a path", str((kind, port, bus)))
        t.ok(hub.parse_dev("usb:COM77:5")[2] == 5, "a plain bus id is still a number")
        r = hub_usb.usb_cmd("COM77", "SET ID 7", ">100>7", wait=1.0)
        t.ok(r == "OK id=7", "the board behind the bridge answered (%r)" % r)
        t.ok(ser.sent[-1] == "#>100>7 SET ID 7", "framed as a path on the wire", ser.sent[-1])
        r = hub_usb.usb_cmd("COM77", "SET ID 3", 3, wait=1.0)
        t.ok(r == "OK id=3" and ser.sent[-1] == "#3 SET ID 3", "a board on the first cable is addressed as before")
        try:
            hub_usb.usb_cmd("COM77", "SET ID 7", ">100>200", wait=0.3)
            t.ok(False, "a path to nothing times out")
        except TimeoutError as e:
            t.ok(">100>200" in str(e), "a path to nothing times out and says which path", str(e))
    finally:
        hub_usb._usb_get = real_get

    cpp = (F.FIRMWARE / "src" / "core" / "RS485Bus.cpp").read_text(encoding="utf-8")
    t.contains(cpp, "act as that", "firmware: a gateway plugged into the PC handles its own first hop")
