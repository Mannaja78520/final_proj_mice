# Robot pose model: pictures, training, first real video (for Codex on the PC)

Owner:
Updated: 2026-10-28 21:10 (Bangkok)
Branch: (new branch from main after PR "No-robot 2026-10-28" merges)
Last commit: -
Plan: A52-3

## Goal
User 2026-10-28: *like YOLO pose for our robot: find where each joint of nong is
from a camera, tell front/back/left/right, check the move is right, auto
calibrate if sizes change.* The fit, compare and calibrate code is done and
QC'd on synthetic views (tools/robot_pose, check_robot_pose,
docs/experiments/2026-10-28_robot_pose.md). Missing: a TRAINED keypoint model
and a run on a real lab video. All of this is PC work (GPU, private videos).

## Rules
Never edit the friend's folders. Never push videos, frames, model weights or
anything under .local. Config/data, not hard-coded (config/robot_pose.json).
OOP, small modules. Task-file Doing now / File status / Facts found as HANDOFF.md says.

## Steps (each one is self-contained)
1. Real-looking pictures: new `tools/robot_pose/render_mujoco.py`, class that
   takes `.local/robot_pose/synth/views.jsonl` (pose + camera per view, written by
   `python -m tools.robot_pose synth --n 20000 --no-images`) and renders each view
   with MuJoCo offscreen from `tools/nong_sim` (same rig, same camera: f, cx, cy,
   r, t in camera.py; OpenCV axes). Domain randomisation: light, colours,
   floor/backdrop textures, blur, noise. Use the depth buffer to set v=1 for
   keypoints hidden behind the body (synth.py only hides the chest marker).
   If the CAD meshes (urdf_view.json) look closer to the real robot, use them.
2. Lab frames with free labels: for each lab video with a known command
   timeline (.local/lab_1028: dance2.py logs + the 30-pose chunk files), fit
   the camera from the holds (`VideoCheck.holds` + `PoseFitter.fit_camera`),
   project the commanded pose's keypoints, write YOLO labels for frames where
   the robot is still (commanded = real there). Spot-check 50 by eye; drop
   bad ones. Keep frames + labels in .local only.
3. Train: `pip install ultralytics`; `yolo pose train data=<dataset.yaml>
   model=yolo11n-pose.pt imgsz=640 epochs=100` (try the s model too), on the
   RTX 5070 Ti. Copy best.pt to `.local/robot_pose/model/best.pt`
   (config detector.model). Record: images per source, epochs, wall time,
   pose mAP50 / mAP50-95 on a held-out LAB set (not synthetic), per keypoint.
4. First real check: `python -m tools.robot_pose detect <lab video>` then
   `python -m tools.robot_pose check <kp.jsonl> <sequence.yaml> --start <s>`.
   Use the ccl_v5 cap 60 run (slowest). Report per joint mean/p95/lag and the
   facing into docs/experiments/2026-10-28_robot_pose.md (new section, raw
   numbers, compare with DREAM / RoboPose real-image results there).
5. If one camera is too weak (see the doc: 1 camera ~2-5 deg, flips), film
   front + side next lab day; fit_pose takes a list of cameras.

## Doing now
Nothing yet.

## File status
No edits yet.

## Facts found
- Keypoint order and L/R flip come from config/robot_pose.json; the dataset yaml
  carries them (`synth.py dataset_yaml`). Keep the order when labelling lab frames.
- Studio frame: Y up, robot's left +X, front +Z; camera.py uses OpenCV axes.
- `PoseFitter.fit_pose` with one camera lands on the solution nearest its
  start pose; start from the command (VideoCheck does).
- Lab: camera 0 640x480 ~30 fps, WAIST 50 faces it (lab-robot-1028.md).

## Done
- (cloud, 2026-10-28) tools/robot_pose + check_robot_pose + experiment doc.

## Next
1. Step 1 or 2 above, whichever the PC can start first.

## Blocked
- Step 2/4 need the lab videos on the PC; step 5 needs a lab day.
