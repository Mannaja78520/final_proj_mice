# Handover

Written by `tools/handover.py`. Read this first if you are picking up work somebody else started.

**When:** 2026-09-08 22:23  
**Last step:** A25 landed: rainbow guarded, shortcuts tab named

**Source saved:** `E:\final_proj\mice\code`

## Snapshots taken

* **hub, shared web, QC and tools** - patch 0029: `E:\final_proj\mice\code\patches_code\0029_a25-landed-rainbow-guarded-shortcuts-tab-named`
* **Nong Studio web app** - patch 0081: `E:\final_proj\mice\code\nong\main_python_set_nong\patches\0081_a25-landed-rainbow-guarded-shortcuts-tab-named`
* **firmware and the module page** - patch 0052: `E:\final_proj\mice\code\firmware\patches\0052_a25-landed-rainbow-guarded-shortcuts-tab-named`

Each area keeps its own numbered history and can be put back on its own: `--list` to see them, `--restore <n>` to go back. Nothing here reverts anything by itself.

## What is in .staging but not promoted

* changed in staging: PATCHES.md
* changed in staging: firmware/PATCHES.md
* changed in staging: nong/main_python_set_nong/PATCHES.md

## What the plan still has open

* A24-41 [todo] 2026-09-08 13:01  hw=lift board + PCM5102A + TPA3118 + the 12V speaker  — user 2026-09-08: add to the plan to 

## How to carry on

```
python qc/run_qc.py --quick                    ~90 s, is it green now
python firmware/tools/gen_tables.py            after editing WebUI.h or mice.css
python qc/run_qc.py                            full, real browser
python E:/final_proj/mice/code/promote.py      gate + promote, absolute path
python tools/plan.py show                      what the plan says
python tools/handover.py save "<next step>"     checkpoint again
```

Work in `code/.staging`, never the real tree. Read `CLAUDE.md` first - it is the standing agreement, and every rule in it was paid for.


## Latest checkpoint — 2026-10-21T01:12:20.203290+07:00 — codex:10201312-aba2

User requires a handoff before every end/stop so another agent can continue. This is a checkpoint during active work; no claim is released yet.

- Task A45-18; source E:/final_proj/mice/code/.staging-voice-speed, branch codex/voice-speed-multilang, HEAD 9de4b3a701e527d12930ffb339bdc9796a971400. Root main remains 6d443f82b5978c8d138f4bf999dcfb0fda32efda. Not merged/deployed yet.
- Latest quick 5321/0 in198.6s; 15 sabotage mutations caught/restored. Independent voice and final chatty fixture reviews clean.
- Full1 behavior7242/0 but receipt refused CRLF->LF restores. Full2 input manifest stable840files but chattyfixture6/1 due background census tripping cross-port fake guard. Fixture now directly calls identical production probes; all7assertions and12s/90s limits unchanged; focused7/0 and2mutations prove preserved coverage.
- FINAL FULL ACTIVE under /root/qc_runner: python -u qc/run_qc.py --jobs 2 --browsers 2; tree frozen, no competing tests/GPU/browser/build/restart. Log E:/final_proj/mice/code/.voice-bench-1020/full-production-qc-final.log. Before840inputs fingerprint c39c5f7554c21cdf8f279b733636840659b7f6479bb5846386e5b4da24a2f5de. Wait final verdict/receipt/after manifest; never start duplicate gate or edit candidate.
- Upon exact green: delegate scoped root promote --staging .staging-voice-speed --only paths in .voice-bench-1020/landing-paths.json (18paths). Baseline already accepted. Promotion commits only copied paths to ROOT main; push that root HEAD to remote feature branch, create/attach/merge PR, then root FF to origin/main. Do not push private WIP branch first. Never add -A or stage local config/keys/EXE.
- Then spec build to scratch/voice-build-dist, inspect current listener identities and running show/flash before prepared deploy.ps1; replace only Hub+Voice, preserve watcher/friend/user prefs. Prepared deployed_smoke.py checks new medium-for-en+Thai models, 30s+foreign real HTTP clips, auth401/pages/build stale:false. Helpers in .voice-bench-1020; not executed yet.
- Final scoped_land.py wrapper enforces18paths/explicit robot page/mutex. Run only after main+deployment smoke; default land.py is unscoped and unsafe here. Move OUR .voice-bench-1020 outside source to E:/final_proj/mice/voice-validation-2026-10-20 after logs close; preserve unknown _video_test and otherchat scratch/dance-video-check. Update final handoff and RELEASE; task done only after actual main+build/smoke.
- Other chat Continue Mice project work (01a1560a-7078-7492-8717-7c7992cd949c) released resources and currently only reads status; messaging authorized by user. Notify explicit RELEASE when done.
- Root 13 unrelated source/settings files preserved via root-preserve.json and byte backup ZIP. Real microphone, echo, human speech and robot speaker remain user tests; conversation is turn-taking.


## Checkpoint update — 2026-10-21T01:29:14.918366+07:00 — codex:10201312-aba2

Supersedes the earlier active-run/HEAD/artifact target above. A45-18 remains owned and in QC; no release.

- Frozen source HEAD85cd9d042753eb0faf33bf231bf9889626946163 in E:/final_proj/mice/code/.staging-voice-speed. Twenty landing paths in root/.voice-bench-1020/landing-paths.json. Root main still6d443f8; not promoted/merged/built/deployed.
- Latest quick5324/0 in225.7s;16 sabotage mutations caught/restored. Exact source and watcher-status reviews clean. Watcher fix tracks actualPopen: existing live process after transienthealthmiss isrunning, notstarted. New3assertions forbidspawn/verifyidentity; originalchecksretained.
- Prior finalgate was cancelled after this verifiedstatusbug (partial5547/1); ownprocessescleaned,840-inputmanifest unchanged. One inert browserprofile retained after deletion approvalrejection; no liveprocess. Do not countpartialrun asgreen.
- Release FULL nowactive under /root/qc_runner, runnerPID30216 (verifyidentitybeforeanyprocessaction), --jobs2 --browsers2. Rootartifact full-production-qc-release.log; before840inputs fingerprint1660ba819f77edc4d1722f85508f9f59184904a1f8a13fbedea8f19f77b3ad26. Wait exactgreen/aftermanifest/receipt; no duplicateQC or candidateedits.
- Main promotion remains scoped20paths withacceptedbaseline; delegatepromote/land toqc_runner. Push ROOTpromotecommittofeaturebranch, create/attach/mergePR, FFroot, specbuild. KeepAGENTS.md newhandoffsection (otherchatA45-20) and13preservedrootfiles.
- All actualruntimeports8642/8767/8769/8000/5173 wereoff01:16; prepareddeploy.ps1 nowhandlesverifiedstoppedHub/Voice. Aftergreen/build startactualstack, usingfriend ownexisting E:/final_proj/mice/Face_Regonize/Start Reconize.vbs only, no externalrepoedits. Friendhealth /api/health; frontend localhost:5173 canbeIPv6. Ourwatcher python -u apps/faces/service.py --partner reconize --port8769 fromroot. VoiceviaHubstart. Preparedsmokechecksallready,auth401,newVoicepage,stale:false,Thai30sand3foreignclips.
- Finalartifacttarget is E:/final_proj/mice/code/scratch/voice-validation-2026-10-20 INSIDEcode/ignoredscratch. Do notuseearliersiblingtarget. Moveonlyourbench afterlogsclose; unknown_video_test andotherchatdanceevidenceuntouched. Preparedhelpers/rootpaths supportmove.
- Before every end/stop: durableBRIDGEHANDOFF withexactstatus/claims; unfinishedownedtask planhandoff, completedtaskstaysdone. Nevertransferotheractiveowners.


## Completed handoff — 2026-10-21T01:57:52+07:00 — codex:10201312-aba2

Supersedes all earlier active-run checkpoints above.

Task: robot A45-18 DONE; owner codex:10201312-aba2. A45-20 standing handoff instruction included with its owner's explicit ACK; other tasks/owners are not transferred.
Tree: E:/final_proj/mice/code, branch main, source merge HEAD 3c8b65cb0f53bdc0a884ca67fc6a9cb859323e95, PR https://github.com/Mannaja78520/final_proj_mice/pull/40. Candidate E:/final_proj/mice/code/.staging-voice-speed, branch codex/voice-speed-multilang, HEAD 85cd9d042753eb0faf33bf231bf9889626946163. Promotion10ec233fab20c7516900ffab66f96f6829c135ce. Final metadata commit: git log -1 -- docs/HANDOVER.md.
Completed: 30-second speech safety, elapsed-silence endpoint, session/recorder cleanup, multilingual STT recovery and actual model status, English accuracy, four-language answers, bounded/deduplicated TTS, fast installed voice option, and honest reused face-watcher status. Original PR39 empty-WAV fallback/status/Edge hedge retained.
Exact20 source paths: apps/voice/app.js, apps/voice/index.html, apps/voice/index.template.html, apps/voice/qa_data.json, apps/voice/service.py, config/voice_providers.json, docs/systems.json, docs/systems/app-voice.md, docs/systems/hub-show.md, docs/systems/qc.md, qc/checks/check_voice_bench.py, qc/checks/check_voice_conversation.py, qc/checks/check_voice_fast.py, qc/checks/check_voice_source.py, qc/checks/check_voice_stt.py, qc/data/voice_conversation.mjs, docs/voice-validation-2026-10-20.md, qc/checks/check_chatty_board.py, main_python/hub_api_faces.py, qc/checks/check_faces_start.py.
Evidence: quick5324/0 in225.7s; full7245/0 in849.8s without retries;840 input hashes unchanged, green receipt1660ba819f77edc4d1722f85508f9f59184904a1f8a13fbedea8f19f77b3ad26. Sixteen sabotage mutations caught/restored; independent reviews clean. Two local QC files CRLF vs Git LF; tested raw bytes preserved. Earlier red/interrupted logs are historical, not green evidence.
Landing: wrapper exit0; gate says nothing to promote, no new copies/QC. Snapshot E:/final_proj/mice/code/patches_code/0031_landing-a45-18 (370files); only A45-18 marked done. All20 source hashes and both HEADs unchanged. land.py detects promoted in a historical directory and prints landed; this does not mean another copy occurred.
Deployment: MiceHub.spec build22.8s; installed dist/MiceHub.exe equals new build. Actual Hub stale:false, new Voice page, loaded LLM/STT specialists, Thai30s and EN/JA/ZH transcription/audio, actual Thai/English model status, auth401, Studio/Voice200, healthy watcher and friend dual/CUDA passed. Source20 bytes still match green tree.
Artifacts: E:/final_proj/mice/code/scratch/voice-validation-2026-10-20/README.md and landing-paths.json; full-production-qc-release.log/receipt/manifests/verdict; sabotage evidence; scoped-promotion.log; scoped-land-verdict.json; pyinstaller.log; deployment.json; deployed-smoke.json; deployed-cached-pipeline.json. Backup old EXE: same directory/MiceHub-before-A45-18.exe. All private evidence ignored inside code. Unknown _video_test and other-chat dance files preserved.
Latency: verified exact warmed answer/audio STT-to-audio TH0.631s, EN0.426s, JA0.346s, ZH0.321s. Add1.5s quiet endpoint gives1.82-2.13s before browser/speaker overhead. First new Thai phrasing needed5.19s synthesis/6.084s pipeline; do not call it cached or guarantee every answer under5s. Installed same-language voice can reduce network waits. Synthetic clips and fake capture/robot do not establish human/mic/echo/physical speaker performance. Conversation is turn-taking.
Running services LEFT ON: Hub8642 PID31956; Voice8767 PID32060; watcher8769 PID37960; friend8000 PID40500; frontend::1:5173 PID10196. Recheck actual command/identity before process actions. Friend started with existing external Start Reconize.vbs; no external source edits. No QC/build/sabotage driver remains. One inert test browser profile retained after automatic deletion approval rejection; no live process; do not bypass rejection.
Bookkeeping only: AGENTS.md, PATCHES.md, docs/BRIDGE.md, docs/HANDOVER.md, docs/PLAN.html, docs/plan_state.js. Approved AGENTS rawsha2561f8e6731ef51d03fce13c010c998338b91322cdb1f53a8cbe55ad12f8cad729c. Unrelated dirty user/settings/source files preserved; keys/runtime EXE/private media excluded from staging.
Remaining/blockers: no unfinished owned implementation/gate. Next: refresh Voice, test actual microphone, room echo and physical robot speaker, claiming hardware first. Other-chat A45-10/11/12 blockers stay in that handoff; no silent takeover.
RELEASE NOW: all our20 source claims, candidate freeze, integration/promotion, QC/fake/browser/GPU/measurement, build/restart/deploy, private evidence/snapshot and bookkeeping edit claims. No exclusive claim retained. Services stay running. Mutex only covers this checkpoint/commit, released in finally. Notify authorized Continue Mice project work after publication. Every later work stop requires a fresh HANDOFF; A45-18 stays done.
