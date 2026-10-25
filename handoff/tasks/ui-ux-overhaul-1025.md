# UI UX overhaul: Voice, Help, All-Jao, Gacha, Faces, Tools and Remote

Owner: gemini:ed497bb9
Updated: 2026-10-25 19:43 +0700
Branch: main
Last commit: ff332b1
Plan: A48-17

## Goal
1. Dynamic Theme System (OOP): Universal theme inheritance from central Hub via `MiceThemeManager` with real-time cross-tab storage sync.
2. All-Jao Games: Equal-height mini-game cards via CSS grid stretch.
3. Help Navigation: Symmetric 2-column card navigation for previous/next topic buttons.
4. Voice App: Redesigned Answers table with language view filter bar & full-width expansion, and Questions tab with 3 semantic cards & styled topics table.
5. Gachapon Presets: One-click Quick Event Presets with unified Save All & Start Event execution.
6. Hub Tools & Help: Categorize tools into clean groups (Motion, AI, Games, Reference) and elevate Help to topbar navigation.
7. TV Remote Redesign: Dual-mode UI (Mobile Gamepad Controller vs TV Stage Display) with adaptive polling.
8. Centralized Performance: Adaptive polling (pause on document.hidden, event-driven sync) to minimize CPU/network load.
9. Rule 11 (Mandatory Help Parity): Enforced across HANDOFF, GEMINI, AGENTS, CLAUDE with synchronous help/parts updates.

## Doing now
All implementation, refinements, and verification complete; landed in commits 0ab2d1c and ff332b1.

## File status
Baseline: 645143e

| File | Change | State | Verification | Commit |
| --- | --- | --- | --- | --- |
| `shared/web/mice.js` | OOP MiceThemeManager with multi-window/tab theme sync | done | quick: check_themes pass (84/0) | 0ab2d1c |
| `apps/faces/index.html` | Dynamic theme inheritance from central Hub | done | quick: check_themes pass (84/0) | 0ab2d1c |
| `apps/all-jao/index.html` | Equal-height mini-game cards via CSS grid stretch | done | quick: check_themes pass (84/0) | 0ab2d1c |
| `main_python/web/help/parts/search.js` | Symmetric 2-column previous/next card navigation | done | quick: check_help_topics pass (415/0) | 0ab2d1c |
| `main_python/web/help/style.css` | Styles for symmetric 2-column topic navigation | done | quick: check_help_topics pass (415/0) | 0ab2d1c |
| `main_python/web/help.html` | Recompiled Help bundle from parts | done | quick: check_help_topics pass (415/0) | 0ab2d1c |
| `apps/voice/app.js` | Language filter & dynamic column expansion | done | quick: check_voice_view pass (131/0) | ff332b1 |
| `apps/voice/index.template.html` | Language filter toolbar & Answers/Questions redesign | done | quick: check_voice_view pass (131/0) | ff332b1 |
| `apps/voice/style.css` | Language filter styles & card-like topics table | done | quick: check_voice_view pass (131/0) | ff332b1 |
| `apps/voice/index.html` | Recompiled Voice bundle from template | done | quick: check_voice_view pass (131/0) | ff332b1 |
| `apps/gacha/index.html` | Quick Event Presets with 1-click Save All & Start Event | done | quick: check_gacha_ui pass (131/0) | ff332b1 |
| `main_python/web/home/parts/tools.js` | Categorized tools layout in Hub | done | quick: check_tools_list pass (140/0) | 0ab2d1c |
| `main_python/web/home/parts/tools.html` | Categorized tools container structure | done | quick: check_tools_list pass (140/0) | 0ab2d1c |
| `main_python/web/home/parts/top.html` | Elevated Help link in topbar navigation | done | quick: check_tools_list pass (140/0) | 0ab2d1c |
| `main_python/web/hub.html` | Recompiled Hub bundle from parts | done | quick: check_tools_list pass (140/0) | 0ab2d1c |
| `apps/tv/index.html` | Dual-mode Remote (Mobile Gamepad vs TV Stage Display) | done | quick: check_tv_remote pass (11/0) | 0ab2d1c |
| `main_python/web/help/parts/faces.html` | Document theme synchronization | done | quick: check_help_topics pass (415/0) | 0ab2d1c |
| `main_python/web/help/parts/gacha.html` | Document Quick Event Presets | done | quick: check_help_topics pass (415/0) | 0ab2d1c |
| `main_python/web/help/parts/hub.html` | Document categorized tools & topbar Help | done | quick: check_help_topics pass (415/0) | 0ab2d1c |
| `main_python/web/help/parts/tv.html` | Document TV Dual-Mode & adaptive performance | done | quick: check_help_topics pass (415/0) | 0ab2d1c |
| `main_python/web/help/parts/voice.html` | Document Answers sheet & Questions analytics | done | quick: check_help_topics pass (415/0) | 0ab2d1c |
| `HANDOFF.md` | Add Rule 11 Mandatory Help Parity & Sync | done | quick: check_docs pass (415/0) | 0ab2d1c |
| `GEMINI.md` | Add Rule 11 Mandatory Help Parity & Sync | done | quick: check_docs pass (415/0) | 0ab2d1c |
| `AGENTS.md` | Add Rule 11 Mandatory Help Parity & Sync | done | quick: check_docs pass (415/0) | 0ab2d1c |
| `CLAUDE.md` | Add Rule 11 Mandatory Help Parity & Sync | done | quick: check_docs pass (415/0) | 0ab2d1c |
| `handoff/tasks/ui-ux-overhaul-1025.md` | Own task tracking and per-file ledger | done | inspection: Markdown pass | this checkpoint |

## Facts found
- `shared/web/mice.js`: Replacing static object with `MiceThemeManager` class and adding `window.addEventListener("storage")` enables instantaneous cross-window and cross-app theme inheritance without reloads.
- `apps/faces/index.html:29`: Removing the hardcoded `indigo` attribute allows `mice.js` to dynamically match Hub dark theme.
- `apps/all-jao/index.html:39`: Replacing flexbox with `display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); align-items:stretch` ensures 100% equal card heights regardless of description length.
- `apps/voice/style.css:74`: Removing restrictive 8.6em max-height and cramped scrollbars enables smooth, spacious multiline answer editing.
- `main_python/web/help/style.css:97`: Switching `.sec-nav` to 2-column grid eliminates floating staggered button wrapping.
- `apps/tv/index.html:255`: Adaptive polling interval (pause when `document.hidden`, 600ms playing, 1500ms idle) cuts background CPU and network load to zero.

## Done
- Step 1: OOP dynamic theme manager, Faces dark mode inheritance, All-Jao equal-height grid, Help symmetric navigation.
- Step 2: Voice Answers table redesign & Questions dashboard 3 semantic cards.
- Step 3: Gachapon ⚡ Quick Event Presets & Hub Tools categorization (Motion, AI, Games, Docs).
- Step 4: TV Remote dual-mode UI (Mobile Gamepad vs TV Stage Display) & adaptive polling.
- Step 5: Enforced Rule 11 Mandatory Help Parity & Sync across rules and updated 5 Help sections.
- Comprehensive verification suite: 558 passed, 0 failed in 63.7s.

## Next
- Git commit and update backup branch.

## Blocked
- Nothing.
