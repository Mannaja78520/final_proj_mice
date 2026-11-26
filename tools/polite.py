"""Be polite to the PC: run our heavy background work at low priority.

User 2026-11-26: a full QC run left the PC laggy and hard to use. QC, builds and
measurement scripts are BACKGROUND work: they should finish a little later rather
than make the machine unusable. This lowers the calling process to
  * CPU priority BELOW_NORMAL (children inherit it),
  * I/O priority LOW and memory priority LOW (the disk and RAM pressure that makes a
    desktop stutter; Windows only),
and on other systems `nice`.

NEVER used on the real hub, the Voice helper or the Face recognition service: those
serve people and must keep normal priority. Entry points of OUR tools call
`polite.apply("name")` first.

Switches: `qc/data/qc_speed.json` "polite": false, or env MICE_POLITE=0, or the flag
--exact-timing (a measurement that needs exact timing). When it is off the tool prints
that it runs at normal priority, so nobody reads a timing as a polite one.
"""
import ctypes
import json
import os
import sys
import time
from pathlib import Path

BELOW_NORMAL = 0x4000
ROOT = Path(__file__).resolve().parent.parent
SPEED_FILE = ROOT / "qc" / "data" / "qc_speed.json"


def _strip_comments(text):
    """Drop // comments that are outside strings (a tiny scanner: no regex, no escapes to get wrong)."""
    out, in_str, esc, i = [], False, False, 0
    while i < len(text):
        c = text[i]
        if in_str:
            out.append(c)
            if esc:
                esc = False
            elif c == chr(92):
                esc = True
            elif c == '"':
                in_str = False
        elif c == '"':
            in_str = True
            out.append(c)
        elif c == "/" and text[i + 1:i + 2] == "/":
            while i < len(text) and text[i] != chr(10):
                i += 1
            continue
        else:
            out.append(c)
        i += 1
    return "".join(out)


def config_polite():
    """The file's "polite" value (default True). Comments in the file are allowed."""
    try:
        raw = SPEED_FILE.read_text(encoding="utf-8")
        data = json.loads(_strip_comments(raw))
        return bool(data.get("polite", True))
    except (OSError, ValueError):
        return True


def enabled(argv=None):
    """True unless MICE_POLITE=0, --exact-timing, or "polite": false in the config."""
    argv = sys.argv if argv is None else argv
    if os.environ.get("MICE_POLITE", "").strip() == "0":
        return False
    if "--exact-timing" in argv:
        return False
    return config_polite()


def lower_priority():
    """Lower this process now. Returns a short description of what was set."""
    if os.name != "nt":
        try:
            os.nice(10)
            return "nice +10"
        except OSError:
            return "nice failed"
    done = []
    try:
        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        k32.GetCurrentProcess.restype = ctypes.c_void_p
        h = ctypes.c_void_p(k32.GetCurrentProcess())
        k32.SetPriorityClass.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
        if k32.SetPriorityClass(h, BELOW_NORMAL):
            done.append("cpu below-normal")
        # I/O priority: ProcessIoPriority (33) = IoPriorityLow (1)
        try:
            nt = ctypes.WinDLL("ntdll")
            val = ctypes.c_ulong(1)
            nt.NtSetInformationProcess.argtypes = [ctypes.c_void_p, ctypes.c_int,
                                                   ctypes.c_void_p, ctypes.c_ulong]
            if nt.NtSetInformationProcess(h, 33, ctypes.byref(val), 4) == 0:
                done.append("io low")
        except (OSError, AttributeError):
            pass
        # memory priority: ProcessMemoryPriority (0), MEMORY_PRIORITY_LOW (2)
        try:
            class _Mem(ctypes.Structure):
                _fields_ = [("MemoryPriority", ctypes.c_ulong)]
            k32.SetProcessInformation.argtypes = [ctypes.c_void_p, ctypes.c_int,
                                                  ctypes.c_void_p, ctypes.c_ulong]
            mem = _Mem(2)
            if k32.SetProcessInformation(h, 0, ctypes.byref(mem), ctypes.sizeof(mem)):
                done.append("memory low")
        except (OSError, AttributeError):
            pass
    except OSError:
        return "not available"
    return ", ".join(done) or "nothing set"


def priority_class(pid=None):
    """The Windows priority class of a process (0x4000 below normal, 0x20 normal), or None."""
    if os.name != "nt":
        return None
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.OpenProcess.restype = ctypes.c_void_p
    k32.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
    k32.GetPriorityClass.argtypes = [ctypes.c_void_p]
    h = k32.OpenProcess(0x1000, False, pid or os.getpid())     # QUERY_LIMITED_INFORMATION
    if not h:
        return None
    try:
        return k32.GetPriorityClass(h)
    finally:
        k32.CloseHandle(ctypes.c_void_p(h))


# ---- yield to the person using the PC --------------------------------------------------
# User 2026-11-26: the PC lagged (SolidWorks, typing) while our runs were going. Lower priority
# is not always enough, so heavy jobs also YIELD: while a configured foreground app runs
# ("yieldTo", e.g. SLDWORKS.exe) or the person touched keyboard/mouse in the last
# "idleSeconds", no new work starts - and in "freeze" mode the running processes are
# SUSPENDED (NtSuspendProcess, nothing is killed, nothing is lost) and resumed afterwards.

def _speed_cfg():
    try:
        return json.loads(_strip_comments(SPEED_FILE.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return {}


def yield_settings(cfg=None):
    """What the governor and the optional yield read from qc/data/qc_speed.json."""
    cfg = _speed_cfg() if cfg is None else cfg
    return {"yieldTo": [str(x).lower() for x in (cfg.get("yieldTo") or [])],
            "idleSeconds": float(cfg.get("idleSeconds") or 20),
            "yieldToInput": bool(cfg.get("yieldToInput", False)),
            # "none" (default): always-on headroom only; "pause": also stop starting while a
            # foreground app runs / the person is typing; "freeze": also suspend running work
            "yieldMode": str(cfg.get("yieldMode") or "none"),
            "targetCpuPct": float(cfg.get("targetCpuPct") or 75),
            "reserveRamGb": float(cfg.get("reserveRamGb") or 6),
            "gpuReservePct": float(cfg.get("gpuReservePct") or 30),
            "reserveCpus": int(cfg.get("reserveCpus") or 4),
            "cpuCapPercent": cfg.get("cpuCapPercent")}


def user_idle_ms():
    """Milliseconds since the last keyboard/mouse input (Windows); None when unknown."""
    if os.name != "nt":
        return None
    try:
        class _Lii(ctypes.Structure):
            _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]
        lii = _Lii(ctypes.sizeof(_Lii), 0)
        if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii)):
            return None
        return (ctypes.windll.kernel32.GetTickCount() - lii.dwTime) & 0xFFFFFFFF
    except (OSError, AttributeError):
        return None


def running_names():
    """Lower-case image names of running processes."""
    try:
        import psutil
        return {(p.info["name"] or "").lower() for p in psutil.process_iter(["name"])}
    except ImportError:
        pass
    if os.name == "nt":
        try:
            import subprocess
            out = subprocess.run(["tasklist", "/FO", "CSV", "/NH"], capture_output=True,
                                 text=True, timeout=30).stdout
            return {l.split(",")[0].strip('"').lower() for l in out.splitlines() if l}
        except (OSError, subprocess.SubprocessError):
            return set()
    return set()


def busy_reason(settings=None, names=None, idle_ms=None):
    """Why our heavy work should yield right now, or None. Inputs can be injected (tests)."""
    st = settings or yield_settings()
    have = running_names() if names is None else {n.lower() for n in names}
    for app in st["yieldTo"]:
        if app in have:
            return "%s is running" % app
    if st["yieldToInput"]:
        idle = user_idle_ms() if idle_ms is None else idle_ms
        if idle is not None and idle < st["idleSeconds"] * 1000:
            return "you used the keyboard/mouse %.0f s ago" % (idle / 1000.0)
    return None


class PauseClock:
    """Seconds spent paused, so a hard time limit never counts the time a run was frozen."""

    def __init__(self):
        self._total, self._since = 0.0, None

    def begin(self):
        if self._since is None:
            self._since = time.time()

    def end(self):
        if self._since is not None:
            self._total += time.time() - self._since
            self._since = None

    @property
    def paused(self):
        return self._total + (time.time() - self._since if self._since is not None else 0.0)


def _nt_each(pids, name):
    """Call NtSuspendProcess / NtResumeProcess on pids. Returns how many were reached."""
    if os.name != "nt":
        return 0
    nt = ctypes.WinDLL("ntdll")
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.OpenProcess.restype = ctypes.c_void_p
    k32.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
    n = 0
    for pid in pids:
        h = k32.OpenProcess(0x0800, False, pid)                  # PROCESS_SUSPEND_RESUME
        if not h:
            continue
        try:
            getattr(nt, name)(ctypes.c_void_p(h))
            n += 1
        finally:
            k32.CloseHandle(ctypes.c_void_p(h))
    return n


def freeze(pids):
    """Suspend processes (no kill: nothing is lost). Returns how many."""
    return _nt_each(pids, "NtSuspendProcess")


def thaw(pids):
    return _nt_each(pids, "NtResumeProcess")


class LoadSampler:
    """Live load of the whole machine: CPU %, free RAM (GB), GPU % (nvidia-smi, cached)."""

    def __init__(self, gpu_every=10.0):
        self._cpu_prev = None
        self._gpu_at, self._gpu = 0.0, None
        self.gpu_every = gpu_every

    @staticmethod
    def _times():
        class _Ft(ctypes.Structure):
            _fields_ = [("lo", ctypes.c_uint), ("hi", ctypes.c_uint)]
        a, b, c = _Ft(), _Ft(), _Ft()
        ctypes.windll.kernel32.GetSystemTimes(ctypes.byref(a), ctypes.byref(b), ctypes.byref(c))
        v = lambda f: (f.hi << 32) | f.lo
        return v(a), v(b), v(c)                      # idle, kernel (includes idle), user

    def cpu_pct(self):
        if os.name != "nt":
            try:
                return os.getloadavg()[0] / (os.cpu_count() or 1) * 100.0
            except (OSError, AttributeError):
                return 0.0
        idle, kern, user = self._times()
        prev, self._cpu_prev = self._cpu_prev, (idle, kern, user)
        if not prev:
            return 0.0
        di, dk, du = idle - prev[0], kern - prev[1], user - prev[2]
        total = dk + du
        return max(0.0, min(100.0, (total - di) * 100.0 / total)) if total > 0 else 0.0

    @staticmethod
    def free_ram_gb():
        if os.name != "nt":
            try:
                return os.sysconf("SC_AVPHYS_PAGES") * os.sysconf("SC_PAGE_SIZE") / 2 ** 30
            except (ValueError, OSError, AttributeError):
                return 99.0

        class _Ms(ctypes.Structure):
            _fields_ = [("len", ctypes.c_uint), ("load", ctypes.c_uint)] + \
                       [(n, ctypes.c_uint64) for n in ("tot", "avail", "tpf", "apf", "tv", "av", "ae")]
        m = _Ms()
        m.len = ctypes.sizeof(m)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
        return m.avail / 2 ** 30

    @staticmethod
    def total_ram_gb():
        try:
            if os.name == "nt":
                class _Ms(ctypes.Structure):
                    _fields_ = [("len", ctypes.c_uint), ("load", ctypes.c_uint)] + \
                               [(n, ctypes.c_uint64) for n in ("tot", "avail", "tpf", "apf", "tv", "av", "ae")]
                m = _Ms()
                m.len = ctypes.sizeof(m)
                ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
                return m.tot / 2 ** 30
            return os.sysconf("SC_PHYS_PAGES") * os.sysconf("SC_PAGE_SIZE") / 2 ** 30
        except (OSError, ValueError, AttributeError):
            return 0.0

    def gpu_pct(self):
        now = time.time()
        if now - self._gpu_at < self.gpu_every:
            return self._gpu
        self._gpu_at = now
        try:
            import subprocess
            out = subprocess.run(["nvidia-smi", "--query-gpu=utilization.gpu",
                                  "--format=csv,noheader,nounits"], capture_output=True,
                                 text=True, timeout=10).stdout.split()
            self._gpu = max(float(x) for x in out) if out else None
        except (OSError, ValueError, Exception):    # noqa: BLE001 - no GPU / no tool: no limit
            self._gpu = None
        return self._gpu

    def sample(self):
        return {"cpu": self.cpu_pct(), "ram_free_gb": self.free_ram_gb(), "gpu": self.gpu_pct()}


class Governor:
    """Always-on headroom for the person using the PC (user 2026-11-26: leave room for the
    other programs that are open, do not stop and wait).

    Every ~2 s it reads the live load of the WHOLE machine. While total CPU is above
    targetCpuPct, free RAM below reserveRamGb, or the GPU above 100 - gpuReservePct, our
    pools start no NEW check (the ones running finish; at least one check per pool always
    keeps going, so a busy PC slows us down instead of stopping us). It also tightens the
    job's CPU cap when the machine is over target and relaxes it when there is room again.
    It never suspends or kills anything by default; "yieldMode": "pause"/"freeze" in
    qc/data/qc_speed.json adds the stronger yield to foreground apps ("yieldTo") and input."""

    def __init__(self, settings=None, pids=None, clock=None, load=None, set_cap=None,
                 base_cap=None, say=None, every=2.0, probe=None):
        self.st = settings or yield_settings()
        self.pids, self.clock = pids or (lambda: []), clock or PauseClock()
        self.load = load or LoadSampler().sample
        self.set_cap, self.say = set_cap, say or (lambda m: None)
        self.every, self._last = every, 0.0
        self.probe = probe                                  # optional strong-yield probe (tests)
        self.base_cap = base_cap or 100.0
        self.cap, self.floor_cap = self.base_cap, min(self.base_cap, 40.0)
        self.hold, self.reasons, self.frozen = False, [], []
        self.held_ticks = self.ticks = 0
        self.min_cap = self.base_cap
        self._told = ""

    def holding(self):
        """True while NO new check may start. Cheap: samples at most every `every` s."""
        self.tick()
        return self.hold

    def tick(self, now=None):
        now = now or time.time()
        if now - self._last < self.every:
            return
        self._last = now
        s = self.load()
        reasons = []
        if s["cpu"] > self.st["targetCpuPct"]:
            reasons.append("CPU %.0f%% > %.0f%%" % (s["cpu"], self.st["targetCpuPct"]))
        if s["ram_free_gb"] < self.st["reserveRamGb"]:
            reasons.append("free RAM %.1f GB < %.1f GB" % (s["ram_free_gb"], self.st["reserveRamGb"]))
        if s.get("gpu") is not None and s["gpu"] > 100 - self.st["gpuReservePct"]:
            reasons.append("GPU %.0f%% busy" % s["gpu"])
        strong = None
        if self.st["yieldMode"] in ("pause", "freeze"):
            strong = (self.probe or (lambda: busy_reason(self.st)))()
            if strong:
                reasons.append(strong)
        self.ticks += 1
        self.reasons, self.hold = reasons, bool(reasons)
        self.held_ticks += 1 if self.hold else 0
        # freeze mode: suspend the running work only for the strong reason, nothing is killed
        if self.st["yieldMode"] == "freeze":
            if strong and not self.frozen:
                self.frozen = [p for p in self.pids() if p != os.getpid()]
                freeze(self.frozen)
                self.clock.begin()
            elif not strong and self.frozen:
                thaw(self.frozen)
                self.frozen = []
                self.clock.end()
        # dynamic CPU cap
        if self.set_cap:
            if s["cpu"] > self.st["targetCpuPct"]:
                new = max(self.floor_cap, self.cap - 10.0)
            elif s["cpu"] < self.st["targetCpuPct"] - 15:
                new = min(self.base_cap, self.cap + 5.0)
            else:
                new = self.cap
            if new != self.cap:
                self.cap = new
                self.min_cap = min(self.min_cap, new)
                self.set_cap(new)
        msg = ", ".join(reasons)
        if msg != self._told:
            self._told = msg
            self.say("QC is making room for the PC (%s): not starting new checks" % msg
                     if msg else "QC: the PC has room again, starting checks as before")

    def stats(self):
        return {"ticks": self.ticks, "held_ticks": self.held_ticks,
                "cap_now": self.cap, "cap_min": self.min_cap}


def wait_until_free(tool, max_wait=1800, settings=None, probe=None, sleep=time.sleep, say=print):
    """Gate for a tool that cannot be paused mid-way: do not START while the person is busy."""
    st = settings or yield_settings()
    probe = probe or (lambda: busy_reason(st))
    t0, told = time.time(), 0.0
    while True:
        why = probe()
        if not why:
            return True
        if time.time() - t0 > max_wait:
            say("%s: still busy (%s) after %d s: starting anyway at low priority" % (tool, why, max_wait))
            return False
        if time.time() - told > 60:
            say("%s: waiting, %s (MICE_POLITE=0 or --exact-timing to skip)" % (tool, why))
            told = time.time()
        sleep(5)


def apply(tool, argv=None, gate=False):
    """Entry-point helper: lower priority unless switched off; say so only when off."""
    argv = sys.argv if argv is None else argv
    on = enabled(argv)
    while "--exact-timing" in sys.argv:
        sys.argv.remove("--exact-timing")
    if on:
        if gate and "--no-yield" not in argv:
            wait_until_free(tool)
        return lower_priority()
    print("%s: running at NORMAL priority (polite mode off: MICE_POLITE=0, --exact-timing "
          "or \"polite\": false); timings are not from a polite run." % tool, flush=True)
    return "normal"
