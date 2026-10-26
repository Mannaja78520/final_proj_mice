# Rig Nong from two group cheer videos with camera changes

Owner: codex:10261829-d886
Updated: 2026-10-26 18:30 +0700
Branch: codex/cheer-rig-1026 (metadata only; application source unchanged)
Last commit: this checkpoint (metadata only; media stay private)
Plan: A48-20

## Goal
Rig Nong from both supplied cheer videos. Multiple dancers perform the same routine and the camera changes angle. Produce two private Studio projects and review previews.

## Doing now
Complete. All four Blender rigs and previews validated, JSON/YAML/music saved, two newly named Studio projects installed, ZIP tested. No running process, application source change or hardware command.

## File status
Baseline: root had unrelated source/config/EXE/project/plan changes; preserve all. Only own task and private artifact directory are owned.

| File | Change | State | Verification | Commit |
| --- | --- | --- | --- | --- |
| `handoff/tasks/cheer-rig-1026.md` | task status | doing | manual | this checkpoint |
| `.local/cheer_rig_1026/I0lCxX8373M.mp4` | local reference | done | decoded 168.28 seconds | private, uncommitted |
| `.local/cheer_rig_1026/CLG7VdVhhLM.mp4` | local reference | done | decoded 94.84 seconds | private, uncommitted |
| `.local/cheer_rig_1026/I0lCxX8373M_sheet.jpg` | contact sheet | done | visually inspected | private, uncommitted |
| `.local/cheer_rig_1026/CLG7VdVhhLM_sheet.jpg` | contact sheet | done | visually inspected | private, uncommitted |
| `.local/cheer_rig_1026/extract_group.py` | offline multi-person extraction | done | complete 8 Hz extraction and overlays | private, uncommitted |
| `.local/cheer_rig_1026/fit_studio.cjs` | existing Studio solver offline | done | 788/440 keys, collision/time checks pass | private, uncommitted |
| `.local/cheer_rig_1026/build_blender.py` | exact transform hierarchy | done | four native files saved | private, uncommitted |
| `.local/cheer_rig_1026/render_motion.py` | reference and robot previews | done | full rendered sequences | private, uncommitted |
| `.local/cheer_rig_1026/compose_preview.py` | paired preview/audio | done | four complete audio/video decodes pass | private, uncommitted |
| `.local/cheer_rig_1026/verify_blender.py` | native rig verification | done | four files, 10 animated controls each | private, uncommitted |
| `.local/cheer_rig_1026/finish_artifacts.py` | artifact checks/package | done | independent angle/time/YAML/video/ZIP checks pass | private, uncommitted |
| `.local/cheer_rig_1026/README_TH.md` | instructions and real limits | done | manual | private, uncommitted |
| `.local/cheer_rig_1026/come_and_cheer.json` | speed-limited show | done | 788 poses/paths/timing incl HOME entry pass | private, uncommitted |
| `.local/cheer_rig_1026/witsawa_kriangkrai.json` | speed-limited show | done | 440 poses/paths/timing incl HOME entry pass | private, uncommitted |
| `.local/cheer_rig_1026/come_and_cheer.yaml` | existing Studio export | done | independently parsed and matched all JSON angles/times | private, uncommitted |
| `.local/cheer_rig_1026/witsawa_kriangkrai.yaml` | existing Studio export | done | independently parsed and matched all JSON angles/times | private, uncommitted |
| `.local/cheer_rig_1026/come_and_cheer.blend` | speed-limited editable rig | done | native render pass | private, uncommitted |
| `.local/cheer_rig_1026/witsawa_kriangkrai.blend` | speed-limited editable rig | done | native render pass | private, uncommitted |
| `.local/cheer_rig_1026/come_and_cheer_reference.blend` | reference editable rig | done | native render pass | private, uncommitted |
| `.local/cheer_rig_1026/witsawa_kriangkrai_reference.blend` | reference editable rig | done | native render pass | private, uncommitted |
| `nong/main_python_set_nong/projects/cheer_come_and_cheer_20261026.json` | new user project | done | new name, valid 10-joint JSON, no overwrite | private, uncommitted |
| `nong/main_python_set_nong/projects/cheer_witsawa_kriangkrai_20261026.json` | new user project | done | new name, valid 10-joint JSON, no overwrite | private, uncommitted |
| `nong/main_python_set_nong/sequences/cheer_come_and_cheer_20261026.yaml` | new user sequence | done | parsed format, no overwrite | private, uncommitted |
| `nong/main_python_set_nong/sequences/cheer_witsawa_kriangkrai_20261026.yaml` | new user sequence | done | parsed format, no overwrite | private, uncommitted |

Private exact per-file inventory including generated intermediates: .local/cheer_rig_1026/file_status.csv (5937 rows). Deliverable hashes: .local/cheer_rig_1026/manifest.json; independent results: .local/cheer_rig_1026/validation.json.

## Facts found
- Studio pose_from_video.js:61 sets numPoses=1; ordinary UI cannot reliably handle group clips. vidBodyFrame:161 removes camera yaw for arm directions. Waist mapping uses camera-relative yaw so keep waist neutral for these reference clips.
- rig_default.json contains measured CAD rig. settings_shared.json includes malformed test rig min:[30], so do not use that as calibrated production data.
- Existing user source changes in Studio setup/view/style must remain intact.
- Artifacts use shipped rig_default, not malformed settings_shared. Both HOME entry legs clear; entry needs 864/878 ms <=1000 ms. At 60 deg/s peak most human cheer transitions must reduce amplitude. Reference Blender animation is explicitly virtual only; robot JSON remains speed/path checked. Waist and shrug stay at saved neutral to avoid confusing camera yaw with human yaw.

## Done
- Downloaded both user reference clips locally. Contact sheets confirm synchronized red-shirt dancers and several cuts/front/oblique views. No application source, service, robot or calibration writes.
- Extracted 1347/759 samples at 8 Hz; kept dance windows 5–163.375 and 5–89.875 s. Group corroboration in 502/337 samples. Original Studio fitter and 1-degree collision sampling reused without changing application files. Wire rounding corrected offline and rechecked.
- Four Blender rigs created and rendered; two original-rhythm references plus two constrained to saved 60 deg/s peak. User MP3 cues contain 1 s prep silence for robot versions. No video/model files go to public Git.

- Final validation passed: 1228 checked robot poses and every leg, peak-speed floors, HOME entries, YAML parity, four full decoded MP4s with audio, four native Blender rigs with 10 animated controls each. ZIP 16 deliverables, 54,613,911 bytes, CRC pass. Saved two new Studio projects and two YAMLs under claimed unique names.

## Next
1. No required work remains; deliver ZIP and reference previews. Optional future refinement can use the editable reference rigs.
2. Full application QC not run: no application source changed. Real hardware remains untested, outside this artifact task.

## Blocked
- None. Defaulted to full dance windows and group corroboration after optional question remained unanswered. No hardware acceptance claimed.
