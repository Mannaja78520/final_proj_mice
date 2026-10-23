# Prize machines tabs + Google Sheet: PC reconciliation

Owner: codex:10231359-8856
Updated: 2026-10-23 07:04Z
Branch: codex/gacha-reconcile-1023
Tree: E:/final_proj/mice/code/.staging-gacha-reconcile
Last commit: f83bfad (pre-audit checkpoint); source baseline 993862e
Plan: A47-14/15/16 done; A47-17 trial pages; A47-18 PC reconciliation/deployment

## Goal
Finish safe PC-only gacha work. Reconcile PR #70/#73/#74/#75 with actual runtime,
check whether a real Sheet is configured without exposing secrets or writing to Google,
and coordinate one final hub build with parent chat 01a16787-933e-7d81-97a1-0a3561d110b9.
Preserve Studio/Help trials until the user chooses keep/drop. A47-5 remains hardware-only.

## Doing now
Reconcile stale A47-17 status using live preview evidence, then hand A47-18 final
combined deployment to parent. Parent holds all QC/fake browser/build/restart resources.
No source edits required: all requested gacha/tabs/trial implementation is already merged.

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

## Runtime audit (2026-10-23; actual PC, not a fake gate)
- Evidence: real root scratch/gacha-reconcile-1023/runtime-audit.json (redacted).
- Actual exe dist/MiceHub.exe (PIDs9080/33336), no MICE_GACHA_CONFIG/DATA overrides.
  /api/version HTTP200, built 2026-10-23 13:25, stale:false. A stale:false response alone
  does not prove the latest assets: root is #74 while parent source includes #75.
- /app/gacha/, /app/voice/app.js and /mice-ui.js HTTP200; SHA256 matches #75 baseline.
- /studio/preview.html and /help-preview HTTP200; all registered files injected and
  data-real links present. All10 preview/page asset requests HTTP200.
- /studio/ and /help match actual root page text exactly; neither has trial injections.
- Live trial_bar.css=505B and trial_bar.js=624B match #74 root; both differ from #75.
  Parent includes #75 (993862e): final build/deploy must serve its mobile/close fix.
- Effective /api/gacha rules: no Sheet link or CSV links, machines0. Offline config:
  no script URL, key override, service key or secret at root/dist/main_python local paths.
  No external Sheet call, secret generation, real Google write or hardware command.
- All checks here are read-only HTTP/content/config assertions. No QC/browser gate,
  new screenshot, model load, service restart or build was performed by this chat.

## Next
1. Under shared mutex close A47-17 (merged trials + real HTTP/content evidence).
2. Parent final combined gate includes gacha/gacha_sheet/mice_tabs/previews, then builds
   MiceHub.spec and deploys once. Recheck trial_bar.css/js hashes against #75 after restart.
3. Parent takes A47-18 for that final integration and completion. Preserve real pages,
   dirty user data, trial pages, no real Sheet write without explicit authorization.

## Blocked
- Real Google read/write requires a configured Sheet and authorized Google setup/write test.
- Keep/drop for trial design is the user's choice; preserve both trial pages meanwhile.
- Actual hub build/restart/full gate reserved to parent until explicit BRIDGE release.
- A47-5 requires board/bench; no flash or physical motion authorized in this chat.
