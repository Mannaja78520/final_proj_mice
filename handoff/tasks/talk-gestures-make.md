# Talking gestures: sound in Show and new moves

Owner: claude:10271603-ce86
Updated: 2026-10-27 16:10Z
Branch: claude/project-thread-i4pp3d
Last commit: this checkpoint
Plan: A46-4

## Goal
User 2026-10-27 (Studio "Moves while talking"): how is this page used; Show
plays no sound; "ด้านขวาครับ" gave "No word asked for a gesture and no beat
fitted"; can it generate new moves itself for words with no gesture
(ด้านขวา / ด้านซ้าย / ข้างบน), fitted, collision-checked, keepable.

## Doing now
Step 1: gestures.py at-least-one-beat + make() rules (config/gesture_makers.json),
hub routes /api/gestures/make (open) and /api/gestures/think (gated, AI via
voice helper /gesture), plan accepts `extra` (unsaved made gestures).

## File status
Baseline: ecf48c2

| File | Change | State | Verification | Commit |
| --- | --- | --- | --- | --- |
| `main_python/gestures.py` | at-least-one beat; make(); clean_keys(); extra in plan | pending | not run | uncommitted |
| `config/gesture_makers.json` | rules for directions/body parts + AI prompt | pending | not run | uncommitted |
| `main_python/hub_api_studio.py` | /api/gestures/make, /think, plan extra | pending | not run | uncommitted |
| `main_python/hub_auth.py` | gate /api/gestures/think | pending | not run | uncommitted |
| `apps/voice/service.py` | /gesture route: think chain with given prompt | pending | not run | uncommitted |
| `nong/main_python_set_nong/web/app_parts/talk_gestures.js` | Show speaks + plays; made moves offer | pending | not run | uncommitted |
| `nong/main_python_set_nong/web/html_parts/talk.html` | AI switch, made-moves box | pending | not run | uncommitted |
| `nong/main_python_set_nong/web/app_parts/timeline.js` | togglePlay({previewOnly}) | pending | not run | uncommitted |
| `qc/checks/check_gestures.py` | new cases | pending | not run | uncommitted |
| help parts | Studio talk card help | pending | not run | uncommitted |

## Facts found
- main_python/gestures.py plan(): total = max(800, len/cps*1000); beats
  want = round(beats_per_s * total/1000) -> 0 for a 1 s line, and a beat needs
  length+2*gap of room. That is why "ด้านขวาครับ" (11 chars, 1 s) got nothing.
- gestures.fitted() uses a gesture only when fit.defs[id] == lib keys.
- hub_api_studio.py:44 api_gestures: GET lib, POST save/fit, plan/play.
- talk_gestures.js talkTry(): only puts plan on the time bar, never sound.
  talkFitOne(def, mirror, restPose) = IK + poseHit + safeKeys + planSafe (RRT).
- Voice page speaks via POST /api/voice/say {text, lang, style} (gated,
  hub_auth.py:137), helper apps/voice/service.py do_say ~3551; then
  POST /api/gestures/play with ms = audio duration.
- Helper think chain: Brain.run_job("think", one) service.py:654; wires
  providers.WIRES[kind]["think"](prov,key,job,system,history,limit,timeout);
  local = _ensure_llm + _complete(messages).
- Hub proxies /api/voice/X -> helper /X (main.py:1571 voice_proxy);
  voice_service_url() main.py:205.
- timeline.js togglePlay() decides previewOnly itself; previewOnly (collisions.js:106)
  stops live sends.

## Done
- nothing yet

## Next
1. Step 1 above, then Studio JS, help, QC, PR.

## Blocked
- nothing (no robot needed)
