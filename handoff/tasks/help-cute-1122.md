# help-cute-1122 — Hub header, language switch, cute pictures, Help in the Tri-U look
Owner: claude:help-cute
Updated: 2026-11-22 15:00
Branch: claude/help-cute-1122
Last commit: bf3232e
Plan: none (user ask 2026-11-22)

## Goal
Language switch recognisable and top-right in every app; cute pictures (Codex) in Help and app icons; Help in the Tri-U look.


User asks: (1) language switch recognisable + same place in every app, Home layout less odd;
(2) pictures for hard parts in Help; (3) Help looks like the Tri-U project, cute GPT-made drawings;
(4) app icons cute too.

## Doing now
Waiting for Codex image batches (app icons, 8 Help scenes) then `python tools/pack_images.py <dir>`.

## Done
- Language pill (globe + own-script name) in `.topbar-end`, top-right on every page (mice-ui.js, mice-lang.js, mice.css)
- Home head: mascot, actions on own row
- `/img/` route, `image` field in app.json -> tools.js draws it; tools/pack_images.py
- Help: ivory/burgundy theme (default light only), hero mouse, "hard parts in pictures" block (bytask.html) + th/zh/ja captions

## Next
Remaining images, QC (check_language, help drift, page_frame, board_frame), PR, rebuild MiceHub.exe (backup old to .local\backup).

## Facts found
- Codex model gpt-6.2-sol is refused on this ChatGPT account; the default gpt-6.1-sol in ~/.codex/config.toml works with built-in image generation (codex-cli 0.165.0).

## File status
| File | Change | State | Verification | Commit |
|---|---|---|---|---|
| shared/web/mice-lang.js, mice-ui.js, mice.css | language pill, corner | done | screenshot only | uncommitted |
| main_python/main.py, tools/registry.py, extensions.py, hub_api_*.py | /img route, image field | done | screenshot only | uncommitted |
| main_python/web/home/*, help/* | header, icons, Help look | done | screenshot only | uncommitted |
| shared/web/img/*, tools/pack_images.py | pictures | partial | not run | uncommitted |
| shared/web/lang/help/{th,zh,ja}.json | captions | done | not run | uncommitted |
