# Installable theme packs (Cloudy, Cream, Aurora)

Owner: claude:themes-1123
Updated: 2026-11-23
Branch: claude/project-thread-3g8wzg
Last commit: this checkpoint
Plan: none (user asked in thread 2026-11-23)

## Goal
"Themes like a VS Code extension: install, then press Use. A cute Cloudy theme, another pretty one, and the cream look of the Help page. Pictures should match: dark theme = dark pictures, light = light."

## Doing now
QC run of themes/contrast/packs checks; then PR, then Codex + Gemini look review with screenshots.

## File status
Baseline: 363e810

| File | Change | State | Verification | Commit |
| --- | --- | --- | --- | --- |
| `main_python/theme_packs.py` | pack validate/install/remove/css | done | check_theme_packs 17 pass, sabotage proven (quick) | this checkpoint |
| `main_python/hub_api_themes.py`, `main.py`, `hub_auth.py` | /api/themes, /themes/<id>/<file>, packs appended to /mice.css | done | hub run + curl + Playwright screenshot | this checkpoint |
| `shared/web/themes/{cloudy,cream,aurora}/` | built-in packs + svg art | done | contrast measured (all >=5:1) | this checkpoint |
| `shared/web/mice.js`, `themes.css` | `--theme-mode`, `data-mode` on html | done | screenshot | this checkpoint |
| `shared/web/mice-theme-art.js`, `mice-ui.js` | dark twin `name-dark.webp` + pack picture swap | done | not browser-QC'd on real images (no dark twins exist yet) | this checkpoint |
| `main_python/web/home/parts/{themes.js,settings.*}`, `style.css`, `hub.html` | Themes gallery in Settings | done | screenshot | this checkpoint |
| `qc/checks/check_theme_packs.py`, `check_themes.py`, `check_theme_contrast.py` | new + updated | see Done | quick | this checkpoint |
| `shared/web/lang/*.json`, `lang/help/*.json`, `web/help/parts/hub.html`, `help.html` | 4-language text | done | lang.py | this checkpoint |

## Facts found
- shared/web/mice.js ThemeManager.list() discovers themes from CSS rules; packs are one extra CSS block each, so every page/app finds them with no list.
- mice.css+mice.js go into board flash (gen_tables.py); packs are hub-only on purpose (mice_nong flash is tight).
- Dark picture convention: `/img/<name>.dark.<ext>`; the Tools-page thread (PR #211) can drop dark twins in and they switch by themselves.
- Pack format: docs in main_python/theme_packs.py header.

## Done
See PR.

## Next
1. Codex (gpt-6.2-sol medium) + Gemini 4 look review with screenshots.
2. Exe rebuild: ask user (another thread owns builds).

## Blocked
- nothing
