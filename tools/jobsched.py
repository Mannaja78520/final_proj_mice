"""One shared job scheduler: priority queues in front of the machine's scarce
resources (the GPU, the CPU pool), the way an OS or a GPU driver does it.

Asked 2026-11-25: "work like a CPU/GPU - cut into small pieces, queue them,
let urgent ones jump the queue, don't wait on one bottleneck". Before this,
Voice had ONE plain lock for the whole GPU: a long translation or helper job
made a live question wait its full turn, and a queued job could never be
overtaken. Now every heavy piece of work says what KIND it is (a "class") and
asks the gate of the resource that class uses:

    with sched.gate("live"):          # waits its turn, urgent classes first
        run_the_model()

Everything that can differ is DATA in config/scheduler.json (resources and
their slots, classes with priority and aging); a new kind of work is a new
entry, not a code change. The file is re-read when it changes, no restart.

How it behaves (all measured by tools/bench_sched.py):
* Priority: lower number first. FIFO among equals.
* Aging: each `agingSeconds` waited lowers a waiting job's number by 1, so
  background work is delayed, never starved.
* No kill: a running piece is never interrupted from outside (that would
  corrupt a model). Long work is cut into slices; a slice calls
  `gate.checkpoint()` (or uses `sched.each`) and steps aside when something
  more urgent is waiting, then comes back through the queue = pre-emption at
  slice boundaries.
* Re-entrant per thread, so a slice that calls a helper which also asks for the
  same resource cannot deadlock itself.
* Stats per class (waits, runs, p50/p95) for the Help/Status pages and charts.
"""
import collections
import json
import threading
import time
from pathlib import Path

DEFAULT_CLASS = "normal"


class Gate:
    """One held (or waiting) place in a resource. Use as a context manager."""

    def __init__(self, resource, klass, priority, reentrant=True, timeout=None):
        self.resource, self.klass, self.priority = resource, klass, priority
        self.reentrant, self.timeout = reentrant, timeout       # reentrant=False: may be released from another thread (leases)
        self.queued_at = time.monotonic()
        self.seq = 0
        self._depth = 0

    def __enter__(self):
        self.resource.acquire(self)
        return self

    def __exit__(self, *exc):
        self.resource.release(self)
        return False

    def should_yield(self):
        """True when something clearly more urgent is waiting for this resource."""
        return self.resource.more_urgent_waiting(self)

    def checkpoint(self):
        """Call between slices: step aside (go to the back of the queue) only if
        something more urgent is waiting. Cheap when nobody is."""
        if self.should_yield():
            self.resource.release(self)
            self.queued_at = time.monotonic()
            self.resource.acquire(self)
            return True
        return False


class _Resource:
    def __init__(self, name, slots, aging, margin):
        self.name, self.slots, self.aging, self.margin = name, slots, aging, margin
        self.cond = threading.Condition()
        self.waiting, self.holders = [], []
        self.local = threading.local()
        self.seq = 0
        self.stats = {}

    def _eff(self, g, now):
        # Aging: waiting makes a job look more urgent, so low classes never starve.
        return g.priority - ((now - g.queued_at) / self.aging if self.aging else 0)

    def _depths(self):
        d = getattr(self.local, "held", None)
        if d is None:
            d = self.local.held = {}
        return d

    def acquire(self, g):
        held = self._depths() if g.reentrant else {}
        if held:                                   # this thread already holds a slot here
            holder = next(iter(held))
            held[holder] = held[holder] + 1
            g._reentrant = holder
            return
        g._reentrant = None
        with self.cond:
            self.seq += 1
            g.seq = self.seq
            self.waiting.append(g)
            deadline = None if g.timeout is None else g.queued_at + g.timeout
            try:
                while not self._my_turn(g):
                    left = None if deadline is None else deadline - time.monotonic()
                    if left is not None and left <= 0:
                        raise TimeoutError("no free place in %s for %s" % (self.name, g.klass))
                    wait = 0.5 if self.aging else None          # aging changes the order with time
                    self.cond.wait(wait if left is None else min(wait or left, left))
            except BaseException:
                self.waiting.remove(g)
                self.cond.notify_all()
                raise
            self.waiting.remove(g)
            self.holders.append(g)
            g.started_at = time.monotonic()
            self._note(g, "wait", g.started_at - g.queued_at)
        if g.reentrant:
            held[g] = 1

    def _my_turn(self, g):
        if len(self.holders) >= self.slots:
            return False
        now = time.monotonic()
        mine = (self._eff(g, now), g.seq)
        return all(mine <= (self._eff(o, now), o.seq) for o in self.waiting)

    def release(self, g):
        held = self._depths() if g.reentrant else {}
        holder = getattr(g, "_reentrant", None)
        if holder is not None:
            held[holder] -= 1
            g._reentrant = None
            return
        held.pop(g, None)
        with self.cond:
            self.holders.remove(g)
            self._note(g, "run", time.monotonic() - g.started_at)
            self.cond.notify_all()

    def more_urgent_waiting(self, g):
        with self.cond:
            return any(o.priority + self.margin <= g.priority for o in self.waiting)

    def _note(self, g, what, seconds):
        s = self.stats.setdefault(g.klass, {"wait": collections.deque(maxlen=500), "run": collections.deque(maxlen=500),
                                            "jobs": 0})
        s[what].append(seconds)
        if what == "run":
            s["jobs"] += 1


def _pct(values, p):
    if not values:
        return 0.0
    v = sorted(values)
    return v[min(len(v) - 1, int(round(p / 100 * (len(v) - 1))))]


class Scheduler:
    def __init__(self, config):
        self._lock = threading.Lock()
        self.path, self._mtime, self._checked = None, None, 0.0
        self._apply(config)

    @classmethod
    def from_file(cls, path):
        path = Path(path)
        try:
            cfg = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            cfg = {"resources": {"gpu": {"slots": 1}}, "classes": {DEFAULT_CLASS: {"priority": 5, "resource": "gpu"}}}
        s = cls(cfg)
        s.path, s._mtime = path, path.stat().st_mtime if path.is_file() else None
        return s

    def _apply(self, cfg):
        cfg = self.validate(cfg)
        old = getattr(self, "_resources", {})
        res = {}
        for name, r in cfg["resources"].items():
            cur = old.get(name)
            if cur is None:
                cur = _Resource(name, r["slots"], r.get("agingSeconds", 20), r.get("yieldMargin", 2))
            else:                                   # live change: keep queues and stats, new numbers
                with cur.cond:
                    cur.slots, cur.aging, cur.margin = r["slots"], r.get("agingSeconds", 20), r.get("yieldMargin", 2)
                    cur.cond.notify_all()
            res[name] = cur
        self.config, self._resources = cfg, res

    @staticmethod
    def validate(cfg):
        if not isinstance(cfg, dict) or not isinstance(cfg.get("resources"), dict) or not isinstance(cfg.get("classes"), dict):
            raise ValueError("scheduler config needs resources and classes")
        for name, r in cfg["resources"].items():
            if type(r.get("slots")) is not int or not 1 <= r["slots"] <= 64:
                raise ValueError("resource %s: slots must be 1..64" % name)
        for name, c in cfg["classes"].items():
            if c.get("resource") not in cfg["resources"] or type(c.get("priority")) is not int:
                raise ValueError("class %s: needs a known resource and an integer priority" % name)
        if DEFAULT_CLASS not in cfg["classes"]:
            raise ValueError("class '%s' is the fallback and must exist" % DEFAULT_CLASS)
        return cfg

    def _maybe_reload(self):
        now = time.monotonic()
        if not self.path or now - self._checked < 2:
            return
        self._checked = now
        try:
            m = self.path.stat().st_mtime
            if m != self._mtime:
                self._apply(json.loads(self.path.read_text(encoding="utf-8")))
                self._mtime = m
        except (OSError, ValueError):
            pass                                    # a half-saved or bad file keeps the last good numbers

    def gate(self, klass=DEFAULT_CLASS, reentrant=True, timeout=None):
        """Ask for a place for this kind of work: `with sched.gate("live"):`.
        With a lease configured, a class that names a shared resource also takes
        a place in the hub's order across programs (fails open: no hub = no wait)."""
        self._maybe_reload()
        cls = self.config["classes"].get(klass) or self.config["classes"][DEFAULT_CLASS]
        gate = Gate(self._resources[cls["resource"]], klass, cls["priority"], reentrant, timeout)
        lease = self.config.get("lease")
        if lease and lease.get("enabled") and cls["resource"] in lease.get("resources", ()) and reentrant:
            return _Both(gate, self._lease_client(lease), klass)
        return gate

    def _lease_client(self, lease):
        client = self.__dict__.get("_lease")
        if client is None or client.url != lease["hubUrl"]:
            client = self._lease = LeaseClient(lease["hubUrl"], lease.get("waitSeconds", 20), lease.get("downSeconds", 30))
        return client

    def each(self, klass, items):
        """Time-slice: yield items one by one, each inside its own gate, so urgent
        work can run between two items of a long job."""
        for item in items:
            with self.gate(klass):
                yield item

    def status(self):
        out = {"resources": {}, "classes": {}}
        for name, r in self._resources.items():
            with r.cond:
                out["resources"][name] = {"slots": r.slots, "running": [g.klass for g in r.holders],
                                          "waiting": [g.klass for g in r.waiting]}
                for k, s in r.stats.items():
                    out["classes"][k] = {"resource": name, "jobs": s["jobs"],
                                         "waitMs": {"p50": round(_pct(s["wait"], 50) * 1000), "p95": round(_pct(s["wait"], 95) * 1000),
                                                    "max": round(max(s["wait"], default=0) * 1000)},
                                         "runMs": {"p50": round(_pct(s["run"], 50) * 1000), "p95": round(_pct(s["run"], 95) * 1000)}}
        return out


class _Both:
    """This program's own order first, then the hub's order across programs."""

    def __init__(self, gate, client, klass):
        self.gate, self.client, self.klass, self.token = gate, client, klass, None

    def __enter__(self):
        self.gate.__enter__()
        try:
            self.token = self.client.acquire(self.klass)
        except BaseException:
            self.gate.__exit__(None, None, None)
            raise
        return self

    def __exit__(self, *exc):
        try:
            if self.token:
                self.client.release(self.token)
        finally:
            self.gate.__exit__(None, None, None)
        return False

    def checkpoint(self):
        return self.gate.checkpoint()

    def should_yield(self):
        return self.gate.should_yield()


class LeaseTable:
    """Hub side: one scheduler for the machine's shared GPU, leases handed out
    by token. A lease that is not released within `ttl` seconds is taken back, so
    a program that crashed while holding the GPU cannot freeze the others."""

    def __init__(self, scheduler, resource="gpu", ttl=60):
        self.sched, self.resource, self.ttl = scheduler, resource, ttl
        self._lock = threading.Lock()
        self._leases = {}
        self._n = 0

    def acquire(self, klass, owner="", wait=20):
        self._reap()
        cls = self.sched.config["classes"].get(klass) or self.sched.config["classes"][DEFAULT_CLASS]
        if cls["resource"] != self.resource:
            raise ValueError("class %s does not use %s" % (klass, self.resource))
        gate = Gate(self.sched._resources[self.resource], klass, cls["priority"], reentrant=False, timeout=wait)
        gate.__enter__()                              # TimeoutError when the wait runs out
        with self._lock:
            self._n += 1
            token = "L%d" % self._n
            self._leases[token] = (gate, time.monotonic() + self.ttl, owner, klass)
        return token

    def release(self, token):
        with self._lock:
            item = self._leases.pop(token, None)
        if item:
            item[0].__exit__(None, None, None)
        return bool(item)

    def _reap(self):
        now = time.monotonic()
        with self._lock:
            late = [t for t, v in self._leases.items() if v[1] < now]
        for t in late:
            self.release(t)

    def status(self):
        self._reap()
        with self._lock:
            held = [{"class": v[3], "owner": v[2], "leftS": round(v[1] - time.monotonic())} for v in self._leases.values()]
        return {**self.sched.status(), "leases": held}


class LeaseClient:
    """Program side: ask the hub for the shared GPU. Anything wrong (no hub, slow
    hub, refused) means go on WITHOUT a lease and remember not to ask again for a
    while: a program must never freeze because the hub is not there."""

    def __init__(self, url, wait=20, down_seconds=30):
        self.url, self.wait, self.down_seconds, self._down_until = url.rstrip("/"), wait, down_seconds, 0.0

    def _post(self, path, body, timeout):
        import urllib.request
        req = urllib.request.Request(self.url + path, data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())

    def acquire(self, klass):
        if time.monotonic() < self._down_until:
            return None
        try:
            r = self._post("/api/scheduler/acquire", {"class": klass, "owner": "pid%d" % __import__("os").getpid(),
                                                        "wait": self.wait}, self.wait + 3)
            return r.get("token") if r.get("ok") else None
        except Exception:                          # noqa: BLE001 - every failure means: go on without a lease
            self._down_until = time.monotonic() + self.down_seconds
            return None

    def release(self, token):
        try:
            self._post("/api/scheduler/release", {"token": token}, 3)
        except Exception:                          # noqa: BLE001 - the hub's ttl takes it back
            pass
