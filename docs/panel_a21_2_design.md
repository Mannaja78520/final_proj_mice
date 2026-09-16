# Panel review - 2026-08-24 03:25

**Question.** A21-2: the technical-detail switch must exist on EVERY page people look at, not only hub.html. The convention already works: mice.css has .tech{display:none} and body.adv .tech reveals it, localStorage key hub_adv remembers the choice, hub.html and apps/voice/index.html already use it (setAdvanced). Remaining pages: main_python/web/rgb.html, apps/camera/index.html, nong/main_python_set_nong/web/index.html (Nong Studio), main_python/web/help.html. Two questions. 1) Per page: what belongs behind the switch versus on the surface - name the concrete things you would hide (addresses, board ids, ports, pin numbers, raw JSON, register names...) and what must always stay visible. For help.html remember A21-4 will rewrite it into designer sections later. 2) Mechanism: how do four more pages get the SAME toggle without four divergent implementations - inline copy of a tiny snippet, or one small js file served beside mice.css that every page includes? Pages are served by a stdlib http server, no build step. Answer: one short list per page, then ONE recommendation for the mechanism with its tradeoff, at most 24 lines.

**Files.** help.html, hub.html, rgb.html, app.json, index.html, app.json, bench/cases.json, bench/run_bench.py, index.html, qa_data.json, service.py, app.js, index.html, style.css, vendor/OrbitControls.js, vendor/STLLoader.js, vendor/three.min.js, mice.css, mice.js, themes.css
**Cost.** 201931 tokens across 3 models

## The head reviewer (gemini-3.1-pro-high)

 - **real** `nong/main_python_set_nong/web/index.html:147` Connection inputs visible, clutters basic view.
 - **maybe** `main_python/web/rgb.html:112` Fallback shows IDs, clutters basic view.
 - **fine** `apps/camera/index.html:82` Details not visible.
 - **fine** `main_python/web/help.html:188` Expected in docs.

## What each model said

### gemini-3.1-pro-high  _(61.0s, 74267 tokens)_

 - **real** `main_python/web/rgb.html:112` IP, port, bus ID visible, needs technical-detail switch.
 - **real** `apps/camera/index.html:82` camera ID, dev string, IP visible, needs technical-detail switch.
 - **real** `nong/main_python_set_nong/web/index.html:147` IP, bus ID, USB port, raw limits visible, needs technical-detail switch.
 - **real** `main_python/web/help.html:188` API endpoints, pio commands visible, needs technical-detail switch.

### gemini-3.7-flash-high  _(40.2s, 102945 tokens)_

 - (nothing to report)
