# Come and Cheer four-view robot motion
Owner: codex:come-4view-01a1f13c
Updated: 2026-11-19T07:40:40.810928+07:00
Plan: A57-4, continues A57-2
Baseline: d94db85

## Doing now
One targeted revision: current R4 visibly lifts higher than four-view v1 at 110.70 and 111.00. Preserve R4 apex motion through that segment using a fixed 110.05–111.65 blend, with 110.55–111.13 on R4 source-clock command. Reuse v1 elsewhere. Repeat native replay/clearance under 60 s, assess actual wrist elevation and visual crossing, keep review only if still materially better on overall angular score.

## File status
| File | Change | State | Verification | Commit |
| --- | --- | --- | --- | --- |
| handoff/tasks/come-4view-1119.md | Task and scope | active | baseline d94db85 | this checkpoint |

## Done
Audio fit seven windows; visual front/side residual 0.20s. V1 saved with measured 64.334 to 49.452deg on 100–116, checks native18 PASS, but overhead upper-arm/range visibly regressed. Original R4 remains current.

## Next
Find which cameras overlap anchor 100–116 s and recover source gesture events.
