"""Every AI that works here is told HOW TO READ, not only how to answer.

Asked 2026-09-22 (A26-93): Codex and Antigravity could still open all of
main.py (~38k tokens) to find one function. tools/ai_brief.txt only covered
the answer style. The read rules now sit in AGENTS.md (Codex), GEMINI.md
(Antigravity) and ai_brief.txt (every agy prompt). This keeps all three.
"""
import qc as F

AREA = "tools"
TITLE = "every AI is told how to read: header first, search, then a range"

MUST = ("systems.py which", "40-100 lines", "300 lines", "already read", "failing line only")


def run(t):
    for name in ("AGENTS.md", "GEMINI.md", "tools/ai_brief.txt"):
        text = (F.CODE / name).read_text(encoding="utf-8", errors="replace")
        gone = [m for m in MUST if m not in text]
        t.ok(not gone, "%s carries the read rules" % name,
             "missing: %s - an agent reads whole files again" % ", ".join(gone))
