"""Finding things on the network — one sweep, however many kinds of thing.

The hub looks for two things on the same subnet: MODULES (boards answering
/api/status) and other HUBS (PCs running this program). Those were two copies
of one loop — same address range, same thread pool, same cache-with-a-shelf-
life, different only in what they ask and how long they trust the answer. Two
copies means a fix to one silently missing from the other, and that already
happened: the modules scan learned to be patient with boards that answer late,
and the hubs scan never did.

ADDING A THIRD KIND OF THING IS ONE LINE — a Finder, with what to ask:

    CAMERAS = Finder("cameras", probe_camera, ttl=30)
    CAMERAS.find()

Nothing else changes. There is no registry to update and no branch to add.

WHAT LIVES HERE, AND WHAT DOES NOT
This finds addresses and asks them a question. It does not know what a module
is, what a hub is, or what to do with either — those stay with the caller, as
the `probe` it hands in. Two shallow classes, no layers that exist only to be
layers.
"""
import threading
import time
from concurrent.futures import ThreadPoolExecutor


class Sweep:
    """Ask every address on one /24 the same question, at the same time.

    255 addresses, 96 at a time, is about three seconds on a normal network
    and most of that is waiting. The worker count is not a tuning knob anyone
    should need: it is high because the work is entirely waiting for a timeout,
    not because the PC is fast.
    """

    def __init__(self, workers=96):
        self.workers = workers

    def hosts(self, my_ip):
        """Every address on my /24, or nothing when there is no network.

        127.0.0.x means no usable interface: sweeping loopback finds only this
        PC pretending to be everyone, which is worse than finding nothing.
        """
        base = my_ip.rsplit(".", 1)[0]
        if base == "127.0.0":
            return []
        return ["%s.%d" % (base, i) for i in range(1, 255)]

    def run(self, probe, my_ip, skip_self=False):
        hosts = self.hosts(my_ip)
        if skip_self:
            hosts = [h for h in hosts if h != my_ip]
        if not hosts:
            return []
        with ThreadPoolExecutor(max_workers=self.workers) as ex:
            return [r for r in ex.map(probe, hosts) if r]


class Finder:
    """One kind of thing, found on the network and remembered briefly.

    `ttl` is how long an answer is trusted before sweeping again. It is short
    on purpose: a scan is cheap and a stale list is a person staring at a robot
    that the screen says is not there.

    `patient` is an optional second, slower probe used ONLY on addresses that
    have answered before. It exists because of a measured fault, not a theory:
    a module sharing its WiFi runs AP_STA on one radio and time-slices between
    the show network and its own access point, so it sometimes answers a touch
    late. On the bench the lift answered a 0.6 s probe 7 times in 8, and the
    hub lost it on 2 scans out of 3 while it sat there perfectly online. The
    second pass is a handful of addresses and costs nothing when they answer.

    That pass is deliberately NOT limited to the swept subnet: a module can be
    perfectly reachable on another one (routed networks do this), and a board
    identified over a cable reports its own address, so plugging one in is
    enough to find it on WiFi afterwards.

    `grace` is how long something that MISSED a sweep stays in the list, marked
    stale, before it is really forgotten. Zero keeps the old behaviour: one
    missed probe and it is gone. That was wrong for the place this runs - the
    user, 2026-08-19: the wifi it not stable sometime i lost connect some time
    other pc lost connect. On a link like that one dropped packet made a hub or
    a robot vanish from the screen while it sat there working, and nobody can
    tell that from a real failure. Keeping the row and SAYING it is late is
    honest; deleting it is not.
    """

    def __init__(self, name, probe, ttl, patient=None, skip_self=False,
                 key=None, sweep=None, grace=0):
        self.name = name
        self.probe = probe
        self.ttl = ttl
        self.grace = grace
        self._seen = {}                     # ip -> (record, when it answered)
        self.patient = patient
        self.skip_self = skip_self
        self.key = key                      # how to sort; None keeps found order
        self.sweep = sweep or Sweep()
        self._lock = threading.Lock()
        self._at = 0.0
        self._found = []

    @property
    def age(self):
        return time.time() - self._at if self._at else None

    def forget(self):
        """Throw away what is known, so the next find() really sweeps.

        Tests need this — a check about a module vanishing and coming back
        cannot wait out a shelf life — and so does anything that knows the
        network just changed underneath it. Better here than having callers
        reach into the internals, which is what the QC check used to do.
        """
        with self._lock:
            self._at, self._found = 0.0, []
            # The grace memory as well. Leaving it meant a "forgotten" finder
            # still remembered: the next sweep re-added everything from before
            # as STALE, and a check that had just cleared the list watched its
            # predecessor's modules reappear. It only showed once the suite ran
            # in a process pool, where one worker runs several checks in turn -
            # alone, every check had a fresh process and nothing to inherit.
            self._seen.clear()

    def cached(self):
        """What is known right now, without asking the network."""
        return list(self._found)

    def find(self, my_ip, force=False, also_ask=()):
        """Sweep if the last answer is stale, and return what is out there.

        `also_ask` are addresses the caller knows about from somewhere else —
        a cable, say — which the sweep may not reach.
        """
        # The lock is held across the whole sweep, three seconds of waiting on
        # the network, and that is deliberate — it is what the two hand-rolled
        # scans did too. It means one sweep at a time: a second caller waits
        # for the answer instead of starting a competing sweep of the same 254
        # addresses. Do not narrow it to just the cache read without deciding
        # what should happen when two pages ask at once.
        with self._lock:
            if not force and self._at and time.time() - self._at < self.ttl:
                # A copy, not the list itself: a caller that mutated what it
                # got back would be editing the cache everyone else reads.
                return list(self._found)

            found = self.sweep.run(self.probe, my_ip, self.skip_self)

            # Addresses the caller NAMED are always asked, whether or not
            # this finder has a patient second pass. They are not a guess: the
            # caller learned them from somewhere the sweep cannot see - a
            # cable, or a person who typed one because the other PC is on a
            # different subnet entirely. Asking only when `patient` was set
            # meant a hub could be added, remembered, listed as known, and
            # never once contacted.
            #
            # The patient probe is used when there is one, because that is the
            # slower, more forgiving ask; otherwise the ordinary probe does.
            ask = self.patient or self.probe
            seen = {r["ip"] for r in found if r.get("ip")}
            known = [r["ip"] for r in self._found if r.get("ip")] if self.patient else []
            known += [ip for ip in also_ask if ip]
            missing = [ip for ip in dict.fromkeys(known) if ip not in seen]
            if missing:
                with ThreadPoolExecutor(max_workers=8) as ex:
                    found += [r for r in ex.map(ask, missing) if r]

            now = time.time()
            for r in found:
                if r.get("ip"):
                    self._seen[r["ip"]] = (dict(r), now)

            # Anything that answered recently but not THIS time is late, not
            # gone. It comes back marked, so a screen can grey it out and say
            # when it was last heard from instead of silently dropping a row.
            if self.grace:
                here = {r.get("ip") for r in found}
                for ip, (rec, when) in list(self._seen.items()):
                    if ip in here:
                        continue
                    if now - when > self.grace:
                        del self._seen[ip]
                        continue
                    late = dict(rec)
                    late["stale"] = True
                    late["lastSeen"] = int(now - when)
                    found.append(late)

            if self.key:
                found.sort(key=self.key)
            self._at, self._found = now, found
            return list(found)
