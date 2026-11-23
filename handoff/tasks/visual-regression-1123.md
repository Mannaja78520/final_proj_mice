# Screenshot regression + numeric 3D check + Thai-leak QC

Owner: claude
Updated: 2026-11-23 04:05 +0000
Branch: claude/project-thread-z9y1v3
Last commit: this checkpoint
Plan: none (user ask 2026-11-23: "ได้เช็คทั้งหมดแล้วจริงปะ ทำไมยังเหลือพังอีกเยอะ")

## Goal
Look at every page like a person (screenshots, 4 languages, dark/light, phone/desktop), check the 3D robot
numerically against the URDF, list visual bugs, add what a script can decide to QC.

## Doing now
Reading the full screenshot run (/tmp/vis/full, not committed) and fixing bugs outside Studio 3D / Tools page / camera threads.

## File status
Baseline: ed5bd89

| File | Change | State | Verification | Commit |
| --- | --- | --- | --- | --- |
| `tools/visual/shoot.js`, `pages.json`, `probe.js`, `serve_hub.py` | screenshot + probe tool (data-driven pages) | done | ran, 4 langs, cloud fake hub | uncommitted |
| `tools/visual/urdf_fk.py`, `urdf_page.js`, `urdf_numeric.py` | independent FK vs page joints | done | repo nong.urdf: 0.000 mm; real SolidWorks model NOT run | uncommitted |
| `qc/checks/check_visual_language.py` | Thai-in-en/zh/ja + popup-at-corner scan | done | failed before fix, passes after (quick, cloud) | uncommitted |
| `main_python/web/home/parts/settings.js`, `hub.html` | settings summary in translatable pieces | done | check_visual_language | uncommitted |
| `shared/web/lang/{en,zh,ja}.json`, `lang/help/*.json` | entries for settings texts, Help Prev/Next | done | tools/lang.py check | uncommitted |
| `tools/lang_add.py` | append pack entries without reformatting | done | used | uncommitted |

## Facts found
- Screenshots taken mid-fade show a dim selected tab that is not a bug: shoot.js disables transitions.
- Committed nong.urdf names meshes/*.stl but the STLs sit in models/ (404 in CAD look) and torso/fore STLs are in assembly-world coordinates: CAD look in a clean checkout shows fragments. Studio 3D thread's area.
- haveRobot() in Studio means "connected to a robot", not "3D ready".

## Done
- see File status

## Next
1. Finish reading screenshots; Codex/Gemini review; fix; full QC; PR.

## Blocked
- Real URDF check needs the PC (E:\final_proj\mice\mice_system) to run tools/visual/urdf_numeric.py with MICE model.
