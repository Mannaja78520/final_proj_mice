# UX/UI usability sweep and residual quality follow-through

Owner: codex:10260449-5ec2
Updated: 2026-10-26 04:49 +0700
Branch: codex/usability-review-1026
Tree: E:/final_proj/mice/code/.staging-usability-review-1026
Last commit: this checkpoint; baseline3298e36
Plan: A48-19 (robot); related A48-13 (physical/remaining Lift), A48-18 completed

## Goal
User asks: finish residual bug/usability/performance improvements across our entire UI, including Hub software hardware use, dynamic for weaker/stronger future PCs and configurable. Latest steering: if Help exists elsewhere, do not add it to Tools; authorizes a fresh session to save tokens. Continue autonomously; no confirmation of routine choices.

## Doing now
Step 1: implement reviewed flat registry launcher, native safe links, truthful states/keyboard focus; Help parity and affected browser regressions. Claimed manifests/Home/help-links/data/screenshot additions. No source edits before this checkpoint. Design review completed tools_design (same-provider gpt-6-astra high); private report pending persistence.

## File status
Planned paths only; can narrow/extend after source/visual audit. Claim additions before editing. New regression filenames/config catalogs may replace listed checks after design.

| File | Change | State | Verification | Commit |
| --- | --- | --- | --- | --- |
| main_python/web/home/parts/tools.html | Remove duplicated Help/header clutter; tools only | planned, not edited | not run | uncommitted, planned |
| main_python/web/home/parts/tools.js | Data-driven compact discoverable tools; omit Help cards/buttons | planned, not edited | not run | uncommitted, planned |
| main_python/web/home/style.css | Responsive consistent cards without tall empty columns | planned, not edited | not run | uncommitted, planned |
| main_python/web/home/parts/top.html | Keep one clear global Help entry, inspect header usability | planned, not edited | not run | uncommitted, planned |
| main_python/web/help/parts/hub.html | Same-step Help parity for actual Tools behavior | planned, not edited | not run | uncommitted, planned |
| main_python/web/hub.html | Generated from parts only | planned, not edited | not run | uncommitted, planned |
| main_python/web/help.html | Generated from parts only | planned, not edited | not run | uncommitted, planned |
| qc/checks/check_tools_list.py | Registry/unknown apps/Help exclusion/keyboard and layout regression | planned, not edited | not run | uncommitted, planned |
| qc/checks/check_responsive.py | Narrow/wide real browser overflow and tap-target checks | planned, not edited | not run | uncommitted, planned |
| docs/systems.json | Only if new paths/system registration needed | planned, not edited | not run | uncommitted, planned |
| docs/systems/hub-web.md | Generated inventory when sources change | planned, not edited | not run | uncommitted, planned |
| docs/systems/qc.md | Generated inventory after test changes | planned, not edited | not run | uncommitted, planned |
| docs/systems/agents.md | Generated active task inventory | planned, not edited | not run | uncommitted, planned |
| handoff/tasks/usability-review-1026.md | Per-file handoff and concrete next actions | ready for takeover | handoff structure checked | this checkpoint |
| apps/studio/app.json | Flat launcher copy/regression/Help parity | pending | not run | uncommitted |
| apps/tv/app.json | Flat launcher copy/regression/Help parity | pending | not run | uncommitted |
| apps/camera/app.json | Flat launcher copy/regression/Help parity | pending | not run | uncommitted |
| apps/voice/app.json | Flat launcher copy/regression/Help parity | pending | not run | uncommitted |
| apps/all-jao/app.json | Flat launcher copy/regression/Help parity | pending | not run | uncommitted |
| apps/photobooth/app.json | Flat launcher copy/regression/Help parity | pending | not run | uncommitted |
| apps/gacha/app.json | Flat launcher copy/regression/Help parity | pending | not run | uncommitted |
| apps/faces/app.json | Flat launcher copy/regression/Help parity | pending | not run | uncommitted |
| apps/help/app.json | Flat launcher copy/regression/Help parity | pending | not run | uncommitted |
| main_python/web/home/parts/home.html | Flat launcher copy/regression/Help parity | pending | not run | uncommitted |
| qc/checks/check_help_links.py | Flat launcher copy/regression/Help parity | pending | not run | uncommitted |
| qc/data/tools_launcher.js | Flat launcher copy/regression/Help parity | pending | not run | uncommitted |
| docs/shots/hub-tools-card.png | Flat launcher copy/regression/Help parity | pending | not run | uncommitted |

## Facts found
- Root main HEAD3298e36 = merged PR82. AdaptivePC policy is DONE in source: profiles/CPU-GPU-RAM/headroom/settings, bounded Voice translation/native threads/admission, independent browser render limits. Do not rebuild it needlessly or claim unknown real performance.
- PR82 full8418/0@f248802,994inputs+20privateCAD stable; four parallel failures passed alone2/2 (app_browser,edge_cases,freeze_stop,checked_dispatch). Metadata closure212/0. Package11,463,270bytes,11assets+4native modules archiveverified, not run/installed. Proof root scratch/adaptive-resources-1026 and immutable .staging-adaptive-resources-1026/scratch/adaptive-resources-1026.
- Screenshot private root scratch/usability-review-1026/user-tools.png; inspect it. Current Tools groups are separate columns with unequal card counts, fourth Help category falls into a low isolated block; headings duplicate Thai/English and cards mix styles. User explicitly dislikes this.
- Global Help ALREADY EXISTS at main_python/web/home/parts/top.html #helpLink. Tools redundantly has top Open Help link (tools.html), docs/help category, per-tool Help buttons and Help links in empty/error states (tools.js). User latest wants Help absent from Tools when elsewhere: retain global accessible Help and remove duplicates from Tools/Home embedded tools, update tests/docs accordingly.
- Tools implementation main_python/web/home/parts/tools.js: MiceToolsManager/createToolRow/render/loadApps; app registry /api/apps auto-discovers apps. Preserve unknown/new app discovery, truthful error versus empty state, escaping and global login/STOP. Categorization currently hardcoded TOOL_GROUPS; move new adjustable labels/category data to config/registry per user data-driven rule if redesign changes them.
- Tools current UI says Open/Help and English blurbs; favor short Thai-first descriptions and consistent Open actions, brand names may remain. Confirm actual global Help remains reachable by keyboard/narrow screen before removing duplicates.
- Hub is built from home parts; NEVER edit generated hub.html/help.html/app.js directly. Mandatory Help parity in same feature step; OOP/modular focused classes, no monolithic dump.
- Root is intentionally dirty. Preserve exact user config/gacha.json+voice.json, dist/MiceHub.exe, MiceHub.spec (contains user process-kill helper +our3raw policy data entries), Nong Studio html_parts/setup.html+view.html/style.css/generatedindex, projects/settings_shared, plans/logs/private data/untracked files. Audit existing dirty Studio differences before any scoped merge; never blanket copy. Do NOT execute root spec (its preexisting helper kills live Hub). Isolated spec baseline is safe for packaging.
- Existing source trees/proofs must stay intact; no reset/stash/clean/init/archive old trees. Root E:/final_proj/mice/code; app project path is parent E:/final_proj/mice, not Git itself.
- Confirmed remaining P1 Lift gap: firmware/src/modules/lift/LiftModule.cpp continuous UP/DOWN/HOME relies on limit switches, no independent travel/homing deadline; disconnected/stuckHIGH input can keep motor energized until STOP. No hardware fault observed. Source repair remains: configurable deadline +latched fault, meaningful native/fake regression and mice_lift build. Do not silently drop this older authorized issue; handle as separate scoped step after UX investigation with contract/design review.
- Combined Voice+Face+browser actual inference latency/CPU-RAM-VRAM/thermal utilization UNMEASURED; capacity snapshot Ultra9 275HX24logical/31.4GiB RAM/RTX5070TiLaptop12227MiB is not utilization proof. No 100%hardware or bug-free claim. Resource admission advisory; STT/Spark floors are not hard model-size caps. External Face_Regonize/All-Jao-Games belong to friend; no edits outside code.
- Physical pause is HUMAN USER-NOTREADY. No robot probes, scans/retries, COM/WiFi reads, motion/flash/calibration/HOME/trim, camera capture or Hub/helper/service cutover. Connection alone is not consent. User will adjust elbowtrim manually. Prior live processes/settings unchanged.
- Sole QC/fake/browser/build/timing driver may run only after fresh inventory and BRIDGE claim; no concurrent heavy/model jobs. Simulated modules/browser and native compile permitted. No real models downloaded/loaded by settings tests. Preserve source inputs during full and raw-hash privateCAD read-only model path E:/final_proj/mice/model/nong_urdf/solidworks/export/nong_description.
- Coordination/plan mutations use short root .staging-coordination.lock, owner.txt, no recursive delete; docs/BRIDGE live exact file claims; tools/plan.py --page robot --agent provider:session. Required reviews codex-first supported agents per docs/COORDINATION.md212; previous source reviews are historical, not approval of new UI.

## Done
Prepared isolated branch from accepted root, privately preserved user screenshot, identified existing global Help and duplicated Tools entries, recorded old completed work and real remaining gaps. No source fixes/QC/model/robot/runtime actions in this task yet.

## Next
1. New session take this task and A48-19 with its own provider:session; read screenshot/rules/relevant system headers; inspect root dirty diffs read-only; claim exact source/test/help paths under mutex.
2. Ask bounded design/source review; redesign Tools without duplicated Help; real browser visuals/click/keyboard at360-1920px/allthemes, error/empty/discovery states. Inspect all own pages and record actionable findings; fix through parts, update Help same step.
3. Reconcile other residual software gaps (including Lift) in separate scoped/tested steps, then affected checks +deliberate regressions, independent final review, stable full once per final batch, safe spec package/archive proof.
4. Scoped PR/merge/root integration only after current proof, preserve all root dirty bytes or explicit own insert-only merges; use existing private guarded script patterns without inheriting old full receipt. Do not end at a plan or report only; finish authorized implementable work.

## Blocked
Physical tests remain user-paused; no software blocker. Actual combined inference measurements require idle/resource claim and must never overlap QC; no unsupported real-performance or external-backend enforcement claims.
