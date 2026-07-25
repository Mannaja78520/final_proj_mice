#!/usr/bin/env python3
"""bench.py — measure the dependent variables of the transport tests.

One tool for all three transports. It sends the same command N times, waits for
each reply, and reports the numbers the test tables ask for: success rate and
round-trip latency (min / mean / p95 / max).

    python bench.py wifi  --host 10.77.237.159 --cmd PING -n 50
    python bench.py wifi  --host nong.local    --cmd PING -n 50 --rate 10
    python bench.py usb   --port COM5          --cmd PING -n 50
    python bench.py rs485 --port COM6 --id 3   --cmd PING -n 50 --rate 50

wifi mode needs nothing but Python (stdlib urllib -> GET /api/cmd?c=...).
usb and rs485 modes need pyserial:  pip install pyserial

Options
  --cmd TEXT     command line to send (default PING). Use UPPERCASE: module
                 commands are matched case-sensitively by the firmware.
  -n N           how many commands to send (default 50)
  --rate R       commands per second (default: as fast as replies come back)
  --timeout S    per-command reply timeout in seconds (default 2.0)
  --id N         rs485 only: module address, framed as "#<id> <cmd>"
  --csv PATH     append one summary row to a CSV file
  --quiet        summary only, no per-command lines

Notes on the USB reader: boot-log lines share the port, so they are skipped —
but only when they look like a real log TAG ("[wifi] ...", "[  1234][I] ..."),
never just because a line starts with "[". Replies such as PIN VALID ("[{...}]")
and FILES ('["..."]') are JSON arrays that also start with "[" and must NOT be
skipped. Test USB-04 is the experiment for exactly this rule.
"""
import argparse
import csv
import os
import re
import statistics
import sys
import time
import urllib.parse
import urllib.request

# a boot-log line: "[wifi] ...", "[boot] ...", "[  1234][I][x.cpp:12] ..."
LOG_LINE = re.compile(r"^\[(?:[a-z]{2,8}\]|\s*\d+\]\[)")


def is_log_line(line):
    """True for firmware log noise, False for a real reply (incl. JSON arrays)."""
    return bool(LOG_LINE.match(line))


def percentile(values, p):
    if not values:
        return float("nan")
    s = sorted(values)
    k = (len(s) - 1) * p
    lo, hi = int(k), min(int(k) + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


class WifiLink:
    """HTTP GET /api/cmd?c=<command> — one connection per command, like a script."""

    name = "wifi"

    def __init__(self, args):
        self.base = "http://%s/api/cmd" % args.host
        self.timeout = args.timeout

    def send(self, cmd):
        url = self.base + "?" + urllib.parse.urlencode({"c": cmd})
        with urllib.request.urlopen(url, timeout=self.timeout) as r:
            return r.read().decode("utf-8", "replace").strip()

    def close(self):
        pass


class SerialLink:
    """USB serial, or RS485 through a dongle when --id is given."""

    def __init__(self, args, framed):
        try:
            import serial  # pyserial
        except ImportError:
            sys.exit("pyserial is required for usb/rs485 mode:  pip install pyserial")
        self.framed = framed
        self.addr = args.id
        self.timeout = args.timeout
        self.name = "rs485" if framed else "usb"
        self.ser = serial.Serial(args.port, 115200, timeout=0.05)
        time.sleep(0.2)
        self.ser.reset_input_buffer()

    def send(self, cmd):
        line = ("#%d %s" % (self.addr, cmd)) if self.framed else cmd
        self.ser.write((line + "\n").encode())
        self.ser.flush()
        deadline = time.monotonic() + self.timeout
        buf = ""
        want = "@%d " % self.addr if self.framed else None
        while time.monotonic() < deadline:
            chunk = self.ser.read(256).decode("utf-8", "replace")
            if not chunk:
                continue
            buf += chunk
            while "\n" in buf:
                raw, buf = buf.split("\n", 1)
                raw = raw.strip("\r ").strip()
                if not raw or is_log_line(raw):
                    continue
                if want is None:
                    return raw
                if raw.startswith(want):
                    return raw[len(want):]
                # an '@' line from a different module: not our reply, keep waiting
        raise TimeoutError("no reply in %.1fs" % self.timeout)

    def close(self):
        try:
            self.ser.close()
        except Exception:
            pass


class _LinkArgs:
    """Minimal stand-in for the argparse namespace the link classes expect."""

    def __init__(self, host, port, id, timeout):
        self.host, self.port, self.id, self.timeout = host, port, id, timeout


def open_link(transport, host=None, port=None, id=0, timeout=2.0):
    """Factory used by testapp.py so both tools share one transport layer."""
    a = _LinkArgs(host, port, id, timeout)
    if transport == "wifi":
        if not host:
            raise ValueError("wifi needs a host (ip or <name>.local)")
        return WifiLink(a)
    if transport in ("usb", "rs485"):
        if not port:
            raise ValueError("%s needs a serial port" % transport)
        if transport == "rs485" and not (1 <= id <= 247):
            raise ValueError("rs485 needs --id 1-247")
        return SerialLink(a, framed=(transport == "rs485"))
    raise ValueError("unknown transport %r" % transport)


def run(link, args):
    lat, replies, lost = [], 0, 0
    first_reply = None
    interval = (1.0 / args.rate) if args.rate else 0.0
    t_series = time.monotonic()

    for i in range(args.n):
        if interval:
            due = t_series + i * interval
            now = time.monotonic()
            if due > now:
                time.sleep(due - now)
        t0 = time.monotonic()
        try:
            reply = link.send(args.cmd)
            ms = (time.monotonic() - t0) * 1000.0
            lat.append(ms)
            replies += 1
            if first_reply is None:
                first_reply = reply
            if not args.quiet:
                print("%4d  %7.1f ms  %s" % (i + 1, ms, reply[:100]))
        except Exception as e:
            lost += 1
            if not args.quiet:
                print("%4d  LOST      %s" % (i + 1, e))

    print("\n--- %s  cmd=%r  n=%d  rate=%s ---" %
          (link.name, args.cmd, args.n, args.rate or "max"))
    print("sent %d   replied %d   lost %d   success %.1f %%" %
          (args.n, replies, lost, 100.0 * replies / args.n if args.n else 0.0))
    if lat:
        print("latency ms:  min %.1f   mean %.1f   p95 %.1f   max %.1f" %
              (min(lat), statistics.mean(lat), percentile(lat, 0.95), max(lat)))
    if first_reply:
        print("first reply: %s" % first_reply[:200])

    if args.csv:
        new = not os.path.exists(args.csv)
        with open(args.csv, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if new:
                w.writerow(["when", "transport", "target", "cmd", "n", "rate",
                            "replied", "lost", "success_pct", "min_ms", "mean_ms",
                            "p95_ms", "max_ms", "first_reply"])
            w.writerow([time.strftime("%Y-%m-%d %H:%M:%S"), link.name,
                        getattr(args, "host", None) or getattr(args, "port", ""),
                        args.cmd, args.n, args.rate or "max", replies, lost,
                        round(100.0 * replies / args.n, 2) if args.n else 0,
                        round(min(lat), 1) if lat else "",
                        round(statistics.mean(lat), 1) if lat else "",
                        round(percentile(lat, 0.95), 1) if lat else "",
                        round(max(lat), 1) if lat else "",
                        (first_reply or "")[:200]])
        print("appended a summary row to %s" % args.csv)

    return 0 if lost == 0 else 1


def main():
    p = argparse.ArgumentParser(description="transport benchmark for the mice modules")
    p.add_argument("transport", choices=["wifi", "usb", "rs485"])
    p.add_argument("--host", help="wifi: ip or <name>.local")
    p.add_argument("--port", help="usb/rs485: serial port, e.g. COM5")
    p.add_argument("--id", type=int, default=0, help="rs485: module address 1-247")
    p.add_argument("--cmd", default="PING", help="command line to send (UPPERCASE)")
    p.add_argument("-n", type=int, default=50, help="number of commands")
    p.add_argument("--rate", type=float, default=0, help="commands per second")
    p.add_argument("--timeout", type=float, default=2.0, help="reply timeout, seconds")
    p.add_argument("--csv", help="append a summary row to this CSV")
    p.add_argument("--quiet", action="store_true")
    args = p.parse_args()

    if args.transport == "wifi":
        if not args.host:
            p.error("wifi mode needs --host")
        link = WifiLink(args)
    else:
        if not args.port:
            p.error("%s mode needs --port" % args.transport)
        if args.transport == "rs485" and not (1 <= args.id <= 247):
            p.error("rs485 mode needs --id 1-247")
        link = SerialLink(args, framed=(args.transport == "rs485"))

    try:
        return run(link, args)
    finally:
        link.close()


if __name__ == "__main__":
    sys.exit(main())
