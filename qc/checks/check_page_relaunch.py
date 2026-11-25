"""A browser page that never reports gets one fresh browser, not a 4-minute wait.

2026-11-25/26: in about one full run in three a different browser check failed in
the crowd with "QC SILENT: the page reported nothing in 190-478 s" (marks list
empty, browser alive) and passed when re-run alone. qc/lib/browser.py now waits
FIRST_REPORT_SECS for any report and, if there is none, restarts the browser once
with a new profile; the page is then judged exactly as before. This proves the
rule with a stub launcher (no real browser): a report in time means no relaunch,
silence means exactly one relaunch on a fresh profile, and a page that stays
silent is still given up on after that one.
"""
import qc as F

AREA = "tooling"
TITLE = "a silent browser page is relaunched once on a fresh profile"


def run(t):
    import browser
    import fake_serial

    calls = []
    saved = (browser.kill, browser._wait_until_gone, browser._wait_for_done, browser._rmtree)
    browser.kill = lambda tag=None: None
    browser._wait_until_gone = lambda *a, **k: None
    browser._rmtree = lambda *a, **k: None
    waited = []
    browser._wait_for_done = lambda seconds, grace=150, start=None: waited.append(start) or True
    try:
        def say_at(n):
            def launch(prof):
                calls.append(prof)
                if len(calls) >= n:
                    fake_serial.qc_marks.append("hello")
            return launch

        start = len(fake_serial.qc_marks)
        browser._launch_and_wait(say_at(1), "P", 5, start, first_report=0.5)
        t.ok(calls == ["P"], "a page that reports in time is launched once", repr(calls))

        del calls[:]
        start = len(fake_serial.qc_marks)
        browser._launch_and_wait(say_at(2), "P", 5, start, first_report=0.5)
        t.ok(calls == ["P", "P_again"],
             "a silent page is relaunched once, on a fresh profile", repr(calls))

        del calls[:]
        start = len(fake_serial.qc_marks)
        browser._launch_and_wait(say_at(99), "P", 5, start, first_report=0.5)
        t.ok(len(calls) == 2, "and never more than once", repr(calls))
        t.ok(len(waited) == 3, "every case still waits for the page's own done mark", repr(waited))
    finally:
        browser.kill, browser._wait_until_gone, browser._wait_for_done, browser._rmtree = saved
        del fake_serial.qc_marks[:]

    t.ok(browser.FIRST_REPORT_SECS >= 60,
         "the first-report limit is generous (healthy pages report in seconds)",
         str(browser.FIRST_REPORT_SECS))
    src = (F.QC / "lib" / "browser.py").read_text(encoding="utf-8")
    t.ok(src.count("_launch_and_wait(") >= 3,
         "page() and raw_page() both go through it")
