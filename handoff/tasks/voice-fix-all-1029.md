# Fix voice everywhere and the hanging Voice app

Owner: claude:jf5f (cloud thread)
Updated: 2026-10-29 19:10 (UTC)
Branch: claude/project-thread-jf5f5g
Last commit: 8658d42 (PR #111 merge)
Plan: A55-1

## Goal
User 2026-10-29: "แก้พวกเรื่องเสียง voice ต่างๆของทุกจุดด้วยนะรวมแอพ voice ที่ค้าง"
(fix every voice/sound problem everywhere, including the Voice app that hangs).

## Doing now
Nothing: merged (PR #111) and tested on the PC from a worktree. Only the deploy into the main PC tree is left (Next 1).

## File status
Baseline: c67e631.

| File | Change | State | Verification | Commit |
| --- | --- | --- | --- | --- |
| `main_python/voice_helper.py` | NEW: VoiceHelper start/state/ensure/call, log, python list | done | check_voice_helper 16/0, sabotage 6/6 | pushed |
| `config/voice_helper.json` | NEW: autoStart, python list, startSeconds, waitSeconds, log | done | check_voice_helper | pushed |
| `main_python/main.py` | VOICE_HELPER; proxy starts helper when refused (GET 503 starting, POST waits) | done | check_voice_helper, check_voice | pushed |
| `main_python/hub_api_apps.py` | /api/voice/start via VOICE_HELPER; GET /api/voice/helper | done | check_voice_helper | pushed |
| `main_python/hub_speak.py` | rig line starts helper via call() | done | check_voice_helper, check_speak | pushed |
| `main_python/hub_api_studio.py` | AI gesture starts helper via call() | done | voice suite | pushed |
| `apps/voice/service.py` | one load per model (_load_lock_stt/_llm) | done | check_voice_helper part 7 | pushed |
| `apps/voice/app.js`, `index.template.html`, `index.html` | wait for helper with seconds, show why + log tail | done | voice suite (cloud browser) | pushed |
| `main_python/web/help/parts/voice.html`, `help.html` | help: helper starts by itself | done | build_web | pushed |
| `qc/lib/qc.py`, `qc/run_qc.py` | MICE_VOICE_AUTOSTART=0 in QC | done | full QC | pushed |
| `qc/checks/check_voice_helper.py` | NEW check | done | 16/0 | pushed |
| `docs/systems.json`, `docs/systems/*` | files registered, A55-1 trap note | done | systems build | pushed |
| `docs/PLAN.html`, `docs/plan_state.js` | A55 heading, A55-1 | done | check_plan_areas | pushed |

## Facts found
- PC 2026-10-29 19:05Z (read-only, RC): NO hub, NO helper running; 8642/8767/8779 refused; GPU 0 MiB. PC HEAD 1283955 (#106, behind main). Live voice.json: hear [local], think [local], speak [edge, local], stt small, llm Qwen2.5-0.5B. tts_spark/server.log last 2026-10-22.
- The "Voice app" = `MiceHub.exe --open voice` (main_python/app_window.py): an Edge --app window on the hub's /apps/voice page; the work is the helper apps/voice/service.py on 8767.
- Old hub_api_apps.py /api/voice/start: stdout/stderr DEVNULL (no log); frozen exe used shutil.which("python") (can be the Store stub); no guard against two starts.
- apps/voice/app.js startVoiceService (~line 718): waits only 10 s, then stays "helper started, connecting…" forever = the visible hang.
- Nothing started the helper automatically: hub_speak._make (rig speech), hub_api_studio.ask_ai_gesture and every /api/voice/* failed while it was down.
- apps/voice/service.py:514 `_lock` = ONE lock for listen, answer, translate and model loads; held while a model loads (1110, 2200, 2241, 2397, 2474, 2522).
- service.py:2045 preload() worker loads models WITHOUT `_lock`; `_load_stt`/`_load_llm` (927, 1997) set `*_loading` but never check it: a question during preload loads a 2nd copy.

## Done
- PC 2026-10-30 03:08 (UTC+7), worktree at 8658d42 run from source: page opened -> /api/voice/health 503 starting at 6 s -> helper (C:\Program Files\Python312) answered at 12 s, health 200; helper stopped -> back by itself in ~2 s; helper.log clean. /say and /ask through the hub still need the hub login (user rule 2026-09-14, kept).
- PC repro 2026-10-29 (RC, read/launch only): `Mice Voice.lnk` = `dist\MiceHub.exe --open voice`; hub up in 5 s, 8767 never came up in 180 s; /api/voice/start = 401 without login. Helper by hand (C:\Program Files\Python312): /health 200 in 3 s; first model answer 25.4 s (models loading), warm 7.2 s on cuda; FAQ 0.03 s; Edge /say 6.6-6.8 s per new line, 0.02 s cached; GPU 7.7 GB after.
- Fix: hub owns and auto-starts the helper; page waits with a clock; one model load at a time.
- QC: voice suite 1194/0; full 9072/11 - failures are cloud env (other pio envs not built, no torch/cv2, browser checks time out in the cloud, census timing under load).

## Next
1. Deploy into E:\final_proj\mice\mice_system once the RL job there is done: that tree has diverged from main (3 local commits, 72 local edits, 12 overlap incoming RL files) - commit its work, merge origin/main, rebuild `python -m PyInstaller --clean --noconfirm MiceHub.spec`. Then remove the test worktree `.claude\worktrees\voice-test` (its hub 26664 + helper 13744 run now).
2. Ideas not done: Edge ~6.7 s per new line (stream audio to the rig instead of the whole clip); the 0.5B model invents facts (coffee shop) - a bigger model or a cloud key.

## Blocked
- nothing
