# Make every app easy for non-engineers

Owner:
Updated: 2026-11-20 12:11 +0000
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

## Doing now
Full QC, then PR. (2026-11-20, claude)

## Done
- Mice.Words (shared/web/mice-ui.js): one table turns browser error text into plain sentences, raw text behind the technical switch; ~45 catch sites converted (Studio parts, Home parts, Voice, TV).
- hub_compress.py + Handler.send_bytes: gzip when asked, ETag/304 for pages/scripts/styles, /api stays no-store.
- Measured (gzip): Studio app.js 653->211 KB, Home 181->59, Help 261->73, Voice 186->52; revisit = 304, 0 bytes.
- check_page_squeeze (sabotage-proven), Help bytask.html note (Rule 11).

## Next / not done
- Wording audit of visible labels (not errors) on Gacha/Faces/Studio panels; Studio 653 KB script is still heavy for a TV (split/lazy-load = bigger job, needs on-device numbers).
- Not tested on a real Android TV; no robot/hardware tests.

## File status
Baseline: 72d5eff. All rows: uncommitted, quick QC pass for check_page_squeeze/designer_first/build_web/systems; full QC running.
