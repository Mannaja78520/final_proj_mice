"""A fake `serial` module: one EXCLUSIVE COM port with a nong module on it.

Mimics Windows: a second open() of the same port raises PermissionError, so
the test proves the hub really shares ONE handle between its clients instead
of each client opening its own.
"""
import json
import random
import threading
import time
import types

PORT = "COM99"

_open_holders = set()          # ports currently opened (exclusivity)
_holder_lock = threading.Lock()
opens = []                     # every successful open, for the test to count
concurrent_writers = []        # >1 here would mean commands interleaved
# dead[0] = the board was unplugged/reset: handles opened BEFORE now are stale
# and every write on them fails, but a newly opened handle works again.
dead = [False]

# What the module was actually told, so a check can assert on the WIRE instead
# of on the UI's opinion of itself. wire is [(ms since first command, cmdline)].
wire = []
# What the module BEHIND the hotspot was told. Kept separate from `wire` so a
# forwarded command cannot be mistaken for one sent straight down the cable —
# which is the exact difference between loading a show onto the right robot
# and loading it onto the wrong one.
far_wire = []
qc_marks = []                  # "MOVE QCMARK <x>" the page sent (see browser.py)
_t0 = [None]
_motion_cache = [None]         # commands that stop a running sequence (see _Nong)


def reset():
    """Forget the recorded traffic (call at the start of a check)."""
    del wire[:], far_wire[:], qc_marks[:], opens[:]
    _t0[0] = None
    dead[0] = False
    NONG.joints = [90.0] * 10
    NONG.jcfg = {}
    NONG.pins = {"servo1": 32, "servo2": 33}
    NONG.ram, NONG.ram_open, NONG.held, NONG.playing = "", False, "", False
    NONG.playing_file = FAR.playing_file = ""
    NONG.busy = False
    NONG.far_joints = [90.0] * 10
    NONG.far_held = ""
    FAR.joints = [90.0] * 10
    FAR.ram, FAR.ram_open, FAR.held, FAR.playing = "", False, "", False


def poses():
    """Just the POSE commands, in wire order, as (ms, [joint values], T)."""
    out = []
    for ms, c in wire:
        if not c.upper().startswith("POSE"):
            continue
        t = int(c.split(" T ")[1]) if " T " in c else None
        vals = [v for v in c.split()[1:] if v.replace(".", "").lstrip("-").isdigit()]
        out.append((ms, vals[:10], t))
    return out


class SerialException(Exception):
    pass


class _Nong:
    """The module firmware's line protocol, enough of it to drive the UIs."""

    def __init__(self, log=None):
        self.log = wire if log is None else log
        self.joints = [90.0] * 10
        self.jcfg = {}   # joint -> the last JCFG applied
        self.pins = {"servo1": 32, "servo2": 33}
        self.ram, self.ram_open, self.ram_name = "", False, ""
        self.held = ""      # the sequence the module is holding
        self.busy = False   # mid-move: REACH must refuse rather than stall it
        self.far_joints = [90.0] * 10   # mirrors FAR, for checks to read
        self.far_held = ""
        self.playing = False
        self.playing_file = ""
        self.lock = threading.Lock()

    # A command that MOVES the robot takes the robot: the board stops playing
    # its own sequence rather than letting two clocks drive the same servos.
    # Mirrors CommandRouter::preemptSequence.
    #
    # The list is READ from config/commands.json, the same file the firmware
    # compiles its table from — a copy here could say the fake stops on a
    # command the real board ignores, and QC would prove a fix that does not
    # exist on the robot.
    @staticmethod
    def _motion():
        if _motion_cache[0] is None:
            import registry
            _motion_cache[0] = {c["name"].upper() for c in registry.commands()
                                if c.get("motion")}
        return _motion_cache[0]

    def _preempt(self, head, reply):
        if not self.playing or head not in self._motion():
            return reply
        self.playing, self.playing_file = False, ""
        return reply if reply.startswith("ERR") else reply + " (sequence stopped)"

    def info(self):
        return json.dumps({
            "id": 1, "name": "nong-test", "type": "nong", "sd": True,
            "wifi": {"ip": "", "mode": "off"},
            # same shape as the real board: seq is top level, and says whether
            # the module is playing something on its OWN clock right now
            "seq": {"running": self.playing, "file": self.playing_file},
            "module": {"joints": self.joints, "seq": "", "speed": 120},
        })

    def line(self, cmd):
        c = cmd.strip()
        if not c:
            return None
        # record every command with the time it arrived, so timing-sensitive
        # checks (holds, pauses) can assert on what really went down the wire
        if _t0[0] is None:
            _t0[0] = time.time()
        self.log.append((round((time.time() - _t0[0]) * 1000), c))
        if c.upper().startswith("MOVE QCMARK "):
            qc_marks.append(c[len("MOVE QCMARK "):])
            return "OK MOVE"
        head = c.split(" ", 1)[0].upper()
        if head == "STOP":
            return self._preempt(head, "OK stopped")
        if head == "INFO":
            return self.info()
        if head == "PING":
            return "PONG 1 nong-test nong"
        if head == "POSE":
            vals = [float(x) for x in c.split()[1:] if x.replace(".", "").replace("-", "").isdigit()]
            with self.lock:
                for i, v in enumerate(vals[:10]):
                    self.joints[i] = v
            return self._preempt(head, "OK POSE")
        if head == "FILES":
            return json.dumps([{"n": "wave.yaml", "s": 812}])
        if head in ("PIN", "PIN?", "PINS", "PINS?"):
            up = c.upper()
            if up.startswith("PIN VALID"):
                return json.dumps([{"gpio": 13, "cls": "ok", "pwm": True}])
            parts = c.split()
            if len(parts) >= 3 and parts[1].upper() not in ("VALID", "CLEAR"):
                self.pins[parts[1].lower()] = int(parts[2])   # PIN <name> <gpio>
                return "OK %s=%s (reboot to apply)" % (parts[1].lower(), parts[2])
            return json.dumps(self.pins)
        # ---- upload with no SD card lands in memory, and MOVE plays it ----
        if head == "FBEGIN":
            self.ram, self.ram_open = "", True
            self.ram_name = c.split(" ", 1)[1] if " " in c else "?"
            return "OK writing %s (memory - no SD card)" % self.ram_name
        if head == "FDATA":
            import base64
            if not self.ram_open:
                return "ERR no FBEGIN"
            try:
                chunk = base64.b64decode(c.split(" ", 1)[1])
            except Exception:
                return "ERR bad base64"
            self.ram += chunk.decode(errors="replace")
            return "OK %d" % len(chunk)
        if head == "FEND":
            if not self.ram_open:
                return "ERR no FBEGIN"
            self.ram_open = False
            self.held = self.ram
            return "OK held %s in memory (%d bytes)" % (self.ram_name, len(self.held))
        if head == "MOVE":
            arg = c.split(" ", 1)[1].strip() if " " in c else ""
            if arg.upper() == "STOP":
                self.playing, self.playing_file = False, ""
                return "OK move stopped"
            # a real board plays from the CARD when it has one, and from
            # memory when it does not - the fake must not be stricter
            if self.held:
                self.playing, self.playing_file = True, "(memory)"
                return "OK playing the sequence held in memory"
            if arg and arg.rsplit("/", 1)[-1] in ("wave.yaml",):
                self.playing = True
                self.playing_file = "/moves/" + arg.rsplit("/", 1)[-1]
                return "OK playing " + self.playing_file
            return "ERR no sequence"
        # ---- the fleet on the far side of this module's own AP ----
        if head == "PEERS":
            return json.dumps([
                {"id": 1, "name": "nong-test", "type": "nong",
                 "ip": "192.168.4.1", "self": True},
                {"id": 7, "name": "far-nong", "type": "nong",
                 "ip": "192.168.4.2"},
            ])
        if head == "REACH":
            parts = c.split(" ", 2)
            if len(parts) < 3:
                return "ERR usage: REACH <ip|name|id> <command>"
            who, inner = parts[1], parts[2]
            if who.lower() not in ("far-nong", "7", "192.168.4.2"):
                return 'ERR no module "%s" - try its ip, or PEERS to list them' % who
            if self.busy:
                return "ERR busy - the module is moving"
            # The far module is a REAL second module that keeps its own state:
            # a sequence uploaded through the cable has to still be there
            # afterwards, and its joints must move while ours do not.
            r = FAR.line(inner)
            self.far_joints = FAR.joints
            self.far_held = FAR.held
            return r if r is not None else "ERR no reply"
        if head == "JCFG":
            # one joint's whole setup in a line — remember it so a check can
            # read back what the batch actually applied
            parts = c.split()
            if len(parts) >= 11:
                self.jcfg[parts[1]] = parts[2:11]
                return "OK JCFG " + parts[1]
            return "ERR usage: JCFG <1-10|name> ..."
        if head in ("HOME", "ZERO", "RELAX", "ATTACH", "SPEED", "LIMIT", "GEAR",
                    "PULSE", "RANGE", "RATE", "SERVO", "AUTH", "JOINT",
                    "SETZERO", "UP", "DOWN", "GOTO"):
            return self._preempt(head, "OK " + head)
        return "OK"


NONG = _Nong()
# A SECOND module, on the far side of NONG's own hotspot. The PC has no route
# to it at all - everything it is told arrives via `REACH` through NONG.
FAR = _Nong(far_wire)


class Serial:
    def __init__(self, *a, **k):
        self.port = k.get("port")
        self.baudrate = k.get("baudrate", 115200)
        self.timeout = k.get("timeout", 0.15)
        self.dtr = self.rts = False
        self.is_open = False
        self._fresh = False     # opened after the unplug -> works again
        self._rx = bytearray()
        self._rxlock = threading.Lock()

    def open(self):
        with _holder_lock:
            if self.port in _open_holders:
                raise SerialException(
                    "could not open port '%s': PermissionError(13, "
                    "'Access is denied.', None, 5)" % self.port)
            if self.port != PORT:
                raise SerialException("could not open port %r: no such device" % self.port)
            _open_holders.add(self.port)
            opens.append((self.port, time.time()))
        self.is_open = True
        self._fresh = dead[0]      # opened after the unplug: this one is good
        # boot/log noise the readers must skip
        with self._rxlock:
            self._rx += b"[nong] servos attached\n[  1234][I] wifi off\n"

    def close(self):
        if self.is_open:
            with _holder_lock:
                _open_holders.discard(self.port)
        self.is_open = False

    def reset_input_buffer(self):
        with self._rxlock:
            self._rx.clear()

    def write(self, data: bytes):
        # Windows after an unplug/reset: the handle stays "open" but every
        # write fails. Set fake_serial.dead = True to reproduce it.
        if dead[0] and not self._fresh:
            raise PermissionError(
                13, "The device does not recognize the command.", None, 22)
        concurrent_writers.append(1)
        try:
            if len(concurrent_writers) > 1:
                raise AssertionError("two commands on the wire at once!")
            for raw in data.decode(errors="replace").split("\n"):
                if not raw.strip():
                    continue
                time.sleep(random.uniform(0.002, 0.012))   # wire + module latency
                if raw.startswith("#"):                    # RS485 frame -> "@id ..."
                    bid, _, rest = raw[1:].partition(" ")
                    r = NONG.line(rest)
                    if bid == "*":
                        out = "@1 PONG 1 nong-test nong"
                    else:
                        out = "@%s %s" % (bid, r)
                else:
                    out = NONG.line(raw)
                with self._rxlock:
                    self._rx += b"[nong] tick\n"           # log noise between replies
                    # "\n<reply>\n", exactly like emitLine() on the board: the
                    # leading blank line is what lets the hub tell a reply from
                    # the orphaned tail of a log line
                    self._rx += ("\n" + out + "\n").encode()
            return len(data)
        finally:
            concurrent_writers.pop()

    @property
    def in_waiting(self):
        with self._rxlock:
            return len(self._rx)

    def read(self, n=1):
        end = time.time() + (self.timeout or 0)
        while True:
            with self._rxlock:
                if self._rx:
                    out = bytes(self._rx[:n])
                    del self._rx[:n]
                    return out
            if time.time() >= end:
                return b""
            time.sleep(0.002)


class _Port:
    def __init__(self, device, description, hwid):
        self.device, self.description, self.hwid = device, description, hwid


def _comports():
    return [_Port(PORT, "Silicon Labs CP210x (fake nong)", "USB VID:PID=10C4:EA60")]


def install():
    """Put this fake in sys.modules as `serial` / `serial.tools.list_ports`."""
    import sys
    mod = types.ModuleType("serial")
    mod.Serial = Serial
    mod.SerialException = SerialException
    tools = types.ModuleType("serial.tools")
    lp = types.ModuleType("serial.tools.list_ports")
    lp.comports = _comports
    tools.list_ports = lp
    mod.tools = tools
    sys.modules["serial"] = mod
    sys.modules["serial.tools"] = tools
    sys.modules["serial.tools.list_ports"] = lp
    return mod
