# Named local character profiles

Owner: codex:10221534-bb09
Updated: 2026-10-22T16:50:33.171197+07:00
Branch: task/A45-27-10221534-bb09
Last commit: 9b3b757 (readiness replay checkpoint follows)
Plan: A45-27; A45-26 PC deployment continuation

## Goal
ตั้งจริต แนวท่า และเสียงได้ แก้ตัวที่เซฟในเครื่องได้ทันที มี default แยกจากโฟลเดอร์จริตแต่ละชื่อพร้อมเสียง/ท่าของตัวเอง ใช้ซ้ำโดยไม่กระทบค่าหลัก; ต่อ Claude และลด token cost.

## Done
- Isolated tree E:/final_proj/mice/code/.staging-profiles; main user edits preserved.
- Profiles module, local snapshots/copies, persistent selection, per-character settings/FAQ/manners/audio/motions/cache, stale-tab rejection and immutable default guard.
- Voice Personality UI creates/selects/reloads named copies and uploads sound/motion; answer sheet selects recorded audio and owned motions. Existing hub parser and speech queue reused.
- Targeted existing checks 219/0. New check_voice_profiles 49/0 including real Edge create/upload/save/switch/restore. Initial check_speak failure then isolated pass; timestamp-boundary theory not established.
- One same-provider independent design/code reviewer found and verified fixes: automatic default writes, legacy-key read redaction, FAQ/search dirty-state tracking. No remaining blocker in bounded source review.

## Doing now
Full final06f7434 passed7547/0 in500.7s, with check_hub_nav isolated retry green.
PR51 merged bd73420. Root main updated with all user data preserved and plan union.
First build failed because old exe still running; stopped verified idle hub, rebuilt
via spec successfully. Voice8767 restarted; feeling8779/watcher/friend preserved.
Actual packaged hub selects current's gestures; original voice/style/FAQ/calibration
hashes unchanged. WAV76608frames, first4.591s/repeat0.049s, exact cache reuse.
First real replay41/50:9 early typed/verse requests saw local model import unavailable while preloading. Health later loaded; failed user_exact/new_poem probes now pass. Original rows/verdict preserved in root scratch/profiles-deploy-2026-10-22/replay-first/. All50 re-running after confirmed readiness, replay-ready.log. No source changes to conceal startup failure.

## Next
1. Finish real replay and inspect actual service health/errors.
2. Mark A45-27 done only after replay; close this task via bookkeeping PR with generated header and own real plan row. Full runtime gate remains06f7434; metadata-only checks after closure.
3. Release own QC/build/deploy claims in root BRIDGE, preserving user dirty files and running services. No robot motion performed.

## Blocked
- No external prerequisite. Real replay in flight; human judgement of voice emotion and physical robot playback remain unmeasured.
