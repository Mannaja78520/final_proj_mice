"""Every Studio pop-up question is a centred modal, not pinned to the top-left.

2026-11-23: "Back to the simple shapes: which sizes?" showed at the top-left over
the 3D view and title bar. mice.css has *{margin:0}, which strips the <dialog>
auto margins, so a dialog without the shared .askdlg class (margin:auto) sits in
the corner. Every dialog, in the HTML parts and the ones JS builds, must carry it.
"""
import re
from pathlib import Path

import qc as F

AREA = "studio"
TITLE = "every Studio dialog uses the centred .askdlg class"



def run(t):
    web = Path(__file__).resolve().parents[2] / "nong" / "main_python_set_nong" / "web"
    tags = []
    for p in list((web / "html_parts").glob("*.html")) + [web / "index.template.html"]:
        for m in re.finditer(r"<dialog\b[^>]*>", p.read_text(encoding="utf-8")):
            tags.append((p.name, m.group(0)))
    t.ok(len(tags) >= 2, "found the static dialogs", tags)
    for name, tag in tags:
        t.ok("askdlg" in tag, "%s: %s centred" % (name, tag[:60]), tag)
    for p in (web / "app_parts").glob("*.js"):
        src = p.read_text(encoding="utf-8")
        for m in re.finditer(r'createElement\("dialog"\)', src):
            t.ok("askdlg" in src[m.end():m.end() + 200], "%s: built dialog centred" % p.name)
    css = (web / "style.css").read_text(encoding="utf-8")
    t.ok(re.search(r"\.askdlg\{margin:auto", css), "the .askdlg rule keeps margin:auto")
