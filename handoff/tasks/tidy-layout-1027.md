# Tidy the code folder layout

Owner: claude:10271959-0190
Updated: 2026-10-28 00:40 +0000
Branch: claude/project-thread-9y1rwe
Last commit: this checkpoint
Plan: A51-1 (PR #93 merged e1eaefd), A51-2

## Goal
User 2026-10-27: the code folder is cluttered; put .staging copies in their own
folder so they stop piling up at the root; tidy the other folders; rename
`code` (agreed: `mice_system`, do it LAST); everything dynamic + OOP, with a
header map of what lives where. Plan: /mnt/project-files/layout/layout_plan_2026-10-27.md

## Doing now
A51-2 (PR 2): apps as extensions. main_python/extensions.py (class Extensions:
per-PC store extensions.json beside hub_auth.json; detect mice-app.json / app.json /
partners.json "detect"; add/remove(hide)/restore/update; {data}/{parent} folder
tokens), hub_api_extensions.py routes, /api/apps hides apps whose "needs" partner
is missing, Tools tab add/remove UI, help part, docs/extensions.md + docs/INSTALL.md,
check_extensions.

## File status
Baseline: e1eaefd (PR #93 merged). PR 2 = A51-2.

| File | Change | State | Verification | Commit |
| --- | --- | --- | --- | --- |
| `main_python/extensions.py` | new: class Extensions (per-PC list, detect, add/remove/restore/update, partners_here) | done | check_extensions (sabotage 2/2) | 2nd A51-2 commit |
| `main_python/hub_api_extensions.py` | new: /api/extensions routes + folder dialog | done | check_extensions | 4c437b3 |
| `main_python/main.py`, `hub_api_apps.py`, `hub_auth.py` | EXT, hub_apps(everything), app_by_id, read_partners via partners_here | done | quick QC 6538/0 | both |
| `main_python/web/home/parts/apps_manage.{html,js}`, `index.template.html`, `tools/web_build.json`, built `hub.html`/`help.html`, `help/parts/hub.html` | Tools card "แอปในเครื่องนี้" + help | done | check_designer_first, quick QC | 2nd |
| `config/partners.json`, `apps/{faces,photobooth,all-jao}/app.json` | {parent} folders, detect, needs | done | check_extensions | 4c437b3 |
| `tools/add_app.py` | new: installer hook | done | not run against a live hub | 2nd |
| `docs/extensions.md`, `docs/INSTALL.md`, README, HANDOFF | docs + links | done | check_systems | 2nd |
| `qc/checks/check_extensions.py`, `docs/systems.json`, `docs/systems/hub-extensions.md`, `promote.py`, `.gitignore` | check + system header + skip/ignore per-PC list | done | pass | both |

## Facts found
- Root detection "parent if name startswith .staging" was copied in 9 tools + qc/run_qc.py:322, qc/checks/check_history.py:40; check_dev_tools.py:112 holds "prefix not exact name".
- promote.py:52 STAGING default, :71 _pick_staging, :176-178 book names, :417/:456 locks; SKIP_DIRS already has dist/build.
- check_code_patches.py:41 and check_promote_ask.py:41 assume `<root>/.staging` is a tree.
- PC root (read-only 2026-10-27): 20 `.staging-*` trees, build.bat untracked, scratch/ _photo_test/ _video_test/ patches_code/ build/ ignored.
- E:\final_proj\mice\Photobooth is the friend's git repo (ChocolateOwO/Photobooth); Photobooth-run/Dummy is run data.

## Done
- Survey + plan posted to the user.
- Quick QC 6400/6: 3 need the pio firmware build (flash/OTA, PlatformIO download limit in the container), plan-area heading fixed.
- PR #93 full QC (after merging main f78ace9): 8922 passed, 6 failed; systems header fixed; the other 5 (check_link_states x2, check_studio_boot, check_tools_list, check_view: headless chromium dump-dom timeouts) fail the same on origin/main in this container (run alone, 2026-10-28).

## Next
1. PC steps after #93 merges, ONLY when coordinator says the PC is quiet (RL running): pull; move the 20 `.staging-*` trees into `.staging/<name>` (move, no delete); move build.bat to _out/.
2. PR 2 (A51-2): code done, quick QC green; open draft PR, full QC, tell coordinator, merge. After merge the PC must rebuild MiceHub.exe.
3. Later with user OK: rename code -> mice_system, move parent-folder items (plan file section 3).

## Blocked
- Rename code -> mice_system and parent-folder moves: after other threads merge, user OK.
