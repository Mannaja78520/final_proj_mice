"""Which way to a board is fastest right now: USB cable, RS485 or WiFi.

Asked 2026-09-21: *when we connect rs485 and usb and wifi so use the less
letency as possible*. Measured that day on nong 67: a small command took
~59 ms over the PC hotspot, while a 1.2 KB status reply took longer over
RS485 (87 us a byte) than over WiFi - so no fixed order is right, and the
answer has to be measured.

How (Codex review 2026-09-21 shaped every rule here):
  * real traffic times itself - record() is called by the hub's own command
    paths for SMALL replies only, so a big status reply is not scored as a
    slow link;
  * a probe fills the gaps (main.py route_probe_loop), gently: only ports
    that are already open, never marked as client use;
  * a failure drops the route at once; a better route has to win by a margin
    with several samples behind it before the choice moves, so WiFi jitter
    cannot flap it;
  * samples are tied to the board seen on that route, so a COM port or an IP
    reused by another board does not inherit an old score.
Tunables live in config/route_latency.json.
"""
import json
import threading
import time

DEFAULTS = {"probeEverySec": 10, "sampleTtlSec": 30, "smallReplyBytes": 200,
            "smoothing": 0.3, "switchMarginMs": 5, "switchMarginPct": 20,
            "switchAfterSamples": 3}


class Latency:
    def __init__(self, cfg_path=None):
        self.cfg = dict(DEFAULTS)
        if cfg_path:
            try:
                with open(cfg_path, encoding="utf-8") as f:
                    got = json.load(f)
                self.cfg.update({k: v for k, v in got.items() if k in DEFAULTS})
            except (OSError, ValueError):
                pass                    # defaults are a working setting
        self._lock = threading.Lock()
        self._ms = {}        # dev -> (smoothed ms, time of last sample)
        self._owner = {}     # dev -> board key last seen on it
        self._chosen = {}    # board key -> dev

    # ---- samples ---------------------------------------------------------
    def record(self, dev, ms, reply_len=0):
        if not dev or reply_len > self.cfg["smallReplyBytes"]:
            return
        a = self.cfg["smoothing"]
        with self._lock:
            old = self._ms.get(dev)
            v = ms if old is None else old[0] * (1 - a) + ms * a
            n = 1 if old is None else old[2] + 1
            self._ms[dev] = (v, time.time(), n)

    def samples(self, dev):
        with self._lock:
            got = self._ms.get(dev)
        return got[2] if got else 0

    def fail(self, dev):
        """A route that just failed is out until it answers again."""
        with self._lock:
            self._ms.pop(dev, None)
            for key, d in list(self._chosen.items()):
                if d == dev:
                    del self._chosen[key]       # no hysteresis after a failure

    def ms(self, dev):
        with self._lock:
            got = self._ms.get(dev)
        if not got or time.time() - got[1] > self.cfg["sampleTtlSec"]:
            return None
        return got[0]

    def age(self, dev):
        """Seconds since this route was last timed, or None if never."""
        with self._lock:
            got = self._ms.get(dev)
        return None if not got else time.time() - got[1]

    def bind(self, dev, key):
        """The board seen on `dev`. A different board there starts from zero."""
        with self._lock:
            if self._owner.get(dev) not in (None, key):
                self._ms.pop(dev, None)
            self._owner[dev] = key

    # ---- choice ----------------------------------------------------------
    def choose(self, key, devs):
        """The route to use for board `key` among live `devs` (in fallback order).

        Unmeasured routes keep the old order; a measured faster route has to
        beat the current one by the margin, with switchAfterSamples behind it.
        """
        if not devs:
            return None
        c = self.cfg
        with self._lock:
            cur = self._chosen.get(key)
        if cur not in devs:
            cur = None
        measured = [(self.ms(d), d) for d in devs if self.ms(d) is not None]
        if not measured:
            pick = cur or devs[0]
        else:
            best_ms, best = min(measured)
            cur_ms = self.ms(cur) if cur else None
            if cur is None or cur_ms is None:
                pick = best
            elif best == cur:
                pick = cur
            else:
                # Hysteresis is the MARGIN (both ways) plus enough SAMPLES
                # behind the smoothed value. Not a count of calls: the hub asks
                # on every command, and 3 calls in 30 ms prove nothing - an
                # earlier per-call streak never switched at all on nong 67.
                ahead = (cur_ms - best_ms >= c["switchMarginMs"] and
                         best_ms <= cur_ms * (1 - c["switchMarginPct"] / 100.0))
                pick = best if (ahead and self.samples(best) >= c["switchAfterSamples"]) else cur
        with self._lock:
            self._chosen[key] = pick
        return pick

