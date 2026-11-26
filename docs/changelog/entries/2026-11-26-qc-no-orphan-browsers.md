---
date: 2026-11-26
kind: fixed
prs: -
area: qc
title: QC no longer leaves headless browsers running after a crash, Ctrl+C or a timed-out check
---
Problem: 119 headless Edge processes from QC runs stayed alive on the PC (up to 67 h old, about 4 GB of memory) after killed runs, crashes and timed-out checks.
Method: the runner joins a Windows job object that kills everything it started when it ends (even if killed hard); Ctrl+C and SIGTERM end the run cleanly; every run starts by killing browsers whose owner is gone or older than 6 h (never a live run's); a full run fails if it leaves a browser behind. Proven with real processes in check_no_orphans.
Numbers: a hard-killed runner now takes its child and a detached grandchild with it within 15 s (was: they lived on).
