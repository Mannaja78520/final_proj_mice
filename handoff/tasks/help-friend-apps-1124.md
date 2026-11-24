# help-friend-apps-1124 ? In-app Help for All-Jao, Reconize and Photobooth
Owner: codex:11240637-1d82 (Claude reviews)
Plan: A59-1 (system)
Branch: claude/project-thread-181856 ? baseline 7f8b1b3
Updated: 2026-11-24 07:20 +0700
Last commit: 5b5ff25 (targeted gate)

## Goal
Detailed step-by-step app and Hub guides in th/en/zh/ja with real app screenshots and demo data.
Keep each native language/palette. Capture Hub variations. Check screenshot-text match with Gemini 4 medium.
Never edit Face_Regonize, All-Jao-Games or Photobooth. Ask friend nothing. Use the existing request list.
Run targeted/full QC and draft PR. Merge only when green, then rebuild/restart the PC Hub and retest four languages. Serialize QC and builds, push WIP, report in Thai.

## Added 2026-11-23 23:36 ? Reconize Help drop-in
Ready to copy from docs/friend/reconize_help_package/help to Face_Regonize/help by user or designated person.
Thai/English README covers install, precedence and recapture. Keep byte-identical to apps/faces/help with QC.

## Doing now
Step 4 follow-up: implement Gemini picture/text findings and both Photobooth guest themes, then retest.

## Done
- 8998b6e: inspected the real UI for all three in Edge against scratch instances.
- aa8e2ad: captured and visually reviewed 43 native screenshots. Demo photos, hidden QR/addresses and sign-in hints.
- Four-language walkthroughs, native variant documentation, Reconize package and byte-parity QC written.
- All-Jao wheel/claw name labels render question marks in partner source. Added to friend request list.

## Facts found
- Reconize English: sign-in, dashboard, people, import, activities, recognition, CCTV, Connect, attendance, uploads, history, reports, PDPA, photos, video, settings and privacy.
- All-Jao Thai/English: welcome, four games and four organizer tabs. Quiz reachable via top game tabs. Normal Hub proxy returned 200.
- Photobooth English: guest flow through QR, synthetic captures, admin sign-in and nine organizer views, unpaired route.
- Help resolves exact variants first, then declared nativeVariant. The partner help root takes precedence.
- Scratch used 4173, 5173, 8000, 8111/8113. No real data, fake Hub or PyInstaller used.

## Next
Targeted QC passed 1285/0 on e6fc031. Gemini 4 Argon Medium reviewed 43 images. Full QC on 5b5ff25: 10632/8.

## Blocked
Full gate failed on one missing Plan field (restored here), three Home language checks and four camera checks. Baseline comparison pending. [Draft #245](https://github.com/Mannaja78520/final_proj_mice/pull/245).

## File status
| File | Change | State | Verification | Commit |
|---|---|---|---|---|
| apps/all-jao/help/en.html | guide, parity check or docs | written | targeted QC 1285/0 | this checkpoint |
| apps/all-jao/help/help.json | native capture and Help support | written | targeted QC 1285/0 | aa8e2ad |
| apps/all-jao/help/img/th-light-game-claw-admin.webp | native app screenshot | written | reviewed in Edge | aa8e2ad |
| apps/all-jao/help/img/th-light-game-claw.webp | native app screenshot | written | reviewed in Edge | aa8e2ad |
| apps/all-jao/help/img/th-light-game-login.webp | native app screenshot | written | reviewed in Edge | aa8e2ad |
| apps/all-jao/help/img/th-light-game-memory-admin.webp | native app screenshot | written | reviewed in Edge | aa8e2ad |
| apps/all-jao/help/img/th-light-game-memory.webp | native app screenshot | written | reviewed in Edge | aa8e2ad |
| apps/all-jao/help/img/th-light-game-quiz-admin.webp | native app screenshot | written | reviewed in Edge | aa8e2ad |
| apps/all-jao/help/img/th-light-game-quiz.webp | native app screenshot | written | reviewed in Edge | aa8e2ad |
| apps/all-jao/help/img/th-light-game-wheel-admin.webp | native app screenshot | written | reviewed in Edge | aa8e2ad |
| apps/all-jao/help/img/th-light-game-wheel.webp | native app screenshot | written | reviewed in Edge | aa8e2ad |
| apps/all-jao/help/ja.html | guide, parity check or docs | written | targeted QC 1285/0 | this checkpoint |
| apps/all-jao/help/shots.json | native capture and Help support | written | targeted QC 1285/0 | aa8e2ad |
| apps/all-jao/help/th.html | guide, parity check or docs | written | targeted QC 1285/0 | this checkpoint |
| apps/all-jao/help/zh.html | guide, parity check or docs | written | targeted QC 1285/0 | this checkpoint |
| apps/faces/help/en.html | guide, parity check or docs | written | targeted QC 1285/0 | this checkpoint |
| apps/faces/help/help.json | native capture and Help support | written | targeted QC 1285/0 | aa8e2ad |
| apps/faces/help/img/en-light-reconize-activities.webp | native app screenshot | written | reviewed in Edge | aa8e2ad |
| apps/faces/help/img/en-light-reconize-attendees.webp | native app screenshot | written | reviewed in Edge | aa8e2ad |
| apps/faces/help/img/en-light-reconize-cctv.webp | native app screenshot | written | reviewed in Edge | aa8e2ad |
| apps/faces/help/img/en-light-reconize-connect.webp | native app screenshot | written | reviewed in Edge | aa8e2ad |
| apps/faces/help/img/en-light-reconize-dashboard.webp | native app screenshot | written | reviewed in Edge | aa8e2ad |
| apps/faces/help/img/en-light-reconize-event-photos.webp | native app screenshot | written | reviewed in Edge | aa8e2ad |
| apps/faces/help/img/en-light-reconize-history.webp | native app screenshot | written | reviewed in Edge | aa8e2ad |
| apps/faces/help/img/en-light-reconize-import.webp | native app screenshot | written | reviewed in Edge | aa8e2ad |
| apps/faces/help/img/en-light-reconize-login.webp | native app screenshot | written | reviewed in Edge | aa8e2ad |
| apps/faces/help/img/en-light-reconize-pdpa.webp | native app screenshot | written | reviewed in Edge | aa8e2ad |
| apps/faces/help/img/en-light-reconize-people.webp | native app screenshot | written | reviewed in Edge | aa8e2ad |
| apps/faces/help/img/en-light-reconize-privacy.webp | native app screenshot | written | reviewed in Edge | aa8e2ad |
| apps/faces/help/img/en-light-reconize-recognition.webp | native app screenshot | written | reviewed in Edge | aa8e2ad |
| apps/faces/help/img/en-light-reconize-reports.webp | native app screenshot | written | reviewed in Edge | aa8e2ad |
| apps/faces/help/img/en-light-reconize-settings.webp | native app screenshot | written | reviewed in Edge | aa8e2ad |
| apps/faces/help/img/en-light-reconize-uploads.webp | native app screenshot | written | reviewed in Edge | aa8e2ad |
| apps/faces/help/img/en-light-reconize-video.webp | native app screenshot | written | reviewed in Edge | aa8e2ad |
| apps/faces/help/ja.html | guide, parity check or docs | written | targeted QC 1285/0 | this checkpoint |
| apps/faces/help/shots.json | native capture and Help support | written | targeted QC 1285/0 | aa8e2ad |
| apps/faces/help/th.html | guide, parity check or docs | written | targeted QC 1285/0 | this checkpoint |
| apps/faces/help/zh.html | guide, parity check or docs | written | targeted QC 1285/0 | this checkpoint |
| apps/photobooth/help/en.html | guide, parity check or docs | written | targeted QC 1285/0 | this checkpoint |
| apps/photobooth/help/help.json | native capture and Help support | written | targeted QC 1285/0 | aa8e2ad |
| apps/photobooth/help/img/en-light-booth-activity.webp | native app screenshot | written | reviewed in Edge | aa8e2ad |
| apps/photobooth/help/img/en-light-booth-capture.webp | native app screenshot | written | reviewed in Edge | aa8e2ad |
| apps/photobooth/help/img/en-light-booth-choose.webp | native app screenshot | written | reviewed in Edge | aa8e2ad |
| apps/photobooth/help/img/en-light-booth-decorate.webp | native app screenshot | written | reviewed in Edge | aa8e2ad |
| apps/photobooth/help/img/en-light-booth-delivery.webp | native app screenshot | written | reviewed in Edge | aa8e2ad |
| apps/photobooth/help/img/en-light-booth-editor.webp | native app screenshot | written | reviewed in Edge | aa8e2ad |
| apps/photobooth/help/img/en-light-booth-frames.webp | native app screenshot | written | reviewed in Edge | aa8e2ad |
| apps/photobooth/help/img/en-light-booth-history.webp | native app screenshot | written | reviewed in Edge | aa8e2ad |
| apps/photobooth/help/img/en-light-booth-profiles.webp | native app screenshot | written | reviewed in Edge | aa8e2ad |
| apps/photobooth/help/img/en-light-booth-retention.webp | native app screenshot | written | reviewed in Edge | aa8e2ad |
| apps/photobooth/help/img/en-light-booth-review.webp | native app screenshot | written | reviewed in Edge | aa8e2ad |
| apps/photobooth/help/img/en-light-booth-sign-in.webp | native app screenshot | written | reviewed in Edge | aa8e2ad |
| apps/photobooth/help/img/en-light-booth-start.webp | native app screenshot | written | reviewed in Edge | aa8e2ad |
| apps/photobooth/help/img/en-light-booth-statistics.webp | native app screenshot | written | reviewed in Edge | aa8e2ad |
| apps/photobooth/help/img/en-light-booth-system.webp | native app screenshot | written | reviewed in Edge | aa8e2ad |
| apps/photobooth/help/img/en-light-booth-test.webp | native app screenshot | written | reviewed in Edge | aa8e2ad |
| apps/photobooth/help/img/en-light-booth-unpaired.webp | native app screenshot | written | reviewed in Edge | aa8e2ad |
| apps/photobooth/help/ja.html | guide, parity check or docs | written | targeted QC 1285/0 | this checkpoint |
| apps/photobooth/help/shots.json | native capture and Help support | written | targeted QC 1285/0 | aa8e2ad |
| apps/photobooth/help/th.html | guide, parity check or docs | written | targeted QC 1285/0 | this checkpoint |
| apps/photobooth/help/zh.html | guide, parity check or docs | written | targeted QC 1285/0 | this checkpoint |
| docs/extensions.md | guide, parity check or docs | written | targeted QC 1285/0 | this checkpoint |
| docs/friend/friend_requests_all_2026-11-23.md | guide, parity check or docs | written | targeted QC 1285/0 | this checkpoint |
| docs/friend/reconize_help_package/README.md | guide, parity check or docs | written | targeted QC 1285/0 | this checkpoint |
| docs/friend/reconize_help_package/help/en.html | package copy | written | targeted QC 1285/0 | this checkpoint |
| docs/friend/reconize_help_package/help/help.json | package copy | written | targeted QC 1285/0 | this checkpoint |
| docs/friend/reconize_help_package/help/img/en-dark-faces-open.webp | package copy | written | reviewed capture copied | this checkpoint |
| docs/friend/reconize_help_package/help/img/en-light-faces-open.webp | package copy | written | reviewed capture copied | this checkpoint |
| docs/friend/reconize_help_package/help/img/en-light-reconize-activities.webp | package copy | written | reviewed capture copied | this checkpoint |
| docs/friend/reconize_help_package/help/img/en-light-reconize-attendees.webp | package copy | written | reviewed capture copied | this checkpoint |
| docs/friend/reconize_help_package/help/img/en-light-reconize-cctv.webp | package copy | written | reviewed capture copied | this checkpoint |
| docs/friend/reconize_help_package/help/img/en-light-reconize-connect.webp | package copy | written | reviewed capture copied | this checkpoint |
| docs/friend/reconize_help_package/help/img/en-light-reconize-dashboard.webp | package copy | written | reviewed capture copied | this checkpoint |
| docs/friend/reconize_help_package/help/img/en-light-reconize-event-photos.webp | package copy | written | reviewed capture copied | this checkpoint |
| docs/friend/reconize_help_package/help/img/en-light-reconize-history.webp | package copy | written | reviewed capture copied | this checkpoint |
| docs/friend/reconize_help_package/help/img/en-light-reconize-import.webp | package copy | written | reviewed capture copied | this checkpoint |
| docs/friend/reconize_help_package/help/img/en-light-reconize-login.webp | package copy | written | reviewed capture copied | this checkpoint |
| docs/friend/reconize_help_package/help/img/en-light-reconize-pdpa.webp | package copy | written | reviewed capture copied | this checkpoint |
| docs/friend/reconize_help_package/help/img/en-light-reconize-people.webp | package copy | written | reviewed capture copied | this checkpoint |
| docs/friend/reconize_help_package/help/img/en-light-reconize-privacy.webp | package copy | written | reviewed capture copied | this checkpoint |
| docs/friend/reconize_help_package/help/img/en-light-reconize-recognition.webp | package copy | written | reviewed capture copied | this checkpoint |
| docs/friend/reconize_help_package/help/img/en-light-reconize-reports.webp | package copy | written | reviewed capture copied | this checkpoint |
| docs/friend/reconize_help_package/help/img/en-light-reconize-settings.webp | package copy | written | reviewed capture copied | this checkpoint |
| docs/friend/reconize_help_package/help/img/en-light-reconize-uploads.webp | package copy | written | reviewed capture copied | this checkpoint |
| docs/friend/reconize_help_package/help/img/en-light-reconize-video.webp | package copy | written | reviewed capture copied | this checkpoint |
| docs/friend/reconize_help_package/help/img/ja-dark-faces-open.webp | package copy | written | reviewed capture copied | this checkpoint |
| docs/friend/reconize_help_package/help/img/ja-light-faces-open.webp | package copy | written | reviewed capture copied | this checkpoint |
| docs/friend/reconize_help_package/help/img/th-dark-faces-open.webp | package copy | written | reviewed capture copied | this checkpoint |
| docs/friend/reconize_help_package/help/img/th-light-faces-open.webp | package copy | written | reviewed capture copied | this checkpoint |
| docs/friend/reconize_help_package/help/img/zh-dark-faces-open.webp | package copy | written | reviewed capture copied | this checkpoint |
| docs/friend/reconize_help_package/help/img/zh-light-faces-open.webp | package copy | written | reviewed capture copied | this checkpoint |
| docs/friend/reconize_help_package/help/ja.html | package copy | written | targeted QC 1285/0 | this checkpoint |
| docs/friend/reconize_help_package/help/shots.json | package copy | written | targeted QC 1285/0 | this checkpoint |
| docs/friend/reconize_help_package/help/th.html | package copy | written | targeted QC 1285/0 | this checkpoint |
| docs/friend/reconize_help_package/help/zh.html | package copy | written | targeted QC 1285/0 | this checkpoint |
| docs/systems/agents.md | guide, parity check or docs | written | targeted QC 1285/0 | this checkpoint |
| docs/systems/app-faces.md | guide, parity check or docs | written | targeted QC 1285/0 | this checkpoint |
| docs/systems/app-small.md | guide, parity check or docs | written | targeted QC 1285/0 | this checkpoint |
| handoff/tasks/help-friend-apps-1124.md | guide, parity check or docs | written | targeted QC 1285/0 | this checkpoint |
| main_python/hub_api_help.py | native capture and Help support | written | targeted QC 1285/0 | aa8e2ad |
| main_python/web/help.html | native capture and Help support | written | targeted QC 1285/0 | aa8e2ad |
| main_python/web/help/parts/bytask.html | native capture and Help support | written | targeted QC 1285/0 | aa8e2ad |
| qc/checks/check_app_help.py | guide, parity check or docs | written | targeted QC 1285/0 | this checkpoint |
| shared/web/lang/help/ja.json | native capture and Help support | written | targeted QC 1285/0 | aa8e2ad |
| shared/web/lang/help/th.json | native capture and Help support | written | targeted QC 1285/0 | aa8e2ad |
| shared/web/lang/help/zh.json | native capture and Help support | written | targeted QC 1285/0 | aa8e2ad |
| tools/help_shots.py | native capture and Help support | written | targeted QC 1285/0 | aa8e2ad |
