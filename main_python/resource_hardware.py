"""Small cached capability probes. Never import an AI library or open a device."""
import os
import shutil
import subprocess
import tempfile
import threading
import time


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
        tool = shutil.which("nvidia-smi")
        if not tool:
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
