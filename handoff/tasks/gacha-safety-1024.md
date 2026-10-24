# Gacha: bounded centering, nudge and truthful fault reporting

Owner: codex:10231901-f6cc
Updated: 2026-10-24T15:56:11.451017+07:00
Branch: codex/gacha-safety-1024-f6cc
Tree: E:/final_proj/mice/code/.staging-continue-urdf
Last commit: a3642dd; immutable inherited-source WIP follows
Plan: A47-20 (robot); A0-35 audit done

## Goal
Carry confirmed Gemini safety gaps through isolated fix, actual-source regression, sabotage, independent existing-main review and exact full gate. Preserve user5s pause and queued gacha webUI/autocalibration work. Main owns HOME/physical explanation; user defers physical elbow trim to themselves. No CAD/calibration edits.

## Doing now
Inherited latest frozen root gacha3files only, cpp00bda4e426f2024da77c04c87e2d6946035449f5a29843e745f83faf5ef6fdd7, after actual Gemini15:38freezeACK. Offline implementation prepared: CenterMotion clock uses debounced Hall, configured timeout->jam, no delay; separate motion_result preserves last-prize seq/result. GNUDGE validates signedPWM/duration, busy/missingMotor guard and asynchronous nudge phase (max1000ms data); registry motion flag+COMMANDS docs. CLEAR restores all7 fields and refuses before NVS erase while busy. URDF doc removes all90/arms-straight assumption. Actual-source C++ fixture tests timeout/noisyHall/5spause/fullphase/STOPeveryphase/wrap/invalidnudge/CLEAR. NO compiler/test/QC run yet; waiting explicit Lab lease. Root source untouched.

## Facts found
- Root latest center adds3500ms deadline but finishes done when Hall absent; rawHall bypasses debounce and delay20ms blocks loop. Prior23Oct snapshot was unbounded. Current4cycle device log reports at_hallFalse in2/4, not successful physical centering.
- GNUDGE cpp217 accepts unbounded signedms and delays under router recursive lock; missing busyguard/motionregistry. Negative ms can hold lock/motor for huge unsigned duration. It must become bounded asynchronous job.
- GCFG CLEAR omits7new phase/fallback fields. Root quick5716/0 is explicitly --quick in raw transcript805, not full. Existing native tests cover GachaMath counting, not new FSM.
- snapshots/raw transcript and full audit report are private scratch/gemini-audit-1024; root immutable baseline under frozen-basis. Nong11config arrays unchanged pre/post; physical position unmeasured. Face PC-only startup proof retained by own chat.

## Done / evidence
A0-35 audit findings delivered main/Lab, metadata a3642dd pushed. Main authorized source fixes and will independently review exact diff; no new model/agent. Lab holds exclusive physical driver and has not released QC/native-build resources.

## Next
Acquire explicit Lab QC/native-build lease, generate tables/system headers, compile/run actual-source regression. Fix only verified failures; prove deliberate breakage via sabotage, then send exact diff+evidence existing main for independent review. Full gate after review, no blind promotion/flash into dirty root. Preserve user queued webUI/autocalibration separately.

## Blocked
QC/build execution waits explicit Lab lease; no physical testing or firmware deployment by this source task while Lab owns hardware. User physical elbow centering is deferred, not passed.

## Latest snapshot
- Root cpp remains separately frozen; current hash 00bda4e426f2024da77c04c87e2d6946035449f5a29843e745f83faf5ef6fdd7. Own source candidate WIP is not validated or deployed.
