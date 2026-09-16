---
name: web-page-check
description: Drive one web page of this project in a real browser from a throwaway script - no full QC run needed
---

# Web page check — one screen, real browser, no gate

Use when building or changing any page the hub or a module serves and you want
to SEE it driven (clicks, fetch stubs, rendered rows) without running the whole
QC suite. This is the same machinery `qc/run_qc.py` uses; nothing new to install.

## Recipe

```python
import sys
sys.path.insert(0, r"E:\final_proj\mice\code\.staging\qc")
sys.path.insert(0, r"E:\final_proj\mice\code\.staging\qc\lib")

import browser, fake_serial, qc as F

base, main = F.start_hub()          # staging hub on a free port, logged out
# ...or reuse an already-running hub: base = "http://127.0.0.1:8642"

DRIVER = """
<script>
function done(s){ qcMark("RESULT " + s); qcMark("done"); }
setTimeout(function(){ /* drive the page, then */ done("rows=1"); }, 2000);
</script>
"""
browser.raw_page("<h1>wrapper</h1>" + DRIVER, base, seconds=20)

for m in fake_serial.qc_marks:
    print(m)                        # every qcMark() the page made
browser.kill()
```

## Rules that keep it honest

- `qcMark(...)` is how the page reports; results land in
  `fake_serial.qc_marks`. Always end the driver with `qcMark("done")`.
- Assert on what reached the module (`fake_serial.wire`, `fake_wifi.MODULE.cmds`),
  never on what the page says about itself.
- ONE QC-driven process at a time — never while a gate, promote or another
  check run is live (they share the fake serial port and the marks list).
- Headless Edge must exist; `browser.available()` says so. `browser.kill()`
  cleans up if a run leaves a browser behind.
- Login-gated pages: POST `/api/login` JSON `{"user":"manny","password":"12345678"}`
  to the hub first (demo creds; boards ship manny/12345678 too).

## When NOT here

A change that should be guarded forever belongs in `qc/checks/check_*.py`
following the same pattern — this skill is for looking, not for landing.
