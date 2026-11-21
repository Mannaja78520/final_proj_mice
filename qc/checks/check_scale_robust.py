"""A big rig stays listed in a readable order, and a crowd of clients is not refused.

Measured 2026-11-21 (user: "test every speed ... 30 to 255 boards"):
* 200 clients opening the hub at once: p95 about 2 s, max 7 s, some timeouts,
  because ThreadingHTTPServer listens with a queue of 5. With the queue at 256:
  p95 75-260 ms, no errors (raw numbers: tools/bench/chaos_services.py).
* the board list sorted names and ids as TEXT: id 100 before 20, "lift 10"
  before "lift 2", and no grouping by kind.
* a second saved WiFi (SET WIFI2/3) is tried when the first cannot be joined.
"""
import re

import qc as F

AREA = "hub"
TITLE = "255 boards list in natural order; servers keep a deep listen queue; backup WiFi exists"
SLOW = False


def run(t):
    import hub_modules
    boards = [{"name": n, "type": ty, "id": i} for n, ty, i in
              [("nong 10", "nong", 100), ("nong 2", "nong", 20), ("nong 2", "nong", 3),
               ("cam", "cam", 5), ("blank", "blank", 1), ("", "", 7)]]
    got = [(b["name"], b["id"]) for b in sorted(boards, key=hub_modules.board_order)]
    t.ok(got == [("cam", 5), ("nong 2", 3), ("nong 2", 20), ("nong 10", 100), ("", 7), ("blank", 1)],
         "numbers sort as numbers, unset boards last", str(got))
    big = [{"name": "nong %d" % (i % 40), "type": "nong", "id": i} for i in range(1, 256)]
    a = [b["id"] for b in sorted(big, key=hub_modules.board_order)]
    t.ok(a == [b["id"] for b in sorted(reversed(big), key=hub_modules.board_order)],
         "the order does not depend on arrival order", "")

    for rel in ("main_python/main.py", "apps/voice/service.py", "apps/faces/service.py"):
        src = (F.CODE / rel).read_text(encoding="utf-8", errors="replace")
        m = re.search(r"request_queue_size\s*=\s*(\d+)", src)
        t.ok(bool(m) and int(m.group(1)) >= 128, rel + " listens with a queue of 128 or more",
             m.group(0) if m else "default queue is 5")

    fw = F.FIRMWARE / "src/core"
    cmd = (fw / "CommandRouter.cpp").read_text(encoding="utf-8", errors="replace")
    web = (fw / "WebPortal.cpp").read_text(encoding="utf-8", errors="replace")
    t.ok('"WIFI2"' in cmd and "setWifiN" in cmd, "SET WIFI2/WIFI3 stores a backup network", "")
    # the join timeout (W_CONNECTING) hands over to the next saved network
    # before the diagnostic/hotspot fallback; and a spent list retries from slot 0
    t.ok(re.search(r"WIFI_CONNECT_TIMEOUT_MS\)\s*\{[^}]*wifilist::next\(netIdx_, have\)", web, re.S) is not None,
         "a failed join moves to the next saved network", "")
    t.ok("wifilist::first(have)" in web or "nx = wifilist::first" in web,
         "a spent list starts again from the main network", "")

    # PC measurements 2026-11-21 (Windows, real Ollama and friend app)
    faces = (F.CODE / "apps/faces/service.py").read_text(encoding="utf-8", errors="replace")
    m = re.search(r"wait = min\(([\d.]+), wait \* 2\)", faces)
    t.ok(bool(m) and float(m.group(1)) <= 10, "the live feed reconnects within 10 s of the friend app returning",
         m.group(0) if m else "no backoff found (was a 30 s cap: 19 s of pure waiting after a restart)")
    prov = (F.CODE / "config/voice_providers.json").read_text(encoding="utf-8", errors="replace")
    m = re.search(r'"ready": "http://127.0.0.1:11435/api/tags", "waitSeconds": (\d+)', prov)
    t.ok(bool(m) and int(m.group(1)) <= 20, "a question waits at most 20 s for Ollama before the backup answers",
         m.group(0) if m else "not found (was 40 s: the first visitor heard nothing for 45 s)")
