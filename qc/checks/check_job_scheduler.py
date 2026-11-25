"""Shared scheduler: urgent work jumps the queue, nothing starves, nothing deadlocks.

2026-11-25: Voice had one plain lock for the whole GPU, so a live question
waited behind every queued translation (measured 1077 ms median in
tools/bench_sched.py, 150 ms with the scheduler, same total work time).
Asserts on the ORDER work really ran in, on the real Voice Brain wiring, and on
live config reload.
"""
import json
import sys
import tempfile
import threading
import time
from pathlib import Path

import qc as F

AREA = "tools"
TITLE = "the shared scheduler lets live work jump the queue without starving background work"

CFG = {"resources": {"gpu": {"slots": 1, "agingSeconds": 0.2, "yieldMargin": 2}},
       "classes": {"normal": {"priority": 5, "resource": "gpu"},
                   "live": {"priority": 0, "resource": "gpu"},
                   "background": {"priority": 9, "resource": "gpu"}}}


def run(t):
    sys.path.insert(0, str(F.CODE / "tools"))
    import jobsched
    s = jobsched.Scheduler(json.loads(json.dumps(CFG)))

    # 1. Priority order: hold the slot, queue background x3 then live; live must run first.
    order, ready = [], []
    holder = s.gate("normal")
    holder.__enter__()

    def job(klass, name):
        ready.append(name)
        with s.gate(klass):
            order.append(name)

    threads = []
    for name, klass in (("bg1", "background"), ("bg2", "background"), ("bg3", "background"), ("live", "live")):
        th = threading.Thread(target=job, args=(klass, name))
        th.start()
        threads.append(th)
        time.sleep(0.03)
    holder.__exit__(None, None, None)
    for th in threads:
        th.join(5)
    t.ok(order[0] == "live" and order[1:] == ["bg1", "bg2", "bg3"], "live jumps ahead; equals keep arrival order", str(order))

    # 2. Aging: with a stream of live work, an old background job still gets its turn.
    s2 = jobsched.Scheduler(json.loads(json.dumps(CFG)))
    done = []
    stop = threading.Event()

    def stream():
        while not stop.is_set():
            with s2.gate("live"):
                time.sleep(0.02)

    feeders = [threading.Thread(target=stream) for _ in range(3)]
    for f in feeders:
        f.start()
    time.sleep(0.05)
    bg = threading.Thread(target=lambda: (s2.gate("background").__enter__(), done.append(1)))
    bg.start()
    bg.join(6)
    stop.set()
    for f in feeders:
        f.join(2)
    t.ok(done == [1], "background work is delayed, never starved (aging)", "still waiting after 6 s of live traffic")

    # 3. Re-entrant: the same thread asking again (helper inside a slice) must not deadlock.
    box = []

    def nested():
        with s.gate("live"):
            with s.gate("background"):
                box.append("inner")

    th = threading.Thread(target=nested)
    th.start()
    th.join(3)
    t.ok(box == ["inner"] and not th.is_alive(), "a thread asking twice does not deadlock itself")

    # 4. Cooperative pre-emption at a checkpoint: a long job steps aside for a live one.
    s3 = jobsched.Scheduler(json.loads(json.dumps(CFG)))
    log = []

    def long_job():
        with s3.gate("background") as g:
            for i in range(6):
                log.append("bg%d" % i)
                time.sleep(0.05)
                g.checkpoint()

    lj = threading.Thread(target=long_job)
    lj.start()
    time.sleep(0.08)
    with s3.gate("live"):
        log.append("LIVE")
    lj.join(5)
    pos = log.index("LIVE")
    t.ok(0 < pos < 6, "a long job lets a live one in between slices", str(log))

    # 5. Config is data and reloads live; a bad file keeps the last good numbers.
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "scheduler.json"
        path.write_text(json.dumps(CFG), encoding="utf-8")
        s4 = jobsched.Scheduler.from_file(path)
        s4._checked = 0
        two = json.loads(json.dumps(CFG))
        two["resources"]["gpu"]["slots"] = 2
        path.write_text(json.dumps(two), encoding="utf-8")
        import os
        os.utime(path, (time.time() + 5, time.time() + 5))
        s4.gate("live")
        t.ok(s4.status()["resources"]["gpu"]["slots"] == 2, "editing the config changes slots with no restart")
        s4._checked = 0
        path.write_text("{ broken", encoding="utf-8")
        os.utime(path, (time.time() + 9, time.time() + 9))
        s4.gate("live")
        t.ok(s4.status()["resources"]["gpu"]["slots"] == 2, "a broken config file keeps the last good numbers")

    # 6. The shipped config is valid and Voice really routes its model use through it.
    ship = json.loads((F.CODE / "config" / "scheduler.json").read_text(encoding="utf-8"))
    try:
        jobsched.Scheduler.validate(ship)
        ok = True
    except ValueError:
        ok = False
    t.ok(ok and ship["classes"]["live"]["priority"] < ship["classes"]["translate"]["priority"],
         "shipped config is valid and live outranks translation")
    left = [str(p.name) for p in (F.CODE / "apps" / "voice").glob("*.py") if "self._lock" in p.read_text(encoding="utf-8")]
    t.ok(not left, "Voice has no plain GPU lock left that bypasses the scheduler", str(left))

    # 7. A single job reaches the gate from its own request thread, not through a
    # FIFO pool in front of it (that pool hid the queue from the priority gate:
    # PC measurement 2026-11-25, gate wait 0 ms while callers waited ~3 s).
    sys.path.insert(0, str(F.CODE / "apps" / "voice"))
    from resources import VoiceResources
    got = VoiceResources(F.CODE).map(lambda _x: threading.get_ident(), [1])
    t.ok(got == [threading.get_ident()], "one translation job runs on the caller's thread, ahead of any pool queue", str(got))
