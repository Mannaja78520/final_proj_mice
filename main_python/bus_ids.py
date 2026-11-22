"""Find, check and repair board ids on ONE RS485 bus - however many boards.

Why this exists (numbers: docs/architecture/scaling-ids.md, qc/lib/bus_sim.py):
a plain `#* PING` squeezes every board into 24 reply slots, so 247 boards put
~10 on each slot and the hub reads wreckage. And the default id is one MAC
byte, so two boards can share an id; then `#12 ...` reaches both.

This class speaks the ranged protocol (firmware/src/core/BusAddr.h):
  PING lo hi      one board per slot, no collisions between unique ids
  CHIPS lo hi s   each board reports its permanent chip; duplicates split lanes
  #~chip SET ID   re-address one board by its chip

It knows nothing about serial ports: `exchange(line, seconds)` sends one bus
line and returns the lines heard. The hub gives it a real port, QC a fake bus.
"""
import re

SLOTS = 24          # must match BusAddr::SLOTS
LANES = 2           # must match BusAddr::LANES
SLOT_S = 0.010
MAX_ID = 247

_PONG = re.compile(r"^@(\d+)\s+PONG\s+(\d+)\s+(.+)\s+(\S+)$")
_CHIP = re.compile(r"^@(\d+)\s+CHIP\s+([0-9A-Fa-f]{12})( G)?$")   # " G" = gateway


class BusIds:
    def __init__(self, exchange, salts=tuple(range(1, 17))):
        self.exchange = exchange
        self.salts = salts
        self.garbled = 0     # lines heard that were neither PONG nor CHIP
        self.gateways = set()   # chips that said "G": a bus hangs behind them

    @staticmethod
    def ranges(lo=1, hi=MAX_ID):
        return [(a, min(a + SLOTS - 1, hi)) for a in range(lo, hi + 1, SLOTS)]

    def census(self, lo=1, hi=MAX_ID):
        """{id: {"name","type"}} of every board that answered, range by range."""
        found = {}
        # Boards on OLD firmware answer every ranged PING in slot id % 24, which
        # can land on a new board's slot and wreck both - the same way every time
        # for the same ranges. So a pass that heard wreckage is repeated with the
        # range start moved up by 1, 2, 3 ids: a different slot pairing each time
        # (old board k wrecks new board k+1+shift, so a new board is only lost
        # when old boards sit on every one of the ids just below it).
        # The union of the passes is what is on the bus (qc check_bus_scale).
        for shift in (0, 1, 2, 3):
            bad = 0
            for a in range(lo + shift, hi + 1, SLOTS):
                a0, b0 = a, min(a + SLOTS - 1, hi)
                for ln in self.exchange("#* PING %d %d" % (a0, b0), SLOTS * SLOT_S + 0.15):
                    m = _PONG.match(ln)
                    if m:
                        found[int(m.group(1))] = {"name": m.group(3), "type": m.group(4)}
                    else:
                        bad += 1
            self.garbled += bad
            if not bad:
                break
        return found

    def chips(self, lo=1, hi=MAX_ID, only=None):
        """{id: {chip, ...}}: every chip heard per id, over several salts.

        Two boards on one id answer in the same slot of different lanes only
        half the time per salt, so the salts are what make a duplicate certain
        to show. A range that came back garbled is simply asked again.
        """
        out = {}
        self.unclean = []        # ranges that never came back without wreckage
        for a, b in self.ranges(lo, hi):
            if only is not None and not any(a <= i <= b for i in only):
                continue          # nobody lives here: skip its ~0.6 s
            for salt in self.salts:
                bad = 0
                for ln in self.exchange("#* CHIPS %d %d %d" % (a, b, salt),
                                        SLOTS * LANES * SLOT_S + 0.15):
                    m = _CHIP.match(ln)
                    if m:
                        out.setdefault(int(m.group(1)), set()).add(m.group(2).upper())
                        if m.group(3):
                            self.gateways.add(m.group(2).upper())
                    else:
                        bad += 1
                self.garbled += bad
                # A pass with no wreckage is complete: every board in the range
                # was heard alone, duplicates included (they sit in different
                # lanes). Only a garbled pass needs another salt. That is what
                # keeps a clean 247-board bus at one pass per range (~7 s).
                if not bad:
                    break
            else:
                self.unclean.append((a, b))
        return out

    def duplicates(self, lo=1, hi=MAX_ID):
        """{id: sorted chips} for ids that more than one board answers to."""
        return {i: sorted(c) for i, c in self.chips(lo, hi).items() if len(c) > 1}

    def fix(self, lo=1, hi=MAX_ID):
        """Give every duplicate but one its own free id. Returns {chip: new id}.

        The lowest chip keeps the id (stable between runs); the others move to
        the lowest unused id. Verified afterwards: a move that did not take is
        reported, never assumed.
        """
        moved, failed = {}, []
        for _round in range(12):    # three boards on one id may hide one another
            seen = self.chips(lo, hi)
            dup = sorted(i for i, c in seen.items() if len(c) > 1)
            if not dup and not self.unclean:
                break
            # an unclean range hides boards: ask it again next round
            used = set(seen)
            for ident in dup:
                for chip in sorted(seen[ident])[1:]:
                    free = next((n for n in range(1, MAX_ID + 1) if n not in used), None)
                    if free is None:
                        failed.append(chip)   # bus full: needs another bus
                        continue
                    self.exchange("#~%s SET ID %d" % (chip, free), 0.2)
                    used.add(free)
                    moved[chip] = free
        # verify: a move that did not take is reported, never assumed
        now = self.chips(lo, hi) if moved else {}
        for chip, new in list(moved.items()):
            if chip not in now.get(new, set()):
                failed.append(chip)
                del moved[chip]
        # one entry per chip: a full bus retried every round and listed the same chip 12 times
        return {"moved": moved, "failed": sorted(set(failed))}
