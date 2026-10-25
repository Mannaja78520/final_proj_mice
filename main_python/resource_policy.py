"""Data-driven resource choices, shared by the Hub and separately launched helpers."""
import json
import math
import os
from pathlib import Path

from resource_hardware import Capabilities, visible_gpus
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
        if not isinstance(r, dict) or not isinstance(r.get("browser"), dict):
            raise ValueError("Resource registry must be an object with browser presets")
        def number(value, low, high, integer=False):
            return type(value) in ((int,) if integer else (int, float)) and math.isfinite(value) and low <= value <= high
        if type(r.get("version")) is not int or r["version"] != 1 or not number(r.get("probeSeconds"), 1, 3600):
            raise ValueError("Resource registry version/probe interval is invalid")
        if not isinstance(r.get("defaults"), dict) or set(r["defaults"]) != {"mode", "device", "cpuThreads", "workers", "ramReserveMiB", "vramReserveMiB"}:
            raise ValueError("Resource defaults are incomplete")
        expected = set(r["defaults"]) - {"mode", "device"}
        if set(r.get("limits", {})) != expected:
            raise ValueError("Resource control limits are incomplete")
        for bounds in r["limits"].values():
            if not isinstance(bounds, list) or len(bounds) != 2 or not all(number(v, 0, 1048576, True) for v in bounds) or bounds[0] > bounds[1]:
                raise ValueError("Resource control limits are invalid")
        for group in (r.get("profiles"), r.get("devices"), r.get("browser", {}).get("profiles")):
            if not isinstance(group, list) or not 1 <= len(group) <= 32:
                raise ValueError("Resource choices are incomplete")
            if any(not isinstance(p, dict) for p in group):
                raise ValueError("Resource choices must be objects")
            ids = [p.get("id") for p in group]
            if any(not isinstance(i, str) or not i or len(i) > 32 for i in ids) or len(set(ids)) != len(ids):
                raise ValueError("Resource choice identifiers must be unique")
            if any(not isinstance(p.get("label"), str) or not p["label"] for p in group):
                raise ValueError("Resource choice labels are missing")
        if {p["id"] for p in r["devices"]} != {"auto", "cpu", "cuda"} or any(p["id"] == "auto" for p in r["profiles"] + r["browser"]["profiles"]):
            raise ValueError("Resource device/profile identifiers are invalid")
        for p in r["profiles"]:
            if not all((number(p.get("minCpus"), 1, 256, True), number(p.get("minMemoryMiB"), 0, 4194304, True),
                        number(p.get("cpuShare"), 0.01, 1), number(p.get("maxThreads"), 1, 256, True), number(p.get("workers"), 1, 8, True))):
                raise ValueError("CPU profile bounds are invalid")
        for p in r["browser"]["profiles"]:
            if not all((number(p.get("fps"), 1, 120), number(p.get("pixelRatio"), 0.5, 3), number(p.get("minCpus"), 1, 256, True),
                        number(p.get("minMemoryGiB"), 0, 4096), type(p.get("antialias")) is bool)):
                raise ValueError("Browser profile limits are invalid")
        if set(r.get("minimumLoadMiB", {})) != {"llmCpu", "sparkCpu", "sparkCuda", "sttCpu", "sttCuda"} or not all(number(v, 1, 1048576, True) for v in r["minimumLoadMiB"].values()):
            raise ValueError("Model admission budgets are invalid")
        if not number(r.get("loadHeadroom"), 1, 4):
            raise ValueError("Model memory headroom is invalid")
        self.validate(r["defaults"])

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
        gpu = [{**g, "budgetMiB": max(0, g["freeMiB"] - cfg["vramReserveMiB"])} for g in visible_gpus(h.get("gpus", []), h.get("visibleDevices"))]
        usable = [g for g in gpu if g["budgetMiB"] >= 512]
        device = "cuda" if cfg["device"] != "cpu" and usable else "cpu"
        warning = saved.get("warning", "")
        if cfg["device"] == "cuda" and not usable:
            warning = (warning + " " if warning else "") + "GPU ยังไม่พร้อมหรือหน่วยความจำไม่พอ จึงใช้ CPU"
        if ram is not None and ram < min(self.registry["minimumLoadMiB"]["llmCpu"], self.registry["minimumLoadMiB"]["sttCpu"]):
            warning = (warning + " " if warning else "") + "งบ RAM ไม่พอสำหรับโหลด AI ใหม่ ปรับหน่วยความจำสำรองหรือเลือกงานที่เล็กลง"
        return {"revision": saved["revision"], "profile": profile["id"], "label": profile["label"],
                "hardwareGpuCount": len(h.get("gpus", [])), "device": device, "deviceIndex": usable[0]["index"] if device == "cuda" else 0, "cpuThreads": threads, "workers": workers, "ramBudgetMiB": ram,
                "gpus": usable if device == "cuda" else [], "warning": warning}

    def status(self):
        saved = self.store.read()
        snapshot = self.capabilities.snapshot()
        return {"ok": True, **saved, "effective": self.resolve(snapshot, saved), "hardware": snapshot,
                "choices": {"profiles": self.registry["profiles"], "devices": self.registry["devices"],
                            "limits": self.registry["limits"]},
                "notice": "ค่ามีผลกับการโหลดงานครั้งถัดไป บางค่าเธรดต้องเปิดตัวช่วยเสียงใหม่ งานที่เปิดอยู่ยังใช้ค่าเดิม งบหน่วยความจำช่วยตรวจความพร้อมและเลือกวิธีโหลด ไม่ใช่เพดานการใช้ทั้งหมด"}

    def client_data(self):
        return self.registry["browser"]

    def child_environment(self):
        return {**os.environ, "MICE_RESOURCE_SETTINGS": str(self.settings_path),
                "MICE_RESOURCE_REGISTRY": str(self.registry_path)}
