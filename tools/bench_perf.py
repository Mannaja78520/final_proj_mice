"""Does a real board keep up during every task? Reads PERF? around each one.

    python tools/bench_perf.py COM21            one pass over every task
    python tools/bench_perf.py COM21 --soak 600 then repeat for 600 s
    python tools/bench_perf.py 192.168.137.181  the same over WiFi (the hub
                                                may keep running)

Each task: PERF? (starts a clean window), run the task, PERF? again, print one
row. Moves stay small (+-10 deg around home, T >= 600 ms) and leave WAIST and
SHRUG alone, so it is safe on a dressed nong. Stop the hub first: it owns the
port while it runs. Limits the verdict uses are in LIMITS below.
"""
import re
import sys
import time

import serial

LIMITS = {"loop_max_us": 20000,   # one servo frame; longer = a frame can slip
          "frame_max_ms": 30,     # 50 Hz is 20 ms; 30 is a visible stutter
          "stack_free": 1024}     # bytes left on the loop task


def open_port(name):
    s = serial.Serial()
    s.port, s.baudrate, s.timeout = name, 115200, 0.05
    s.dtr = s.rts = False            # opening must not reset the board
    s.open()
    time.sleep(0.3)
    s.reset_input_buffer()
    return s


class Wifi:
    """The board's own /api/cmd, logged in with the shipped accounts."""
    LOGINS = [("admin", "admin123"), ("super_admin", "admin123"),
              ("manny", "12345678")]

    def __init__(self, ip):
        import urllib.error
        import urllib.parse
        import urllib.request
        self.ip, self.u, self.cookie = ip, urllib, ""
        for user, pwd in self.LOGINS:
            req = urllib.request.Request(
                "http://%s/api/login" % ip, method="POST",
                data=urllib.parse.urlencode({"user": user, "pass": pwd}).encode())
            try:
                with urllib.request.urlopen(req, timeout=10) as r:
                    c = r.headers.get("Set-Cookie") or ""
                    m = re.search(r"mice_board=([^;]+)", c)
                    if m:
                        self.cookie = m.group(1)
                        return
            except urllib.error.HTTPError as e:
                if e.code == 404:          # firmware with no login at all
                    return
        sys.exit("%s refused every shipped login" % ip)

    def get(self, path):
        req = self.u.request.Request("http://%s%s" % (self.ip, path),
                                     headers={"Cookie": "mice_board=" + self.cookie})
        try:
            with self.u.request.urlopen(req, timeout=10) as r:
                return len(r.read())
        except Exception:                  # noqa: BLE001
            return 0

    def ask(self, line, timeout):
        req = self.u.request.Request(
            "http://%s/api/cmd?c=%s" % (self.ip, self.u.parse.quote(line)),
            headers={"Cookie": "mice_board=" + self.cookie})
        try:
            with self.u.request.urlopen(req, timeout=max(timeout, 3)) as r:
                return r.read().decode(errors="replace")
        except Exception as e:             # noqa: BLE001 - a hang is a result
            return "ERR %s" % e


def ask(s, line, wait=1.5, want=None):
    if isinstance(s, Wifi):
        return "\n" + s.ask(line, wait) + "\n"
    s.write((line + "\n").encode())
    end, buf = time.time() + wait, ""
    while time.time() < end:
        buf += s.read(4096).decode(errors="replace")
        if want and re.search(want, buf):
            break
    return buf


def perf(s):
    m = re.search(r"PERF (.+)", ask(s, "PERF?", 2, r"PERF .*reset=\w+"))
    return dict(kv.split("=", 1) for kv in m.group(1).split()) if m else {}


def home_pose(s):
    m = re.search(r"^([\d.\- ]{20,})$", ask(s, "POSE?", 1.5, r"\n[\d.]"), re.M)
    return [float(x) for x in m.group(1).split()] if m else None


def pose(base, d):
    # joints 1-8 only; '-' keeps WAIST and SHRUG exactly where they are
    return " ".join("%.1f" % (a + d) for a in base[:8]) + " - -"


def tasks(s, base):
    yield "idle 5 s", lambda: time.sleep(5)
    yield "slow poses x6", lambda: [
        (ask(s, "POSE %s T 800" % pose(base, d), 0.2), time.sleep(0.9))
        for d in (10, -10, 10, -10, 10, 0)]
    yield "one joint sweep", lambda: [
        (ask(s, "JOINT 1 %.1f T 600" % (base[0] + d), 0.2), time.sleep(0.7))
        for d in (10, -10, 0)]
    yield "retarget 20/s while moving", lambda: [
        (ask(s, "POSE %s T 600" % pose(base, (i % 3 - 1) * 8), 0.02),
         time.sleep(0.05)) for i in range(60)]
    yield "status spam 20/s", lambda: [ask(s, "INFO", 0.05) for _ in range(60)]
    if isinstance(s, Wifi):
        yield "web page x5 while moving", lambda: (
            ask(s, "POSE %s T 3000" % pose(base, 8), 0.3),
            [s.get("/") for _ in range(5)], time.sleep(1),
            ask(s, "HOME T 1000", 0.3), time.sleep(1.3))
    yield "HELP (big reply)", lambda: ask(s, "HELP", 3)
    yield "FILES", lambda: ask(s, "FILES", 3)
    yield "stop mid-move", lambda: (
        ask(s, "POSE %s T 2000" % pose(base, 10), 0.3), time.sleep(0.5),
        ask(s, "STOP", 0.3), ask(s, "HOME T 1000", 0.3), time.sleep(1.3))
    yield "relax / attach", lambda: (
        ask(s, "RELAX", 0.5), time.sleep(0.5), ask(s, "ATTACH", 0.5))
    yield "home", lambda: (ask(s, "HOME T 1000", 0.3), time.sleep(1.3))


def run_once(s, base, first_boots):
    bad = []
    print("%-28s %8s %8s %8s %6s %7s %8s %6s %5s %s" % (
        "task", "loop_avg", "loop_max", "work_max", "frame", "frames",
        "heap_min", "stack", "boots", "reset"))
    for name, job in tasks(s, base):
        perf(s)
        job()
        p = perf(s)
        if not p:
            print("%-28s NO ANSWER - board restarted or hung" % name)
            bad.append(name + ": no answer")
            continue
        print("%-28s %8s %8s %8s %6s %7s %8s %6s %5s %s" % (
            name, p["loop_avg_us"], p["loop_max_us"], p["work_max_us"],
            p["frame_max_ms"], p["frames"], p["heap_min"], p["stack_free"],
            p["boots"], p["reset"]))
        if int(p["loop_max_us"]) > LIMITS["loop_max_us"]:
            bad.append("%s: loop_max %s us" % (name, p["loop_max_us"]))
        if int(p["frame_max_ms"]) > LIMITS["frame_max_ms"]:
            bad.append("%s: frame gap %s ms" % (name, p["frame_max_ms"]))
        if 0 < int(p["stack_free"]) < LIMITS["stack_free"]:
            bad.append("%s: stack %s B left" % (name, p["stack_free"]))
        if p["boots"] != first_boots:
            bad.append("%s: RESTARTED (boots %s -> %s, reset=%s)" % (
                name, first_boots, p["boots"], p["reset"]))
    return bad


def main(argv):
    port = argv[0]
    soak = float(argv[argv.index("--soak") + 1]) if "--soak" in argv else 0
    s = Wifi(port) if re.match(r"^\d+\.\d+\.\d+\.\d+$", port) else open_port(port)
    p0 = perf(s)
    if not p0:
        sys.exit("no PERF? answer on %s - old firmware, or not a module" % port)
    base = home_pose(s)
    if not base:
        sys.exit("no POSE? answer - is this a nong?")
    print("start: boots=%s reset=%s heap=%s up=%ss" % (
        p0["boots"], p0["reset"], p0["heap"], p0["up_s"]))
    bad, t0, rounds = [], time.time(), 0
    while True:
        bad += run_once(s, base, p0["boots"])
        rounds += 1
        if time.time() - t0 >= soak:
            break
    end = perf(s)
    print("\n%d round(s), %.0f s. heap %s -> %s (min %s)" % (
        rounds, time.time() - t0, p0["heap"], end.get("heap"), end.get("heap_min")))
    print("VERDICT: " + ("OK - kept up in every task" if not bad
                         else "PROBLEMS:\n  " + "\n  ".join(bad)))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
