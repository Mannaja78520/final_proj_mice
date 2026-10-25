# Mandatory per-file handoff for every AI

Owner: codex:10241515-audit
Updated: 2026-10-25T07:41:34.357282+07:00
Branch: codex/handoff-files-1025
Tree: E:/final_proj/mice/code/.staging-handoff-files-1025
Last commit: 628f333 (initial task checkpoint)
Plan: A48-16

## Goal
User25Oct: all AIs keep concise per-file change/state/verification/commit handoffs; notify Gemini directly and put the rule in Claude's instructions while its weekly limit is exhausted.

## Doing now
Rules and template implemented; isolated metadata41/0 and three missing-contract sabotages caught. Next publish live instruction files, then deliver Gemini notice and reconcile final per-file inventory.

Before edits: add a shared File status table contract, matching entry-file pointers for Codex/Claude/Gemini, and template regression assertions. Reconcile actual owned Git changes; preserve every other task and dirty root file. No app, firmware, robot, camera, service or QC-driver operation.

## File status
| File | Change | State | Verification | Commit |
| --- | --- | --- | --- | --- |
| `HANDOFF.md` | Per-file handoff contract | done | isolated metadata41/0; scratch/handoff-file-status-1025/metadata-validation.json | uncommitted |
| `handoff/TEMPLATE.md` | Per-file handoff contract | done | isolated metadata41/0; scratch/handoff-file-status-1025/metadata-validation.json | uncommitted |
| `AGENTS.md` | Per-file handoff contract | done | isolated metadata41/0; scratch/handoff-file-status-1025/metadata-validation.json | uncommitted |
| `CLAUDE.md` | Per-file handoff contract | done | isolated metadata41/0; scratch/handoff-file-status-1025/metadata-validation.json | uncommitted |
| `GEMINI.md` | Per-file handoff contract | done | isolated metadata41/0; scratch/handoff-file-status-1025/metadata-validation.json | uncommitted |
| `qc/checks/check_handoff_first.py` | Per-file handoff contract | done | isolated metadata41/0; scratch/handoff-file-status-1025/metadata-validation.json | uncommitted |
| `handoff/tasks/handoff-file-status-1025.md` | Own progress and evidence | pending | owned diff reviewed | this checkpoint |

## Facts found
- Shared template currently names files in Doing now but lacks an exhaustive per-file state/evidence/commit table.
- check_handoff_first currently checks header fields and line budgets, not completeness against Git.
- Active source owner retains QC-only lease; metadata validation here uses isolated temp files only, no shared Hub/fake/browser driver.

## Done
- Read latest8530dbf rules and relevant agents/QC headers; claim A48-16 recorded under shared mutex.

## Next
1. Apply concise common rule/template/provider pointers and structural regression assertions.
2. Validate metadata with temporary fixtures, deliberate missing-contract sabotage, and owned diff review; no full QC claim.
3. Publish live instruction changes, deliver Gemini notice, checkpoint and release own claim.

## Blocked
Nothing for rules/metadata work. Do not run another owner's QC/fake/hardware driver.

## Verification checkpoint
41 isolated metadata assertions passed; removing template table, Claude entry rule and common rule each correctly fails the check. No shared QC/fake/Hub/browser/hardware driver ran. Coverage here protects the rule/template and creation/take behavior; it does not automatically prove every historical changed file was listed.
