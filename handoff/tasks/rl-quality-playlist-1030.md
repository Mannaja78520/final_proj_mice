# RL quality audit and six-clip CMU cheer playlist

Owner: codex:rl-1030-01a1891f
Updated: 2026-10-30 04:45:45 +07:00
Branch: main (bookkeeping only; all experiments private)
Last commit: this checkpoint
Plan: A50-2; A50-1 remains owned by Claude

## Goal
User: check every output against actual humans, improve algorithms as far as practical. Use ALL SIX cheerleader clips as one development/evaluation set now; do not wait for the original two to pass. Compare quality and training costs per clip, retest improvements across clips. Take over Claude's unfinished work upon verified quota stop, without another permission question. No quota stop has been verified; no Claude claims taken.

## Doing now
First3 new raw clips pass schema/count/timestamp checks and have center-candidate JSON rigs; fourth raw extraction PID4228 still active. Candidates fail final music-clock/quality gate (shape-only playback444-517s for83-90s source, worst150-160deg; YAML unavailable). Selected-person skeleton samples for old4 reviewed; reference reliability/start alignment need investigation. No new training/GPU/hardware or Claude takeover.
## File status
Baseline1283955; pre-existing dirty files remain owned by others. Private files are ignored, never publish models/media. No source promotion or task completion claimed.

| File | Change | State | Verification | Commit |
| --- | --- | --- | --- | --- |
| handoff/tasks/rl-quality-playlist-1030.md | scope, evidence, next steps | active checkpoint | own file reconciled | this checkpoint |
| docs/PLAN.html | own A50-2 scope/progress | done checkpoint | plan.py note succeeded | ac03084 |
| docs/plan_state.js | generated plan progress | done checkpoint | plan.py | ac03084 |
| docs/BRIDGE.md | own appended claims/checkpoints | shared uncommitted | mutex; preserve earlier edits | uncommitted |
| .local/rl_playlist_1030/9xOEOfDo7NA_contact.jpg | private experiment/audit evidence | checkpoint; see Facts | candidate/sampled checks only; final quality pending | git-ignored |
| .local/rl_playlist_1030/backend_lock.json | private experiment/audit evidence | checkpoint; see Facts | candidate/sampled checks only; final quality pending | git-ignored |
| .local/rl_playlist_1030/CLG7VdVhhLM_contact.jpg | private experiment/audit evidence | checkpoint; see Facts | candidate/sampled checks only; final quality pending | git-ignored |
| .local/rl_playlist_1030/come_and_cheer_center_30fps_repaired_sample.jpg | private experiment/audit evidence | checkpoint; see Facts | candidate/sampled checks only; final quality pending | git-ignored |
| .local/rl_playlist_1030/come_and_cheer_center_30fps_tracked_sample.jpg | private experiment/audit evidence | checkpoint; see Facts | candidate/sampled checks only; final quality pending | git-ignored |
| .local/rl_playlist_1030/come_and_cheer_center_30fps_worst_sample.jpg | private experiment/audit evidence | checkpoint; see Facts | candidate/sampled checks only; final quality pending | git-ignored |
| .local/rl_playlist_1030/come_and_cheer_left_30fps_repaired_sample.jpg | private experiment/audit evidence | checkpoint; see Facts | candidate/sampled checks only; final quality pending | git-ignored |
| .local/rl_playlist_1030/come_and_cheer_left_30fps_tracked_sample.jpg | private experiment/audit evidence | checkpoint; see Facts | candidate/sampled checks only; final quality pending | git-ignored |
| .local/rl_playlist_1030/come_and_cheer_left_30fps_worst_sample.jpg | private experiment/audit evidence | checkpoint; see Facts | candidate/sampled checks only; final quality pending | git-ignored |
| .local/rl_playlist_1030/compose_previews.py | private experiment/audit evidence | checkpoint; see Facts | candidate/sampled checks only; final quality pending | git-ignored |
| .local/rl_playlist_1030/composition.err.log | private experiment/audit evidence | checkpoint; see Facts | candidate/sampled checks only; final quality pending | git-ignored |
| .local/rl_playlist_1030/composition.log | private experiment/audit evidence | checkpoint; see Facts | candidate/sampled checks only; final quality pending | git-ignored |
| .local/rl_playlist_1030/composition_process.json | private experiment/audit evidence | checkpoint; see Facts | candidate/sampled checks only; final quality pending | git-ignored |
| .local/rl_playlist_1030/ctfNcvYev_U_contact.jpg | private experiment/audit evidence | checkpoint; see Facts | candidate/sampled checks only; final quality pending | git-ignored |
| .local/rl_playlist_1030/downloaded.txt | private experiment/audit evidence | checkpoint; see Facts | candidate/sampled checks only; final quality pending | git-ignored |
| .local/rl_playlist_1030/download.log | private experiment/audit evidence | checkpoint; see Facts | candidate/sampled checks only; final quality pending | git-ignored |
| .local/rl_playlist_1030/extraction.err.log | private experiment/audit evidence | checkpoint; see Facts | candidate/sampled checks only; final quality pending | git-ignored |
| .local/rl_playlist_1030/extraction.log | private experiment/audit evidence | checkpoint; see Facts | candidate/sampled checks only; final quality pending | git-ignored |
| .local/rl_playlist_1030/extraction_process.json | private experiment/audit evidence | checkpoint; see Facts | candidate/sampled checks only; final quality pending | git-ignored |
| .local/rl_playlist_1030/extract_playlist.py | private experiment/audit evidence | checkpoint; see Facts | candidate/sampled checks only; final quality pending | git-ignored |
| .local/rl_playlist_1030/hgB_vo7PEdw_contact.jpg | private experiment/audit evidence | checkpoint; see Facts | candidate/sampled checks only; final quality pending | git-ignored |
| .local/rl_playlist_1030/I0lCxX8373M_contact.jpg | private experiment/audit evidence | checkpoint; see Facts | candidate/sampled checks only; final quality pending | git-ignored |
| .local/rl_playlist_1030/inference_smoke.json | private experiment/audit evidence | checkpoint; see Facts | candidate/sampled checks only; final quality pending | git-ignored |
| .local/rl_playlist_1030/interim_training.json | private experiment/audit evidence | checkpoint; see Facts | candidate/sampled checks only; final quality pending | git-ignored |
| .local/rl_playlist_1030/manifest.json | private experiment/audit evidence | checkpoint; see Facts | candidate/sampled checks only; final quality pending | git-ignored |
| .local/rl_playlist_1030/new_candidate_baselines.json | private experiment/audit evidence | checkpoint; see Facts | candidate/sampled checks only; final quality pending | git-ignored |
| .local/rl_playlist_1030/preview_composition.json | private experiment/audit evidence | checkpoint; see Facts | candidate/sampled checks only; final quality pending | git-ignored |
| .local/rl_playlist_1030/quality_audit_initial.json | private experiment/audit evidence | checkpoint; see Facts | candidate/sampled checks only; final quality pending | git-ignored |
| .local/rl_playlist_1030/raw_validation.json | private experiment/audit evidence | checkpoint; see Facts | candidate/sampled checks only; final quality pending | git-ignored |
| .local/rl_playlist_1030/retarget_blood_center.log | private experiment/audit evidence | checkpoint; see Facts | candidate/sampled checks only; final quality pending | git-ignored |
| .local/rl_playlist_1030/retarget_cheer_center.err.log | private experiment/audit evidence | checkpoint; see Facts | candidate/sampled checks only; final quality pending | git-ignored |
| .local/rl_playlist_1030/retarget_cheer_center.log | private experiment/audit evidence | checkpoint; see Facts | candidate/sampled checks only; final quality pending | git-ignored |
| .local/rl_playlist_1030/retarget_great_center.err.log | private experiment/audit evidence | checkpoint; see Facts | candidate/sampled checks only; final quality pending | git-ignored |
| .local/rl_playlist_1030/retarget_great_center.log | private experiment/audit evidence | checkpoint; see Facts | candidate/sampled checks only; final quality pending | git-ignored |
| .local/rl_playlist_1030/retarget_playlist.cjs | private experiment/audit evidence | checkpoint; see Facts | candidate/sampled checks only; final quality pending | git-ignored |
| .local/rl_playlist_1030/retarget_processes.json | private experiment/audit evidence | checkpoint; see Facts | candidate/sampled checks only; final quality pending | git-ignored |
| .local/rl_playlist_1030/selected_track_review.json | private experiment/audit evidence | checkpoint; see Facts | candidate/sampled checks only; final quality pending | git-ignored |
| .local/rl_playlist_1030/video_review_initial.json | private experiment/audit evidence | checkpoint; see Facts | candidate/sampled checks only; final quality pending | git-ignored |
| .local/rl_playlist_1030/witsawa_kriangkrai_center_30fps_repaired_sample.jpg | private experiment/audit evidence | checkpoint; see Facts | candidate/sampled checks only; final quality pending | git-ignored |
| .local/rl_playlist_1030/witsawa_kriangkrai_center_30fps_tracked_sample.jpg | private experiment/audit evidence | checkpoint; see Facts | candidate/sampled checks only; final quality pending | git-ignored |
| .local/rl_playlist_1030/witsawa_kriangkrai_center_30fps_worst_sample.jpg | private experiment/audit evidence | checkpoint; see Facts | candidate/sampled checks only; final quality pending | git-ignored |
| .local/rl_playlist_1030/witsawa_kriangkrai_left_30fps_repaired_sample.jpg | private experiment/audit evidence | checkpoint; see Facts | candidate/sampled checks only; final quality pending | git-ignored |
| .local/rl_playlist_1030/witsawa_kriangkrai_left_30fps_tracked_sample.jpg | private experiment/audit evidence | checkpoint; see Facts | candidate/sampled checks only; final quality pending | git-ignored |
| .local/rl_playlist_1030/witsawa_kriangkrai_left_30fps_worst_sample.jpg | private experiment/audit evidence | checkpoint; see Facts | candidate/sampled checks only; final quality pending | git-ignored |
| .local/rl_playlist_1030/YJwyYWiMWHI_contact.jpg | private experiment/audit evidence | checkpoint; see Facts | candidate/sampled checks only; final quality pending | git-ignored |
| .local/rl_playlist_1030/references/9xOEOfDo7NA_raw.json | private experiment/audit evidence | checkpoint; see Facts | candidate/sampled checks only; final quality pending | git-ignored |
| .local/rl_playlist_1030/references/blood_entaneer_center_candidate_30fps_analysis.json | private experiment/audit evidence | checkpoint; see Facts | candidate/sampled checks only; final quality pending | git-ignored |
| .local/rl_playlist_1030/references/blood_entaneer_center_candidate_30fps.json | private experiment/audit evidence | checkpoint; see Facts | candidate/sampled checks only; final quality pending | git-ignored |
| .local/rl_playlist_1030/references/blood_entaneer_center_candidate_30fps_summary.json | private experiment/audit evidence | checkpoint; see Facts | candidate/sampled checks only; final quality pending | git-ignored |
| .local/rl_playlist_1030/references/cheer_rao_ma_cheer_center_candidate_30fps_analysis.json | private experiment/audit evidence | checkpoint; see Facts | candidate/sampled checks only; final quality pending | git-ignored |
| .local/rl_playlist_1030/references/cheer_rao_ma_cheer_center_candidate_30fps.json | private experiment/audit evidence | checkpoint; see Facts | candidate/sampled checks only; final quality pending | git-ignored |
| .local/rl_playlist_1030/references/cheer_rao_ma_cheer_center_candidate_30fps_summary.json | private experiment/audit evidence | checkpoint; see Facts | candidate/sampled checks only; final quality pending | git-ignored |
| .local/rl_playlist_1030/references/entaneer_great_center_candidate_30fps_analysis.json | private experiment/audit evidence | checkpoint; see Facts | candidate/sampled checks only; final quality pending | git-ignored |
| .local/rl_playlist_1030/references/entaneer_great_center_candidate_30fps.json | private experiment/audit evidence | checkpoint; see Facts | candidate/sampled checks only; final quality pending | git-ignored |
| .local/rl_playlist_1030/references/entaneer_great_center_candidate_30fps_summary.json | private experiment/audit evidence | checkpoint; see Facts | candidate/sampled checks only; final quality pending | git-ignored |
| .local/rl_playlist_1030/references/hgB_vo7PEdw_raw.json | private experiment/audit evidence | checkpoint; see Facts | candidate/sampled checks only; final quality pending | git-ignored |
| .local/rl_playlist_1030/references/YJwyYWiMWHI_raw.json | private experiment/audit evidence | checkpoint; see Facts | candidate/sampled checks only; final quality pending | git-ignored |
| .local/rl_playlist_1030/review_previews/come_and_cheer_center_30fps_comparison_source.mp4 | private experiment/audit evidence | checkpoint; see Facts | candidate/sampled checks only; final quality pending | git-ignored |
| .local/rl_playlist_1030/review_previews/come_and_cheer_left_30fps_comparison_source.mp4 | private experiment/audit evidence | checkpoint; see Facts | candidate/sampled checks only; final quality pending | git-ignored |
| .local/rl_playlist_1030/review_previews/witsawa_kriangkrai_center_30fps_comparison_source.mp4 | private experiment/audit evidence | checkpoint; see Facts | candidate/sampled checks only; final quality pending | git-ignored |
| .local/rl_playlist_1030/review_previews/witsawa_kriangkrai_left_30fps_comparison_source.mp4 | private experiment/audit evidence | checkpoint; see Facts | candidate/sampled checks only; final quality pending | git-ignored |
| .local/rl_playlist_1030/sources/9xOEOfDo7NA.info.json | private experiment/audit evidence | checkpoint; see Facts | candidate/sampled checks only; final quality pending | git-ignored |
| .local/rl_playlist_1030/sources/9xOEOfDo7NA.mp4 | private experiment/audit evidence | checkpoint; see Facts | candidate/sampled checks only; final quality pending | git-ignored |
| .local/rl_playlist_1030/sources/ctfNcvYev_U.info.json | private experiment/audit evidence | checkpoint; see Facts | candidate/sampled checks only; final quality pending | git-ignored |
| .local/rl_playlist_1030/sources/ctfNcvYev_U.mp4 | private experiment/audit evidence | checkpoint; see Facts | candidate/sampled checks only; final quality pending | git-ignored |
| .local/rl_playlist_1030/sources/hgB_vo7PEdw.info.json | private experiment/audit evidence | checkpoint; see Facts | candidate/sampled checks only; final quality pending | git-ignored |
| .local/rl_playlist_1030/sources/hgB_vo7PEdw.mp4 | private experiment/audit evidence | checkpoint; see Facts | candidate/sampled checks only; final quality pending | git-ignored |
| .local/rl_playlist_1030/sources/YJwyYWiMWHI.info.json | private experiment/audit evidence | checkpoint; see Facts | candidate/sampled checks only; final quality pending | git-ignored |
| .local/rl_playlist_1030/sources/YJwyYWiMWHI.mp4 | private experiment/audit evidence | checkpoint; see Facts | candidate/sampled checks only; final quality pending | git-ignored |
| .local/rl_playlist_1030/yolo_config/Ultralytics/settings.json | private experiment/audit evidence | checkpoint; see Facts | candidate/sampled checks only; final quality pending | git-ignored |
| .local/rl_playlist_1030/references/ctfNcvYev_U_raw.json | last dense source | active PID4228 | inspect log then validate completed JSON | git-ignored |

## Facts found
- Latest heartbeat: raw_validation.json validates Blood2788frames, Cheer3003frames, Great2998frames; strict increasing timestamps and feature counts align. Extraction wall times555/618s for first2, CPU concurrent with preparation, not clean benchmark. Fourth source still processing; no duplicates launched.
- new_candidate_baselines.json records3center candidates: Blood676keys/444.642s/mean15.61/worst149.60deg; Cheer817/517.183s/17.68/160.02; Great795/507.229s/17.98/155.75. Shape-only planner intentionally slows; these are NOT final music-clock results. Backend pose/path/min-time arrays empty and entry clear, but final dense/actual sequence verification remains pending. YAML skipped (keyCue undefined), not delivered.
- selected_track_review.json plus4tracked_sample.jpg show selected source skeleton at worst old4frames. Some selected actors are small background figures despite trusted=true. Opening Witsawa source shows arms down during fade while all candidates start arms up. Need temporal identity/depth/trust and initial-state diagnosis, not just more RL. These are four samples, not full footage approval.
- Original training: .local/rl_final_1030; input .local/cheer_rig_1029_30fps; four center/left sets for Come and Witsawa, servo_5mm. Overrides reach.dancerTopPct95, marginDeg2, reward.lift0.3, reward.smooth0.5. All20rounds done, no Python training/QC driver at own extraction launch.
- Reports: private quality_audit_initial.json (results SHA and32 contenders), interim_training.json (checkpoint/boundary data), video_review_initial.json (worst-frame index). Final raw-human mean RL errors15.2-16.6deg, not proof reference poses are right. Ghost is reach-remapped, not unmodified human; relabel before final delivery.
- Three HYBRID board exports REJECTED: Come center, Come left, Witsawa left. Export Studio flags32/20/17. Witsawa center hybrid and other3 RL exports written. No physical execution. Sim-level hybrid also collides in3sets. Do not use rejected motions.
- Shared smoothing raises RL jerk32-38pct and worsens raw error in ALL4 (same input/reference/model). Investigate rather than assuming smooth is better. Approximate collision0 is not continuous full-geometry clearance proof.
- Best music-error checkpoint can precede last. Preserve best candidates; select using separate evaluation, not just reward/round20.
- Original full comparison videos have blank source pane in reviewed frames. Private compose_previews.py overlays actual source/audio using analysis.source.from (~4.938s), preserving motion/original files. Four outputs158.47s/158.47s/85.03s/85.03s verified decode+audio/video; sampled worst frames inspected with humans visible.
- Worst sampled RL poses still diverge (Come center138.638s, Come left123.557s, Witsawa center53.653s, Witsawa left0.033s). Witsawa opening source has title/fade and down arms; reference/start state needs checking. These are samples, NOT full temporal validation. Add selected-person skeleton to source before judging tracking correctness.
- Manifest has6source paths, true duration/FPS, contact sheets and six-still-per-clip review. All sampled clips are lead performances. Entaneer First crouches around94.8s require reporting robot's absent leg DOFs; preserve upper-body semantics.
- extract_playlist.py reuses shared CPU detector/appearance/re-id, redirects only own config. CPU smoke4 at20s found4people/embeddings/appearances each. Full extraction now active, not yet verified. Logs/process JSON locate it.
- backend_lock.json freezes5shared scripts; both private adapters refuse drift. Shared extract_30fps.py hardcodes source/output; retarget_30fps.cjs names every unknown ID Witsawa. Never run old CLI for new IDs.
- retarget_playlist.cjs reuses frozen class in memory, removes old CLI, sets private ROOT and explicit output name. Syntax/inspect4 passed; actual fitting NOT tested. CLI: ID OUTPUT_NAME CANDIDATE_STYLE ANCHOR [--inspect]. Center anchor is candidate, not evidence of complete routine discovery. YAML may be unavailable in backend.
- Sources to evaluate: https://xbpeng.github.io/projects/DeepMimic/index.html and https://atarilab.github.io/dynaretarget.io/ . Papers are candidates, not proof of the best algorithm on nong.

## Playlist inventory
| ID | Lead title | Status |
| --- | --- | --- |
| 9xOEOfDo7NA | เลือดเอ็นทาเนียร์ | downloaded; extraction queued/running |
| hgB_vo7PEdw | เชียร์เรามาเชียร์ | downloaded; extraction queued/running |
| YJwyYWiMWHI | Entaneer the Great | downloaded; extraction queued/running |
| I0lCxX8373M | Come and Cheer | existing2rigs/RL; quality open |
| ctfNcvYev_U | Entaneer the First | downloaded; extraction queued/running |
| CLG7VdVhhLM | วิศวะเกรียงไกร | existing2rigs/RL; quality open |
Playlist PLp0S6kSqcUg_V2y6azyYTEjBmJuQ-vfQN:15entries, six lead. Exclude clapping/MV-only. New4 original59.94FPS preserved; old2 reused, not overwritten.

## Quality gate and cross-clip experiments
1. Validate raw source poses/actor identity/choreography against FULL footage. Mark occlusion, fills, cuts and uncertainty. Never average incompatible routines or reward wrong reference poses.
2. Review every final output at original song timestamps, every clip and difficult windows, with human video/selected skeleton and multiple robot views. Report per-arm/per-clip mean/P95/worst errors, timing/beat phase, lift/waist/shrug, coverage/confidence and jerk.
3. Check actual exported sequence through joint/servo limits and continuous collision tests including HOME/entry and after smoothing. Sim is not physical proof. No autonomous hardware motion.
4. Compare baseline/planner/RL/hybrid and justified constrained IK/trajectory/MPC/learning candidates on identical source/clock/model/gap/smoothing. Stage budget: all6baselines -> short trials -> expand justified candidates/hard clips -> final audit all6.
5. Record per-clip preprocessing/retarget/train/inference/render costs, GPU-hours/peakVRAM if measured, concurrency and estimation labels. No invented measurements. Cross-clip/held-out validation distinguishes shared improvements from per-clip tuning. Retest all6 after shared changes; report worst clip and preserve each clip's best version.
6. Set acceptance thresholds from actual robot tolerances/reference uncertainty before selecting winners. No safety violations, no meaningful regressions; inspect worst windows. Different winners per clip allowed. Stop refinement on documented plateau, never claim global perfection.
7. Deliver editable Studio rig/project, checked matching sequence/preview/audio, evidence and index for each eligible clip/choreography. Missing/inaccessible clips stay pending. Private media never public git; preserve user projects. Source changes follow staging/claims/Help parity/QC/review.

## Done
- This heartbeat: first3 new raw references validated and shape candidate rigs generated privately; no final quality approval. Added selected-skeleton visual diagnostics to old4worst samples; last source extraction continues.
- Six source inventory,4new downloads,6contact sheets and sampled36stills; metadata inspections6 passed.
- Private extraction/retarget adapters prepared; AST/node checks and inspect passed; CPU inference smoke4 passed. Dense extraction running PID4228, no duplicate launch.
- RL4trainings complete. Detected3hybrid collision failures and all4smoothing regressions; no final approval.
- Repaired4full comparison copies with source/audio and visually checked worst samples; full temporal/selected-actor review pending. Rendering presentation repair does not fix motion defects.

## Next
0. Next wake: inspect PID4228/fourth raw file, validate it and retarget Entaneer First candidate. Existing3 candidates must not be overwritten. Diagnose private YAML keyCue issue and add music-clock planner/RL baselines before spending full training budget. Raw/new candidate/selected-track JSON reports hold exact evidence.
1. Inspect extraction_process.json/PID4228 and extraction.log/err; validate each RAW_READY JSON count/timestamps/features before retarget. Do NOT relaunch whole batch. If failed, diagnose and select only unfinished IDs; output overwrite refused.
2. Retarget private raw files via retarget_playlist.cjs using explicit clip/output/style/anchor. Validate actor/routine coverage and physical path before treating candidates as rigs. No fixed-center-only final result. Review backend hashes before refreshing lock.
3. Audit all4 repaired comparison files in review_previews/ and actual human reference, add selected-person overlay, relabel ghost as reachable target, inspect full temporal motion. Diagnose saturation/reference misses, unsafe hybrid transitions and board smoothing regression in own isolated experiments; avoid active Claude files until actual handoff/quota stop.
4. Complete6clip baseline table and justified candidate trials, validate transfer/regressions, render/package matching final exports. Keep evidence/next here at every stop, plan updates under mutex. Notify meaningful changes only. Heartbeat stays active until ALL6scope complete, not training alone.

## Blocked
Quality gate remains open. Own reference extraction is active; no user action needed. Active Claude process exists, no verified limit or transfer. Shared claims retained by original owners.
