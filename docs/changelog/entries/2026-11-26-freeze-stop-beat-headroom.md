---
date: 2026-11-26
kind: fixed
prs: -
area: qc
title: check_freeze_stop: more headroom for the page's beats in a busy run
---
Problem: check_freeze_stop failed in busy full runs (the hub stopped the show because a busy page missed two beats) and passed alone.
Method: the hub's beat timeout in that part of the check is 6 s instead of 2.5 s (beats come every 1 s) and the page waits past it, so staying alive still proves it really kept beating.
Numbers: green twice alone; with the timeout set below the beat interval the check fails, as it should.
