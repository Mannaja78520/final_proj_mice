# Follow front chest/face cross-X choreography
Owner: codex:cross-1105-01a1891f
Updated: 2026-11-05T05:01:28.182300+07:00
Branch: private candidate work; shared source read-only
Last commit: this checkpoint
Plan: A57-2

## Goal
User says front-body/face cross-X poses are missing and requests copying those as well as raised arms. User adds backward hand/arm flick, anchor Come and Cheer1:50(110s), similar gesture in nearly allclips. Diagnose against original source across6; correct supported crossing/elbow/wrist/forearm relations using bounded work, preserve oldbest. Previous stop of broad RL loops stays: no new training, NN extraction, confidence promotion, hardware motion or Voice. User explicitly authorizes this targeted correction; do not restart old heartbeat trials.

## Doing now
Confirmed actual Blood27.8..29s comparison: source chestcross28.63 vs actualR4 oneup/oneout mismatch. Next exact Come110s backward-sweep source+actual review and cached all6 relation/phase audit. Inspect current selected R4 + cached source/trajectory receipts and actual source images to identify cross windows, limb ownership and loss stage. Separate source ambiguity, retarget loss, physical limits and export deformation. Existing helper/source files read-only; new own .local/cross_x_1105. No source/data worker started yet.

## File status
| File | Change | State | Verification | Commit |
| --- | --- | --- | --- | --- |
| handoff/tasks/cross-x-1105.md | task/scope/facts | current | oldtasks/rules/claims read | this checkpoint |
| docs/PLAN.html | A57-2 | shared update | Plan under mutex | uncommitted |
| docs/plan_state.js | generated plan | shared update | Plan under mutex | uncommitted |
| docs/BRIDGE.md | own claim | shared append | mutex | uncommitted |

| .local/cross_x_1105/inspect_cross.py | exact frame review | pending | no NN/controller | git-ignored |
| .local/cross_x_1105/blood_source_contact.png | source+current preview4times | pending | exact sourceclock decode | git-ignored |

| .local/cross_x_1105/come110_source_contact.png | user110s anchor source/actual frames | pending | originalsourceclock decode | git-ignored |

| .local/cross_x_1105/audit_relations.py | cached all6 cross/depth stage audit | pending | no NN/controller search | git-ignored |
| .local/cross_x_1105/relations.json | source candidates/paired stage values | pending | source/frame/lineage assertions | git-ignored |

| .local/cross_x_1105/coupled_point_trial.py | one bounded source cross coupled IK | pending | actual native18 point oracle, no trajectory claim | git-ignored |
| .local/cross_x_1105/point_trial/results.json | point feasible candidate+all failures | pending | budget60s/50objectiveeval per anchor | git-ignored |

## Facts found
Cached13.174s all6 source/actual lineage checks pass. Blood28.629 reference/control cross+.74, staticfit+.55, inputMPC-1.69, actual-2.14 shoulder widths (body-frame comparative, not source3Dtruth): first cross loss is control and export worsens it. Source2D confirms actualCross despite strict both-hands-midline metric missing partial crosses; retain wrist-order/forearm crossing separately. Come110.51 currentreference higher/lessforward than actual; source depth still inferred. Actualrig has no independent wrist, fixed palm mount; arm sweep canbe corrected, purewrist snap cannot be invented.
Current results6 are accepted best-available R4, not choreography-perfect. Prior chestcross/forearm/phase defects acknowledged. Original cached person22358frames77chunks; no need NN rerun. Actual safety normal11/MUSIC18mm; analytic_sequence_limits_v2 is authoritative per-joint cosine. Existing current Studio/bundles passed software/clock persistence, not human fidelity. All old full data exposed development/regression.

## Done
Cachedall6 audit13.174s complete,14diagnosticcases. Coupled2point3.237s84nativequeries bothnativeclear, but ACTUALLYviewed Bloodpoint isREJECTED as sourcecopy: unconstraineddepth putsLwristbehind(-1.149shoulderwidth) andRfront(+1.367); 2Dfit underbodyframe hides this. Comeup-point visuallycloser butnotbackwardsweep/trajectoryproof. No currentoutputchanged. Correct sourcefront-occlusion constraint and actualviewprojection for Blood only; no global front-bias that would suppress backward gestures.
Read current delivery/handoff and relevant debugging/contract rules; no source modification.

## Next
One diagnosed Bloodpoint correction: sourcecross wrists/forearms visibly infront, so requirebody-frontwrists and use actualwaist view projection; originalsourceFit seed, samebounds/native18/budget. ReuseComepoint unchanged. Then one originalstateeventtrajectory.
Register cached paths/versions, inspect real cross frames, audit whether source->reference->input->actual R4 loses crossing, then one justified bounded correction with before/after + no-regression/native export checks. Keep held/inferred/unknown separate; do not invent hidden wrists/crosscut identity. Select new output only after full affected-path/HOME/clock/audio/rounded YAML proof; update results front only when ready.

## Blocked
None yet.
