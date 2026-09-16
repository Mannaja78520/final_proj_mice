# Panel review - 2026-08-24 21:45

**Question.** Task A21-5: the hub diagnostics button must become two halves for a designer audience. Today GET /api/diag returns ONE plain-text bundle built by diagnostics() in main_python/main.py around line 2163 - THIS PC, FIRMWARE BUILT, SERIAL PORTS, MODULES FOUND sections, ids and ports included, guarded secret-free by qc/checks/check_diagnostics.py. The hub page main_python/web/hub.html has one Copy diagnostics button (diagBtn around line 392). Wanted: a plain summary first - what is connected, what failed, what to try - readable with no ids or ports at all; the technical bundle stays complete but sits behind one click. Constraints: hub is Python stdlib only, frozen into MiceHub.exe; pages already have a technical-detail switch using class .tech; every error must still offer the fix. Question: where should the split live - two endpoints (/api/diag/plain + /api/diag) or one text with marked sections the page splits - and what exactly belongs in the plain half versus the technical half? Answer as short numbered points, no code.

**Files.** main.py
**Cost.** 322227 tokens across 3 models

## The head reviewer (gemini-3.7-flash-high)

 - **unchecked** `:` main_python/web/hub.html:392: real. Adding .tech to technical button hides button by default; breaks check_diagnostics.py check for id="diagBtn".
 - **unchecked** `:` main_python/main.py:3704: real. Adding /api/diag/plain duplicates /api/diag; breaks single bundle design.
 - **unchecked** `:` 1. Split location: fine: matches existing design.
 - **unchecked** `:` 2. Plain half purpose: fine: matches existing design.
 - **unchecked** `:` 3. Plain half contents: fine: matches existing design.
 - **unchecked** `:` 4. Plain half errors and fixes: fine: matches existing design.
 - **unchecked** `:` 5. Technical half contents: fine: matches existing design.
 - **unchecked** `:` 6. UI split: fine: matches existing design.

## What each model said

### gemini-3.1-pro-high  _(132.2s, 62973 tokens)_

 - **fine** `main_python/main.py:3704` Add /api/diag/plain endpoint routing
 - **fine** `main_python/web/hub.html:392` Add plain button, add .tech class to technical button

### gemini-3.7-flash-high  _(124.5s, 104431 tokens)_

 - **unchecked** `:` 1. Split location: one text bundle from `GET /api/diag` with marked section delimiter. Single HTTP fetch, preserves fallback textarea behavior, and keeps `qc/checks/check_diagnostics.py` verifying full output in one call.
 - **unchecked** `:` 2. Plain half purpose: designer summary of what is connected, what failed, and what to try, using friendly names and health status without hardware identifiers.
 - **unchecked** `:` 3. Plain half contents: module names, reachable module counts, firmware build readiness, host name, and action items.
 - **unchecked** `:` 4. Plain half errors and fixes: missing `esptool` (install PlatformIO), stale `MiceHub.exe` (run update), quiet modules (check power and WiFi).
 - **unchecked** `:` 5. Technical half contents: runtime info (`os`, `python`, `web build`, `frozen`), serial port mappings (`COMx`), module `#id`s, transport routes (`via usb`, `via rs485`, `via wifi`), binary byte sizes, and raw exception strings.
 - **unchecked** `:` 6. UI split: plain summary renders first; technical bundle sits behind `.tech` toggle or disclosure click, with `diagFall` textarea keeping full text for phone copy.
