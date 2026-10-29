# AI watch: start/stop by hand from the desktop

Owner: claude:ai-watch-onoff
Updated: 2026-10-29 05:48 +0000
Branch: claude/project-thread-29emvx
Last commit: <sha>
Plan: A53-1

## Goal
User 2026-10-29: "ห๊ะทำไมถึงเป็นฝังในเครื่องนะเอาแบบเปิดปิดได้ได้ไหมอาจจะเก็บไว้ใน desktop เดี่ยวเปิดปิดเอง ... เสีย ram ฟรีๆ ... ตอนเล่นเกม ... กระตุก ... เครื่องร้อน"
-> tools/ai_watch.py must NOT start at logon. Desktop shortcuts ON / OFF, clear on/off state,
install removes the old logon task/Startup entry, watcher light (long sleep, low priority), settings in config/ai_watch.json.

## Doing now
Full QC (`python qc/run_qc.py --quiet`), then PR + merge.

## File status
Baseline: e8f51c3

| File | Change | State | Verification | Commit |
| --- | --- | --- | --- | --- |
| `tools/ai_watch.py` | start/stop/--popup, install = desktop shortcuts + remove logon, idle priority, wake_in | done | check_ai_watch 29/29 + 4 sabotages caught | this checkpoint |
| `tools/limitwatch/jobs.py` | pid_alive works without psutil off Windows | done | check_ai_watch | this checkpoint |
| `config/ai_watch.json` | poll 180 s, `control` block (priority, shortcuts, Thai messages) | done | check_ai_watch | this checkpoint |
| `qc/checks/check_ai_watch.py` | _on_off(): install/start/stop/priority/wake | done | sabotage x4 | this checkpoint |
| `docs/systems/ai-watch.md`, `docs/systems/agents.md` | rules + rebuilt | done | systems.py build | this checkpoint |
| `handoff/tasks/ai-watch-onoff.md`, `docs/PLAN.html`, `docs/plan_state.js` | task + A53-1 | done | n/a | this checkpoint |

## Facts found
- tools/ai_watch.py cmd_install: schtasks ONLOGON task "MiceAIWatch", else Startup\MiceAIWatch.vbs; launcher %LOCALAPPDATA%/MiceAIWatch/launch.py tries roots() (rename-safe).
- tools/ai_watch.py cmd_run: loop tick + sleep poll_seconds (30 s); pid in _out/ai_watch/watcher.pid.
- tools/limitwatch/watcher.py:198 _fire_due fires jobs whose "due" <= now, so sleep can be cut to the next due job.

## Done
- Code + check: `python qc/run_qc.py --quiet --no-build check_ai_watch check_resource_policy` 108/108 (cloud, Linux; Windows .lnk path untested here).

## Next
1. Full QC, PR, merge; PC: git pull --ff-only in E:\\final_proj\\mice\\code, then `python tools/ai_watch.py install` (makes the desktop shortcuts).

## Blocked
- nothing
