# Studio Distance: shoulder to elbow and shoulder to hand

Owner: claude:10210423-30cf (PC session)
Updated: 2026-10-21 09:30 (Bangkok)
Branch: claude/project-thread-5ylnwy
Last commit: c9b8ae3 (feature); branch head see `git log -1`
Plan: A45-26

## Goal
Add distances shoulder->elbow and shoulder->hand, left and right separately, keeping the existing distances.

## Done
- `app_parts/distances.js`: point kinds are a table (`DIST_POINTS`); shoulder = the shrug anchor
  both shoulder servos turn about, read live (no fkPoints, so WAIST/SHRUG are not disturbed).
- `distances.json`: 4 new pairs (L/R shoulder to elbow, L/R shoulder to hand); the old 4 kept.
- Tooltip (`html_parts/view.html`), help (`main_python/web/help/parts/accounts.html`), web built, Studio patch 0056.
- `check_studio_distances`: all 8 against endpoints found another way (parent of joint group 0/4),
  RIG lengths, bent + asymmetric pose, WAIST/SHRUG, rebuilt longer arm, label overlap, missing model.
  26/0; sabotage 4/4 caught.

## Next
1. After the PR merges: on the PC, pull main into `E:\final_proj\mice\code` (keep its dirty files),
   rebuild the exe (`python -m PyInstaller --clean --noconfirm MiceHub.spec`), restart the hub,
   open Studio, press Distances, look at the 8 lines. Then delete this file.

## Blocked
- Nothing. Label overlap was checked only in the QC window size, not on a phone screen by eye.
