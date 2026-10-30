# Independent Voice acceptance audit and duplicate-start fix

Owner: codex:voice-1030-01a1891e
Updated: 2026-10-30 13:30 +0700
Branch: codex/voice-helper-audit-1030
Last commit: this checkpoint
Plan: A55-2

## Goal
User: check all Voice features requested from Claude, fix remaining bugs and
verify actual results until complete. Do not disturb other work or live services.

## Doing now
Source repairs and Help generated; independent gpt-6-astra high review APPROVED.
No new tests run during peer heavy grant ending13:55:29 Bangkok; require explicit
peer completion/release before QC/compile. Next focused/sabotage, firmware, quick/full.

## File status
Baseline: 5bc6d2e (origin/main, PR115); own seven-file delta only.

| File | Change | State | Verification | Commit |
| --- | --- | --- | --- | --- |
| `handoff/tasks/voice-helper-audit-1030.md` | own audit/checkpoint | active | task claimed | this checkpoint |
| `main_python/voice_helper.py` | retain alive timed-out child, report error | fixed | 22/0, sabotage/restoration exact, review approved | 29c9f1a |
| `qc/checks/check_voice_helper.py` | timeout boundary/concurrency/recovery regression | verified | baseline19/3; fixed22/0; sabotage caught | bddff00 |
| `main_python/web/help/parts/voice.html` | document no duplicate helper while slow | verified | affected docs/Help passed | 29c9f1a |
| `main_python/web/help.html` | Windows gate prerequisite repair/Help | implemented | independent review approved; tests pending | this checkpoint |
| `docs/systems/agents.md` | regenerate header for own handoff file | rebuilt | only own handoff added; verification next | this checkpoint |
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

| `tools/ai_watch.py` | Windows gate prerequisite repair/Help | implemented | independent review approved; tests pending | this checkpoint |
| `docs/systems/ai-watch.md` | Windows gate prerequisite repair/Help | implemented | independent review approved; tests pending | this checkpoint |
| `qc/data/video_group.cjs` | Windows gate prerequisite repair/Help | implemented | independent review approved; tests pending | this checkpoint |
| `qc/checks/check_extensions.py` | Windows gate prerequisite repair/Help | implemented | independent review approved; tests pending | this checkpoint |
| `main_python/gacha.py` | Windows gate prerequisite repair/Help | implemented | independent review approved; tests pending | this checkpoint |
| `qc/checks/check_gacha_config_concurrency.py` | Windows gate prerequisite repair/Help | implemented | independent review approved; tests pending | this checkpoint |
| `main_python/web/help/parts/hub.html` | Windows gate prerequisite repair/Help | implemented | independent review approved; tests pending | this checkpoint |
| `main_python/web/help/parts/gacha.html` | Windows gate prerequisite repair/Help | implemented | independent review approved; tests pending | this checkpoint |
| `docs/systems/app-gacha.md` | Windows gate prerequisite repair/Help | implemented | independent review approved; tests pending | this checkpoint |
| `docs/systems/qc.md` | Windows gate prerequisite repair/Help | implemented | independent review approved; tests pending | this checkpoint |

| `_out/voice-helper-audit/gacha-diagnostic-report.txt` | ignored diagnosis evidence | saved | actual diagnostic only | not committed |
| `_out/voice-helper-audit/gacha-diagnostic.json` | ignored diagnosis evidence | saved | actual diagnostic only | not committed |
| `_out/voice-helper-audit/gacha-diagnostic.log` | ignored diagnosis evidence | saved | actual diagnostic only | not committed |
| `_out/voice-helper-audit/gacha-diagnostic.py` | ignored diagnosis evidence | saved | actual diagnostic only | not committed |
| `_out/voice-helper-audit/priority-diagnostic.json` | ignored diagnosis evidence | saved | actual diagnostic only | not committed |
| `_out/voice-helper-audit/priority-diagnostic.py` | ignored diagnosis evidence | saved | actual diagnostic only | not committed |
| `_out/voice-helper-audit/quick-diagnosis.txt` | ignored diagnosis evidence | saved | actual diagnostic only | not committed |

| `_out/voice-helper-audit/prerequisite-review.md` | exact source hashes + independent review | saved | approved read-only; not test proof | not committed |

## Facts found
- A55-1 is explicitly done in main's plan; PR111 merged8658d42. Its source is stable;
  remaining deployment and real app checks remain separate, not claimed from Claude.
- `main_python/voice_helper.py:139`: after60s start() replaces _proc although
  poll() is still None. Read-only fake Popen+clock at0/61 produced2 alive children.
- Existing1194/0 Voice results do not cover timeout expiry. Full9072/11 is RED,
  attributed to cloud environment by Claude; independent local gate still needed.
- Live helper13744 and Hub26664 belong to Claude's voice-test tree. Do not touch.
- Root main has unrelated RL changes; this isolated worktree starts clean origin/main4c25306.

## Done
- Implemented six Windows/fixture failures with Help parity; review approved after
  correcting event-dict regression fixture. No new test/compile driver started.
- Own checkout moved to supported path; RepoLayout now resolves real root correctly.
- Quick6659/11 exit1 (314.2s), 3893 inputs byte-exact; full not run.
- Failures: firmware binaries not built, two unsupported-copy layout expectations,
  watcher priority, extension separators, gacha atomic rename and video fixture keyCue.
  Minimal source/fixture repairs now reviewed; no new tests yet and no failures waived.
- Rebased onto main5bc6d2e; only own7file delta. Runtime/test/Voice Help content
  unchanged from independent review; generated agents conflict resolved from registry.
- Corrected generated agents header; systems/handoff/web metadata checks84/0 exit0.
- Sabotage exit0: baseline22/0, mutation19/3 exit1, restored22/0 exit0;
  runtime SHA256 a6609c67cdcfd6705d0436b3e086ff7f0fa0e9c070db6741f65d637a67862763 identical.
- Affected Voice/Help1237/1 exit1 in278.4s; only check_systems stale agents header.
- QC runner hit provider usage limit after reporting actual results; not a final gate approval.
- Fixed focused check22/0 exit0 (35.5s), not full gate; preserved _out evidence.
- Independent Codex review gpt-6-astra high approved exact final runtime/test/Help diff;
  no drivers/source edits by reviewer. UI may need Start/retry after a timeout.
- Reproduced duplicate-start failure with fake process/clock only, no ports/models.
- New regression: baseline check_voice_helper 19 passed / 3 expected failures; existing16 assertions pass.
- Rebased task-only branch from local RL history to clean origin/main4c25306 before publishing; no unrelated commits pushed.
- Read project debugging, verification, communication and subsystem instructions.

## Next
1. After peer release, focused new gacha/priority/extensions/video checks + sabotage; compile-only nong prerequisite; freeze quick/full.
2. Full gate only after QC lease and heavy-job constraints are satisfied; do not skip failures.
3. Continue feature acceptance: packaged launch, authenticated ask/say, STT, fallback,
   conversation/Stop and physical audio evidence; source/fakes are not hardware proof.

## Blocked
- Deployment/authenticated end-to-end and physical microphone/speaker checks are unverified.
- Quick/full gate pending; own quiet lease released for bounded peer heavy window.
  Require peer completion/release and fresh inventory before timing checks.
