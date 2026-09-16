# Panel review - 2026-08-26 00:30

**Question.** Review the batch that just landed for A22-1 (full-code bug audit). Claims: (1) nong/main_python_set_nong/web/app.js retimeAt() retimes ONLY keyframes whose predecessor changed, so hand-typed times survive delKey/dupKey/moveKey - check the three callers and whether updateKey/addKey still behave; (2) livePause() calls hubStop() BEFORE the liveLinked() early return so a hub show started while Live was ticked stops when the user unticks and pauses - any path that still leaves a hub clock running? (3) saveProject/loadProject round-trip seqNext; exportYaml/editLocalSeq/playLocalSeq now surface HTTP errors - do all three report AND keep old data on screen? (4) shared/web/mice.css .pin now uses --mut/--txt and button.secondary is defined - any other rule in any page still naming --muted/--fg or an undefined token? Report only what is NOT true in the code.

**Files.** app.js, mice.css, check_studio_edits.py
**Cost.** 582812 tokens across 3 models

## The head reviewer (gemini-3.1-pro-high)

 - **real** `nong/main_python_set_nong/web/app.js:4014` monitorChanged() sets playing false without hubStop(), leaving hub clock running.
 - **real** `nong/main_python_set_nong/web/app.js:1652` moveKey() misses retimeAt(Math.max(i, j) + 1), leaving keyframe after swapped pair on stale travel time.
 - **real** `nong/main_python_set_nong/web/app.js:1625` dupKey() does not retime duplicate, copying predecessor travel time into zero-distance move.

## What each model said

### gemini-3.1-pro-high  _(614.1s, 200289 tokens)_

 - **FAILED** Error: timeout waiting for response

### gemini-3.7-flash-high  _(181.5s, 247954 tokens)_

 - **real** `nong/main_python_set_nong/web/app.js:1652` moveKey() does not call retimeAt(Math.max(i, j) + 1), leaving keyframe after swapped pair on stale travel time despite changed predecessor.
 - **real** `nong/main_python_set_nong/web/app.js:1625` dupKey() does not retime duplicate keyframe, copying predecessor travel time into zero-distance move.
 - **real** `nong/main_python_set_nong/web/app.js:4014` monitorChanged() unchecks liveChk and sets playing to false without calling hubStop(), leaving hub clock running.
 - **real** `apps/camera/index.html:18` body references undefined token --font, falling back to browser default instead of --sans.
 - **real** `apps/voice/index.html:18` body references undefined token --font, falling back to browser default instead of --sans.
 - **real** `apps/voice/index.html:24` .card references undefined token --panel, rendering transparent background instead of --card.
