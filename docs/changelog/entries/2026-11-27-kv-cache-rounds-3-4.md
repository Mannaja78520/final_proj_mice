---
date: 2026-11-27
kind: improved
prs: -
area: ai
title: KV cache measured again: q4_0 and a smaller context do not pay off, q8_0 stays
---
Problem: could the local AI's KV cache shrink below q8_0 without hurting answers?
Method: q4_0 and a smaller context were measured beside the Voice helper and a face-model loop on 118 cases; q4_0 changed 40 answers and some became wrong, and a smaller context saves only 1.5 % of the model's GPU memory, so nothing was changed.
Numbers: docs/experiments/experiment-records.md (2026-11-27 KV cache rounds 3-4).
