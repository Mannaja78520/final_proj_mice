# Every app works alone and together

Owner: claude:11230402-8826 (cloud thread, branch claude/project-thread-dyrzf2)
Updated: 2026-11-23
Plan: A57-1

## Goal
User 2026-11-23: every app (ours + the friend's) must work fully alone, no hub, with nearly the same
functions; when the hub / other apps run they join up (Voice + face greets, games + prize machine,
one camera owner). Friend code is never edited: asks go in docs/friend/friend_requests_all_2026-11-23.md (section G).

## Doing now
Full QC, then PR + merge + PC exe rebuild.

## Done
- main_python/peers.py (registry of running programs by ability + one-owner camera claims), alone.py (`--alone <app>`), hub_api_peers.py (/api/peers), main.py wiring.
- app.json: alonePort + caps (studio 8651, voice 8652, camera 8653, gacha 8654, tv 8655, help 8656).
- cam_sources._pc_or_peer: a webcam owned by another program is read from it.
- faces watcher: peers.where() finds a speak/camera neighbour when no hub answers.
- qc/checks/check_alone_apps.py (sabotage-proven), Help hub.html block + 4 languages, docs/architecture/standalone-apps.md, friend file section G.

## Next
- PC: rebuild MiceHub.exe, try `MiceHub.exe --alone voice` and two apps together with a real webcam.
- Home page card list of alone apps (belongs to the Tools-page thread; /api/peers is ready).

## Blocked
- nothing. Untested on the real exe, real webcams, real boards (fakes only).

## Facts found
- main.py: `--only` is taken by run_qc.py's own flag (argv is shared in-process), so the flag is `--alone`.
- registry apps carry `needs` for friend programs (faces, photobooth, all-jao): `--alone` refuses them with the reason.
- Camera claims live in <temp>/mice-peers/cam-<dev>.json (O_EXCL); a backlog-8 listener in a test made `answers()` time out: use listen(128).

## File status
| File | Change | State | Verification | Commit |
| --- | --- | --- | --- | --- |
| `main_python/peers.py`, `alone.py`, `hub_api_peers.py` | new | done | check_alone_apps quick pass + sabotage 7/7 | this checkpoint |
| `main_python/main.py`, `cam_sources.py`, `tools/registry.py` | wiring | done | same | this checkpoint |
| `apps/*/app.json`, `apps/faces/rules.py`, `apps/faces/service.py` | ports/caps, neighbour lookup | done | check_alone_apps, faces_greet quick pass | this checkpoint |
| `qc/checks/check_alone_apps.py` | new | done | pass | this checkpoint |
| help part + `shared/web/lang/*` + docs | Help 4 langs, architecture, friend G | done | quick QC running | this checkpoint |
