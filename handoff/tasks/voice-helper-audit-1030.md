# Independent Voice acceptance audit and duplicate-start fix
Owner: codex:voice-1030-01a1891e
Updated: 2026-10-30 18:20 +0700
Branch: codex/voice-helper-audit-1030
Last commit: this checkpoint
Plan: A55-2
## Goal
Check all requested Voice behavior, fix bugs and verify actual results; preserve other work.
## Doing now
Peer explicit18:20 heavy release +clear inventory; exclusive own QC reclaimed.
Run focused layout/promotion/Help then mutation/restoration; checkpoint before
canonical-LF manifest quick-r3/full. Source9641ce0 review approved, tests pending.
No input edits while drivers run; preserve five canonical-LF outputs.
## File status
Baseline5bc6d2e; own scoped delta only. Ignored evidence preserved; tests distinguish fakes/hardware.
| File | Change | State | Verification | Commit |
| --- | --- | --- | --- | --- |
| `handoff/tasks/voice-helper-audit-1030.md` | own audit/checkpoint | active | task claimed | this checkpoint |
| `main_python/voice_helper.py` | retain alive timed-out child, report error | fixed | 22/0, sabotage/restoration exact, review approved | 29c9f1a |
| `qc/checks/check_voice_helper.py` | timeout boundary/concurrency/recovery regression | verified | baseline19/3; fixed22/0; sabotage caught | bddff00 |
| `main_python/web/help/parts/voice.html` | document no duplicate helper while slow | verified | affected docs/Help passed | 29c9f1a |
| `main_python/web/help.html` | promotion root/fixture/Help repair | implemented | final independent review approved; tests pending | 9641ce0 |
| `docs/systems/agents.md` | promotion root/fixture/Help repair | implemented | final independent review approved; tests pending | 9641ce0 |
| `docs/systems/app-voice.md` | record lifecycle trap | verified | independent review approved | 29c9f1a |
| `_out/voice-helper-audit/baseline.log` | baseline regression evidence (ignored) | saved | 19/3 expected | not committed |
| `_out/voice-helper-audit/fixed-helper.log` | fixed focused result (ignored) | saved | 22/0, exit0 | not committed |
| `_out/voice-helper-audit/live-readonly.json` | passive live status (ignored) | saved | GET only, no inference | not committed |
| `docs/PLAN.html` | root-only A55-2 row | active | plan tool add/doing succeeded | uncommitted root bookkeeping |
| `docs/plan_state.js` | root-only generated plan | active | plan tool sync | uncommitted root bookkeeping |
| `docs/BRIDGE.md` | root-only exact claims/provenance notice | active | mutex append | uncommitted root bookkeeping |
| `_out/voice-helper-audit/acceptance.md` | ignored verification evidence | saved | actual results preserved | not committed |
| `_out/voice-helper-audit/affected-console.log` | ignored verification evidence | saved | actual results preserved | not committed |
| `_out/voice-helper-audit/affected-exit.txt` | ignored verification evidence | saved | actual results preserved | not committed |
| `_out/voice-helper-audit/affected-full.log` | ignored verification evidence | saved | actual results preserved | not committed |
| `_out/voice-helper-audit/agents-header-diff.txt` | ignored verification evidence | saved | actual results preserved | not committed |
| `_out/voice-helper-audit/review.md` | ignored verification evidence | saved | actual results preserved | not committed |
| `_out/voice-helper-audit/run_sabotage.py` | ignored verification evidence | saved | actual results preserved | not committed |
| `_out/voice-helper-audit/sabotage-baseline.log` | ignored verification evidence | saved | actual results preserved | not committed |
| `_out/voice-helper-audit/sabotage-evidence.json` | ignored verification evidence | saved | actual results preserved | not committed |
| `_out/voice-helper-audit/sabotage-mutated.log` | ignored verification evidence | saved | actual results preserved | not committed |
| `_out/voice-helper-audit/sabotage-restored.log` | ignored verification evidence | saved | actual results preserved | not committed |
| `_out/voice-helper-audit/sabotage-spec.json` | ignored verification evidence | saved | actual results preserved | not committed |
| `_out/voice-helper-audit/sabotage.log` | ignored verification evidence | saved | actual results preserved | not committed |
| `_out/voice-helper-audit/gate-preflight.txt` | ignored verification evidence | saved | actual results preserved | not committed |
| `_out/voice-helper-audit/metadata-fixed.log` | ignored verification evidence | saved | actual results preserved | not committed |
| `_out/voice-helper-audit/after-quick-manifest.json` | ignored verification evidence | saved | actual results preserved | not committed |
| `_out/voice-helper-audit/before-manifest.json` | ignored verification evidence | saved | actual results preserved | not committed |
| `_out/voice-helper-audit/cache-copy.log` | ignored verification evidence | saved | actual results preserved | not committed |
| `_out/voice-helper-audit/gate-web-build.log` | ignored verification evidence | saved | actual results preserved | not committed |
| `_out/voice-helper-audit/quick-console.log` | ignored verification evidence | saved | actual results preserved | not committed |
| `_out/voice-helper-audit/quick-exit.txt` | ignored verification evidence | saved | actual results preserved | not committed |
| `_out/voice-helper-audit/quick-full.log` | ignored verification evidence | saved | actual results preserved | not committed |
| `_out/voice-helper-audit/snapshot_inputs.py` | ignored verification evidence | saved | actual results preserved | not committed |
| `tools/ai_watch.py` | Windows gate prerequisite repair/Help | implemented | review approved; focused190/0; full pending | e194b12 |
| `docs/systems/ai-watch.md` | Windows gate prerequisite repair/Help | implemented | review approved; focused190/0; full pending | e194b12 |
| `qc/data/video_group.cjs` | Windows gate prerequisite repair/Help | implemented | review approved; focused190/0; full pending | e194b12 |
| `qc/checks/check_extensions.py` | Windows gate prerequisite repair/Help | implemented | review approved; focused190/0; full pending | e194b12 |
| `main_python/gacha.py` | Windows gate prerequisite repair/Help | implemented | review approved; focused190/0; full pending | e194b12 |
| `qc/checks/check_gacha_config_concurrency.py` | Windows gate prerequisite repair/Help | implemented | review approved; focused190/0; full pending | e194b12 |
| `main_python/web/help/parts/hub.html` | promotion root/fixture/Help repair | implemented | final independent review approved; tests pending | 9641ce0 |
| `main_python/web/help/parts/gacha.html` | Windows gate prerequisite repair/Help | implemented | review approved; focused190/0; full pending | e194b12 |
| `docs/systems/app-gacha.md` | Windows gate prerequisite repair/Help | implemented | review approved; focused190/0; full pending | e194b12 |
| `docs/systems/qc.md` | Windows gate prerequisite repair/Help | implemented | review approved; focused190/0; full pending | e194b12 |
| `_out/voice-helper-audit/gacha-diagnostic-report.txt` | ignored diagnosis evidence | saved | actual diagnostic only | not committed |
| `_out/voice-helper-audit/gacha-diagnostic.json` | ignored diagnosis evidence | saved | actual diagnostic only | not committed |
| `_out/voice-helper-audit/gacha-diagnostic.log` | ignored diagnosis evidence | saved | actual diagnostic only | not committed |
| `_out/voice-helper-audit/gacha-diagnostic.py` | ignored diagnosis evidence | saved | actual diagnostic only | not committed |
| `_out/voice-helper-audit/priority-diagnostic.json` | ignored diagnosis evidence | saved | actual diagnostic only | not committed |
| `_out/voice-helper-audit/priority-diagnostic.py` | ignored diagnosis evidence | saved | actual diagnostic only | not committed |
| `_out/voice-helper-audit/quick-diagnosis.txt` | ignored diagnosis evidence | saved | actual diagnostic only | not committed |
| `_out/voice-helper-audit/prerequisite-review.md` | exact source hashes + independent review | saved | approved read-only; not test proof | not committed |
| `_out/voice-helper-audit/prerequisite-focused-console.log` | isolated QC evidence | saved | 190/0 exit0 63.2s | not committed |
| `_out/voice-helper-audit/prerequisite-focused-full.log` | isolated QC evidence | saved | 190/0 exit0 63.2s | not committed |
| `_out/voice-helper-audit/prerequisite-focused-exit.txt` | isolated QC evidence | saved | 190/0 exit0 63.2s | not committed |
| `_out/voice-helper-audit/prerequisite-sabotage.py` | isolated QC evidence | saved | phase results in prerequisite-sabotage-evidence.json | not committed |
| `_out/voice-helper-audit/prerequisite-sabotage.log` | isolated QC evidence | saved | phase results in prerequisite-sabotage-evidence.json | not committed |
| `_out/voice-helper-audit/prerequisite-sabotage-evidence.json` | isolated QC evidence | saved | phase results in prerequisite-sabotage-evidence.json | not committed |
| `_out/voice-helper-audit/gacha-sabotage-spec.json` | isolated QC evidence | saved | phase results in prerequisite-sabotage-evidence.json | not committed |
| `_out/voice-helper-audit/priority-sabotage-spec.json` | isolated QC evidence | saved | phase results in prerequisite-sabotage-evidence.json | not committed |
| `_out/voice-helper-audit/extensions-sabotage-spec.json` | isolated QC evidence | saved | phase results in prerequisite-sabotage-evidence.json | not committed |
| `_out/voice-helper-audit/video-sabotage-spec.json` | isolated QC evidence | saved | phase results in prerequisite-sabotage-evidence.json | not committed |
| `_out/voice-helper-audit/firmware-prepare-console.log` | isolated QC evidence | saved | compile exit0; tracked bytes unchanged | not committed |
| `_out/voice-helper-audit/firmware-prepare-exit.txt` | isolated QC evidence | saved | compile exit0; tracked bytes unchanged | not committed |
| `_out/voice-helper-audit/before-final-gates-manifest.json` | isolated QC evidence | saved | quick6751/2 exit1; five newline drifts preserved | not committed |
| `_out/voice-helper-audit/after-quick-r2-manifest.json` | isolated QC evidence | saved | quick6751/2 exit1; five newline drifts preserved | not committed |
| `_out/voice-helper-audit/after-full-manifest.json` | isolated QC evidence | pending | not run unless focused190/0 | not committed |
| `_out/voice-helper-audit/quick-r2-console.log` | isolated QC evidence | saved | quick6751/2 exit1; five newline drifts preserved | not committed |
| `_out/voice-helper-audit/quick-r2-full.log` | isolated QC evidence | saved | quick6751/2 exit1; five newline drifts preserved | not committed |
| `_out/voice-helper-audit/quick-r2-exit.txt` | isolated QC evidence | saved | quick6751/2 exit1; five newline drifts preserved | not committed |
| `_out/voice-helper-audit/full-console.log` | isolated QC evidence | pending | not run unless focused190/0 | not committed |
| `_out/voice-helper-audit/full-full.log` | isolated QC evidence | pending | not run unless focused190/0 | not committed |
| `_out/voice-helper-audit/full-exit.txt` | isolated QC evidence | pending | not run unless focused190/0 | not committed |
| `_out/voice-helper-audit/gacha-sabotage-baseline.log` | isolated QC evidence | saved | green; tracked bytes restored | not committed |
| `_out/voice-helper-audit/gacha-sabotage-mutated.log` | isolated QC evidence | saved | expected regression failure caught | not committed |
| `_out/voice-helper-audit/gacha-sabotage-restored.log` | isolated QC evidence | saved | green; tracked bytes restored | not committed |
| `_out/voice-helper-audit/priority-sabotage-baseline.log` | isolated QC evidence | saved | green; tracked bytes restored | not committed |
| `_out/voice-helper-audit/priority-sabotage-mutated.log` | isolated QC evidence | saved | expected regression failure caught | not committed |
| `_out/voice-helper-audit/priority-sabotage-restored.log` | isolated QC evidence | saved | green; tracked bytes restored | not committed |
| `_out/voice-helper-audit/extensions-sabotage-baseline.log` | isolated QC evidence | saved | green; tracked bytes restored | not committed |
| `_out/voice-helper-audit/extensions-sabotage-mutated.log` | isolated QC evidence | saved | expected regression failure caught | not committed |
| `_out/voice-helper-audit/extensions-sabotage-restored.log` | isolated QC evidence | saved | green; tracked bytes restored | not committed |
| `_out/voice-helper-audit/video-sabotage-baseline.log` | isolated QC evidence | saved | green; tracked bytes restored | not committed |
| `_out/voice-helper-audit/video-sabotage-mutated.log` | isolated QC evidence | saved | expected regression failure caught | not committed |
| `_out/voice-helper-audit/video-sabotage-restored.log` | isolated QC evidence | saved | green; tracked bytes restored | not committed |
| `promote.py` | promotion root/fixture/Help repair | implemented | final independent review approved; tests pending | 9641ce0 |
| `qc/checks/check_parallel_runs.py` | promotion root/fixture/Help repair | implemented | final independent review approved; tests pending | 9641ce0 |
| `qc/checks/check_build_web.py` | diagnosis only; temp fixture not drift cause | unchanged | no repair needed | no change |
| `apps/camera/index.html` | canonical LF generator preparation | prepared | canonical LF; normalized HEAD identity verified | 5bc6d2e byte-only |
| `apps/voice/index.html` | canonical LF generator preparation | prepared | canonical LF; normalized HEAD identity verified | 5bc6d2e byte-only |
| `main_python/web/hub.html` | canonical LF generator preparation | prepared | canonical LF; normalized HEAD identity verified | 5bc6d2e byte-only |
| `nong/main_python_set_nong/web/app.js` | canonical LF generator preparation | prepared | canonical LF; normalized HEAD identity verified | 5bc6d2e byte-only |
| `nong/main_python_set_nong/web/index.html` | canonical LF generator preparation | prepared | canonical LF; normalized HEAD identity verified | 5bc6d2e byte-only |
| `_out/voice-helper-audit/layout-design-review.md` | current layout/gate evidence | saved | independent read-only review | not committed |
| `_out/voice-helper-audit/layout-final-review.md` | current layout/gate evidence | saved | independent read-only review | not committed |
| `_out/voice-helper-audit/layout-focused-console.log` | current layout/gate evidence | pending | not run | not committed |
| `_out/voice-helper-audit/layout-focused-full.log` | current layout/gate evidence | pending | not run | not committed |
| `_out/voice-helper-audit/layout-focused-exit.txt` | current layout/gate evidence | pending | not run | not committed |
| `_out/voice-helper-audit/run-layout-sabotage.py` | current layout/gate evidence | pending | not run | not committed |
| `_out/voice-helper-audit/layout-sabotage-spec.json` | current layout/gate evidence | pending | not run | not committed |
| `_out/voice-helper-audit/layout-sabotage.log` | current layout/gate evidence | pending | not run | not committed |
| `_out/voice-helper-audit/layout-sabotage-evidence.json` | current layout/gate evidence | pending | not run | not committed |
| `_out/voice-helper-audit/layout-sabotage-baseline.log` | current layout/gate evidence | pending | not run | not committed |
| `_out/voice-helper-audit/layout-sabotage-mutated.log` | current layout/gate evidence | pending | not run | not committed |
| `_out/voice-helper-audit/layout-sabotage-restored.log` | current layout/gate evidence | pending | not run | not committed |
| `_out/voice-helper-audit/before-r3-gates-manifest.json` | current layout/gate evidence | pending | not run | not committed |
| `_out/voice-helper-audit/quick-r3-console.log` | current layout/gate evidence | pending | not run | not committed |
| `_out/voice-helper-audit/quick-r3-full.log` | current layout/gate evidence | pending | not run | not committed |
| `_out/voice-helper-audit/quick-r3-exit.txt` | current layout/gate evidence | pending | not run | not committed |
| `_out/voice-helper-audit/after-quick-r3-manifest.json` | current layout/gate evidence | pending | not run | not committed |
## Facts found
- promote.py:58/90/98 rooted MAIN back into the copy; fixing MAIN also corrects promotion destination/bookkeeping.
- check_dev_tools.py:67 nested sabotage->QC rebuilds real web outputs despite outer--no-build; prepare canonical LF before freeze.
- MiceHub.spec global kill calls prohibit direct build while live EXEs exist; private safe recipe needed later (acceptance.md).
## Done
- Sourcee194b12 independently approved; focused190/0, four sabotage cycles caught/restored exact; nong compile0/78.89s.
- Quick-r2@8d79fff6751/2 exit1/968.8s, five newline drifts; full NOT run. Earlier red/Voice receipts preserved.
## Next
Fix/review layout, focused+sabotage, then stable canonical-LF quick/full; PR/integration/package/real Voice acceptance after green.
## Blocked
No resource blocker now; authenticated real STT/ask/say/mic/speaker/rig/package still unverified.
