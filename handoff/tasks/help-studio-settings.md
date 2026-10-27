# Help groups, Settings without password, Studio panels

Owner: claude:10230525-3d21
Updated: 2026-10-27 13:26 +0000
Branch: claude/project-thread-s0kmlq
Last commit: this checkpoint
Plan: A49-1 Help groups, A49-2 Settings split, A49-3 Studio panels

## Goal
User 2026-10-23 06:37Z: "help ดีแล้วแต่ทำ group ให้หน่อย ... โชว์ได้หรือเก็บได้ตาม group เผื่อมีแอพ
และอย่างอื่นเพิ่มในอนาคตและขอมีปุ่มถัดไป (next) preverse ... ส่วน studio เอามันกลับขึ้นไปในพื้นที่ของ
ตัวเองอยู่ด้านบนเหมือนเดิมแต่ขอมีรูปแบบนี้ ... สามารถปิดเปิดรูปได้หรือลากออกไปด้านนอก ... ให้เป็น editable
พวก ช่องอื่นๆ ด้วยและ setting ขอให้มีแบบไม่ใส่รหัสสำหรับ setting ที่ไม่ซีเรียสกับหุ่นจริง ใส่รหัสกับที่ซีเรียสจริงๆ"

## Doing now
A49-2 Settings split next (Studio Setup tab): data file of cards that open without a login.

## File status
Baseline: origin/main 023c644

| File | Change | State | Verification | Commit |
| --- | --- | --- | --- | --- |
| `main_python/web/help/parts/topics.js` | new: HELP_GROUPS draws the nav, groups open/close, remembered | done | check_help_groups (browser) | this checkpoint |
| `main_python/web/help/index.template.html` | nav is now `<nav id="helpNav">` filled by topics.js | done | check_help_topics, check_help_groups | this checkpoint |
| `main_python/web/help/style.css` | group buttons, shut groups, phone rows | done | quick browser | this checkpoint |
| `main_python/web/help.html` | rebuilt | done | check_build_web | this checkpoint |
| `tools/web_build.json` | help js = topics.js + search.js | done | build | this checkpoint |
| `qc/checks/check_help_groups.py` | new check | done | sabotage pending | this checkpoint |
| `main_python/web/previews/*` | Help trial dropped (now real) | done | check_previews | this checkpoint |

## Facts found
- main already had one topic at a time + Previous/Next (help/parts/search.js MiceHelpNavigator, A48-17,
  class `pv-off`, `.sec-nav`); A49-1 adds only the groups. search.js reads `nav a[href^='#']` at
  start, so topics.js must run first (web_build.json order).
- Plan ids A47-18..20 were taken by other agents while this branch was unpushed: use A49-*.
- Studio login gate: app_parts/notices.js:42 showTab sets renderWhich="login" when !currentUser,
  hiding every robot/setup card. Open-without-login candidates: Model/Clothes, Build from URDF, Rig
  setup, Saving, Move setup to another PC (their APIs are NEVER_GATED in hub_auth).
- QC browser trap: a hash link's hashchange runs after location.hash changes; wait for the page.
  Setting iframe src that differs only in #part does not reload (no onload).

## Done
- A49-1 Help groups: full QC 8752 pass; failing on main too (not ours, verified in a clean origin/main
  worktree 2026-10-27): check_race_guards "abandoned clock" (2 asserts) and check_responsive /app/tv/ at
  320px (#btnModeTech 42px too wide). Flaky in crowd, green alone: check_safe_motion, check_loop_return.

## Next
1. Full QC, PR, merge A49-1. 2. A49-2 settings split (data file of open cards). 3. A49-3 Studio panels.

## Blocked
- nothing
