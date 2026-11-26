# Voice helper: free the GPU when idle

Owner: claude (project thread, branch claude/voice-idle-unload)
Updated: 2026-11-26
Branch: claude/voice-idle-unload
Last commit: see git log
Plan: user ask 2026-11-26 (PC sluggish with SolidWorks open; Voice held 5.4 GB of the 12 GB card)

## Goal
Voice models leave GPU memory after idleUnloadMinutes (config/voice.json, default 15, 0 = never) and load again on the next request,
with a "warming up" state; never during a request or presence/greeter mode; optional yieldVramWhen (e.g. SLDWORKS.exe) shortens it to a minute.

## Done
- apps/voice/idle_unload.py (calls the existing brain.unload()), hooks in service.py (do_POST wrapper, health(), main()), config keys, help in 4 languages,
  changelog, qc/checks/check_voice_idle_unload.py (fakes, 16 asserts, 3 breaks caught), tools/voice_idle_measure.py (real numbers; NOT run).
- Full QC on 918b0bea: 10967 passed, 2 failed, both about the new file and fixed after (a bare subprocess without creationflags; a `self._lock` name the scheduler guard
  forbids) and re-checked; 1 FLAKY (check_visual_language, see Open).

## Open
- Real measurement: run `python tools/voice_idle_measure.py` when nobody uses Voice (it unloads the real helper's models; the next answer is slow). Expect ~5.4 GB freed.
- Merge note: claude/project-thread-q4yvte (VRAM measurement) edits apps/voice/service.py health(); the only real conflict with this branch is that hunk
  (keep both: its planner view lines and my idleUnload / _asleep_note lines).
- check_visual_language flaked in the crowd: "no leftover English UI text on home in ja - QC_temp_app": another check's temporary app (QC_temp_app) was in the app
  registry the Home page reads. Same kind of shared-state leak as the projects/sequences/reports folders (qc.isolate_data): give each check its own apps registry
  copy (MICE_EXTENSIONS is already per hub; find who writes QC_temp_app).
- check_one_module_list (FLAKY earlier, passed alone 2/2): its driver already waits for readiness (up to 30 s for the far-PC row); with polite mode's CPU cap the
  scans can be slower, so the cheap fix is more headroom on that wait (30 s -> 60 s) once a crowd failure's text shows it timed out. Not changed without that evidence.
- Full QC wall time under polite mode with other work on the PC: 1082 s (parallel 733 s) in the run above vs 613 s on an idle PC.
