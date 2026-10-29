# 2026-10-28 Robot pose from a camera (A52-3), synthetic accuracy

User 2026-10-28: like YOLO pose, find nong's own joints from a camera; tell
front / back / left / right; check a move is right; auto-calibrate later.
Code: `tools/robot_pose` (config `config/robot_pose.json`), QC `check_robot_pose`.
Status: **synthetic only**. No real video has been run (the YOLO model is not
trained yet: handoff/tasks/robot-pose-data.md). Raw output also in the project
files `experiments/2026-10-28_robot_pose/` (fit3.out, fit1.out).

## Method
1. 14 keypoints on Studio's rig bodies (head, neck, chest marker, base, both
   shoulders, elbows, wrists, paddle tips and paddle edges), 3D from
   `NongTree.frames` (the same tree check_nong_sim holds to Studio's scene).
2. Detector (to train): YOLO pose, one class, `kpt_shape [14, 3]`, `flip_idx`
   from the L_/R_ names. Labels are free: a rendered view of a known pose.
3. Fit: Levenberg-Marquardt (numpy) on confidence-weighted reprojection error
   + a weak pull to the commanded pose, inside the joint limits; camera fitted
   once from still moments with a known command. Facing from the waist's front
   vector vs the camera; front/back helped by the chest marker's visibility.
4. Compare with the board's own clock (`BoardClock`): per joint mean/p95/max
   error, bias, servo lag (bias removed first), stuck joints.
5. Calibrate: joint offsets + arm lengths + camera(s) from known-command frames;
   torsoH holds the scale, the waist offset is not fitted (the camera explains it).

## Raw numbers (rig_default, 2026-10-28, `python -m tools.robot_pose.bench`)
Camera 1400 mm, 15 deg up, fov 60, 640x480; 24 trials per row (8 azimuths x 3
random poses inside the joint limits); start = truth + N(0, 10 deg).
Mean absolute error per joint (deg), order L_SH_P L_SH_R L_EL_P L_EL_R R_SH_P R_SH_R R_EL_P R_EL_R WAIST SHRUG.

| cameras | noise px | per joint mean | median | p90 | wall s |
| --- | --- | --- | --- | --- | --- |
| 1 | 0 | 0.7 0.3 0.4 0.6 0.8 0.2 0.5 0.7 0.1 0.1 | 0.13 | 0.8 | 5.9 |
| 1 | 1 | 4.2 2.5 6.0 4.9 2.7 1.9 1.9 3.1 1.3 0.8 | 1.55 | 5.3 | 14.1 |
| 1 | 2 | 4.7 3.5 4.9 4.6 8.7 3.6 6.6 7.7 3.6 1.7 | 3.28 | 11.8 | 16.0 |
| 2 (90 deg apart) | 0 | 0.1 0.1 0.1 0.1 0.1 0.0 0.1 0.1 0.1 0.0 | 0.05 | 0.2 | 7.4 |
| 2 | 1 | 1.2 1.2 1.4 1.0 0.8 1.1 1.1 0.6 0.7 0.5 | 0.84 | 1.9 | 11.9 |
| 2 | 2 | 3.0 2.3 2.9 2.3 2.8 2.2 2.7 2.5 1.4 1.1 | 1.80 | 5.2 | 26.9 |

Facing, random cameras (distance 900-2600 mm, elevation -15..35, fov 45-75,
2 px noise), 8 azimuths x 3: **24/24** labels right when started near the
command, 24/24 when started from home. Joint error started from home (no
command known): median 5.3 deg, p90 42 deg (one camera: depth flips).

QC (check_robot_pose, same pipeline): two cameras worst joint < 1 deg (0 px);
one camera 1 px median < 3 deg; L/R-swapped keypoints undone from front and
back; calibration recovers +15 mm upper arm and +4 deg elbow offset (2 cams).

## What the numbers say
- One camera is enough for facing and for big faults (stuck joint, wrong
  direction, > ~10 deg), not for fine angles: an elbow bent toward the camera
  and one bent away look the same. Two cameras 90 deg apart cut the error ~2x
  and remove the flips. For checks of a few degrees, film front + side.
- Error grows with keypoint noise roughly linearly; at 1400 mm the upper arm
  is ~60 px long in 640x480, so 2 px noise is ~2 deg of bone direction.
- From the side, the two arms overlap: which arm is which must come from the
  detector (appearance, e.g. a coloured marker), not from geometry.

## Comparison with published work
- YOLO-Pose (Maji et al., CVPRW 2022) is the detector family used: one-stage
  box + keypoints with an OKS loss; its paper reports on COCO people, not robots.
- DREAM (Lee et al., ICRA 2020) is the closest method: robot keypoints learned
  from synthetic domain-randomised renders only, then PnP for the camera. We
  follow it (synthetic labels from the rig, camera by reprojection fit) and
  add the joint angles to the fit instead of reading them from the encoders,
  because nong's hobby servos report no position.
- RoboPose (Labbe et al., CVPR 2021) estimates camera AND joint angles from one
  image by render-and-compare; it also reports that one view leaves joint
  ambiguities, the same effect as the 1-camera rows above.
- Domain randomisation (Tobin et al., IROS 2017; Tremblay et al., CVPRW 2018)
  is why synthetic-only training can transfer; we add auto-labelled lab frames
  (known commands) to close the gap.
- Numbers on real video to compare with those papers' real-image results:
  not available yet (needs the trained model and a lab film).

## First trained detector on LAB frames (PC, 2026-10-29)
Setup: ultralytics 8.4.191, torch 2.11.0+cu128, RTX 5070 Ti Laptop GPU (shared with the RL run all the time),
`yolo11n-pose.pt`, imgsz 640, batch 16, 100 epochs, seed 0. Train = 18,661 MuJoCo/CAD renders
(16,802 + 1,859, all used for training). Val = the 36 auto-labelled LAB frames only (one HOME pose,
4 visible keypoints each: both shoulders and elbows). Weights and frames stay in `.local/robot_pose`.

| model | train wall | LAB box mAP50 | LAB box mAP50-95 | LAB pose mAP50 | LAB pose mAP50-95 |
| --- | --- | --- | --- | --- | --- |
| yolo11n-pose | 7,850 s (2 legs: killed at epoch 47 by a shell time limit, resumed from last.pt) | 0.077 | 0.032 | 0.000 | 0.000 |
| yolo11s-pose | 18,664 s (one leg, GPU shared with RL) | 0.316 | 0.134 | 0.000 | 0.000 |

yolo11s best.pt is now `.local/robot_pose/model/best.pt` (config detector.model).

Step 4 first look (yolo11s, `detect .local/lab_1028/ccl_v5_cap060.mp4 --every 0.5`, 43 s wall):
1,356 of 1,357 sampled frames got a pose, but the shoulder midpoint lands at median (183, 274) px
(x p10-p90 152-227) while the lab labels put the shoulders at about (205, 187) px: ~90 px too low, on the
chest/box area. `check` against the sequence was NOT run: with keypoints this far off, joint errors
would measure the detector, not the robot. Rerun step 4 after the next training round.

- Box recall on LAB is 1.0 but precision 0.037: on a lab frame it puts 10+ "nong" boxes on furniture,
  the cabinet and the PC with confidence up to 0.87, while the real robot gets 0.06. On a render it
  finds the robot alone at 0.91. This is the sim-to-real gap DREAM and Tobin et al. warn about: the
  renders' backgrounds and lighting do not cover a cluttered lab.
- Pose mAP is 0 because no box with the right keypoints passes the OKS bar; the 36 LAB labels have only
  4 of 14 keypoints, so OKS is computed on those 4.
- Next, in order: real backgrounds behind the renders (random lab photos, COCO-style images), real
  lab frames in TRAIN (fresh holds next lab day, step 5), a coloured marker per arm; then train again.

## References
- D. Maji, S. Nagori, M. Mathew, D. Poddar. YOLO-Pose: Enhancing YOLO for Multi Person Pose Estimation Using Object Keypoint Similarity Loss. CVPR Workshops 2022.
- T. E. Lee, J. Tremblay, T. To, J. Cheng, T. Mosier, O. Kroemer, D. Fox, S. Birchfield. Camera-to-Robot Pose Estimation from a Single Image. ICRA 2020.
- Y. Labbe, J. Carpentier, M. Aubry, J. Sivic. Single-view robot pose and joint angle estimation via render & compare. CVPR 2021.
- J. Tobin, R. Fong, A. Ray, J. Schneider, W. Zaremba, P. Abbeel. Domain Randomization for Transferring Deep Neural Networks from Simulation to the Real World. IROS 2017.
- J. Tremblay et al. Training Deep Networks with Synthetic Data: Bridging the Reality Gap by Domain Randomization. CVPR Workshops 2018.
- K. Levenberg 1944; D. Marquardt 1963 (the solver).
