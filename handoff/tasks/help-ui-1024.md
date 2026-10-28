# Help matches the actual prize and recognition screens

Owner: codex:10281554-9dc6
Updated: 2026-10-28 15:59 +0700
Branch: codex/help-ui-1024
Tree: E:/final_proj/mice/code/.staging-help-ui-1024
Last commit: 8064292 (HEAD and local origin tracking ref; this continuation is uncommitted, push failed)
Plan: A48-15

## Goal
Human: Help is broken and confusing; prize app and FaceReg differ from Help.
Human correction: ONE fixed Hall at Receive; FOUR magnets on wheel; Drop has no Hall; Receive and Drop are on the same side.

## Doing now
Stopped at recorded merge/commit/push blockers after offline verification and final diff inspection. No task process is running and no QC, service or hardware claim was taken. This task file is saved locally but uncommitted.

## File status
Baseline: 2bd3299. Owned b41604f metadata and e79ea8a source. Final baseline diff has exactly the nine paths below; source unchanged; this handoff is the only tracked edit and cannot be committed in this session. Other root/owner source not ours.

| File | Change | State | Verification | Commit |
| --- | --- | --- | --- | --- |
| main_python/web/help/parts/gacha.html | Actual tabs, one Receive Hall/four magnets; bounded command facts retained from A47-20 | review/QC pending | static browser diagram inspected; preview-evidence.json; no hardware | e79ea8a |
| main_python/web/help/parts/faces.html | Actual three tabs and greeting steps | review/QC pending | latest browser card search and topic navigation pass | e79ea8a |
| main_python/web/help/parts/search.js | Search full topic without neighbour links | review/QC pending | latest card search, no-result, clear, navigation pass manually | e79ea8a |
| main_python/web/help/style.css | Hide technical paths; contain phone overflow | review/QC pending | latest wide hidden paths; phone faces/gacha375px scroll375px | e79ea8a |
| main_python/web/help.html | Builder output | unchanged; review/QC pending | offline source/output equality 1/1; Help links 25/25; builder 14/14 | e79ea8a |
| qc/checks/check_help_topics.py | Permanent content/browser regressions | browser execution blocked | Python syntax 1/1; full check requires hub/browser | e79ea8a |
| docs/systems/hub-web.md | Generated check index | unchanged | not reported stale by check_systems | e79ea8a |
| docs/systems/qc.md | Generated file index | stale; merge first | check_systems 10 passed / 1 failed overall | e79ea8a |
| handoff/tasks/help-ui-1024.md | Current evidence and next actions | local only | handoff 32/32; diff check clean; commit/push blocked | uncommitted |

Historical preview evidence is in ignored root scratch/help-ui-1024; it was not accessed this round. Current evidence is in this tree's ignored scratch/help-ui-1024/offline-checks.log. Root PLAN/BRIDGE and runtime sources were not edited.

## Facts found
- qc/checks/check_systems.py:37 verifies generated subsystem headers; current unmerged tree reports studio.md, app-voice.md, qc.md and agents.md stale. None was changed this round. Reconcile main before generating them.
- qc/checks/check_help_links.py:35 and qc/checks/check_build_web.py:12 provide offline checks; qc/lib/qc.py:383 runs a selected check without the full driver.
- tools/plan.py:62-79 redirects staging plan writes to the root checkout unless MICE_PLAN is set; root writes are forbidden this round. Plan update deferred until merge can reconcile current task state.
- qc/checks/check_help_topics.py:41-43 starts a hub and uses a browser; the complete check and its sabotage proof cannot run under current restrictions.
- tools/build_web.py:38-55 renders one page in memory; this permits a source/output comparison without rewriting other generated pages.
- apps/gacha/index.html:303,346 contain unescaped GCALIB quotes, preventing all script execution; live app has blank tabs and checking status. A47-20 already owns this source.
- Help faces screenshots show Open it while captions claim greeting/rules fields. Actual greeting tab is What the rig says; Move/on selectors belong to each camera row (apps/faces/index.html:296,372).
- Help gacha diagram puts Hall #1/#3 on wheel and Receive opposite Drop, contradicting human hardware correction. Drop mode and guaranteed centering claims are unsupported.
- Help search filters only .f and table rows, ignoring new .info-box content.
- Help .where display:block overrides shared hidden technical labels.

## Done
- Final diff inspection: only this task file changed; CRLF preserved; git diff --check passed. No new commit was possible.
- Offline checks on unmerged HEAD 8064292: check_help_links 25/25, check_build_web 14/14, check_handoff_first 32/32; check_systems 10 passed and 1 failed (four stale headers). Help source/output equality 1/1 and check_help_topics Python syntax 1/1. Total 83 passed, 1 failed, no crashes. Existing builder/system checks include their own negative fixtures; Help search sabotage was not run.
- Invoked these four existing run(t) checks directly through qc.run_check, without run_qc.py. All test temporary files stayed under this tree's ignored scratch/help-ui-1024. Evidence: scratch/help-ui-1024/offline-checks.log. No hub, browser, services, hardware, package build or source edits.
- 2026-10-28: read HANDOFF, AGENTS (Codex entry), task, CLAUDE and coordination. User-authorized takeover by codex:10281554-9dc6 in this tree only. Attempted WIP add/commit/push and git merge main; all blocked before any merge or new commit.
- Read-only live browser reproduction for prize page and Help faces.
- Source e79ea8a built and manually inspected in static preview; original running app/Help untouched. Own generated Hub/Studio/camera/voice output side effects restored before commit.
- Human geometry retained without inferred angular placement. A47-20 bounded GCALIB/GTEST/GNUDGE/GDRAIN wording retained under technical detail; do not restore old mass/100percent claims.
- Evidence: E:/final_proj/mice/code/scratch/help-ui-1024/preview-evidence.json and corrected-mechanism.png. Private evidence ignored; no keys/photos/hardware commands.

## Next
1. Restore authorized Git metadata access and GitHub authentication, commit/push this task checkpoint, then git merge main (currently 023c644); preserve newer owners' work.
2. Repeat allowed focused checks on the merged branch. Obtain existing-main independent review, then coordinated browser/sabotage/full QC only in a separately authorized round.
3. Coordinate original prize-app usability repair with A47-20 owner; Help-only work does not complete that request.

## Blocked
- Git add/commit: cannot create this worktree's index.lock (Permission denied). git merge main: cannot create ORIG_HEAD.lock (Permission denied). No new commit or merge exists.
- git push -u origin codex/help-ui-1024: schannel AcquireCredentialsHandle failed, SEC_E_NO_CREDENTIALS (0x8009030e). Last locally recorded remote commit remains 8064292; remote could not be refreshed.
- Complete check_help_topics, browser regression/sabotage, full QC, hardware, live services, MiceHub.exe rebuild and deployment are outside current user authorization. Existing other-owner QC claim is not released by this task.
- Root PLAN/BRIDGE/shared mutex writes are forbidden. Branch-local plan is older than main and does not contain A48-15; avoid inventing a duplicate before merge.
- Existing-main independent review and original app usability work require their owners. No review, integration, gate or deployment approval claimed.
- check_systems is red: four existing generated subsystem headers are stale. No header regeneration before the required merge; other owners' headers must be preserved.
