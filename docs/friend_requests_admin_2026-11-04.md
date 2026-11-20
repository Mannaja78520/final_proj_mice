# Asks for the friend: one admin story across the hub and the apps (2026-11-04)

Read from their code (HEAD: Face_Regonize e8d4a22, Photobooth 858f0b6, All-Jao-Games f9e8ff4). We edit nothing of theirs.
Goal: the hub's admin login is the front door; each app also accepts a hub-issued credential.

1. Face_Regonize: set a real `JWT_SECRET` in .env (config.py:104 has a guessable dev default) and change the default
   admin/admin123 (config.py:108-109). Nothing else: its Bearer JWT already works for the hub (auth.py:48, deps.py:52-61).
2. Photobooth: add a second authenticator at the existing AdminAuthenticator port (admin_gate.py:38-49) that accepts
   `Authorization: Bearer <service token>` from an env var, localhost only, no cookie/pairing/CSRF. Today the hub cannot
   log in for it (cookie + device pairing + CSRF, admin_gate.py:52-69; password only by CLI, cli.py:318).
3. All-Jao-Games: admin is `admin/1234` checked in the browser (script.js:143-152), so it guards nothing. Ask: take the
   admin flag from the hub page that serves the game (/play/all-jao/), or accept that the game has no real admin.

Our side (no wait): partners.json login kinds jwt (done) + bearer; per-app secrets in a git-ignored local file;
hub shows an app's admin button only to hub admins.
