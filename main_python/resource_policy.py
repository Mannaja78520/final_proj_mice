"""Data-driven resource choices, shared by the Hub and separately launched helpers."""
import json
import math
import os
from pathlib import Path

from resource_hardware import Capabilities
from resource_settings import ResourceSettings


class ResourcePolicy:
    def __init__(self, registry, settings, capabilities=None):
        self.registry_path, self.settings_path = Path(registry), Path(settings)
        self.registry = json.loads(self.registry_path.read_text(encoding="utf-8"))
        self._validate_registry()
        self.capabilities = capabilities or Capabilities(self.registry["probeSeconds"])
        self.store = ResourceSettings(settings, self.registry["defaults"], self.validate)

    def _validate_registry(self):
        r = self.registry
        if r.get("version") != 1 or not r.get("profiles") or not r.get("browser", {}).get("profiles"):
            raise ValueError("Resource registry is incomplete")
        for field in ("profiles",):
            ids = [p["id"] for p in r[field]]
            if len(set(ids)) != len(ids) or "auto" in ids:
                raise ValueError("Resource profile identifiers must be unique")
        for p in r["browser"]["profiles"]:
            if not (1 <= p["fps"] <= 120 and 0.5 <= p["pixelRatio"] <= 3 and type(p["antialias"]) is bool):
                raise ValueError("Browser profile limits are invalid")

    def validate(self, settings):
        r = self.registry
        if not isinstance(settings, dict) or set(settings) != set(r["defaults"]):
            raise ValueError("ต้องส่งค่าประสิทธิภาพให้ครบ และใช้เฉพาะตัวเลือกที่มี")
        if settings["mode"] not in ["auto"] + [p["id"] for p in r["profiles"]]:
            raise ValueError("ไม่มีโหมดประสิทธิภาพนี้")
        if settings["device"] not in [p["id"] for p in r["devices"]]:
            raise ValueError("ไม่มีตัวเลือกหน่วยประมวลผลนี้")
        for key, (low, high) in r["limits"].items():
            value = settings[key]
            if type(value) is not int or not low <= value <= high:
                raise ValueError("ค่าประสิทธิภาพอยู่นอกช่วงที่กำหนด: " + key)
        return dict(settings)

    def resolve(self, snapshot=None, saved=None):
        saved = saved or self.store.read()
        cfg = saved["settings"]
        h = snapshot if snapshot is not None else self.capabilities.snapshot()
        cores = max(1, int(h.get("logicalCpus") or 1))
        profiles = self.registry["profiles"]
        profile = profiles[0]
        if cfg["mode"] == "auto":
            for p in profiles:
                if cores >= p["minCpus"] and (h.get("memoryMiB") or 0) >= p["minMemoryMiB"]:
                    profile = p
        else:
            profile = next(p for p in profiles if p["id"] == cfg["mode"])
        threads = cfg["cpuThreads"] or max(1, min(profile["maxThreads"], math.floor(cores * profile["cpuShare"])))
        threads = min(threads, max(1, cores - 1))
        workers = min(cfg["workers"] or profile["workers"], threads)
        available = h.get("availableMemoryMiB")
        ram = max(0, available - cfg["ramReserveMiB"]) if available is not None else None
        gpu = [{**g, "budgetMiB": max(0, g["freeMiB"] - cfg["vramReserveMiB"])} for g in h.get("gpus", [])]
        usable = [g for g in gpu if g["budgetMiB"] >= 512]
        device = "cuda" if cfg["device"] != "cpu" and usable else "cpu"
        warning = saved.get("warning", "")
        if cfg["device"] == "cuda" and not usable:
            warning = (warning + " " if warning else "") + "GPU ยังไม่พร้อมหรือหน่วยความจำไม่พอ จึงใช้ CPU"
        return {"revision": saved["revision"], "profile": profile["id"], "label": profile["label"],
                "device": device, "deviceIndex": usable[0]["index"] if device == "cuda" else 0, "cpuThreads": threads, "workers": workers, "ramBudgetMiB": ram,
                "gpus": usable if device == "cuda" else [], "warning": warning}

    def status(self):
        saved = self.store.read()
        snapshot = self.capabilities.snapshot()
        return {"ok": True, **saved, "effective": self.resolve(snapshot, saved), "hardware": snapshot,
                "choices": {"profiles": self.registry["profiles"], "devices": self.registry["devices"],
                            "limits": self.registry["limits"]},
                "notice": "ค่ามีผลกับการโหลดงานครั้งถัดไป โมเดลที่เปิดอยู่ยังใช้ค่าเดิม งบหน่วยความจำเป็นค่าช่วยเลือกวิธีโหลด ไม่ใช่เพดานการใช้ทั้งหมด"}

    def client_data(self):
        return self.registry["browser"]

    def child_environment(self):
        return {**os.environ, "MICE_RESOURCE_SETTINGS": str(self.settings_path),
                "MICE_RESOURCE_REGISTRY": str(self.registry_path)}
