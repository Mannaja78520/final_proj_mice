# Help matches the actual prize and recognition screens

Owner: codex:10242258-597a
Updated: 2026-10-25
Branch: codex/help-ui-1024
Tree: E:/final_proj/mice/code/.staging-help-ui-1024
Last commit: e79ea8a source; this checkpoint records final handoff
Plan: A48-15

## Goal
Human: Help is broken and confusing; prize app and FaceReg differ from Help.
Human correction: ONE fixed Hall at Receive; FOUR magnets on wheel; Drop has no Hall; Receive and Drop are on the same side.

## Doing now
Candidate ready for existing-main review and coordinated QC in source integration batch. No QC driver, source deployment or hardware. Static preview runs on loopback50140; previous62648 expired after interruption.

## File status
Baseline: 2bd3299. Owned b41604f metadata and e79ea8a source. Final baseline diff has exactly the nine paths below; source clean, only this handoff pending before checkpoint. Other root/owner source not ours.

| File | Change | State | Verification | Commit |
| --- | --- | --- | --- | --- |
| main_python/web/help/parts/gacha.html | Actual tabs, one Receive Hall/four magnets; bounded command facts retained from A47-20 | review/QC pending | static browser diagram inspected; preview-evidence.json; no hardware | e79ea8a |
| main_python/web/help/parts/faces.html | Actual three tabs and greeting steps | review/QC pending | latest browser card search and topic navigation pass | e79ea8a |
| main_python/web/help/parts/search.js | Search full topic without neighbour links | review/QC pending | latest card search, no-result, clear, navigation pass manually | e79ea8a |
| main_python/web/help/style.css | Hide technical paths; contain phone overflow | review/QC pending | latest wide hidden paths; phone faces/gacha375px scroll375px | e79ea8a |
| main_python/web/help.html | Builder output | review/QC pending | web build JS syntax passed; no full QC | e79ea8a |
| qc/checks/check_help_topics.py | Permanent content/browser regressions | pending execution | Python compile only; no QC/sabotage run | e79ea8a |
| docs/systems/hub-web.md | Generated check index | review/QC pending | builder result trimmed to own new check; no systems QC | e79ea8a |
| docs/systems/qc.md | Generated file index | review/QC pending | builder result trimmed to own new file; no systems QC | e79ea8a |
| handoff/tasks/help-ui-1024.md | Current evidence and next actions | pending | reconcile final diff before checkpoint | this checkpoint |

Private preview/evidence scripts live in ignored root scratch/help-ui-1024. Root plan/BRIDGE bookkeeping owned entries only. No config changes; no unrelated generated outputs will be committed.

## Facts found
- apps/gacha/index.html:303,346 contain unescaped GCALIB quotes, preventing all script execution; live app has blank tabs and checking status. A47-20 already owns this source.
- Help faces screenshots show Open it while captions claim greeting/rules fields. Actual greeting tab is What the rig says; Move/on selectors belong to each camera row (apps/faces/index.html:296,372).
- Help gacha diagram puts Hall #1/#3 on wheel and Receive opposite Drop, contradicting human hardware correction. Drop mode and guaranteed centering claims are unsupported.
- Help search filters only .f and table rows, ignoring new .info-box content.
- Help .where display:block overrides shared hidden technical labels.

## Done
- Read-only live browser reproduction for prize page and Help faces.
- Source e79ea8a built and manually inspected in static preview; original running app/Help untouched. Own generated Hub/Studio/camera/voice output side effects restored before commit.
- Human geometry retained without inferred angular placement. A47-20 bounded GCALIB/GTEST/GNUDGE/GDRAIN wording retained under technical detail; do not restore old mass/100percent claims.
- Evidence: E:/final_proj/mice/code/scratch/help-ui-1024/preview-evidence.json and corrected-mechanism.png. Private evidence ignored; no keys/photos/hardware commands.

## Next
1. Existing main independently review exact e79ea8a Help/test diff, preserve A47-20 command-contract changes when integrating. New main8530dbf may need merge; no blind restore.
2. Run check_help_topics (including sabotage of search fix), affected checks and full QC only after exclusive resource coordination; build Help from parts. No review/gate/deployment approval claimed.
3. Finish the original app usability repair with A47-20 gacha owner; this task changes Help only. Other Help sections remain unaudited. Do not mark user request complete from static preview.

## Blocked
- QC-only resource held by codex:10231901-f6cc for isolated gacha/Studio/TV gate.
