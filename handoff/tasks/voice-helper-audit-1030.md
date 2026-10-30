# Independent Voice acceptance audit and duplicate-start fix

Owner: codex:voice-1030-01a1891e
Updated: 2026-10-30 14:41 +0700
Branch: codex/voice-helper-audit-1030
Last commit: this checkpoint
Plan: A55-2

## Goal
User: check all Voice features requested from Claude, fix remaining bugs and
verify actual results until complete. Do not disturb other work or live services.

## Doing now
Four sabotage cycles caught expected failures and restored byte-exact (exit0).
QC runner next compiles isolated nong image; stop if tracked content changes.
Then checkpoint, freeze manifest, quick/full serial; exclusive software lease held.
No live services/neural models/mic/speaker/hardware.

## File status
Baseline: 5bc6d2e (origin/main, PR115); own scoped delta only.
| File | Change | State | Verification | Commit |
| --- | --- | --- | --- | --- |
| `handoff/tasks/voice-helper-audit-1030.md` | own audit/checkpoint | active | task claimed | this checkpoint |
| `main_python/voice_helper.py` | retain alive timed-out child, report error | fixed | 22/0, sabotage/restoration exact, review approved | 29c9f1a |
| `qc/checks/check_voice_helper.py` | timeout boundary/concurrency/recovery regression | verified | baseline19/3; fixed22/0; sabotage caught | bddff00 |
| `main_python/web/help/parts/voice.html` | document no duplicate helper while slow | verified | affected docs/Help passed | 29c9f1a |
| `main_python/web/help.html` | Windows gate prerequisite repair/Help | implemented | review approved; focused190/0; full pending | e194b12 |
| `docs/systems/agents.md` | regenerate header for own handoff file | verified | metadata84/0; own task only | 83e53b9 |
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
| `main_python/web/help/parts/hub.html` | Windows gate prerequisite repair/Help | implemented | review approved; focused190/0; full pending | e194b12 |
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
| `_out/voice-helper-audit/firmware-prepare-console.log` | isolated QC evidence | pending | not run unless focused190/0 | not committed |
| `_out/voice-helper-audit/firmware-prepare-exit.txt` | isolated QC evidence | pending | not run unless focused190/0 | not committed |
| `_out/voice-helper-audit/before-final-gates-manifest.json` | isolated QC evidence | pending | not run unless focused190/0 | not committed |
| `_out/voice-helper-audit/after-quick-r2-manifest.json` | isolated QC evidence | pending | not run unless focused190/0 | not committed |
| `_out/voice-helper-audit/after-full-manifest.json` | isolated QC evidence | pending | not run unless focused190/0 | not committed |
| `_out/voice-helper-audit/quick-r2-console.log` | isolated QC evidence | pending | not run unless focused190/0 | not committed |
| `_out/voice-helper-audit/quick-r2-full.log` | isolated QC evidence | pending | not run unless focused190/0 | not committed |
| `_out/voice-helper-audit/quick-r2-exit.txt` | isolated QC evidence | pending | not run unless focused190/0 | not committed |
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

## Facts found
- A55-1 is explicitly done in main's plan; PR111 merged8658d42. Its source is stable;
  remaining deployment and real app checks remain separate, not claimed from Claude.
- `main_python/voice_helper.py:139`: after60s start() replaces _proc although
  poll() is still None. Read-only fake Popen+clock at0/61 produced2 alive children.
- Claude full9072/11 is RED; independent current full required.
- Live helper13744 and Hub26664 belong to Claude's voice-test tree. Do not touch.
- Own tree based on origin/main5bc6d2e; unrelated root RL source/history excluded.

## Done
- Focused prerequisites190/0 exit0 63.2s; map/Help and all four repaired failure groups pass.
- Four sabotage cycles exit0 154.17s: gacha7/0->6/1->7/0;
  priority29/0->28/1->29/0; extensions28/0->26/2->28/0; video60/0->58/2->60/0.
  All tracked-byte drift arrays empty. Last two are fixture proof only.
- Voice timeout fixed22/0; sabotage22/0->19/3->22/0 byte-exact; review approved.
- Windows/config/fixture source and same-step Help e194b12 independently approved;
  reviewed regression fixture corrected to production event dict before focused check.
- Earlier quick6659/11 red and affected1237/1 (stale agents header) preserved;
  metadata header correction84/0. No failures waived; no current full yet.
- Own checkout moved to supported .staging path; layout behavior awaits quick recheck.

## Next
1. Compile-only nong prerequisite; checkpoint any prepare drift; freeze/re-run quick, then full only if green/stable.
2. Full gate only after QC lease and heavy-job constraints are satisfied; do not skip failures.
3. Continue feature acceptance: packaged launch, authenticated ask/say, STT, fallback,
   conversation/Stop and physical audio evidence; source/fakes are not hardware proof.

## Blocked
- Deployment/authenticated end-to-end and physical microphone/speaker checks are unverified.
- Quick/full pending; peer heavy block explicitly released13:44, inventory clear.
  Own exclusive software timing/build lease re-claimed for verification.
