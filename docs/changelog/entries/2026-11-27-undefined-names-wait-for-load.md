---
date: 2026-11-27
kind: fixed
prs: -
area: qc
title: check_no_undefined_names judges a page after it has loaded, not after a fixed 7 seconds
---
Problem: in a busy full run the check judged a page after a fixed 7 seconds, before it had loaded, and reloaded it, so its "judged on its first load" assertion failed (green alone).
Method: it now waits until every page has loaded (up to 25 s) and then 2 s for the probes; the assertions are unchanged and a failure now prints what each page said.
Numbers: green alone (17.5 s); 8 copies at once pass 5 of 8 (the others fail only on the page-load time of 64 pages at once).
