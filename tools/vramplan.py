"""Dynamic GPU-memory planner: place models by live free VRAM and priority.

Asked 2026-11-25: "if the PC has 2, 4, 6, 8, 10 or 12 GB, don't fix it by GB,
make it dynamic; no app should get slower than it must". So there are NO
size tiers anywhere. When a model is about to load, the planner:

  1. measures the free VRAM right now (everything on the card counts: the
     face app, Ollama, other programs), plus what our own loaded models hold;
  2. keeps a headroom that scales with the card (config/vram_models.json);
  3. packs models onto the GPU most-important first (live hearing, then the
     local AI, then speech), a model that does not fit goes to the CPU
     (quality unchanged, only slower) or is unloaded if it cannot run there;
  4. a newcomer only pushes out a model that is LESS important, never an equal
     one (no thrashing); the pushed-out one reloads lazily and then finds the
     CPU, or whatever room has appeared since.

Sizes: a first guess from the registry, then the real size measured after the
first load and remembered, so the guess improves by itself on every machine.

`MICE_VRAM_CAP_MIB` pretends the card is that small (for testing 2/4/6/8/10 GB
on a bigger card): total is capped and free = cap - what is really in use.
Pure Python, no GPU library: the caller supplies the probe.
"""
import json
import os
import re
import threading
from pathlib import Path


BACKGROUND_FROM = 5          # priorities at or above this are background work (config/vram_models.json)


class Registry:
    def __init__(self, data, learned_path=None):
        self.headroom = data.get("headroom", {"fraction": 0.05, "minMiB": 256})
        self.rules = [(re.compile(r["match"]), r) for r in data["rules"]]
        self.learned_path = Path(learned_path) if learned_path else None
        self.learned = {}
        if self.learned_path and self.learned_path.is_file():
            try:
                self.learned = json.loads(self.learned_path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                self.learned = {}

    @classmethod
    def from_file(cls, path, learned_path=None):
        return cls(json.loads(Path(path).read_text(encoding="utf-8")), learned_path)

    def info(self, key):
        for rx, rule in self.rules:
            if rx.search(key.lower()):
                size = self.learned.get(key, rule["mib"])
                return {"mib": int(size), "priority": rule["priority"],
                        "cpuSlowdown": rule.get("cpuSlowdown", 2), "savedMs": rule.get("savedMs", 200), "canCpu": rule.get("canCpu", True),
                        "measured": key in self.learned}
        raise ValueError("no rule for " + key)

    def learn(self, key, mib):
        if mib and mib > 0:
            self.learned[key] = int(mib)
            if self.learned_path:
                try:
                    self.learned_path.parent.mkdir(parents=True, exist_ok=True)
                    self.learned_path.write_text(json.dumps(self.learned, indent=1), encoding="utf-8")
                except OSError:
                    pass

    def headroom_mib(self, total_mib):
        return max(int(self.headroom["minMiB"]), int(total_mib * self.headroom["fraction"]))


def capped(probe_result, cap_mib):
    """What a smaller card would show: total capped, free = cap - really used."""
    if not probe_result or not cap_mib:
        return probe_result
    total, free = probe_result["totalMiB"], probe_result["freeMiB"]
    used = total - free
    cap = min(total, cap_mib)
    return {**probe_result, "totalMiB": cap, "freeMiB": max(0, cap - used)}


def pack(capacity_mib, demands):
    """demands: [{key, mib, priority, cpuSlowdown, canCpu, resident}] -> {key: 'cuda'|'cpu'|'unload'}.
    Live models (priority < BACKGROUND_FROM) before background ones; inside a band the model that
    saves the most time per MiB goes first (measured 2026-11-25 in tools/bench_vram.py: putting the
    big hearing model on a small card first made every visitor slower than pinning the speech
    model that saves 5.8 s in 3 GB); equal gains keep the model already resident. A model that does not fit never blocks
    a smaller, less important one from using the room that is left."""
    order = sorted(demands, key=lambda d: (d["priority"] >= BACKGROUND_FROM, -d.get("savedMs", d["cpuSlowdown"] * 100) / max(1, d["mib"]),
                                           not d["resident"], d["priority"]))
    left, out = capacity_mib, {}
    for d in order:
        if d["mib"] <= left:
            out[d["key"]] = "cuda"
            left -= d["mib"]
        else:
            out[d["key"]] = "cpu" if d["canCpu"] else "unload"
    return out


class Arbiter:
    """The live bookkeeping: which models we hold on the GPU, and the decision for a new one."""

    def __init__(self, registry, probe, cap_mib=None):
        self.reg, self._probe = registry, probe
        self.cap_mib = cap_mib if cap_mib is not None else int(os.environ.get("MICE_VRAM_CAP_MIB") or 0) or None
        self._lock = threading.RLock()
        self._held = {}                              # key -> {"mib", "unload", "device"}
        self.last = {}

    def card(self):
        try:
            return capped(self._probe(), self.cap_mib)
        except Exception:                            # noqa: BLE001 - no probe = no GPU knowledge = CPU
            return None

    def request(self, key, unload=None):
        """Decide where `key` loads NOW. Returns {device, evict:[keys], why, card}. Evicted models'
        unload callbacks are called here, before the caller loads."""
        with self._lock:
            info = self.reg.info(key)
            card = self.card()
            if not card:
                return {"device": "cpu" if info["canCpu"] else "unload", "evict": [], "why": "no GPU reading", "card": None}
            mine_on_gpu = {k: v for k, v in self._held.items() if v["device"] == "cuda" and k != key}
            capacity = card["freeMiB"] + sum(v["mib"] for v in mine_on_gpu.values()) - self.reg.headroom_mib(card["totalMiB"])
            demands = [{"key": key, "resident": False, **{x: info[x] for x in ("mib", "priority", "cpuSlowdown", "savedMs", "canCpu")}}]
            for k, v in mine_on_gpu.items():
                i = self.reg.info(k)
                demands.append({"key": k, "resident": True, "mib": v["mib"], "priority": i["priority"],
                                "cpuSlowdown": i["cpuSlowdown"], "savedMs": i["savedMs"], "canCpu": i["canCpu"]})
            # Models at least as important as the newcomer are never moved for it (no thrashing);
            # the rest compete with it for what is left, and the losers are pushed out.
            immovable = sum(d["mib"] for d in demands[1:] if d["priority"] <= info["priority"])
            movable = [demands[0]] + [d for d in demands[1:] if d["priority"] > info["priority"]]
            plan = pack(capacity - immovable, movable)
            evict = [d["key"] for d in movable[1:] if plan[d["key"]] != "cuda"]
            if plan[key] != "cuda":
                evict = []                           # losing is not a reason to push anyone else out
            for k in evict:
                held = self._held.pop(k, None)
                if held and held.get("unload"):
                    try:
                        held["unload"]()
                    except Exception:                # noqa: BLE001 - a failing unload must not block the load
                        pass
            device = plan[key]
            self.last = {"key": key, "device": device, "evict": evict, "capacityMiB": capacity, "needMiB": info["mib"],
                         "freeMiB": card["freeMiB"], "totalMiB": card["totalMiB"]}
            why = ("fits in %d MiB of room" % capacity if device == "cuda" else
                   "only %d MiB of room for %d MiB: runs on the CPU, same quality" % (max(0, capacity), info["mib"]))
            return {"device": device, "evict": evict, "why": why, "card": card}

    def loaded(self, key, device, unload=None, before_free_mib=None):
        """Tell us a load finished. Measures its real size when given the free VRAM from before."""
        with self._lock:
            info = self.reg.info(key)
            mib = info["mib"]
            if device == "cuda" and before_free_mib is not None:
                card = self.card()
                if card and before_free_mib - card["freeMiB"] > 64:
                    mib = before_free_mib - card["freeMiB"]
                    self.reg.learn(key, mib)
            self._held[key] = {"mib": mib, "unload": unload, "device": "cuda" if str(device).startswith("cuda") else "cpu"}

    def released(self, key):
        with self._lock:
            self._held.pop(key, None)

    def status(self):
        with self._lock:
            return {"card": self.card(), "capMiB": self.cap_mib,
                    "headroomMiB": self.reg.headroom_mib((self.card() or {}).get("totalMiB", 0)),
                    "models": {k: {"device": v["device"], "mib": v["mib"]} for k, v in self._held.items()},
                    "lastDecision": self.last}
