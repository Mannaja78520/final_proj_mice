# ai-status-page-1124 — "AI work" status page in the MICE hub
Owner: codex:11251000-b23d
Plan: system A59-2
Branch: claude/project-thread-181856
Updated: 2026-11-25T11:11:48+07:00
Last commit: 1d21fff (first full-QC input)

## User ask (Thai, 2026-11-24)
cmsg_01R7BbYxaTb3Yv9YS3gQaaA3LaPHxqrTy1gy5i5h9CNTes: "Is there a place to see which GPT is working and how far it has got?"
cmsg_01R7BbYxaTb3Yv9YS3gQaaA34v2d2dJ3DAzLRRVi6YfuDN: "Can it be shown in the app?"

## Goal
A page in the MICE hub (Tools/admin area, a card in the Tools list like other apps or a Home tab; follow docs/web_style.md,
shared/web/mice-ui.js parts, themes, designer-first: plain words, technical detail behind the technical switch) that shows,
live, every AI task: which AI/model (Codex, Gemini, Claude; from the task's `Owner:` line), task name, "Doing now",
last update time (from the file/git, shown as "x minutes ago"), state (working / done / blocked / stale: no update for N hours),
Last commit + branch, link-free plain text. Source = handoff/tasks/*.md + HANDOFF.md (read-only, parsed by a small OOP module,
e.g. main_python/ai_status.py + route in a hub_api_*.py; no hardcoded task list: a new task file appears by itself).
Auto-refresh every ~15 s (light client for Android TV Chrome 75), works on a phone, 4 languages (shared/web/lang/<code>.json),
Help updated in all 4 languages with a real screenshot (apps/<id>/help format from PR #233 if it is an app; else hub Help part), Rule 11.
Handle odd files (missing fields, huge files: read only the head sections, cap size), never expose secrets; admin-only if the
hub has an access tier for Tools.
Also show the running Codex/Claude work if cheap: parse nothing else; do NOT shell out to read logs.

## Rules
CLAUDE.md applies (read HANDOFF.md, update this file + WIP push after every step). New QC check (parser on odd/empty/huge files,
route returns the list, designer-first words), sabotage-prove it. Full QC once; draft PR from branch claude/project-thread-181856;
merge when green or equal to main's known env failures (standing approval cmsg_01R7BbYxaTb3Yv9YS3gQaaA3XEQcQQyoUgXwMT6wXgfeYv);
then rebuild MiceHub.exe from a clean main worktree on the PC (standing approvals cmsg_01R7BbYxaTb3Yv9YS3gQaaA39kL7igdPaE1F66ZxWq6meq,
cmsg_01R7BbYxaTb3Yv9YS3gQaaA3GFKFwe31L9cSDhiS4Mbs2z), restart the hub and leave it running. Do not edit friend repos.

## Doing now
Prepare an isolated release candidate from current main with only this task's feature files. Regenerate the task inventory. Preserve both WIP task files on the shared branch.

## Done
- Read HANDOFF.md, CLAUDE.md, the task and shared coordination rules.
- Pulled the shared branch at d7cd8b7. Worktree started clean and detached because the named branch is checked out by the friend Help job.

- Registered A59-2 in the real system plan and claimed exact files in the shared bridge. The friend job owns separate paths.
- Pushed initial checkpoint cbfb06a after rebasing concurrent work.

- The Gemini design panel returned no review after a CLI output redirection failure. No approval recorded.
- Built the Tools page, administrator route, reader, four language packs and Hub Help. Parser, linked checkout resolution and plain wording passed direct checks. JS and Python parsed successfully.

- Targeted QC 83/0. Administrator access and read-bound sabotages each tripped the intended assertion. The first read-bound mutation left the bounded stream read intact, so it was corrected and rerun.
- Edge at 360px verified login, Tools link, four state rows, technical toggle, offline last view and 15.0 s refresh. Initial screenshots revealed literal question marks from PowerShell redirection. Rewrote translations with a UTF-8 source file, added native-script assertions and fixed heading spacing.

- Native text and the shared Chrome 75 DOM fallback passed the second Edge run. Review also confirmed the admin gate and bounded parser. Fixed a shared-header startup race by using one language script loader.

- Recovered eight final Help captures. All eight match the previous browser capture exports byte for byte. The previous contextual check recorded English dark mode only.

- Checkpoint 777a439 pushed after pull --rebase. Current origin/main fc39932 is an ancestor.
- Contextual Hub Help returned 8/8 localized headings and matching light/dark illustrations in Edge with the fake Hub. Evidence: _out/ai-status-1124/verify_help_resume.log.

- Serial full QC at 1d21fff exited 1 after 4021.6s: 10682 passed, 3 failed. AI work 21/0, PC camera 13/0, visual language 165/0. Evidence: _out/ai-status-1124/full-1d21fff.log and .done.json.
- The inherited friend handoff lacks Branch and Plan. Our top-level MICE_PLAN override caused the packing-list crash and canonical plan-path failure. No feature assertion failed. Shared QC driver released.

## Next
Verify the scoped diff, claim free QC driver and rerun the full serial gate with the default plan path.

## Facts found
- main_python/hub_api_apps.py:50 supplies the registry-driven Tools list. A manifest in apps/ adds a tile.
- main_python/main.py:2444 and main_python/hub_auth.py:574 expose session identity and the administrator role.
- main_python/main.py:79 resolves source and frozen installs separately. Use the writable Hub DATA root for live task files.
- main_python/web/help/shots.json and tools/help_shots.py define browser-captured Hub Help images.

## File status
| File | Change | State | Verification | Commit |
| --- | --- | --- | --- | --- |
| handoff/tasks/ai-status-page-1124.md | Take task and record branch baseline | In progress | git diff --check | this checkpoint |

| main_python/ai_status.py | Planned AI work integration | Built | focused QC and native text check | b0b4e9b |
| main_python/hub_api_apps.py | Planned AI work integration | Built | parser and syntax checks only | 64d425f |
| apps/ai-status/app.json | Planned AI work integration | Built | parser and syntax checks only | 64d425f |
| apps/ai-status/index.html | Planned AI work integration | Built | focused QC and native text check | d7bb1ec |
| apps/ai-status/status.js | Planned AI work integration | Built | focused QC and native text check | b0b4e9b |
| main_python/web/help/parts/hub.html | Planned AI work integration | Built | focused QC and native text check | b0b4e9b |
| main_python/web/help/shots.json | Planned AI work integration | Built | parser and syntax checks only | 64d425f |
| main_python/web/help.html | Planned AI work integration | Built | focused QC and native text check | b0b4e9b |
| docs/systems.json | Planned AI work integration | Built | parser and syntax checks only | 64d425f |
| docs/systems/hub-apps.md | Planned AI work integration | Built | parser and syntax checks only | 64d425f |
| qc/checks/check_ai_status.py | Planned AI work integration | Built | focused QC and native text check | b0b4e9b |
| shared/web/lang/en.json | Planned AI work integration | Built | focused QC and native text check | b0b4e9b |
| shared/web/lang/th.json | Planned AI work integration | Built | focused QC and native text check | b0b4e9b |
| shared/web/lang/ja.json | Planned AI work integration | Built | focused QC and native text check | b0b4e9b |
| shared/web/lang/zh.json | Planned AI work integration | Built | focused QC and native text check | b0b4e9b |
| shared/web/lang/help/en.json | Planned AI work integration | Built | focused QC and native text check | b0b4e9b |
| shared/web/lang/help/ja.json | Planned AI work integration | Built | focused QC and native text check | b0b4e9b |
| shared/web/lang/help/zh.json | Planned AI work integration | Built | focused QC and native text check | b0b4e9b |
| main_python/web/help/img/en-light-hub-ai-status.webp | Browser capture | Verified | Edge contextual Help and byte match to export | 777a439 |
| main_python/web/help/img/en-dark-hub-ai-status.webp | Browser capture | Verified | Edge contextual Help and byte match to export | 777a439 |
| main_python/web/help/img/th-light-hub-ai-status.webp | Browser capture | Verified | Edge contextual Help and byte match to export | 777a439 |
| main_python/web/help/img/th-dark-hub-ai-status.webp | Browser capture | Verified | Edge contextual Help and byte match to export | 777a439 |
| main_python/web/help/img/ja-light-hub-ai-status.webp | Browser capture | Verified | Edge contextual Help and byte match to export | 777a439 |
| main_python/web/help/img/ja-dark-hub-ai-status.webp | Browser capture | Verified | Edge contextual Help and byte match to export | 777a439 |
| main_python/web/help/img/zh-light-hub-ai-status.webp | Browser capture | Verified | Edge contextual Help and byte match to export | 777a439 |
| main_python/web/help/img/zh-dark-hub-ai-status.webp | Browser capture | Verified | Edge contextual Help and byte match to export | 777a439 |
| config/ai_status.json | AI work config or generated API documentation | Built | parser and syntax checks only | 64d425f |
| main_python/api_index.json | AI work config or generated API documentation | Built | parser and syntax checks only | 64d425f |
| docs/HUB_API.md | AI work config or generated API documentation | Built | parser and syntax checks only | 64d425f |
| docs/systems/agents.md | Generated handoff file inventory | Built | not run | 64d425f |
| docs/systems/qc.md | Generated check inventory | Built | not run | 64d425f |
| docs/systems/hub-web.md | Generated inventory for Help images | Built | Diff lists exactly eight new captures | 777a439 |

## Blocked
Release gate pending. Shared QC, integration, build and restart are unclaimed.

## Result
(Codex: PR link, screenshot paths, what you verified; report in Thai)
