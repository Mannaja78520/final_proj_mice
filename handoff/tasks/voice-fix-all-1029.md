# Fix voice everywhere and the hanging Voice app

Owner: claude:jf5f (cloud thread)
Updated: 2026-10-29 19:10 (UTC)
Branch: claude/project-thread-jf5f5g
Last commit: this checkpoint
Plan: A55-1

## Goal
User 2026-10-29: "แก้พวกเรื่องเสียง voice ต่างๆของทุกจุดด้วยนะรวมแอพ voice ที่ค้าง"
(fix every voice/sound problem everywhere, including the Voice app that hangs).

## Doing now
Reading apps/voice/service.py for what can block every request (shared GPU lock,
model loads); a read-only diagnosis runs on the PC (no process stopped).

## File status
Baseline: c67e631. No code edits yet.

| File | Change | State | Verification | Commit |
| --- | --- | --- | --- | --- |
| `docs/PLAN.html`, `docs/plan_state.js` | A55-1 row | done | plan.py | this checkpoint |
| `handoff/tasks/voice-fix-all-1029.md` | this file | done | n/a | this checkpoint |

## Facts found
- The "Voice app" = `MiceHub.exe --open voice` (main_python/app_window.py): an Edge --app window on the hub's /apps/voice page; the work is the helper apps/voice/service.py on 8767.
- apps/voice/service.py:514 `_lock` = ONE lock for listen, answer, translate and model loads; held while a model loads (1110, 2200, 2241, 2397, 2474, 2522).
- service.py:2045 preload() worker loads models WITHOUT `_lock`; `_load_stt`/`_load_llm` (927, 1997) set `*_loading` but never check it.
- main_python/hub_api_apps.py:131 /api/voice/start: helper stdout/stderr go to DEVNULL (no log).

## Done
- nothing yet

## Next
1. Read the PC diagnosis, find the hang, fix with a QC check, sabotage-prove it.

## Blocked
- nothing
