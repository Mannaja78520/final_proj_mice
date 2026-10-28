"""Real Edge journeys for failed scans/actions and the Lift fault recovery controls."""
import browser
import fake_serial
import qc as F

AREA = "hub"
TITLE = "failed UI actions remain visible and Lift clear never sends motion"
SLOW = True


def run(t):
    if not browser.available():
        t.give_up("Edge is required for the changed usability journeys")
        return
    fake_serial.reset()
    base, _main = F.start_hub()
    script = (F.QC / "data/usability_browser.js").read_text(encoding="utf-8")
    try:
        browser.raw_page('<script>' + script + '</script>', base, seconds=100)
    finally:
        browser.kill()
    marks = [m[7:] for m in fake_serial.qc_marks if m.startswith("USABLE~")]
    t.ok(len(marks) >= 18, "every changed failure/recovery journey reported", marks)
    for mark in marks:
        key, _, value = mark.partition("=")
        t.eq(value, "true", key)
