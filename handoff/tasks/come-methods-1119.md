# Come and Cheer full-song method comparison
Owner: codex:come-methods-01a1f13c
Updated: 2026-11-19T08:17:46.323825+07:00
Branch: main
Plan: A57-6
Baseline: ce53a41
Last commit: this checkpoint

## Doing now
Complete. Deliverable recommended as the new-take review version. No worker or hardware active.

## Done
- Used cached front and recovered the three other fixed views. Compare on fixed song clock, common 15.8–159.2 s dance span with both jumps scored separately. Front+profiles give approximate 3D directions. Rear arm scoring held out of arm fitting; rear can support body angle inference.
- R4 + jump edit, archived RL center and left, and fixed-view fit all evaluated. Arm/rear/waist/shoulder angle errors for fit 31.300/34.144/5.165/1.041 deg. R4 42.752/36.300/13.330/3.629. RL center57.419/52.822/48.146/4.348; left55.034/48.557/46.000/3.878. Prominent bilateral arm peak/valley matches within 550 ms: fit70/86, R4 61, RL center68, left64. Different dancer/source prevents a controlled RL-method conclusion.
- Use horizontal torso rotation for waist and left/right shoulder height difference for shrug. Visual 34.2/75.2 turns and 37.8/86.7 shoulder tilt, both jumps, 110.8/148 cross checked. High X still misses all 25 confident source frames across four methods. Full candidate retains 887 keys and all clock fields with 702 changed motion keys incl yaw 678 and shrug 631. Both jump windows mapped to protected arms, both wrists rise/fall in modeled servo.
- Initial exact compiler rejected three local regions. Transition-dependent acceleration faults reproduced through hard restores. Final half-cosine tapered splice passes actual compiler/YAML, 169281 command1ms + 8465 servo50Hz samples and adjacent paths at 18 mm. Original clock and motion limits unchanged. Final native path proof exact; real hardware not run.
- Full 2:48 comparison 2525 frames and original audio audit/decode passes. Edge file mode video and all 8 native seeks pass. Actual Studio JS via isolated loopback imports exact 887 keys with embedded 168.313 s original audio; preview 8 samples zero difference and no device helper calls. Previous full jump project SHA unchanged.

## File status
| File | Change | State | Verification | Commit |
| --- | --- | --- | --- | --- |
| handoff/tasks/come-methods-1119.md | Scope and results | done | scoped diff | this checkpoint |
| results/come-four-view/index.html | Latest full comparison link | done | checked reference | git-ignored |
| results/come-four-view/methods/index.html | Thai benchmark, preview and clickable cues | done | 6 links, 8 real seeks | git-ignored |
| results/come-four-view/methods/Come_full_camera.nong.json | New editable full-song motion | done | 887 exact keys and original song | git-ignored |
| results/come-four-view/methods/sequence.yaml | Native projected trajectory | done | full parsed replay/native18 | git-ignored |
| results/come-four-view/methods/I0lCxX8373M_source_audio.mp3 | Native audio asset | done | decoded original sha | git-ignored |
| results/come-four-view/methods/comparison_full.mp4 | Four timed camera feeds/four methods | done | 2525 frames, audio clock, full decode | git-ignored |
| results/come-four-view/methods/measurements.json | Score, limits and playback evidence | done | benchmark and deliverable checks | git-ignored |
| .local/come_methods_1119/file_ledger.csv | Exact primary files and evidence hashes | done | current verified snapshots | git-ignored |

## Next
A57-2 overhead X remains open. Fixing crossing would need a different executable arm path, since pushing near-hand geometry produced native collisions. No new training requested/performed. Current reviewed fit is separate from previously selected production result.
