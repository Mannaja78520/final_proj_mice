---
date: 2026-11-26
kind: fixed
prs: -
area: voice
title: Voice idle unload no longer interrupts a model that is still loading
---
Problem: measured on the real PC, the idle unload could fire while the local model was still loading and then said "asleep" with nothing in memory.
Method: it now waits for loading to finish, counts idle time from then, does nothing when no model is loaded, and records how much GPU memory an unload freed.
Numbers: about 4 GB of 5.1 GB freed after 30 s idle (test setting); the first answer after the sleep took 11.8 s, the next 0.4 s. See docs/experiments/experiment-records.md.
