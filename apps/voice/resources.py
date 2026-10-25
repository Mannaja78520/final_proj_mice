"""Apply the shared machine policy only when a Voice model is actually loaded."""
import os
from pathlib import Path
import sys


class VoiceResources:
    def __init__(self, code):
        code = Path(code)
        shipped = Path(__file__).resolve().parents[2]
        sys.path.insert(0, str(shipped / "main_python"))
        from resource_policy import ResourcePolicy
        self.policy = ResourcePolicy(os.environ.get("MICE_RESOURCE_REGISTRY") or shipped / "config/resource_policy.json",
                                     os.environ.get("MICE_RESOURCE_SETTINGS") or code / ".local/resource_settings.json")
        self.resident = {}

    def whisper(self, model, factory, force_cpu=False):
        plan = self.policy.resolve()
        attempts = [("cpu", "int8")]
        if not force_cpu and plan["device"] == "cuda":
            attempts = [("cuda", "float16"), ("auto", "auto")] + attempts
        error = None
        for device, compute in attempts:
            try:
                loaded = factory(model, device=device, compute_type=compute,
                                 cpu_threads=plan["cpuThreads"], num_workers=plan["workers"],
                                 device_index=plan["deviceIndex"] if device != "cpu" else 0)
                actual = getattr(getattr(loaded, "model", None), "device", device)
                self.mark("stt:" + model, plan, str(actual), compute)
                return loaded
            except Exception as exc:
                error = exc
        raise error

    def torch_plan(self, torch):
        plan = self.policy.resolve()
        torch.set_num_threads(plan["cpuThreads"])
        # Never change inter-op threads after Torch has started parallel work.
        if not hasattr(self, "_interop_set"):
            try:
                torch.set_num_interop_threads(plan["workers"])
            except RuntimeError:
                pass
            self._interop_set = True
        if not torch.cuda.is_available():
            plan = {**plan, "device": "cpu", "gpus": []}
        memory = {g["index"]: str(g["budgetMiB"]) + "MiB" for g in plan["gpus"]
                  if g["index"] < torch.cuda.device_count()}
        if plan["ramBudgetMiB"] is not None:
            memory["cpu"] = str(max(1, plan["ramBudgetMiB"])) + "MiB"
        return plan, memory

    def mark(self, key, plan, device, compute=""):
        self.resident[key] = {**plan, "actualDevice": device, "compute": compute}

    def status(self):
        requested = self.policy.store.read()
        return {"requestedRevision": requested["revision"], "requested": requested["settings"],
                "loaded": dict(self.resident),
                "pending": any(p["revision"] != requested["revision"] for p in self.resident.values()),
                "warning": requested["warning"],
                "notice": "การเปลี่ยนค่ามีผลเมื่อโหลดโมเดลครั้งถัดไป"}

    def workers(self, maximum):
        return max(1, min(maximum, self.policy.resolve()["workers"]))

    def clear(self):
        self.resident.clear()
