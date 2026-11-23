# help-per-app-1123 — Help per app, dynamic in the hub, real screenshots
Owner: codex:11231744-055a
Updated: 2026-11-23 17:45 +0700
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

## Rules (CLAUDE.md, all binding)
Read HANDOFF.md. Update THIS file + push WIP commit around EVERY step. QC: `python qc/run_qc.py --quiet <checks>`,
full QC once before merge. Never edit friend repos (Face_Regonize, All-Jao-Games, Photobooth). No keys/real data in repo.
Look at every screenshot yourself and compare with the step text. Have Gemini 4 review pictures vs text (GPT+Gemini reviews are leads, verify).
PR as draft from this branch; merge own PR when QC green (standing approval cmsg_01R7BbYxaTb3Yv9YS3gQaaA3XEQcQQyoUgXwMT6wXgfeYv). Tell the user a MiceHub.exe rebuild is needed.

## Doing now
Step 1: establish isolated staging, then connect the installed-app registry, Hub routes, and Help loader. Prove Voice end to end in four languages.

## Done
- Read handoff and workflow. Branch baseline 12474a5. Protected local EXE, prompt and dist reports are outside the task.

## Next (in order)
1. Registry + hub routes + loader in help template (one app, voice, end to end, 4 langs).
2. Move the other app parts; manifests; topics.js sidebar from data.
3. tools/help_shots.py + shots.json per app; generate all images; view them; fix text/recipes.
4. QC checks + add-app test; friend request file note; docs.
5. Full QC, draft PR, Gemini review, report to user in Thai.

## File status
| File | Change | State | Verification | Commit |
|---|---|---|---|---|
| handoff/tasks/help-per-app-1123.md | WIP progress | doing | baseline reconciled | this checkpoint |
