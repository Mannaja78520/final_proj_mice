---
date: 2026-11-26
kind: new
prs: -
area: tools
title: PRs with the auto-merge label now merge themselves once the quick checks pass
---
Problem: the owner had to type a merge approval for every PR.
Method: label `auto-merge` on a ready PR; GitHub Actions squash-merges it when the light CI check `quick-qc` passes. Only owner-added labels on same-repo branches count.
