"""Shared machine budgets for Voice loads, native threads and translation jobs."""
import concurrent.futures
import os
from pathlib import Path
import sys
import threading


class VoiceResources:
    def __init__(self, code):
        code = Path(code)
        shipped = Path(__file__).resolve().parents[2]
        sys.path.insert(0, str(shipped / "main_python"))
        from resource_policy import ResourcePolicy
        self.resident = {}
        self.warning = ""
        try:
            self.policy = ResourcePolicy(os.environ.get("MICE_RESOURCE_REGISTRY") or shipped / "config/resource_policy.json",
                                         os.environ.get("MICE_RESOURCE_SETTINGS") or code / ".local/resource_settings.json")
        except (OSError, ValueError, KeyError, TypeError):
            self.policy = None
            self.warning = "อ่านนโยบายประสิทธิภาพไม่ได้ ใช้ CPU แบบประหยัดชั่วคราว"

    def plan(self, fresh=False):
        if self.policy is not None:
            return self.policy.resolve(snapshot=self.policy.capabilities.snapshot(force=fresh))
        return {"revision":"unavailable", "profile":"fallback", "device":"cpu", "deviceIndex":0,
                "cpuThreads":1, "workers":1, "ramBudgetMiB":None, "gpus":[], "warning":self.warning}

    def admit(self, plan, workload, device="cpu"):
        key = workload + ("Cuda" if device.startswith("cuda") else "Cpu")
        minimum = self.policy.registry["minimumLoadMiB"][key] if self.policy is not None else None
        available = next((g["budgetMiB"] for g in plan["gpus"] if device == "cuda:" + str(g["index"])), None) if device.startswith("cuda") else plan["ramBudgetMiB"]
        if minimum is None or available is None or available < minimum:
            raise MemoryError("หน่วยความจำที่เหลือยังไม่พอหรืออ่านไม่ได้ เลือกโมเดลเล็กลงหรือปรับหน่วยความจำสำรอง")

    def cpu_options(self, plan, estimated_mib=None):
        self.admit(plan, "llm")
        # Only CPU is eligible. Accelerate must reject a model that cannot fit;
        # no unrestricted CPU/GPU allocation or disk offload fallback.
        if estimated_mib is not None and estimated_mib * self.policy.registry["loadHeadroom"] > plan["ramBudgetMiB"]:
            raise MemoryError("โมเดลที่เลือกใหญ่กว่างบ RAM เลือกโมเดลเล็กลงหรือปรับหน่วยความจำสำรอง")
        return {"device_map":{"":"cpu"}, "max_memory":{"cpu":str(plan["ramBudgetMiB"])+"MiB"}}

    def cpu_load(self, model, factory, config_factory, torch, plan):
        self.admit(plan, "llm")
        from accelerate import init_empty_weights
        configuration = config_factory.from_pretrained(model, trust_remote_code=True)
        with init_empty_weights(include_buffers=True):
            empty = factory.from_config(configuration, torch_dtype=torch.float32, trust_remote_code=True)
        tensors = list(empty.parameters()) + list(empty.buffers())
        estimate = sum(p.numel() * p.element_size() for p in tensors) / 1048576
        options = self.cpu_options(plan, estimate)
        del empty, tensors
        return factory.from_pretrained(model, torch_dtype=torch.float32, low_cpu_mem_usage=True,
                                       trust_remote_code=True, **options)

    def whisper(self, model, factory, force_cpu=False):
        plan = self.plan(fresh=True)
        if plan["device"] == "cuda":
            runtime = sys.modules.get("torch")
            plan = self.verify_gpus(plan, getattr(runtime, "cuda", None))
        attempts = [("cpu", "int8")]
        if not force_cpu and plan["device"] == "cuda":
            attempts = [("cuda", "float16")] + attempts
        error = None
        for device, compute in attempts:
            try:
                selected_device = "cuda:" + str(plan["deviceIndex"]) if device != "cpu" else "cpu"
                self.admit(plan, "stt", selected_device)
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
        plan = self.plan(fresh=True)
        if not hasattr(self, "_torch_applied"):
            torch.set_num_threads(plan["cpuThreads"])
            try:
                torch.set_num_interop_threads(plan["workers"])
            except RuntimeError:
                pass
            self._torch_applied = {"threads":torch.get_num_threads(), "interop":torch.get_num_interop_threads()}
        applied = self._torch_applied
        plan = {**plan, "torchThreads":applied["threads"], "torchInteropThreads":applied["interop"],
                "restartRequired":applied["threads"] != plan["cpuThreads"] or applied["interop"] != plan["workers"]}
        plan = self.verify_gpus(plan, torch.cuda)
        memory = {g["index"]:str(g["budgetMiB"])+"MiB" for g in plan["gpus"]}
        if plan["ramBudgetMiB"] is not None:
            memory["cpu"] = str(max(1, plan["ramBudgetMiB"]))+"MiB"
        return plan, memory

    def verify_gpus(self, plan, cuda):
        valid = []
        if cuda is None:
            # One physical GPU has no ordering ambiguity. For multiple GPUs,
            # require runtime UUID verification rather than guessing an index.
            valid = plan["gpus"] if plan.get("hardwareGpuCount", 1) == 1 else []
        else:
            try:
                if cuda.is_available():
                    devices = []
                    for i in range(cuda.device_count()):
                        uuid = str(getattr(cuda.get_device_properties(i), "uuid", "")).lower().replace("gpu-", "").replace("-", "")
                        devices.append((i, uuid))
                    for g in plan["gpus"]:
                        wanted = g.get("uuid", "").lower().replace("gpu-", "").replace("-", "")
                        matches = [i for i,uuid in devices if uuid and wanted and uuid == wanted]
                        if len(matches) == 1:
                            valid.append({**g,"index":matches[0]})
                        elif plan.get("hardwareGpuCount", 1) == 1 and len(devices) == 1:
                            valid.append({**g,"index":0})
            except (AttributeError, RuntimeError):
                valid = []
        updated = {**plan,"gpus":valid,"device":"cuda" if valid and plan["device"] == "cuda" else "cpu"}
        if valid: updated["deviceIndex"] = valid[0]["index"]
        elif plan["device"] == "cuda": updated["warning"] = "ยืนยัน GPU ที่พร้อมใช้ไม่ได้ จึงใช้ CPU"
        return updated

    def pick_device(self, plan, requested):
        if requested == "cpu" or plan["device"] != "cuda":
            return "cpu"
        if requested.startswith("cuda:"):
            if any(requested == "cuda:"+str(g["index"]) for g in plan["gpus"]):
                return requested
            return "cpu"
        return "cuda:"+str(plan["deviceIndex"])

    def records_lock(self):
        return self.__dict__.setdefault("_record_lock", threading.RLock())

    def mark(self, key, plan, device, compute=""):
        with self.records_lock():
            self.resident[key] = {**plan, "actualDevice":device, "compute":compute}

    def drop(self, kind):
        with self.records_lock():
            self.resident = {k:v for k,v in self.resident.items() if not k.startswith(kind+":")}

    def status(self):
        requested = self.policy.store.read() if self.policy is not None else {"revision":"unavailable", "settings":{}, "warning":self.warning}
        with self.records_lock():
            loaded = dict(self.resident)
        pending = any(p["revision"] != requested["revision"] or p.get("restartRequired") for p in loaded.values())
        jobs = getattr(self, "_jobs_plan", None)
        if jobs and jobs["revision"] != requested["revision"]: pending = True
        return {"requestedRevision":requested["revision"], "requested":requested["settings"], "loaded":loaded,
                "translationPool":jobs, "pending":bool(pending), "warning":requested["warning"],
                "notice":"ค่ามีผลเมื่อโหลดโมเดลครั้งถัดไป เธรดและงานแปลที่เปิดแล้วต้องเปิดตัวช่วยเสียงใหม่"}

    def map(self, function, items):
        # One shared pool across HTTP requests; callers never nest this pool.
        lock = self.__dict__.setdefault("_jobs_lock", threading.Lock())
        with lock:
            if not hasattr(self, "_jobs"):
                self._jobs_plan = self.plan()
                self._jobs = concurrent.futures.ThreadPoolExecutor(max_workers=self._jobs_plan["workers"])
            pool = self._jobs
        return list(pool.map(function, items))

    def clear(self):
        with self.records_lock():
            self.resident.clear()
