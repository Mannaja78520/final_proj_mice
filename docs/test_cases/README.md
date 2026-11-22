# Test case lists (2026-11-22)

Three reviewers brainstormed cases independently from the code, one per area
(UI/UX, API/backend, firmware/sim). They are lists to run, not results.

| File | Cases | Runnable now (cloud) |
|---|---|---|
| ui_cases.md | 210 (UI-001..210) | most, with Playwright against the hub |
| api_cases.md | 164 (API-001..164) | most, HTTP against the hub + fake serial |
| firmware_cases.md | 173 (FW-001..173) | 140 SIM (QEMU/fake serial on the PC), 33 LAB |

Findings of the reviewers were checked against the code before being believed.
Results of what was actually run: `results_2026-11-22.md`.
LAB cases are not waited for: they join the lab session list (see results).
