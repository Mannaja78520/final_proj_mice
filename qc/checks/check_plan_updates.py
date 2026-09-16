"""A user request reaches the STATE block before work starts - really.

A21-1's second rule: anything the user asks for is written into the plan the
moment it is asked, in their own words, BEFORE the work starts. Asked
2026-08-22 after having to ask several times. A rule that only lives in a
conversation dies with the conversation; this check pins the rule and its
mechanism into every session's required reading.
"""
import qc as F

AREA = "tools"
TITLE = "the write-it-into-the-plan rule exists with its tool beside it"

RULE_2 = "goes into the STATE block the moment it is"


def run(t):
    claude_md = (F.CODE / "CLAUDE.md").read_text(encoding="utf-8")
    t.contains(claude_md, RULE_2,
               "CLAUDE.md still carries the plan-updates rule")
    t.ok((F.CODE / "tools" / "plan.py").is_file(),
         "tools/plan.py - the mechanism the rule names - is still there")
