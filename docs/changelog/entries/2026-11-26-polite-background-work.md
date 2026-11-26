---
date: 2026-11-26
kind: improved
prs: -
area: qc
title: QC, builds and measurement scripts now run at low priority so the PC stays usable
---
Problem: a full QC run left the PC laggy and hard to use.
Method: QC (runner, pool workers, Edge launched through PowerShell, subprocesses), the exe build wrapper and our measurement scripts lower themselves to below-normal CPU, low disk and low memory priority; the QC job is capped at 80% of the machine and leaves 4 logical CPUs free. Switch off with MICE_POLITE=0, --exact-timing or "polite": false in qc/data/qc_speed.json (the tool says it runs at normal priority). The real hub, Voice and Faces are never touched.
Numbers: see docs/experiments/experiment-records.md (2026-11-26 polite mode).
