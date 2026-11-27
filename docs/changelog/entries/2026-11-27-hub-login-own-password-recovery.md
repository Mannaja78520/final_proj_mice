---
date: 2026-11-27
kind: new
prs: -
area: hub
title: The hub ships admin / admin123, asks you to choose your own password, and has a recovery code and a reset for a forgotten one
---
Problem: dist/hub_password.txt, an old random hub password in plain text, had been committed to the public repo, and a forgotten password had no way back except deleting a file by hand.
Method: the shipped login is the tracked main_python/hub_login.default.json (admin and super_admin, admin123); a changed password lives only as a salted hash in the git-ignored hub_auth.json. The first login on the shipped password opens a plain "choose your own password" box (skippable with Remind me later). Choosing one shows a recovery code once (only its hash is kept; it works once and is replaced). "Forgot password?" on the login box takes name, code and a new password, with a growing lockout per source and for everyone. "Reset Hub Password.bat" puts the shipped logins back, and only works on the hub PC (it edits the local file; there is no network route). The plain-text password file is no longer written and an old one is deleted. Help in four languages.
Numbers: check_hub_login (77 asserts, 10 breaks caught) and check_hub_login_page (real browser at 360 px, 20 asserts); the old committed password counts as leaked.
