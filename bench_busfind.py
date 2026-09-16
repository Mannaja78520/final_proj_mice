"""Find who is on the RS485 bus, with nothing configured.

Mixed transceivers (MAX485, XY-485, ...) are all plain RS485 and speak the
same wire: A-to-A, B-to-B, common GND, 115200. Which brand sits where does
not matter to software.

For every COM port on this PC: open it, shout the broadcast PING, see who
answers. Ports that answer are bus consoles. Then each console pings the
ids heard on the OTHER console through the bus - the part one console alone
cannot prove (a lone console hears itself: bridge() answers self-addressed
and broadcast frames locally, so silence there means nothing).

Usage:
    python bench_busfind.py                every COM port
    python bench_busfind.py COM26 COM29    just these

CLOSE THE HUB FIRST - it owns the ports, and an open port here fails anyway.
"""
import sys
import time

import serial
from serial.tools import list_ports

BAUD = 115200


def open_port(name):
    s = serial.Serial(name, BAUD, timeout=0.1)
    s.dtr = False                       # clearing these AFTER open still
    s.rts = False                       # reboots some boards - wait it out
    time.sleep(3.5)
    s.reset_input_buffer()
    return s


def read_lines(s, seconds):
    # FIXED window - a sliding one never closes while boot spam keeps
    # arriving, and the script hung on exactly that.
    out, buf, end = [], b"", time.time() + seconds
    while time.time() < end:
        chunk = s.read(256)
        if chunk:
            buf += chunk
            while b"\n" in buf:
                ln, buf = buf.split(b"\n", 1)
                out.append(ln.decode(errors="replace").strip())
    return out


def shout(s, cmd, seconds=1.6):
    s.write(cmd.encode() + b"\n")
    return read_lines(s, seconds)


def main():
    wanted = [w.upper() for w in sys.argv[1:]]
    # Only real USB-serial adapters: a phantom COM port (Bluetooth incoming,
    # modem) can BLOCK FOREVER inside open(), which is what hung the first
    # run on COM4. Real CH340/CP210x/FTDI ports carry a vendor id.
    names = [p.device for p in list_ports.comports()
             if p.vid is not None
             and (not wanted
                  or any(p.device.upper().endswith(w) for w in wanted))]
    print("ports seen:", ", ".join(names) if names else "(none)", flush=True)

    consoles = {}
    for name in names:
        try:
            s = open_port(name)
        except Exception as e:                        # noqa: BLE001
            print("  %-14s busy or absent (%s)" % (name, str(e)[:40]))
            continue
        ids = []
        for ln in shout(s, "PING", 1.2):
            if ln.startswith("PONG"):
                parts = ln.split()
                ids.append((parts[1] if len(parts) > 1 else "?",
                            " ".join(parts[2:3]) if len(parts) > 2 else "",
                            " ".join(parts[3:])[:24]))
        if ids:
            consoles[name] = (s, ids)
            print("  %-14s CONSOLE - broadcast answered by:" % name)
            for pid, _, who in ids:
                print("                     id %-4s" % pid)
        else:
            print("  %-14s no answer to broadcast (adapter without module,"
                  " or dead bus side)")
            s.close()

    # ---- cross-ping: the only proof that counts ------------------------
    ok = True
    items = list(consoles.items())
    for aname, (a, aids) in items:
        for bname, (b, bids) in items:
            if aname == bname:
                continue
            for pid, _, _ in bids:
                got = shout(a, "#%s PING" % pid)
                hit = [ln for ln in got if "PONG" in ln and pid in ln]
                if hit:
                    print("LINK OK   %s -> %s id %s : %s"
                          % (aname, bname, pid, hit[0][:60]))
                else:
                    ok = False
                    print("LINK DEAD %s -> %s id %s : no answer"
                          % (aname, bname, pid))
    if len(consoles) < 2:
        print("\nfewer than two consoles answered - wire both driver boards,"
              " then run this again")
    elif ok:
        print("\nBUS ALIVE - every console reached every other console")
    else:
        print("\nbus problems above - check A/B swap, GND between the two"
              " driver boards, and DE/RE wiring")


if __name__ == "__main__":
    main()
