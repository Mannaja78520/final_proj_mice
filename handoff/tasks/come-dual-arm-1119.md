# Come and Cheer coordinated arm retraction
Owner: codex:come-dual-arm-01a1f13c
Updated: 2026-11-19T20:23:35.289267+07:00
Plan: A58-3
Baseline: b5ddb24
Last commit: this checkpoint

## Doing now
Complete. Verified four additional retractions. No live workers or hardware.

## Done
- Two coordinated hand paths scored 40/49 with every previous event retained. Side variant recovered106.4 while arc variant recovered102.0. Accepted a local blend of the viable alternatives on unchanged song time after testing native paths.
- Exact match counts unchanged thresholds: retract37 -> 41/49, lift77/99 and lower54/66. All prior identities retained. New matches at102.0,106.4,120.2,139.0 s. At120.2 the modeled opposing wrist goes 11.9 mm farther sideways. Eight pulls remain.
- Exact projected path 18 mm, 169281 1ms command and 8465 50Hz servo samples and adjacent paths pass. Same keys for body/jumps, clock and embedded original audio. Exact 0deg modeled body difference. Both jump arcs retained, no hardware.
- Full 2:48 with four source angles and compared robot paths; 2525 frames and source audio timing/decode verified. Four exact Edge seeks, six links. Actual isolated Studio import 887 exact frames and eight preview sample parity, original 168.313s audio and zero device calls. Before/after views reviewed at102 and120.2. Previous project SHA retained.

## File status
| File | Change | State | Verification | Commit |
| --- | --- | --- | --- | --- |
| handoff/tasks/come-dual-arm-1119.md | Result and limits | done | scoped diff | this checkpoint |
| results/come-four-view/elbow-route/index.html | New current link | done | verified navigation | git-ignored |
| results/come-four-view/arm-clearance/index.html | Thai results and chapter navigation | done | 6 links, 4 exact seeks | git-ignored |
| results/come-four-view/arm-clearance/Come_dual_arm.nong.json | Full project and matching song | done | actual Studio import | git-ignored |
| results/come-four-view/arm-clearance/sequence.yaml | Compiled movement | done | full native 18 and timing | git-ignored |
| results/come-four-view/arm-clearance/I0lCxX8373M_source_audio.mp3 | Original music | done | source clock and SHA | git-ignored |
| results/come-four-view/arm-clearance/wrist_timing_full.mp4 | full comparison video | done | 2525 frames and full decode | git-ignored |
| results/come-four-view/arm-clearance/measurements.json | Exact motion and delivery proofs | done | receipts verified | git-ignored |
| .local/come_dual_arm_1119/file_ledger.csv | SHA/byte receipts | done | per-path fingerprint | git-ignored |

## Next
Eight misses remain. Keep fixed tolerance and prior matches for any future work. No physical run inferred.
