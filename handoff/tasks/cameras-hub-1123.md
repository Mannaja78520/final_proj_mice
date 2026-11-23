# One camera hub: ESP32 + USB + IP cams shared by recording, face recognition, live watch

Owner: claude (cloud thread, branch claude/project-thread-b9oyj2)
Updated: 2026-11-23
Branch: claude/project-thread-b9oyj2
Last commit: see git log
Plan: none yet (user ask 2026-11-23)

## Goal
User 2026-11-23: one camera system. ESP32-CAM boards AND other cameras (USB / IP / ...)
usable at the same time by video recording, Face_Regonize, and later a watch window or
live stream for other people. Merge the "ESP32 camera" app into one "Cameras" app with
sources inside. Friend asks go into ONE consolidated friend file. Also: All-Jao app text
must not say "3 games", Photobooth text must not say only QR code.

## Doing now
Camera app UI (apps/camera), watch window, language packs, Help, friend file.

## File status
Baseline: 2045752 (main)

| File | Change | State | Verification | Commit |
| --- | --- | --- | --- | --- |
| `config/cameras.json` | kinds registry (link, demo) | done | check_camera_hub quick, fake ffmpeg | this checkpoint |
| `main_python/cam_sources.py` | one list of cameras, add/remove, relay_for(dev) | done | same | this checkpoint |
| `main_python/hub_api_cameras.py` | /api/cameras routes | done | same | this checkpoint |
| `main_python/main.py`, `hub_auth.py`, `cam_relay.py` | cam: dev in cam.stream/cam.jpg, gate, GONE text | done | same | this checkpoint |
| `apps/faces/look.py`, `service.py` | follow cameras marked for faces without restart | done | same | this checkpoint |
| `qc/checks/check_camera_hub.py` | new check (sabotage-proven: loopback refusal) | done | quick pass | this checkpoint |
| `apps/camera/*` | Cameras app UI + watch window | pending | not run | uncommitted |
| `shared/web/lang/*`, help parts | 4 languages + Help | pending | not run | uncommitted |
| `docs/friend/*` | one consolidated friend file | pending | not run | uncommitted |

## Facts found
- main_python/cam_relay.py: CamRelay (board) and PcCamRelay (ffmpeg) already fan one reader out to many viewers; UrlCamRelay in cam_sources reuses PcCamRelay.
- main_python/main.py cam.stream branch resolves `dev`; `cam:<id>` and `pc:` go through cam_sources.relay_for.
- apps/faces/look.py hub_frames reads any dev through the hub, so cam:<id> works for face recognition with no change; look.sync follows ?face=1.
- User-added cameras: .local/cameras/cameras.json (git-ignored; a link may hold a password).

## Next
1. UI, languages, Help, friend file, systems.json, api index, full QC, PR, merge, PC exe rebuild.

## Blocked
- nothing (untested on real ESP32-CAM / IP camera hardware; fakes only)
