---
name: mice-web-check
description: Verify Mice hub, Nong Studio, module pages, and app UI changes with the existing Edge/fake-module browser harness and shared design system.
---

All repository paths refer to the Mice root. Follow current project design and
review decisions in `CLAUDE.md` and the relevant plan entry. Reuse shared UI
assets and existing page behavior; do not introduce a new browser framework.

For a visual redesign, use the installed `webapp-design` skill if available;
read only the references the screen needs. Otherwise inspect the current shared
styles and a representative sibling page. Preserve shared tokens, offline assets,
keyboard access, labels, and existing DOM hooks used by scripts and checks.

For browser execution, read `.claude/skills/web-page-check/SKILL.md` and relevant
notes in `qc/lib/browser.py`. Its sample uses a machine-specific staging path;
resolve the actual working tree rather than copying that absolute path.
Use the existing fake-module harness. Check browser availability first.

Verify the changed user journey, including relevant loading, empty, error,
offline/stale, logged-out, and ready states. Check narrow and wide layouts with
the project's responsive checks. A screenshot establishes appearance, not
click behavior, login enforcement, persistence, or commands reaching a module.

Assert effects using fake-module commands or saved isolated data. End a harness
driver with its completion marker and clean up the browser in finally. Run only
one QC/fake-module driver at a time, never alongside a promotion gate.

Use a permanent regression check for a fixed behavior. A throwaway browser
inspection does not replace required QC or the final gate. Keep technical details
behind the product's existing technical switch, with actionable messages and
controls visible to the operator.
