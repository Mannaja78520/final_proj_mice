---
date: 2026-11-26
kind: fixed
prs: -
area: qc
title: check_voice_bench waits for the helper to answer instead of 15 s
---
Problem: check_voice_bench failed in a full run at low priority: the real Voice helper needed more than the fixed 15 seconds to start listening (green alone in 58 s).
Method: the check now waits up to 60 s for the helper to answer and stops at once if the process died.
Numbers: green alone; with the wait cut to 0.01 s the check fails as it should.
