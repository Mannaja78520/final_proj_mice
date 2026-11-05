# Automatic model routing for project work
Owner: codex:cross-1105-01a1891f
Updated: 2026-11-06T02:07:21.434400+07:00
Plan: A57-3
Branch: PC instruction-only; no runtime source promotion
Last commit: this checkpoint

## Goal
User requests automatically deciding between Luna for simple checks/QC and Sol for demanding work, without repeatedly asking which model.

## Doing now
COMPLETE: AGENTS.md requests task-based Codex delegation. Luna handles bounded check batches; Sol retains complex diagnosis/safety; tiny scripts run directly. Fresh worker context and compact briefs, no duplicate primarySol worker. Primary model/globalconfig unchanged.

## File status
| File | Change | State | Verification | Commit |
| --- | --- | --- | --- | --- |
| AGENTS.md | automatic bounded Luna/Sol delegation | done | exact diff/check PASS; existing handoff QC85/0 | this checkpoint |
| handoff/tasks/model-routing-1106.md | task/evidence | current | owner/claim recorded | this checkpoint |
| docs/BRIDGE.md | instruction claim/release | current | mutex | this checkpoint |
| docs/PLAN.html | A57-3 status | current | tools/plan.py | shared dirty changes preserved |
| docs/plan_state.js | generated plan | current | tools/plan.py | shared dirty changes preserved |
| .local/cross_x_1105/model_routing_push_receipt.json | task/rule backup receipt | done | remote tree allowlist AGENTS+task only | git-ignored |

## Facts found
Official https://learn.chatgpt.com/docs/agent-configuration/subagents documents explicit or applicable AGENTS-requested delegation, per-worker model overrides and extra worker context costs. Current collaboration API exposes gpt-6-luna and gpt-6.1-sol, with fork_turns=none required for explicit model overrides. No tool changes the primary model in-place. Local config currently selects gpt-6.1-sol/xhigh; do not silently change global configuration or claim primary switching.

## Done
Added Codex-only automatic routing instructions. Existing handoff/instruction check85PASS/0FAIL; git diff --check PASS; exact diff inspected. First standalone harness import resolved qc namespace instead of qc/lib and raised before checks; corrected path to the same qc/run_qc.py import setup, no test disabled. No artificial worker spawned for small instruction validation. No runtime/app source/config/services/robot/model trials changed. Shared pre-existing plan dirtychanges preserved, not committed as ours.
Read official documentation and current local supported capabilities. Existing gesture task remains independent and OPEN; no old numerical workers relaunched.

## Next
Apply this policy to subsequent authorized work without asking for per-step model selection. Small standalone checks remain scripts. Larger repeatable QC batches go to one compact Luna worker; ambiguous failures return to Sol once. No new request required to select the worker model; all resource/review/safety claims still apply.

## Limits
Dispatch is a policy followed by Codex, not a universal app-level automatic main-model router. Worker startup/context also consumes quota; no savings percentage promised. Other providers retain their supported models. Preserve all QC ownership, safety and required review rules.
