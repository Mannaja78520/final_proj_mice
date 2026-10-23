# Prize machines tabs + Google Sheet: PC reconciliation

Owner: codex:10231359-8856
Updated: 2569-10-23 07:01Z
Branch: codex/gacha-reconcile-1023
Tree: E:/final_proj/mice/code/.staging-gacha-reconcile
Last commit: baseline 993862e (PR #75)
Plan: A47-14/15/16 done; A47-17 trial pages; A47-18 PC reconciliation/deployment

## Goal
Finish safe PC-only gacha work. Reconcile PR #70/#73/#74/#75 with actual runtime,
check whether a real Sheet is configured without exposing secrets or writing to Google,
and coordinate one final hub build with parent chat 01a16787-933e-7d81-97a1-0a3561d110b9.
Preserve Studio/Help trials until the user chooses keep/drop. A47-5 remains hardware-only.

## Doing now
Audit actual local hub and redacted config presence. Read-only HTTP/files only.
Parent codex:10231353-0401 owns QC/fake browser, URDF and eventual hub build/restart.
No QC, heavy model loads, hardware movement, external sheet calls or service changes.
Own only this task file, serialized A47-17/18 plan metadata, isolated metadata tree,
and private scratch/gacha-reconcile-1023. Human authorizes parent coordination.

## Facts found
- GitHub API 2026-10-23 confirms all four PRs merged: #70 c73488d,
  #73 e1dc35d, #74 45dac39, #75 993862e. Real root HEAD at audit start =45dac39.
- #70: gacha page tabs; gacha_sheet.py ways link/script/service; login-only sheet routes.
- #73: Voice/Reconize on Mice.Tabs; small Camera/Photobooth/All-Jao pages retained.
- #74: Studio /studio/preview.html and Help /help-preview injected through previews.json;
  #75: trial strip one line, bottom-left, mobile icon/link, close button.
- Prior PR evidence is reported evidence, not a new local gate: #70 fake sheet16 asserts,
  sabotage9/9; #73 full7834 with isolated reruns; #74 full7855 with isolated reruns;
  #75 quick5747 + check_previews. Parent must verify final combined source before deployment.
- main_python/gacha.py:44 flat rules.sheet_* defaults; save_cfg merges rules.
- main_python/gacha_sheet.py:137 secret is local; :191 key defaults to data/google_service.json;
  :262 auto order script/service/link. Do not print keys, secrets or configured Sheet IDs.
- main_python/hub_api_gacha.py:147 sheet_view may contact configured external service;
  use redacted offline config checks before any sheet route. /sheet/script can create a secret.
- SolidWorks under E:/final_proj/mice/model/gachapong is read-only and outside this scope.

## Done
- Read AGENTS, HANDOFF, coordination, CLAUDE, system headers and verification/web skills.
- Claimed task via BRIDGE under shared mutex; stale stopped Claude ownership explicitly
  transferred under human continuation request. A47-18 added; A47-17 taken, still doing.
- Created isolated metadata worktree from merged #75. Main dirty files remain untouched.
- Parent notified: no QC/build/restart competition; requested gacha/tabs/previews in final gate.

## Next
1. Audit live HTTP availability/assets and running exe paths; inspect effective gacha config
   presence only, including external overrides, dist copy and local service-key presence.
2. Update exact evidence and pending deployment instructions; close A47-17 only on evidence.
3. Send result/branch to parent so one verified build includes merged gacha/trials.

## Blocked
- Real Google read/write requires a configured Sheet and authorized Google setup/write test.
- Keep/drop for trial design is the user's choice; preserve both trial pages meanwhile.
- Actual hub build/restart/full gate reserved to parent until explicit BRIDGE release.
- A47-5 requires board/bench; no flash or physical motion authorized in this chat.
