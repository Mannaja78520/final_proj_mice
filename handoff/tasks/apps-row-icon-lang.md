# Apps on this PC rows: icon glued to name blocks translation

Owner:
Updated: 2026-11-23 10:41 +0000
Branch: <branch, or main>
Last commit: <sha>
Plan: <plan ids, e.g. A45-11>

## Goal
<the user's ask, in their words if possible>

## Doing now
<written and pushed BEFORE each step: what you are about to do, the files, the approach>

## File status
Baseline: <starting SHA; reconcile owned commits, working diff and untracked files>

| File | Change | State | Verification | Commit |
| --- | --- | --- | --- | --- |
| `<repo/relative/path>` | <short change> | pending | not run | uncommitted |

<One latest row per owned source/generated/test/config/doc file, including additions,
deletions and renames. Use exact paths; link evidence and label quick/full or
simulated/hardware. Do not attribute other owners' edits. No edits: say so.
For this handoff file itself, Commit may be `this checkpoint`.>

## Facts found
- <file:line - what it does / why it matters; so the next AI does not read it again>

## Done
- <what landed, with PR or commit and how it was verified>

## Next
1. <the next concrete step, with the command if there is one>

## Blocked
- <what it waits on: robot, user account, a person, a decision; or "nothing">

## Task (from coordinator 2026-11-23, for GPT Codex on PC)
English mode: last row of "Apps on this PC" still shows "ผลงานล่าสุด" (should be "Latest work"); see .local\shots\tools_en_daylight.png.
Likely cause: main_python/web/home/parts/apps_manage.js draw() builds the title as `(a.icon ? a.icon + ' ' : '') + name`, one text node, so the whole-text-node key "ผลงานล่าสุด" (shared/web/lang/en.json:237) never matches.
Fix: render the icon in its own span, name in its own span (row() title). Add a QC test in qc/data/app_lifecycle.js, run `python tools/build_web.py`, `python qc/run_qc.py --quiet <checks>`, update Help if wording changes, PR + merge (standing approval), then ask for exe rebuild.
