# Latest results entry and Nong Studio motion+audio library
Owner: codex:results-1105-01a1891f
Updated: 2026-11-05T03:29:10.082473+07:00
Branch: isolated .staging/latest-results-1105; live bookkeeping only
Last commit: this checkpoint
Plan: A56-1

## Goal
User2026-11-05: expose latest/best results on a simple front page across tasks; open current6cheer outputs in Nong Studio WITH matching originalaudio and motion. Modify Studio as needed; no new RL training or autonomous robot motion. Stable results catalog/Home app + desktop shortcut; Studio library/project+audio load/playback/save with unsaved-work protection. Isolated staging latest-results-1105; preserve unrelated dirty source and other owners.

## Doing now
Studio implementation and catalog6 complete in isolated stage; five review issues patched. Focused browser+compatibility64/0 after fixes. Capturing mutation proof (prior session output lost), then actual6 bundle integration, final review, quick/full QC, explicit-file promotion, Home registration and Desktop shortcut. No hardware/training.

## File status
| File | Change | State | Verification | Commit |
| --- | --- | --- | --- | --- |
| nong/main_python_set_nong/web/app_parts/project_library.js | motion/music library or generated parity | staged | focused64/0; mutation/re-review pending | uncommitted |
| nong/main_python_set_nong/web/app_parts/sequence_audio.js | motion/music library or generated parity | staged | focused64/0; mutation/re-review pending | uncommitted |
| nong/main_python_set_nong/web/app_parts/project_save_load.js | motion/music library or generated parity | staged | focused64/0; mutation/re-review pending | uncommitted |
| nong/main_python_set_nong/web/app_parts/timeline.js | motion/music library or generated parity | staged | focused64/0; mutation/re-review pending | uncommitted |
| nong/main_python_set_nong/web/app_parts/main_loop.js | motion/music library or generated parity | staged | focused64/0; mutation/re-review pending | uncommitted |
| nong/main_python_set_nong/web/app_parts/boot.js | motion/music library or generated parity | staged | focused64/0; mutation/re-review pending | uncommitted |
| nong/main_python_set_nong/web/html_parts/header.html | motion/music library or generated parity | staged | focused64/0; mutation/re-review pending | uncommitted |
| nong/main_python_set_nong/web/html_parts/project_library.html | motion/music library or generated parity | staged | focused64/0; mutation/re-review pending | uncommitted |
| nong/main_python_set_nong/web/index.template.html | motion/music library or generated parity | staged | focused64/0; mutation/re-review pending | uncommitted |
| tools/web_build.json | motion/music library or generated parity | staged | focused64/0; mutation/re-review pending | uncommitted |
| main_python/web/help/parts/studio.html | motion/music library or generated parity | staged | focused64/0; mutation/re-review pending | uncommitted |
| docs/systems.json | motion/music library or generated parity | staged | focused64/0; mutation/re-review pending | uncommitted |
| docs/systems/studio.md | motion/music library or generated parity | staged | focused64/0; mutation/re-review pending | uncommitted |
| qc/checks/check_studio_library_audio.py | motion/music library or generated parity | staged | focused64/0; mutation/re-review pending | uncommitted |
| AGENTS.md | motion/music library or generated parity | staged | focused64/0; mutation/re-review pending | uncommitted |
| nong/main_python_set_nong/web/app_parts/sliders.js | motion/music library or generated parity | staged | focused64/0; mutation/re-review pending | uncommitted |
| nong/main_python_set_nong/web/app_parts/checked_motion.js | motion/music library or generated parity | staged | focused64/0; mutation/re-review pending | uncommitted |
| nong/main_python_set_nong/web/app.js | motion/music library or generated parity | staged | focused64/0; mutation/re-review pending | uncommitted |
| nong/main_python_set_nong/web/index.html | motion/music library or generated parity | staged | focused64/0; mutation/re-review pending | uncommitted |
| nong/main_python_set_nong/web/style.css | motion/music library or generated parity | staged | focused64/0; mutation/re-review pending | uncommitted |
| main_python/web/help.html | motion/music library or generated parity | staged | focused64/0; mutation/re-review pending | uncommitted |

## Facts found
Existing Extensions installs app folders without root code change and Home draws them. Hub8642 is not running. Entry main_python/main.py; EXE extension store dist/extensions.json vs source main_python/extensions.json. loadProject currently ignores sourceAudioAsset metadata, so audio/timeline feature is needed. Current full6R4 deliverable is available with known pose limitations; do not retrain. Other owner promoted Voice/Studio fixes through Nov2; preserve them and do not start Voice for viewing output.

## Done
Built sibling latest-results app and 6 portable original-motion+embedded-song files. Studio library/media clock/save/draft/preview isolation and Help staged. 64 focused assertions pass after five review fixes. Not promoted/installed yet.

## Next
Implement/review/verify/land latest catalog+Studio audio library, exactfileledger, Help parity, tests dirtycancel/missingaudio/clock/pause/seek/loop/save-reopen/no commands. Required mutation/QC/review/promotion. Add stable Home/desktop entry and future delivery guidance.

## Blocked
None.
