# Nong Studio: dynamic URDF display and motion parity

Owner: claude:10222214-b01b (cloud thread "Studio URDF view mode")
Updated: 2026-10-23 (cloud, Bangkok morning)
Branch: claude/project-thread-wvmxq5 (from task/A48-1-10230507-3ac1 @7b7a904)
Tree: cloud clone (repo root); PC tree .staging-urdf-studio unused
Last commit: c82daa6 (base; handoff-only WIP commit follows)
Plan: A48-1 (robot page)

## Goal
- User: เอา URDF ไปใส่ nong studio เลือกได้ว่าจะโชว์แบบเดิมหรือ URDF
- URDF mode must use actual URDF dimensions/origins/axes, without stretching to the old proxy rig.
- On returning to the old display, ASK whether to use URDF dimensions or edit/use custom dimensions. Keep custom dimensions recoverable; do not overwrite silently.
- User added: ทำให้เป็น dynamic แก้ง่ายด้วย. Put choices, joint bindings/signs, source paths and dimension mappings in editable config/data; one source of truth, not model-specific conditionals.
- User added: test video following, realtime following, and related playback/monitor paths. Verify anatomical left/right, raised-hand direction and URDF joint movement, not merely a static screenshot.
- Do not move physical hardware for this task: user's earlier instruction parks combined real-robot tests until they have the robot again.

## Doing now
- Round 3 full QC: 7793 passed (3 flakes green alone, receipt refused by qc_chain_proj rewrite). Merged; PC reruns check_urdf_look.

## Round 3 (PC 06:35 run: fit L 15.9 / R 10.5 deg, right arm agree -0.22..-0.93)
- urdfFitArm now also matches how the upper arm and forearm TURN from HOME
  (quaternion from home to each sample, fit.frames) - directions alone leave the
  roll about a bone free - and polishes all 4 zeros together at the end.
- Reported deg = directions only. Fixture 3 (check_urdf_look): CAD tilts 5-8 deg
  off the rig: every arm joint agrees > 0.9. It did NOT reproduce the PC's right
  arm failure (directions-only also passes it), so the real cause is unproven.
- The real block now writes qc/_urdf_real.json (git-ignored): URDF joints, tips,
  rig, bindings. If the PC still fails, paste that file's text to the cloud
  thread (numbers only, no meshes) to work the fit out offline.

## Round 2 found (claude:10222214-b01b, 2026-10-23)
- The PC's real-model block compared the URDF with the FIXTURE rig, not the
  user's rig: rig_default.json has axis y/x + tilts (-40 deg etc), invert, zero 0.
  Against it, URDF L_SH_R ~ -(shapes' L_SH_P). And the CAD's zero is its drawn
  pose, not Studio's zero. Axis-dot sense cannot handle either.
- Fix: urdf_view.js urdfFitArm per arm: chain = the arm's 4 URDF joints by
  depth; grid (gridDeg) + polish to 0.01 deg of sense/zero per pair (shoulder on
  the upper-arm direction, elbow on the forearm direction) vs rigArmDirs (the
  shapes, analytic) over `samples` poses; optional pair swap; tie-break toward
  zero (a universal joint has twin answers). Numbers in sign/offsetDeg are kept.
  urdf_view.json "fit"; arm offsetDeg now "auto".
- Tip "mesh" = centroid of the forearm part's far end (each STL corner once!).
- check_urdf_look fixture 2 = RIG2 (the real rig values), drawn at HOME,
  names swapped (L shoulder, R elbow): 14 poses + each joint < 1 mm. Real
  block now uses rig_default.json and compares from HOME.

## Done (claude:10222214-b01b, 2026-10-22/23)
- web/urdf_view.json (looks, models, joint names/sign/offset, hands, sizes) +
  app_parts/urdf_view.js (listed after build_rig.js in tools/web_build.json).
- build_rig.js: buildRobot -> urdfBuildInto(robot) else buildRigShapes();
  applyPose/jointAxisVec defer to URDF while urdfOn. rig_data.js: RIG.view.
- pose_from_video.js vidWaistTable reads bodyGroup's WORLD turn.
- html_parts/view.html Robot look box + #lookAsk dialog; style.css; help part.
- hub_api_studio.py: /api/list?kind=models&deep=1 lists sub-folders.
- .gitignore: models/*/ (real CAD package stays private).
- qc/checks/check_urdf_look.py 24/24; sabotage 9/9 caught (rpy order, auto
  sense, ROS turn, own sizes, mesh tip, hand frame, CAD-sizes button...).

## Facts found
- urdf_view.js: tree built in mm (xyz*unitMm, mesh scale*unitMm), root
  turned ROS->Studio once; shoulders re-centred onto (0, dims.shoulderY, 0).
  bodyGroup = helper under the waist link, turned so it is world-aligned at
  zero. Hand = at the tip, -Y along the forearm, palmTurn from the rig.
- Tip "mesh": farthest forearm-mesh vertex along the upper arm's zero line.
  Mesh loads can be synchronous (cache): urdfMeshArrived ignores them until
  urdfOn; urdfSettle measures them. urdfMissing remembers 404 meshes.
- Torso collision box is still RIG.dims torso* (not from the CAD).
- SHRUG on the CAD look = the URDF shrug joint only (shrugCurve not used).
- buildYaml() returns {name, yaml}, not a string.
- fake_serial.NONG.joints = what monitorTick reads (set before browser.page).
- tools/build_web.py:87-112: Studio app_parts order comes from tools/web_build.json; app.js/index.html are generated. New .js part must be listed or build fails. Edit sources then build, never hand-edit the bundles.
- web/app_parts/build_rig.js:130 builds old proxy robot; :216 applyPose applies the shared pose. This is the likely common update boundary to investigate, avoiding separate video/realtime render logic.
- web/app_parts/scene.js defines THREE scene/camera/controls in millimetres, Y up; camera default target near body. A loaded URDF needs framing based on its actual bounds.
- web/app_parts/urdf_import.js exists (A31-7), but is NOT a native URDF tree renderer. It maps each link to one of the old six mesh/body parts, ignores intermediate links and full joint transforms, and guesses bar lengths from outgoing joint origins. It is insufficient for the new 11-link model.
- Existing importer uses DOMParser, metres*1000, and ROS Z-up -> Studio Y-up cyclic conversion (x,y,z)->(y,z,x). Validate exact rotations using matrices/quaternions; do not permute Euler angles blindly for a general import.
- The old importer asks via confirm before changing arm lengths; this is distinct from requested display-mode switch/dimension policy. Preserve legacy imports/projects.
- Studio joint order: L_SH_P L_SH_R L_EL_P L_EL_R R_SH_P R_SH_R R_EL_P R_EL_R WAIST SHRUG; pose values are joint degrees with configurable RIG.zero (usually90), not raw URDF radians. Bind by name through DATA and test signs/neutral exactly once.
- main_python/main.py:147-151 separates external DATA/STUDIO/MODELS from bundled STUDIO_WEB. :327 allows .urdf uploads. :2056-2058 serves /studio/ assets and /models/ user data. hub_api_studio.py:180 handles upload extension checks; :205 writes rig_default.json. Support both standalone nong main.py and Hub packaged runtime when integrating.
- Existing source areas: app_parts/{rig_data,rig_setup_ui,stl_meshes,save_state,project_save_load,pose_from_video,dummy_link,video_page,main_loop,boot}.js; html_parts/{view,setup}.html. Trace targeted functions, not entire large bundles.
- HANDOFF.md forbids committing CAD/model files to PUBLIC Git. Keep actual .SLDASM/.STL/URDF package local user data. A small synthetic URDF test fixture is appropriate; do not upload real geometry in PR/review.

## Working model (actual local files)
- Canonical URDF: E:/final_proj/mice/model/nong_urdf/solidworks/export/nong_description/urdf/nong_description.urdf
- Meshes: sibling ../meshes/*.STL, 11 binary STL in METRES, package://nong_description/meshes/...
- Native assembly: E:/final_proj/mice/model/nong_urdf/solidworks/nong_urdf_review.SLDASM; source parts still reference original model folders.
- Native SW2URDF config, mapping and validation: same solidworks/ directory, native_bindings.json, saved_export_config.xml, native_validation.json, sh_fasteners_fix.json, README_TH.md.
- 11 links /10 revolute joints,241 active CAD components,1,171,032 triangles. CAD total mass2.24359349166kg (materials unverified). All original joint elements preserved after SH bolt fix and parsed successfully.
- Tree: base_link -> waist_link -> shrug_link -> L/R_sh_mid -> L/R_upper_link -> L/R_el_mid -> L/R_fore_link. Logical joint names in URDF use lowercase waist/shrug, uppercase arm names.
- User verified SH rotation is correct. Do not change native URDF axes/signs/origins/limits casually. All native axes differ by a sign from the old STEP draft, so do not use that draft as authoritative.
- SH bolt fix complete:20 fasteners moved from L/R_upper_link to shrug_link (10 per side); stay with shoulder carrier, follow waist/shrug, not SH_P/SH_R. Geometry and inertias updated; all10 joint XML definitions identical to backup.
- Four-bar remains simplified: horn/coupler frozen on waist_link, shrug one revolute rocker. User asked feasibility; explained exact animation needs nonlinear closure solver, not constant-ratio mimic. Full four-bar animation was NOT implemented or promised as completed.
- There is a comparison export nong_description_sh_fixed/ next to canonical package. It is not a new authoritative source. Both packages now have .vscode/settings.json mapping their own package URI.
- VS Code last visibly displays comparison package successfully after adding its missing package map and Developer: Reload Window. Canonical convenience workspace: E:/final_proj/mice/model/nong_urdf/nong_urdf.code-workspace.
- CAD STLs/URDF must be made available to Studio locally; no copy/upload into Studio models/ has happened yet.

## Coordination / preserved work
- Main root E:/final_proj/mice/code is DIRTY from others/user: generated Studio app.js/index.html, settings_shared.json, Hub/help, voice/camera/config, dist exe, system headers, BRIDGE and other data. Preserve all; no reset/clean/add -A. Main HEAD c82daa6 when this worktree was created.
- Old A46-3 code is merged (handoff/tasks/robot-hotspot-live.md says deployed); its old BRIDGE claims on rig_setup_ui/rig_data/main_loop/html_parts/generated assets/web build manifest lack explicit RELEASE. Our BRIDGE entry REQUESTS release/coordination, not an inferred takeover. Resolve before overlapping edits/integration. Physical tests remain parked; do not revive them.
- Own claim was limited to new URDF renderer/config/serving/QC paths plus app_parts/{build_rig,scene,stl_meshes,urdf_import,project_save_load,save_state,boot}.js and docs/urdf_nong.md in OWN tree. Own claims will be explicitly released for Cross. No QC/driver/runtime/hardware resources acquired or process started.

## PC steps done 2026-10-23 06:06 (claude:xdlrot)
- Pulled main 1cb87f3, build_web, systems build, MiceHub.exe rebuilt with the spec, hub +
  Voice helper restarted, /api/version stale=false (3a460df0e536). Backups:
  scratch/deploy-a48-1-2026-10-23 (exe, voice.json, settings_shared, old plan patch).
- Copied model/nong_urdf/solidworks/export/nong_description (57 MB) to
  nong/main_python_set_nong/models/nong_description/ (git-ignored; nothing under model/ edited).
- `MICE_URDF_MODEL=<that folder> check_urdf_look`: 25/26. Real model: WAIST agree 1.00
  (axis 1.00), SHRUG 0.99 (axis 1.00). ALL 8 arm joints agree -0.14..0.07 with axis
  0.00..0.02: the URDF arm axes are PERPENDICULAR to the shapes' axes, not reversed.
  sign/offsetDeg cannot fix that, so urdf_view.json was left unchanged. URDF (ROS frame:
  y = left, z = up): SH_P/EL_P axis ~(-1,0,0) = forward axis; EL_R ~(0,-1,0) = lateral;
  SH_R (0,-0.54,-0.84) tilted. Looks like the CAD's P/R naming (or frame) differs from
  Studio's; a quick P<->R swap in the bindings broke the synthetic fixture checks
  (5 fails), so it is NOT a plain swap. Needs the URDF thread's decision.
- Studio > Views: Robot look = CAD model (URDF) loads "nong from SolidWorks", shows the 8
  axis warnings, a slider moves it (screenshots scratch/deploy-a48-1-2026-10-23/urdf-*.png).
  Put back to Simple shapes with the old sizes (dims identical) and the old pose.

## PC check after A48-2 (2026-10-23 06:35, claude:xdlrot)
- Pulled main ff72311, build_web, systems build, exe rebuilt with the spec, hub restarted
  (stale=false 4483d12f1d67). check_urdf_look with MICE_URDF_MODEL = the export folder: 30/31.
- Real model: fit L 15.9 deg (up 11.8), swapSh true, swapEl false; fit R 10.5 deg (up 10.5),
  swapSh true, swapEl false. Bindings: L_SH_P=L_SH_R(-), L_SH_R=L_SH_P, L_EL_P=L_EL_P,
  L_EL_R=L_EL_R(-), R_SH_P=R_SH_R(-), R_SH_R=R_SH_P(-), R_EL_P=R_EL_P, R_EL_R=R_EL_R(-).
- Agree from home: L_SH_P/L_SH_R/L_EL_P/L_EL_R 1.00 each, WAIST 1.00, SHRUG 1.00, but
  R_SH_P -0.22, R_SH_R 0.82, R_EL_P -0.10, R_EL_R -0.93: the RIGHT arm is still wrong.
- Warnings > 5 deg: yes, both arms ("left ... up to 16 deg", "right ... up to 10-15 deg").
- Studio > Views, CAD model: the two warnings still show. Left shoulder pitch 90 -> 150,
  seen from the Left view: the CAD left arm swings forward like the shapes' (screenshots
  scratch/deploy-a48-2-2026-10-23/left-up-*.png). Put back to Simple shapes, old pose and sizes.
  urdf_view.json not changed.

## PC check after A48-3 (2026-10-23 06:45, claude:xdlrot)
- main ce99f69, build_web, systems build, exe rebuilt (stale=false ed5ace9ea74b), hub restarted.
- check_urdf_look (real model): 33/34, real-model case still FAILS.
  Fit L 15.7 deg (up 14.6) swapSh, R 11.4 deg (up 11.4) swapSh; swapEl false both.
  Agree from home: left 1.00 x4, WAIST/SHRUG 1.00; R_SH_P -0.62, R_SH_R 0.43, R_EL_P -0.39,
  R_EL_R 0.71. Bindings as A48-2 except R_SH_P=R_SH_R now (+).
- qc/_urdf_real.json (git-ignored) sent to the coordinator in full. Note in it: the right
  hand tip is NOT from the mesh (`fromMesh: false`, local [145.8, 63.0, -91.0]) while the
  left one is (`fromMesh: true`, [-1.9, 4.7, -181.7]) - a likely cause of the right arm fit.
- Studio Views CAD: warnings "left up to 16 deg, right up to 21 deg". Raising each shoulder
  pitch +60 (Left / Right views): both CAD arms swing forward like the shapes, the right
  forearm sits differently. Screenshots scratch/deploy-a48-3-2026-10-23/{left,right}-up-*.png.
  Back to Simple shapes, old pose and sizes.

## Next
1. Full QC green -> PR -> merge.
2. PC: copy E:/final_proj/mice/model/nong_urdf/solidworks/export/nong_description
   into Studio's models folder (models/nong_description/), rebuild MiceHub.exe,
   run `MICE_URDF_MODEL=<that folder> python qc/run_qc.py --quiet check_urdf_look`
   and read the "real model" lines (bindings, senses, agree per joint). A joint
   with agree < 0.5 or "axis" < 0.7: set its sign/offsetDeg in urdf_view.json.
3. Lab day: robot-tests.md item 6.

## Blocked / not done
- Real SolidWorks URDF not tested yet (only on the PC). Not tested on the robot.
