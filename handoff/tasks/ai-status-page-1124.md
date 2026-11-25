# ai-status-page-1124 — "AI work" status page in the MICE hub
Owner: codex:11251000-b23d
Plan: system A59-2
Branch: claude/project-thread-181856
Updated: 2026-11-25T14:46:44+07:00
Last commit: a0f1a383 (release candidate on b20e09ae)

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
Run final preflight covering the failed checks and AI work/Help/translation on exact a0f1a383 with standard Windows TEMP/TMP and isolated camera peers. Start one sequential full gate only if preflight passes.

## Done
- Built AI work in Hub Tools, administrator GET, bounded handoff reader, four locales and Hub Help. Focused QC 83/0 and both admin/read-bound sabotages tripped their assertions.
- Edge at 360px verified login, Tools link, four task states, technical switch, offline last view, 15.0s refresh and the Chrome 75 DOM fallback. Eight final Help captures and their four localized headings loaded correctly. Evidence: _out/ai-status-1124/browser_check.log and verify_help_resume.log.
- Earlier Gemini design attempt returned no review. Independent Codex review confirmed the 32-file candidate's access, read bound and Help/locale coverage. Follow-up review of current 931b7264 confirmed exact translations come first, attribute writes are guarded against loops, and the release diff is 34 files.
- First serial full QC at 1d21fff: 10682 passed, 3 failed. The inherited WIP friend handoff lacked fields, and our MICE_PLAN override caused two plan failures. The AI work, camera and visual-language checks passed. Evidence: _out/ai-status-1124/full-1d21fff.log.
- Scoped candidate 7cea7e6 retained the 32 AI work paths and left both handoffs on the shared WIP branch. Preflight 208/0. Full 10652/8 after a live camera peer and visual-language failures. Isolated replay fixed camera (13/0); visual-language remained red. Evidence: _out/ai-status-1124/full-7cea7e6.log and replay-7cea7e6.log. Claims were released between runs; no other job was stopped.
- Current-main candidate ee6a7172 rebased onto b20e09ae. Regenerated common inventories, Help and API; the clean app-voice inventory removes references to absent private profiles. Candidate adds no Voice code/settings edits.
- Matched checks on b20e09ae and ee6a7172 reproduced the dynamic Thai Tools title in en/zh/ja. Main also leaked loading text. Candidate AI work 21/0, camera 13/0, systems 13/0. Evidence: _out/ai-status-1124/matched-b20e09ae.log and matched-ee6a7172.log.
- Candidate 931b7264 and WIP 3c6395ad fix dynamic Tools labels using existing locale placeholders, translate loading/network messages and keep localized Help in sync. Exact preflight PASS 509/0, including visual-language, AI work, Help, handoff, camera, systems and translations. Evidence: _out/ai-status-1124/preflight-931b7264.log.
- Full serial QC at 931b7264: 10740 passed, 9 failed in 3488.1s. AI work 21/0, camera 13/0, systems 13/0. Red: face-count connection abort, Gacha stock/jam, 3 plan probe errors from our temp path inside the checkout, and 3 untranslated Voice fallback assertions. Exact evidence: _out/ai-status-1124/full-931b7264.log. The source tree still matches the candidate. Shared QC released.

- Normal-temp comparison: candidate 272/3, current main 269/6. Face count, Gacha stock/jam, camera and plan integrity all passed. Both trees reproduce the three Voice fallback failures. Main also has the three Tools-title failures fixed on the candidate. Logs: _out/ai-status-1124/normal-temp-replay-931b7264.log and normal-temp-baseline-b20e09ae.log. Shared QC released.

- Translated the matched Voice fallback and its related status text in th/ja/zh; Hub Help explains the status consistently in four languages. Exact eight-file delta, no Voice app or friend code changes. Build/diff passed on a0f1a383 and WIP d7caafd0.

## Next
After a green full gate, record the final scoped review and publish, merge, build and restart. If candidate QC is green, record final review, publish a scoped PR, merge under standing approval, then rebuild and restart.

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
| main_python/web/help/parts/hub.html | Localize AI work and fallback status / Help | Built | Build and diff pass; focused QC pending | a0f1a383 |
| main_python/web/help/shots.json | Planned AI work integration | Built | parser and syntax checks only | 64d425f |
| main_python/web/help.html | Localize AI work and fallback status / Help | Built | Build and diff pass; focused QC pending | a0f1a383 |
| docs/systems.json | Planned AI work integration | Built | parser and syntax checks only | 64d425f |
| docs/systems/hub-apps.md | Planned AI work integration | Built | parser and syntax checks only | 64d425f |
| qc/checks/check_ai_status.py | Planned AI work integration | Built | focused QC and native text check | b0b4e9b |
| shared/web/lang/en.json | Localize AI work and Tools labels / Help | Built | Focused preflight passed | 931b7264 |
| shared/web/lang/th.json | Localize AI work and fallback status / Help | Built | Build and diff pass; focused QC pending | a0f1a383 |
| shared/web/lang/ja.json | Localize AI work and fallback status / Help | Built | Build and diff pass; focused QC pending | a0f1a383 |
| shared/web/lang/zh.json | Localize AI work and fallback status / Help | Built | Build and diff pass; focused QC pending | a0f1a383 |
| shared/web/lang/help/en.json | Localize AI work and fallback status / Help | Built | Build and diff pass; focused QC pending | a0f1a383 |
| shared/web/lang/help/ja.json | Localize AI work and fallback status / Help | Built | Build and diff pass; focused QC pending | a0f1a383 |
| shared/web/lang/help/zh.json | Localize AI work and fallback status / Help | Built | Build and diff pass; focused QC pending | a0f1a383 |
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
| docs/systems/agents.md | Regenerate candidate inventory | Staged in candidate | Generated; candidate gate pending | 7cea7e6 |
| docs/systems/qc.md | Generated check inventory | Built | not run | 64d425f |
| docs/systems/hub-web.md | Generated inventory for Help images | Built | Diff lists exactly eight new captures | 777a439 |

| docs/systems/app-voice.md | Regenerate clean inventory after current-main sync | Generated | Exact generated diff; QC pending | ee6a7172 |

| shared/web/mice-lang.js | Reuse locale placeholders for dynamic tool labels | Built | Visual-language preflight passed | 931b7264 |

## Blocked
The reproduced blockers have scoped fixes or a corrected fixture. Full QC is still required for merge, build and restart.

## Result
(Codex: PR link, screenshot paths, what you verified; report in Thai)
