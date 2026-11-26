---
date: 2026-11-26
kind: improved
prs: -
area: qc
title: QC, builds and measurement scripts now run at low priority so the PC stays usable
---
Problem: a full QC run left the PC laggy and hard to use, and other programs are open in real use.
Method: QC (runner, workers, Edge launched through PowerShell, subprocesses), the exe build wrapper and our measurement scripts run at below-normal CPU, low disk and low memory priority inside a job object with a CPU cap and a memory limit. A governor watches the whole machine every 2 seconds and starts no new check while CPU is above 75%, free RAM below 6 GB or the GPU is busy (one check per pool always runs, nothing is stopped or killed). Off: MICE_POLITE=0, --exact-timing or "polite": false (the tool says it runs at normal priority). Optional stronger yield in qc/data/qc_speed.json. The real hub, Voice and Faces are never touched.
Numbers: see docs/experiments/experiment-records.md (2026-11-26 polite mode).
