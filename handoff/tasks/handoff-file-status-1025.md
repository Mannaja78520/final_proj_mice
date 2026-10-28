# Mandatory per-file handoff for every AI

Owner: codex:10281555-7ab9
Updated: 2026-10-28T09:00:10.569Z
Branch: codex/handoff-files-1025
Tree: E:/final_proj/mice/code/.staging-handoff-files-1025
Last commit: 83c05a3 (last locally recorded push; unchanged; this checkpoint is uncommitted)
Plan: A48-16

## Goal
User25Oct: all AIs keep concise per-file change/state/verification/commit handoffs; notify Gemini directly and put the rule in Claude's instructions while its weekly limit is exhausted.

## Doing now
Stopped at infrastructure blockers. Focused pre-merge metadata verification is complete; only this task file is changed. No merge, commit, push, service action or hardware work completed this round.

## File status
| File | Change | State | Verification | Commit |
| --- | --- | --- | --- | --- |
| `HANDOFF.md` | Per-file handoff contract | done | V2: direct pre-merge metadata 41/0 | 9b57ee9 |
| `handoff/TEMPLATE.md` | Per-file handoff contract | done | V2: direct pre-merge metadata 41/0 | 9b57ee9 |
| `AGENTS.md` | Per-file handoff contract | done | V2: direct pre-merge metadata 41/0 | 9b57ee9 |
| `CLAUDE.md` | Per-file handoff contract | done | V2: direct pre-merge metadata 41/0 | 9b57ee9 |
| `GEMINI.md` | Per-file handoff contract | done | V2: direct pre-merge metadata 41/0 | 9b57ee9 |
| `qc/checks/check_handoff_first.py` | Per-file handoff contract | done | V2: direct pre-merge metadata 41/0 | 9b57ee9 |
| `handoff/tasks/handoff-file-status-1025.md` | Resume, merge blockers and focused evidence | done locally; commit blocked | V2: metadata 41/0; diff checked | uncommitted |
| `scratch/handoff-file-status-1025/resume-metadata-20261028.json` | Focused-check evidence and hashes | done locally | V2: 41/0; pre-merge only | uncommitted; ignored scratch |

## Facts found
- HANDOFF.md:29-40 requires exact per-file state/evidence/commit rows and Git reconciliation; the task now records the uncommitted checkpoint honestly.
- handoff/TEMPLATE.md:15 and qc/checks/check_handoff_first.py:53-59 enforce the table and provider rules; direct run passed 41/0.
- qc/checks/check_handoff_first.py:65-70 checks task fields/line budgets, not exhaustive Git ownership. No automatic ledger-completeness claim.
- qc/checks/check_handoff_first.py:72-89 tests new/take/done in temporary files; this run placed fixtures under this tree and used no QC driver.
- tools/plan.py:78-81 redirects staging plan writes to the prohibited root checkout; shared plan/mutex updates are blocked.
- docs/COORDINATION.md:193 identifies AGENTS.md as the Codex entry; read it with HANDOFF and CLAUDE.
- Local main 023c644 already contains 9b57ee9. Its four entry/rule files also add Help Parity; preserve those additions when the merge becomes possible.

## Done
- Current round: direct check_handoff_first passed 41 assertions / 0 failures; git diff --check passed. No conflict entries; HEAD and origin tracking remain 83c05a3.
- Attempted pre-step git add and git merge main: both exited 1; index.lock and ORIG_HEAD.lock creation denied. Merge did not begin; no WIP commit or push possible.
- Resumed User28Oct task; clean branch at 83c05a3. No pre-existing uncommitted files.
- Rules/template/regression9b57ee9 pushed;6live local files hash-match checked, unrelated dirty data preserved.
- Direct native Gemini notice delivered; proof scratch/handoff-file-status-1025/gemini-notice.json. Claude receives rule through CLAUDE.md, no quota-consuming invocation.
- Read latest8530dbf rules and relevant agents/QC headers; claim A48-16 recorded under shared mutex.

## Next
1. Restore allowed Git metadata writes and Git HTTPS access; preserve this uncommitted task update.
2. Review/commit this checkpoint, then git push -u origin codex/handoff-files-1025. Set Doing now and merge the then-current local main into this branch only.
3. Reconcile merged instructions and task history; rerun direct check_handoff_first, update every checkpoint field, commit and push. Current 41/0 is pre-merge evidence only.
4. Branch-to-main integration/full QC stay deferred. Other owners migrate/correct their own ledgers.

## Blocked
- Git add failed to create index.lock; git merge main failed to create ORIG_HEAD.lock under .git/worktrees/-staging-handoff-files-1025: Permission denied. Neither merge nor commit began; no ACL/permission workaround attempted.
- git ls-remote --heads origin codex/handoff-files-1025 failed: schannel AcquireCredentialsHandle SEC_E_NO_CREDENTIALS (0x8009030e). No new push attempted without a commit; remote state cannot be freshly confirmed.
- Shared root PLAN/BRIDGE/mutex writes are outside the permitted tree. A48-16 remains the existing plan ID; no root plan update made.
- User28Oct excludes full QC, main integration/push, MiceHub.exe rebuild, live services, robot/board/camera/person tests. No such work ran.
- Gemini/other owners retain their ledger adoption and corrections; no external messages sent this round.

## Verification checkpoint
V2 (2026-10-28, pre-merge): `scratch/handoff-file-status-1025/resume-metadata-20261028.json`; direct real qc.Case/check_handoff_first, 41 passed / 0 failed. Fixtures stayed in this tree. Evidence has file SHA256 values; ignored scratch is not staged. Current tracked diff is only this task file; main was not changed.

Historical V1 (not rerun on live root):
V1: scratch/handoff-file-status-1025/metadata-validation.json. Live six-file hash manifest: scratch/handoff-file-status-1025/live-rules.json. Delivery receipt: scratch/handoff-file-status-1025/gemini-notice.json.
41 isolated metadata assertions passed; removing template table, Claude entry rule and common rule each correctly fails the check. No shared QC/fake/Hub/browser/hardware driver ran. Coverage here protects the rule/template and creation/take behavior; it does not automatically prove every historical changed file was listed.

## Adoption audit follow-up
Gemini committedcce6e57 own56file ledger; source owner adopted exact columns in both task files. Independent path-vs-commit check caught4wrong Gemini SHA rows: notices/tabs should2bd3299, helpgacha b5a161b, helpfirmware ce0aeb0. Correction notice visibly delivered to nativeed497bb9, Working; only its own ledger allowed. Gemini also ran handoffQC55/0 despite no-driver instruction; source QC owner notified, avoid shared dashboard as gate proof. No main QC/hardware/appsource action. Report scratch/handoff-file-status-1025/gemini-ledger-provenance-check.json; not final approval of Gemini work. Requested rules/notice task staysdone; Gemini owns corrections.
