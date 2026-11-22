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

## Newcomer test, 2026-11-21 (read-only; we edited nothing of theirs)

Someone who knows nothing about the project opened each friend app. For the friend, most important first:

**Face_Regonize (5173)**
1. Phone (390 px) is broken: the sidebar stays ~255 px wide, so content gets ~135 px and the People table is cut off on every page after login. Collapse the sidebar under ~768 px.
2. Unknown URL (`/nonexistent`) shows an empty page - add a "page not found" screen with a way back.
3. The whole UI is English (only people's names are Thai). Staff are Thai: Thai labels, or a language switch.
4. Login page shows "Demo login: admin / admin123" to everyone; "Local Video Experiment (Admin experiment)" sits in the normal menu.
5. Chrome 75 (Android TV): `?.`, `??`, `replaceAll` are everywhere (CameraNode 24, Recognition 14) and Vite has no `build.target`, so the bundle needs Chrome 87+. Set `build.target: 'chrome70'` (or use @vitejs/plugin-legacy) if the TV must open it.

**All-Jao-Games (4173)**
1. The server is not running after a PC start; the hub starts it from /app/all-jao/ (we have not re-tested that auto-start).
2. Admin lists 4 games (incl. quiz "รู้ใจแค่ไหน") but the player page offers only 3.
3. Username placeholder reads "xxxxxxx"; the tagline mixes English and Thai; one 404 in the console on first load; README points to `D:\All Jao Games\data`.
4. Chrome 75: one spot, `motion.js:78` `tab?.closest(...)`.

**Photobooth (5191)**
1. A fresh start shows "Kiosk not paired" (401 on /api/booth/frames) on Admin and Booth until `run-dummy.ps1 -PairOnly` is run. A first-time user is stuck; the page should say how to pair, or pair itself on localhost.
2. No Thai text at all, and the first page shows technical words ("API 1 - dummy - database 0012_policy_per_event - code 64724759c918").
3. `/nope` shows the home page instead of 404; port 8113 `/` answers "not found".
4. Chrome 75: same `?.` / `??` / `replaceAll` problem as Face_Regonize.

Not tested (needs a person or hardware): playing a game to the end and the prize, phone over the LAN, photo capture and QR.

**Language (all three apps, 2026-11-22)**
The hub now has Thai / English / Chinese / Japanese and adds `?lang=th|en|zh|ja` to every link it opens into your app. If you can, read `lang` from the address (and remember it) and show that language; any app that ignores it keeps working as before.
