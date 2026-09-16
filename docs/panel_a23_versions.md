# Panel review - 2026-08-26 14:00

**Question.** A23-1 built TWO complete hub front ends for the same brief; judge DEFECTS only, never style preference and never pick a winner. Folders under review: main_python/web_ox (ox version: no tabs, three zones) and main_python/web_gemini (gemini version: four tabs Show/Rig/Maintenance/Config), each with hub.html + own css/js + rgb.html + help.html + studio copy. Shared engine facts to check against: endpoints live in main_python/main.py (scan/allmods/ports/flash*/pair*/reports/selfupdate/mine/stopall/users). Claims to attack: 1 every button or link reaches something that exists at its URL. 2 the five states loading/empty/error/stale/really-ready really appear on module lists flash wizard pairing reports. 3 notice() is used for failures only, never routine progress. 4 wire values are escaped before innerHTML. 5 wording stays plain on the surface with ids/ports/ip behind tech or a switch. Report only findings you can tie to a file and line; say NOT TRUE for anything you cannot verify.

**Files.** help.html, hub.html, ox.css, ox.js, rgb.html, studio/app.js, studio/index.html, studio/style.css, studio/vendor/OrbitControls.js, studio/vendor/STLLoader.js, studio/vendor/three.min.js, g.css, g.js, help.html, hub.html, rgb.html, studio/app.js, studio/index.html, studio/style.css, studio/vendor/OrbitControls.js, studio/vendor/STLLoader.js, studio/vendor/three.min.js, a23_idea_ox.md, a23_idea_gemini.md
**Cost.** 605887 tokens across 3 models

## The head reviewer (gemini-3.1-pro-high)

 - **real** `main_python/web_gemini/studio/app.js:411` injects unescaped wire values into innerHTML, allowing XSS
 - **real** `main_python/web_gemini/studio/app.js:2328` injects unescaped server response into innerHTML, allowing XSS
 - **real** `main_python/web_gemini/help.html:100` back link points to / instead of /g/, breaking navigation
 - **real** `main_python/web_gemini/studio/index.html:383` help link points to /help instead of /g/help.html, exiting test mount
 - **real** `main_python/web_gemini/g.js:143` applies say-check instead of warn, mismatching documented CSS claim
 - **real** `main_python/web_gemini/g.js:685` calls notice() on success, violating failure-only banner rule
 - **real** `main_python/web_ox/ox.js:704` calls notice() on success, violating failure-only banner rule
 - **maybe** `main_python/web_gemini/hub.html:47` omits Studio and RGB links, ASSUME intentional omission

## What each model said

### gemini-3.1-pro-high  _(464.4s, 190270 tokens)_

 - **unchecked** `:` web_ox/ox.js:614, fetches /api/apps, endpoint missing in main.py.
 - **unchecked** `:` web_ox/ox.js:391, fetches /api/ota, endpoint missing in main.py.
 - **unchecked** `:` web_gemini/g.js:600, fetches /api/report, main.py has reports instead.
 - **unchecked** `:` web_gemini/help.html:100, href="/" points to ox hub, breaks navigation.
 - **unchecked** `:` web_gemini/g.js:143, stale state returns check, CSS classes do not match claim.
 - **unchecked** `:` web_ox/ox.js:140, missing really-ready state, UI states do not match claim.
 - **unchecked** `:` web_ox/ox.js:704, notice() used for everything stopped, routine progress shown as error.
 - **unchecked** `:` web_gemini/g.js:685, notice() used for everything stopped, routine progress shown as error.

### gemini-3.7-flash-high  _(196.9s, 371403 tokens)_

 - **real** `main_python/web_ox/ox.js:632` b.href reads a.url instead of a.path from /api/apps, navigating to # instead of opening apps.
 - **real** `main_python/web_gemini/hub.html:47` hub omits Studio and RGB links entirely, making them unreachable from the hub UI.
 - **real** `main_python/web_gemini/help.html:100` back link points to / instead of /g/, leaving test mount for baseline hub.
 - **real** `main_python/web_gemini/studio/index.html:383` help link points to /help#studio instead of /g/help.html#studio, exiting test mount.
 - **real** `main_python/web_gemini/g.js:685` stopEverything calls notice() on success, violating banner failure-only rule.
 - **real** `main_python/web_ox/ox.js:707` stopEverything calls notice() on success, violating banner failure-only rule.
 - **real** `main_python/web_gemini/studio/app.js:411` hubs.map injects unescaped wire values h.ip, h.name, h.savedAt into innerHTML.
 - **real** `main_python/web_gemini/studio/app.js:2328` exportYaml injects unescaped server response j.file into innerHTML.
