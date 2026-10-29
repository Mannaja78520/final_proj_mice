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
Writing qc/checks/check_voice_helper.py (fake helper script on a free port:
one start only, early exit reported with log tail, Store stub skipped, call()
retries after refused); then the Voice page start/wait UI.

## File status
Baseline: c67e631.

| File | Change | State | Verification | Commit |
| --- | --- | --- | --- | --- |
| `main_python/voice_helper.py` | NEW: VoiceHelper start/state/ensure/call, log, python list | done | not run | this checkpoint |
| `config/voice_helper.json` | NEW: autoStart, python list, startSeconds, waitSeconds, log | done | not run | this checkpoint |
| `main_python/main.py` | VOICE_HELPER instance; proxy starts helper when refused | done | not run | this checkpoint |
| `main_python/hub_api_apps.py` | /api/voice/start via VOICE_HELPER; GET /api/voice/helper | done | not run | this checkpoint |
| `main_python/hub_speak.py` | rig line starts helper via call() | done | not run | this checkpoint |
| `main_python/hub_api_studio.py` | AI gesture starts helper via call() | done | not run | this checkpoint |
| `qc/lib/qc.py`, `qc/run_qc.py` | MICE_VOICE_AUTOSTART=0 in QC | done | not run | this checkpoint |
| `apps/voice/app.js` | start: wait with seconds, show exit/log | pending | not run | uncommitted |
| `qc/checks/check_voice_helper.py` | NEW check | pending | not run | uncommitted |
| `docs/systems.json`, help parts | register files, help text | pending | not run | uncommitted |
| `docs/PLAN.html`, `docs/plan_state.js` | A55-1 row | done | plan.py | 1st checkpoint |

## Facts found
- PC 2026-10-29 19:05Z (read-only, RC): NO hub, NO helper running; 8642/8767/8779 refused; GPU 0 MiB. PC HEAD 1283955 (#106, behind main). Live voice.json: hear [local], think [local], speak [edge, local], stt small, llm Qwen2.5-0.5B. tts_spark/server.log last 2026-10-22.
- The "Voice app" = `MiceHub.exe --open voice` (main_python/app_window.py): an Edge --app window on the hub's /apps/voice page; the work is the helper apps/voice/service.py on 8767.
- Old hub_api_apps.py /api/voice/start: stdout/stderr DEVNULL (no log); frozen exe used shutil.which("python") (can be the Store stub); no guard against two starts.
- apps/voice/app.js startVoiceService (~line 718): waits only 10 s, then stays "helper started, connecting…" forever = the visible hang.
- Nothing started the helper automatically: hub_speak._make (rig speech), hub_api_studio.ask_ai_gesture and every /api/voice/* failed while it was down.
- apps/voice/service.py:514 `_lock` = ONE lock for listen, answer, translate and model loads; held while a model loads (1110, 2200, 2241, 2397, 2474, 2522).
- service.py:2045 preload() worker loads models WITHOUT `_lock`; `_load_stt`/`_load_llm` (927, 1997) set `*_loading` but never check it: a question during preload loads a 2nd copy.

## Done
- Hub-side helper owner + autostart (files above), not yet tested.

## Next
1. Read the PC diagnosis, find the hang, fix with a QC check, sabotage-prove it.

## Blocked
- nothing
