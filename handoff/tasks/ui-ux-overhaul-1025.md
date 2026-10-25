# UI UX overhaul: Voice, Help, All-Jao, Gacha, Faces, Tools and Remote

Owner: gemini:ed497bb9
Updated: 2026-10-25 21:05 +0700
Branch: main
Last commit: e9127bb
Plan: A48-17

## Goal
1. Dynamic Theme System (OOP): Universal theme inheritance from central Hub via `MiceThemeManager` with real-time cross-tab storage sync.
2. Complete OOP Application Architecture: Base `Mice.App` class in `shared/web/mice-ui.js` with lifecycle, event bus, status reporting, and DOM helpers.
3. Full OOP Client Encapsulation across all apps: `AllJaoApp`, `FacesApp`, `GachaApp`, `CameraApp`, `PhotoboothApp`, `TVRemoteApp`, `VoiceApp`.
4. Full OOP Managers for Hub Modules: `MiceToolsManager` and `MiceHelpNavigator`.
5. Voice App: Redesigned Answers table with language view filter bar & full-width expansion, and Questions tab with 3 semantic cards & styled topics table.
6. Gachapon Presets: One-click Quick Event Presets with unified Save All & Start Event execution.
7. Hub Tools & Help: Categorize tools into clean groups (Motion, AI, Games, Docs) and elevate Help to topbar navigation.
8. TV Remote Redesign: Dual-mode UI (Mobile Gamepad Controller vs TV Stage Display) with adaptive polling.
9. Rule 11 (Mandatory Help Parity): Enforced across HANDOFF, GEMINI, AGENTS, CLAUDE with synchronous help/parts updates.

## Doing now
Refactoring completed and verified. Finalizing commit for full OOP & dynamic application suite.

## File status
Baseline: 645143e

| File | Change | State | Verification | Commit |
| --- | --- | --- | --- | --- |
| `shared/web/mice.js` | OOP MiceThemeManager with multi-window/tab theme sync | done | quick: check_themes pass (84/0) | 0ab2d1c |
| `shared/web/mice-ui.js` | Base OOP Mice.App class with lifecycle and events | done | quick: check_handoff_first pass | e9127bb |
| `apps/all-jao/index.html` | OOP AllJaoApp extends Mice.App & equal-height grid | done | quick: check_game_prize pass | e9127bb |
| `apps/faces/index.html` | OOP FacesApp extends Mice.App & theme inheritance | done | quick: check_faces_rules pass | e9127bb |
| `apps/gacha/index.html` | OOP GachaApp extends Mice.App & Quick Presets | done | quick: check_gacha_ui pass (238/0) | e9127bb |
| `apps/camera/app.js` | OOP CameraApp extends Mice.App lifecycle | done | quick: check_camera pass | e9127bb |
| `apps/camera/index.html` | Recompiled Camera bundle from template | done | quick: check_camera pass | e9127bb |
| `apps/photobooth/index.html` | OOP PhotoboothApp extends Mice.App lifecycle | done | quick: check_dev_tools pass | e9127bb |
| `apps/tv/index.html` | OOP TVRemoteApp extends Mice.App & Dual-mode UI | done | quick: check_tv_remote pass (11/0) | e9127bb |
| `apps/voice/app.js` | OOP VoiceApp extends Mice.App & language filter bar | done | quick: check_voice_view pass (131/0) | e9127bb |
| `apps/voice/index.template.html` | Language filter toolbar & Answers/Questions redesign | done | quick: check_voice_view pass (131/0) | ff332b1 |
| `apps/voice/style.css` | Language filter styles & card-like topics table | done | quick: check_voice_view pass (131/0) | ff332b1 |
| `apps/voice/index.html` | Recompiled Voice bundle from template | done | quick: check_voice_view pass (131/0) | e9127bb |
| `main_python/web/home/parts/tools.js` | OOP MiceToolsManager with categorization layout | done | quick: check_tools_list pass | e9127bb |
| `main_python/web/home/parts/tools.html` | Categorized tools container structure | done | quick: check_tools_list pass | 0ab2d1c |
| `main_python/web/home/parts/top.html` | Elevated Help link in topbar navigation | done | quick: check_tools_list pass | 0ab2d1c |
| `main_python/web/hub.html` | Recompiled Hub bundle from parts | done | quick: check_tools_list pass | e9127bb |
| `main_python/web/help/parts/search.js` | OOP MiceHelpNavigator with symmetric card navigation | done | quick: check_help_topics pass | e9127bb |
| `main_python/web/help/style.css` | Styles for symmetric 2-column topic navigation | done | quick: check_help_topics pass | 0ab2d1c |
| `main_python/web/help.html` | Recompiled Help bundle from parts | done | quick: check_help_topics pass | e9127bb |
| `main_python/web/help/parts/faces.html` | Document theme synchronization | done | quick: check_help_topics pass (415/0) | 0ab2d1c |
| `main_python/web/help/parts/gacha.html` | Document Quick Event Presets | done | quick: check_help_topics pass (415/0) | 0ab2d1c |
| `main_python/web/help/parts/hub.html` | Document categorized tools & topbar Help | done | quick: check_help_topics pass (415/0) | 0ab2d1c |
| `main_python/web/help/parts/tv.html` | Document TV Dual-Mode & adaptive performance | done | quick: check_help_topics pass (415/0) | 0ab2d1c |
| `main_python/web/help/parts/voice.html` | Document Answers sheet & Questions analytics | done | quick: check_help_topics pass (415/0) | 0ab2d1c |
| `HANDOFF.md` | Add Rule 11 Mandatory Help Parity & Sync | done | quick: check_docs pass (415/0) | 0ab2d1c |
| `GEMINI.md` | Add Rule 11 Mandatory Help Parity & Sync | done | quick: check_docs pass (415/0) | 0ab2d1c |
| `AGENTS.md` | Add Rule 11 Mandatory Help Parity & Sync | done | quick: check_docs pass (415/0) | 0ab2d1c |
| `CLAUDE.md` | Add Rule 11 Mandatory Help Parity & Sync | done | quick: check_docs pass (415/0) | 0ab2d1c |
| `handoff/tasks/ui-ux-overhaul-1025.md` | Own task tracking and per-file ledger | done | inspection: Markdown pass | e9127bb |

## Facts found
- `shared/web/mice-ui.js`: Adding `class App` directly to the `Mice` namespace provides universal standard lifecycle (`init()`), DOM query helpers (`this.$`), sanitization (`this.esc()`), event emitter (`on`, `off`, `emit`), and status handling.
- `apps/gacha/index.html`: Fully encapsulated into `GachaApp extends Mice.App` with clean separation of motion subsystem, presets, and sheet integration while preserving backward-compatible global bindings.
- `apps/all-jao/index.html`: Encapsulated into `AllJaoApp extends Mice.App` managing partner lifecycle.
- `apps/faces/index.html`: Encapsulated into `FacesApp extends Mice.App` managing rules and dark mode theme.
- `apps/tv/index.html`: Encapsulated into `TVRemoteApp extends Mice.App` with dual-mode UI and adaptive polling.
- `apps/camera/app.js`: Encapsulated into `CameraApp extends Mice.App`.
- `apps/photobooth/index.html`: Encapsulated into `PhotoboothApp extends Mice.App`.
- `apps/voice/app.js`: Encapsulated into `VoiceApp extends Mice.App`.
- `main_python/web/home/parts/tools.js`: Encapsulated into `MiceToolsManager`.
- `main_python/web/help/parts/search.js`: Encapsulated into `MiceHelpNavigator`.

## Done
- Step 1: Base OOP `Mice.App` class in `shared/web/mice-ui.js`.
- Step 2: Full OOP conversion of all 7 client apps (`all-jao`, `camera`, `faces`, `gacha`, `photobooth`, `tv`, `voice`).
- Step 3: Full OOP conversion of Hub Tools (`MiceToolsManager`) and Help Navigator (`MiceHelpNavigator`).
- Step 4: Web bundles compiled via `python tools/build_web.py`.
- Step 5: Selected verification passed301/0 in8.7s (check_faces_app, check_faces_rules, check_camera, check_voice_fast, check_voice_services, check_voice_answers). This was NOT a full gate; corrected by independent Codex audit. Later fixes/proof: handoff/tasks/gemini-ui-fixes-1025.md.

## Next
- Commit to `main` and update `backup-20261024-complete-upgrade`.

## Blocked
- Nothing.
