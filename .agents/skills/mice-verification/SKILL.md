---
name: mice-verification
description: Verify a completed Mice coding change, regression fix, firmware build, or promotion using current QC evidence and the exact changed tree.
---

All repository paths refer to the Mice root. Read `qc/README.md` and the relevant
staging/promotion rules in `CLAUDE.md`. Derive proof from the requested behavior;
do not substitute a generic test command for the repository's gate.

During iteration, use `python qc/run_qc.py --quick` and affected area checks as
required by the project. For a source change, the full gate is required before
claiming completion. `python promote.py` performs QC before copying changes;
inspect its options and current staging state before use. Never run `--init`
over unpromoted work or promote unrelated changes just to finish a small task.

Before starting a gate, establish that no other QC/fake-module driver is active.
Keep its input tree stable during the run. Avoid concurrent heavy model jobs
that could contaminate timing checks. Run builds for affected firmware targets;
report compile/size checks separately from on-board execution.

Confirm the actual command, tree, exit status, and relevant assertions. Inspect
the final diff, including new files and accidental deletions. For a bug fix,
show that the regression check fails without the fix; use isolated or reversible
changes and restore them before the final gate. Preserve test-touched user data.

Follow existing independent review requirements for the exact final files. Do
not accept empty, failed, or stale review results as approval. When a review
causes code changes, recheck affected behavior and invalidate proof for older
content. Do not stack an additional review framework over the existing one.

For changes limited to skills or agent instructions, validate SKILL.md metadata,
links, path resolution, invocation scope, and conflicting rules. No robot build,
hardware run, source promotion, or new runtime regression test is needed solely
for those instruction changes. Update the actual plan record.

Report changed behavior and concise evidence. Label checks as passed, failed,
skipped, unavailable, or not run. Never describe simulated results as measured
hardware results, a source run as a packaged build, or a review as proof of
bug-free software. Stop after authorized work and its required checks finish.
