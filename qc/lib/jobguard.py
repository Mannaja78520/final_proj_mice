"""QC leaves no browser behind.

2026-11-26: 119 headless Edge processes from QC runs were still alive on the PC, up
to 67 h old, about 4 GB of RAM. A killed or crashed runner, a check killed at its hard
limit, a Ctrl+C - each left its browsers running, because a browser is started through
PowerShell `Start-Process` and so is NOT a child of the check that wanted it.

Four layers, each cheap:
  1. A Windows JOB OBJECT with KILL_ON_JOB_CLOSE: the runner puts itself in one at
     start; every process it starts afterwards (pool children, PowerShell, Edge)
     belongs to the job whatever their parent does, and Windows kills them all when
     the runner ends - even on TerminateProcess, a crash or a power-button kill of
     the terminal. (install)
  2. Signal handlers and atexit: Ctrl+C, SIGTERM and CTRL_BREAK end the run normally,
     so the finally blocks and the exit hook kill what is left. (install_exit_hooks)
  3. A startup sweep: a QC browser is tagged MICEQCBROWSER<owner pid>END; one whose
     owner is dead, or that is older than MAX_AGE_SECS, is killed. A live owner's
     browsers are never touched (browser.sweep's live-pid rule, #273). (kill_stale)
  4. A check at the END of a full run: any tagged browser this run left (owner dead
     or this runner) fails the run. (left_behind)
"""
import atexit
import ctypes
import json
import os
import re
import signal
import subprocess
import sys
import time

MAX_AGE_SECS = 6 * 3600           # no QC page lives this long; older = a leak
_TAG = re.compile(r"MICEQCBROWSER(\d+)END")
_JOB = [None]                     # the handle must stay open for the life of the process


def install(cpu_cap_percent=None, below_normal=False, job_memory_gb=None):
    """Put this process in a kill-on-close job object. True when it took effect.

    Polite mode (user 2026-11-26, the PC was laggy during QC) also makes the JOB lower every
    process in it - including the PowerShell-launched Edge - to BELOW_NORMAL, and caps the whole
    job at `cpu_cap_percent` of the machine so it can never be fully saturated."""
    if os.name != "nt" or _JOB[0] is not None:
        return _JOB[0] is not None
    try:
        from ctypes import wintypes
        k32 = ctypes.WinDLL("kernel32", use_last_error=True)

        class _Basic(ctypes.Structure):
            _fields_ = [("PerProcessUserTimeLimit", ctypes.c_int64),
                        ("PerJobUserTimeLimit", ctypes.c_int64),
                        ("LimitFlags", wintypes.DWORD),
                        ("MinimumWorkingSetSize", ctypes.c_size_t),
                        ("MaximumWorkingSetSize", ctypes.c_size_t),
                        ("ActiveProcessLimit", wintypes.DWORD),
                        ("Affinity", ctypes.c_size_t),
                        ("PriorityClass", wintypes.DWORD),
                        ("SchedulingClass", wintypes.DWORD)]

        class _IoCounters(ctypes.Structure):
            _fields_ = [(n, ctypes.c_uint64) for n in
                        ("a", "b", "c", "d", "e", "f")]

        class _Extended(ctypes.Structure):
            _fields_ = [("Basic", _Basic), ("Io", _IoCounters),
                        ("ProcessMemoryLimit", ctypes.c_size_t),
                        ("JobMemoryLimit", ctypes.c_size_t),
                        ("PeakProcessMemoryUsed", ctypes.c_size_t),
                        ("PeakJobMemoryUsed", ctypes.c_size_t)]

        k32.CreateJobObjectW.restype = wintypes.HANDLE
        k32.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
        k32.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int,
                                                ctypes.c_void_p, wintypes.DWORD]
        k32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
        k32.GetCurrentProcess.restype = wintypes.HANDLE
        job = k32.CreateJobObjectW(None, None)
        if not job:
            return False
        info = _Extended()
        info.Basic.LimitFlags = 0x2000            # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if job_memory_gb:
            info.Basic.LimitFlags |= 0x200        # JOB_OBJECT_LIMIT_JOB_MEMORY
            info.JobMemoryLimit = int(job_memory_gb * 2 ** 30)
        if below_normal:
            info.Basic.LimitFlags |= 0x20         # JOB_OBJECT_LIMIT_PRIORITY_CLASS
            info.Basic.PriorityClass = 0x4000     # BELOW_NORMAL_PRIORITY_CLASS
        if not k32.SetInformationJobObject(job, 9, ctypes.byref(info), ctypes.sizeof(info)):
            return False
        if cpu_cap_percent:
            class _Cpu(ctypes.Structure):
                _fields_ = [("ControlFlags", wintypes.DWORD), ("CpuRate", wintypes.DWORD)]
            cpu = _Cpu(0x1 | 0x4, int(cpu_cap_percent * 100))   # ENABLE | HARD_CAP, 1/100 percent
            k32.SetInformationJobObject(job, 15, ctypes.byref(cpu), ctypes.sizeof(cpu))  # best effort
        if not k32.AssignProcessToJobObject(job, k32.GetCurrentProcess()):
            return False
        _JOB[0] = job
        return True
    except Exception:                              # noqa: BLE001 - a guard never stops a run
        return False


def set_cpu_cap(percent):
    """Tighten or relax the job's hard CPU cap while it runs (the governor calls this)."""
    if os.name != "nt" or _JOB[0] is None:
        return False
    try:
        from ctypes import wintypes
        k32 = ctypes.WinDLL("kernel32", use_last_error=True)

        class _Cpu(ctypes.Structure):
            _fields_ = [("ControlFlags", wintypes.DWORD), ("CpuRate", wintypes.DWORD)]
        cpu = _Cpu(0x1 | 0x4, int(max(1, min(100, percent)) * 100))
        k32.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int,
                                                ctypes.c_void_p, wintypes.DWORD]
        return bool(k32.SetInformationJobObject(_JOB[0], 15, ctypes.byref(cpu), ctypes.sizeof(cpu)))
    except Exception:                                  # noqa: BLE001
        return False


def job_peak_memory_gb():
    """Peak memory the job (QC run) used, in GB: for the run's summary line."""
    if os.name != "nt" or _JOB[0] is None:
        return None
    try:
        from ctypes import wintypes
        k32 = ctypes.WinDLL("kernel32", use_last_error=True)

        class _Basic(ctypes.Structure):
            _fields_ = [("a", ctypes.c_int64), ("b", ctypes.c_int64), ("flags", wintypes.DWORD),
                        ("c", ctypes.c_size_t), ("d", ctypes.c_size_t), ("e", wintypes.DWORD),
                        ("f", ctypes.c_size_t), ("g", wintypes.DWORD), ("h", wintypes.DWORD)]

        class _Io(ctypes.Structure):
            _fields_ = [(n, ctypes.c_uint64) for n in "abcdef"]

        class _Ext(ctypes.Structure):
            _fields_ = [("Basic", _Basic), ("Io", _Io), ("pm", ctypes.c_size_t),
                        ("jm", ctypes.c_size_t), ("peakp", ctypes.c_size_t), ("peakj", ctypes.c_size_t)]
        e = _Ext()
        k32.QueryInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p,
                                                  wintypes.DWORD, ctypes.c_void_p]
        if not k32.QueryInformationJobObject(_JOB[0], 9, ctypes.byref(e), ctypes.sizeof(e), None):
            return None
        return e.peakj / 2 ** 30
    except Exception:                                  # noqa: BLE001
        return None


def job_pids():
    """Process ids in this runner's job object (the runner, pool children, Edge ...)."""
    if os.name != "nt" or _JOB[0] is None:
        return []
    try:
        from ctypes import wintypes
        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        n = 4096
        buf = (ctypes.c_size_t * (n + 2))()
        k32.QueryInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p,
                                                  wintypes.DWORD, ctypes.c_void_p]
        if not k32.QueryInformationJobObject(_JOB[0], 3, buf, ctypes.sizeof(buf), None):
            return []
        got = min(int(buf[1]), n)                      # NumberOfProcessIdsInList
        return [int(buf[2 + i]) for i in range(got)]
    except Exception:                                  # noqa: BLE001
        return []


def _on_signal(signum, _frame):
    raise SystemExit(128 + (signum if isinstance(signum, int) else 0))


def install_exit_hooks():
    """Ctrl+C / SIGTERM / CTRL_BREAK end the run normally; atexit sweeps what is left."""
    for name in ("SIGINT", "SIGTERM", "SIGBREAK"):
        sig = getattr(signal, name, None)
        if sig is not None:
            try:
                signal.signal(sig, _on_signal)
            except (ValueError, OSError):
                pass                               # not the main thread
    atexit.register(lambda: kill_stale(include_owner=os.getpid()))


def _list(image):
    """[(pid, created_epoch, command line)] of processes called `image`."""
    if os.name != "nt":
        return []
    ps = ("Get-CimInstance Win32_Process -Filter \"Name='%s'\" | ForEach-Object { "
          "[pscustomobject]@{p=$_.ProcessId; t=[int64]([DateTimeOffset]$_.CreationDate)"
          ".ToUnixTimeSeconds(); c=$_.CommandLine} } | ConvertTo-Json -Compress" % image)
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                           capture_output=True, text=True, timeout=60)
        data = json.loads(r.stdout) if r.stdout.strip() else []
    except (OSError, subprocess.SubprocessError, ValueError):
        return []
    if isinstance(data, dict):
        data = [data]
    return [(int(d["p"]), int(d["t"]), d.get("c") or "") for d in data]


def stale_browsers(image="msedge.exe", now=None, max_age=MAX_AGE_SECS, include_owner=None,
                   since=None):
    """QC browsers that should not be alive: [(pid, owner, age_secs)].

    A browser counts when its owner pid is dead, or it is older than `max_age`, or its
    owner is `include_owner` (the caller itself, at exit). `since` limits to browsers
    started at or after that epoch time (the end-of-run check). A live other owner's
    young browser is never listed."""
    import runlock
    now = now or time.time()
    out = []
    for pid, created, cmd in _list(image):
        m = _TAG.search(cmd)
        if not m:
            continue                               # not ours: never touched
        owner = int(m.group(1))
        age = now - created
        if since is not None and created < since:
            continue
        if (not runlock.pid_alive(owner)) or age > max_age or owner == include_owner:
            out.append((pid, owner, int(age)))
    return out


def kill_stale(image="msedge.exe", **kw):
    """Kill every browser stale_browsers lists (process trees). Returns the list."""
    found = stale_browsers(image, **kw)
    for pid, _owner, _age in found:
        try:
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60)
        except (OSError, subprocess.SubprocessError):
            pass
    return found


def left_behind(since, image="msedge.exe", settle=6.0):
    """Browsers this run left alive (owner gone, or the runner itself). Waits for the
    ones just killed to finish dying, kills what remains, returns it."""
    deadline = time.time() + settle
    found = stale_browsers(image, since=since, include_owner=os.getpid())
    while found and time.time() < deadline:
        time.sleep(1.0)
        found = stale_browsers(image, since=since, include_owner=os.getpid())
    if found:
        kill_stale(image, since=since, include_owner=os.getpid())
    return found
