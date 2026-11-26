---
date: 2026-11-26
kind: improved
prs: -
area: docs
title: Friend request: the face backend's video scheduler re-reads a 6.4 MB file 8 times a second
---
Problem: the friend's face backend kept one thread busy (about 29% of a core) even with no job queued.
Method: py-spy on the running backend found the video scheduler parsing a 6.4 MB state file about 8 times a second; the cause, numbers and a one-time fix are in the friend request list (item 18), measured by stopping and restarting the backend for 5 minutes.
Numbers: stopping it did not change the PC's lag probes, so it is not the cause of the slowness; see handoff/tasks/lag-diagnosis-1126.md.
