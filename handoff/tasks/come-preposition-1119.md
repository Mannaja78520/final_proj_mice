# Come and Cheer retraction pre-positioning
Owner: codex:come-preposition-01a1f13c
Updated: 2026-11-19T20:02:44.927562+07:00
Branch: main
Plan: A58-1
Baseline: 58244ab
Last commit: this checkpoint

## Doing now
Complete. Delivered verified full-song version and before/after report; no active jobs or device use.

## Done
- Tested two ways to position the arm early using source wrist travel, preserving prior lift/lower/retraction observations. Checked long transition collisions against both leg endpoints. The best pre-position-only version gave 33/49 with no lost gesture; another pre-position pathway safely recovered 134.3.
- Combined the viable left-arm pathway with local arm phase correction at 130.5 using the earlier motion on the fixed song clock. Final signed retractions 30 -> 35/49, lifts 76 -> 77/99, lowers 53 -> 54/66, no previously matched gesture identity lost, same 0.30 s criterion. New retractions at 57.5, 128.9, 130.5, 132.0 and 134.3. Fourteen remain.
- Final exact native18 geometry and limits pass all 169281 command and 8465 servo samples and adjacent paths. Waist/shoulder and jump keys and clock preserved. Modeled motion coupling changed waist/shoulder at most 0.348 degrees, both jump wrist arcs still pass. Prior project SHA unchanged and no physical run.
- Full 2:48 original song and model preview. Frame/audio decode and clock verified, four exact browser seeks and six local links. Actual isolated Studio load verified 887 keys, 168.313 s embedded song, eight sample parity exact, zero device calls. Viewed 57.5 and 130.5 source/robot/plots.

## File status
| File | Change | State | Verification | Commit |
| --- | --- | --- | --- | --- |
| handoff/tasks/come-preposition-1119.md | Result and limits | done | scoped diff | this checkpoint |
| results/come-four-view/pull-events/index.html | Link from prior result | done | local navigation | git-ignored |
| results/come-four-view/preposition/index.html | Thai outcomes and chapter cues | done | six links, four real seeks | git-ignored |
| results/come-four-view/preposition/Come_preposition.nong.json | Edited full-song motion with audio | done | 887-key Studio import | git-ignored |
| results/come-four-view/preposition/sequence.yaml | Compiled sequence | done | full parsed native18 | git-ignored |
| results/come-four-view/preposition/I0lCxX8373M_source_audio.mp3 | Original song | done | asset hash and audio alignment | git-ignored |
| results/come-four-view/preposition/wrist_timing_full.mp4 | Full visible comparison | done | total frame/audio decode and visual cue checks | git-ignored |
| results/come-four-view/preposition/measurements.json | Exact scores and proof | done | native and Studio/Edge receipts | git-ignored |
| .local/come_preposition_1119/file_ledger.csv | Per-path evidence and delivery fingerprint | done | exact SHA and bytes | git-ignored |

## Next
Fourteen target pulls remain unmatched at the fixed criteria. Preserve the verified routes for reuse. No real-hardware result inferred.
