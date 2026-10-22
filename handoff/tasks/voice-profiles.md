# Named local character profiles

Owner: codex:10221534-bb09
Updated: 2026-10-22T16:07:17.980701+07:00
Branch: task/A45-27-10221534-bb09
Last commit: 060c9c0 (packaged-path checkpoint follows)
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
Full gate at060c9c0 passed7544/0. Final packaging inspection found frozen
hub reading temporary instead of external user-data folder. Fixed root derivation;
3 actual target assertions added. Deliberate regression caught1/1, restored green.
All8 sabotage cases caught. Final exact-tree full gate follows this checkpoint.
No hardware moved. Prior4-failure run and aborted quick retained as historical evidence.

## Next
1. Run final full quiet QC after packaged-path fix; source frozen until completion.
2. Inspect exact final diff, commit/push branch and PR; merge only after full QC green. Reviewer integration findings fixed (old-profile migration, Windows aliases, captured-path reads).
3. Preserve root dirty work while deploying merged A45-26+A45-27: systems build, exe via spec, restart own hub/voice/feeling services, verify live profiles and prior 50-case replay. No robot motion without ready hardware.
4. Mark plan done only after deployment verification; update this file and push at every stop.

## Blocked
- No external prerequisite for implementation. Full QC pending; actual human judgement of voice emotion and real robot playback remain unmeasured.
