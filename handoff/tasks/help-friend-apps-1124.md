# help-friend-apps-1124 — Detailed in-app Help (real screenshots) for All-Jao, Reconize, Photobooth
Owner: codex:11240637-1d82 (Claude reviews). Branch: claude/project-thread-181856
Updated: 2026-11-24 06:43 +0700
Last commit: 2e93bdf (claim)
Plan: system A59-1

## Goal (user, 2026-11-23 23:34, Thai)
"Game app, Reconize: put pictures from the REAL app into their Help too. I said detailed Help, not only
the hub page, because it is Help specific to that app. When an app is added, its Help is added."
Today apps/all-jao/help, apps/faces/help, apps/photobooth/help only show 1-2 hub-side shots (launcher,
game grid). Make each a DETAILED step-by-step guide with real screenshots taken INSIDE the friend app itself:
every main screen / game / tab, in order, each picture matching its step text.

## Rules
- NEVER edit the friend repos (Face_Regonize, All-Jao-Games, Photobooth). Everything lives in OUR repo
  under apps/<id>/help (format from PR #233: help.json, th/en/zh/ja.html, shots.json, img/<lang>-<light|dark>-<name>.webp).
- Run the friend apps on the PC to capture (standing PC approvals: pull ff-only, build, start/stop hub and apps,
  tests, bash; start Face_Regonize via Start Reconize.vbs if 8000 is down; All-Jao: node server.cjs port 4173,
  through /play/all-jao/). Reconize login admin/admin123 (factory default, test only). No real people's faces,
  names or photos in screenshots: use dummy/test data; public repo, no keys/private data.
- Capture tooling: extend tools/help_shots.py + shots.json (steps: click/eval/clip/native) so a new app brings its
  own recipe. Native apps keep their own language/palette: say so under the image (as in #233) and state which
  languages the app itself offers; take shots in each language the app supports, else one set + text in 4 langs.
  Light/dark: take both where the app has a theme, else one set.
- Text in all 4 languages (th/en/zh/ja), plain words for non-engineers (business/art staff), technical detail
  only behind the existing "tech" marker. Cover: what the app is for, starting it from the hub, each screen/game
  step by step, settings, what to do when it does not start / shows an error, how it links with the hub
  (Voice+Face greeting, Games+Prize machine).
- Add-app must still bring/remove the Help (check_app_help). Keep Help parity rule (Rule 11), run `python tools/build_web.py`.
- Look at EVERY screenshot yourself and compare with its text; ask Gemini 4 (medium) to review picture vs text; findings are leads.
- Ask friend nothing; if the app needs something from them, append to docs/friend/friend_requests_all_2026-11-23.md.

## Added 2026-11-23 23:36 (user, cmsg_01R7BbYxaTb3Yv9YS3gQaaA3UpcFi8qSpSKyV15CmSFPMp, Thai: "we make this and can upload it into the friend's repo; make a handoff for Reconize's help")
Extra deliverable, Reconize ONLY (user's own exception): a READY-TO-DROP Help package under
docs/friend/reconize_help_package/ : the files exactly as they must sit in the Face_Regonize repo
(its own `help/` folder in our PR #233 format: help.json, th/en/zh/ja.html, img/), a README.md (Thai + English)
saying where each file goes, the 3-5 short steps to drop it in, how the hub then picks it up
(hub_api_help.py reads {partner folder}/help first, then our apps/faces/help), and how to re-take the pictures
(tools/help_shots.py recipe). Keep the package and apps/faces/help identical (one source, a script or QC check
that they match). Do NOT write into the Face_Regonize folder yourself and do not change its code; the user (or a
person they name) uploads it. If you ever must touch it: back up first.

## Steps
1. List real screens of each app (read their running UI, not the plan). Write the list in "Facts found".
2. Recipes in shots.json + capture; view all images.
3. Write th/en/zh/ja guides per app (detailed, step by step).
4. QC: `python qc/run_qc.py --quiet app_help help_links help_topics help_groups help_drift docs page_frame` then full QC once
   (cloud-only env failures are the known ones). Draft PR from the branch, merge when green per standing approval
   cmsg_01R7BbYxaTb3Yv9YS3gQaaA3XEQcQQyoUgXwMT6wXgfeYv, then rebuild MiceHub.exe on the PC (clean main worktree, not while another build runs),
   restart hub, retest /help in 4 languages.
5. Update this file + push a WIP commit after EVERY step. Report in Thai to the user at the end.

## Doing now
Step 2: extend capture recipes and capture native screens in isolated demo instances. Add native image resolution, Help parity and QC in the same checkpoint if needed.

## Done
- Read handoff, task and project workflow. Clean task tree at 7f8b1b3.

- Opened all three apps in Edge against scratch databases. Inventory recorded below.

## Next
- Capture and view each screenshot, then write and translate its matching step.

## Blocked
- None confirmed yet.

## Facts found
- PR #233 (merged) made per-app Help: apps/<id>/help, hub_api_help.py, check_app_help.
- Partners are hidden when not installed: run the hub from mice_system\dist (parent folder holds Face_Regonize, All-Jao-Games).

- Reconize: Login, Dashboard, People, Face Recognition, Attendees, Activities, CCTV/Camera Node, Connect, Import Participants, Upload History, Recognition History, Reports, PDPA, Event Photos, Settings, Local Video Experiment and Privacy Policy. Native English.
- All-Jao: landing, game grid, wheel, memory, claw and quiz in game navigation. The grid changes with restored session state. Native Thai with English headings.
- Photobooth: unpaired notice, paired Admin sign in, Event Profiles and editor, Frames, Test booth / TV, History, Statistics, Activity log, Retention and System. Native English. Need activate a dummy event for guest flow.
- Scratch processes: backend/frontend Reconize 8000/5173, All-Jao 4173, Photobooth Dummy 8111/8113. No fake Hub or PyInstaller ran. Original app repos untouched.

## File status
| File | Change | State | Verification | Commit |
|---|---|---|---|---|
| handoff/tasks/help-friend-apps-1124.md | claim and next step | active | diff inspected | this checkpoint |
