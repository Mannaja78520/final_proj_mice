"""Adaptive choices and writes use real production modules, without loading AI."""
import concurrent.futures
import ast
import io
import contextlib
import threading
import importlib.util
import json
import os
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
        t.ok([p[1]["device"] for p in calls] == ["cuda", "cpu"] and
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
        # Admission and native-thread settings remain honest across future loads.
        exhausted = manager.resolve({**strong, "availableMemoryMiB": 1000})
        try:
            voice.cpu_options(exhausted)
        except MemoryError:
            blocked = True
        else:
            blocked = False
        t.ok(blocked, "an exhausted CPU memory budget rejects a new LLM before weight allocation")
        cpu_options = voice.cpu_options(full)
        t.eq(set(cpu_options["max_memory"]), {"cpu"}, "the CPU placement fallback cannot re-enable an unrestricted GPU")
        mapped = manager.resolve({**strong, "gpus":[{**strong["gpus"][0], "index":1}], "visibleDevices":"1"})
        t.ok(mapped["gpus"][0]["index"] == 0 and mapped["gpus"][0]["physicalIndex"] == 1,
             "CUDA visibility maps the selected physical GPU to its logical device")
        two = {**full, "gpus":[{**full["gpus"][0], "index":0},{**full["gpus"][0], "index":1}]}
        t.eq(voice.pick_device(two, "cuda:1"), "cuda:1", "explicit Spark GPU selection is preserved")
        t.eq(voice.pick_device(full, "cuda:9"), "cpu", "an unavailable explicit Spark device falls back safely")
        voice.mark("stt:discarded", full, "cpu"); voice.mark("llm:kept", full, "cpu"); voice.drop("stt")
        t.ok("stt:discarded" not in voice.resident and "llm:kept" in voice.resident,
             "discarded STT and specialist records do not remain resident")
        state = {"threads":1, "interop":1}
        torch = SimpleNamespace(set_num_threads=lambda n:state.update(threads=n),
                                set_num_interop_threads=lambda n:state.update(interop=n),
                                get_num_threads=lambda:state["threads"], get_num_interop_threads=lambda:state["interop"],
                                cuda=SimpleNamespace(is_available=lambda:False))
        initial,_ = voice.torch_plan(torch)
        current = manager.store.read()
        manager.store.save({**current["settings"], "workers":2, "cpuThreads":2}, current["revision"])
        later,_ = voice.torch_plan(torch)
        t.ok(later["restartRequired"] and later["torchInteropThreads"] == initial["torchInteropThreads"],
             "changed native worker settings report the actual old value and restart requirement")
        voice.mark("llm:new", later, "cpu")
        t.ok(voice.status()["pending"], "a new model revision cannot hide a process-global thread change")
        voice.clear()
        # Corrupt registry input has a controlled failure rather than breaking unrelated APIs.
        registry = json.loads((F.CODE / "config/resource_policy.json").read_text(encoding="utf-8"))
        bad_path = Path(folder)/"bad-registry.json"
        for mutate in [lambda r:r.update(probeSeconds=float("nan")),
                       lambda r:r["defaults"].update(workers=True),
                       lambda r:r["profiles"][0].update(workers=-2),
                       lambda r:r["browser"]["profiles"].append(r["browser"]["profiles"][0])]:
            bad = json.loads(json.dumps(registry)); mutate(bad); bad_path.write_text(json.dumps(bad),encoding="utf-8")
            try:
                ResourcePolicy(bad_path,store)
            except (ValueError,TypeError):
                rejected = True
            else:
                rejected = False
            t.ok(rejected, "malformed editable resource registry is rejected before use")
        # CPU admission counts metadata-only tensors before any model weights load.
        weight_loads = []
        model_factory = SimpleNamespace(from_config=lambda *a,**k:SimpleNamespace(
            parameters=lambda:[SimpleNamespace(numel=lambda:268435456, element_size=lambda:4)], buffers=lambda:[]),
            from_pretrained=lambda *a,**k:weight_loads.append(k) or SimpleNamespace(device="cpu"))
        config_factory = SimpleNamespace(from_pretrained=lambda *a,**k:object())
        metadata_calls=[]
        def empty_context(**kwargs):
            metadata_calls.append(kwargs)
            return contextlib.nullcontext()
        with patch.dict(sys.modules, {"accelerate":SimpleNamespace(init_empty_weights=empty_context)}):
            try:
                voice.cpu_load("explicit-model",model_factory,config_factory,SimpleNamespace(float32="float32"),
                               {**full,"ramBudgetMiB":512})
            except MemoryError:
                refused = True
            else:
                refused = False
            t.ok(refused and not weight_loads, "CPU fallback rejects oversized selected weights before allocation or disk offload")
            voice.cpu_load("explicit-model",model_factory,config_factory,SimpleNamespace(float32="float32"),
                           {**full,"ramBudgetMiB":4096})
            t.eq(weight_loads[0]["device_map"], {"":"cpu"}, "admitted CPU weights stay on CPU with no implicit offload")
            t.ok(all(c.get("include_buffers") is True for c in metadata_calls),
                 "metadata admission keeps registered buffers on meta as well as parameters")
        # Execute the shipped reload and translation methods without importing AI.
        syntax = ast.parse((F.CODE/"apps/voice/service.py").read_text(encoding="utf-8"))
        methods = {n.name:n for n in ast.walk(syntax) if isinstance(n,ast.FunctionDef) and n.name in ("maybe_reload","translate_all","do_translate")}
        def production(name, namespace):
            exec(compile(ast.Module(body=[methods[name]],type_ignores=[]),str(F.CODE/"apps/voice/service.py"),"exec"),namespace)
            return namespace[name]
        fresh_file=Path(folder)/"voice.json";fresh_file.write_text("{}")
        fresh={"stt":{"model":"new-stt"},"llm":{"model":"new-llm"}}
        reload_model=production("maybe_reload",{"registry":SimpleNamespace(load=lambda p:fresh)})
        brain=SimpleNamespace(cfg_path=fresh_file,_cfg_mtime=None,_lock=threading.RLock(),_resources=voice,
                              _stt_loaded_model="old-stt",_llm_loaded_model="old-llm")
        voice.mark("stt:old-stt",full,"cpu");voice.mark("stt:specialist",full,"cpu");voice.mark("llm:old-llm",full,"cpu")
        reload_model(brain)
        t.ok(not voice.resident and brain._stt is None and brain._llm is None,
             "actual model replacement removes primary, specialist and LLM resident records")
        translate=production("translate_all",{})
        lock=threading.Lock();release=threading.Event();filled=threading.Event();active=[0,0,0]
        budget=manager.resolve()["workers"]
        def translated(text,target,source):
            with lock:
                active[0]+=1;active[1]=max(active[1],active[0]);active[2]+=1
                if active[0]>=budget:filled.set()
            try:
                if not release.wait(5):raise TimeoutError("fixture release")
                return text+target,"fixture"
            finally:
                with lock:active[0]-=1
        brain=SimpleNamespace(_resources=voice,translate_text=translated)
        with concurrent.futures.ThreadPoolExecutor(2) as callers:
            pending=[callers.submit(translate,brain,"hello","en") for _ in range(2)]
            try:
                reached=filled.wait(4)
            finally:
                release.set()
            outputs=[future.result(timeout=5) for future in pending]
        t.ok(reached and active[1]<=budget and active[2]==6 and all(len(o)==4 for o in outputs),
             "simultaneous actual translations share one global bounded pool without nested deadlock")
        do_translate = production("do_translate", {"json":json})
        submits = []
        def tracked_map(fn,items):
            submits.append(1)
            return voice.map(fn,items)
        request_brain=SimpleNamespace(_resources=SimpleNamespace(map=tracked_map),
                                      translate_text=lambda *a,**k:("translated",""),translate=lambda text:("translated",""))
        for request in ({"text":"hello","target":"ja"},{"text":"สวัสดี"}):
            payload=json.dumps(request).encode()
            handler=SimpleNamespace(headers={"Content-Length":str(len(payload))},rfile=io.BytesIO(payload),
                                    brain=request_brain,_json=lambda data,*args:data)
            do_translate(handler)
        t.eq(len(submits),2,"single-target and legacy HTTP translations also enter the same bounded pool")
        reversed_cuda=SimpleNamespace(is_available=lambda:True,device_count=lambda:2,
                                     get_device_properties=lambda i:SimpleNamespace(uuid=["GPU-b","GPU-a"][i]))
        mapped_plan=voice.verify_gpus({**full,"hardwareGpuCount":2,"gpus":[{**full["gpus"][0],"uuid":"GPU-a","index":0}]},reversed_cuda)
        t.eq(mapped_plan["deviceIndex"],1,"runtime GPU UUIDs correct NVIDIA versus CUDA ordering")
        unavailable=voice.verify_gpus({**full,"hardwareGpuCount":2},None)
        t.eq(unavailable["device"],"cpu","ambiguous multi-GPU ordering falls back instead of guessing")
        # No implicit device=auto can bypass CPU admission after CUDA fails.
        exhausted_policy=ResourcePolicy(F.CODE/"config/resource_policy.json",Path(folder)/"exhausted.json",
                                        Capabilities(probe=lambda:{**strong,"availableMemoryMiB":1000}))
        spare=module.VoiceResources.__new__(module.VoiceResources);spare.policy=exhausted_policy;spare.resident={}
        attempted=[]
        def broken_cuda(name,**options):
            attempted.append(options["device"])
            raise RuntimeError("CUDA fixture refusal")
        with patch.dict(sys.modules,{"torch":None}):
            try:spare.whisper("selected",broken_cuda)
            except MemoryError:refused=True
            else:refused=False
        t.ok(refused and attempted==["cuda"],"failed CUDA cannot silently allocate a CPU STT model beyond its RAM budget")
        voice._jobs.shutdown(wait=True)
        # A standalone helper cannot import Python modules out of the Hub PYZ.
        bundle=Path(folder)/"bundle";data_root=Path(folder)/"writable"
        for relative in ("main_python/resource_policy.py","main_python/resource_hardware.py","main_python/resource_settings.py",
                         "config/resource_policy.json","apps/voice/resources.py"):
            target=bundle/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(F.CODE/relative,target)
        child_code = "import sys,json;from pathlib import Path;sys.path.insert(0,str(Path(sys.argv[1])/'apps/voice'));from resources import VoiceResources;r=VoiceResources(Path(sys.argv[1]));print(json.dumps({'settings':str(r.policy.settings_path),'revision':r.status()['requestedRevision'],'ai_imported':'torch' in sys.modules}))"
        env={**os.environ,"MICE_RESOURCE_REGISTRY":str(bundle/"config/resource_policy.json"),
             "MICE_RESOURCE_SETTINGS":str(data_root/".local/resource_settings.json")}
        child=subprocess.run([sys.executable,"-I","-c",child_code,str(bundle)],cwd=folder,env=env,
                             capture_output=True,text=True,encoding="utf-8",timeout=15)
        t.eq(child.returncode,0,"isolated packaged-layout Voice imports only its shipped raw shared modules")
        if child.returncode==0:
            result=json.loads(child.stdout)
            t.ok(result["settings"]==env["MICE_RESOURCE_SETTINGS"] and result["revision"]=="default" and not result["ai_imported"],
                 "packaged helper uses persistent DATA and imports no AI library during settings discovery")
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
