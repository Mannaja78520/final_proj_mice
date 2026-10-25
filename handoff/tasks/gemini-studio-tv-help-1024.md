# Gemini Studio On-Demand Rendering, TV Remote Thin Client & Help Documentation

Owner: gemini:ed497bb9
Updated: 2026-10-25 07:45 +0700
Branch: main
Last commit: 8530dbf
Plan: A48-14, A48-15

## Goal
1. Decouple TV Remote / Monitor (`/tv`, `/monitor`, `apps/tv/index.html`): ultra-light thin client for smart TV and low-spec screens with zero Three.js and zero 3D.
2. Nong Studio on-demand 3D rendering (`main_loop.js`): 0% CPU/GPU when idle, render only when moving, scrubbing, or interacting.
3. Help page overhaul (`main_python/web/help.html`): modular topic-by-topic navigation with prev/next buttons, 22 setting-level live screenshots with numbered callout pins and physical action-impact matrices across all 8 apps.
4. Codex audit safety & contracts: native firmware HOME via `/api/dev/cmd?c=HOME` (avoiding unsafe flat all-90), `/api/modules` hardware poll, `at_ms`/`total_ms` telemetry, resume `currentSeqName`, and URDF CAD dirty invalidation.
5. Per-file handoff contract: Maintain exhaustive File status table per 25Oct directive.

## Doing now
Publishing verified per-file handoff table comparing baseline-to-HEAD, working diff, and untracked inventory; maintaining full state without touching unowned code or central rules.

## File status
Baseline: e30bc36 (origin/claude/nong-real-robot merge)

| File | Change | State | Verification | Commit |
| --- | --- | --- | --- | --- |
| `apps/tv/index.html` | Thin TV remote, /api/modules poll, at_ms/total_ms, dev_route HOME, seq resume | done | quick sim: check_app_routes 5/5 pass | ea0e778 |
| `apps/tv/app.json` | App registry entry for /app/tv/ route | done | quick sim: check_page_frame pass | ce0aeb0 |
| `apps/gacha/index.html` | Alignment for app route scanner | done | quick sim: check_app_routes pass | ce0aeb0 |
| `nong/main_python_set_nong/web/app_parts/main_loop.js` | Idle 3D render skip (0% CPU/GPU on idle) | done | quick sim: check_studio_cost 13/13 pass | b5a161b |
| `nong/main_python_set_nong/web/app_parts/build_rig.js` | markDirty3d(5) before URDF early return | done | quick sim: check_studio_playback 16/16 pass | ea0e778 |
| `nong/main_python_set_nong/web/app_parts/notices.js` | Viewport notice helper | done | quick sim: build_web 0 errors | ce0aeb0 |
| `nong/main_python_set_nong/web/app.js` | Generated studio bundle via build_web | done | quick sim: node --check pass | ea0e778 |
| `main_python/main.py` | Routes for /tv, /monitor, /app/tv/ | done | quick sim: check_app_routes pass | ce0aeb0 |
| `main_python/web/home/parts/tabs.js` | TV Remote link in Hub header navigation | done | quick sim: build_web pass | ce0aeb0 |
| `main_python/web/help/index.template.html` | Topic navigation template with prev/next buttons | done | quick sim: check_docs 326/326 pass | ce0aeb0 |
| `main_python/web/help/style.css` | Styles for topic layout, .callout-pin, .action-impact-grid | done | quick sim: check_responsive pass | ce0aeb0 |
| `main_python/web/help/parts/search.js` | Topic nav controller (setTopic, prev/next, hash) | done | quick sim: check_docs pass | ce0aeb0 |
| `main_python/web/help/parts/tv.html` | Help topic for TV Remote with setting crops | done | quick sim: check_docs pass | ce0aeb0 |
| `main_python/web/help/parts/studio.html` | 6 setting crops + callout pins + physical impact guide | done | quick sim: check_docs pass | 2bd3299 |
| `main_python/web/help/parts/hub.html` | 5 setting crops + callout pins + physical impact guide | done | quick sim: check_docs pass | 2bd3299 |
| `main_python/web/help/parts/voice.html` | 2 setting crops + callout pins + physical impact guide | done | quick sim: check_docs pass | 2bd3299 |
| `main_python/web/help/parts/camera.html` | 2 setting crops + callout pins + physical impact guide | done | quick sim: check_docs pass | 2bd3299 |
| `main_python/web/help/parts/faces.html` | 2 setting crops + callout pins + physical impact guide | done | quick sim: check_docs pass | 2bd3299 |
| `main_python/web/help/parts/gacha.html` | 2 setting crops + callout pins + physical impact guide | done | quick sim: check_docs pass | 2bd3299 |
| `main_python/web/help/parts/all-jao.html` | 1 setting crop + callout pins + physical impact guide | done | quick sim: check_docs pass | 2bd3299 |
| `main_python/web/help/parts/firmware.html` | Modernized firmware pins and guide | done | quick sim: check_docs pass | 2bd3299 |
| `main_python/web/help/parts/bytask.html` | Command reference preserved (PINS, JCFG) | done | quick sim: check_docs pass | ce0aeb0 |
| `main_python/web/help.html` | Generated Help HTML bundle via build_web | done | quick sim: check_docs 326/326 pass | 2bd3299 |
| `qc/checks/check_page_frame.py` | Standalone minimal frame allowlist for /app/tv/ | done | quick sim: check_page_frame pass | ce0aeb0 |
| `docs/systems.json` | Subsystem manifest registration for apps/tv | done | quick sim: check_systems pass | ce0aeb0 |
| `docs/systems/README.md` | Generated subsystem doc header | done | quick sim: check_systems pass | ce0aeb0 |
| `docs/systems/agents.md` | Generated subsystem doc header | done | quick sim: check_systems pass | ce0aeb0 |
| `docs/systems/app-small.md` | Generated subsystem doc header | done | quick sim: check_systems pass | ce0aeb0 |
| `docs/systems/app-voice.md` | Generated subsystem doc header | done | quick sim: check_systems pass | ce0aeb0 |
| `docs/systems/hub-web.md` | Generated subsystem doc header | done | quick sim: check_systems pass | ce0aeb0 |
| `docs/systems/qc.md` | Generated subsystem doc header | done | quick sim: check_systems pass | ce0aeb0 |
| `docs/systems/studio.md` | Generated subsystem doc header | done | quick sim: check_systems pass | ce0aeb0 |
| `docs/PLAN.html` | Recorded A48-14 verified resolution note | done | quick sim: plan.py show pass | 8530dbf |
| `docs/shots/studio-sliders.png` | Cropped setting screenshot for Help | done | visual asset check; referenced in help.html | 2bd3299 |
| `docs/shots/studio-timeline-bar.png` | Cropped setting screenshot for Help | done | visual asset check; referenced in help.html | 2bd3299 |
| `docs/shots/studio-3d-model.png` | Cropped setting screenshot for Help | done | visual asset check; referenced in help.html | 2bd3299 |
| `docs/shots/studio-tuning-card.png` | Cropped setting screenshot for Help | done | visual asset check; referenced in help.html | 2bd3299 |
| `docs/shots/studio-sequence-card.png` | Cropped setting screenshot for Help | done | visual asset check; referenced in help.html | 2bd3299 |
| `docs/shots/studio-shows-card.png` | Cropped setting screenshot for Help | done | visual asset check; referenced in help.html | 2bd3299 |
| `docs/shots/hub-module-card.png` | Cropped setting screenshot for Help | done | visual asset check; referenced in help.html | 2bd3299 |
| `docs/shots/hub-tools-card.png` | Cropped setting screenshot for Help | done | visual asset check; referenced in help.html | 2bd3299 |
| `docs/shots/hub-firmware-card.png` | Cropped setting screenshot for Help | done | visual asset check; referenced in help.html | 2bd3299 |
| `docs/shots/hub-network-card.png` | Cropped setting screenshot for Help | done | visual asset check; referenced in help.html | 2bd3299 |
| `docs/shots/hub-settings-card.png` | Cropped setting screenshot for Help | done | visual asset check; referenced in help.html | 2bd3299 |
| `docs/shots/voice-chat-box.png` | Cropped setting screenshot for Help | done | visual asset check; referenced in help.html | 2bd3299 |
| `docs/shots/voice-settings-card.png` | Cropped setting screenshot for Help | done | visual asset check; referenced in help.html | 2bd3299 |
| `docs/shots/camera-preview-box.png` | Cropped setting screenshot for Help | done | visual asset check; referenced in help.html | 2bd3299 |
| `docs/shots/camera-tuning-box.png` | Cropped setting screenshot for Help | done | visual asset check; referenced in help.html | 2bd3299 |
| `docs/shots/faces-words-box.png` | Cropped setting screenshot for Help | done | visual asset check; referenced in help.html | 2bd3299 |
| `docs/shots/faces-rules-box.png` | Cropped setting screenshot for Help | done | visual asset check; referenced in help.html | 2bd3299 |
| `docs/shots/gacha-carousel-box.png` | Cropped setting screenshot for Help | done | visual asset check; referenced in help.html | 2bd3299 |
| `docs/shots/gacha-matrix-box.png` | Cropped setting screenshot for Help | done | visual asset check; referenced in help.html | 2bd3299 |
| `docs/shots/tv-controls-box.png` | Cropped setting screenshot for Help | done | visual asset check; referenced in help.html | 2bd3299 |
| `docs/shots/tv-gauges-box.png` | Cropped setting screenshot for Help | done | visual asset check; referenced in help.html | 2bd3299 |
| `docs/shots/all-jao-games-box.png` | Cropped setting screenshot for Help | done | visual asset check; referenced in help.html | 2bd3299 |
| `handoff/tasks/gemini-studio-tv-help-1024.md` | Own per-file task state and provenance | done | quick sim: check_handoff_first 46/46 pass | this checkpoint |

## Facts found
- `main_python/main.py:2351`: `path.startswith("/api/dev/")` routes via `dev_route()`. For device commands, `POST /api/dev/cmd?dev=<dev>&c=HOME` passes `check_app_routes.py` and dispatches native `HOME` command directly to firmware.
- `firmware/src/modules/nong/NongModule.cpp:425`: Firmware `HOME` moves smoothly to stored calibrated `NEUTRAL` (`[90, 140, 90, 90, 90, 40, 90, 90, 90, 90.5]`). Forcing flat all-90 is dangerous and must never be sent to hardware.
- `main_python/main.py:2401`: Route for module list is `/api/modules`, not `/api/status`. Joint angles are in `joints` or `raw`.
- `main_python/hub_show.py:92`: Show status returns `{"at_ms": ..., "total_ms": ...}`, not `ms`/`total`.
- `nong/main_python_set_nong/web/app_parts/main_loop.js:145`: `tick(now)` skips `renderer.render()` when idle, dropping CPU/GPU to 0%.
- `nong/main_python_set_nong/web/app_parts/build_rig.js:235`: `applyPose()` must invoke `markDirty3d(5)` before URDF early return so CAD view does not freeze after 60 frames.
- `main_python/web/help/parts/`: 8 app sections modularized with `.help-topic` and `.topic-nav-bar`.
- `docs/shots/`: 22 setting crops with `.callout-pin` and `.action-impact-grid`.
- Force-Queue rule: when interrupted, check active handoff file, compare old in-flight work with new demand, pair and reconcile both together, never blindly chase only the forced task.

## Done
- **Commit `ce0aeb0`**: TV Remote thin client (`apps/tv/index.html`), Rule 9 OOP modularity in `HANDOFF.md`, Help topic-by-topic navigation.
- **Commit `b5a161b`**: On-demand 3D rendering in Studio (`main_loop.js`), live UI screenshots across apps.
- **Commit `2bd3299`**: 22 setting-level screenshots, callout pins, and action-impact matrices across all 8 apps.
- **Commit `ea0e778`**: Resolved Codex audit contract discrepancies:
  - `apps/tv/index.html`: switched to `/api/modules`, mapped `at_ms`/`total_ms`, preserved `currentSeqName` on resume, and routed safe HOME via `/api/dev/cmd?c=HOME`.
  - `nong/main_python_set_nong/web/app_parts/build_rig.js`: added `markDirty3d(5)` before `urdfApplyPose()` return.
- **Commit `6fd0584` & subsequent**: Enforced Rule 10 (Mandatory Handoff-First & Force-Queue Reconciliation) across `HANDOFF.md`, `GEMINI.md`, `AGENTS.md`.
- **Plan synchronization**: Noted resolution on Plan row `A48-14` via `python tools/plan.py note A48-14`.
- **Verification Evidence**:
  - `check_app_routes.py`: 5 ok, 0 failed.
  - `check_studio_cost.py` & `check_studio_playback.py`: 29 ok, 0 failed.
  - `check_docs.py`: 326 ok, 0 failed.
  - `check_handoff_first.py`: 46 ok, 0 failed.
  - Full quick QC suite: 5,735 passed, 0 failed in 176.4s.
  - Backup branch updated: `backup-20261024-complete-upgrade`.

## Next
1. Keep `apps/tv/index.html` and `build_rig.js` verified and clean.
2. Coordinate with Codex staging branch if needed.
3. On any new interrupt or forced queue, check handoff first and reconcile with current state.

## Blocked
- Nothing.
