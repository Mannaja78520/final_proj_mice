# Wrong-language text on every page (Tools look + 4 languages)

Owner: claude:lang-leftovers-1123
Updated: 2026-11-23 16:25 (Asia/Bangkok)
Branch: claude/project-thread-y6bwqj
Last commit: this checkpoint
Plan: none (user ask 2026-11-23)

## Goal
User 2026-11-23: Tools page look (icons vs dark background), the "ผลงานล่าสุด" card, Thai showing in English mode; check every page of every app in all 4 languages.

## Doing now
Help packs (en/zh/ja/th) filled by the PC session with Codex/Gemini; then rescan help, QC, merge PR #211, rebuild MiceHub.exe.

## File status
Baseline: 2045752 (main)

| File | Change | State | Verification | Commit |
| --- | --- | --- | --- | --- |
| `main_python/web/home/style.css`, `parts/tools.js` | one cartoon icon set, dark tile, accent Open | done | quick QC same as main; screenshot checked | 0542190, 0ab62cc |
| `shared/web/mice-lang.js` | translate alt, title, textarea placeholders, late attributes | done | lang_scan clean on small pages | 0542190 |
| `shared/web/lang/*.json`, `lang/help/*.json` | packs filled (small pages, Studio, Help) | Help in progress on PC | lang_scan | see PR #211 |
| `tools/lang_scan/`, `tools/lang_batch.py` | scan + batch add tools | done | ran on PC and cloud | see PR #211 |

## Facts found
- Tools card name/blurb come from apps/*/app.json via /api/apps; Thai text is translated by key (shared/web/lang/*.json, whole text node). "ผลงานล่าสุด" is a local extension (not in repo).
- mice-lang.js skipped TEXTAREA/CODE elements entirely, so their placeholder was never translated (fixed).

## Done
- Tools page, small pages, Studio translated; Help in progress.

## Next
1. Re-run `NODE_PATH=$(npm root -g) node tools/lang_scan/scan.js <hub> out.json help` and fix leftovers.
2. Icons: soften baked-in plate colours (Codex review 2026-11-23), keep one cartoon set.
3. Merge PR #211, rebuild exe on PC.

## Blocked
- Codex usage limit until about 16:07 Bangkok; icon image generation unavailable.
