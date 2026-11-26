# PC feels slow (everything): display/input-path diagnosis

Owner: claude (project thread)
Updated: 2026-11-26 21:05 (local)
Branch: claude/voice-idle-unload
Last commit: see git log
Plan: user report 2026-11-26: typing, windows and all apps lag; paused by the user ("moving for a bit"), resume when they say so

## Goal
Find why the whole PC feels slow when CPU, RAM, disk and GPU compute look free. Read-only: no kills, no setting changes.

## Doing now
Paused at the user's request. Nothing is running.

## Done (measured 2026-11-26, laptop Intel Core Ultra 9 275HX, RTX 5070 Ti Laptop + Intel iGPU, 24 threads, 32 GB)
- Our QC/builds were NOT running during the slowness (checked 20:33): not ours. Friend backend stopped 5 min (20:45-20:50): lag probes unchanged, so not it either
  (probe numbers in docs/friend/friend_requests_to_send_2026-11-26.md item 18). The probe is %TEMP%\probe.py (1 ms sleep overshoot + window-message round trip).
- Idle-ish counters: CPU 7-15%, disk time ~1%, queue 0.01, DPC 0.2%, interrupt 0.3-0.5%, pages/sec ~4, available RAM ~10.8 GB, commit 73%.
- Display: Intel iGPU drives the internal panel, 2560x1600 @ 60 Hz; the NVIDIA card renders (hybrid graphics). dwm.exe 293 MB, 13,096 handles, 0.4% GPU 3D.
- Power: Balanced plan with the default overlay, AC online, battery 91%. CPU at 91% of maximum frequency on average (no performance limit, "% Performance Limit" 100),
  turbo 139-159% performance. NVIDIA idle P8, 285 MHz, 49 C, no throttle reason active now; its lifetime counters show ~51,000 s of "SW Power Capping" and of
  "SW Thermal Slowdown" since driver start (historic, not active now).
- Uptime 2.99 days (boot 2026-11-23 21:15).
- Remote tools: AnyDesk service running (pid 5524, one established connection to 15.235.230.203:443 = its relay: online, not necessarily a session), Radmin VPN control
  service, GlobalProtect (PanGPS), Nearby Share launcher (86 CPU-s). No OBS, Xbox Game Bar or Teams process found. Port 7070 listening (AnyDesk).

## Not done yet (resume when the user is back and says so)
- Keyboard/mouse hooks and IME (ctfmon, TabTip, Thai/English layouts), input device drivers.
- Paged/nonpaged pool sizes, top handle counts and working sets, hard faults/s, MsMpEng activity, disk latency under load.
- A probe run (probe.py + typeperf) DURING a moment the user feels the lag, to see whether any number moves at that moment.
- Whether an AnyDesk/Radmin session is actually active (check with the user: they may not use either).
- If nothing conclusive: reboot is the next test. Before it: running hub (MiceHub.exe), Voice helper, face watcher, friend backend (restart with Start Reconize.vbs),
  any QC run and this Remote Control session would end; unpushed work: none known on the branches listed in the last reports (all pushed), but check `git status` first.
