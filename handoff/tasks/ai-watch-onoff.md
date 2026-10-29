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
Editing tools/ai_watch.py (start/stop/install shortcuts), config/ai_watch.json ("control" block), qc/checks/check_ai_watch.py.

## File status
Baseline: e8f51c3

| File | Change | State | Verification | Commit |
| --- | --- | --- | --- | --- |
| `handoff/tasks/ai-watch-onoff.md` | this task | in progress | n/a | this checkpoint |
| `docs/PLAN.html` | A53-1 added, doing | done | plan.py | this checkpoint |

## Facts found
- tools/ai_watch.py cmd_install: schtasks ONLOGON task "MiceAIWatch", else Startup\MiceAIWatch.vbs; launcher %LOCALAPPDATA%/MiceAIWatch/launch.py tries roots() (rename-safe).
- tools/ai_watch.py cmd_run: loop tick + sleep poll_seconds (30 s); pid in _out/ai_watch/watcher.pid.
- tools/limitwatch/watcher.py:198 _fire_due fires jobs whose "due" <= now, so sleep can be cut to the next due job.

## Done
- nothing yet

## Next
1. Implement, run `python qc/run_qc.py --quiet --no-build check_ai_watch check_resource_policy`.

## Blocked
- nothing
