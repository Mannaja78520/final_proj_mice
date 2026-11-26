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


def apply(tool, argv=None):
    """Entry-point helper: lower priority unless switched off; say so only when off."""
    argv = sys.argv if argv is None else argv
    on = enabled(argv)
    while "--exact-timing" in sys.argv:
        sys.argv.remove("--exact-timing")
    if on:
        return lower_priority()
    print("%s: running at NORMAL priority (polite mode off: MICE_POLITE=0, --exact-timing "
          "or \"polite\": false); timings are not from a polite run." % tool, flush=True)
    return "normal"
