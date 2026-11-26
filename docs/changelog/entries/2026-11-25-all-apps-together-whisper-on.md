---
date: 2026-11-25
kind: improved
prs: 251, 259
area: performance
title: All apps together: Whisper on GPU, shared priority scheduler
---
Problem: Voice, face recognition and cameras competed for the GPU; live work could wait behind background work.
Method: Whisper back on GPU, early face lookup on /ask; one shared scheduler (live jumps the queue, background yields, aging prevents starvation), classes and limits in config/scheduler.json.
Numbers: see docs/experiments/2026-11-25_all_apps_together.md
