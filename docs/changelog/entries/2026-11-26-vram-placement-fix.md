---
date: 2026-11-26
kind: fixed
prs: -
area: voice
title: The GPU planner now puts the model that saves the most time on the GPU, and waits for a busy model instead of moving to the CPU
---
Problem: measured 2026-11-26 on the PC: at 6 GB the small hearing model loaded first and kept the GPU while the Thai one (saves 2.5 s per visitor) ran on the CPU; at 10 GB a busy local AI sent a newcomer to the CPU, so a bigger card had fewer models on the GPU than 8 GB.
Method: an equally important model is replaced only by one that saves more time than everything it pushes out; a busy model is asked again until its idle moment (8 s, config) before the newcomer falls back to the CPU; the Thai hearing size uses the measured saving (2877 ms CPU vs 422 ms GPU).
Numbers: a QC check now walks 2 to 16 GB in 256 MiB steps and fails if a bigger card ever saves less time. Re-measurement: docs/perf_vram_2026-11-26.md.
