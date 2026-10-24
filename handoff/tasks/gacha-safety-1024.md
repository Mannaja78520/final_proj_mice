# Gacha: bounded centering, nudge and truthful fault reporting

Owner: codex:10231901-f6cc
Updated: 2026-10-24T22:51:43.017840+07:00
Branch: codex/gacha-safety-1024-f6cc
Tree: E:/final_proj/mice/code/.staging-continue-urdf
Last commit: a3642dd; immutable inherited-source WIP follows
Plan: A47-20 (robot); A0-35 audit done

## Goal
Carry confirmed Gemini safety gaps through isolated fix, actual-source regression, sabotage, independent existing-main review and exact full gate. Preserve user5s pause and queued gacha webUI/autocalibration work. Main owns HOME/physical explanation; user defers physical elbow trim to themselves. No CAD/calibration edits.

## Doing now
Latest committed root2bd3299 merged into own branch ba80ca8, preserving TV/help/screenshots/perf changes (73files) plus uncommitted AAAE17:33 gacha features. Backend now includes intake, async bounded calibration with verified learned advance, per-pocket self-test, bounded/open-event drain, async validated nudge, full CLEAR, truthfully faulted missing Hall and separate motion_result. Actual-source native first123/0; after independent-main findings corrected strict signed GSPIN pre-multiply bound, GTEST per-pocket verification and Hall lost during pause:135/0. No full/final review/sabotage yet. QC-only lease explicitly released by Lab22:12 and claimed22:16; physical stopped/separate, no live command/flash/restart. New UI syntax defect belongs current2bd blob (not olde30): claim minimal gacha syntax/async status + actual fake browser checks. Main independent final review waits exact whole batch. Root untouched.

## Facts found
- Root latest center adds3500ms deadline but finishes done when Hall absent; rawHall bypasses debounce and delay20ms blocks loop. Prior23Oct snapshot was unbounded. Current4cycle device log reports at_hallFalse in2/4, not successful physical centering.
- GNUDGE cpp217 accepts unbounded signedms and delays under router recursive lock; missing busyguard/motionregistry. Negative ms can hold lock/motor for huge unsigned duration. It must become bounded asynchronous job.
- GCFG CLEAR omits7new phase/fallback fields. Root quick5716/0 is explicitly --quick in raw transcript805, not full. Existing native tests cover GachaMath counting, not new FSM.
- snapshots/raw transcript and full audit report are private scratch/gemini-audit-1024; root immutable baseline under frozen-basis. Nong11config arrays unchanged pre/post; physical position unmeasured. Face PC-only startup proof retained by own chat.

## Done / evidence
A0-35 audit findings delivered main/Lab, metadata a3642dd pushed. Main authorized source fixes and will independently review exact diff; no new model/agent. Lab holds exclusive physical driver and has not released QC/native-build resources.

## Next
Fix latest gacha UI quote syntax with fast parse regression and real browser fake-load/control/fault-poll coverage. Reconcile command docs/registry contracts; update source headers via generators. Strengthen native defaults/pause/self-test cases, run deliberate sabotage, gacha firmware/native/affected checks. Send stable full diff and evidence to existing main for independent review, then exact full gate. Preserve root user data/latest features; no physical promotion/flash permission.

## Blocked
No physical testing, camera, Hub restart or firmware deployment acquired. User physical elbow centering is deferred, not passed. Root main/source features must be reconciled before any later authorized integration; do not overwrite with old snapshot.

## Latest snapshot
- Current root cpp late24Oct SHAaaae3506d77d3a8fe828e4baa3d8a95619d717102bc33ba5985cfc9b4b117d74 differs again; immutable snapshot in root scratch/gemini-audit-1024/late-24oct. Own candidate90847e8 is NOT validated/deployed; no source write or execution in root by this chat.
