# Prize machines page in tabs + edit the Google Sheet

Owner: claude:10230525-3d21
Updated: 2026-10-23 06:05Z
Branch: claude/project-thread-s0kmlq
Last commit: (none yet)
Plan: A47-14 tabs, A47-15 sheet editing

## Goal
User 2026-10-23: "🎁 Prize machines ขอเป็น tab เพื่อให้ตั้งค่าง่ายไม่ต้องเลื่อนลงล่างอย่างเดียว
และขอให้แก้ไฟล์ใน google sheet ได้ด้วยถ้าเอาลิ้งมาใส่". Tabs on /app/gacha/; paste a Google
Sheet link and the hub reads AND writes it. No key in git; the way is config, not one route.

## Doing now
Second full QC after adding shared Mice.Tabs (mice-ui.js + .tabbed in mice.css), then merge PR #70.

## Facts found
- apps/gacha/index.html: one long page, 11 cards; all JS inline; Mice.Api for every call.
- shared/web/mice.css:162-186 `.tabs` / `.tab` / `.tab.on` are the shared tab look (Voice uses them).
- main_python/gacha.py:40 rules cfg is flat keys (sheet_items_csv, sheet_people_csv,
  sheet_write_url); cfg() merges nested dicts ONE level (c[k].update), so keep rules keys flat.
- gacha.py:216 `_post` returned only the HTTP status: the script's {ok:false} was ignored.
- gacha.py:222 pull_rules reads two published-CSV links; push_rules POSTs {kind:"rules"}.
- hub_api_gacha.py:186 GET /api/gacha hides sheet_write_url; routes are one if-chain.
- hub_auth.py:95 gated paths list for /api/gacha/*: a new route must be added there.
- qc/checks/check_gacha.py:172 tests pull by replacing g.fetch.

## Done
- plan rows A47-14, A47-15 added (doing).
- main_python/gacha_sheet.py: ways link (gviz CSV, read only) / script (apps/gacha/sheet_script.gs,
  hub secret in .local/gacha/sheet_secret.txt) / service (JWT RS256 via cryptography, Sheets v4,
  key .local/gacha/google_service.json); auto = script, service, link. docs/gacha/apps_script.gs removed.
- gacha.py: pull/push through the way; sheet_auto_push, sheet_log (background `_sheet_soon`);
  save_cfg merges `rules`. Routes /api/gacha/sheet, /sheet/read, /sheet/write, /sheet/script (gated in hub_auth).
- apps/gacha/index.html: 8 tabs from TABS (#hash kept), Google Sheet tab with Thai steps + tab editor.
- check_gacha_sheet 16 asserts; sabotage 9/9 caught. Browser look 1280/390: no sideways scroll, no JS errors.

## Next
1. Full QC, PR, merge; delete this file in the merging PR.
2. PC: rebuild MiceHub.exe (spec); user does the 5 Thai steps once with a real sheet (not tested
   against real Google yet: only fakes).

## Blocked
- nothing (real Google Sheet test needs the user's sheet: lab-day or user later).

## Widened ask (user 2026-10-23 05:38Z, 05:43Z)
- Tabs like Face_Regonize on every app page except Studio; Voice first after Prize machines
  (settings + each answer in tabs after login). Then TRIAL pages next to the real ones:
  Studio with the new tabs, Help split by topic (separate preview links, nothing replaced).
- Face_Regonize (read only): frontend/src/components/Layout.tsx = left sidebar NAV list,
  one page per section; components/ui.tsx:122 `Tabs` = pill row for filters.
- Shared part: Mice.Tabs (shared/web/mice-ui.js) + `.tabbed` (shared/web/mice.css), held by
  check_mice_tabs (browser, wide = beside, phone = above; sabotage 3/3). mice_nong flash 82.9% after.
- Full QC #1 (before Mice.Tabs): 7815 pass; only the known receipt refusal (qc_chain_proj.json
  rewrite) + 5 crowd flakes (modsite_*, studio_peer) that pass alone.
