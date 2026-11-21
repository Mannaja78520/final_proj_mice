"""Speed and reconnect of the PC services: hub 8642, voice 8767, faces 8769.

    python tools/bench/chaos_services.py --out <dir>

Starts voice and faces itself (the hub must already answer on 8642), then
1. times GET paths one client at a time and with 10/50/200 clients at once
   (p50/p95/p99/max in ms, error count);
2. kills each service with SIGKILL (3 times) and records how fast it is seen
   down, what the hub answers meanwhile, and whether/when it comes back;
3. runs the hub path while a service flaps, to see the hub itself stays fast.

User 2026-11-21: "test every speed and every reconnect". Raw numbers go to
<out>/services.json; nothing here touches a board or a friend's repo.
"""
import argparse
import json
import os
import signal
import statistics
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
HUB = "http://127.0.0.1:8642"
SERVICES = {
    "voice": {"port": 8767, "cmd": [sys.executable, str(ROOT / "apps/voice/service.py")],
              "direct": "/health", "via_hub": "/api/voice/health"},
    "faces": {"port": 8769, "cmd": [sys.executable, str(ROOT / "apps/faces/service.py")],
              "direct": "/health", "via_hub": "/api/faces/state"},
}
PAGES = ["/", "/studio/", "/app/voice/", "/app/faces/", "/help.html", "/api/version",
         "/api/modules", "/api/ports"]


def get(url, timeout=5):
    t = time.perf_counter()
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            r.read()
            code = r.status
    except urllib.error.HTTPError as e:
        code = e.code
    except Exception:
        code = 0
    return code, (time.perf_counter() - t) * 1000


def pct(xs, p):
    xs = sorted(xs)
    return round(xs[min(len(xs) - 1, int(len(xs) * p / 100))], 1)


def load(url, clients, per_client):
    lat, codes = [], {}
    lock = threading.Lock()

    def work():
        for _ in range(per_client):
            c, ms = get(url)
            with lock:
                lat.append(ms)
                codes[c] = codes.get(c, 0) + 1
    t0 = time.perf_counter()
    ths = [threading.Thread(target=work) for _ in range(clients)]
    [t.start() for t in ths]
    [t.join() for t in ths]
    wall = time.perf_counter() - t0
    return {"clients": clients, "n": len(lat), "p50": pct(lat, 50), "p95": pct(lat, 95),
            "p99": pct(lat, 99), "max": round(max(lat), 1), "codes": codes,
            "req_per_s": round(len(lat) / wall, 1)}


def kill_service(name):
    """SIGKILL whatever listens on the service's port (psutil: Windows and Linux), else pkill."""
    port = SERVICES[name]["port"]
    try:
        import psutil
        for c in psutil.net_connections(kind="tcp"):
            if c.status == psutil.CONN_LISTEN and c.laddr and c.laddr.port == port and c.pid:
                psutil.Process(c.pid).kill()
    except ImportError:
        subprocess.run(["pkill", "-9", "-f", SERVICES[name]["cmd"][1]])


def start(name):
    s = SERVICES[name]
    log = open(os.path.join(tempfile.gettempdir(), "chaos_%s.log" % name), "ab")
    return subprocess.Popen(s["cmd"], cwd=str(ROOT), stdout=log, stderr=log)


def wait_up(url, limit=60):
    t = time.perf_counter()
    while time.perf_counter() - t < limit:
        if get(url, 1)[0] == 200:
            return round(time.perf_counter() - t, 2)
        time.sleep(0.1)
    return None


def wait_down(url, limit=20):
    t = time.perf_counter()
    while time.perf_counter() - t < limit:
        c, _ = get(url, 1)
        if c != 200:
            return round(time.perf_counter() - t, 2), c
        time.sleep(0.05)
    return None, 200


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--pages-only", action="store_true")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    res = {"when": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "pages": {}, "services": {}}

    for p in PAGES:                        # 1. pages, one client and many
        res["pages"][p] = [load(HUB + p, c, max(5, 400 // c)) for c in (1, 10, 50, 200)]
        r = res["pages"][p][0]
        print("%-16s 1 client p50 %6.1f p95 %6.1f ms | 200 clients p95 %7.1f max %7.1f errs %s" % (
            p, r["p50"], r["p95"], res["pages"][p][3]["p95"], res["pages"][p][3]["max"],
            {k: v for k, v in res["pages"][p][3]["codes"].items() if k != 200}))

    if a.pages_only:
        (out / "pages_only.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
        return
    procs = {n: start(n) for n in SERVICES}          # 2. services
    for n, s in SERVICES.items():
        base = "http://127.0.0.1:%d" % s["port"]
        info = {"cold_start_s": wait_up(base + s["direct"], 90)}
        if info["cold_start_s"] is None:
            info["note"] = "never came up; see the temp folder chaos_%s.log" % n
            res["services"][n] = info
            continue
        info["direct"] = [load(base + s["direct"], c, max(5, 300 // c)) for c in (1, 10, 50)]
        info["via_hub"] = [load(HUB + s["via_hub"], c, max(5, 300 // c)) for c in (1, 10, 50)]
        info["kills"] = []
        for k in range(3):                           # kill -9 three times in a row
            # kill whoever answers on the port, not only the copy started here:
            # the hub starts its own voice helper on first use (voice_helper.py)
            kill_service(n)
            t_kill = time.perf_counter()
            down_s, _ = wait_down(base + s["direct"], 10)
            c, ms = get(HUB + s["via_hub"], 10)     # what the hub says while it is down
            revived = None                           # does the hub bring it back by itself?
            while time.perf_counter() - t_kill < 25:
                if get(base + s["direct"], 2)[0] == 200:
                    revived = round(time.perf_counter() - t_kill, 2)
                    break
                get(HUB + s["via_hub"], 3)           # a page asking is the trigger
                time.sleep(0.2)
            if revived is None:                      # nobody revived it: restart by hand
                procs[n] = start(n)
            up = wait_up(base + s["direct"], 90)
            info["kills"].append({"down_seen_s": down_s, "hub_code_when_down": c,
                                  "hub_answer_ms_when_down": round(ms, 1),
                                  "revived_by_itself_s": revived, "back_s_after_manual": up})
            print(n, "kill", k + 1, info["kills"][-1])
        res["services"][n] = info

    # 3. hub speed while a service flaps
    stop = threading.Event()

    def flap():
        while not stop.is_set():
            kill_service("voice")
            time.sleep(0.5)
            get(HUB + SERVICES["voice"]["via_hub"], 3)
            stop.wait(4)
    th = threading.Thread(target=flap)
    th.start()
    res["hub_while_voice_flaps"] = load(HUB + "/api/version", 20, 60)
    stop.set()
    th.join()
    print("hub while voice flaps:", res["hub_while_voice_flaps"])

    for n in SERVICES:
        kill_service(n)
    (out / "services.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print("raw ->", out / "services.json")


if __name__ == "__main__":
    main()
