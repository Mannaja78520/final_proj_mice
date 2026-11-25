"""A browser page that reports nothing explains itself.

2026-11-26: about one full run in three, one browser check ends in "QC SILENT: the
page reported nothing in 175-478 s" and passes alone; load alone does not reproduce
it and relaunching does not cure it. browser.diagnose() prints one line when it
happens: was the driver page fetched from the hub, did the browser log in, did it
load scripts, when was its last request, did Edge log errors or leave a crash dump,
how many browser processes are alive. This proves each part of the line.
"""
import tempfile
import time
from pathlib import Path

import qc as F

AREA = "tooling"
TITLE = "a silent browser page is diagnosed: fetched? logged in? errors? crash dump?"


def run(t):
    import browser
    t0 = time.time() - 30
    prof = Path(tempfile.mkdtemp(prefix="qc_diag_")) / "profile_1"
    (prof / "Crashpad" / "reports").mkdir(parents=True)
    last = {"prof": str(prof), "page": "_qcdriver_9_9.html", "t0": t0}

    none = browser.diagnose(last, requests=[], running=0)
    t.ok("page GET NO" in none and "login POST NO" in none and "last hub request never" in none,
         "no request at all says the page was never fetched", none)

    reqs = [(t0 + 1, "GET", "/studio/_qcdriver_9_9.html", 200),
            (t0 + 2, "POST", "/api/login", 200),
            (t0 + 2, "GET", "/studio/app.js", 200),
            (t0 + 3, "GET", "/mice.css", 200),
            (t0 + 4, "POST", "/api/qc/mark", 503),
            (t0 - 100, "GET", "/studio/_qcdriver_9_9.html", 200)]      # an older page: not ours
    got = browser.diagnose(last, requests=reqs, running=7)
    t.ok("page GET yes (200)" in got and "login POST yes" in got
         and "2 script/style requests" in got and "1 other hub calls" in got
         and "browser processes 7" in got,
         "a fetched, logged-in page is described, older pages are ignored", got)

    (Path(str(prof) + ".edge.log")).write_text(
        "[0101/000000:ERROR:fallback_task_provider.cc:126] Every renderer should have\n"
        "[0101/000001:ERROR:network_service.cc:99] net::ERR_CONNECTION_RESET on x\n"
        "[0101/000002:INFO:ok.cc:1] fine\n", encoding="utf-8")
    (prof / "Crashpad" / "reports" / "a.dmp").write_bytes(b"x")
    got = browser.diagnose(last, requests=reqs, running=1)
    t.ok("ERR_CONNECTION_RESET" in got and "fallback_task_provider" not in got,
         "Edge's own log errors are shown and the known noise line is not", got)
    t.ok("crash dumps 1" in got, "a crash dump is counted", got)

    src = (F.QC / "lib" / "browser.py").read_text(encoding="utf-8")
    t.ok("print(diagnose()" in src and "--log-file=" in src,
         "QC SILENT prints the diagnosis and every browser writes a log file")
    qsrc = (F.QC / "lib" / "qc.py").read_text(encoding="utf-8")
    t.ok("HUB_REQUESTS.append" in qsrc, "the QC hub remembers every request")
