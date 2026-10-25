"""Small cached capability probes. Never import an AI library or open a device."""
import os
import shutil
import subprocess
import tempfile
import threading
import time


class Capabilities:
    def __init__(self, ttl=30, probe=None, clock=time.monotonic):
        self.ttl, self.probe, self.clock = ttl, probe or self.detect, clock
        self._lock = threading.Lock()
        self._value, self._at = None, float("-inf")

    def snapshot(self):
        with self._lock:
            if self._value is None or self.clock() - self._at >= self.ttl:
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
                  "availableMemoryMiB": None, "gpus": [], "unknown": []}
        try:
            import psutil
            try:
                result["logicalCpus"] = len(psutil.Process().cpu_affinity()) or result["logicalCpus"]
            except (AttributeError, OSError, psutil.Error):
                pass
            memory = psutil.virtual_memory()
            result.update(memoryMiB=memory.total // 1048576, availableMemoryMiB=memory.available // 1048576)
        except (ImportError, OSError, AttributeError):
            result["unknown"].append("memory")
        tool = shutil.which("nvidia-smi")
        if not tool:
            result["unknown"].append("gpu")
            return result
        # A file bounds what we read into memory; no shell, windows or model start.
        try:
            with tempfile.TemporaryFile() as output:
                proc = subprocess.Popen([tool, "--query-gpu=index,name,memory.total,memory.free",
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
                index, name, total, free = [v.strip() for v in line.split(",", 3)]
                result["gpus"].append({"index": int(index), "name": name[:100],
                                       "totalMiB": int(total), "freeMiB": int(free)})
        except (OSError, ValueError, subprocess.SubprocessError):
            result["gpus"] = []
            result["unknown"].append("gpu")
        return result
