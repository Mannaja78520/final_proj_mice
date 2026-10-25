"""Adaptive choices and writes use real production modules, without loading AI."""
import concurrent.futures
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch
import urllib.error
import urllib.request

import qc as F

AREA = "tools"
TITLE = "machine budgets are configurable, portable and independent of browser rendering"


def run(t):
    sys.path.insert(0, str(F.CODE / "main_python"))
    from resource_policy import ResourcePolicy
    from resource_hardware import Capabilities
    from resource_settings import StaleSettings
    with tempfile.TemporaryDirectory(prefix="mice_resources_") as folder:
        store = Path(folder) / "persistent/settings.json"
        weak = {"logicalCpus": 2, "memoryMiB": 4096, "availableMemoryMiB": 3000, "gpus": []}
        strong = {"logicalCpus": 24, "memoryMiB": 32768, "availableMemoryMiB": 24000,
                  "gpus": [{"index": 0, "name": "Synthetic GPU", "totalMiB": 12288, "freeMiB": 10000}]}
        manager = ResourcePolicy(F.CODE / "config/resource_policy.json", store,
                                 Capabilities(probe=lambda: strong))
        t.eq(manager.resolve(weak)["profile"], "light", "a weaker PC chooses the light budget")
        full = manager.resolve(strong)
        t.eq(full["profile"], "fast", "a stronger PC chooses its configured capacity tier")
        t.ok(full["cpuThreads"] < 24 and full["gpus"][0]["budgetMiB"] < 10000,
             "automatic mode leaves CPU and graphics memory for other work")
        busy = {**strong, "availableMemoryMiB": 1000, "gpus": [{**strong["gpus"][0], "freeMiB": 1000}]}
        t.eq(manager.resolve(busy)["profile"], "fast", "transient load does not oscillate the capacity tier")
        t.eq(manager.resolve(busy)["device"], "cpu", "unavailable graphics memory selects the CPU fallback")
        unknown = manager.resolve({"logicalCpus": 1, "memoryMiB": None, "availableMemoryMiB": None, "gpus": []})
        t.ok(unknown["profile"] == "light" and unknown["ramBudgetMiB"] is None,
             "unknown memory remains unknown and gets a conservative profile")
        cfg = manager.store.read()["settings"]
        for key, value in [("mode", "invented"), ("device", "invented"), ("cpuThreads", True),
                           ("workers", float("nan")), ("ramReserveMiB", -1)]:
            try:
                manager.validate({**cfg, key: value})
            except ValueError:
                rejected = True
            else:
                rejected = False
            t.ok(rejected, "invalid resource setting is refused: " + key)
        saved = manager.store.save({**cfg, "device": "cpu", "cpuThreads": 256}, "default")
        t.eq(manager.resolve(weak)["cpuThreads"], 1, "manual thread requests are bounded by the actual CPU")
        t.eq(manager.resolve(strong)["device"], "cpu", "explicit CPU choice cannot return to an unrestricted GPU path")
        original = store.read_bytes()
        with patch("resource_settings.os.replace", side_effect=PermissionError("fixture write denied")):
            try:
                manager.store.save({**cfg, "mode": "light"}, saved["revision"])
            except PermissionError:
                pass
        t.eq(store.read_bytes(), original, "failed atomic persistence retains the previous exact bytes")
        def change(mode):
            try:
                manager.store.save({**cfg, "mode": mode}, saved["revision"])
                return "saved"
            except StaleSettings:
                return "stale"
        with concurrent.futures.ThreadPoolExecutor(2) as pool:
            results = list(pool.map(change, ["light", "balanced"]))
        t.eq(sorted(results), ["saved", "stale"], "simultaneous stale-tab writes cannot overwrite each other")
        store.write_text("{broken", encoding="utf-8")
        damaged = manager.store.read()
        t.ok(damaged["warning"] and damaged["settings"] == cfg,
             "invalid local settings expose a warning and retain safe defaults")
        t.eq(store.read_text(), "{broken", "reading invalid settings never repairs or discards the user's file")
        store.unlink()
        # Failed discovery is cached too; repeatedly opening settings does not spawn probes.
        probes = []
        def unavailable():
            probes.append(1)
            raise OSError("fixture unavailable")
        cached = Capabilities(probe=unavailable)
        cached.snapshot(); cached.snapshot()
        t.eq(len(probes), 1, "failed capability discovery is cached")
        # Real Voice adapter: both normal fallback and lazy CPU recovery receive budgets.
        spec = importlib.util.spec_from_file_location("voice_resource_adapter", F.CODE / "apps/voice/resources.py")
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        voice = module.VoiceResources.__new__(module.VoiceResources)
        voice.policy, voice.resident = manager, {}
        calls = []
        def model(name, **options):
            calls.append((name, options))
            if options["device"] != "cpu":
                raise RuntimeError("fixture CUDA unavailable")
            return SimpleNamespace(model=SimpleNamespace(device="cpu"))
        voice.whisper("selected-model", model)
        t.ok([p[1]["device"] for p in calls] == ["cuda", "auto", "cpu"] and
             all(p[0] == "selected-model" and p[1]["cpu_threads"] == full["cpuThreads"] for p in calls),
             "Voice preserves the selected model and limits every CUDA/CPU fallback")
        calls.clear(); voice.whisper("language-specialist", model, force_cpu=True)
        t.ok(len(calls) == 1 and calls[0][1]["num_workers"] == full["workers"],
             "lazy specialist CPU recovery keeps the same worker budget")
        t.ok(not voice.status()["pending"], "resident model revision initially matches requested settings")
        manager.store.save({**cfg, "mode": "light"}, "default")
        t.ok(voice.status()["pending"] and len(voice.resident) == 2,
             "saving new settings marks resident models pending without unloading them")
        voice.clear()
        t.ok(not voice.status()["pending"], "unloaded models release their applied revision records")
        # Actual Hub API uses an isolated writable store, never the PC's real settings.
        base, _main = F.start_hub()
        import hub_api_resources
        previous = hub_api_resources._policy
        hub_api_resources._policy = manager
        try:
            try:
                urllib.request.urlopen(urllib.request.Request(base + "/api/resources", data=b"{}"), timeout=10)
            except urllib.error.HTTPError as exc:
                code = exc.code
            else:
                code = 200
            t.eq(code, 401, "resource writes are gated on the server before body handling")
            F.login(base)
            current = json.loads(F.get(base + "/api/resources")[1])
            data = {"revision": current["revision"], "settings": {**cfg, "mode": "balanced"}}
            t.eq(F.post(base + "/api/resources", json.dumps(data).encode())[0], 200,
                 "authenticated resource settings persist through the real API")
            t.eq(F.post(base + "/api/resources", json.dumps(data).encode())[0], 409,
                 "the real API refuses a stale settings revision")
            request = urllib.request.Request(base + "/api/resources", data=json.dumps(data).encode(),
                                             headers={"Cookie": F._cookie[0], "Origin": "http://other.invalid"})
            try:
                urllib.request.urlopen(request, timeout=10)
            except urllib.error.HTTPError as exc:
                code = exc.code
            else:
                code = 200
            t.eq(code, 403, "a different browser origin cannot write machine settings")
            script = F.get(base + "/mice.js")[1]
            if isinstance(script, bytes):
                script = script.decode()
            t.ok(script.index("MiceResourceRegistry") < script.index("class MiceResourceClient"),
                 "client presets and policy exist synchronously before the app starts")
            t.ok("Synthetic GPU" not in script and str(store) not in script,
                 "public browser bootstrap excludes machine inventory and private paths")
        finally:
            hub_api_resources._policy = previous
    node = shutil.which("node")
    t.ok(bool(node), "Node is available for actual client-policy fixtures")
    if node:
        ran = subprocess.run([node, str(F.CODE / "qc/data/resource_policy.js")], cwd=F.CODE,
                             capture_output=True, text=True, encoding="utf-8", timeout=30)
        for line in ran.stdout.splitlines():
            if line.startswith(("PASS ", "FAIL ")):
                t.ok(line.startswith("PASS "), line[5:])
        t.ok(ran.returncode == 0, "actual browser-policy fixtures finish", ran.stderr[-1000:])
