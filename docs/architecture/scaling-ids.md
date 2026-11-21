# Boards past 255, many buses, many companies (2026-11-21)

Measured in `qc/lib/bus_sim.py` (virtual time, real collision model), raw numbers in
`docs/experiments/2026-11-21_bus_scale.json`, pinned by `check_bus_scale`.
Everything below is **tested against a simulator and a host C++ compile, not on real boards.**

## The three things people mix up

| Name | Size | What it is for | Unique where |
|---|---|---|---|
| chip (eFuse MAC) | 12 hex, 48 bit | who the board IS, never changes | everywhere, every company |
| id | 1 byte, 1..247 | the short address on ONE RS485 cable | one bus only |
| group | text | which company/installation (also derives the WiFi password) | one company |

`hub_modules.board_key` already names a board by its **chip**. So one board that is on
USB, RS485 and WiFi at once is ONE row with three routes (fastest first, fail over when one
goes quiet). The id is only a detail of the RS485 route. Fix made 2026-11-21: a board with
no chip known is keyed by id + type + **the cable it was heard on** (before, board 5 on
COM3 and board 5 on COM4 merged into one).

## Why 255 is only an RS485 number, and the real limits

* Address byte: ids 1..247 per cable. More boards = more cables (one hub PC can own many
  USB-RS485 adapters, each is its own bus: 4 buses x 247 = 988 found, 988 distinct chips, 4.3 s each,
  scanned in parallel).
* Electrical: a MAX485 is **1 unit load, 32 nodes per segment** by spec (we use MAX485/XY485).
  247 on one cable needs 1/8-load transceivers (e.g. 256-node parts) or repeaters; lab-untested.
* WiFi/USB have no id limit; an ESP32 soft-AP serves only ~4-10 stations, so WiFi at scale means
  boards joining the venue router, not each other (router DHCP pool, not tested).
* Companies: each company runs its own hub; ids only need to be unique per cable. Across
  companies identity = (group, chip): chips never collide, so >255 customers is no problem.

## What broke at scale, and the fix

1. **Plain `#* PING` collapses.** 24 reply slots; boards found of 8/24/64/128/247 on a full bus:
   8 / 24 / 0 / 0 / 0. Ranged `PING lo hi` gives each id its own slot: 247 of 247, 0 collisions, 4.3 s.
2. **Default ids collide.** The id is one MAC byte: 100 boards -> 17 shared ids, 247 -> 60.
   `CHIPS lo hi salt` shows every chip per id (two lanes split duplicates; a clean pass is complete),
   `#~chip SET ID n` re-addresses one board, `BusIds.fix()` moves all but one to free ids, then verifies.
3. **A bad hash hid duplicates** (low FNV bit = parity, salt flipped it for all boards alike):
   fixed with an avalanche step; the C++ and Python hashes are compared bit for bit in QC.
4. Chips were only fetched for the first 6 boards of a bus; now all (once, cached by name).

## Mass power-on (all plugged in at once), bus time until every board is known and unique

| boards | 8 | 24 | 64 | 128 | 247 |
|---|---|---|---|---|---|
| seconds (one-off) | 11 | 41 | 43 | 95 | 141 |

Worst case (random default ids). Later scans cost ~4.3 s of ranged PING at most once a minute
per cable (7% bus duty); the chips are remembered. Normal commands are untouched: an addressed
`#id cmd` has no slot (2.6 ms on the wire with 1 or 247 boards); a command that arrives mid-scan
waits at most one range window (0.39 s).
Not covered: boards booting in the same millisecond on WiFi (join storm), USB hub power inrush
and Windows COM-port limits - need the lab; boards already have no RS485 chatter at boot.

## Plain steps to run it
1. Plug every cable (USB adapter = one bus). 2. The hub scans each cable range by range.
3. Duplicate ids are listed; `BusIds.fix()` gives each a free id (by chip). 4. Rows are by chip,
so WiFi/USB/RS485 of the same board merge into one.

## Chained buses: 247 -> bridge -> 247 -> bridge -> 247 (added 2026-11-21)

**Rule: a board is its chip; a path is only a route.** A bus board with a second link is a
*gateway*. Boards behind it are addressed by the ids of the buses crossed:
`#>100>200>7 CMD` = board 7 on the bus behind gateway 200 which sits on the bus behind gateway 100.
Replies come back as `@>100>200>7 ...`. The `>` prefix makes an old board read the address as 0
(its toInt), so old firmware stays silent instead of obeying `#12/7` as `#12`.
Gateways answer `CHIPS` with a trailing ` G`, so one pass finds every bridge without asking each board.
`bus_net.Topology` walks the tree from the root cable; each bus is scanned with the same ranged
PING/CHIPS as one bus (a `SubBus` wrapper adds the path). Root cable = USB port, WiFi socket or a fake,
so the same walk works whatever carries the first hop.

Simulated numbers (`check_bus_topology`, `docs/experiments/2026-11-21_bus_topology.json`):
3 buses x 247 = **741 boards found, 741 chips, 0 collisions**; the same ids (1..247) repeat on every bus.
Relay delay per hop is an ASSUMED 4 ms (not measured on hardware): reply 0 / 4 / 8 ms later at depth 0 / 1 / 2.

### Odd topologies and what happens

| Rig | What the code does |
|---|---|
| Bridge behind bridge (up to 3 gateways, 4 hops) | walked; a 5th hop is refused (listed in `refused`), firmware drops it too |
| Ring (B's gateway wired back to A) | a chip met twice is not entered again: scan ends, extra route kept in `loops` |
| Board on two buses | one chip, two routes; the shortest wins, the other is the fail-over |
| Same ids on different buses | fine: ids are per bus, identity is the chip |
| Ids clash inside a bridged bus | CHIPS shows every chip per id on that bus, `#>gw>~chip SET ID` repairs it |
| Cloned chip in two places | indistinguishable from a loop by data: reported in `loops` for a person to decide |
| Broadcast storm across bridges | impossible: broadcasts are never forwarded; `#>12>* PING lo hi` scans the bus behind 12 only |
| Wire loop carrying a line forever | each gateway strips one hop; a line dies after 4 |
| Old firmware next to a gateway | ignores `#>...` lines (reads as id 0) |
| Gateway dies | its whole subtree goes stale (same stale/lastSeen rules as one board); USB/WiFi routes of those boards still work |
| Bridge by WiFi (a WiFi board hosts a bus) | same Topology, root exchange = that WiFi socket |
| Two PCs masters on one cable | NOT solved in code: RS485 has one master; wire one hub per root cable (lab/doc rule) |
| Different baud on the second link | not detectable here; bridge ports must be set to the same baud |

Not built/untested: the second physical UART of a gateway board (firmware has `setDownstream`/`onDownstreamLine`
but no hardware owner wires them yet), hub UI for the tree, real timing of a relay hop, firmware compile (no pio here).
