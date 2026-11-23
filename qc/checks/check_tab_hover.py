"""The selected tab keeps its fill under the pointer (user 2026-11-23, real PC).

`button:hover:not(:disabled)` is more specific than `.tab.on`, so hovering the selected tab (every
real click leaves the pointer there) turned its background pale while the label stayed
--on-acc: 1.25:1 contrast, unreadable. A rule `.tab.on:hover` must win over it.
"""
import re
from pathlib import Path

import qc as F

AREA = "hub"
TITLE = "the selected tab stays readable while hovered"
SLOW = False


def run(t):
    css = (Path(F.CODE) / "shared" / "web" / "mice.css").read_text(encoding="utf-8")
    t.ok("button:hover:not(:disabled){border-color:var(--acc);background:var(--acc-soft)}" in css,
         "the general button hover rule is still the reason this check exists")
    m = re.search(r"\.tab\.on:hover:not\(:disabled\)\{([^}]*)\}", css)
    t.ok(bool(m), "a .tab.on:hover rule at least as specific as the button hover rule exists")
    body = m.group(1) if m else ""
    t.ok("background:var(--acc)" in body and "color:var(--on-acc)" in body,
         "it keeps the accent fill and its readable label colour", body)
