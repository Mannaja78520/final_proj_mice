# Nong Studio: dynamic URDF display and motion parity

Owner: open — user requested handoff to Cross on 2026-10-23
Updated: 2026-10-23T05:08:45.8071617+07:00
Branch: task/A48-1-10230507-3ac1
Tree: E:/final_proj/mice/code/.staging-urdf-studio
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
- STOPPED at user's explicit handoff request, before Studio implementation. No source feature, integration, review or QC has been done for A48-1.
- Created an isolated clean Git worktree at the tree above from main c82daa6. No staging source changes. Do not reinitialize or overwrite old staging trees.

## Done
- Registered A48-1 as doing under codex:10230507-3ac1 in real root docs/PLAN.html; it will be handed off to todo before this turn ends.
- Read HANDOFF.md, AGENTS.md, CLAUDE.md, docs/COORDINATION.md, latest BRIDGE claims, docs/systems/studio.md, docs/web_style.md and Studio CLAUDE.md.
- Read applicable .agents/skills/{mice-web-check,mice-contract-check,mice-verification}/SKILL.md and .claude/skills/web-page-check/SKILL.md.
- Prior CAD and VS Code tasks finished: working native SolidWorks export and visible URDF; details below. Those files are outside code and local only.

## Facts found
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

## Next
1. Read this task; create a provider:session using plan.py, take A48-1 under real-root coordination mutex, record exact branch/tree/claims. Resolve old overlapping claims without discarding work.
2. Read only targeted functions around applyPose/buildRobot and persistence/video/realtime entry points. Review design per existing Codex-first independent review workflow; no review has run yet.
3. Implement generic URDF tree renderer: every link, parent->origin xyz/rpy->joint-axis rotation->child, visual origins/scales, multiple visuals, exact SI->Studio conversion, relative/package mesh resolution. Reject bad/missing/cyclic/unbound files clearly; handle async load failures/stale completions and dispose GPU resources.
4. Add configurable UI display modes with explicit dimension source state. URDF mode always keeps native size. Ask on switching to old mode: URDF dimensions or custom; provide cancel that preserves current mode/state, keep custom values, persist selection/dimensions in projects/drafts/settings without breaking legacy projects. Avoid changing servo calibration/limits by choosing a display.
5. IMPORTANT: old IK/collision/video fitting uses proxy rig dimensions. Drawing a URDF alone does not make motion correct. Ensure the kinematic chain used for fitting/IK matches displayed URDF, or explicitly resolve unsupported mapping before claiming parity. Do not merely overlay detailed meshes on mismatched old proxy pivots.
6. Register new files/checks in docs/systems.json; build systems + web assets; add help section in main_python/web/help/parts/studio.html and rebuild help; save_patch.py per Studio rules. Actual CAD models remain excluded/private.
7. Permanent browser/fake regression: load real local model privately plus synthetic rotated/non-axis-aligned fixture; zero pose/link transforms vs independent FK; all10 isolated joints; left-only/right-only hand up, mirrored camera option, elbows/waist/shrug; video -> fitted keys -> playback; realtime dummy -> pose; monitor reported pose; timeline/slider/export parity. Compare numeric world positions, render state and fake wire, not screenshot only. Verify modes/dimension prompt accept/cancel/custom, reload/project persistence, missing meshes/bad URDF/reselect races, phone/desktop layouts.
8. Run applicable QC quiet, deliberate sabotage proving new check fails, independent final review, one exclusive full frozen-tree QC gate, then authorized integration/build/deploy with backups. Preserve old user projects/settings and all unrelated dirt. Do not report fake checks as physical measurements.

## Blocked / not done
- Implementation, local Studio model installation, reviews, all A48-1 tests and deployment are NOT STARTED.
- Old overlapping file-claim coordination unresolved. No technical blocker established; task paused solely because user requested this handoff.
