# help-friend-apps-1124 - Detailed in-app Help
Owner: codex:11240637-1d82 (Claude reviews)
Plan: A59-1 (system)
Branch: claude/project-thread-181856; baseline 7f8b1b3
Updated: 2026-11-24 07:33 +0700
Last commit: 3f1459c (verified Help source and assets)

## Goal
Three real-app guides in th/en/zh/ja, demo data, no edits to friend repos. Verify, push scoped WIP, merge only when green, rebuild/retest MiceHub, report in Thai.

## Added 2026-11-23 23:36 - Reconize Help drop-in
Copy docs/friend/reconize_help_package/help to Face_Regonize/help by user or designated person. Bilingual README covers install, precedence and recapture. QC checks exact parity.

## Doing now
Help verification complete. Resume deployment after the full release gate is green.

## Done
- Captured and inspected 49 native screenshots. All-Jao through Hub proxy. Photobooth guest flow in Midnight Blue and Minimal Light with synthetic camera.
- Gemini 4 Argon Medium viewed 43 first-round images. Added scroll cues, populated Reconize Activities and Photobooth frame confirmation. Stopped demo processes.
- Draft PR #245. At 3f1459c: targeted QC 1431/0 and isolated Edge /help 376/376 images across four languages and two themes. Evidence in _out/help-friend-1124/{final-targeted-qc,help-browser-smoke}.log.

## Facts found
- Reconize English: login, dashboard, people/import, activities, recognition, CCTV/Connect, attendance, uploads/history, reports, consent/photos/video, settings and privacy.
- All-Jao Thai/English: welcome, four games and organizer tabs. Quiz also in top tabs. Player-name question-mark labels listed in friend requests.
- Photobooth English: guest flow through QR, organizer login/profiles/editor/frames/test/history/stats/activity/retention/system.
- Help resolves exact image, native language in requested mode, then native default. Installed partner Help wins. QC-generated reports excluded from staging.

## Next
After baseline checks pass, reconcile latest main, run the full gate, merge PR #245 and rebuild/restart MiceHub from clean main. Retest installed /help in all four languages.

## Blocked
Full QC at 5b5ff25 was 10632/8. Plan field fixed and retested. Same 3 Home language and 4 PC camera failures on unchanged main adcd3466 (171/7). Merge, rebuild and installed-Hub check pending.

## File status
| File | Change | State | Verification | Commit |
|---|---|---|---|---|
| apps/all-jao/help/en.html | Help, package, capture or QC | written | targeted QC 1431/0 | 3f1459c |
| apps/all-jao/help/help.json | Help, package, capture or QC | written | targeted QC 1285/0 | aa8e2ad |
| apps/all-jao/help/img/th-light-game-claw-admin.webp | native screenshot | written | visually checked | aa8e2ad |
| apps/all-jao/help/img/th-light-game-claw.webp | native screenshot | written | visually checked | aa8e2ad |
| apps/all-jao/help/img/th-light-game-login.webp | native screenshot | written | visually checked | aa8e2ad |
| apps/all-jao/help/img/th-light-game-memory-admin.webp | native screenshot | written | visually checked | aa8e2ad |
| apps/all-jao/help/img/th-light-game-memory.webp | native screenshot | written | visually checked | aa8e2ad |
| apps/all-jao/help/img/th-light-game-quiz-admin.webp | native screenshot | written | visually checked | aa8e2ad |
| apps/all-jao/help/img/th-light-game-quiz.webp | native screenshot | written | visually checked | aa8e2ad |
| apps/all-jao/help/img/th-light-game-wheel-admin.webp | native screenshot | written | visually checked | aa8e2ad |
| apps/all-jao/help/img/th-light-game-wheel.webp | native screenshot | written | visually checked | aa8e2ad |
| apps/all-jao/help/ja.html | Help, package, capture or QC | written | targeted QC 1431/0 | 3f1459c |
| apps/all-jao/help/shots.json | Help, package, capture or QC | written | targeted QC 1431/0 | 3f1459c |
| apps/all-jao/help/th.html | Help, package, capture or QC | written | targeted QC 1431/0 | 3f1459c |
| apps/all-jao/help/zh.html | Help, package, capture or QC | written | targeted QC 1431/0 | 3f1459c |
| apps/faces/help/en.html | Help, package, capture or QC | written | targeted QC 1431/0 | 3f1459c |
| apps/faces/help/help.json | Help, package, capture or QC | written | targeted QC 1285/0 | aa8e2ad |
| apps/faces/help/img/en-light-reconize-activities.webp | native screenshot | written | visually checked | 3f1459c |
| apps/faces/help/img/en-light-reconize-attendees.webp | native screenshot | written | visually checked | aa8e2ad |
| apps/faces/help/img/en-light-reconize-cctv.webp | native screenshot | written | visually checked | aa8e2ad |
| apps/faces/help/img/en-light-reconize-connect.webp | native screenshot | written | visually checked | aa8e2ad |
| apps/faces/help/img/en-light-reconize-dashboard.webp | native screenshot | written | visually checked | aa8e2ad |
| apps/faces/help/img/en-light-reconize-event-photos.webp | native screenshot | written | visually checked | aa8e2ad |
| apps/faces/help/img/en-light-reconize-history.webp | native screenshot | written | visually checked | aa8e2ad |
| apps/faces/help/img/en-light-reconize-import.webp | native screenshot | written | visually checked | aa8e2ad |
| apps/faces/help/img/en-light-reconize-login.webp | native screenshot | written | visually checked | aa8e2ad |
| apps/faces/help/img/en-light-reconize-pdpa.webp | native screenshot | written | visually checked | aa8e2ad |
| apps/faces/help/img/en-light-reconize-people.webp | native screenshot | written | visually checked | aa8e2ad |
| apps/faces/help/img/en-light-reconize-privacy.webp | native screenshot | written | visually checked | aa8e2ad |
| apps/faces/help/img/en-light-reconize-recognition.webp | native screenshot | written | visually checked | aa8e2ad |
| apps/faces/help/img/en-light-reconize-reports.webp | native screenshot | written | visually checked | aa8e2ad |
| apps/faces/help/img/en-light-reconize-settings.webp | native screenshot | written | visually checked | 3f1459c |
| apps/faces/help/img/en-light-reconize-uploads.webp | native screenshot | written | visually checked | aa8e2ad |
| apps/faces/help/img/en-light-reconize-video.webp | native screenshot | written | visually checked | aa8e2ad |
| apps/faces/help/ja.html | Help, package, capture or QC | written | targeted QC 1431/0 | 3f1459c |
| apps/faces/help/shots.json | Help, package, capture or QC | written | targeted QC 1431/0 | 3f1459c |
| apps/faces/help/th.html | Help, package, capture or QC | written | targeted QC 1431/0 | 3f1459c |
| apps/faces/help/zh.html | Help, package, capture or QC | written | targeted QC 1431/0 | 3f1459c |
| apps/photobooth/help/en.html | Help, package, capture or QC | written | targeted QC 1431/0 | 3f1459c |
| apps/photobooth/help/help.json | Help, package, capture or QC | written | targeted QC 1285/0 | aa8e2ad |
| apps/photobooth/help/img/en-dark-booth-capture.webp | native screenshot | written | visually checked | 3f1459c |
| apps/photobooth/help/img/en-dark-booth-choose.webp | native screenshot | written | visually checked | 3f1459c |
| apps/photobooth/help/img/en-dark-booth-decorate.webp | native screenshot | written | visually checked | 3f1459c |
| apps/photobooth/help/img/en-dark-booth-delivery.webp | native screenshot | written | visually checked | 3f1459c |
| apps/photobooth/help/img/en-dark-booth-review.webp | native screenshot | written | visually checked | 3f1459c |
| apps/photobooth/help/img/en-dark-booth-start.webp | native screenshot | written | visually checked | 3f1459c |
| apps/photobooth/help/img/en-light-booth-activity.webp | native screenshot | written | visually checked | aa8e2ad |
| apps/photobooth/help/img/en-light-booth-capture.webp | native screenshot | written | visually checked | 3f1459c |
| apps/photobooth/help/img/en-light-booth-choose.webp | native screenshot | written | visually checked | 3f1459c |
| apps/photobooth/help/img/en-light-booth-decorate.webp | native screenshot | written | visually checked | 3f1459c |
| apps/photobooth/help/img/en-light-booth-delivery.webp | native screenshot | written | visually checked | 3f1459c |
| apps/photobooth/help/img/en-light-booth-editor.webp | native screenshot | written | visually checked | aa8e2ad |
| apps/photobooth/help/img/en-light-booth-frames.webp | native screenshot | written | visually checked | aa8e2ad |
| apps/photobooth/help/img/en-light-booth-history.webp | native screenshot | written | visually checked | aa8e2ad |
| apps/photobooth/help/img/en-light-booth-profiles.webp | native screenshot | written | visually checked | aa8e2ad |
| apps/photobooth/help/img/en-light-booth-retention.webp | native screenshot | written | visually checked | aa8e2ad |
| apps/photobooth/help/img/en-light-booth-review.webp | native screenshot | written | visually checked | 3f1459c |
| apps/photobooth/help/img/en-light-booth-sign-in.webp | native screenshot | written | visually checked | aa8e2ad |
| apps/photobooth/help/img/en-light-booth-start.webp | native screenshot | written | visually checked | 3f1459c |
| apps/photobooth/help/img/en-light-booth-statistics.webp | native screenshot | written | visually checked | aa8e2ad |
| apps/photobooth/help/img/en-light-booth-system.webp | native screenshot | written | visually checked | aa8e2ad |
| apps/photobooth/help/img/en-light-booth-test.webp | native screenshot | written | visually checked | aa8e2ad |
| apps/photobooth/help/img/en-light-booth-unpaired.webp | native screenshot | written | visually checked | aa8e2ad |
| apps/photobooth/help/ja.html | Help, package, capture or QC | written | targeted QC 1431/0 | 3f1459c |
| apps/photobooth/help/shots.json | Help, package, capture or QC | written | targeted QC 1431/0 | 3f1459c |
| apps/photobooth/help/th.html | Help, package, capture or QC | written | targeted QC 1431/0 | 3f1459c |
| apps/photobooth/help/zh.html | Help, package, capture or QC | written | targeted QC 1431/0 | 3f1459c |
| docs/extensions.md | Help, package, capture or QC | written | targeted QC 1431/0 | 3f1459c |
| docs/friend/friend_requests_all_2026-11-23.md | Help, package, capture or QC | written | targeted QC 1285/0 | e6fc031 |
| docs/friend/reconize_help_package/README.md | Help, package, capture or QC | written | targeted QC 1431/0 | 3f1459c |
| docs/friend/reconize_help_package/help/en.html | Help, package, capture or QC | written | targeted QC 1431/0 | 3f1459c |
| docs/friend/reconize_help_package/help/help.json | Help, package, capture or QC | written | targeted QC 1285/0 | e6fc031 |
| docs/friend/reconize_help_package/help/img/en-dark-faces-open.webp | native screenshot | written | visually checked | e6fc031 |
| docs/friend/reconize_help_package/help/img/en-light-faces-open.webp | native screenshot | written | visually checked | e6fc031 |
| docs/friend/reconize_help_package/help/img/en-light-reconize-activities.webp | native screenshot | written | visually checked | 3f1459c |
| docs/friend/reconize_help_package/help/img/en-light-reconize-attendees.webp | native screenshot | written | visually checked | e6fc031 |
| docs/friend/reconize_help_package/help/img/en-light-reconize-cctv.webp | native screenshot | written | visually checked | e6fc031 |
| docs/friend/reconize_help_package/help/img/en-light-reconize-connect.webp | native screenshot | written | visually checked | e6fc031 |
| docs/friend/reconize_help_package/help/img/en-light-reconize-dashboard.webp | native screenshot | written | visually checked | e6fc031 |
| docs/friend/reconize_help_package/help/img/en-light-reconize-event-photos.webp | native screenshot | written | visually checked | e6fc031 |
| docs/friend/reconize_help_package/help/img/en-light-reconize-history.webp | native screenshot | written | visually checked | e6fc031 |
| docs/friend/reconize_help_package/help/img/en-light-reconize-import.webp | native screenshot | written | visually checked | e6fc031 |
| docs/friend/reconize_help_package/help/img/en-light-reconize-login.webp | native screenshot | written | visually checked | e6fc031 |
| docs/friend/reconize_help_package/help/img/en-light-reconize-pdpa.webp | native screenshot | written | visually checked | e6fc031 |
| docs/friend/reconize_help_package/help/img/en-light-reconize-people.webp | native screenshot | written | visually checked | e6fc031 |
| docs/friend/reconize_help_package/help/img/en-light-reconize-privacy.webp | native screenshot | written | visually checked | e6fc031 |
| docs/friend/reconize_help_package/help/img/en-light-reconize-recognition.webp | native screenshot | written | visually checked | e6fc031 |
| docs/friend/reconize_help_package/help/img/en-light-reconize-reports.webp | native screenshot | written | visually checked | e6fc031 |
| docs/friend/reconize_help_package/help/img/en-light-reconize-settings.webp | native screenshot | written | visually checked | 3f1459c |
| docs/friend/reconize_help_package/help/img/en-light-reconize-uploads.webp | native screenshot | written | visually checked | e6fc031 |
| docs/friend/reconize_help_package/help/img/en-light-reconize-video.webp | native screenshot | written | visually checked | e6fc031 |
| docs/friend/reconize_help_package/help/img/ja-dark-faces-open.webp | native screenshot | written | visually checked | e6fc031 |
| docs/friend/reconize_help_package/help/img/ja-light-faces-open.webp | native screenshot | written | visually checked | e6fc031 |
| docs/friend/reconize_help_package/help/img/th-dark-faces-open.webp | native screenshot | written | visually checked | e6fc031 |
| docs/friend/reconize_help_package/help/img/th-light-faces-open.webp | native screenshot | written | visually checked | e6fc031 |
| docs/friend/reconize_help_package/help/img/zh-dark-faces-open.webp | native screenshot | written | visually checked | e6fc031 |
| docs/friend/reconize_help_package/help/img/zh-light-faces-open.webp | native screenshot | written | visually checked | e6fc031 |
| docs/friend/reconize_help_package/help/ja.html | Help, package, capture or QC | written | targeted QC 1431/0 | 3f1459c |
| docs/friend/reconize_help_package/help/shots.json | Help, package, capture or QC | written | targeted QC 1431/0 | 3f1459c |
| docs/friend/reconize_help_package/help/th.html | Help, package, capture or QC | written | targeted QC 1431/0 | 3f1459c |
| docs/friend/reconize_help_package/help/zh.html | Help, package, capture or QC | written | targeted QC 1431/0 | 3f1459c |
| docs/systems/agents.md | Help, package, capture or QC | written | targeted QC 1285/0 | e6fc031 |
| docs/systems/app-faces.md | Help, package, capture or QC | written | targeted QC 1285/0 | e6fc031 |
| docs/systems/app-small.md | Help, package, capture or QC | written | targeted QC 1431/0 | 3f1459c |
| handoff/tasks/help-friend-apps-1124.md | final evidence and remaining gate | verified | handoff QC passed | this checkpoint |
| main_python/hub_api_help.py | Help, package, capture or QC | written | targeted QC 1431/0 | 3f1459c |
| main_python/web/help.html | Help, package, capture or QC | written | targeted QC 1431/0 | 3f1459c |
| main_python/web/help/parts/bytask.html | Help, package, capture or QC | written | targeted QC 1431/0 | 3f1459c |
| qc/checks/check_app_help.py | Help, package, capture or QC | written | targeted QC 1431/0 | 3f1459c |
| shared/web/lang/help/ja.json | Help, package, capture or QC | written | targeted QC 1431/0 | 3f1459c |
| shared/web/lang/help/th.json | Help, package, capture or QC | written | targeted QC 1431/0 | 3f1459c |
| shared/web/lang/help/zh.json | Help, package, capture or QC | written | targeted QC 1431/0 | 3f1459c |
| tools/help_shots.py | Help, package, capture or QC | written | targeted QC 1431/0 | 3f1459c |
