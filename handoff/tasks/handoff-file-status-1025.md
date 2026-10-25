# Mandatory per-file handoff for every AI

Owner: codex:10241515-audit
Updated: 2026-10-25T07:45:35.200333+07:00
Branch: codex/handoff-files-1025
Tree: E:/final_proj/mice/code/.staging-handoff-files-1025
Last commit: 9b57ee9 (rules/template/regression)
Plan: A48-16

## Goal
User25Oct: all AIs keep concise per-file change/state/verification/commit handoffs; notify Gemini directly and put the rule in Claude's instructions while its weekly limit is exhausted.

## Doing now
Completed requested shared/provider rules and template; live files verified. Gemini notice delivered, receipt visible; its ledger migration is separate follow-up. Claude rule ready on resume. No app/hardware/QC-driver work.


## File status
| File | Change | State | Verification | Commit |
| --- | --- | --- | --- | --- |
| `HANDOFF.md` | Per-file handoff contract | done | V1: isolated metadata41/0 | 9b57ee9 |
| `handoff/TEMPLATE.md` | Per-file handoff contract | done | V1: isolated metadata41/0 | 9b57ee9 |
| `AGENTS.md` | Per-file handoff contract | done | V1: isolated metadata41/0 | 9b57ee9 |
| `CLAUDE.md` | Per-file handoff contract | done | V1: isolated metadata41/0 | 9b57ee9 |
| `GEMINI.md` | Per-file handoff contract | done | V1: isolated metadata41/0 | 9b57ee9 |
| `qc/checks/check_handoff_first.py` | Per-file handoff contract | done | V1: isolated metadata41/0 | 9b57ee9 |
| `handoff/tasks/handoff-file-status-1025.md` | Own progress and evidence | done | owned diff reviewed | this checkpoint |

## Facts found
- Shared template currently names files in Doing now but lacks an exhaustive per-file state/evidence/commit table.
- check_handoff_first currently checks header fields and line budgets, not completeness against Git.
- Active source owner retains QC-only lease; metadata validation here uses isolated temp files only, no shared Hub/fake/browser driver.

## Done
- Rules/template/regression9b57ee9 pushed;6live local files hash-match checked, unrelated dirty data preserved.
- Direct native Gemini notice delivered; proof scratch/handoff-file-status-1025/gemini-notice.json. Claude receives rule through CLAUDE.md, no quota-consuming invocation.
- Read latest8530dbf rules and relevant agents/QC headers; claim A48-16 recorded under shared mutex.

## Next
1. Requested rule/notice task complete; task remains until branch integration. Gemini owns its ledger acknowledgment/migration.
2. Source integration can include regression commit9b57ee9 in its next coordinated gate; this metadata-only validation is not fullQC or app deployment.
3. Other task owners migrate their active tables on resume; never fabricate their file ownership/evidence.

## Blocked
Nothing for rules/metadata work. Do not run another owner's QC/fake/hardware driver.

## Verification checkpoint
V1: scratch/handoff-file-status-1025/metadata-validation.json. Live six-file hash manifest: scratch/handoff-file-status-1025/live-rules.json. Delivery receipt: scratch/handoff-file-status-1025/gemini-notice.json.
41 isolated metadata assertions passed; removing template table, Claude entry rule and common rule each correctly fails the check. No shared QC/fake/Hub/browser/hardware driver ran. Coverage here protects the rule/template and creation/take behavior; it does not automatically prove every historical changed file was listed.
