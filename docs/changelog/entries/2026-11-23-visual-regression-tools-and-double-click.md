---
date: 2026-11-23
kind: improved
prs: 215, 216, 214
area: qc
title: Visual regression tools and double-click starters
---
Problem: Automated checks missed visual bugs; starting each app needed a command line.
Method: Added screenshot compare (old vs new), a numeric 3D-vs-URDF check and a language-leak check; launchers in main_python/launchers use the freshly built exe.
