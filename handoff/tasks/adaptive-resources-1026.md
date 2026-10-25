# Adaptive PC and browser resource policy

Owner: codex:10241515-audit
Updated: 2026-10-26T01:28:48.309454+07:00
Branch: codex/adaptive-resources-1026
Tree: E:/final_proj/mice/code/.staging-adaptive-resources-1026
Last commit: this checkpoint; baseline69fd19ed
Plan: A48-18 (robot); related A48-13 assessment/hardwarepause

## Goal
User: dynamically suit weaker/stronger future PCs and allow customization, including Hubsoftware CPU/GPU/RAM and client rendering. Preserve manual model/character choices, userdata/dirtyroot and physical pause.

## Doing now
Before runtime edits: Codex-first same-provider independent design consultation per COORDINATION supported-agent route. Propose data-driven shared capability/profile service, persistent machine-local settings, bounded cached probes, gated settings API/UI, effective Voice compute/thread/memory settings, separately client-local Studio render policy. Preserve existing dirty-only rendering, link RTT adaptation, safety/collision/motion timing and provider fallback. No models downloaded/loaded or hardware probed by detection. Read-only quality assessment also found Lift missing traveldeadline (separate issue), Hub denied-storage startup fault (fix in this UI step). No runtime/service cutover.

## File status
Planned exactpaths; final design may narrow these. No runtime files changed yet.

| File | Change | State | Verification | Commit |
| --- | --- | --- | --- | --- |
| config/resource_policy.json | Adaptive resource implementation/docs/checks or generated output | pending | not run | uncommitted |
| main_python/resource_policy.py | Adaptive resource implementation/docs/checks or generated output | pending | not run | uncommitted |
| main_python/hub_api_resources.py | Adaptive resource implementation/docs/checks or generated output | pending | not run | uncommitted |
| main_python/main.py | Adaptive resource implementation/docs/checks or generated output | pending | not run | uncommitted |
| apps/voice/resources.py | Adaptive resource implementation/docs/checks or generated output | pending | not run | uncommitted |
| apps/voice/service.py | Adaptive resource implementation/docs/checks or generated output | pending | not run | uncommitted |
| shared/web/resources.js | Adaptive resource implementation/docs/checks or generated output | pending | not run | uncommitted |
| main_python/web/home/parts/settings.html | Adaptive resource implementation/docs/checks or generated output | pending | not run | uncommitted |
| main_python/web/home/parts/settings.js | Adaptive resource implementation/docs/checks or generated output | pending | not run | uncommitted |
| main_python/web/home/parts/boot_scans.js | Adaptive resource implementation/docs/checks or generated output | pending | not run | uncommitted |
| main_python/web/help/parts/hub.html | Adaptive resource implementation/docs/checks or generated output | pending | not run | uncommitted |
| main_python/web/help/parts/voice.html | Adaptive resource implementation/docs/checks or generated output | pending | not run | uncommitted |
| main_python/web/hub.html | Adaptive resource implementation/docs/checks or generated output | pending | not run | uncommitted |
| main_python/web/help.html | Adaptive resource implementation/docs/checks or generated output | pending | not run | uncommitted |
| nong/main_python_set_nong/web/app_parts/scene.js | Adaptive resource implementation/docs/checks or generated output | pending | not run | uncommitted |
| nong/main_python_set_nong/web/app_parts/main_loop.js | Adaptive resource implementation/docs/checks or generated output | pending | not run | uncommitted |
| nong/main_python_set_nong/web/app.js | Adaptive resource implementation/docs/checks or generated output | pending | not run | uncommitted |
| qc/checks/check_resource_policy.py | Adaptive resource implementation/docs/checks or generated output | pending | not run | uncommitted |
| qc/data/resource_policy.js | Adaptive resource implementation/docs/checks or generated output | pending | not run | uncommitted |
| docs/systems.json | Adaptive resource implementation/docs/checks or generated output | pending | not run | uncommitted |
| docs/systems/hub-web.md | Adaptive resource implementation/docs/checks or generated output | pending | not run | uncommitted |
| docs/systems/app-voice.md | Adaptive resource implementation/docs/checks or generated output | pending | not run | uncommitted |
| docs/systems/shared-web.md | Adaptive resource implementation/docs/checks or generated output | pending | not run | uncommitted |
| docs/systems/studio.md | Adaptive resource implementation/docs/checks or generated output | pending | not run | uncommitted |
| docs/systems/qc.md | Adaptive resource implementation/docs/checks or generated output | pending | not run | uncommitted |
| handoff/tasks/adaptive-resources-1026.md | Adaptive resource implementation/docs/checks or generated output | pending | not run | uncommitted |

## Facts found
- Root69fd19ed accepted prior8335/0 (one gesturecrowdretry2/2), not proof of upcomingpolicy.
- CurrentPC Ultra9 275HX24cores,31.4GiB RAM, RTX5070TiLaptop12227MiB VRAM. Snapshot only, no full-load utilization proof.
- Voice already CUDA16/CPUint8 fallback, local LLM GPU/4bit/CPU paths, speechcache; use existing mechanisms and don't equate100%utilization with success.
- Studio already dirty-renders and RTT-adapts link; safe planning yields under budgets. Client can be weaker than Hub, so resolve separately.
- Frozen assets via asset(); writable machine settings must live under DATA, not PyInstaller _MEIPASS. Local settings never modify registry defaults or characterconfig.

## Done
Read-only initial assessment, isolated tree established; no source edits/build/QC/device activity yet.

## Next
1. Complete independent design review; implement bounded modular policy and Help parity.
2. Actual integration/regression/browser checks, deliberate reversions, final independent review and stable full.
3. Spec package/archive verification and guarded PR/sourceintegration preserving rootdirtywork. Hardware remains paused.

## Blocked
Physical tests USER-NOTREADY; elbowtrim user-deferred. No software blocker. No device/service/runtime changes authorized by adaptation task.
