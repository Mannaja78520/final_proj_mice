# help-friend-repos-1124 — Put Help + a main-page Help button into Face_Regonize and Photobooth
Owner: codex:11240915-1a99
Updated: 2026-11-24T09:18+07:00
Last commit: 1c2a087 (Mice handoff claim)

## User orders (Thai, 2026-11-24)
- cmsg_01R7BbYxaTb3Yv9YS3gQaaA3Q6QC2jUpeSUV6Yw8pqH9TK: "put facereg and photobooth into the friend's git now; the game: let me look first for a moment"
- cmsg_01R7BbYxaTb3Yv9YS3gQaaA32W8jHrzFH9jPqiqEZXH89j: "also put it on the main page in the facereg and photobooth apps, easy to click"
- cmsg_01R7BbYxaTb3Yv9YS3gQaaA3G1GZftdzWidxFYUeavAdkg: "let GPT do all of it, you are out of quota"
Standing PC approvals: cmsg_01R7BbYxaTb3Yv9YS3gQaaA39kL7igdPaE1F66ZxWq6meq, cmsg_01R7BbYxaTb3Yv9YS3gQaaA3GFKFwe31L9cSDhiS4Mbs2z.

## THIS IS THE USER'S OWN EXCEPTION to "never edit friend repos", for Face_Regonize and Photobooth ONLY
Allowed: ADD the help/ folder and ONE minimal Help button on each app's main page. Nothing else in their code.
NOT allowed: All-Jao-Games (HOLD, user wants to look first: do not touch, do not push). Their main branch, force-push, merging.

## Work (per repo; use a clean clone/worktree under E:\work, never their working tree if it has uncommitted changes)
1. Read-only first: git status, branch, remote, last commit. Back up (note commit + copy under mice_system\.local\backup).
2. New branch `add-mice-help` from the repo's default branch.
3. Copy the package: Face_Regonize <- docs/friend/reconize_help_package/help -> `help/` at repo root;
   Photobooth <- docs/friend/photobooth_help_package/help -> `help/` at repo root (packages are in mice_system main, PRs #245, #247).
   Commit: "Add MICE Help package (help/)".
4. Main-page Help button: read their frontend, reuse their own button style/classes, no new dependencies.
   Reconize: dashboard header (and login page if simple). Photobooth: organizer/admin main page and, only if it
   does not disturb the guest flow, a small Help on the start screen. Must work STANDALONE (no MiceHub): serve/link their
   own help/ files (least invasive way that works in their server); optionally also offer MiceHub http://127.0.0.1:8642/help#faces
   (#photobooth) when reachable. Say which you chose. Commit separately: "Add Help button to main page".
5. Test: the app still starts, the button opens the help and its images show; screenshot each main page with the button
   (light/dark if themed); LOOK at every screenshot. Gemini 4 may review (leads only).
6. Push: `git push -u origin add-mice-help` (no force). If refused / credentials needed, STOP and write exactly why here.
7. Also update docs/friend/friend_requests_all_2026-11-23.md in mice_system (our repo, new branch from main, draft PR,
   merge per standing approval cmsg_01R7BbYxaTb3Yv9YS3gQaaA3XEQcQQyoUgXwMT6wXgfeYv when green): say the Help is now in the
   friend repos on branch add-mice-help (+ commit ids) and the friend may merge it, and how the hub picks it up.
8. Update this file after EVERY step and push a WIP commit to branch claude/project-thread-181856 of mice_system.
   Never put keys/passwords/real data in git.

## Done when
Both friend repos have branch add-mice-help pushed (or the exact blocker is written here), screenshots checked,
our friend-request doc updated, nothing in All-Jao-Games touched, report in Thai in "Result" below.

## Doing now
Verify package bytes against source, back up clone bases and pending Face links, claim plan work, then prepare standalone Help integration.

## Done
- Took the task as codex:11240915-1a99 on detached Mice HEAD 683f59f (remote handoff branch).
- Reconciled clone branches. Face base e998b0e, package 3ea59d1, two pending UI edits and prior .vite5180.log. Photobooth base 858f0b6, package ee9e201, clean tree.

## Next
Serve the existing help packages through each frontend's Vite dev and production entry points. Use Face dashboard/login and Photobooth organizer. Test isolated from 8000/5173.

## Facts found
- Face frontend/vite.config.ts proxies /api to port 8000 by default. Isolated tests must override it or use a build with a separate backend. Face backend/app/main.py serves frontend/dist.
- Photobooth frontend/vite.config.ts supports PHOTOBOOTH_KIOSK_PORT. Production _mount_spa in backend/src/photobooth/main.py serves files in frontend/dist.
- Existing Face links target port 8642. Both apps must link to local /help/en.html.

## File status

| File | Change | State | Verification | Commit |
| --- | --- | --- | --- | --- |
| Mice: handoff/tasks/help-friend-repos-1124.md | Session and clone inventory | In progress | git diff --check | this checkpoint |
| Face: frontend/src/components/Layout.tsx | Existing Hub Help link, switch to standalone | Pending | Prior typecheck, browser not run | uncommitted |
| Face: frontend/src/pages/Login.tsx | Existing Hub Help link, switch to standalone | Pending | Prior typecheck, browser not run | uncommitted |
| Face: .vite5180.log | Inherited test output, preserve outside commit | Existing | not run | uncommitted |
| Face: frontend/vite.config.ts | Register Help serving/build plugin | Pending | not run | uncommitted |
| Face: frontend/vite.help.ts | Serve/copy the root help package | Pending | not run | uncommitted |
| Photobooth: frontend/vite.config.ts | Register Help serving/build plugin | Pending | not run | uncommitted |
| Photobooth: frontend/vite.help.ts | Serve/copy the root help package | Pending | not run | uncommitted |
| Photobooth: frontend/src/features/admin/components/AdminLayout.tsx | Organizer Help link | Pending | not run | uncommitted |
| Mice: docs/friend/friend_requests_all_2026-11-23.md | Record verified branches and Hub discovery | Pending | not run | uncommitted |

Package rows use clone names as prefixes.
| Face: help/en.html | Bundled guide or image | Committed | Source parity pending | 3ea59d1 |
| Face: help/help.json | Bundled guide or image | Committed | Source parity pending | 3ea59d1 |
| Face: help/img/en-dark-faces-open.webp | Bundled guide or image | Committed | Source parity pending | 3ea59d1 |
| Face: help/img/en-light-faces-open.webp | Bundled guide or image | Committed | Source parity pending | 3ea59d1 |
| Face: help/img/en-light-reconize-activities.webp | Bundled guide or image | Committed | Source parity pending | 3ea59d1 |
| Face: help/img/en-light-reconize-attendees.webp | Bundled guide or image | Committed | Source parity pending | 3ea59d1 |
| Face: help/img/en-light-reconize-cctv.webp | Bundled guide or image | Committed | Source parity pending | 3ea59d1 |
| Face: help/img/en-light-reconize-connect.webp | Bundled guide or image | Committed | Source parity pending | 3ea59d1 |
| Face: help/img/en-light-reconize-dashboard.webp | Bundled guide or image | Committed | Source parity pending | 3ea59d1 |
| Face: help/img/en-light-reconize-event-photos.webp | Bundled guide or image | Committed | Source parity pending | 3ea59d1 |
| Face: help/img/en-light-reconize-history.webp | Bundled guide or image | Committed | Source parity pending | 3ea59d1 |
| Face: help/img/en-light-reconize-import.webp | Bundled guide or image | Committed | Source parity pending | 3ea59d1 |
| Face: help/img/en-light-reconize-login.webp | Bundled guide or image | Committed | Source parity pending | 3ea59d1 |
| Face: help/img/en-light-reconize-pdpa.webp | Bundled guide or image | Committed | Source parity pending | 3ea59d1 |
| Face: help/img/en-light-reconize-people.webp | Bundled guide or image | Committed | Source parity pending | 3ea59d1 |
| Face: help/img/en-light-reconize-privacy.webp | Bundled guide or image | Committed | Source parity pending | 3ea59d1 |
| Face: help/img/en-light-reconize-recognition.webp | Bundled guide or image | Committed | Source parity pending | 3ea59d1 |
| Face: help/img/en-light-reconize-reports.webp | Bundled guide or image | Committed | Source parity pending | 3ea59d1 |
| Face: help/img/en-light-reconize-settings.webp | Bundled guide or image | Committed | Source parity pending | 3ea59d1 |
| Face: help/img/en-light-reconize-uploads.webp | Bundled guide or image | Committed | Source parity pending | 3ea59d1 |
| Face: help/img/en-light-reconize-video.webp | Bundled guide or image | Committed | Source parity pending | 3ea59d1 |
| Face: help/img/ja-dark-faces-open.webp | Bundled guide or image | Committed | Source parity pending | 3ea59d1 |
| Face: help/img/ja-light-faces-open.webp | Bundled guide or image | Committed | Source parity pending | 3ea59d1 |
| Face: help/img/th-dark-faces-open.webp | Bundled guide or image | Committed | Source parity pending | 3ea59d1 |
| Face: help/img/th-light-faces-open.webp | Bundled guide or image | Committed | Source parity pending | 3ea59d1 |
| Face: help/img/zh-dark-faces-open.webp | Bundled guide or image | Committed | Source parity pending | 3ea59d1 |
| Face: help/img/zh-light-faces-open.webp | Bundled guide or image | Committed | Source parity pending | 3ea59d1 |
| Face: help/ja.html | Bundled guide or image | Committed | Source parity pending | 3ea59d1 |
| Face: help/shots.json | Bundled guide or image | Committed | Source parity pending | 3ea59d1 |
| Face: help/th.html | Bundled guide or image | Committed | Source parity pending | 3ea59d1 |
| Face: help/zh.html | Bundled guide or image | Committed | Source parity pending | 3ea59d1 |
| Photobooth: help/en.html | Bundled guide or image | Committed | Source parity pending | ee9e201 |
| Photobooth: help/help.json | Bundled guide or image | Committed | Source parity pending | ee9e201 |
| Photobooth: help/img/en-dark-booth-capture.webp | Bundled guide or image | Committed | Source parity pending | ee9e201 |
| Photobooth: help/img/en-dark-booth-choose.webp | Bundled guide or image | Committed | Source parity pending | ee9e201 |
| Photobooth: help/img/en-dark-booth-decorate.webp | Bundled guide or image | Committed | Source parity pending | ee9e201 |
| Photobooth: help/img/en-dark-booth-delivery.webp | Bundled guide or image | Committed | Source parity pending | ee9e201 |
| Photobooth: help/img/en-dark-booth-review.webp | Bundled guide or image | Committed | Source parity pending | ee9e201 |
| Photobooth: help/img/en-dark-booth-start.webp | Bundled guide or image | Committed | Source parity pending | ee9e201 |
| Photobooth: help/img/en-dark-photobooth-open.webp | Bundled guide or image | Committed | Source parity pending | ee9e201 |
| Photobooth: help/img/en-light-booth-activity.webp | Bundled guide or image | Committed | Source parity pending | ee9e201 |
| Photobooth: help/img/en-light-booth-capture.webp | Bundled guide or image | Committed | Source parity pending | ee9e201 |
| Photobooth: help/img/en-light-booth-choose.webp | Bundled guide or image | Committed | Source parity pending | ee9e201 |
| Photobooth: help/img/en-light-booth-decorate.webp | Bundled guide or image | Committed | Source parity pending | ee9e201 |
| Photobooth: help/img/en-light-booth-delivery.webp | Bundled guide or image | Committed | Source parity pending | ee9e201 |
| Photobooth: help/img/en-light-booth-editor.webp | Bundled guide or image | Committed | Source parity pending | ee9e201 |
| Photobooth: help/img/en-light-booth-frames.webp | Bundled guide or image | Committed | Source parity pending | ee9e201 |
| Photobooth: help/img/en-light-booth-history.webp | Bundled guide or image | Committed | Source parity pending | ee9e201 |
| Photobooth: help/img/en-light-booth-profiles.webp | Bundled guide or image | Committed | Source parity pending | ee9e201 |
| Photobooth: help/img/en-light-booth-retention.webp | Bundled guide or image | Committed | Source parity pending | ee9e201 |
| Photobooth: help/img/en-light-booth-review.webp | Bundled guide or image | Committed | Source parity pending | ee9e201 |
| Photobooth: help/img/en-light-booth-sign-in.webp | Bundled guide or image | Committed | Source parity pending | ee9e201 |
| Photobooth: help/img/en-light-booth-start.webp | Bundled guide or image | Committed | Source parity pending | ee9e201 |
| Photobooth: help/img/en-light-booth-statistics.webp | Bundled guide or image | Committed | Source parity pending | ee9e201 |
| Photobooth: help/img/en-light-booth-system.webp | Bundled guide or image | Committed | Source parity pending | ee9e201 |
| Photobooth: help/img/en-light-booth-test.webp | Bundled guide or image | Committed | Source parity pending | ee9e201 |
| Photobooth: help/img/en-light-booth-unpaired.webp | Bundled guide or image | Committed | Source parity pending | ee9e201 |
| Photobooth: help/img/en-light-photobooth-open.webp | Bundled guide or image | Committed | Source parity pending | ee9e201 |
| Photobooth: help/img/ja-dark-photobooth-open.webp | Bundled guide or image | Committed | Source parity pending | ee9e201 |
| Photobooth: help/img/ja-light-photobooth-open.webp | Bundled guide or image | Committed | Source parity pending | ee9e201 |
| Photobooth: help/img/th-dark-photobooth-open.webp | Bundled guide or image | Committed | Source parity pending | ee9e201 |
| Photobooth: help/img/th-light-photobooth-open.webp | Bundled guide or image | Committed | Source parity pending | ee9e201 |
| Photobooth: help/img/zh-dark-photobooth-open.webp | Bundled guide or image | Committed | Source parity pending | ee9e201 |
| Photobooth: help/img/zh-light-photobooth-open.webp | Bundled guide or image | Committed | Source parity pending | ee9e201 |
| Photobooth: help/ja.html | Bundled guide or image | Committed | Source parity pending | ee9e201 |
| Photobooth: help/shots.json | Bundled guide or image | Committed | Source parity pending | ee9e201 |
| Photobooth: help/th.html | Bundled guide or image | Committed | Source parity pending | ee9e201 |
| Photobooth: help/zh.html | Bundled guide or image | Committed | Source parity pending | ee9e201 |

## Result
(Codex: write branch names, commit ids, changed files/lines, screenshot paths, push result)
