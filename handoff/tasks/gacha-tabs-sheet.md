# Prize machines page in tabs + edit the Google Sheet

Owner: claude:10230525-3d21
Updated: 2026-10-23 05:35Z
Branch: claude/project-thread-s0kmlq
Last commit: (none yet)
Plan: A47-14 tabs, A47-15 sheet editing

## Goal
User 2026-10-23: "🎁 Prize machines ขอเป็น tab เพื่อให้ตั้งค่าง่ายไม่ต้องเลื่อนลงล่างอย่างเดียว
และขอให้แก้ไฟล์ใน google sheet ได้ด้วยถ้าเอาลิ้งมาใส่". Tabs on /app/gacha/; paste a Google
Sheet link and the hub reads AND writes it. No key in git; the way is config, not one route.

## Doing now
Writing main_python/gacha_sheet.py (ways: link read-only, script = Apps Script web app with a
hub-made secret, service = service-account key file in .local) + page tabs.

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

## Next
1. gacha_sheet.py + routes /api/gacha/sheet*, apps_script.gs with ops + SECRET.
2. Tabs on the page, Sheet tab with an editable grid and Thai one-time steps.
3. check_gacha_sheet (fake script server) + sabotage; full QC; PR; merge.

## Blocked
- nothing (real Google Sheet test needs the user's sheet: lab-day or user later).
