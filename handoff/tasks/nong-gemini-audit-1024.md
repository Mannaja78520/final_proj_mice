# Nong HOME/CAD and Gemini evidence audit

Owner: codex:10241515-audit
Updated: 2026-10-24T15:23:12.697472+07:00
Plan: A48-13 (robot)
Branch: codex/nong-gemini-audit-1024
Tree: E:/final_proj/mice/code/.staging-nong-gemini-audit-1024
Last commit: 33f3892 initial checkpoint; see git log for latest

## Goal
Explain current nong joint numbers and arms-at-side HOME after CAD; audit every Gemini completion claim and test all implemented nong functions.

## Doing now
Human observes actual HOME mismatch, specifically right elbow rotated slightly backwards/not centered. Broad motion tests paused; Lab instructed safe STOP, targeted right-elbow diagnosis and no global/persistent calibration writes. Continue read-only trace HOME/90/nativeCAD0 and audit prior evidence. Lab chat01a167a0 owns actual hardware tests; integration01a1679e independently audits Gemini source and gate evidence. This chat holds no hardware, QC, service, camera or source lease.

## Facts found
- nong/main_python_set_nong/rig_default.json: zero=[0,0,0,0,0,0,0,0,90,90]; home/neutral=[90,140,90,90,90,40,90,90,90,90.5]. DEFAULT_RIG in rig_data.js is a fallback, not authoritative saved calibration.
- scratch/lab-hardware-1023/identity-first.json: actual nong67 INFO before Gemini takeover already reports identical joints/target/neutral at19:04 23Oct. Thus these HOME numbers did not originate from Gemini tests.
- firmware/src/modules/nong/NongModule.cpp:425 onward handles NEUTRAL read/write and persistence; HOME uses saved neutral, not forced90.
- web/urdf_view.json fit.anchor=home; urdf_view.js:578,619 builds home-relative render offset; :738 applies transform to THREE joint groups. This does not itself rewrite robot calibration.
- docs/urdf_nong.md:174 equates all90 with hanging arms in export instructions; this is unsuitable as a statement of the saved physical HOME and needs review against native audit.
- settings_shared.json tracked diff changes only savedAt/savedBy, not saved joint arrays. Browser-local/project calibration must be distinguished from server defaults.
- Gemini-owned lab task says all tests completed but lists only selected joints/functions. A completion summary alone is not raw physical proof. No matching show/dispense logs found yet in named Lab scratch directories.

## Done
- User requests added to actual plan A48-13, isolated metadata worktree created; dirty root preserved.
- Human correction overrides physical interpretation: right elbow is rotated slightly backward/not centered despite INFO=HOME. Numbers matching saved HOME DO NOT prove physical centering. Lab instructed pause broad motions/safe STOP, inspect rightEL pitch/roll/trim/horn/gear and acquire actual visual evidence where available.
- Fresh24Oct15:18 actual INFO from Lab matches all saved HOME/current/target values, idle and attached. Saved private scratch/nong-gemini-audit-1024/current-pose.json and findings.md. Firmware text NEUTRAL?/LIMIT? rounds shrug90.5 to90; INFO retains precise90.5.
- Independent static audit confirms Gemini SETTLE_CENTER returns before jam timeout, allowing unbounded motor pulses on missing Hall; integration asked to fix through isolated review/regression/gate. No actual fault injection.
- Gemini dashboard at ~/.gemini/antigravity/brain/fe045bc5-b8e9-40a9-92d2-04545c47561b/lab_progress_dashboard.md claims exhaustive hardware/5716 full QC but enumerates only two joints and inconsistently describes WAIST90.5. Raw logs and exact receipt still required; this does not prove untested operations failed.
- Lab actual Hub reports stale after gacha hardware header changed since19:25 build. Integration audits artifact/source parity; no restart allowed during Lab lease.
- Existing Lab and integration chats explicitly resumed for disjoint read-only source audit and dedicated physical test matrix; no new chats.

## Next
1. Get current INFO/POSE/NEUTRAL from sole Lab owner, distinguish commanded state from measured physical geometry.
2. Audit Gemini actual logs/artifact hashes/review/gate, compare against complete nong command/feature matrix.
3. Record passed/failed/unverified/blocked precisely; fix confirmed source gaps only via claims, staging, regression and review/gate.

## Blocked
Nothing for read-only audit. Physical testing depends on actual device readiness; Lab owns that assessment. Do not silently change HOME/SETZERO/neutral or send all90.
