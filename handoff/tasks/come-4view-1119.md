# Come and Cheer four-view robot motion
Owner: codex:come-4view-01a1f13c
Updated: 2026-11-19T07:55:28.602758+07:00
Branch: main
Plan: A57-4, continues A57-2
Baseline: d94db85
Last commit: this checkpoint

## Doing now
Delivered and verified. No worker or device session active.

## Done
- Registered 4 fixed feeds to original song. Seven active windows agreed. Front and side visual checks exposed ~0.20 s residual and corrected it for this excerpt. Front/side mapping uses anatomical left-right verification. Rear is visual evidence; the body hides the arms from it.
- 1:36–1:58 four-view editable excerpt with 22 s embedded song and video. Core 100–116 s mean arm direction error 53.253 -> 37.694 deg on the new, approximate camera reference. 110.7/111.0 snapshots still miss a convincing overhead X. Full sequence is review only.
- Confirmed both jumps on the 4 views at 50.6 and 82.6 s. In full R4 project changed only 20 arm keys. Parsed command and modeled servo waist and shrug differences are 0. Both wrists rise and lower around both accents. Same original full audio and timing. 169281 command samples, 8465 servo samples and adjacent paths pass native 18 mm checks.
- Actual current Studio JS via isolated local HTTP imported both files with 887/137 exact keys and original embedded songs at 168.313/22 s, playback comparison 0 deg across eight samples each, no device calls. Live Hub was offline.
- Final landing 10/10 links; three audio/video comparisons passed; deliverable hashes and original selected R4 hash verified. No robot run. Original camera files and full R4 baseline kept.

## File status
Exact SHA256 and byte counts for delivered files and retained evidence in .local/come_4view_1119/file_ledger.csv. Media is ignored in Git.
| File | Change | State | Verification | Commit |
| --- | --- | --- | --- | --- |
| handoff/tasks/come-4view-1119.md | Task and verified results | done | scoped diff check | this checkpoint |
| results/index.html | Link to verified results | done | link resolves | git-ignored |
| results/help.html | Guidance for opening the new result | done | token and link check | git-ignored |
| .local/latest-results-1105/build_catalog.py | Retains new root and help links when regenerated | done | same exact insertions | git-ignored |
| results/come-four-view/index.html | Thai results entry | done | 10 links resolve | git-ignored |
| results/come-four-view/Come_four_view.nong.json | 22-second four-view experiment | done | Studio 137 exact keys, song, parity | git-ignored |
| results/come-four-view/sequence.yaml | Parsed excerpt | done | limits + native geometry | git-ignored |
| results/come-four-view/Come_four_view.wav | Excerpt audio | done | embedded sha256 | git-ignored |
| results/come-four-view/comparison.mp4 | Four-view and R4 comparison | done | 440 frames and original-song clock | git-ignored |
| results/come-four-view/measurements.json | Excerpt scores and receipts | done | file hashes and source limits | git-ignored |
| results/come-four-view/jumps/Come_two_arm_raises.nong.json | Full song with two revised jump accents | done | Studio 887 exact keys, song, parity | git-ignored |
| results/come-four-view/jumps/sequence.yaml | Full-song compiled motion | done | actual parsed native limits and geometry | git-ignored |
| results/come-four-view/jumps/I0lCxX8373M_source_audio.mp3 | Original song for YAML | done | SHA and cue match | git-ignored |
| results/come-four-view/jumps/song-47-55.mp4 | First jump comparison | done | 160 frames, audio clock and visual check | git-ignored |
| results/come-four-view/jumps/song-79-87.mp4 | Second jump comparison | done | 160 frames, audio clock and visual check | git-ignored |
| results/come-four-view/jumps/measurements.json | Full-song evidence and original protection | done | checks and hashes verified | git-ignored |
| .local/come_4view_1119/file_ledger.csv | Private and delivered path hashes | done | enumerated files, self omitted | git-ignored |

## Facts found
The 4-camera reference is an approximate near-orthogonal measurement with visibility weighting. Error was scored against the same new take used to fit, not an independent accuracy test. Do not extrapolate the excerpt numbers to the full song. Mirrored coordinates and the scratch waist/shoulder-lock candidate were rejected and retained privately. The arm-only change applies only to the jump windows; the robot's existing moving waist and shrug survive across the song.

## Next
A57-2 overhead X shape work remains open. Reuse 4-angle frames for that specific elbow/wrist relation before further retargeting. No approval for real-robot playback inferred.
