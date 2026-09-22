"""One list of modules: every board once, with every route to it, fastest first.

Moved out of main.py on 2026-09-23 (A26-93). Nothing here changed in
behaviour. main.py imports these names back and calls bind() with itself;
names that live there, and names QC swaps on main, are read late as _hub.
"""
import json
import socket
import time
import urllib.error
import urllib.parse
import urllib.request

_hub = None           # the main module, set by bind()


def bind(hub):
    global _hub
    _hub = hub


def board_key(mod):
    """What makes this board THIS board.

    The chip MAC when the board reports one - it cannot be changed, so it is
    the only honest answer. Older firmware does not report it, and then the id
    is all there is: it is used, but qualified with the type, because two blank
    boards from the same box share a default id and are not the same board.

    Returns a tuple so two boards can never collide by accident of formatting.
    """
    chip = (mod.get("chip") or "").strip().upper()
    if chip:
        return ("chip", chip)
    ident = mod.get("id")
    if ident is not None:
        return ("id", str(ident), (mod.get("type") or "").lower())
    return ("addr", mod.get("dev") or mod.get("ip") or repr(mod))


_route_table = {}   # board key -> its live local devs, fallback order (A26-79)


def _live_devs(m):
    """Routes worth choosing between: live, and WiFi only if the radio is on.

    Fallback order, used until something is measured: WiFi first, then the
    cable - the order the hub page used before latency was measured (A26-7).
    """
    rs = [r for r in m.get("routes") or [] if not r.get("stale")]
    radio_off = (m.get("wifi_mode") or "") == "off"
    wifi = [r["dev"] for r in rs if r.get("kind") == "wifi" and not radio_off]
    cable = [r["dev"] for r in rs if r.get("kind") in ("usb", "rs485")]
    return wifi + cable


def _pick_route(m):
    """Stamp each route with its measured ms and the board with `best`."""
    key = m.get("key") or ""
    for r in m.get("routes") or []:
        if r.get("kind") in ("usb", "rs485", "wifi"):
            _hub.route_latency.LAT.bind(r["dev"], key)
            ms = _hub.route_latency.LAT.ms(r["dev"])
            if ms is not None:
                r["ms"] = round(ms, 1)
    live = _live_devs(m)
    _route_table[key] = live
    m["best"] = _hub.route_latency.LAT.choose(key, live) if len(live) > 1 else (live[0] if live else None)


def resolve_auto(dev):
    """`auto:<board key>` -> the fastest live route to that board, right now.

    Resolved on EVERY call, so a page opened on auto: follows the board from
    cable to WiFi and back without being reopened.
    """
    key = dev[5:]
    live = _route_table.get(key)
    if live is None:
        for m in modules_here():
            if m.get("key") == key:
                live = _route_table.get(key)
                break
    if not live:
        raise ValueError("that board is not reachable any way right now")
    return _hub.route_latency.LAT.choose(key, live) if len(live) > 1 else live[0]


def route_probe_once():
    """PING the routes nobody is timing, for boards reached more than one way.

    Gentle on purpose (Codex review 2026-09-21): never while a show plays,
    never a port that is closed (opening one can reset the board), never
    counted as a client using the cable. A route in use is timed by its own
    traffic; this only keeps the OTHER routes known.
    """
    if _hub.show.running():
        return 0
    n = 0
    fresh_for = _hub.route_latency.LAT.cfg["sampleTtlSec"] / 2.0
    for key, live in list(_route_table.items()):
        if len(live) < 2:
            continue
        for dev in live:
            age = _hub.route_latency.LAT.age(dev)
            if age is not None and age < fresh_for:
                continue
            try:
                kind, addr, bus, _peer = _hub.parse_dev(dev)
                if kind == "usb":
                    if addr not in _hub._usb_open or addr in _hub._flash_ports:
                        continue
                    _hub.usb_cmd(addr, "PING", bus, wait=1.0, client=False)
                else:
                    _hub.dev_cmd(dev, "PING", wait=2.0)
                n += 1
            except Exception:                 # noqa: BLE001 - usb_cmd/dev_cmd
                pass                          # already marked the route failed
    return n


def route_probe_loop():
    while True:
        time.sleep(_hub.route_latency.LAT.cfg["probeEverySec"])
        try:
            route_probe_once()
        except Exception as e:                # noqa: BLE001
            print("[hub] route probe:", e)


def modules_here(force=False):
    """Every module this PC can reach, once each, with every way to reach it.

    The hub used to hand the page two lists and let it draw both. A board that
    is plugged in AND on the WiFi appeared twice, as two robots, with different
    controls on each row - so which row you happened to click decided whether
    the command went down the cable or over the air.
    """
    out = {}

    def add(mod, route):
        key = board_key(mod)
        seen = out.get(key)
        if not seen:
            # `stale` is deliberately NOT copied here: it belongs to the ROUTE
            # that went quiet, not to the board. A nong on a cable that also
            # missed a WiFi sweep is not late - it is in front of you.
            seen = {k: v for k, v in mod.items() if k not in ("dev", "stale",
                                                              "lastSeen")}
            seen["routes"] = []
            seen["key"] = "/".join(str(p) for p in key)
            out[key] = seen
        # A board answering on WiFi knows its own name and type better than a
        # cable probe that ran a minute ago, so later, richer answers win - but
        # never overwrite something with nothing, and NEVER from a route that
        # has gone quiet. Renaming a board (SET NAME, or the module site) is
        # answered at once on the cable while the WiFi sweep keeps handing back
        # the record it last heard, for the whole grace period: the row then
        # flips between the old name and the new one every few seconds, and
        # the person who just renamed it cannot tell which board they are
        # looking at. A late answer may still ADD a field nothing else knows.
        fresh = not mod.get("stale")
        for field in ("name", "type", "group", "fw", "ip", "id", "chip"):
            if mod.get(field) in (None, "", []):
                continue
            if not fresh and seen.get(field) not in (None, "", []):
                continue
            seen[field] = mod[field]
        if mod.get("stale"):
            route = dict(route, stale=True, lastSeen=mod.get("lastSeen"))
        if route not in seen["routes"]:
            seen["routes"].append(route)

    for u in _hub.probe_usb_all(force):
        mod = u.get("module")
        # A port with NO board of its own can still have a bus behind it - that
        # is exactly what an RS485 adapter is. Skipping the port when its direct
        # probe came back empty threw away every module on the bus, so a real
        # rig showed three boards of four and the missing one was the nong.
        # The fake never showed it: its port has both a module AND a bus.
        if mod:
            add(mod, {"kind": "usb", "dev": "usb:" + u["port"], "port": u["port"]})
        for b in (u.get("rs485") or []):
            add(b, {"kind": "rs485", "bus": b.get("id"),
                    "dev": "usb:%s:%s" % (u["port"], b.get("id")),
                    "port": u["port"]})

    for mod in _hub.scan_modules(force):
        ip = mod.get("ip")
        if not ip:
            continue
        add(mod, {"kind": "wifi", "dev": "wifi:" + ip, "ip": ip})

    # A board is late only when EVERY way in is late. One live route is enough
    # to call it present, which is the whole point of listing routes at all.
    for seen in out.values():
        rs = seen["routes"]
        if rs and all(r.get("stale") for r in rs):
            seen["stale"] = True
            ago = [r.get("lastSeen") for r in rs if r.get("lastSeen") is not None]
            seen["lastSeen"] = min(ago) if ago else None
        _pick_route(seen)

    # A stable order, so the list does not shuffle under someone's hand between
    # two scans: named boards first, by name, then by whatever identity there is.
    return sorted(out.values(),
                  key=lambda m: ((m.get("name") or "~").lower(), str(m.get("id"))))


def remote_modules(force=False):
    """What the OTHER PCs on this network are holding. (modules, errors).

    Split out so /api/allmods and the merged list below cannot drift into two
    different ideas of what another hub is offering.
    """
    out, errs = [], []
    for h in _hub.scan_hubs(force):
        ip = h.get("ip")
        if not ip:
            continue
        try:
            with urllib.request.urlopen(
                    "http://%s:%d/api/mine" % (ip, _hub.PORT), timeout=6) as r:
                d = json.loads(r.read().decode(errors="replace"))
            host = d.get("host") or ip
            for m in (d.get("modules") or []):
                m = dict(m)
                m["dev"] = "hub:%s/%s" % (ip, m["dev"])
                m["host"] = host
                m["hostIp"] = ip
                out.append(m)
        except Exception as e:                                # noqa: BLE001
            # A laptop that has just been closed is normal. Report it per PC
            # rather than failing the whole list.
            errs.append({"ip": ip, "error": str(e)})
    return out, errs


def modules_everywhere(force=False):
    """Every module ANY hub here can reach, once each. (modules, errors).

    Asked for 2026-08-21: *the module make it list the module only once for me
    please... make it list once show which module arviable on the top*. The
    page used to draw two lists - this PC's modules, and other PCs' modules -
    so a board plugged into the laptop next door appeared in one list while the
    same board on the venue WiFi appeared in the other. One robot, two rows,
    and the row you happened to press decided which machine carried the
    command.

    Merged HERE and not in the page, because `board_key` is the answer to *is
    this the same board* and it already lives here. A copy of that rule in
    JavaScript is a second answer to the same question.

    Every way in survives as a route, each saying which PC it goes through, so
    the row can show one module and the detail under it can show all four ways
    to reach it.
    """
    mine = modules_here(force)
    here = socket.gethostname()
    out = {}
    for m in mine:
        key = board_key(m)
        m = dict(m)
        m["mine"] = True
        m["routes"] = [dict(r, host=here, mine=True) for r in (m.get("routes") or [])]
        out[key] = m

    remote, errs = _hub.remote_modules(force)
    for m in remote:
        key = board_key(m)
        route = {"kind": "hub", "dev": m.get("dev"), "host": m.get("host"),
                 "hostIp": m.get("hostIp"), "mine": False}
        seen = out.get(key)
        if not seen:
            seen = {k: v for k, v in m.items() if k not in ("dev", "host", "hostIp")}
            seen["routes"] = []
            seen["mine"] = False
            seen["key"] = "/".join(str(p) for p in key)
            out[key] = seen
        # A board this PC can reach directly is still the same board when the
        # laptop next door can reach it too - so the far route is ADDED, never
        # a second row. Never overwrite something with nothing.
        for field in ("name", "type", "group", "fw", "ip", "id", "chip"):
            if m.get(field) not in (None, "", []) and not seen.get(field):
                seen[field] = m[field]
        if route not in seen["routes"]:
            seen["routes"].append(route)

    return sorted(out.values(),
                  key=lambda m: ((m.get("name") or "~").lower(),
                                 str(m.get("id")))), errs
