---
name: mice-debugging
description: Diagnose Mice firmware, hub, Studio, transport, timing, or QC failures by reproducing the fault and tracing component boundaries before patching.
---

Resolve the Mice root from the working tree and its `CLAUDE.md`. All repository
paths below are relative to that root. Follow its staging and plan rules.

1. Establish the exact failing tree and running build. Inspect local changes,
   the decisive error, and the relevant QC check before proposing a cause.
   For stale executable symptoms, inspect `qc/checks/check_stale_build.py`.
2. Reproduce the user action with the smallest relevant check. List available
   checks with `python qc/run_qc.py --list`; use its supported area filter.
   Start with fake modules for PC diagnostics. Do not flash or move real boards
   merely to investigate a software claim without authorization for that action.
3. Trace the relevant path: browser event -> hub API -> port ownership/queue ->
   transport framing -> firmware command -> module behavior. Record what was
   sent and received at the boundary where expected and observed diverge.
   `fake_serial.wire`, `fake_wifi.MODULE.cmds`, and timestamps are evidence;
   a slider displaying the requested value does not prove a motor received it.
4. Test one causal hypothesis at a time. Check serial locks, device addresses,
   logging mixed with replies, timeout units, and command ownership when those
   are implicated. Read the implementation; old notes and model claims may be
   stale. Do not add sleeps or retries merely to hide a failure.
5. Add or strengthen a regression check for the actual failure and verify that
   it fails with the fix absent. Make the focused fix and rerun affected checks.

If a failure appears only under load, first check for another QC/browser driver
or competing heavy process. Never run simultaneous fake-module drivers. Do not
silently discard a red result as a flake. After repeated ineffective fixes,
revisit the hypothesis and record the evidence before attempting another patch.
Use the existing review workflow when required; judge findings against code.

Before claiming completion, follow `../mice-verification/SKILL.md`. Report
cause, changed paths, actual proof, and unmeasured hardware behavior briefly.
