# PC Face app, watcher and Photobooth integration

Owner: codex:10231359-7280
Updated: 2026-10-23T14:00:18.822288+07:00
Branch: codex/face-pc-1023
Last commit: 45dac39 (baseline; see git log for checkpoint)
Plan: A45-30; remaining real run A45-14/A45-12

## Goal
Finish all PC-only Face app/watcher/Photobooth work without editing friend's sources.
Coordinate results with parent codex:10231353-0401, which owns URDF/QC/build/restart.

## Doing now
Read-only inspection of actual listeners, supported APIs and Photobooth startup path.
Read protected friend instructions first. No inference, model loads, QC or restarts.

## Facts found
- HANDOFF.md: friend sources outside code are read-only/start-only; no edits allowed.
- apps/faces/service.py belongs to app-faces; its system header has been read.
- Live baseline: friend 8000 PID11376, web5173 PID49656, watcher8769 PID38676,
  hub8642 PID33336 and Voice8767 PID29020 are listening.
- Source branch is HEAD-only for task metadata; dirty main runtime is not assumed equal.

## Done
- Read AGENTS/HANDOFF/CLAUDE, coordination, relevant task files and app-faces header.
- Claimed only this handoff plus private scratch; A45-30 added under shared mutex.
- Parent informed that exclusive resources remain theirs.

## Next
1. Inspect actual metadata/status APIs and friend/Photobooth launch requirements.
2. Ask parent for bounded existing-model/name measurement lease after its gate release.
3. Save evidence and exact remaining hardware/key/person/friend blocks; send checklist delta.

## Blocked
- Concurrency/inference waits for explicit parent resource release.
- Real robot source and enrolled-person camera-to-name measurement require robot/person.
