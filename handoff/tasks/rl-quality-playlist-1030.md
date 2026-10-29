# RL quality audit and six-clip CMU cheer playlist
Owner: codex:rl-1030-01a1891f
Updated: 2026-10-30 05:19:27 +07:00
Branch: main bookkeeping only; experiments private; no shared source changes
Last commit: this checkpoint
Plan: A50-2 (own); A50-1 remains Claude-owned

## Goal
Check all outputs against actual humans and improve algorithms as far as practical. Use ALL SIX lead clips jointly now, measure per-clip quality/cost and regressions, retain each best result. User authorizes takeover of unfinished Claude work upon verified limit, no reconfirmation. No Claude quota stop verified; do not take its files based on silence/process disappearance.

## Doing now
Heartbeat every30min. All4 new raw references and center candidates/YAML complete; final quality NOT passed. Own sequential short-GPU pilot PID17580 active: first Blood round1/3 completed57.3s, no observed errors. Budget1024envs x3rounds x20updates per new clip, no-video, private reports; no full retraining. Other services untouched. CPU extraction4228 and compositor36332 finished; release only own completed CPU claims.

## File status
Original baseline1283955; preserve all other dirty work. Complete exact per-file rows (File/Change/State/Verification/Commit plus size/time) for private inputs/generated models/media are in `.local/rl_playlist_1030/file_status.csv`; refresh each checkpoint, never treat running-file existence as completion. This ledger preserves per-file evidence without exceeding150lines in this task. Changed source/control files:
| File | Change | State | Verification | Commit |
| --- | --- | --- | --- | --- |
| handoff/tasks/rl-quality-playlist-1030.md | scope/evidence/next | active checkpoint | ledger reconciled | this checkpoint |
| docs/PLAN.html | own A50-2 scope/progress | checkpoint | plan.py | ac03084 |
| docs/plan_state.js | generated plan progress | checkpoint | plan.py | ac03084 |
| docs/BRIDGE.md | own claims/checkpoints only | shared uncommitted | mutex; preserve earlier entries | uncommitted |
| .local/rl_playlist_1030/extract_playlist.py | CPU extraction with private paths/drift guard | full batch done |4real-frame smoke,4dense schema/count/time checks | git-ignored |
| .local/rl_playlist_1030/retarget_playlist.cjs | private explicit naming/paths/export-only |4center candidates done | syntax+inspect4+actual4fits; no final quality approval | git-ignored |
| .local/rl_playlist_1030/context_compat.cjs | restore cue helpers from normalized read-only fragment | private fix | original missing; fixed read/write+cue preservation | git-ignored |
| .local/rl_playlist_1030/verify_context.cjs | bounded actual regression | passed | original helper undefined, adapter correct | git-ignored |
| .local/rl_playlist_1030/compose_previews.py | repair4original-human panes/audio | done presentation | full duration/streams and4worst-source images inspected | git-ignored |
| .local/rl_playlist_1030/run_pilots.py | staged-budget sequential pilots | active PID17580 | syntax + first training round; full batch pending | git-ignored |
| .local/rl_playlist_1030/backend_lock.json | freeze65shared dependencies | recorded | original5unchanged before extending65 | git-ignored |
| .local/rl_playlist_1030/file_status.csv | complete exact private artifact ledger | this checkpoint | files/sizes/times; individual validation linked | git-ignored |

## Facts found
- Original RL4 training DONE20/20: .local/rl_final_1030, input .local/cheer_rig_1029_30fps, servo_5mm. Training recorded reach.dancerTopPct95, marginDeg2, lift0.3, smooth0.5. All current output/reference methods need identical provenance for fair comparison.
- IMPORTANT config discrepancy: original summary.record.config confirms95/2, but root config99/5; board-export logs robotTop38.7deg vs pilots41.7deg. Audit/re-score exported motions with training's recorded configuration before comparing remapped errors. Raw-human and remapped-reference scores are separate. Physical collision findings still apply to actual played curves.
- Original final RL raw-human mean15.2-16.6deg is NOT full accuracy approval: reference itself needs validation. Ghost uses reach-remapped target, not raw human; relabel final previews. quality_audit_initial.json stores32rows/results hash; interim_training.json stores checkpoint/boundary evidence. Best round may precede last; preserve candidates and use held-out selection.
- Three hybrid board exports REJECTED: Come center/left and Witsawa left, Studio flags32/20/17. Witsawa center hybrid plus remaining3 RL exports written, never physically executed. Shared smoothing increases RL jerk32-38pct and worsens raw error in all4; investigate, do not assume smooth=better. Approximate collision0 is not continuous full-geometry proof.
- Original4 comparison videos had blank human pane. review_previews/ contains repaired full158.47/158.47/85.03/85.03s copies with source/audio offset analysis.source.from(~4.938s), same robot motion. preview_composition.json records durations,video/audio and samples. Presentation repair is not motion repair.
- selected_track_review.json and4tracked_sample.jpg show selected2D source skeleton at old4worst frames. Some trusted=true actors are tiny/background figures. Witsawa opening fade shows arms down while simulations start arms up. Need full temporal identity/depth/trust/start-state diagnosis; four samples do not prove identity continuity.
- manifest.json: six original59.94FPSsources;4new downloaded,2old reused. All sampled footage lead performances. Entaneer First crouches around94.8s: robot lacks leg DOFs, preserve upper-body meaning and disclose morphology limits.
- raw_validation.json: Blood2788samples, Cheer3003, Great2998, First5682; count/timestamp/feature alignment checks pass. Each has intro/end no-person frames, tracked within output. Full actor/reference audit pending. Extraction CPU wall times recorded in each raw.extraction, concurrency not a clean benchmark.
- new_candidate_baselines.json (refresh includes4): center SHAPE candidates Blood676keys/444.642s/mean15.61/worst149.60deg; Cheer817/517.183/17.68/160.02; Great795/507.229/17.98/155.75; First1314/786.268/12.45/135.50. Source spans83/90/90/180s; these are intentionally slowed shape baselines, not final music-clock results. First safe.failed1 remains diagnostic; final endpoint/path arrays clear does not erase that.
- YAML issue reproduced: shared qc/data/video_group.cjs searches LF brace boundary in CRLF music_on_a_keyframe.js, leaving keyCue/setKeyCue undefined. Own context_compat normalizes/extracts existing functions in memory. Original failure preserved; verify_context passed actual read/write/unrelated-cue check. Shared source bytes untouched.
- All4 candidate YAML exports now exist. candidate_export_validation.json verifies exact pose counts,10joint values within0.05deg and durations versus candidate JSON.44-86KB files are not board-ready chains, no matching MP3 yet, and final actual-playback/clearance/music checks pending.
- retarget adapter CLI ID OUTPUT_NAME CANDIDATE_STYLE ANCHOR [--inspect|--export-only]. Explicit names/private roots, old CLI never runs. Existing targets refused. Candidate center not complete routine discovery; different routines must be evidenced and kept separate. YAML presence does not mean final delivery.
- backend_lock65 plus pilot_input_hashes freeze Python experiment/simulator and shared JS/config. Pilot driver checks before/after each case and aborts on drift. Private repoSummary override prevents touching shared docs. Current models are read-only; no promotion or hardware.
- Pilot launch first deferred correctly during peer voice check PID6596, then inventory empty before start. Own GPU claim recorded BRIDGE. PID17580 sequential4pilots, env1024/rounds3/updates20, no-video, BelowNormal. Short pilot scores are undertrained and cannot rank converged algorithms. Costs/peak Torch allocation recorded pilot_batch.json, not total NVIDIA VRAM.
- Literature candidates, not automatic winners: https://xbpeng.github.io/projects/DeepMimic/index.html and https://atarilab.github.io/dynaretarget.io/ . Compare nong-compatible constrained IK/trajectory/MPC/imitation/hybrid using actual held-out results.

## Playlist inventory
| ID | Lead title | Current |
| --- | --- | --- |
| 9xOEOfDo7NA | เลือดเอ็นทาเนียร์ | reference+center candidate/YAML; short pilot running |
| hgB_vo7PEdw | เชียร์เรามาเชียร์ | reference+center candidate/YAML; short pilot queued |
| YJwyYWiMWHI | Entaneer the Great | reference+center candidate/YAML; short pilot queued |
| I0lCxX8373M | Come and Cheer | existing2RL outputs; quality open |
| ctfNcvYev_U | Entaneer the First | reference+center candidate/YAML; short pilot queued |
| CLG7VdVhhLM | วิศวะเกรียงไกร | existing2RL outputs; quality open |
Playlist PLp0S6kSqcUg_V2y6azyYTEjBmJuQ-vfQN has15entries/six lead. Exclude clapping/MV-only. Preserve all user projects; models/media remain private.

## Quality gate and cross-clip experiments
1. Validate source/reference and identity against full footage, mark occlusion/fills/cuts/uncertainty. Never average incompatible routines or reward wrong reference poses. Add selected-person skeleton throughout preview, not samples only.
2. Review each final output throughout song at original timestamps/multiple views. Report per-arm/per-clip mean/P95/worst windows, timing/beat/phase, lift/waist/shrug, coverage/confidence and jerk. Worst clips cannot hide behind average.
3. Verify actual exported sequence joint/servo limits and continuous collisions including HOME/entry/after smoothing. Sim is not physical evidence. No autonomous hardware motion. Match exported timing/pose/audio to preview and reference configuration.
4. Stage budget: all6baselines -> short trials -> expand justified methods/hard clips -> final audit all6. Compare methods on identical data/clock/model/gap/smoothing. Measure costs and label concurrency/estimates. Keep tuning separate from held-out/cross-clip checks; distinguish generic transfer from per-clip tuning. Retest all6 after shared changes, preserve best version per clip.
5. Set thresholds from robot tolerances/reference uncertainty before choosing winners. Require no safety violation or meaningful regression and worst-window review. Different winners per clip allowed. Document plateau/limits honestly; no claim of global perfection.
6. Deliver editable rig/project, matching checked sequence/preview/audio, comparison/cost report and index per eligible clip/choreography. Inaccessible clips stay pending. Product changes need normal staging/claims/Help parity/QC/review. No such product change yet.

## Done
Six sources prepared; new4dense references/candidates and YAML verified structurally. Private missing-helper fix has before/after regression. Original4training completed; safety/smoothing/reference failures documented;4human-pane copies repaired and sampled. Full quality and final delivery remain open.

## Next
1. Check pilot_process.json/PID17580, pilots.log/err and pilot_batch.json. Do NOT duplicate/restart finished pilots blindly. Driver refuses existing summaries on restart; inspect recorded hashes/config and preserve completed cases before adapting resume to remaining IDs. On failure fix actual cause, not retries. Release own GPU claim when driver stops; check status first.
2. After pilots, compare raw-human errors/timing/safety/cost across six clips (old4sets represent2clips). Do not rank methods from3round undertraining. Plan useful next candidates: constraints/retarget reference fixes, collision-safe hybrid blending, board-playable smoother parameter trials. Never merely train longer against wrong reference.
3. Resolve config discrepancy for original board-export rescoring; audit selected identities/depth and start states throughout footage. Expand distinct routines where evidenced. Validate native board playback/chain size/matching audio before final artifact packaging.
4. Keep this task+file_status.csv/evidence and plan current at every stop, mutex for shared bookkeeping. Notify meaningful changes only. Automation continues every30min until ALL6scope complete, not training alone.

## Blocked
No user action needed. Short GPU pilots are running; quality gate open. Active Claude exists, no verified quota handoff. Other source/task claims stay with their owners; own finished extraction/compositor CPU claims can be released.
