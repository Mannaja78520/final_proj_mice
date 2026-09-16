# Mice coding instructions

For simultaneous Codex, Antigravity and Claude sessions, read
`docs/COORDINATION.md` and the newest `docs/BRIDGE.md` entries before editing.
Claim files before writing; serialize bridge/plan updates with the shared
mutex. Existing sessions must reload these rules. Ownership and QC claims
apply across all working copies. Do not infer release from inactivity.
For limits or a new prompt, follow the provider-limit and resume procedure in
`docs/COORDINATION.md`: Codex help first; fallback only when unavailable.
The latest relevant BRIDGE handoff identifies the task, tree and next step.

User preference: Caveman **full**, plain-speak, and token-thrift. Replies stay
short; clarity, exact technical detail, and verified results outrank compression.
These preferences do not reduce implementation scope or required checks.
Any thrift rule against re-reading yields to final-diff inspection, changed
files, failed checks, or new evidence. Do not treat older context as immutable.

Read `CLAUDE.md` once per session for the existing project workflow. Use the
current request to determine scope; old unfinished tasks do not authorize
unrelated work. Read relevant entries and decisions in `docs/PLAN.html`, not
the entire historical STATE block. Update the real plan with `tools/plan.py`.
Use `--page robot` or `--page system` explicitly when task ids could overlap.

Load only relevant skills. The reusable communication skills live in the
host's user skill directory (`~/.codex/skills` or `~/.claude/skills`). Their names
are `caveman`, `plain-speak`, and `token-thrift`; preserve the user's full mode.
If unavailable, the first paragraph supplies the essential communication rule.

Project skills, shared by any agent that can read Markdown:

| When | Read |
| --- | --- |
| Bug, regression, build failure, timing or transport fault | `.agents/skills/mice-debugging/SKILL.md` |
| Commands, motion, configuration registries, transports, or calibration change | `.agents/skills/mice-contract-check/SKILL.md` |
| Hub, Studio, module page, or app UI change | `.agents/skills/mice-web-check/SKILL.md` |
| Before declaring a coding task complete or promoting changes | `.agents/skills/mice-verification/SKILL.md` |

These skills complement the existing staging, QC, and review workflow; they
do not introduce a second planning system or replace required model reviews.
Use the existing review workflow once for the applicable change. Do not add
extra panels or paid model comparisons just to select skills. Skills do not
authorize subagents, hardware actions, or external publication by themselves.

For source changes, preserve unpromoted `.staging` work and unrelated user edits.
Never initialize staging blindly. Only one QC/fake-module driver may run at a
time; do not edit its tree while its gate runs. Preserve line endings on Windows.
Agent instruction and skill setup may be edited directly in this tree; verify
those files and update the real plan without promoting unrelated source work.

Continue authorized work through verification. Report what changed, evidence,
and any remaining limits. A failed model call is not an approving review, and
a simulated module check is not a hardware measurement.
