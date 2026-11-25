"""Voice uses the GPU it has, and a question never waits on the camera look.

PC 2026-11-25 (docs/experiments/experiment-records.md, "all apps at once"):
* torch on the PC is the CPU build, so Whisper's GPU check (torch.cuda) said
  "no GPU" and all three Whisper models loaded on CPU int8: STT 3.09 s per
  clip. CTranslate2 (what Whisper really runs on) saw the GPU fine. Fix:
  VoiceResources._stt_cuda_runtime asks CTranslate2. After: 0.75 s.
* cublas64_12.dll came from torch/lib only; the pip nvidia-cublas-cu12 wheel
  is found now by service._add_nvidia_wheel_dlls.
* Every POST /ask first looked up who is at the camera, synchronously:
  3.07 s vs 0.73 s with a name given. The look runs on a worker now and is
  started already on /transcribe; /ask waits at most face.askWaitSeconds.
"""
import sys
import threading
import time
import types
from pathlib import Path

import qc as F

AREA = "voice"
TITLE = "voice: Whisper GPU check follows CTranslate2; /ask does not wait for the face look"


def run(t):
    run_vendors(t)
    sys.path.insert(0, str(F.CODE / "apps" / "voice"))
    import resources
    import face_link

    vr = resources.VoiceResources.__new__(resources.VoiceResources)
    cpu_torch = types.SimpleNamespace(cuda=types.SimpleNamespace(is_available=lambda: False))
    gpu_ct2 = types.SimpleNamespace(get_cuda_device_count=lambda: 1)
    no_ct2 = types.SimpleNamespace(get_cuda_device_count=lambda: 0)
    saved = {k: sys.modules.get(k) for k in ("torch", "ctranslate2")}
    try:
        sys.modules["torch"], sys.modules["ctranslate2"] = cpu_torch, gpu_ct2
        got = vr._stt_cuda_runtime()
        t.ok(got is None, "CPU-only torch + CTranslate2 GPU -> trust the GPU (None)",
             "got %r: Whisper would fall to CPU int8 again (3.09 s vs 0.75 s per clip)" % (got,))
        sys.modules["ctranslate2"] = no_ct2
        got = vr._stt_cuda_runtime()
        t.ok(got is cpu_torch.cuda, "no CUDA anywhere -> keep torch's no-GPU answer", "got %r" % (got,))
        plan = {"device": "cuda", "hardwareGpuCount": 1, "deviceIndex": 0,
                "gpus": [{"index": 0, "uuid": "x", "budgetMiB": 8000}]}
        sys.modules["ctranslate2"] = gpu_ct2
        t.ok(vr.verify_gpus(plan, vr._stt_cuda_runtime())["device"] == "cuda",
             "single GPU plan stays cuda for Whisper", "plan fell to cpu")
    finally:
        for k, v in saved.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v

    src = (F.CODE / "apps" / "voice" / "service.py").read_text(encoding="utf-8")
    t.ok("_add_nvidia_wheel_dlls()" in src and "prefetch_person()" in src,
         "service finds pip nvidia DLLs and starts the face look on /transcribe",
         "one of the two calls is missing from apps/voice/service.py")

    class Slow(face_link.FaceLink):
        def __init__(self):
            self.cfg = {"face": {"askWaitSeconds": 0.3, "askStaleSeconds": 30}}
            self.looks = 0

        def _query_faces_service(self, camera=""):
            self.looks += 1
            time.sleep(1.5)
            return "Somchai"

    face_link.faces_on, real_on = (lambda cfg: True), face_link.faces_on
    try:
        f = Slow()
        t0 = time.time()
        first = f.get_detected_person()
        took = time.time() - t0
        t.ok(took < 0.8, "first /ask waits at most the deadline, not the 1.5 s look",
             "took %.2f s, name %r" % (took, first))
        time.sleep(1.6)
        again = f.get_detected_person()
        t.ok(again == "Somchai", "next question gets the name the look found", "got %r" % (again,))
        f2 = Slow()
        f2.prefetch_person()
        time.sleep(1.6)
        t0 = time.time()
        named = f2.get_detected_person()
        t.ok(named == "Somchai" and time.time() - t0 < 0.8,
             "a look started while hearing gives /ask the name with no wait",
             "got %r in %.2f s" % (named, time.time() - t0))
        t.ok(f2.looks <= 2 and threading.active_count() < 50, "one look at a time, no thread pile-up",
             "looks=%d" % f2.looks)
    finally:
        face_link.faces_on = real_on


def run_vendors(t):
    """AMD and Intel GPUs are told apart from NVIDIA by data (config/gpu_vendors.json)."""
    sys.path.insert(0, str(F.CODE / "main_python"))
    sys.path.insert(0, str(F.CODE / "tools"))
    import resource_hardware as hw
    import ollama_serve
    got = {a["name"]: a for a in hw.classify_adapters(
        ["NVIDIA GeForce RTX 5070 Ti Laptop GPU", "AMD Radeon RX 7800 XT", "Intel(R) UHD Graphics",
         "Microsoft Basic Render Driver", "Parsec Virtual Display Adapter"])}
    t.ok(len(got) == 3, "virtual/basic adapters are ignored", "got %s" % list(got))
    t.ok(got["NVIDIA GeForce RTX 5070 Ti Laptop GPU"]["cudaRuntime"], "NVIDIA can run CUDA", "")
    amd = got["AMD Radeon RX 7800 XT"]
    t.ok(amd["vendor"] == "amd" and not amd["cudaRuntime"] and amd["ollamaEnv"].get("OLLAMA_VULKAN") == "1"
         and amd["sttBackend"] == "cpu", "AMD: no CUDA, Ollama via Vulkan, Whisper on CPU", "got %r" % amd)
    real = hw.adapter_names
    try:
        hw.adapter_names = lambda: ["AMD Radeon RX 7800 XT"]
        t.ok(ollama_serve._vendor_env({}).get("OLLAMA_VULKAN") == "1", "AMD-only PC starts Ollama with Vulkan", "")
        t.ok(ollama_serve._vendor_env({"gpuBackend": "off"}) == {}, "gpuBackend off leaves Ollama alone", "")
        hw.adapter_names = lambda: ["AMD Radeon RX 7800 XT", "NVIDIA GeForce RTX 4060"]
        t.ok(ollama_serve._vendor_env({}) == {}, "NVIDIA present: Ollama keeps its CUDA default", "")
    finally:
        hw.adapter_names = real
