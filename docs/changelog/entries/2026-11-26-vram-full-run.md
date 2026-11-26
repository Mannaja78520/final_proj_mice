---
date: 2026-11-26
kind: improved
prs: -
area: voice
title: GPU-memory planner measured on the real PC: card sizes 2 to 12 GB and spill vs swap vs hybrid
---
Problem: nobody knew how the planner behaves on a small card, or whether moving jobs to the CPU or taking turns on the GPU is better.
Method: ran the whole voice helper on this PC with a pretend card of 2, 4, 6, 8, 10 and 12 GB and the whole card, with the face app, camera and background jobs running, and compared three ways of using the CPU.
Numbers: hearing takes about 4 s with models on the CPU (2 to 6 GB) and about 1 s from 8 GB; the planner as shipped wins; at 6 GB it keeps the wrong hearing model on the CPU; the "hybrid" way makes hearing 3 times slower. See docs/perf_vram_2026-11-26.md.
