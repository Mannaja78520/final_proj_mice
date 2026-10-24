# Gacha: bounded centering, nudge and truthful fault reporting

Owner: codex:10231901-f6cc
Updated: 2026-10-24T22:08:51.905790+07:00
Branch: codex/gacha-safety-1024-f6cc
Tree: E:/final_proj/mice/code/.staging-continue-urdf
Last commit: a3642dd; immutable inherited-source WIP follows
Plan: A47-20 (robot); A0-35 audit done

## Goal
Carry confirmed Gemini safety gaps through isolated fix, actual-source regression, sabotage, independent existing-main review and exact full gate. Preserve user5s pause and queued gacha webUI/autocalibration work. Main owns HOME/physical explanation; user defers physical elbow trim to themselves. No CAD/calibration edits.

## Doing now
Inherited latest frozen root gacha3files only, cpp00bda4e426f2024da77c04c87e2d6946035449f5a29843e745f83faf5ef6fdd7, after actual Gemini15:38freezeACK. Offline implementation prepared: CenterMotion clock uses debounced Hall, configured timeout->jam, no delay; separate motion_result preserves last-prize seq/result. GNUDGE validates signedPWM/duration, busy/missingMotor guard and asynchronous nudge phase (max1000ms data); registry motion flag+COMMANDS docs. CLEAR restores all7 fields and refuses before NVS erase while busy. URDF doc removes all90/arms-straight assumption. Actual-source C++ fixture tests timeout/noisyHall/5spause/fullphase/STOPeveryphase/wrap/invalidnudge/CLEAR. NO compiler/test/QC run yet. Lab hit usage limit mid-release; main reconstructs actual state before QC-only takeover. Clock resumed22:05 and root drift discovered AGAIN: cppAAAE3506...25103B/17:33 now adds intake/GCALIB/GTEST/GDRAIN and new UI/registry work. Preserve late-24oct snapshot; candidate90847e8 remains based older00BDA and MUST NOT overwrite latest user features. Root untouched by this chat.

## Facts found
- Root latest center adds3500ms deadline but finishes done when Hall absent; rawHall bypasses debounce and delay20ms blocks loop. Prior23Oct snapshot was unbounded. Current4cycle device log reports at_hallFalse in2/4, not successful physical centering.
- GNUDGE cpp217 accepts unbounded signedms and delays under router recursive lock; missing busyguard/motionregistry. Negative ms can hold lock/motor for huge unsigned duration. It must become bounded asynchronous job.
- GCFG CLEAR omits7new phase/fallback fields. Root quick5716/0 is explicitly --quick in raw transcript805, not full. Existing native tests cover GachaMath counting, not new FSM.
- snapshots/raw transcript and full audit report are private scratch/gemini-audit-1024; root immutable baseline under frozen-basis. Nong11config arrays unchanged pre/post; physical position unmeasured. Face PC-only startup proof retained by own chat.

## Done / evidence
A0-35 audit findings delivered main/Lab, metadata a3642dd pushed. Main authorized source fixes and will independently review exact diff; no new model/agent. Lab holds exclusive physical driver and has not released QC/native-build resources.

## Next
Reconstruct current actor/source freeze with main; rebase/merge late-24oct feature snapshot into isolated candidate and extend actual-source harness for intake/drain/calibration. Then acquire stopped-owner QC-only lease with evidence, generate headers, compile/regress/sabotage, independent existing-main review and full gate. No actual robot commands, hardware, Hub restart or flash.

## Blocked
QC/build execution waits explicit Lab lease; no physical testing or firmware deployment by this source task while Lab owns hardware. User physical elbow centering is deferred, not passed.

## Latest snapshot
- Current root cpp late24Oct SHAaaae3506d77d3a8fe828e4baa3d8a95619d717102bc33ba5985cfc9b4b117d74 differs again; immutable snapshot in root scratch/gemini-audit-1024/late-24oct. Own candidate90847e8 is NOT validated/deployed; no source write or execution in root by this chat.
