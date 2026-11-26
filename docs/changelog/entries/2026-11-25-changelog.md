---
date: 2026-11-25
kind: new
prs: -
area: agents
title: Every change is now written in a short patch-notes log
---
Problem: Nothing recorded per change which part changed, why, and by what method, so writing the project report meant digging through PRs.
Method: One small entry file per change in docs/changelog/entries/ (no shared file, so parallel agents never clash); docs/CHANGELOG.md is generated from them; a QC check fails a branch that changes code without an entry.
Numbers: none. Older entries (#200-#268) are backfilled from PR titles only.
