---
name: public-repo-rules
description: The repo is public: what must never be committed
metadata:
  type: feedback
---

No API keys, real passwords, thesis files, model files, audio/video/private data, the friend's code (Face_Regonize, All-Jao-Games, Photobooth are the friend's repos: read, git pull --ff-only, run only; list their problems for the user to send). Factory defaults live in tracked *.default.json; customer-changed values in a gitignored local file. This memory folder is public too: tools/memory.py check refuses keys and e-mail addresses.

**Why:** user 2026-11-20 after a credentials review.
**How to apply:** if unsure, leave it out and say so.
