# Gacha: bounded centering, nudge and truthful fault reporting

Owner: codex:10231901-f6cc
Updated: 2026-10-25T07:43:24+07:00
Branch: codex/gacha-safety-1024-f6cc
Tree: E:/final_proj/mice/code/.staging-continue-urdf
Last commit: 3bb6c07; next WIP checkpoint includes pending source below
Plan: A47-20 (robot); A0-35 audit done

## Goal
Carry confirmed Gemini safety gaps through isolated fix, actual-source regression, sabotage, independent existing-main review and exact full gate. Preserve user5s pause and queued gacha webUI/autocalibration work. Main owns HOME/physical explanation; user defers physical elbow trim to themselves. No CAD/calibration edits.

## Doing now
Reconcile 25Oct mandatory per-file handoff and all interrupted A47-20/A48-14 work before another code step. Preserve completed UI/render work; native162/0 and actual UI203/0 combined; next reconcile latest root8530dbf (Gemini partial fixes/rules), Help owner, docs/registry/system generation, sabotage/build/affected checks, exact-source independent review then full gate. No physical commands/config/Hub restart.

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

## File handoff
File | Change | State | Verification/evidence | Commit
--- | --- | --- | --- | ---
firmware/config/esp32_hardware_gacha_module.h | Bounded timing/default constants | pending | prior native135/0; final build pending | 3bb6c07
firmware/src/modules/gacha/GachaMath.h | Nonblocking bounded CenterMotion | pending | prior native135/0; sabotage pending | 90847e8
firmware/src/modules/gacha/GachaModule.h | Async jobs/phases, progress, learned advance | pending | prior native135/0; final build pending | 3bb6c07
firmware/src/modules/gacha/GachaModule.cpp | Bounded jobs/STOP, strict args, per-pocket verification; no-rock/settle/fallback truthful | pending | latest native162/0 incl no-rock/settle/pause0/timedfallback; no full signoff | uncommitted after3bb6c07
firmware/config/commands.json | Preserve latest features; truthful async Hall contract | pending | generation/docs checks pending | uncommitted
firmware/COMMANDS.md | Limits/progress/timed result, no mass/centre guarantee | pending | contract checks pending | uncommitted
apps/gacha/index.html | Parse fixes, motion status, per-pocket units, STOP | pending | current Gacha16/0 + syntax4/0,8magnets/4slots, GSPIN1; sabotage/review pending | uncommitted
apps/gacha/motion.js | Separate async polling class | pending | browser demonstrated phase/jam/STOP; sabotage pending | uncommitted
qc/checks/check_gacha_motion.py | Compile actual source methods/commands with fake IO | pending | native162/0 after physical-phase fixture update | 3bb6c07
qc/data/gacha_motion.cpp | Motor/deadline/args/calib/drain/test/default/no-rock regressions | pending | native162/0, incl persistent Hall during rest and verified each pocket | uncommitted
qc/checks/check_gacha_ui.py | Actual page->Hub->fake board;8magnets/4pockets | pending | current16/0 with8magnets/4slots; sabotage pending | uncommitted
qc/checks/check_remote_scripts.py | Parse shipped inline/helper JS | pending |current4/0; sabotage pending | uncommitted
docs/urdf_nong.md | Separate native zero/Studio zero/90/HOME | done | independent source review earlier; no geometry edits | 90847e8
handoff/tasks/gacha-safety-1024.md | Reconciled per-file current state | pending | explicit file ledger; final completion later | next WIP

- Current combined evidence: scratch/continue-urdf-1023/ui-native-affected-1025-v1.log =203/0 (25.5s), not full QC.
