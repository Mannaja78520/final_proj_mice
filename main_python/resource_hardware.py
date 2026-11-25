"""Small cached capability probes. Never import an AI library or open a device."""
import json
import os
import re
import shutil
import subprocess
import tempfile
import threading
import time
from pathlib import Path

VENDORS = Path(__file__).resolve().parent.parent / "config" / "gpu_vendors.json"


def load_vendors(path=None):
    """The vendor table (config/gpu_vendors.json, // comments allowed). {} rows when unreadable."""
    try:
        text = Path(path or VENDORS).read_text(encoding="utf-8")
        text = re.sub(r"^\s*//.*$", "", text, flags=re.M)
        return json.loads(text)
    except (OSError, ValueError):
        return {"vendors": [], "ignore": []}


def classify_adapters(names, table=None):
    """Adapter names -> [{name, vendor, ...vendor row}] for real GPUs only. Pure, no probing."""
    table = table or load_vendors()
    out = []
    for name in names:
        low = name.lower()
        if any(w in low for w in table.get("ignore", [])):
            continue
        row = next((v for v in table.get("vendors", []) if any(m in low for m in v["match"])), None)
        out.append({"name": name[:100], "vendor": row["id"] if row else "unknown",
                    "cudaRuntime": bool(row and row.get("cudaRuntime")),
                    "ollamaEnv": dict(row.get("ollamaEnv", {})) if row else {},
                    "sttBackend": row.get("sttBackend", "cpu") if row else "cpu"})
    return out


def adapter_names():
    """GPU adapter names from Windows (no vendor tool needed); [] elsewhere or on failure."""
    if os.name != "nt":
        return []
    try:
        out = subprocess.run(["powershell", "-NoProfile", "-Command",
                              "(Get-CimInstance Win32_VideoController).Name"],
                             capture_output=True, text=True, timeout=5,
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).stdout
    except (OSError, subprocess.SubprocessError):
        return []
    return [line.strip() for line in out.splitlines() if line.strip()][:8]


def visible_gpus(gpus, visible):
    if visible is None:
        return [{**g, "physicalIndex": g["index"]} for g in gpus]
    if not visible.strip() or visible.strip() == "-1":
        return []
    result = []
    for logical, token in enumerate(visible.split(",")):
        token = token.strip()
        found = [g for g in gpus if str(g["index"]) == token or (token.startswith("GPU-") and g.get("uuid", "").startswith(token))]
        if len(found) != 1 or any(g["physicalIndex"] == found[0]["index"] for g in result):
            return []  # Unsupported/ambiguous mapping must never target another GPU.
        result.append({**found[0], "physicalIndex": found[0]["index"], "index": logical})
    return result


class Capabilities:
    def __init__(self, ttl=30, probe=None, clock=time.monotonic):
        self.ttl, self.probe, self.clock = ttl, probe or self.detect, clock
        self._lock = threading.Lock()
        self._value, self._at = None, float("-inf")

    def snapshot(self, force=False):
        with self._lock:
            if force or self._value is None or self.clock() - self._at >= self.ttl:
                try:
                    self._value = self.probe()
                except Exception:
                    self._value = {"logicalCpus": os.cpu_count() or 1, "memoryMiB": None,
                                   "availableMemoryMiB": None, "gpus": [], "unknown": ["memory", "gpu"]}
                self._at = self.clock()
            return self._value

    @staticmethod
    def detect():
        result = {"logicalCpus": os.cpu_count() or 1, "memoryMiB": None,
                  "availableMemoryMiB": None, "gpus": [], "unknown": [],
                  "visibleDevices": os.environ.get("CUDA_VISIBLE_DEVICES")}
        try:
            import psutil
            try:
                result["logicalCpus"] = len(psutil.Process().cpu_affinity()) or result["logicalCpus"]
            except (AttributeError, OSError, psutil.Error):
                pass
            memory = psutil.virtual_memory()
            result.update(memoryMiB=memory.total // 1048576, availableMemoryMiB=memory.available // 1048576)
        except (ImportError, OSError, AttributeError):
            try:
                if os.name == "nt":
                    import ctypes
                    class Memory(ctypes.Structure):
                        _fields_ = [("length", ctypes.c_ulong), ("load", ctypes.c_ulong)] + [(key, ctypes.c_ulonglong) for key in
                                    ("total", "available", "pageTotal", "pageAvailable", "virtualTotal", "virtualAvailable", "extended")]
                    value = Memory(); value.length = ctypes.sizeof(value)
                    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(value)):
                        raise OSError("Memory discovery unavailable")
                    total, available = value.total, value.available
                else:
                    total = os.sysconf("SC_PHYS_PAGES") * os.sysconf("SC_PAGE_SIZE")
                    available = os.sysconf("SC_AVPHYS_PAGES") * os.sysconf("SC_PAGE_SIZE")
                result.update(memoryMiB=total // 1048576, availableMemoryMiB=available // 1048576)
            except (AttributeError, OSError, ValueError):
                result["unknown"].append("memory")
        # Every adapter Windows reports, by vendor: AMD/Intel cannot run CUDA but
        # Ollama can use them (user 2026-11-25). NVIDIA ones also get VRAM below.
        result["adapters"] = classify_adapters(adapter_names())
        tool = shutil.which("nvidia-smi")
        if not tool:
            if not result["adapters"]:
                result["unknown"].append("gpu")
            return result
        # A file bounds what we read into memory; no shell, windows or model start.
        try:
            with tempfile.TemporaryFile() as output:
                proc = subprocess.Popen([tool, "--query-gpu=index,uuid,name,memory.total,memory.free",
                                         "--format=csv,noheader,nounits"], stdout=output,
                                        stderr=subprocess.DEVNULL,
                                        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                try:
                    proc.wait(timeout=1.5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=1)
                    raise OSError("GPU discovery timed out")
                if proc.returncode:
                    raise OSError("GPU discovery unavailable")
                output.seek(0)
                text = output.read(8192).decode("utf-8", "replace")
            for line in text.splitlines()[:16]:
                index, uuid, name, total, free = [v.strip() for v in line.split(",", 4)]
                result["gpus"].append({"index": int(index), "uuid": uuid, "name": name[:100],
                                       "totalMiB": int(total), "freeMiB": int(free)})
        except (OSError, ValueError, subprocess.SubprocessError):
            result["gpus"] = []
            result["unknown"].append("gpu")
        return result
