"""The hub hands each module its group-mates' WiFi passwords (user 2026-09-28).

Every module raises its own WiFi (hotspot). Its password is 12345678 out of
the box, the group-derived one once it joins a group, or whatever its owner
chose with APPASS. A module that wants to lean on a neighbour's hotspot has to
know that neighbour's password - and after an owner changes it, nobody but the
hub knows it, because the hub is the one thing already talking to every board.

So, on a slow clock: ask every module this hub can reach for its group, its
hotspot name and its password; then tell each module in a group the others'
with PEERPASS. Only what changed is sent, so a quiet site costs two queries per
board per round and no flash writes. Ungrouped modules are left alone - the
group is what says these boards belong together.
"""
import re
import threading
import time

_hub = None           # the main module, set by bind()
ROUND_S = 120         # a password changes rarely; this is plenty
_sent = {}            # (board key, peer ssid) -> password last handed over
_last = {"at": 0, "groups": {}, "sent": 0, "error": ""}
_lock = threading.Lock()


def bind(hub):
    global _hub
    _hub = hub


def parse_group(reply):
    """`GROUP "show" appass=abc...` -> ("show", "abc..."); ungrouped -> ("", pass)."""
    m = re.search(r'GROUP\s+(?:"([^"]*)"|\(none\))\s+appass=(\S+)', reply or "")
    if not m:
        return None, None
    return m.group(1) or "", m.group(2)


def parse_ap(reply):
    """The hotspot name out of a WIFI reply: ... ap="nong" apip=..."""
    m = re.search(r'\bap="([^"]+)"', reply or "")
    return m.group(1) if m else ""


def share_once(modules=None, cmd=None):
    """One round. Returns {group: [ssid, ...]} and how many PEERPASS went out.

    `modules` and `cmd` default to the hub's own; QC passes fakes.
    """
    modules = modules if modules is not None else _hub.modules_here()
    cmd = cmd or _hub.dev_cmd
    boards = []
    for m in modules:
        dev = m.get("best")
        if not dev or m.get("stale"):
            continue
        try:
            group, pw = parse_group(cmd(dev, "GROUP"))
            ssid = parse_ap(cmd(dev, "WIFI")) if group else ""
        except Exception:                          # noqa: BLE001 - next round
            continue
        if group and ssid and pw:
            boards.append({"key": repr(m.get("key") or dev), "dev": dev,
                           "group": group, "ssid": ssid, "pass": pw})
    groups = {}
    for b in boards:
        groups.setdefault(b["group"], []).append(b)
    sent = 0
    for mates in groups.values():
        for me in mates:
            for other in mates:
                if other is me:
                    continue
                k = (me["key"], other["ssid"])
                if _sent.get(k) == other["pass"]:
                    continue                       # it already has this one
                try:
                    said = cmd(me["dev"], "PEERPASS %s %s" % (other["ssid"], other["pass"]))
                except Exception:                  # noqa: BLE001
                    continue
                if (said or "").startswith("OK"):
                    _sent[k] = other["pass"]
                    sent += 1
    out = {g: sorted(b["ssid"] for b in ms) for g, ms in groups.items()}
    with _lock:
        _last.update(at=time.time(), groups=out, sent=_last["sent"] + sent, error="")
    return out, sent


def status():
    with _lock:
        return dict(_last)


def loop():
    time.sleep(20)                                 # let the first scan settle
    while True:
        try:
            share_once()
        except Exception as e:                     # noqa: BLE001
            with _lock:
                _last["error"] = str(e)
        time.sleep(ROUND_S)
