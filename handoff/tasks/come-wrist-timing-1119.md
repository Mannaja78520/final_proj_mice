# Come and Cheer wrist timing revision
Owner: codex:come-timing-01a1f13c
Updated: 2026-11-19T19:10:43.509057+07:00
Branch: main
Plan: A57-7
Baseline: 65f2b69
Last commit: this checkpoint

## Doing now
Finished. Full candidate verified and published. No own workers.

## Done
- Used same new dancer on fixed song clock. Wrist height is shoulder-relative; hand depth along inferred body forward axis. Fit both trajectories and signed motion; score one arm at a time at 10 Hz and require same direction and active speed within 0.30 s. Opposite profile validation subset improved. Both jump substitutions excluded from fitting and event counts.
- Previous -> final per-arm match counts: retraction 12/49 -> 20/49, lift 69/99 -> 75/99, lower 40/66 -> 53/66. Matched retraction lag 0.167 -> 0.070 s. 29 retractions still fail timing or amplitude, 24 lifts and 13 lowering events remain, overhead X still open. These are estimates in the model/recording, not real hardware.
- First full curve fit plus isolated native failure restores passed, then one focused retraction amplitude refinement. Initial key collision and analytic acceleration failures retained; approved only pull_final after tapered baseline restore near 143.66 s. All 169281 command samples and 8465 servo samples / adjacent paths pass MUSIC 18 mm; analytically confirmed joint limits.
- Original project preserved. Both jump windows and all waist/shoulder keys, cue times and original audio exact. Coupled native smoothing changes modeled waist/shoulder playback by max 0.782 deg with identical body keys. Both jump arm raises and falls rechecked.
- Full video front/rear/side synchronized with previous and revised model playback and wrist graphs. Visually checked 41.2, 58.6, 76.0 and remaining 101.4. Audio alignment and full H264/AAC decode pass. Edge four chapter seeks exact. Actual isolated Studio import 887 exact keys, 168.313 s embedded audio, eight preview samples 0deg difference, no device calls.

## File status
| File | Change | State | Verification | Commit |
| --- | --- | --- | --- | --- |
| handoff/tasks/come-wrist-timing-1119.md | Task, results and limits | done | scoped diff | this checkpoint |
| results/come-four-view/index.html | Link to revised full song | done | links verified | git-ignored |
| results/come-four-view/methods/index.html | Link from prior comparison | done | links verified | git-ignored |
| results/come-four-view/wrist-timing/index.html | Before/after playback and timing results | done | six links and four Edge seeks | git-ignored |
| results/come-four-view/wrist-timing/Come_wrist_timing.nong.json | Editable full-song revision with music | done | actual Studio parity | git-ignored |
| results/come-four-view/wrist-timing/sequence.yaml | Native sequence | done | whole-song parsed replay and geometry | git-ignored |
| results/come-four-view/wrist-timing/I0lCxX8373M_source_audio.mp3 | Same cue audio asset | done | audio SHA and clock | git-ignored |
| results/come-four-view/wrist-timing/wrist_timing_full.mp4 | Full paired video and signed curves | done | 2525 frames, decoded audio, visual checks | git-ignored |
| results/come-four-view/wrist-timing/measurements.json | Event counts, links, proof | done | final verification receipt | git-ignored |
| .local/come_wrist_timing_1119/file_ledger.csv | Published and private evidence fingerprints | done | exact file lengths and hashes | git-ignored |

## Next
Targets at 101.4 s and failed high crossing remain useful for subsequent trajectory design. Coarse event matching can overstate fidelity. Keep E-Stop/board settings out of offline edits. No physical robot run.
