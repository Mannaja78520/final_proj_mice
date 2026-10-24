# Gemini Studio On-Demand Rendering, TV Remote Thin Client & Help Documentation

Owner: gemini:ed497bb9
Updated: 2026-10-25 01:05 +0700
Branch: main
Last commit: 2bd3299
Plan: A48-14, A48-15

## Goal
1. Decouple TV Remote / Monitor (`/tv`, `/monitor`, `apps/tv/index.html`) from 3D Three.js: ultra-light thin client for smart TV and low-spec screens.
2. Implement On-Demand 3D rendering in Nong Studio (`main_loop.js`): 0% CPU/GPU when idle, re-render only when moving/scrubbing/interacting.
3. Overhaul Help page (`main_python/web/help.html`): modular topic-by-topic navigation with prev/next buttons, 22 setting-level live screenshots with callout pins and physical action-impact matrices.
4. Address Codex audit findings: URDF dirty invalidation in `build_rig.js`, TV API contracts (`/api/modules`, `at_ms`/`total_ms`, resume `currentSeqName`), and physical robot safety (HOME via `/api/dev/cmd?c=HOME` to invoke native firmware calibrated NEUTRAL, strictly avoiding flat all-90).

## Doing now
Formalizing handoff documentation, verifying that all Codex audit points are resolved with passes in targeted and quick QC suites, and explaining multi-agent audit coordination to the user.

## Facts found
- `main_python/main.py:2351`: `path.startswith("/api/dev/")` routes via `dev_route()`. For device commands, `POST /api/dev/cmd?dev=<dev>&c=HOME` passes `check_app_routes.py` and dispatches native `HOME` command directly to firmware.
- `firmware/src/modules/nong/NongModule.cpp:425`: Firmware `HOME` moves smoothly to stored calibrated `NEUTRAL` (`[90, 140, 90, 90, 90, 40, 90, 90, 90, 90.5]`). Forcing flat all-90 is dangerous and must never be sent to hardware.
- `main_python/hub_show.py:92`: Show status returns `{"at_ms": ..., "total_ms": ...}`, not `ms`/`total`.
- `main_python/main.py:2401`: Route for module list is `/api/modules`, not `/api/status`. Joint angles are in `joints` or `raw`.
- `nong/main_python_set_nong/web/app_parts/main_loop.js`: `tick(now)` skips `renderer.render()` when idle. `build_rig.js:applyPose()` must invoke `markDirty3d(5)` before early return in URDF mode so CAD rendering does not stall after 60 frames.

## Done
- Commits `ce0aeb0`, `b5a161b`, `2bd3299` landed on `main`.
- Backup branches created: `backup-20261024-pre-decouple` and `backup-20261024-complete-upgrade`.
- Resolved Codex audit contract discrepancies in `apps/tv/index.html` and `build_rig.js`.
- Verified QC: `check_app_routes`, `check_studio_cost`, `check_studio_playback`, `check_docs` all PASS (360/360). Quick QC suite passed (5,735/5,735).

## Next
1. Keep `apps/tv/index.html` and `build_rig.js` verified and clean.
2. Coordinate with Codex staging branch if needed.
3. Uphold OOP Rule 9 across all AI tasks.

## Blocked
- Nothing.
