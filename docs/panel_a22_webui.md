# Panel review - 2026-08-25 14:37

**Question.** Find BUGS and ease-of-use failures in the module website master page firmware/src/web/WebUI.h (the hub serves it whole; gen_tables.py cuts it per type). Look for: broken or duplicated JS function names, dead buttons, references to ids that do not exist, commands sent that the nong build does not register, surface text a designer would find hard (jargon, raw ids, error codes shown directly), and missing loading/empty/error states. Check WebPortal.cpp endpoints the page calls actually exist. List findings as file:line - what is wrong - why it matters, most severe first. Answer in at most 45 lines.

**Files.** WebUI.h
**Cost.** 543183 tokens across 3 models

## The head reviewer (gemini-3.1-pro-high)

 - (nothing to report)

## What each model said

### gemini-3.1-pro-high  _(614.0s, 121714 tokens)_

 - **FAILED** Error: timeout waiting for response

### gemini-3.7-flash-high  _(158.6s, 333662 tokens)_

 - **real** `firmware/src/web/WebUI.h:1287` g is block-scoped in try block but used in catch, throwing ReferenceError on fetch error and crashing loadPeers handler.
 - **real** `firmware/src/web/WebUI.h:1207` Empty/error option in loadList lacks value="", causing runSel/playSel to send placeholder text as MOVE/PLAY command.
 - **real** `firmware/src/web/WebUI.h:312` svJoint select lacks onchange handler, so changing joint does not update svRange/svRate inputs and sends wrong values.
 - **real** `firmware/src/web/WebUI.h:1236` Delete file button fetch lacks try/catch, causing unhandled Promise rejection on network error.
 - **real** `firmware/src/web/WebUI.h:1220` loadFiles renders no empty state row when fs is empty, making empty folder indistinguishable from fetch failure.
 - **real** `firmware/src/web/WebUI.h:1484` fetch /api/status on load lacks catch handler, leaving header badges empty without showing error state.
 - **maybe** `firmware/src/web/WebUI.h:448` Console placeholder lists lift-only commands (GOTO, RGB) that fail on nong and cam builds.
 - **fine** `firmware/src/core/WebPortal.cpp:649` All WebPortal endpoints called by WebUI.h exist and are registered correctly.
