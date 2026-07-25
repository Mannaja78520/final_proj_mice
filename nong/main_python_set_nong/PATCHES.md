# Web app patches

Every change to the Nong Studio web app is saved here as a numbered patch. Old patches are never removed — each row is a snapshot you can restore with `python save_patch.py --restore <n>`.

| # | when | change |
|---|---|---|
| 0001 | 2026-07-24 15:47 | Add WAIST (270deg TianKongRC) + SHRUG (MG90S ~6deg) body servos -> 10 joints; PDI-1181MG shoulders corrected to 270deg; per-group servo presets incl tiankong35; waist yaws body / shrug lifts shoulders in 3D |
| 0002 | 2026-07-24 16:14 | Rescale Studio 3D model to real STEP dimensions (joints r42, upper 110 / fore 130 bars, shoulderX 120, slim spine torso); IK self-test tolerance now scales with arm reach |
| 0003 | 2026-07-24 16:32 | FIX: model invisible with an old saved rig — mergeRig now migrates 'zero' (and any per-joint array) to length 10; applyPose is NaN-safe; new ?selftest=migrate regression |
| 0004 | 2026-07-24 16:45 | Shrug corrected to a see-saw ROLL (top-center joint rocks the shoulder bar: left up / right down), not a forward-back tilt; module website readout + labels updated to match |
| 0005 | 2026-07-24 17:07 | Shrug pivot adjustable in mm: the see-saw now rocks about a bearing ABOVE the shoulder line (Rig setup > shrug pivot, default 60mm), not at the servo |
