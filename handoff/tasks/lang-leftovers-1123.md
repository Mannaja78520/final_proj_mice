# lang-leftovers-1123 — wrong-language text on every page

Owner: claude (thread "Fix hub Tools page look and language mix")
Updated: 2026-11-23

## Done (PR on branch claude/project-thread-y6bwqj)
- Tools cards: generic blurbs, one cartoon icon set (default.svg for apps without image), lifted tile + icon plate on dark themes.
- mice-lang.js: now translates `alt`, the tab title, placeholders inside textarea/code, attributes set later.
- Packs: small pages (Home, Voice, Prize machines, Reconize, Photobooth, All-Jao) th/en/zh/ja filled.
- Tools: `python tools/lang_add.py batch.json` adds entries; `NODE_PATH=$(npm root -g) node tools/lang_scan/scan.js <base> out.json [pages]` scans every page x 4 languages (hub must run).

## Next (not done)
- Studio: ~330 English texts untranslated in th/zh/ja.
- Help: ~680 texts untranslated in zh/ja, ~130 Thai fragments in en (fragments split by inline <code>/<b>).
- Re-run the scan; goal: zero "thai" in en/zh/ja, zero latin-run in th/zh/ja apart from brand/technical names.

## File status
All files committed in the PR; QC quick = same failures as clean main (cloud env-only).
