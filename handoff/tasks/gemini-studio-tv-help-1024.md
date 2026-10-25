# Gemini Studio On-Demand Rendering, TV Remote Thin Client & Help Documentation

Owner: gemini:ed497bb9
Updated: 2026-10-25 02:00 +0700
Branch: main
Last commit: ea0e778
Plan: A48-14, A48-15

## Goal
1. Decouple TV Remote / Monitor (`/tv`, `/monitor`, `apps/tv/index.html`): ultra-light thin client for smart TV and low-spec screens with zero Three.js and zero 3D.
2. Nong Studio on-demand 3D rendering (`main_loop.js`): 0% CPU/GPU when idle, render only when moving, scrubbing, or interacting.
3. Help page overhaul (`main_python/web/help.html`): modular topic-by-topic navigation with prev/next buttons, 22 setting-level live screenshots with numbered callout pins and physical action-impact matrices across all 8 apps.
4. Codex audit safety & contracts: native firmware HOME via `/api/dev/cmd?c=HOME` (avoiding unsafe flat all-90), `/api/modules` hardware poll, `at_ms`/`total_ms` telemetry, resume `currentSeqName`, and URDF CAD dirty invalidation.
5. Multi-agent discipline: Rule 9 (strict OOP and small modular files) and Rule 10 (mandatory Handoff-First protocol & Force-Queue reconciliation).

## Doing now
Completed all TV Remote, Studio 3D on-demand, Help page infographics, contract fixes, and Rule 10 force-queue reconciliation. Handoff record finalized for multi-agent auditing.

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
