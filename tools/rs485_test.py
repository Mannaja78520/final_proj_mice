#!/usr/bin/env python3
"""Measure how badly RS485 replies are corrupted, before and after a fix.

    python tools/rs485_test.py                     every module the hub can see
    python tools/rs485_test.py --dev usb:COM18:89  just this one
    python tools/rs485_test.py --rounds 10         more samples

WHY THIS EXISTS
---------------
Measured at the bench on 2026-08-20: every reply arriving over RS485 came back
with runs of NUL bytes replacing runs of characters - even a twenty byte PONG
read `PO` then four NULs then `ined cam` - while two boards on plain USB cables
answered byte-identically through the same hub process.

The cause found by the five-model panel is in RS485Bus::send: `Serial2.flush()`
empties the transmit FIFO, but the byte already being clocked out sits in the
shift register beyond it. The driver enable was dropped 20us later, and one byte
at 115200 takes 86.8us - so the last character was cut in half while the line
was still being driven. Half a character is a framing error, and a framing error
arrives as 0x00.

A theory that fits is not a measurement, which is what this is for. Run it with
one board on the NEW firmware and the others on the old, on the same wires at
the same moment: same bus, same instant, and no wiring change to blame.

WHAT IT PRINTS
--------------
Per module: how many replies came back whole, how many bytes were lost, and
where. A cable module is included on purpose as the control - if the cable rows
are dirty too, the problem is not the bus.
"""
import argparse
import http.cookiejar
import json
import urllib.parse
import urllib.request
from pathlib import Path

HUB = "http://127.0.0.1:8642"


def opener(password):
    """A logged-in opener. Commands need a login; reading the list does not."""
    jar = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    if password:
        req = urllib.request.Request(
            HUB + "/api/login",
            data=json.dumps({"password": password}).encode(),
            headers={"Content-Type": "application/json"})
        try:
            with op.open(req, timeout=20) as r:
                r.read()
        except Exception as e:                               # noqa: BLE001
            print("login failed (%s) - commands will be refused" % e)
    return op


def password_here():
    """The hub writes it in plain text beside itself, for exactly this."""
    f = Path(__file__).resolve().parent.parent / "main_python" / "hub_password.txt"
    if not f.is_file():
        return ""
    for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and " " not in line:
            return line
    return ""


def cmd(op, dev, c, timeout=40):
    url = (HUB + "/api/dev/cmd?dev=" + urllib.parse.quote(dev) +
           "&c=" + urllib.parse.quote(c))
    try:
        with op.open(url, timeout=timeout) as r:
            return r.read().decode("utf-8", "replace")
    except Exception as e:                                   # noqa: BLE001
        return "\x01ERR " + str(e)


def modules(op):
    with op.open(HUB + "/api/modules", timeout=180) as r:
        return (json.loads(r.read()) or {}).get("modules", [])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dev", help="one dev address; default every module found")
    ap.add_argument("--rounds", type=int, default=5)
    ap.add_argument("--cmd", default="INFO",
                    help="what to ask for; INFO is long enough to show damage")
    a = ap.parse_args(argv)

    op = opener(password_here())
    if a.dev:
        targets = [(a.dev, a.dev, "rs485" if a.dev.count(":") >= 2 else "usb")]
    else:
        targets = []
        for m in modules(op):
            for r in m.get("routes", []):
                d = r.get("dev") or ""
                # The hub's OWN word for how it reaches the board. Guessing from
                # the address was wrong within an hour: a colon count called a
                # camera on a plain cable an RS485 module, and the summary then
                # printed an all-clear over 227 corrupted bytes. A measuring
                # tool that reports the wrong thing confidently is worse than
                # no tool.
                targets.append((d, "#%s %s over %s"
                                % (m.get("id"), m.get("name"), r.get("kind")),
                                r.get("kind") or "?"))
    if not targets:
        print("no modules - is the hub running, and are the boards powered?")
        return 1

    print("%-26s %-7s %-7s %-8s %s" % ("module", "whole", "nulls", "shortest", "how"))
    print("-" * 74)
    worst = 0
    dirty_cable = None
    silent = []
    for dev, label, kind in targets:
        lens, nulls, whole = [], 0, 0
        for _ in range(a.rounds):
            reply = cmd(op, dev, a.cmd)
            if reply.startswith("\x01"):
                lens.append(0)
                continue
            n = reply.count("\x00")
            nulls += n
            lens.append(len(reply))
            if n == 0 and len(reply) > 8:
                whole += 1
        how = "RS485" if kind == "rs485" else "cable"
        print("%-26s %d/%-5d %-7d %-8d %s"
              % (label[:26], whole, a.rounds, nulls, min(lens) if lens else 0, how))
        # NO REPLY IS NOT A CLEAN REPLY. Counted apart, because the first
        # version of this summary said "every RS485 reply came back whole"
        # about a module that had answered nothing at all four times. A tool
        # that turns silence into an all-clear is worse than no tool.
        if not any(lens):
            silent.append(label)
        elif how == "RS485":
            worst = max(worst, nulls)
        elif nulls:
            dirty_cable = (label, nulls)

    print()
    if silent:
        print("SAID NOTHING AT ALL: %s. Not corruption - either the board is "
              "not answering or nothing reached it. Whatever else this run "
              "shows, it shows nothing about these." % ", ".join(silent))
    if dirty_cable:
        print("A CABLE is losing bytes (%d NULs on %s). That is not the bus: "
              "two other boards on plain cables answered whole. Look at that "
              "board and that adapter." % (dirty_cable[1], dirty_cable[0]))
    if worst:
        print("RS485 replies are still losing bytes (%d NULs). If the board on "
              "the bus is running the FIXED firmware, the turnaround was not "
              "the whole story - check the common ground and whether two "
              "transceivers share the pair." % worst)
    elif any(k == "rs485" for _d, _l, k in targets) and not silent:
        print("every RS485 reply came back whole.")
    if not worst and not dirty_cable and not silent:
        print("nothing lost a byte anywhere.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
