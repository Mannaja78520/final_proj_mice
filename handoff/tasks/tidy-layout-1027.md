# Tidy the code folder layout

Owner: claude:10271959-0190
Updated: 2026-10-28 00:40 +0000
Branch: claude/project-thread-9y1rwe
Last commit: this checkpoint
Plan: A51-1 (PR #93 merged e1eaefd), A51-2 (PR #95 merged b7005d8) - both done; A51-3 doing

## Goal
User 2026-10-27: the code folder is cluttered; put .staging copies in their own
folder so they stop piling up at the root; tidy the other folders; rename
`code` (agreed: `mice_system`, do it LAST); everything dynamic + OOP, with a
header map of what lives where. Plan: /mnt/project-files/layout/layout_plan_2026-10-27.md

## Doing now
A51-3 (user 2026-10-28): rename code -> mice_system + parent moves. tools/tidy_pc.py (class PcTidy) reads config/layout.json "pc";
check_tidy_pc (sabotage 4/4); hooks use $env:CLAUDE_PROJECT_DIR (worktree/.staging part stripped), voice llm default = CODE/llm,
docs say <root>. PC run = pc_steps_A51-1.md section 5, only after RL + YOLO training end. Thesis/hardware/to_friend/_to_delete moves wait for the user's OK (fill "ok").

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
1. PC steps: /mnt/project-files/layout/pc_steps_A51-1.md. Section 4 (#95 pull + exe rebuild) is queued by the coordinator in the PC session. Sections 2-3 (.staging moves) run only after RL training ends. The coordinator sends them; this thread never does.
2. At the end: one combined list of asks for the friend (old pending asks + mice-app.json in their repos, docs/extensions.md "official" example). Sources: /mnt/project-files/friend_api/*.md, docs/gacha/friend_requests.md.
3. Later, with the user's OK: rename code -> mice_system (RC start command, device folder, .claude hooks, dist/Apps/*.lnk via tools/make_app_shortcuts.py, docs, memory); moves in the parent folder (photobooth/ is OK'd).

## Blocked
- Rename code -> mice_system and parent-folder moves: after other threads merge, user OK.
