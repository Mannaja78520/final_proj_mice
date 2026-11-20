# Make every app easy for non-engineers

Owner:
Updated: 2026-11-20 12:11 +0000
Branch: <branch, or main>
Last commit: <sha>
Plan: <plan ids, e.g. A45-11>

## Goal
<the user's ask, in their words if possible>

## Doing now
<written and pushed BEFORE each step: what you are about to do, the files, the approach>

## File status
Baseline: <starting SHA; reconcile owned commits, working diff and untracked files>

| File | Change | State | Verification | Commit |
| --- | --- | --- | --- | --- |
| `<repo/relative/path>` | <short change> | pending | not run | uncommitted |

<One latest row per owned source/generated/test/config/doc file, including additions,
deletions and renames. Use exact paths; link evidence and label quick/full or
simulated/hardware. Do not attribute other owners' edits. No edits: say so.
For this handoff file itself, Commit may be `this checkpoint`.>

## Facts found
- <file:line - what it does / why it matters; so the next AI does not read it again>

## Done
- <what landed, with PR or commit and how it was verified>

## Next
1. <the next concrete step, with the command if there is one>

## Blocked
- <what it waits on: robot, user account, a person, a decision; or "nothing">

## Doing now
Nothing: round 2 landed (PR #135-#140). Waiting only on the PC Android-VM session.

## Done
- Mice.Words (shared/web/mice-ui.js): one table turns browser error text into plain sentences, raw text behind the technical switch; ~45 catch sites converted (Studio parts, Home parts, Voice, TV).
- hub_compress.py + Handler.send_bytes: gzip when asked, ETag/304 for pages/scripts/styles, /api stays no-store.
- Measured (gzip): Studio app.js 653->211 KB, Home 181->59, Help 261->73, Voice 186->52; revisit = 304, 0 bytes.
- check_page_squeeze (sabotage-proven), Help bytask.html note (Rule 11).

## Next / not done
- Wording audit of visible labels (not errors) on Gacha/Faces/Studio panels; Studio 653 KB script is still heavy for a TV (split/lazy-load = bigger job, needs on-device numbers).
- Not tested on a real Android TV; no robot/hardware tests.

## File status
Baseline: 72d5eff. All rows: uncommitted, quick QC pass for check_page_squeeze/designer_first/build_web/systems; full QC running.

## Update 2026-11-20 (PR #135 merged; follow-up branch claude/project-thread-9mxwqn-2)
Throttled headless Chromium (CPU 4x, 5 Mbit, 40 ms), wire KB / load ms, before -> after:
Home 266->86 KB, 716->478 ms (warm 595->357); Studio 1447->430 KB, 2914->1415 ms (warm 2964->992);
Gacha 140->46 KB; TV remote 94->33 KB; Help 1091->850 KB (images were the rest -> lazy + ETag now).
Not a real Android TV: Studio's 3D scene still needs a real TV measurement.

## Client simulation 2026-11-20 (tools/client_matrix, results in thread; rerun: node tools/client_matrix/run.js)
154 cells (8 profiles x 3 networks x 7 pages; Chromium, Firefox, WebKit): no sideways overflow, no page errors except
Studio without WebGL (fixed: PR #139, check_no_webgl). Slowest cell 3.3 s (3G, CPU 4x).
Studio 3D orbit-drag frame time (software GL, so pessimistic): PC 20 ms (50 fps), old PC CPU 4x 24 ms (42 fps),
TV CPU 6x 46 ms (22 fps), CPU 10x 63 ms (16 fps). Decision: no Studio rewrite or split justified by these numbers;
revisit only if the real Android-VM run (VirtualBox on the PC) is much worse.
Flake fixed: check_no_shift raced the page's own list redraw (PR #140).

## Android VM run + PC local merge 2026-11-21 (claude, on the PC)
- tv-sim VM (VirtualBox 7.2.6, Android-x86 9.0-r2, Chrome 75, 2 CPU at 50%, 1536 MB, VBoxVGA, 1920x1080, files in E:\tv-sim).
  After PR 146 all five pages start in Chrome 75 (/, /studio/, /app/voice/, /app/gacha/, /app/tv/); load event 0.2-3.8 s.
  Studio 3D (software WebGL): idle 64 fps, while a 4-keyframe sequence plays 12.6-13.6 fps. No crash, no out-of-memory.
  Home showed Promise.allSettled / replaceChildren TypeErrors only on the first load right after the hub started
  (/api/version ERR_CONNECTION_REFUSED at that moment); later loads clean. Cause not found.
- Local work merged: main = dc57628 (146 commits ahead of origin/main, not pushed to main). Backup E:\backup\mice_main_b65a0fa.bundle,
  dirty files E:\backup\mice_dirty_2026-11-21.zip, merge worktree E:\work\mice_merge (branch pc-merge-1121), stash pre-merge-1121 kept.
- Full QC on main: 9630 passed, 4 failed. check_rgb_pin x2 and check_local_ai_on_demand fail the same on clean origin/main (env / upstream).
  "system map is sound" fails only in the main checkout because ignored local files (config/voice_profiles/) are listed by tools/systems.py;
  it passes in a clean tree (merge worktree). pio run -e mice_nong -e mice_cam -e mice_lift -e mice_blank: all SUCCESS.
- Privacy audit of the 146 commits: no keys/tokens/passwords, no audio/video/model files, no friend-repo code. Notes: author email in 142 commits,
  local LAN IPs and C:/Users path in docs, 13.8 MB dist/MiceHub.exe in local-only commits 6f92c537 and 01a9befe (checked: no hub_auth/password strings).
