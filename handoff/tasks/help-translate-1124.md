# Translate Help into Thai, Chinese, and Japanese

Owner: codex:11240136-969d
Updated: 2026-11-24 02:23 +0700
Branch: claude/help-translate-1124
Last commit: this checkpoint
Plan: A58-1124 (system)

## Goal
Zero English UI fragments on localized Help. Keep the browser check strict. Build web assets, run targeted and full QC, and push this branch.

## Doing now
Local work is recorded. Origin push remains blocked.

## File status
Baseline: 37cffd9bae0c7d03c943c7e5442ef63e843adcb6

| File | Change | State | Verification | Commit |
| --- | --- | --- | --- | --- |
| apps/all-jao/help/en.html | App Help localization | committed | Edge app fixtures | 8f50409 |
| apps/all-jao/help/ja.html | App Help localization | committed | Edge app fixtures | 8f50409 |
| apps/all-jao/help/th.html | App Help localization | committed | Edge app fixtures | 8f50409 |
| apps/all-jao/help/zh.html | App Help localization | committed | Edge app fixtures | 8f50409 |
| apps/camera/help/ja.html | App Help localization | committed | Edge app fixtures | 8f50409 |
| apps/camera/help/th.html | App Help localization | committed | Edge app fixtures | 8f50409 |
| apps/camera/help/zh.html | App Help localization | committed | Edge app fixtures | 8f50409 |
| apps/faces/help/en.html | App Help localization | committed | Edge app fixtures | 8f50409 |
| apps/faces/help/ja.html | App Help localization | committed | Edge app fixtures | 8f50409 |
| apps/faces/help/th.html | App Help localization | committed | Edge app fixtures | 8f50409 |
| apps/faces/help/zh.html | App Help localization | committed | Edge app fixtures | 8f50409 |
| apps/gacha/help/ja.html | App Help localization | committed | Edge app fixtures | 8f50409 |
| apps/gacha/help/th.html | App Help localization | committed | Edge app fixtures | 8f50409 |
| apps/gacha/help/zh.html | App Help localization | committed | Edge app fixtures | 8f50409 |
| apps/studio/help/ja.html | App Help localization | committed | Edge app fixtures | 8f50409 |
| apps/studio/help/th.html | App Help localization | committed | Edge app fixtures | 8f50409 |
| apps/studio/help/zh.html | App Help localization | committed | Edge app fixtures | 8f50409 |
| apps/voice/help/ja.html | App Help localization | committed | Edge app fixtures | 8f50409 |
| apps/voice/help/th.html | App Help localization | committed | Edge app fixtures | 8f50409 |
| apps/voice/help/zh.html | App Help localization | committed | Edge app fixtures | 8f50409 |
| docs/system_integral.html | Worktree plan row | committed | plan CLI | this checkpoint |
| docs/system_integral_state.js | Worktree plan row | committed | plan CLI | this checkpoint |
| docs/systems/agents.md | Register handoff in system index | committed | focused check_systems | f4c499a |
| handoff/tasks/help-translate-1124.md | Task checkpoint | committed | Edge and QC evidence | this checkpoint |
| main_python/web/help.html | Rebuilt Help | committed | build_web and Edge | dff2b75 |
| main_python/web/help/parts/accounts.html | Help localization | committed | Edge all topics | dff2b75 |
| main_python/web/help/parts/bytask.html | Help localization | committed | Edge all topics | dff2b75 |
| main_python/web/help/parts/firmware.html | Help localization | committed | Edge all topics | dff2b75 |
| main_python/web/help/parts/hub.html | Help localization | committed | Edge all topics | dff2b75 |
| main_python/web/help/parts/qc.html | Help localization | committed | Edge all topics | dff2b75 |
| qc/checks/check_visual_language.py | Zero-English scan | committed | full QC evidence | 8f50409 |
| shared/web/lang/help/ja.json | Help localization | committed | Edge all topics | dff2b75 |
| shared/web/lang/help/th.json | Help localization | committed | Edge all topics | dff2b75 |
| shared/web/lang/help/zh.json | Help localization | committed | Edge all topics | dff2b75 |
| shared/web/lang/ja.json | Help localization | committed | Edge all topics | dff2b75 |
| shared/web/lang/th.json | Help localization | committed | Edge all topics | dff2b75 |
| shared/web/lang/zh.json | Help localization | committed | Edge all topics | dff2b75 |
| tools/visual/pages.json | Zero-English scan | committed | full QC evidence | dff2b75 |


## Facts found
- shared/web/mice-lang.js:20 normalizes whitespace and translates each text node separately. Help locale packs override matching shared keys at line 138.
- Edge against the worktree QC hub found 66 Thai, 63 Chinese and 63 Japanese leaks after the existing exceptions. Raw evidence: _out/help-translate-1124/baseline.json.
- The Help scan includes hub Help and mounted app Help on the same page.

## Done
- Final Edge scan of all topics with eight shipped app guide fixtures: th 0, zh 0, ja 0. Evidence: _out/help-translate-1124/all-apps.json.
- Full QC: 10459 passed, 16 failed. Fixed the stale agents subsystem header afterward. Other failures covered firmware, stale API docs, partner startup and video tooling.. Evidence: _out/help-translate-1124/full-detail.log.
- Focused QC after the subsystem update: 415 passed, 3 failed. All three failures were Thai text on Home. Help and check_systems passed.. Evidence: _out/help-translate-1124/focused-final.log.
- Full QC: 10459 passed, 16 failed. The agents header was stale because this task added a handoff file. Other failures cover firmware, stale API docs, partner startup, and missing ffmpeg.
- Localized shipped app guides and normalized their MICE spelling. The strict QC scan now opens every Help topic before checking its text. Preserved gacha event field values as code.
- Completed the extra text audit, corrected the Studio text boundary, smoothed split firmware Help sentences, and rebuilt Help. Restored the seven unrelated build outputs to their original CRLF bytes.
- Targeted QC: 405 passed, 0 failed. Edge probe: th 0, zh 0, ja 0. A broader scan found a Studio quick-start text node that the probe regex misses.
- Captured the Edge baseline. The first translation pass reduced the counts to 1/1/1. Fixed that fragment and two additional fragments found by a broader visible-text scan. Rebuilt Help and replaced the per-language ratchet with a zero requirement.

## Next
1. Import _out/help-translate-1124/help-translate-1124.bundle into the worktree branch with Git write access.
2. Push the branch when credentials and Git write access are available. The full gate is red. See full-detail.log and focused-final.log for failures.

## Blocked
- Linked worktree Git metadata is read-only for this session. Commits use private metadata inside the worktree.
- CLI push could not access a credential. GitHub connector writes require approval, which is unavailable in this session.
