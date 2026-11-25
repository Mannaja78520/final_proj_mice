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
        th = threading.Thread(target=job, args=(klass, name), daemon=True)
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

    feeders = [threading.Thread(target=stream, daemon=True) for _ in range(3)]
    for f in feeders:
        f.start()
    time.sleep(0.05)
    def background_turn():
        with s2.gate("background"):             # let go again: a slot kept forever starves the feeders
            done.append(1)

    bg = threading.Thread(target=background_turn, daemon=True)
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

    th = threading.Thread(target=nested, daemon=True)
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

    lj = threading.Thread(target=long_job, daemon=True)
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

    # 8. Requests share the character lock; a switch/settings write is alone.
    from profiles import SharedLock, guarded
    lock = SharedLock()
    inside, peak, lk = [0], [0], threading.Lock()

    def reader():
        with lock.shared():
            with lk:
                inside[0] += 1
                peak[0] = max(peak[0], inside[0])
            time.sleep(0.15)
            with lk:
                inside[0] -= 1

    rs = [threading.Thread(target=reader, daemon=True) for _ in range(4)]
    for r in rs:
        r.start()
    for r in rs:
        r.join(5)
    t.ok(peak[0] == 4, "four requests are inside the character lock at once", str(peak[0]))

    ev = []

    def slow_reader():
        with lock.shared():
            ev.append("r-in")
            time.sleep(0.3)
            ev.append("r-out")

    def writer():
        with lock.exclusive():
            ev.append("w-in")
            time.sleep(0.05)
            ev.append("w-out")

    def late_reader():
        with lock.shared():
            ev.append("late-in")

    a = threading.Thread(target=slow_reader, daemon=True)
    a.start()
    time.sleep(0.05)
    w = threading.Thread(target=writer, daemon=True)
    w.start()
    time.sleep(0.05)
    b = threading.Thread(target=late_reader, daemon=True)
    b.start()
    for x in (a, w, b):
        x.join(5)
    t.ok(ev == ["r-in", "r-out", "w-in", "w-out", "late-in"],
         "a switch waits for running requests, runs alone, and is not starved by later ones", str(ev))

    class H:
        command, path = "POST", "/profiles?x=1"
        brain = type("B", (), {"profile_lock": lock, "profiles": None})()

    seen = []
    guarded(lambda h: seen.append(lock._writer == threading.get_ident()))(H())
    H.command, H.path = "GET", "/ask?q=hi"
    guarded(lambda h: seen.append(lock._writer is None and lock._readers == 1))(H())
    t.ok(seen == [True, True], "a profile switch takes the lock alone; a question shares it", str(seen))

    # 8. A CPU-only PyTorch beside a GPU is said out loud in the Voice status.
    import types
    sys.path.insert(0, str(F.CODE / "apps" / "faces"))
    sys.path.insert(0, str(F.CODE / "apps" / "voice"))
    import local_llm

    def device_of(cuda_build, gpu):
        had = sys.modules.get("torch")
        sys.modules["torch"] = types.SimpleNamespace(__version__="9.9.9", version=types.SimpleNamespace(cuda=cuda_build))
        try:
            fake = types.SimpleNamespace(_resources=types.SimpleNamespace(
                status=lambda: {"loaded": {"stt:small": {"hardwareGpuCount": 1 if gpu else 0}}}),
                _llm_where=("cpu", "no usable GPU in the plan"))
            return local_llm.LocalLlm.llm_device(fake)
        finally:
            if had is None:
                sys.modules.pop("torch", None)
            else:
                sys.modules["torch"] = had

    t.ok("requirements.txt" in device_of(None, True).get("warning", ""),
         "a CPU-only torch with a GPU present says so in the Voice status")
    t.ok("warning" not in device_of("12.8", True) and "warning" not in device_of(None, False),
         "no warning when torch has CUDA, or when there is no GPU")

    # 9. Review 2026-11-26: the hub lease must follow the local gate exactly.
    # A nested gate asked the hub for a SECOND lease while its own outer gate
    # held the only one (20 s wait on itself), and a checkpoint stepped aside
    # locally but kept the lease, so the live job that took its place waited
    # 20 s for it. A fake hub records what was held at each ask.
    class FakeHub:
        url = "fake"

        def __init__(self):
            self.held, self.asks = set(), []

        def acquire(self, klass):
            self.asks.append((klass, len(self.held)))
            tok = "T%d" % len(self.asks)
            self.held.add(tok)
            return tok

        def release(self, tok):
            self.held.discard(tok)

    lcfg = json.loads(json.dumps(CFG))
    lcfg["lease"] = {"enabled": True, "hubUrl": "fake", "resources": ["gpu"]}
    s5 = jobsched.Scheduler(lcfg)
    hub = s5._lease = FakeHub()
    with s5.gate("live"):
        with s5.gate("background"):
            pass
    t.ok(hub.asks == [("live", 0)] and not hub.held, "a nested gate does not ask the hub for a second lease",
         str(hub.asks))

    hub.asks.clear()
    started, go_on = threading.Event(), threading.Event()

    def long_job():
        with s5.gate("background") as g:
            started.set()
            go_on.wait(3)
            g.checkpoint()

    lj = threading.Thread(target=long_job, daemon=True)
    lj.start()
    started.wait(3)
    lv = threading.Thread(target=lambda: s5.gate("live").__enter__().__exit__(), daemon=True)
    lv.start()
    time.sleep(0.2)
    go_on.set()
    lj.join(3)
    lv.join(3)
    t.ok(("live", 0) in hub.asks, "a job stepping aside at a checkpoint gives the hub lease back first",
         "lease asks (class, leases held at that moment): %s" % hub.asks)
    t.ok(not hub.held and not lj.is_alive() and not lv.is_alive(), "every lease is returned at the end", str(hub.held))

    src = (F.CODE / "apps" / "voice" / "service.py").read_text(encoding="utf-8")
    body = src[src.find("def watch_faq_audio"):]
    t.ok("brain.profile_lock.shared()" in body[:1500],
         "the 5-second answers watcher shares the character lock instead of blocking every new question",
         "an exclusive poll waits for the slowest running request and holds new ones meanwhile")
