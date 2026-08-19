"""A control that cannot be undone LOOKS like one — everywhere, from one rule.

Three things go wrong with destructive controls, and all three have happened
here:

  * one is dressed as an ordinary button, so unlinking four boards from an
    installation looks exactly like opening a panel;
  * one carries its red spelled out in an inline style, so the day --err
    changes it stays the old colour and nothing points at it;
  * the rule itself gets written with a literal red instead of the token, so
    the light theme inherits a colour chosen for the dark one.

The list below is the point of the check: adding a destructive action means
adding its handler here, and the check then insists the control says so.
"""
import re
from pathlib import Path

import qc as F

AREA = "design"
TITLE = "destructive controls look destructive"

# Handlers that destroy something a person cannot get back by clicking again.
# The control that RUNS one has to look like it: this list is the check, so
# adding a destructive action means adding a line here.
DESTRUCTIVE = ["unlinkSel", "removeUser"]


def run(t):
    css = (F.CODE / "shared" / "web" / "mice.css").read_text(encoding="utf-8")
    hub = (F.HUB / "web" / "hub.html").read_text(encoding="utf-8")

    # ---- the rule exists, and is built from the token ----------------
    t.contains(css, "button.danger{", "the shared sheet defines a danger button")
    rule = css[css.index("button.danger{"):]
    rule = rule[:rule.index("}") + 1]
    t.contains(rule, "var(--err)",
               "coloured from --err, not from a red written out by hand")
    t.ok(not re.search(r"#[0-9a-fA-F]{3,6}", rule),
         "with no literal colour in it",
         "a literal red survives a theme change; a token does not: " + rule)
    t.contains(css, "button.danger:hover",
               "and it answers the pointer, so it does not read as disabled")

    # ---- every destructive control in the hub says so ----------------
    for name in DESTRUCTIVE:
        # where the control is BUILT: the markup that binds the handler, or
        # the id of the button that runs it.
        spots = [m.start() for m in re.finditer(re.escape(name), hub)]
        t.ok(spots, "the hub still has %s" % name,
             "this list is the check: remove the action, remove the line")
        near = "".join(hub[max(0, i - 400):i + 400] for i in spots)
        t.contains(near, "danger",
                   "%s is marked as destructive where it is offered" % name)

    # ---- the confirm panel itself -----------------------------------
    # It does not fit the rule above, because the dangerous control IS the
    # dialog: what matters is which of its two buttons is dressed as the
    # obvious one. The safe choice has to be the prominent one, or a panel
    # that exists to slow someone down speeds them up instead.
    panel = hub[hub.index('id=' + chr(34) + 'flashModal'):][:4000]
    go = panel[max(0, panel.index('id=' + chr(34) + 'fcGo') - 120):
               panel.index('id=' + chr(34) + 'fcGo')]
    cancel = panel[max(0, panel.index('id=' + chr(34) + 'fcCancel') - 120):
                   panel.index('id=' + chr(34) + 'fcCancel')]
    t.contains(go, 'danger',
               'the button that overwrites the firmware is a danger button')
    t.contains(cancel, 'primary',
               'and the one that keeps the firmware is the prominent one')

    # ---- and nobody hand-rolls the colour ----------------------------
    inline = re.findall(r"style[^>\n]{0,40}var\(--err\)", hub)
    t.ok(not inline, "no control spells its danger out in an inline style",
         "found: %r — use class=danger so one rule owns it" % (inline[:3],))
