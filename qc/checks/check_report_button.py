"""The report button works twice in a row, and anyone can press it.

A21-6 put a 🐛 Report button on the hub's stop bar - page-wide, like STOP,
because a problem is noticed wherever you happen to be. No login: complaining
must never need a password (the plan's own words).

The bug this check exists for was caught by the post-landing panel,
2026-08-25: submitReport disables the Send button for the flight, and the
success path closes the modal WITHOUT re-enabling it - so the SECOND report
anyone tried to send had a dead button stuck on *Sending…*. The first report
worked, which is exactly how this class hides: every test sends one report
and stops.
"""
import qc as F

AREA = "ui"
TITLE = "the report button opens from anywhere, needs no login, and works again after sending"


def run(t):
    hub = (F.HUB / "web" / "hub.html").read_text(encoding="utf-8")
    auth = (F.HUB / "hub_auth.py").read_text(encoding="utf-8")

    # ---- reachable from every tab --------------------------------------
    stop = hub[hub.find('class="stopbar"'):]
    stop = stop[:stop.find("</div>")]
    t.contains(stop, 'id="reportBtn"',
               "the Report button sits in the stop bar, above every tab")
    t.contains(stop, "openReport()", "and is wired to open the modal")

    # ---- no password between a person and complaining -------------------
    # The gate is DATA: hub_auth.gated() consults these sets, so the report
    # route belongs in OPEN by name - listed intent, not absence.
    op = auth[auth.find("OPEN = {"):]
    op = op[op.find("{"):op.find("}")]
    t.ok('"/api/report"' in op,
         "sending a report needs NO password (listed in hub_auth OPEN)",
         "complaining must never need a login - a person with a problem and "
         "no account is exactly the person this button is for")
    for gated in ("GATED = {", "GATED_POST = {", "CODE_GATED = {"):
        blk = auth[auth.find(gated):]
        blk = blk[blk.find("{"):blk.find("}")]
        t.ok('"/api/report"' not in blk,
             "and is not in the gated sets (%s)" % gated.split(" ")[0])

    # ---- the second send must work too ---------------------------------
    cr = hub[hub.find("function closeReport"):]
    cr = cr[:cr.find("\n}") + 2]
    t.ok("send.disabled = false" in cr and "'Send report'" in cr.replace('"', "'"),
         "closing the modal re-arms the Send button",
         "submitReport disables it for the flight; a success path that never "
         "re-enables it leaves the next report a dead button stuck on "
         "*Sending...* - caught by the post-landing panel, 2026-08-25")
    sub = hub[hub.find("async function submitReport"):]
    sub = sub[:sub.find("\n}") + 2]
    t.ok("send.disabled = true" in sub,
         "Send is disabled only while the report is in flight")
