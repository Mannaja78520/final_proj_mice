"""Let the Voice helper's models go from the GPU when nobody is using them.

User 2026-11-26: the PC was sluggish (SolidWorks, typing) while the Voice helper sat on 5.4 GB
of the card's 12 GB doing nothing. This frees GPU memory after `idleUnloadMinutes` without a
request (default 15, 0 = never) by calling the same `brain.unload()` the page's Unload button
uses; the process keeps running and the models load again, lazily, on the next request, which
shows a "warming up" state and has its first-request cost measured and kept for /health.

Never unloads: while a request is being answered; in presence/greeter mode (presence.on - the
helper is waiting for someone to walk up); when idleUnloadMinutes is 0.
Optional: `yieldVramWhen` lists apps (e.g. SLDWORKS.exe). While one of them is running and the
helper is idle, it unloads after `yieldVramMinutes` (default 1) instead, so a heavy foreground
app gets the card.

Settings live in config/voice.json (one source, the page and the hub read it too).
"""
import os
import threading
import time

DEFAULT_MINUTES = 15
DEFAULT_YIELD_MINUTES = 1


def running_names():
    """Lower-case image names of running processes (Windows tasklist, psutil if present)."""
    try:
        import psutil
        return {(p.info["name"] or "").lower() for p in psutil.process_iter(["name"])}
    except ImportError:
        pass
    try:
        import subprocess
        out = subprocess.run(["tasklist", "/FO", "CSV", "/NH"], capture_output=True,
                             text=True, timeout=20,
                             creationflags=0x08000000 if os.name == "nt" else 0).stdout
        return {l.split(",")[0].strip('"').lower() for l in out.splitlines() if l}
    except (OSError, ValueError, Exception):       # noqa: BLE001
        return set()


def gpu_used_mib():
    """GPU memory in use on the card (MiB) from nvidia-smi, or None. Used to report what an unload freed."""
    try:
        import subprocess
        out = subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                             capture_output=True, text=True, timeout=10,
                             creationflags=0x08000000 if os.name == "nt" else 0).stdout.split()
        return int(float(out[0]))
    except (OSError, ValueError, IndexError, Exception):      # noqa: BLE001 - no GPU / no tool: no number
        return None


class IdleUnloader:
    """Watches the helper; `brain` needs unload(), a `cfg` dict and presence settings in it."""

    def __init__(self, brain, clock=time.monotonic, names=running_names, poll=15.0,
                 vram_used=gpu_used_mib):
        self.brain, self.clock, self.names, self.poll = brain, clock, names, poll
        self.vram_used = vram_used                 # () -> MiB used on the card: what an unload freed is kept
        self.last_used = clock()
        self.inflight = 0
        self.asleep = False
        self.warming = False
        self.last_unload = None                    # {"at": epoch, "freedMiB": n, "why": str}
        self.first_request_ms = None
        self._woke_at = None
        self._mu = threading.Lock()
        self._stop = threading.Event()

    # ---- settings -----------------------------------------------------------
    def settings(self):
        cfg = getattr(self.brain, "cfg", None) or {}
        try:
            minutes = float(cfg.get("idleUnloadMinutes", DEFAULT_MINUTES))
        except (TypeError, ValueError):
            minutes = DEFAULT_MINUTES
        try:
            yield_min = float(cfg.get("yieldVramMinutes", DEFAULT_YIELD_MINUTES))
        except (TypeError, ValueError):
            yield_min = DEFAULT_YIELD_MINUTES
        apps = [str(a).lower() for a in (cfg.get("yieldVramWhen") or [])]
        return {"minutes": minutes, "yieldMinutes": yield_min, "apps": apps,
                "presence": bool((cfg.get("presence") or {}).get("on"))}

    # ---- requests -----------------------------------------------------------
    def request_start(self, path=""):
        """A request that may use the models begins. Returns True if it has to wake them."""
        with self._mu:
            self.inflight += 1
            self.last_used = self.clock()
            if self.asleep and not self.warming:
                self.warming = True
                self._woke_at = self.clock()
            return self.warming

    def request_end(self):
        with self._mu:
            self.inflight = max(0, self.inflight - 1)
            self.last_used = self.clock()
            if self.warming and self._woke_at is not None:
                self.first_request_ms = int((self.clock() - self._woke_at) * 1000)
                self.warming = False
                self.asleep = False

    # ---- what the brain holds -----------------------------------------------------
    def loading(self):
        """True while a model is still loading: unloading then would race the load."""
        b = self.brain
        return bool(getattr(b, "_llm_loading", False) or getattr(b, "_stt_loading", False))

    def holds_models(self):
        """True when there is something in memory to free. A brain without the usual fields
        (a test double) counts as holding models."""
        b = self.brain
        if not any(hasattr(b, n) for n in ("_llm_loaded_model", "_stt_loaded_model", "_stt_own", "_llm")):
            return True
        return bool(getattr(b, "_llm_loaded_model", None) or getattr(b, "_stt_loaded_model", None)
                    or getattr(b, "_stt_own", None) or getattr(b, "_llm", None))

    # ---- the decision --------------------------------------------------------
    def limit_secs(self):
        """Seconds of idleness after which the models go, or None for never."""
        st = self.settings()
        if st["minutes"] <= 0 or st["presence"]:
            return None
        limit = st["minutes"] * 60.0
        if st["apps"] and set(st["apps"]) & {n.lower() for n in self.names()}:
            limit = min(limit, st["yieldMinutes"] * 60.0)
        return limit

    def tick(self):
        """Unload if the helper has been idle long enough. Returns True when it unloaded."""
        with self._mu:
            if self.inflight or self.asleep:
                return False
            if self.loading():                     # idle time counts from when loading ENDS
                self.last_used = self.clock()
                return False
            if not self.holds_models():            # nothing in memory: nothing to free, not "asleep"
                self.last_used = self.clock()
                return False
            idle = self.clock() - self.last_used
        limit = self.limit_secs()
        if limit is None or idle < limit:
            return False
        before = self.vram_used() if self.vram_used else None
        self.brain.unload()
        time.sleep(1.0) if self.vram_used is gpu_used_mib else None      # the driver reports the release a moment later
        after = self.vram_used() if self.vram_used else None
        with self._mu:
            if self.inflight:                      # a request arrived while unloading: it reloads
                self.asleep = True
            else:
                self.asleep = True
            self.last_unload = {"at": time.time(), "idleSeconds": int(idle),
                                "freedMiB": (before - after) if before is not None and after is not None else None,
                                "why": "idle for %d s" % idle}
        return True

    def state(self):
        """For /health and the page."""
        st = self.settings()
        return {"minutes": st["minutes"], "asleep": self.asleep, "warming": self.warming,
                "lastUnload": self.last_unload, "firstRequestMs": self.first_request_ms,
                "yieldVramWhen": st["apps"]}

    # ---- background thread --------------------------------------------------------
    def start(self):
        th = threading.Thread(target=self._run, daemon=True, name="voice-idle-unload")
        th.start()
        return th

    def _run(self):
        while not self._stop.wait(self.poll):
            try:
                self.tick()
            except Exception as e:                # noqa: BLE001 - freeing memory must never take the helper down
                print("[voice] idle unload: %s" % e)

    def stop(self):
        self._stop.set()
