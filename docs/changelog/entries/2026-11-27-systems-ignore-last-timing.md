---
date: 2026-11-27
kind: fixed
prs: -
area: qc
title: System map no longer lists the git-ignored qc/last_timing.json
---
Problem: the system map listed qc/last_timing.json, a git-ignored file that exists only on a PC that ran QC, so docs/systems/qc.md differed between the PC and a clean checkout and GitHub quick-qc failed.
Method: last_timing.json joins the excluded names in docs/systems.json, like last_progress.json.
