# Come and Cheer missed retraction improvement
Owner: codex:come-pull-01a1f13c
Updated: 2026-11-19T19:27:40.975917+07:00
Plan: A57-8
Baseline: 32bcced
Last commit: this checkpoint

## Doing now
Complete. Verified full-song artifact published; no worker or hardware session active.

## Done
- Same A57-7 reference and 0.30 s event criterion. Optimized local shoulder/elbow corrections to restore amplitude and steepest signed retraction in two variants. Both unprotected variants scored 33/49 on parsed replay, but lost previously matched vertical events. Reverted whole affected windows, then accepted alternative strokes at 69.4 and 101.4 s.
- Final exact parsed modeled replay and 18 mm checks pass: hand retraction 20 -> 30/49; lift 75 -> 76/99; lower 53/66 unchanged. No previously matched event identity lost. Ten new retractions at 29.1, 61.2, 64.7, 69.4, 75.8, 81.1, 101.4, 107.0, 126.5 and 143.7. Nineteen still unmatched.
- Upper-body keys, all timings, original audio, and both jump windows intact. Modeled waist/shoulder difference exactly 0 deg. Both jump wrist rises/falls pass. Native170k command/servo and adjacent paths checked; no robot tested.
- Full 2:48 paired MP4, signed retraction plots per arm, original audio alignment, 2525 frames and all streams decode. Visually checked 29.1, 64.7, 101.4. Four Edge seeks exact, six links valid. Studio loaded 887 exact keys/168.313 s with eight zero-delta preview checks and zero device calls. Old full-song project SHA preserved.

## File status
| File | Change | State | Verification | Commit |
| --- | --- | --- | --- | --- |
| handoff/tasks/come-pull-events-1119.md | Result and handoff | done | scoped diff | this checkpoint |
| results/come-four-view/wrist-timing/index.html | Link from prior version | done | link verified | git-ignored |
| results/come-four-view/pull-events/index.html | Thai outcome, clips and controls | done | four exact seeks and six verified links | git-ignored |
| results/come-four-view/pull-events/Come_retraction_events.nong.json | Full edited show with music | done | exact actual Studio import | git-ignored |
| results/come-four-view/pull-events/sequence.yaml | Commands | done | full parsed replay and native18 | git-ignored |
| results/come-four-view/pull-events/I0lCxX8373M_source_audio.mp3 | Original music | done | decoded SHA parity | git-ignored |
| results/come-four-view/pull-events/wrist_timing_full.mp4 | Side-by-side full comparison | done | frame, audio and visual verification | git-ignored |
| results/come-four-view/pull-events/measurements.json | Same-clock event receipts and limits | done | identity, native and delivery checks | git-ignored |
| .local/come_pull_events_1119/file_ledger.csv | Exact private and published evidence files | done | SHA and bytes | git-ignored |

## Next
Nineteen remaining hand strokes and old overhead-X issue require different paths if continued. Original thresholds and limits retained. No physical playback authorized.
