# All apps at once: speed, GPU, RAM (2026-11-25)

Owner: claude (thread cmsg_01R7BbYxaTb3Yv9YS3gQaaA3MfPQXswnhS8juMgMuyVc2P)
Updated: 2026-11-25
Branch: claude/project-thread-yzc9lu
Last commit: see git log
Plan: none (user ask 2026-11-25)

## Goal
All apps (hub, voice, face, camera) at once on the PC, fast, GPU used well, CPU fallback, AMD too, no quality loss.

## Blocked
- nothing
Ask (user, own words): ทุกอย่างรันพร้อมกันได้โดยไม่มีปัญหา กล้อง ประสิทธิภาพสูงสุด GPU decode/encode, voice ใช้พร้อม facereg, CPU backup, dynamic; ไม่ลดคุณภาพ; report มีรูป

## Doing now
Rerunning full QC after fixing systems map, template fields, check_voice_view.

## Done
- tools/perf_profile.py + tools/perf_load.py (+ config) measure every app alone and together.
- Whisper back on GPU (CTranslate2 probe + pip nvidia-cublas-cu12 DLL path): STT 3.09 s -> 0.75 s.
- /ask no longer blocks on the face look (worker + prefetch on /transcribe): 2.6 s -> 0.06 s median.
- Rejected: Whisper int8_float16 (text only 72% same as float16).

- AMD/Intel support: config/gpu_vendors.json, resource_hardware.classify_adapters, plan "accelerators", ollama_serve gpuBackend (Vulkan). Whisper stays CPU there. Not tested on real AMD.

## Facts found
- PC torch is 2.15.0+cpu; ctranslate2 4.8.2 has CUDA; cublas64_12.dll came only from torch/lib.
- apps/voice/face_link.py get_detected_person was synchronous per /ask (~2.3 s).
- GPU enc/dec engines 0% at all times: camera relay is MJPEG passthrough/CPU.

## File status
| File | Change | State | Verification | Commit |
|---|---|---|---|---|
| apps/voice/resources.py | Whisper CUDA probe via CTranslate2 | done | check voice_gpu_and_ask_speed + sabotage 2/2 | this checkpoint |
| apps/voice/service.py | pip nvidia DLL dirs; prefetch on /transcribe | done | same | this checkpoint |
| apps/voice/face_link.py | person look on worker, deadline | done | same | this checkpoint |
| qc/checks/check_voice_gpu_and_ask_speed.py | new check | done | QC quiet PASS | this checkpoint |
| main_python/resource_hardware.py, resource_policy.py, tools/ollama_serve.py, config/gpu_vendors.json, config/local_ai.json | AMD/Intel detection | done | check voice_gpu_and_ask_speed (fakes) | this checkpoint |
| tools/perf_profile.py, tools/perf_load.py | new tools | done | run on PC | this checkpoint |
| config/perf_profile.json, config/perf_load.json | tool data | done | run on PC | this checkpoint |

## Next
Charts, report, friend doc, experiment-records, full QC, PR, merge.
