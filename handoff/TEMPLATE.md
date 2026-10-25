# <task title>

Owner: <agent id, e.g. claude:handoff-mkf9 or codex:10201312; empty = free>
Updated: <date and time, from the clock>
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
