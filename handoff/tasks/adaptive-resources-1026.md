# Adaptive PC and browser resource policy

Owner: codex:10241515-audit
Updated: 2026-10-26T04:19:22.588407+07:00
Branch: codex/adaptive-resources-1026
Tree: E:/final_proj/mice/code/.staging-adaptive-resources-1026
Last commit: this checkpoint; baseline69fd19ed
Plan: A48-18 (robot); related A48-13 hardwarepause

## Goal
Dynamic configurable resource use on weaker/stronger future Hub PCs and browser clients. Preserve models, provider chain, dirtyroot and physical pause.

## Doing now
Full8418/0@f248802 qualified four parallel failures -> isolated2/2 each;994source+20CAD stable. Package11,463,270bytes built;11 exact asset payloads+4 native resource modules archive-verified, EXE never started/installed. Independent backend gate review accepted. Close only own task metadata next, selected metadata checks; PR then guarded root integration preserving all dirty user files and insert-only3module root spec merge. All runtime hashes frozen.

## File status
Verification: selected326/0 +77/0; nine deliberate regressions caught/restored. Affected1207/1 legacy fixture repaired;1253/1 generated headers refreshed; final selected270/0. Full8418/0 qualified4isolatedretries; package archive verified; not executed. Exact evidence in scratch/adaptive-resources-1026. Runtime reviews approved82e1d5c; source-review.json binds25 raw inputs.

| File | Change | State | Verification | Commit |
| --- | --- | --- | --- | --- |
| MiceHub.spec | Ship raw policy modules for child Python | implemented | full8418/0@f248802;4 isolated retries | 405084b |
| apps/voice/resources.py | Admission, device verification, bounded shared pool and resident status | implemented | full8418/0@f248802;4 isolated retries | 82e1d5c |
| apps/voice/service.py | Apply policy to every local inference/translation path | implemented | full8418/0@f248802;4 isolated retries | 82e1d5c |
| apps/voice/tts_spark/server.py | Apply shared policy to managed Spark | implemented | full8418/0@f248802;4 isolated retries | 82e1d5c |
| config/resource_policy.json | Editable profiles, reserves and admission thresholds | implemented | full8418/0@f248802;4 isolated retries | 82e1d5c |
| docs/systems.json | Generated inventory/build output | implemented | full8418/0@f248802;4 isolated retries | 405084b |
| docs/systems/README.md | Generated inventory/build output | implemented | full8418/0@f248802;4 isolated retries | 405084b |
| docs/systems/agents.md | Generated inventory/build output | implemented | full8418/0@f248802;4 isolated retries | 405084b |
| docs/systems/app-voice.md | Generated inventory/build output | implemented | full8418/0@f248802;4 isolated retries | 405084b |
| docs/systems/hub-auth.md | Generated inventory/build output | implemented | full8418/0@f248802;4 isolated retries | 405084b |
| docs/systems/hub-resources.md | Generated inventory/build output | implemented | full8418/0@f248802;4 isolated retries | f248802 |
| docs/systems/hub-web.md | Generated inventory/build output | implemented | full8418/0@f248802;4 isolated retries | 405084b |
| docs/systems/qc.md | Generated inventory/build output | implemented | full8418/0@f248802;4 isolated retries | f248802 |
| docs/systems/shared-web.md | Generated inventory/build output | implemented | full8418/0@f248802;4 isolated retries | 405084b |
| handoff/tasks/adaptive-resources-1026.md | Per-file checkpoint and next actions | implemented | metadata after full; selected closure pending | this checkpoint |
| main_python/hub_api_apps.py | Pass shared DATA policy environment to Voice | implemented | full8418/0@f248802;4 isolated retries | 405084b |
| main_python/hub_api_resources.py | Authenticated settings and public-only client bootstrap | implemented | full8418/0@f248802;4 isolated retries | 405084b |
| main_python/hub_auth.py | Gate resource POST | implemented | full8418/0@f248802;4 isolated retries | 405084b |
| main_python/main.py | Bind resource API and bootstrap | implemented | full8418/0@f248802;4 isolated retries | 405084b |
| main_python/resource_hardware.py | Bounded unknown-safe CPU RAM GPU discovery | implemented | full8418/0@f248802;4 isolated retries | 82e1d5c |
| main_python/resource_policy.py | Validated stable capacity profiles and fresh load budgets | implemented | full8418/0@f248802;4 isolated retries | 82e1d5c |
| main_python/resource_settings.py | Atomic revisioned machine-local settings | implemented | full8418/0@f248802;4 isolated retries | 82e1d5c |
| main_python/web/help.html | Generated inventory/build output | implemented | full8418/0@f248802;4 isolated retries | 82e1d5c |
| main_python/web/help/parts/hub.html | Help parity | implemented | full8418/0@f248802;4 isolated retries | 82e1d5c |
| main_python/web/help/parts/studio.html | Help parity | implemented | full8418/0@f248802;4 isolated retries | 82e1d5c |
| main_python/web/help/parts/voice.html | Help parity | implemented | full8418/0@f248802;4 isolated retries | 82e1d5c |
| main_python/web/home/parts/boot_scans.js | Storage-denial safe initial scans | implemented | full8418/0@f248802;4 isolated retries | 405084b |
| main_python/web/home/parts/settings.html | Resource settings controls | implemented | full8418/0@f248802;4 isolated retries | 405084b |
| main_python/web/home/parts/settings.js | Editable settings and honest applied/pending display | implemented | full8418/0@f248802;4 isolated retries | 82e1d5c |
| main_python/web/hub.html | Generated inventory/build output | implemented | full8418/0@f248802;4 isolated retries | 82e1d5c |
| nong/main_python_set_nong/web/app.js | Generated inventory/build output | implemented | full8418/0@f248802;4 isolated retries | 405084b |
| nong/main_python_set_nong/web/app_parts/main_loop.js | Throttle rendering without motion timing changes | implemented | full8418/0@f248802;4 isolated retries | 405084b |
| nong/main_python_set_nong/web/app_parts/scene.js | Client renderer limits | implemented | full8418/0@f248802;4 isolated retries | 405084b |
| qc/checks/check_resource_policy.py | Production regression coverage | implemented | full8418/0@f248802;4 isolated retries | 82e1d5c |
| qc/checks/check_resource_policy_browser.py | Production regression coverage | implemented | full8418/0@f248802;4 isolated retries | 82e1d5c |
| qc/data/resource_policy.js | Production regression coverage | implemented | full8418/0@f248802;4 isolated retries | 82e1d5c |
| shared/web/resources.js | Independent client display policy | implemented | full8418/0@f248802;4 isolated retries | 82e1d5c |

| qc/checks/check_voice_fast.py | Initialize actual resource adapter in legacy partial-Brain fixture | implemented | full8418/0@f248802;4 isolated retries | fbc8c32 |

## Facts found
- Capacity uses totalCPU/RAM; free RAM/VRAM budgets refreshed at model admission. Detection never imports/loads AI models.
- CPU LLM metadata admission includes buffers and headroom; STT/Spark minimum floors are advisory, not hard model-size caps.
- GPU UUID verification respects actual library indices; explicit CPU cannot allocate GPU. Unknown hardware falls back conservatively.
- One process-wide translation pool; native thread/pool changes report restart pending. Existing models report actual resident revision.
- Hub PC policy and browser display policy are independent; control/playback/safety ticks remain unchanged.
- Packaged Voice/Spark child Python needs raw policy modules outside native PYZ. Root spec is already dirty: merge only own data entries.
- Separate assessment found Lift missing travel deadline (P1), not repaired by this PC scope. No physical fault observed.

## Done
Design and final substantive source reviews: resource_design (supported gpt-6-astra high) + audit_latest_ui; reviewed findings verified and corrected. Final full8418/0 with4qualifiedisolatedretries and archive verified, no actual models/hardware. Isolated child-layout Python imports passed. Deliberate9/9 guards caught, restored green; scratch/adaptive-resources-1026/regressions.log. Logs scratch/adaptive-resources-1026; older full8335 does not cover this task.

## Next
1. Archive final per-file ledger, delete only own closed task and rebuild agents inventory; selected metadata gate.
2. PR expected-head merge after independent closure review; guarded root source integration.
3. PR/guarded source integration; preserve all root dirty userdata/spec/EXE, record remaining Lift/physical work.

## Blocked
Physical USER-NOTREADY, elbow trim user-deferred. No software blocker. No service/runtime/robot cutover.
