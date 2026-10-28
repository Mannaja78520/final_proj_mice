# Robot pose data: MuJoCo pictures and still lab labels

Owner: (free: step 3 is for the PC)
Updated: 2026-10-28T23:33:50+07:00
Branch: codex/robot-pose-data
Tree: E:/final_proj/mice/code/.claude/worktrees/codex-robot-pose
Baseline / local HEAD: 7f171e3eef83dfbe05f8c27f4783846e2881c0b1
Last commit: a02c5f5 (cloud fixes on top of e085d37)
Plan: A52-3 (steps 1-2 done; step 3 next)

## Goal
Find nong joints from a camera. This round: rendered training views and conservative
lab hold labels. Training/detection/calibration steps 3-5 are outside this request.
Private inputs/outputs ONLY E:/final_proj/mice/code/.local (absolute paths).
Never stage media/weights/.local; preserve RL PID 39888 and all .staging work.

## Doing now
Nothing. Steps 1-2 merged (cloud, 2026-10-28). Step 3 (train) is next, on the PC.


## File status
| File | Change | State | Verification | Commit |
| --- | --- | --- | --- | --- |
| tools/robot_pose/render_scene.py | Shared rig + exact OpenCV camera/GL scene | done | corrected selected526/0; camera/depth/CAD | e085d37 |
| tools/robot_pose/render_meshes.py | Private reduced CAD mesh adapter | done | collar source anchors <5mm; sabotage caught | e085d37 |
| tools/robot_pose/render_mujoco.py (cloud: .local from RepoLayout) | Randomised RGB/depth YOLO dataset | done; 18,661usable/20,000rendered | selected526/0; five mutations caught | e085d37 |
| tools/robot_pose/lab_labels.py | Observed holds, fit, rejection and partial labels | done | lab QC 12/0; four mutations caught | e085d37 |
| qc/checks/check_robot_pose_render.py | Real GL/camera/depth/CAD regression | done | five mutations caught/restored; base/bounds/minvisible | e085d37 |
| qc/checks/check_robot_pose_lab.py | Holds/motion/pose/split regression | done | four mutations caught/restored | e085d37 |
| config/robot_pose.json | Render/CAD/lab quality settings | done | corrected selected526/0; independent review | e085d37 |
| docs/systems.json | Register modules/checks | done | build + check_systems green | e085d37 |
| docs/systems/robot-pose.md | Generated file/check ownership | done | check_systems green | e085d37 |
| docs/systems/qc.md | Generated new-check ownership | done | check_systems green | e085d37 |
| main_python/web/help/parts/studio.html | Renderer and lab-label help parity | done | selected docs/build/links green | e085d37 |
| main_python/web/help.html | Generated Help | done | build_web + selected checks green | e085d37 |
| handoff/tasks/robot-pose-data.md | Step 3 handoff | done | - | this PR |

## Facts found
- `kinematics.py:65` is Studio's shared NongTree: mm, Y up, robot left +X, front +Z.
  Renderer uses exact tree frames without simulation/base translation.
- `camera.py:102` uses OpenCV x-right/y-down/z-forward. Real rendered pixels
  test four viewpoints with a deliberately off-centre principal point (<2px).
- Real CAD is read-only real-root nong/main_python_set_nong/models/nong_description.
  STL metres; cyclic ROS-to-Studio axes; collar lift63.329mm corrects ~63mm offset.
  Link appearances approximate small source offsets (<5mm at collar anchors).
- CAD has no head/neck/chest marker or separate virtual hand extensions.
  Base also lies outside its rendered mesh. All eight landmarks must be v=0.
  Whole-post bounding box still uses the base as a bounds anchor, not a label. Own-housing depth
  radii differ from primitive radii; other-part occlusion gives v=1.
- Eight lab videos valid; ccl_v5_p060.mp4 corrupt (moov atom missing).
  Recorder nominal15fps, actual capture ~30fps; no capture timestamps. Cap60:
  10,965frames /731 video sec vs360.3 logged wall sec. Never equate these clocks.
- Exact 30-pose chunk archives absent outside excluded trees. Private v5 sources
  exist, but chunk.py discards waits; continuous dance frames lack proven holds.
  Initial script/logs disagree (WAIST50 vsHOME). Only final HOME is acknowledged.
- Current rig and the real robot disagree for wrist/hand targets; four slow runs
  retain a visibly displaced forearm after HOME. Drop those candidate frames.
- Lab camera uses four manually observed shoulder/elbow centres, never its own
  projections. Fit max1.3613px/RMS1.3065px. One planar HOME pose: NONMETRIC camera;
  only those four landmarks labelled, others v=0. No general pose accuracy claim.

## Done
- Source steps1/2 implemented with config, registry and same-step generated Help.
- MuJoCo3.17.0/OpenCV4.13.0 installed; no dependency/model downloads or GPU training.
- Final corrected selected QC:526 passed/0 failed (55.8s check phase;362.275s wrapper).
  Evidence private robot_pose/verification/final_selected_qc.log. Earlier507/0 retained.
- Pre-correction full QC exit1: 8,905 passed/21 failed in757.6s. Evidence private
  robot_pose/full_qc_console.log and full_qc_exit.txt. New renderer33/0, lab12/0,
  original robot_pose17/0 and nong_sim13/0 within that full run. Other failures
  need classification; no baseline reproduction or full-green claim.
- Nine deliberate faults caught/restored: camera cy sign, depth occlusion,
  CAD collar offset, absent CAD landmarks; lab motion, wrong HOME, hold edges, split leak.
  Added hidden-only detector-view rejection. Final five-render proof30.401s, source
  hashes restored. Evidence verification/final_render_sabotage.log; lab_sabotage.log.
- Same-provider independent reviewer /root/lab_audit: final source no blockers.
  Evidence private robot_pose/final_source_review.txt. Earlier ai_panel via agy
  gpt-6-astra failed (no review/approval); independent review caught CAD issues.
- Discarded preliminary render: 4,052 images retained in private robot_pose/synth,
  invalid old CAD labels; DO NOT train. Fresh final output is synth_mujoco.
- Step1 final:20,000 RGB images/YOLO labels (18,000train/2,000val),0dropped,
  22,299 depth-hidden keypoints; wall1,408.818s (23m29s), process exit0.
  Evidence private robot_pose/synth_mujoco/render_report.json and rendered.jsonl.
- Final visual QA correction complete: base labels v0;1,339 views with<3visible
  joints quarantined (1,198train/141val). Usable18,661 (16,802train/1,859val),
  13,022hidden keypoints. Repair87.393s; all-pair/label validation143.139s PASS.
  Original20klabels+metadata/report preserved in verification/final_repair_originals;
  rejected pairs in verification/quarantine_minvisible. Corrected12-image preview inspected.
  Final independent source/result review APPROVED: verification/final_source_review.json.
- Startup delay diagnosed:124locked browser profile folders caused~306s sweep.
  Own pre-mutation sabotage baseline aborted (QC15/tools2), source never changed;
  same five faults reran green using fresh private TEMP/TMP. Old profiles preserved.
- First full-QC side effects backed up/restored: four tracked fixture/plan files,
  three new fake-browser/COM99 reports moved private. Evidence verification/cleanup.json.
- Step2: 120 lab candidates; 36 kept /84 dropped in6.627s (27train/9val, by video).
  Drops: 48 conservative hold-boundary +36 displaced-forearm frames; corrupt clip excluded.
  Exactly50 unique overlays inspected by eye: 25accepted/25rejected, all decisions agreed.
  Evidence private robot_pose/lab/dataset/report.json; review50_frames.json + five PNG sheets.
- Git add/commit denied writing real .git/worktrees/.../index.lock; native push
  failed SEC_E_NO_CREDENTIALS. Connected GitHub create_branch also rejected: tool requires
  approval but policy is never. NO new commit/remote branch/checkpoint exists.

- (cloud, 2026-10-28) PC full QC listed 21 failures. Cloud full QC on a02c5f5:
  8988 pass, 5 fail, all the cloud browser checks that fail even on a docs-only PR
  (check_link_states x2, check_studio_boot, check_view, check_tools_list); 4 load-only
  flakes pass alone. Fixed: the two new checks looked for a folder named `code`
  (now RepoLayout.real) and needed a display (OSMesa on headless Linux).
  Diff reviewed: no images, video, frames, labels, meshes or weights.

## Next
1. Step 3 on the PC (GPU): `pip install ultralytics` into code\.local, then
   `yolo pose train data=.local/robot_pose/render/dataset.yaml model=yolo11n-pose.pt
   imgsz=640 epochs=100` (then yolo11s-pose). Hold out the LAB labels (36 kept) as
   the val set, not synthetic. Copy best.pt to `.local/robot_pose/model/best.pt`.
   Record in docs/experiments/2026-10-28_robot_pose.md: images per source, epochs,
   wall time, LAB mAP50 / mAP50-95, per keypoint. Weights and frames stay in .local.
2. Step 4: detect + check on the ccl_v5 cap 60 video (re-copy it: ccl_v5_p060.mp4 is corrupt).
3. Lab labels are thin (one HOME pose, four joints): film fresh holds next lab day.


## Blocked
- New shell launches also fail CreateProcessWithLogonW error1909. Existing render
  session97390 finished exit0; full-QC28110 finished exit1. Independent verification
  reader can run normal commands and is checking logs/diff; parent shell remains blocked.
- Sandbox denies real-root coordination mutex/BRIDGE/PLAN and Git index writes.
  Shared bookkeeping and local git push/upstream cannot be completed here. GitHub mutation
  also denied by automatic approval (requires approval, policy never); no bypass attempted.
- No exact dance timing/holds: broad lab labels deliberately withheld. Only one HOME pose
  and four joints validated; this small lab set is insufficient for full pose evaluation.
