---
date: 2026-11-26
kind: new
prs: -
area: voice
title: The Voice helper frees GPU memory when idle and wakes on the next question
---
Problem: the Voice helper kept about 5.4 GB of the 12 GB graphics card even when nobody had asked it anything for hours, which makes CAD and the desktop stutter.
Method: after idleUnloadMinutes (15, 0 = never) without a request its models are unloaded from GPU memory (the process keeps running); the next question loads them again with a "warming up" status and the wake-up cost is kept for /health. Never during a question or in presence/greeter mode. Optional yieldVramWhen (for example SLDWORKS.exe) unloads after one minute while such a program runs.
Numbers: pending a measurement on the real helper (expect about 5.4 GB freed): tools/voice_idle_measure.py.
