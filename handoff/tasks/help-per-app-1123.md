# help-per-app-1123 — Help per app, dynamic in the hub, real screenshots
Owner: codex:11231744-055a
Updated: 2026-11-23 17:56 +07:00
Branch: claude/project-thread-181856
Last commit: this checkpoint
Plan: A1123-1 (system)

## Goal (user's words, 2026-11-23)
Help pictures do not match the real apps. Each app ships its OWN Help (own folder + manifest,
4 languages th/en/zh/ja, real screenshots of that app). The main hub Help is assembled
DYNAMICALLY from every installed/added app's Help: "Add app" in the hub makes its Help appear,
removing the app removes its Help. Friend apps (Reconize, Photobooth, All-Jao): NEVER edit their
repos; our side (apps/<id>/help) provides their Help; add to the friend request file that they
may ship their own help in the same format later (docs/friend/friend_requests_all_2026-11-23.md).
Replace EVERY Help picture with a real screenshot of the real app, light AND dark variant,
each matching its step text. Reply to the user in Thai.

## Design (agreed by Claude, change only with a reason in this file)
- `apps/<id>/help/help.json` manifest: title/summary per lang, group (start/use/build/wrong), order.
- `apps/<id>/help/{th,en,zh,ja}.html` = the section fragment (`<section id="<id>">`), images as
  `<img data-shot="name" alt=...>`; real files `apps/<id>/help/img/<lang>-<light|dark>-<name>.webp`.
- `apps/<id>/help/shots.json` = recipe per shot (url, clicks/evals, optional clip selector) so a
  new app brings its own recipe. Tool `tools/help_shots.py` (+ Playwright, base on
  tools/visual/shoot.js and serve_hub.py) makes all images: 4 langs x light/dark.
- Hub: route listing help of apps that are visible now (`/api/help/apps`; built from
  tools/registry.py apps + extensions.py extra apps, same visibility as the Tools list) and a
  route serving `apps/<id>/help/*`. `main_python/web/help/` template loads these at runtime into
  `<main>` and the sidebar (HELP_GROUPS in parts/topics.js) BEFORE search.js builds nav/search;
  re-render on language change; theme picks the light/dark image. Anchors `#voice`, `#studio`...
  must keep working (apps/*/app.json "help" field).
- Move parts studio, tv, camera, voice, faces, gacha, all-jao out of
  main_python/web/help/parts/ into the apps' help folders. th = old part; en/zh/ja generated once
  from shared/web/lang/help/<code>.json via tools/help_texts.py logic, then hand-checked.
  Photobooth gets a help too. Hub-wide parts (hub, modsite, accounts, firmware, ...) stay.
- Adapt QC: check_help_links, check_help_topics, check_help_groups, help_drift, docs/help_map.json.
  NEW check: every app with a help folder has 4 langs, every referenced image exists (both
  themes), and an add-app test (extension added -> its help in /api/help/apps; removed -> gone).
- Rule 11: help.html is built; edit parts + run `python tools/build_web.py`. Update docs/systems.json
  then `python tools/systems.py build`. Do not hardcode lists; one source.

## Facts found (Claude, 2026-11-23)
- App groups have insertion slots and the task index renders localized manifest summaries. The shared app visibility rule hides missing partners; documentation inside a partner installation overrides our fallback.
- main_python/main.py hub_apps already applies extension/partner visibility. The Help API reads manifest_dir (independent of the app page root), and the Help client loads the selected language before creating sidebar/search.
- Help = main_python/web/help/{index.template.html,style.css,parts/*.html,parts/topics.js,parts/search.js}
  built into main_python/web/help.html. Texts are Thai; other languages come from
  shared/web/lang/help/<code>.json keyed by Thai text (almost complete for the app parts).
- Images now: docs/shots/*.png (old, wrong) and /img/help/*.webp (cartoons, keep for by-task page).
  Dark swap rule for images: shared/web/img-dark.css (tools/make_dark_images.py).
- Screenshots tool: `python tools/visual/serve_hub.py` (prints base URL, login pw qc-test-password),
  `NODE_PATH=$(npm root -g) node tools/visual/shoot.js <base> <out>`; pages in tools/visual/pages.json.
  Theme ids midnight/daylight via localStorage mice_theme, lang via mice.lang.
- Add app: tools/add_app.py -> POST /api/extensions/add; main_python/extensions.py; manifest mice-app.json.
- Themes thread (cmsg_01R7BbYxaTb3Yv9YS3gQaaA3R9gxTvRCa7nvxb64kPivcA) may touch Help CSS: pull often.

## Rules
Follow HANDOFF.md and CLAUDE.md. Review real screenshots against the steps. Draft PR after full QC and Gemini review. Reply in Thai and report EXE rebuild status.

## Doing now
Step 3: capture real app and Hub UI in four languages and both themes, replace the screenshots and compare every view with its step.

## Done
- Step 2: eight app guides load in four languages. Edge checked all anchors and widths (390/1280 px), the task index, and the gacha technical diagram. Existing drift baseline has no new gaps.
- Step 1: real Hub HTTP handler and Edge rendered Voice at /help#voice in th/en/zh/ja, with active sidebar link and navigation. API index and system map verify. Shared fake Hub is in use by another task, so full QC is pending.
- Read handoff and workflow. Branch baseline 12474a5. Protected local EXE, prompt and dist reports are outside the task.

## Next (in order)
3. tools/help_shots.py + shots.json per app; generate all images; view them; fix text/recipes.
4. QC checks + add-app test; friend request file note; docs.
5. Full QC, draft PR, Gemini review, report to user in Thai.

## File status
| File | Change | State | Verification | Commit |
|---|---|---|---|---|
| apps/all-jao/help/en.html | added | written | Edge four-language app navigation and drift passed; image and full QC pending | this checkpoint |
| apps/all-jao/help/help.json | added | written | Edge four-language app navigation and drift passed; image and full QC pending | this checkpoint |
| apps/all-jao/help/ja.html | added | written | Edge four-language app navigation and drift passed; image and full QC pending | this checkpoint |
| apps/all-jao/help/th.html | added | written | Edge four-language app navigation and drift passed; image and full QC pending | this checkpoint |
| apps/all-jao/help/zh.html | added | written | Edge four-language app navigation and drift passed; image and full QC pending | this checkpoint |
| apps/camera/help/en.html | added | written | Edge four-language app navigation and drift passed; image and full QC pending | this checkpoint |
| apps/camera/help/help.json | added | written | Edge four-language app navigation and drift passed; image and full QC pending | this checkpoint |
| apps/camera/help/ja.html | added | written | Edge four-language app navigation and drift passed; image and full QC pending | this checkpoint |
| apps/camera/help/th.html | added | written | Edge four-language app navigation and drift passed; image and full QC pending | this checkpoint |
| apps/camera/help/zh.html | added | written | Edge four-language app navigation and drift passed; image and full QC pending | this checkpoint |
| apps/faces/help/en.html | added | written | Edge four-language app navigation and drift passed; image and full QC pending | this checkpoint |
| apps/faces/help/help.json | added | written | Edge four-language app navigation and drift passed; image and full QC pending | this checkpoint |
| apps/faces/help/ja.html | added | written | Edge four-language app navigation and drift passed; image and full QC pending | this checkpoint |
| apps/faces/help/th.html | added | written | Edge four-language app navigation and drift passed; image and full QC pending | this checkpoint |
| apps/faces/help/zh.html | added | written | Edge four-language app navigation and drift passed; image and full QC pending | this checkpoint |
| apps/gacha/help/en.html | added | written | Edge four-language app navigation and drift passed; image and full QC pending | this checkpoint |
| apps/gacha/help/help.json | added | written | Edge four-language app navigation and drift passed; image and full QC pending | this checkpoint |
| apps/gacha/help/ja.html | added | written | Edge four-language app navigation and drift passed; image and full QC pending | this checkpoint |
| apps/gacha/help/th.html | added | written | Edge four-language app navigation and drift passed; image and full QC pending | this checkpoint |
| apps/gacha/help/zh.html | added | written | Edge four-language app navigation and drift passed; image and full QC pending | this checkpoint |
| apps/photobooth/app.json | updated | written | Edge four-language app navigation and drift passed; image and full QC pending | this checkpoint |
| apps/photobooth/help/en.html | added | written | Edge four-language app navigation and drift passed; image and full QC pending | this checkpoint |
| apps/photobooth/help/help.json | added | written | Edge four-language app navigation and drift passed; image and full QC pending | this checkpoint |
| apps/photobooth/help/ja.html | added | written | Edge four-language app navigation and drift passed; image and full QC pending | this checkpoint |
| apps/photobooth/help/th.html | added | written | Edge four-language app navigation and drift passed; image and full QC pending | this checkpoint |
| apps/photobooth/help/zh.html | added | written | Edge four-language app navigation and drift passed; image and full QC pending | this checkpoint |
| apps/studio/help/en.html | added | written | Edge four-language app navigation and drift passed; image and full QC pending | this checkpoint |
| apps/studio/help/help.json | added | written | Edge four-language app navigation and drift passed; image and full QC pending | this checkpoint |
| apps/studio/help/ja.html | added | written | Edge four-language app navigation and drift passed; image and full QC pending | this checkpoint |
| apps/studio/help/th.html | added | written | Edge four-language app navigation and drift passed; image and full QC pending | this checkpoint |
| apps/studio/help/zh.html | added | written | Edge four-language app navigation and drift passed; image and full QC pending | this checkpoint |
| apps/tv/help/en.html | added | written | Edge four-language app navigation and drift passed; image and full QC pending | this checkpoint |
| apps/tv/help/help.json | added | written | Edge four-language app navigation and drift passed; image and full QC pending | this checkpoint |
| apps/tv/help/ja.html | added | written | Edge four-language app navigation and drift passed; image and full QC pending | this checkpoint |
| apps/tv/help/th.html | added | written | Edge four-language app navigation and drift passed; image and full QC pending | this checkpoint |
| apps/tv/help/zh.html | added | written | Edge four-language app navigation and drift passed; image and full QC pending | this checkpoint |
| apps/voice/help/en.html | earlier checkpoint | written | Edge four-language app navigation and drift passed; image and full QC pending | ff0a002 |
| apps/voice/help/help.json | earlier checkpoint | written | Edge four-language app navigation and drift passed; image and full QC pending | ff0a002 |
| apps/voice/help/ja.html | earlier checkpoint | written | Edge four-language app navigation and drift passed; image and full QC pending | ff0a002 |
| apps/voice/help/th.html | earlier checkpoint | written | Edge four-language app navigation and drift passed; image and full QC pending | ff0a002 |
| apps/voice/help/zh.html | earlier checkpoint | written | Edge four-language app navigation and drift passed; image and full QC pending | ff0a002 |
| docs/help_map.json | updated | written | Edge four-language app navigation and drift passed; image and full QC pending | this checkpoint |
| docs/HUB_API.md | earlier checkpoint | written | Edge four-language app navigation and drift passed; image and full QC pending | ff0a002 |
| docs/systems.json | earlier checkpoint | written | Edge four-language app navigation and drift passed; image and full QC pending | ff0a002 |
| docs/systems/agents.md | earlier checkpoint | written | Edge four-language app navigation and drift passed; image and full QC pending | ff0a002 |
| docs/systems/app-camera.md | updated | written | Edge four-language app navigation and drift passed; image and full QC pending | this checkpoint |
| docs/systems/app-faces.md | updated | written | Edge four-language app navigation and drift passed; image and full QC pending | this checkpoint |
| docs/systems/app-gacha.md | updated | written | Edge four-language app navigation and drift passed; image and full QC pending | this checkpoint |
| docs/systems/app-small.md | updated | written | Edge four-language app navigation and drift passed; image and full QC pending | this checkpoint |
| docs/systems/app-voice.md | earlier checkpoint | written | Edge four-language app navigation and drift passed; image and full QC pending | ff0a002 |
| docs/systems/hub-web.md | updated | written | Edge four-language app navigation and drift passed; image and full QC pending | this checkpoint |
| docs/systems/qc.md | earlier checkpoint | written | Edge four-language app navigation and drift passed; image and full QC pending | ff0a002 |
| docs/systems/shared-web.md | earlier checkpoint | written | Edge four-language app navigation and drift passed; image and full QC pending | ff0a002 |
| docs/systems/studio.md | updated | written | Edge four-language app navigation and drift passed; image and full QC pending | this checkpoint |
| handoff/tasks/help-per-app-1123.md | updated | doing | Edge four-language app navigation and drift passed; image and full QC pending | this checkpoint |
| main_python/api_index.json | earlier checkpoint | written | Edge four-language app navigation and drift passed; image and full QC pending | ff0a002 |
| main_python/extensions.py | earlier checkpoint | written | Edge four-language app navigation and drift passed; image and full QC pending | ff0a002 |
| main_python/hub_api_help.py | updated | written | Edge four-language app navigation and drift passed; image and full QC pending | this checkpoint |
| main_python/main.py | earlier checkpoint | written | Edge four-language app navigation and drift passed; image and full QC pending | ff0a002 |
| main_python/web/help.html | updated | written | Edge four-language app navigation and drift passed; image and full QC pending | this checkpoint |
| main_python/web/help/index.template.html | updated | written | Edge four-language app navigation and drift passed; image and full QC pending | this checkpoint |
| main_python/web/help/parts/all-jao.html | updated | removed | Edge four-language app navigation and drift passed; image and full QC pending | this checkpoint |
| main_python/web/help/parts/apps.js | updated | written | Edge four-language app navigation and drift passed; image and full QC pending | this checkpoint |
| main_python/web/help/parts/bytask.html | updated | written | Edge four-language app navigation and drift passed; image and full QC pending | this checkpoint |
| main_python/web/help/parts/camera.html | updated | removed | Edge four-language app navigation and drift passed; image and full QC pending | this checkpoint |
| main_python/web/help/parts/faces.html | updated | removed | Edge four-language app navigation and drift passed; image and full QC pending | this checkpoint |
| main_python/web/help/parts/gacha.html | updated | removed | Edge four-language app navigation and drift passed; image and full QC pending | this checkpoint |
| main_python/web/help/parts/search.js | earlier checkpoint | written | Edge four-language app navigation and drift passed; image and full QC pending | ff0a002 |
| main_python/web/help/parts/studio.html | updated | removed | Edge four-language app navigation and drift passed; image and full QC pending | this checkpoint |
| main_python/web/help/parts/topics.js | updated | written | Edge four-language app navigation and drift passed; image and full QC pending | this checkpoint |
| main_python/web/help/parts/tv.html | updated | removed | Edge four-language app navigation and drift passed; image and full QC pending | this checkpoint |
| main_python/web/help/parts/voice.html | earlier checkpoint | removed | Edge four-language app navigation and drift passed; image and full QC pending | ff0a002 |
| shared/web/lang/help/ja.json | updated | written | Edge four-language app navigation and drift passed; image and full QC pending | this checkpoint |
| shared/web/lang/help/th.json | updated | written | Edge four-language app navigation and drift passed; image and full QC pending | this checkpoint |
| shared/web/lang/help/zh.json | updated | written | Edge four-language app navigation and drift passed; image and full QC pending | this checkpoint |
| tools/help_drift.py | updated | written | Edge four-language app navigation and drift passed; image and full QC pending | this checkpoint |
| tools/registry.py | earlier checkpoint | written | Edge four-language app navigation and drift passed; image and full QC pending | ff0a002 |
| tools/web_build.json | earlier checkpoint | written | Edge four-language app navigation and drift passed; image and full QC pending | ff0a002 |
