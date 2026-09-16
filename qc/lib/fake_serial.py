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

# The joint order every part of this project uses, so NEUTRAL can be addressed
# by name here exactly as the board addresses it.
JOINT_NAMES = ["L_SH_P", "L_SH_R", "L_EL_P", "L_EL_R",
               "R_SH_P", "R_SH_R", "R_EL_P", "R_EL_R", "WAIST", "SHRUG"]

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
# One fake board, one chip id - twelve hex digits, exactly as a real one
# formats its eFuse MAC.
# What this fake board has on its SD card, per folder. DATA, so a check that
# needs another file adds a line here rather than teaching the fake a case.
SD_DIRS_BASE = {
    "/moves": [{"n": "wave.yaml", "s": 812}],
    "/music": [{"n": "song.mp3", "s": 40960}, {"n": "clap.wav", "s": 8192}],
    "/data":  [],
}
SD_DIRS = {k: list(v) for k, v in SD_DIRS_BASE.items()}

CHIP = "A0B1C2D3E4F5"
FAR_CHIP = "A0B1C2D3E4F6"        # the module behind it on RS485

# The two boards the fake bus answers as. The slow one is the point: its reply
# lands later than any fixed window a hub might guess at, which is exactly the
# case that was invisible until a real bus was on the bench.
# A cable with a board on it that never stops talking. Listed by _comports()
# only when a check asks for it, so nothing else has to know it exists.
FLOOD_PORT = "COM98"
flood_listed = [False]

# A plain USB-to-RS485 DONGLE: no board of its own on the cable, only boards
# behind it on the bus. The real rig (CH340+MAX485 on COM23 with board 67
# behind it) is shaped exactly like this, and nothing here could produce it -
# every fake cable had a board answering INFO directly, which is the one case
# the module list handled.
DONGLE_PORT = "COM97"
dongle_listed = [False]

BUS_QUICK = "@1 PONG 1 nong-test nong"          # the near board
BUS_SLOW_ID = 67                                # answers late, on purpose
BUS_SLOW = "@%d PONG %d nong-far nong" % (BUS_SLOW_ID, BUS_SLOW_ID)
BUS_SLOW_DELAY = 1.35        # what id 67 really took, measured

# Replies a board still owes the bus. Cancelled by reset(), so one check's
# late answer cannot land in the middle of the NEXT check's serial stream.
# That is not hypothetical: the first full run with the staggered fake failed
# seven checks, none of them about the bus, with the symptom this project
# already knows - measurements missing.
pending_bus = []

far_wire = []
qc_marks = []                  # "MOVE QCMARK <x>" the page sent (see browser.py)


# What firmware the fake claims to run — READ from the firmware's own header,
# not typed here, so a version bump cannot leave the fake behind.
def _fw_version():
    import re as _re
    from pathlib import Path as _P
    hdr = _P(__file__).resolve().parents[2] / "firmware" / "config" / "esp32_hardware.h"
    try:
        m = _re.search(r'#define\s+FW_VERSION\s+"([^"]+)"',
                       hdr.read_text(encoding="utf-8", errors="replace"))
        return m.group(1) if m else "0.0.0"
    except OSError:
        return "0.0.0"


FW_VERSION = _fw_version()
_t0 = [None]
_motion_cache = [None]         # commands that stop a running sequence (see _Nong)


def reset():
    """Forget the recorded traffic (call at the start of a check)."""
    for _t in pending_bus:
        _t.cancel()                  # a reply owed to a check that has ended
    del pending_bus[:]
    del wire[:], far_wire[:], qc_marks[:], opens[:]
    _t0[0] = None
    dead[0] = False
    flood_listed[0] = False      # only the check that wants it sees that cable
    dongle_listed[0] = False
    NONG.joints = [90.0] * 10
    NONG.jcfg = {}
    NONG.neutral = FAR.neutral = [90.0] * 10
    NONG.offset = [0.0] * 10
    FAR.offset = [0.0] * 10
    NONG.audio_file = FAR.audio_file = ""
    NONG.audio_loop = FAR.audio_loop = False
    NONG.pins = {"servo1": 32, "servo2": 33}
    NONG.ram, NONG.ram_open, NONG.held, NONG.playing = "", False, "", False
    SD_DIRS.clear()
    SD_DIRS.update({k: list(v) for k, v in SD_DIRS_BASE.items()})
    NONG.group = FAR.group = ""
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

    def __init__(self, log=None, chip=None, ident=1, name="nong-test"):
        # Its OWN id and name. They used to be written into two strings, so
        # every fake board answered as the same one - and a module behind the
        # RS485 bus therefore inherited the near board's identity, which merged
        # the two into one row and hid exactly the kind of fault the merge
        # exists to catch.
        self.ident = ident
        self.mod_name = name
        self.log = wire if log is None else log
        # Its own chip, because two fakes that report the same one would be
        # merged into a single board by the hub - hiding the very fault the
        # merge exists to fix.
        self.chip = chip or CHIP
        # Empty by default: a board that no hub has spoken to must offer no way
        # back, and that is the case worth being able to drive.
        self.hub = ""
        self.joints = [90.0] * 10
        self.jcfg = {}   # joint -> the last JCFG applied
        # Where each joint goes on boot and on HOME. 90 is only the DEFAULT: a
        # check that asserts a chosen start pose reached the board reads this.
        self.neutral = [90.0] * 10
        # The mounting correction per joint, in JOINT degrees — what the OFFSET
        # command takes and what the box on screen shows. The real board keeps it
        # in servo degrees as `trim` and converts; the fake stores what it was
        # told, so a check can assert the number a person typed arrived intact.
        self.offset = [0.0] * 10
        # The last PLAY: the path with LOOP already taken off, and whether it
        # was told to repeat. Split on the module side, which is the claim.
        self.audio_file = ""
        self.audio_loop = False
        self.pins = {"servo1": 32, "servo2": 33}
        # Which installation this board belongs to. The real board reports it
        # in INFO and accepts GROUP; the fake reported an empty string and
        # answered nothing, so the hub could never be caught dropping it.
        self.group = ""
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
            "id": self.ident, "name": self.mod_name,
            "type": "nong", "sd": True,
            # The chip MAC, which the real board now reports and the hub
            # merges on. A fake without it would make every board look
            # like old firmware and never exercise the merge.
            "chip": self.chip,
            # Which hub last spoke to this board over HTTP. The real one
            # fills this from the X-Mice-Hub header (WebPortal::noteHub);
            # the fake carries it so the page can be driven both ways.
            "hub": self.hub,
            # The real board reports these two and the fake never did, so a
            # page that showed them looked broken here while working against
            # hardware. A fake that under-reports hides the bugs it exists to
            # catch: CommandRouter::buildStatus is the contract.
            "fw": FW_VERSION, "group": self.group,
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
            return "PONG %d %s nong" % (self.ident, self.mod_name)
        if head == "GROUP":
            # Mirrors CommandRouter: CLEAR only when it is the WHOLE argument,
            # or a group called "clear skies" would silently ungroup a board.
            arg = c[len("GROUP"):].strip()
            if not arg:
                return ("GROUP " + ('"%s"' % self.group if self.group
                                    else "(none)") + " appass=mice-fallback")
            self.group = "" if arg.upper() == "CLEAR" else arg
            return ('OK group "%s" appass=mice-%s' % (self.group, self.group)
                    if self.group
                    else "OK ungrouped (shared fallback password)")
        if head == "POSE":
            vals = [float(x) for x in c.split()[1:] if x.replace(".", "").replace("-", "").isdigit()]
            with self.lock:
                for i, v in enumerate(vals[:10]):
                    self.joints[i] = v
            return self._preempt(head, "OK POSE")
        if head == "FILES":
            # per folder: the music picker reads /music and must be able to
            # tell "this card has tracks" from "this card has shows"
            d = (c.split(" ", 1)[1].strip().lower() if " " in c else "/moves")
            return json.dumps(SD_DIRS.get(d, SD_DIRS["/moves"]))
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
            # A file that was uploaded has to appear in the folder it was
            # uploaded to, or a check cannot tell "the upload worked" from
            # "the picker still lists what it listed before".
            path = self.ram_name if self.ram_name.startswith("/") else "/moves/" + self.ram_name
            folder, _, base = path.rpartition("/")
            SD_DIRS.setdefault(folder.lower() or "/moves", []).append(
                {"n": base, "s": len(self.held)})
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
        # PLAY <file> [LOOP] | STOP — the trailing LOOP is taken off HERE, on the
        # module side, because that is the claim: the real board does it before
        # joining the rest of the tokens into a path that may contain spaces.
        if head == "PLAY":
            arg = c.split(" ", 1)[1].strip() if " " in c else ""
            if arg.upper() == "STOP":
                self.audio_file, self.audio_loop = "", False
                return "OK audio stopped"
            if not arg:
                return "ERR usage: PLAY <file> [LOOP]|STOP"
            loop = False
            toks = arg.split()
            if len(toks) > 1 and toks[-1].upper() == "LOOP":
                loop = True
                arg = " ".join(toks[:-1])
            if not arg.startswith("/"):
                arg = "/music/" + arg
            self.audio_file, self.audio_loop = arg, loop
            return ("OK looping " if loop else "OK playing ") + arg
        # LIMIT? — every per-joint setting in one reply, which is what Studio
        # reads before deciding what to send. It used to fall through to a bare
        # OK, so `pullLimits()` had never been driven at all.
        if head == "LIMIT?":
            return json.dumps({
                "min": [0] * 10,
                "max": [180] * 10,
                "gear_pinion": [15] * 10,
                "gear_gear": [18] * 10,
                "pulse_min": [500] * 10,
                "pulse_max": [2500] * 10,
                "max_dps": [120] * 10,
                "servo_range": [270] * 10,
                "frame_hz": [50] * 10,
                "neutral": list(self.neutral),
                "offset": list(self.offset),
            })
        if head == "JCFG":
            # one joint's whole setup in a line — remember it so a check can
            # read back what the batch actually applied
            parts = c.split()
            if len(parts) >= 11:
                # 12 tokens once neutral is carried: sliced to 10 values so the
                # appended one is recorded, while the first nine keep their
                # positions (check_sendrig reads them by index).
                self.jcfg[parts[1]] = parts[2:12]
                if len(parts) >= 12:
                    j = self._joint_index(parts[1])
                    if j is not None:
                        self.neutral[j] = float(parts[11])
                return "OK JCFG " + parts[1]
            return "ERR usage: JCFG <1-10|name> ..."
        # NEUTRAL — the pose the board goes to on boot and on HOME (A26-3)
        if head in ("NEUTRAL", "NEUTRAL?"):
            parts = c.split()
            if head == "NEUTRAL?" or len(parts) == 1:
                return json.dumps({"neutral": self.neutral})
            if len(parts) >= 11:                        # the whole pose at once
                for i in range(10):
                    tok = parts[1 + i]
                    if tok in ("-", "~"):
                        continue
                    self.neutral[i] = float(tok)
                return "OK neutral set for all 10 joints"
            if len(parts) < 3:
                return "ERR usage: NEUTRAL <1-10|name|ALL> <deg>"
            d = float(parts[2])
            if parts[1].upper() == "ALL":
                self.neutral = [d] * 10
            else:
                j = self._joint_index(parts[1])
                if j is None:
                    return "ERR joint 1-10, name, or ALL"
                self.neutral[j] = d
            return "OK neutral " + parts[1] + " = " + parts[2]
        # OFFSET — the mounting correction for ONE joint, in joint degrees (A26-4).
        # The real board refuses anything past NONG_OFFSET_MAX_DEG, so the fake
        # must too: a check that proves a wild value is rejected has to be able to
        # see the rejection here.
        if head in ("OFFSET", "OFFSET?"):
            parts = c.split()
            if head == "OFFSET?" or len(parts) == 1:
                return json.dumps({"offset": self.offset})
            if len(parts) < 3:
                return "ERR usage: OFFSET <1-10|name|ALL> <deg>"
            try:
                d = float(parts[2])
            except ValueError:
                return "ERR usage: OFFSET <1-10|name|ALL> <deg>"
            if d < -30 or d > 30:
                return "ERR offset must be -30..30 deg"
            if parts[1].upper() == "ALL":
                self.offset = [d] * 10
            else:
                j = self._joint_index(parts[1])
                if j is None:
                    return "ERR joint 1-10, name, or ALL"
                self.offset[j] = d
            return "OK offset " + parts[1] + " = " + parts[2] + " deg on the arm"
        if head in ("HOME", "ZERO", "RELAX", "ATTACH", "SPEED", "LIMIT", "GEAR",
                    "PULSE", "RANGE", "RATE", "SERVO", "AUTH", "JOINT",
                    "SETZERO", "UP", "DOWN", "GOTO"):
            return self._preempt(head, "OK " + head)
        return "OK"

    def _joint_index(self, word):
        """1-10 or a joint name -> 0-9. None when it is neither."""
        w = word.strip().upper()
        if w.isdigit():
            n = int(w)
            return n - 1 if 1 <= n <= 10 else None
        return JOINT_NAMES.index(w) if w in JOINT_NAMES else None


NONG = _Nong()
# A SECOND module, on the far side of NONG's own hotspot. The PC has no route
# to it at all - everything it is told arrives via `REACH` through NONG.
FAR = _Nong(far_wire, FAR_CHIP, 67, "nong-far")


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
            if self.port not in (PORT, FLOOD_PORT, DONGLE_PORT):
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

    def _bus_reply(self, text, after):
        """Put one board's answer on the wire, later, the way a bus does."""
        import threading

        def land():
            with self._rxlock:
                self._rx += (chr(10) + text + chr(10)).encode()

        t = threading.Timer(after, land)
        pending_bus.append(t)
        t.daemon = True
        t.start()

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
                    # Addressed frames reach the board they name. Answering
                    # every id as the near board made a bus child report the
                    # near board's chip, which merged two boards into one.
                    who = FAR if bid == str(BUS_SLOW_ID) else NONG
                    r = who.line(rest)
                    if bid == "*":
                        # A BROADCAST IS NOT INSTANT, and pretending it was is
                        # what hid a real bug for the life of this project.
                        #
                        # Boards stagger their answers by their own id so the
                        # replies do not collide, so the last board to speak is
                        # the one with the highest id. The hub used to listen
                        # for a fixed 0.8 s, which silently made every board
                        # above id 40 not exist. Measured on the bench
                        # 2026-08-19: a nong on id 67 answered after 1344 ms.
                        #
                        # So the fake answers as two boards: one quick, and one
                        # SLOW enough that a fixed short window would miss it.
                        self._bus_reply(BUS_QUICK, 0.02)
                        self._bus_reply(BUS_SLOW, BUS_SLOW_DELAY)
                        continue
                    out = "@%s %s" % (bid, r)
                else:
                    # A DONGLE HAS NOTHING TO ANSWER WITH. It is wire, not a
                    # board: a plain command addressed to nobody goes onto the
                    # bus and no module owns it.
                    if self.port == DONGLE_PORT:
                        continue
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
        if self.port == FLOOD_PORT:
            return len(self._flood_chunk())
        with self._rxlock:
            return len(self._rx)

    def _flood_chunk(self):
        """A board that NEVER goes quiet.

        Real, and measured on the bench 2026-08-21: a wedged board sent 23,395
        lines in three seconds and never paused. Nothing in this fake had ever
        done that, so every wait that pushed its own deadline forward on each
        arriving byte looked correct for the life of the project.
        """
        return (b"@85 PONG 85 lift-test nong\n" * 8)

    def read(self, n=1):
        if self.port == FLOOD_PORT:
            return self._flood_chunk()[:n]
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
    ports = [_Port(PORT, "Silicon Labs CP210x (fake nong)", "USB VID:PID=10C4:EA60")]
    if flood_listed[0]:
        ports.append(_Port(FLOOD_PORT, "Silicon Labs CP210x (wedged board)",
                           "USB VID:PID=10C4:EA60"))
    if dongle_listed[0]:
        ports.append(_Port(DONGLE_PORT, "USB-SERIAL CH340 (RS485 dongle)",
                           "USB VID:PID=1A86:7523"))
    return ports


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
