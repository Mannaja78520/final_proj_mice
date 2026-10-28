# Mandatory per-file handoff for every AI

Owner: codex:10281555-7ab9
Updated: 2026-10-28T09:08:35+00:00
Branch: codex/handoff-files-1025
Tree: E:/final_proj/mice/code/.staging-handoff-files-1025
Last commit: 21b169f (HEAD and local origin tracking; pushed by coordinator per Round 2; current edits uncommitted)
Plan: A48-16

## Goal
User25Oct: all AIs keep concise per-file change/state/verification/commit handoffs; notify Gemini directly and put the rule in Claude's instructions while its weekly limit is exhausted.

## Doing now
Offline work complete; leaving docs/systems/agents.md and this checkpoint uncommitted for coordinator review, commit and push. Final handoff validation and evidence hashes cover this checkpoint. No Git writes, services, hardware or QC driver were used.

## File status
| File | Change | State | Verification | Commit |
| --- | --- | --- | --- | --- |
| `HANDOFF.md` | Per-file handoff contract; merged Help Parity preserved | done | V3: direct handoff 45/0 | 9b57ee9; merged main 023c644 |
| `handoff/TEMPLATE.md` | Per-file handoff contract | done | V3: direct handoff 45/0 | 9b57ee9 |
| `AGENTS.md` | Codex per-file rule; merged Help Parity preserved | done | V3: direct handoff 45/0 | 9b57ee9; merged main 023c644 |
| `CLAUDE.md` | Claude per-file rule; merged Help Parity preserved | done | V3: direct handoff 45/0 | 9b57ee9; merged main 023c644 |
| `GEMINI.md` | Gemini per-file rule; merged Help Parity preserved | done | V3: direct handoff 45/0 | 9b57ee9; merged main 023c644 |
| `qc/checks/check_handoff_first.py` | Per-file metadata regression contract | done | V3: direct handoff 45/0 | 9b57ee9 |
| `docs/systems/agents.md` | Regenerate task inventory: remove obsolete usability-review-1026 entry; 38 to 37 files | done locally | V3: direct systems 13/0; systems.py verify exit 0 | uncommitted |
| `handoff/tasks/handoff-file-status-1025.md` | Reconcile Round 2 merge, evidence, file inventory and coordinator handoff | done locally; coordinator publication pending | V3: direct handoff 45/0; diff/inventory checked | uncommitted |
| `scratch/handoff-file-status-1025/round2-metadata-20261028.json` | Post-merge direct-check results, generated-output hashes and final manifest | done locally | V3 final: handoff 45/0 + systems 13/0; hashes recorded | uncommitted; ignored scratch |
| `scratch/handoff-file-status-1025/resume-metadata-20261028.json` | Earlier pre-merge focused evidence; unchanged this round | historical | V2: 41/0; superseded by V3 | uncommitted; ignored scratch |

## Facts found
- HANDOFF.md:29-40 requires exact per-file evidence/commit rows and Git reconciliation; owned working files are listed above.
- docs/COORDINATION.md:193 identifies AGENTS.md as Codex's entry; no CODEX.md exists. Read HANDOFF, task, AGENTS and CLAUDE.
- qc/checks/check_handoff_first.py:53-70 checks the table contract, provider rules, task metadata and 150-line budgets; it does not audit exhaustive Git ownership.
- qc/checks/check_handoff_first.py:72-89 tests new/take/done in temporary files. All direct-check fixtures were confined to this tree.
- qc/checks/check_systems.py:34-98 checks the real map plus isolated stale-header/ownership regressions; it needs no service or QC driver.
- tools/systems.py:164-189 found only agents.md stale; tools/systems.py:214-235 generates all 36 headers/index while retaining text above the marker.
- docs/systems/agents.md:19 now lists 37 files; the merged tree lacks handoff/tasks/usability-review-1026.md, so the stale generated reference was removed.
- tools/plan.py:78-81 redirects staging plan writes to the prohibited root checkout; shared PLAN/BRIDGE/mutex updates remain blocked.
- docs/PLAN.html:1643 already records A48-16 done. Round 2 verifies existing work; no unrelated task takeover.

## Done
- Round 2 step 3: direct post-regeneration checks passed 58 assertions / 0 failures (handoff 45/0, systems 13/0). Final diff/inventory and whitespace review cover exactly two tracked edits; no untracked publication files. Evidence records hashes and local ref identity.
- Round 2 step 1: clean start at 21b169f, matching local origin/codex/handoff-files-1025; local main 023c644 is its ancestor. Coordinator confirms merge/push complete. No Git write or network retry made.
- Reconciled original rule/template/check changes with merged Help Parity additions; no other owner's work dropped. Existing task ownership retained under explicit continuation.
- Round 2 step 2: direct pre-regeneration checks: handoff 45 passed / 0 failed; systems 12 passed / 1 failed solely for agents.md. Saved V3 evidence before repair.
- Ran python -B tools/systems.py build. Inspected all 36 output files: only agents.md changed; existing line endings and all other output bytes preserved. systems.py verify then passed (exit 0); git diff --check passed.
- Historical: rules/template/check 9b57ee9 pushed; direct native Gemini notice delivered; Claude rule added without a quota-consuming call. No repeat notice this round.

## Next
1. Coordinator: review only docs/systems/agents.md and this task file, then commit and push codex/handoff-files-1025. Ignored scratch is local evidence, not a publication file.
2. Coordinator handles any required real-root plan/claim bookkeeping. A48-16 remains done; no main merge/push or unrelated owner-ledger changes are authorized here.

## Blocked
- Round 2 explicitly prohibits git add/merge/commit/push: sandbox Git locks and credential store are unavailable. Coordinator owns publication; no attempts this round. Earlier failed merge/add and SEC_E_NO_CREDENTIALS are historical, not pending retries.
- Real-root PLAN/BRIDGE/mutex writes are outside this tree and prohibited. No alternate plan copy or permission workaround used.
- Full QC driver, main integration/push, MiceHub.exe rebuild, live services and robot/ESP32/USB-board/camera/person tests are excluded by User28Oct; not run or needed for this offline documentation refresh.
- Gemini and other owners retain their own ledger adoption/corrections. Historical external delivery evidence is not a fresh adoption check.

## Verification checkpoint
V3: scratch/handoff-file-status-1025/round2-metadata-20261028.json. Direct real qc.Case checks on merged HEAD 21b169f plus the two local documentation edits; all temporary fixtures inside this tree. Final results: handoff 45/0 and systems 13/0, 58/0 total; system-map verify and git diff --check passed. Baseline failure, repair, input hashes and final file inventory are recorded. This is focused offline evidence, not full QC or hardware approval. No shared QC/fake/Hub/browser/hardware driver, firmware build or full gate.

V2: scratch/handoff-file-status-1025/resume-metadata-20261028.json, pre-merge handoff 41/0; historical only.
V1 (historical, not rerun): metadata-validation.json, live-rules.json and gemini-notice.json under scratch/handoff-file-status-1025 were recorded by the original session. The three contract mutations were detected then; those old artifacts are not present in this checkout and were not recreated.

## Adoption audit follow-up
Historical owner audit: Gemini committed cce6e57 with its 56-file ledger. Four wrong SHA rows were reported directly: notices/tabs should use 2bd3299, helpgacha b5a161b, helpfirmware ce0aeb0; corrections remain theirs. The prior Gemini handoff QC 55/0 was not this task's authorized driver evidence. Prior audit evidence was recorded as scratch/handoff-file-status-1025/gemini-ledger-provenance-check.json, not present here. No new messages, adoption claims or edits to another task this round.
