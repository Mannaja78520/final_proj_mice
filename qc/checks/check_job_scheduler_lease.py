"""The hub's GPU lease: programs share one order, a dead holder cannot freeze the rest.

2026-11-25: Voice, the face app and hub tools are separate programs on one
GPU, so a per-program queue is not enough. Real hub, real HTTP, real client.
"""
import json
import sys
import threading
import time

import qc as F

AREA = "tools"
TITLE = "the hub hands out one GPU order across programs, fails open, and takes back dead leases"


def run(t):
    sys.path.insert(0, str(F.CODE / "tools"))
    import jobsched
    base, _main = F.start_hub()

    def post(path, obj):
        code, body = F.post(base + path, json.dumps(obj).encode())
        return code, (json.loads(body) if body else {})

    # 1. A place is handed out and refused to a second asker until released.
    c1, r1 = post("/api/scheduler/acquire", {"class": "live", "owner": "t1", "wait": 5})
    t.ok(c1 == 200 and r1.get("token"), "a program gets a place", str(r1))
    c2, r2 = post("/api/scheduler/acquire", {"class": "live", "owner": "t2", "wait": 0.4})
    t.ok(c2 == 408, "a second program waits, then is told the place is busy", "%s %s" % (c2, r2))

    # 2. Waiting order across programs: background asked first, live asked later, live goes first.
    order = []

    def ask(klass):
        c, r = post("/api/scheduler/acquire", {"class": klass, "owner": klass, "wait": 8})
        order.append(klass)
        post("/api/scheduler/release", {"token": r["token"]})

    th = []
    for k in ("background", "translate", "live"):
        x = threading.Thread(target=ask, args=(k,), daemon=True)
        x.start()
        th.append(x)
        time.sleep(0.3)
    post("/api/scheduler/release", {"token": r1["token"]})
    for x in th:
        x.join(10)
    t.ok(order[0] == "live", "live work from another program jumps ahead of background", str(order))

    # 3. A holder that never releases loses the place after its time limit.
    import hub_api_scheduler
    tbl = hub_api_scheduler.table()
    old = tbl.ttl
    tbl.ttl = 0.5
    try:
        c, r = post("/api/scheduler/acquire", {"class": "live", "owner": "crashed", "wait": 2})
        time.sleep(0.8)
        c3, r3 = post("/api/scheduler/acquire", {"class": "live", "owner": "next", "wait": 2})
        t.ok(c3 == 200, "a lease nobody released is taken back", str(r3))
        post("/api/scheduler/release", {"token": r3.get("token", "")})
    finally:
        tbl.ttl = old

    # 4. The program-side client: works against the hub, fails open with no hub.
    client = jobsched.LeaseClient(base, wait=3)
    tok = client.acquire("live")
    t.ok(bool(tok), "the client takes a place from the real hub")
    client.release(tok)
    # A BUSY hub (408) is not a dead hub: the next job still asks (review 2026-11-26:
    # one busy answer switched the cross-program order off for 30 s).
    holder = client.acquire("live")
    busy = jobsched.LeaseClient(base, wait=0.3, down_seconds=30)
    first = busy.acquire("background")
    client.release(holder)
    again = busy.acquire("background")
    t.ok(holder and first is None and bool(again), "a busy hub is asked again next time, not skipped for 30 s",
         "first=%r again=%r" % (first, again))
    busy.release(again)
    import hub_api_scheduler
    t.ok(isinstance(hub_api_scheduler.gate("background"), jobsched.Gate),
         "the hub's own GPU work does not ask itself for a lease over HTTP")
    dead = jobsched.LeaseClient("http://127.0.0.1:9", wait=3, down_seconds=30)
    t0 = time.monotonic()
    t.ok(dead.acquire("live") is None and dead.acquire("live") is None and time.monotonic() - t0 < 3,
         "with no hub the client goes on without waiting, and does not retry for a while")

    # 5. Status is readable and a LAN caller may not take places (loopback only is enforced by address).
    code, body = F.get(base + "/api/scheduler")[:2]
    t.ok(code == 200 and "leases" in json.loads(body), "status shows places held and per-class waits")
