---
date: 2026-11-27
kind: fixed
prs: -
area: qc
title: QC: the voice and face helper checks wait until the helper answers instead of for a fixed few seconds
---
Problem: full QC runs failed in different voice and face checks each time (the helper took longer than a fixed 15 s or 6 s to start when many checks started together, and copying the shared sequences folder crashed when another check deleted a file at that moment); each passed alone.
Method: the voice and face helper checks now wait while the helper process is alive until it answers (a dead helper ends the wait at once), and the data-isolation copy skips a file that vanished mid-copy (tested with a vanishing file, break proven).
