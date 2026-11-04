# Follow front chest/face cross-X choreography
Owner: codex:cross-1105-01a1891f
Updated: 2026-11-05T05:01:28.182300+07:00
Branch: private candidate work; shared source read-only
Last commit: this checkpoint
Plan: A56-2

## Goal
User says front-body/face cross-X poses are missing and requests copying those as well as raised arms. Diagnose against original source across6; correct supported crossing/elbow/wrist/forearm relations using bounded work, preserve oldbest. Previous stop of broad RL loops stays: no new training, NN extraction, confidence promotion, hardware motion or Voice. User explicitly authorizes this targeted correction; do not restart old heartbeat trials.

## Doing now
Inspect current selected R4 + cached source/trajectory receipts and actual source images to identify cross windows, limb ownership and loss stage. Separate source ambiguity, retarget loss, physical limits and export deformation. Existing helper/source files read-only; new own .local/cross_x_1105. No source/data worker started yet.

## File status
| File | Change | State | Verification | Commit |
| --- | --- | --- | --- | --- |
| handoff/tasks/cross-x-1105.md | task/scope/facts | current | oldtasks/rules/claims read | this checkpoint |
| docs/PLAN.html | A56-2 | shared update | Plan under mutex | uncommitted |
| docs/plan_state.js | generated plan | shared update | Plan under mutex | uncommitted |
| docs/BRIDGE.md | own claim | shared append | mutex | uncommitted |

## Facts found
Current results6 are accepted best-available R4, not choreography-perfect. Prior chestcross/forearm/phase defects acknowledged. Original cached person22358frames77chunks; no need NN rerun. Actual safety normal11/MUSIC18mm; analytic_sequence_limits_v2 is authoritative per-joint cosine. Existing current Studio/bundles passed software/clock persistence, not human fidelity. All old full data exposed development/regression.

## Done
Read current delivery/handoff and relevant debugging/contract rules; no source modification.

## Next
Register cached paths/versions, inspect real cross frames, audit whether source->reference->input->actual R4 loses crossing, then one justified bounded correction with before/after + no-regression/native export checks. Keep held/inferred/unknown separate; do not invent hidden wrists/crosscut identity. Select new output only after full affected-path/HOME/clock/audio/rounded YAML proof; update results front only when ready.

## Blocked
None yet.
