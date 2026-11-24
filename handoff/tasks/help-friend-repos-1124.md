# help-friend-repos-1124 — Put Help + a main-page Help button into Face_Regonize and Photobooth
Owner: gpt-codex (Claude out of quota; Claude reviews after reset)
Updated: 2026-11-24 02:20
Last commit: (none)

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
Not started.

## Result
(Codex: write branch names, commit ids, changed files/lines, screenshot paths, push result)
