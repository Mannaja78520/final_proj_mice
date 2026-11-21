"""A half-duplex RS485 bus with real collisions, in virtual time.

fake_serial answers instantly and never collides, which is how the 24-slot
PING looked fine against 2000+ checks. Here two frames whose airtime overlaps
are both destroyed (what a shared pair of wires does), at 115200 baud
(10 bits per byte). Boards follow the firmware rules in BusAddr.h; `old=True`
boards are firmware from before the ranged commands: they answer plain PING
only and ignore the rest.
"""
import hashlib
import re

SLOT_S = 0.010
BYTE_S = 10 / 115200.0


def fnv(chip, salt):
    """BusAddr::hash - seeded FNV-1a + avalanche (the C++ test pins the same values)."""
    h = (2166136261 ^ ((salt * 16777619) & 0xFFFFFFFF)) & 0xFFFFFFFF
    for ch in chip.upper().encode():
        h = ((h ^ ch) * 16777619) & 0xFFFFFFFF
    h ^= h >> 16; h = (h * 0x85ebca6b) & 0xFFFFFFFF
    h ^= h >> 13; h = (h * 0xc2b2ae35) & 0xFFFFFFFF
    h ^= h >> 16
    return h


class Board:
    def __init__(self, chip, ident, name=None, type_="blank", old=False):
        self.chip, self.id = chip.upper(), ident
        self.name = name or "MOD-" + chip[6:].upper()
        self.type, self.old = type_, old
        self.gateway = False

    def hear(self, line):
        """[(delay_s, text)] this board puts on the wire for one request line."""
        m = re.match(r"^#(\S+) (.+)$", line)
        if not m:
            return []
        addr, cmd = m.group(1), m.group(2)
        if addr.startswith("~"):
            if self.old or addr[1:].upper() != self.chip:
                return []
            return [(0, "@~%s %s" % (self.chip, self._run(cmd)))]
        if addr in ("*", "0"):
            mm = re.match(r"(?i)^PING(?: (\d+) (\d+))?$", cmd)
            if mm:
                if mm.group(1) and not self.old:
                    lo, hi = int(mm.group(1)), int(mm.group(2))
                    if not lo <= self.id <= hi:
                        return []
                    slot = (self.id - lo) % 24
                    return [(slot * SLOT_S, "@%d PONG %d %s %s" % (self.id, self.id, self.name, self.type))]
                # plain PING: firmware after #154 = one 6 ms slot per id (BusSlot.h);
                # `old` = before that, id % 24 shared 10 ms slots
                d = (self.id % 24) * SLOT_S if self.old else self.id * 0.006
                return [(d, "@%d PONG %d %s %s" % (self.id, self.id, self.name, self.type))]
            mm = re.match(r"(?i)^CHIPS (\d+) (\d+) (\d+)$", cmd)
            if mm and not self.old:
                lo, hi, salt = map(int, mm.groups())
                if not lo <= self.id <= hi:
                    return []
                slot = (self.id - lo) % 24 + 24 * (fnv(self.chip, salt) % 2)
                return [(slot * SLOT_S, "@%d CHIP %s%s" % (self.id, self.chip, " G" if self.gateway else ""))]
            return []
        if addr.isdigit() and int(addr) == self.id:
            return [(0, "@%d %s" % (self.id, self._run(cmd)))]
        return []

    def _run(self, cmd):
        m = re.match(r"(?i)^SET ID (\d+)$", cmd)
        if m and 1 <= int(m.group(1)) <= 247:
            self.id = int(m.group(1))
            return "OK id=%d" % self.id
        return "ERR"


class Gateway(Board):
    """A board with a second link: a whole bus behind it (firmware: RS485Bus::setDownstream).

    `#>12>7 cmd` goes down as `#7 cmd`; `#>12>* cmd` is a broadcast on the bus behind
    it; what comes back is relayed upstream as `@>12>...` (RS485Bus::onDownstreamLine).
    Broadcasts on its OWN bus are never forwarded. `hop_s` is the relay's own delay.
    """
    def __init__(self, *a, down=None, hop_s=0.004, **k):
        super().__init__(*a, **k)
        self.down, self.hop_s, self.gateway = down, hop_s, True

    def hear(self, line):
        m = re.match(r"^#>(\d+)(>\S+)? (.+)$", line)
        if not m:
            return super().hear(line)
        if int(m.group(1)) != self.id:
            return []
        rest, cmd = m.group(2), m.group(3)
        if not rest:                       # ">12" = addressed to us alone
            return super().hear("#%d %s" % (self.id, cmd))
        if rest.count(">") + 1 > 4:        # BusPath::MAX_DEPTH
            return []
        out = []
        nxt = rest if ">" in rest[1:] else rest[1:]     # more hops: stay a path
        for d, text in self.down.frames("#%s %s" % (nxt, cmd)):
            if text.startswith("@"):
                who, _, tail = text[1:].partition(" ")
                out.append((d + self.hop_s, "@>%d>%s %s" % (self.id, who.lstrip(">"), tail)))
            else:
                out.append((d + self.hop_s, text))      # wreckage stays wreckage
        return out


class Bus:
    def __init__(self, boards):
        self.boards = list(boards)
        self.clock = 0.0          # virtual seconds spent listening
        self.collisions = 0       # frames destroyed

    def frames(self, line):
        """[(delay_s, text)] this wire carries for one request, collisions applied."""
        frames = []
        for b in self.boards:
            frames += [(d, t) for d, t in b.hear(line)]
        frames.sort()
        bad, last_end = set(), -1.0
        for i, (d, t) in enumerate(frames):
            if d < last_end:                     # starts while another is on the wire
                bad.update((i - 1, i))
            last_end = max(last_end, d + len(t) * BYTE_S)
        out = []
        for i, (d, t) in enumerate(frames):
            if i in bad:
                self.collisions += 1
                out.append((d, "\x00garbled"))      # wreckage the hub cannot parse
            else:
                out.append((d, t))
        return out

    def exchange(self, line, window):
        self.clock += window
        return [t for d, t in self.frames(line) if d <= window]
