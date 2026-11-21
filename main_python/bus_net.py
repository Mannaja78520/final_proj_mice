"""Every board reachable through chained buses, loops and clones included.

A bus board that has a second link is a GATEWAY (firmware BusPath.h): a whole
bus hangs behind it, and a board on THAT bus can be a gateway too. This walks
the tree from one root cable and answers, for every board: which chip is it,
by which path is it reached (">12>7"), and is it also reachable another way.

Rules that make "any topology a customer can build" safe:
  * IDENTITY is the chip. A path is only a route. A chip met a second time is
    NOT descended into again: that is how a ring, a board on two buses, and a
    gateway wired back to the bus above all end (they are recorded as extra
    routes, see `loops`).
  * Depth is capped (BusPath::MAX_DEPTH = 4 hops: up to 3 gateways in a row) and so is the
    node count, so a miswired or hostile rig cannot make the scan run forever.
  * Broadcasts never cross a gateway; each bus is scanned by an explicit
    `#>12>* PING lo hi`. No storms.
  * Ids only need to be unique PER BUS, so ids repeat across buses by design;
    duplicates inside one bus are repaired with BusIds.fix on that bus.
  * Same chip at two places that are NOT linked by a loop looks identical to a
    loop from here (a cloned chip). Both are reported in `loops`; a person
    decides, because the data alone cannot tell them apart.

`exchange(line, seconds)` is the root link: a USB port, a WiFi socket, a fake.
The same walk therefore works whatever carries the first hop.
"""
import re

import bus_ids

MAX_DEPTH = 4            # '>' hops in an address; keep equal to BusPath::MAX_DEPTH
                         # (= a board behind at most 3 gateways in a row)
MAX_BOARDS = 20000       # stop a runaway scan


class SubBus:
    """The bus behind a gateway, seen as an ordinary link for BusIds."""

    def __init__(self, parent_exchange, path, hop_window=0.08):
        self.parent, self.path, self.hop = parent_exchange, path, hop_window
        self.depth = path.count(">")

    def exchange(self, line, seconds):
        m = re.match(r"^#(\S+) (.*)$", line)
        addr, cmd = m.group(1), m.group(2)
        wrapped = "#%s>%s %s" % (self.path, addr, cmd)
        # every hop adds a relay delay; listen a little longer per level
        heard = self.parent(wrapped, seconds + self.hop * self.depth)
        prefix = "@%s>" % self.path
        out = []
        for ln in heard:
            if ln.startswith(prefix):
                out.append("@" + ln[len(prefix):])
            elif ln.startswith("\\x00") or not ln.startswith("@"):
                out.append(ln)                    # wreckage: BusIds counts it
        return out


class Topology:
    def __init__(self, exchange, max_depth=MAX_DEPTH):
        self.root = exchange
        self.max_depth = max_depth
        self.boards = {}        # chip -> {"path", "id", "bus", "gateway", "depth"}
        self.routes = {}        # chip -> [paths]  (every way found, shortest first)
        self.loops = []         # (chip, path already known, path found again)
        self.refused = []       # paths not descended into (too deep)
        self.buses = 0
        self.duplicate_ids = {}  # bus path -> {id: chips}
        self.links = {}          # bus path -> the link that talks to that bus (for repairs)

    def discover(self):
        self._scan("", self.root, 0)
        for chip in self.routes:
            self.routes[chip].sort(key=lambda p: (p.count(">"), p))
        return self

    def _scan(self, path, exchange, depth):
        self.buses += 1
        self.links[path or "root"] = exchange
        ids = bus_ids.BusIds(exchange, salts=tuple(range(1, 13)))
        found = ids.chips()
        dup = {i: sorted(c) for i, c in found.items() if len(c) > 1}
        if dup:
            self.duplicate_ids[path or "root"] = dup
        for ident in sorted(found):
            for chip in sorted(found[ident]):
                here = "%s>%d" % (path, ident) if path else ">%d" % ident
                if not path:
                    here = "%d" % ident          # first bus: plain id, as always
                known = self.boards.get(chip)
                if known:
                    self.routes[chip].append(here)
                    self.loops.append((chip, known["path"], here))
                    continue
                gw = chip in ids.gateways
                self.boards[chip] = {"id": ident, "path": here, "bus": path or "root",
                                     "gateway": gw, "depth": depth}
                self.routes[chip] = [here]
                if len(self.boards) > MAX_BOARDS:
                    return
                if gw:
                    gpath = here if path else ">%d" % ident
                    # a board behind it is addressed ">a>b>x": hops = gpath hops + 1,
                    # and the firmware drops lines with more than MAX_DEPTH hops
                    if gpath.count(">") + 1 > self.max_depth:
                        self.refused.append(here)
                        continue
                    self._scan(gpath, SubBus(self.root, gpath).exchange, depth + 1)

    @staticmethod
    def address(path):
        """Line prefix for a path: '5' -> '#5', '>12>7' -> '#>12>7'."""
        return "#" + path
