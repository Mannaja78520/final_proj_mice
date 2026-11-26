---
date: 2026-11-25
kind: improved
prs: 252, 253, 258, 260, 261, 262, 264, 265, 268
area: qc
title: QC faster and steadier on the PC
---
Problem: Full QC took 1524 s on the PC and failed randomly under parallel load (checks overwrote each other's saves, the QC hub met the real hub).
Method: Per-check timing, watchdog with hard timeout, build caches, a PC-wide run lock, timing-sensitive checks moved into the pool, each check gets its own projects/sequences/shows copy, QC hub kept away from the real hub.
Numbers: Full QC 1524 s to 832 s; Video LAN driver check 233 s to 22 s.
