# Nong HOME/CAD and Gemini evidence audit

Owner:
Updated: 2026-10-24T22:11:47.507831+07:00
Plan: A48-13 (robot)
Branch: codex/nong-gemini-audit-1024
Tree: E:/final_proj/mice/code/.staging-nong-gemini-audit-1024
Last commit: 33f3892 initial checkpoint; see git log for latest

## Goal
Explain current nong joint numbers and arms-at-side HOME after CAD; audit every Gemini completion claim and test all implemented nong functions.

## Doing now
User explicitly deferred right elbow trim/centering diagnosis24Oct: they will adjust trim themselves; skip that diagnosis and continue other work. Lab confirmed user deferral: restored R_EL_P90 and STOP; never issued95 or trim changes. Continue SD wait-only sequences/audio/transports without wide arm poses, no persistent calibration writes. Continue all other feasible nong checks and Gemini source/evidence safety remediation. Gemini live UI actor coordinated to freeze/release15:38; preserve its queued feature work.

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
- Gemini raw transcript .system_generated/logs/transcript_full.jsonl under brain/fe045... step804 confirms explicit --quick5716/0, while dashboard calls it Full. Prior PR77 full does not cover later dirty gacha FSM. Raw HTTP records212/214 support old device completion514/972ms, not actual capsule drop; those records predate later4phase/pause5000 implementation. Audit confirmed GCFG CLEAR also omits8newfields.
- Lab safely stopped motion/sequence/audio15:22; exact physical-home-stop.json. One targeted human-watched probe now holds R_EL_P91.5 from90 over3000ms, other9 unchanged; awaits observation before return90 and possible second axis. No persistent calibration writes. Broad motion/OTA paused. Evidence right-elbow-pitch-diagnostic.json.
- Fields available in22Oct robot snapshots match fresh24Oct home/gear/pulse/range/frame, not proof trim/invert or physical calibration unchanged.
- Lab actual Hub reports stale after gacha hardware header changed since19:25 build. Integration audits artifact/source parity; no restart allowed during Lab lease.
- Existing Lab and integration chats explicitly resumed for disjoint read-only source audit and dedicated physical test matrix; no new chats.

## Next
1. Get current INFO/POSE/NEUTRAL from sole Lab owner, distinguish commanded state from measured physical geometry.
2. Audit Gemini actual logs/artifact hashes/review/gate, compare against complete nong command/feature matrix.
3. Record passed/failed/unverified/blocked precisely; fix confirmed source gaps only via claims, staging, regression and review/gate.

## Blocked
Nothing for read-only audit. Physical testing depends on actual device readiness; Lab owns that assessment. Do not silently change HOME/SETZERO/neutral or send all90.

## Latest steering and coordination
- USER: right elbow back/outward; firstprobe missed, repeat1.5deg not visually distinguishable. Do not infer backlash/latency or calibration correction from that evidence.
- USER then explicitly canceled elbow trim diagnosis and will set trim themselves. No persistent adjustment authorized/needed from us now; do not keep asking visual questions or repeat probes. Lab latest message confirms restored90/STOP, no95 issued.
- Gemini actor was still changing/building/flashing root while Lab owned hardware. CLI wrong-profile stop failed (trajectory not found); agentapi requires absent LS address. Computer Use reached actual Antigravity fe045 session, interrupted active task, delivered pause via Send Now. Gemini BRIDGE15:38 explicitly releases physical/code/build/flash; user queued gacha work preserved. Matched process inventory no related loop children.
- Lab restored91.5->90/STOP and both known gacha STOP15:34, all3 reported idle then. Check any later probe is restored on cancellation.
- Integration audit now must use latest frozen source00BDA4... rather than earlier original/unbounded or3500ms-false-success snapshots. Root remains metadata/report only, no test driver/hardware/source lease.

## Current continuation
- Source owner now A47-20, isolated codex/gacha-safety-1024-f6cc in .staging-continue-urdf, source claims BRIDGE15:42. Includes latest unsafe GNUDGE nonblocking/bounds/motion registry, centering fault/reset fixes and native0/HOME docs. Main must independently review exact diff when owner sends it; no extra paid model/agent required. QC/build only after Lab explicit lease.
- Lab continues non-wide-motion nong SD/wait-only sequence/audio/transport checks with original calibration preserved. Full matrix scratch/nong-acceptance-1024/nong-acceptance-matrix.md/.json and nong-command-acceptance.csv:32verbs+19groups, not all passed. Physical elbow centered/HOME geometry intentionally deferred by user.

## Checkpoint release
A48-13 handed off with exact next step; own metadata/scratch claims released, no process/driver/resource held. Existing Lab and source chats continue autonomously. Main receives source candidate for independent review; pick up this task then. All work is not complete. Last pushed checkpoint133638f before this metadata release update.

## Latest22xx recheck,24Oct
User asks check Gemini again. Current root AAAE3506...25103B includes GCALIB/GTEST/GDRAIN, changed17:33 after original freeze. Current confirmed blocking/unbounded GNUDGE, blocking/false-success GCALIB, center timeout->done, incomplete CLEAR; registry now includes new verbs. Earlier90847e8 fix must preserve/rebase latest features, not overwrite them. Private latest-gemini-review.md contains exact lines and limits. Root no .qc-receipt; last_run165focused only. Lab was interrupted by usage limit, resumed only to checkpoint cleanup and explicit driver release; last result idle/audiooff/TALKoff/vol70. No robot/trim changes. Main read-only report delivered; await source candidate and Lab final matrix/lease. No main driver/process/resource held after report.
