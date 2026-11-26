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

## Resumed 21:54-21:57 (user back, after their shutdown/restart), read-only
- The PC was shut down at 21:04:54 (Explorer-initiated power off), slept/resumed, and came back by 21:52. `LastBootUpTime` is STILL 2026-11-23 21:15:55 (uptime reads 4,361 min =
  3.03 days) and Fast Startup is ON (HiberbootEnabled = 1): "Shut down" with Fast Startup saves the kernel session, so the kernel, drivers and the GPU driver state were NOT reset.
  Only user processes were. A real reset needs Start > Restart (or Fast Startup off, `powercfg /hibernate off`, a setting change not made here).
- After it: no hub, Voice, face watcher, friend backend, ffmpeg or SolidWorks running (nothing autostarted; not started by us). 265 processes, 128,721 handles, dwm new (1,378 handles,
  245 MB; was 13,096 handles before), MsMpEng 487 MB / 0 CPU.
- Now on BATTERY (AC online False, 87%), Balanced plan, CPU 74% of max frequency (idle, no performance limit), NVIDIA P4 495 MHz, 43.5 C, 0 MiB used (was 7.7 GB), SW Power Cap active
  (expected on battery). Commit 24% (16.5 GB of 68 GB; was 73%), available 19.3 GB (was 10.8), paged pool 1.56 GB, nonpaged pool 0.98 GB, standby 2 GB (cold cache).
- Probe (2 min, 11 windows of 10 s, user using the PC): CPU 4-15% (avg ~6%), DPC 0.12-0.19%, IRQ 0.10-0.43%; timer 1 ms sleep overshoot p99 0.84-1.04 ms; window round trip p50 0.47-0.59 ms,
  p99 1.50-1.71 ms, max 2.1-5.3 ms (before the shutdown, with SolidWorks/hub/friend backend loaded: p99 1.8, 2.7, 21, 38 ms in the 20:46-20:49 windows). Disk 1-28% only in the first
  20 s (cold start: page faults 80k/s, pages input 40k/s), then ~1%. No spike matching a "felt lag" was seen in these two minutes.
- Unexplained and unchanged: system calls ~395,000/s (was 505,000 avg before) and context switches 5-45k/s (was 68k) with nothing of ours running. Largest process-level suspects (read-only,
  per-process counters over 10 s): IntelGraphicsSoftware.Service (pid 5640) about 0.44 core and 470 IO-other-ops/s continuously, plus IntelGraphicsSoftware.exe (pid 25028, started at login
  with `-s`) about 0.07 core; XtuService (Intel Extreme Tuning Utility service, 4,528 handles), PresentMon service, MSI OmApSvcBroker/MSI Center, "System" has 7,999 handles.
  The Intel iGPU drives the panel, so Intel Graphics Software polling is the first thing to look at if the lag comes back (turn off its background service/telemetry or remove the app).
- Most likely cause (one line): not our jobs and not the friend backend; the loaded state (SolidWorks + hub + friend backend + Voice 5.4 GB VRAM + 3 days of kernel/driver state kept by
  Fast Startup + battery-vs-AC power state) rather than any single process; Intel Graphics Software + XTU polling are the standing background overhead.
- If the lag returns: note after how long and watch commit %, paged/nonpaged pool, total handles and dwm handles; run probe.py during it; do a real Restart (not Shut down) first.

## After the REAL restart (boot 2026-11-26 22:38:40, measured 22:51, uptime 13 min)
- The boot time is new (before: 2026-11-23 21:15:55 kept by Fast Startup). Same probe and counters as before, user not loading the PC: timer 1 ms sleep overshoot p50 0.31 / p99 0.77 / max 1.2 ms;
  window round trip p50 0.53 / p99 1.37 / max 2.0 ms; CPU 5.7%, DPC 0.26%, IRQ 0.17%.
- The big change is SYSTEM CALLS: 52,457/s (3-day session: 395,000-545,000/s) and context switches 15,000/s (5-68k before). Memory: commit 19.2% (was 24% / 73%), paged pool 0.89 GB (was 1.56 GB),
  nonpaged pool 0.77 GB (was 0.98 GB), available 20.4 GB, total handles 111,771 (was 128,721), dwm 1,184 handles (was 13,096 after 3 days).
- On battery (AC false, 56%), Balanced. Nothing of ours or the friend's running yet (hub, Voice, face watcher, friend backend not started).
- Reading: the 8-10x higher system-call rate and the 13k dwm handles belonged to the 3-day kernel session that Fast Startup kept alive; a real Restart cleared them. Watch for it growing back
  (system calls/s, dwm handles, paged/nonpaged pool) as the days pass; turn Fast Startup off (`powercfg /hibernate off`, a setting the user must choose) if it returns.
