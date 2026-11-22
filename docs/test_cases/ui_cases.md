# UI / browser test cases (hub on localhost:8642)

Written 2026-11-22. Priorities: P1 = data loss, security, page dead, newcomer blocked; P2 = polish, edge, cosmetic.
Surfaces (superset of the "14 pages"): Home, Tools, Modules, Firmware, Network, Settings, Problem reports (7 tabs of `/`, tab ids in `main_python/web/home/parts/tabs.js`), `/help`, `/rgb.html`, `/studio`, `/app/voice`, `/app/camera`, `/app/faces`, `/app/gacha`, `/app/tv`, `/app/all-jao`, `/app/photobooth` (served by `main.py` ~L2178 and ~L2291-2337; `all-jao`, `faces`, `photobooth` only list when `needs` partner is installed, `apps/*/app.json`).
Conventions: PW = Playwright (`chromium`, `page.goto(BASE+path)`), BASE=http://localhost:8642. Login via `F.login(base)` style helper in `qc/lib` (POST `/api/login`). "Stub" = `page.route` fulfil. Language key `localStorage["mice.lang"]` (default th, `shared/web/mice-lang.js` L11); theme key `mice_theme` (`shared/web/mice.js` L19, ids indigo/midnight/carnival/daylight in `shared/web/themes.css`, daylight is the light one); hub tab key `hubTab`. Page reloads on language change (`mice-lang.js` L91). Existing QC overlap noted as (QC: check_x) so new work targets gaps.
Plausibility column is folded into "how to automate" as a file cite.

| ID | area | steps | expected | how to automate |
|---|---|---|---|---|
| UI-001 | All pages smoke P1 | For each URL in the surface list, goto, wait networkidle | HTTP 200, no `pageerror`, no console.error, title non-empty | PW loop; `page.on('pageerror')`; list from `apps/*/app.json` + `/api/apps` (main.py L2178) |
| UI-002 | All pages P1 | Same loop, collect `requestfailed` and responses with status >=400 | none except allowed `/favicon.ico` (fixed, check_odd_input) | `page.on('response')` filter |
| UI-003 | All pages P1 | Load each page with a 404 sub-resource blocked (`page.route('**/shared/web/mice-ui.js', abort)`) | page shows plain-words banner, not a blank page (`mice-ui.js` L59 banner) | route abort, assert visible text |
| UI-004 | Routing P2 | goto `/app/nope`, `/app/voice/../../main.py`, `/app/voice/%2e%2e/%2e%2e/main.py` | 404 "no such app" / 403 "forbidden", never file bytes (main.py L2183-2192) | `request.get` assert status + body not containing `import` |
| UI-005 | Routing P2 | goto `/studio` and `/studio/` and `/studio/app.js` | all 200; `/studio/../main.py` is refused (main.py L2337-2360) | `request.get` |
| UI-006 | Tabs P1 | On `/` click each of the 7 `#tabs .tab` | only that tab's `[data-tab]` blocks visible, `.tab.on` moves, `hubTab` stored (`tabs.js` L12-22) | PW click loop, `locator('[data-tab]:visible')` |
| UI-007 | Tabs P1 | Set `hubTab=firmware`, reload | firmware tab shown on load (`start.js` L28) | `localStorage.setItem` via `addInitScript` |
| UI-008 | Tabs P2 | Set `hubTab=garbage`, reload | falls back to home, no JS error (`start.js` L28; showTab with unknown name hides all?) verify | init script + pageerror listener |
| UI-009 | Tabs P2 | goto `/#network`, then `/#bogus`, then back button | network shown; bogus ignored; Back returns to previous hash tab (`tabs.js` L88-96) | `page.goBack()` assert tab |
| UI-010 | Tabs P2 | Click tab 20 times in 1 s alternating Home/Network | no duplicate network polls piling (count `/api/net*` requests), ends on last tab | `page.on('request')` count, click with `delay:0` |
| UI-011 | Home P1 | Open Home with hub having 0 modules | empty-state wording for a newcomer, no raw JSON, no "undefined" | stub `/api/modules` -> `[]`; text not match `/undefined|NaN|\[object/` |
| UI-012 | Home P2 | Stub `/api/modules` with 200 modules | page paints under 3 s, no horizontal scroll at 1280 | route fulfil big JSON; `performance.now()`; `scrollWidth<=innerWidth` |
| UI-013 | Home P1 | Stub every `/api/*` to 500 | each tab shows plain words, buttons still clickable, no stack trace text (designer-first rule CLAUDE.md) | `page.route('**/api/**', 500)`; assert no `Traceback|Error:` text |
| UI-014 | Tools P1 | Open Tools tab | one card per registered app, ordered by `order`, each opens in same origin (`apps_manage.js` L116, `app.json`) | compare card count to `/api/apps` |
| UI-015 | Tools P2 | App with `show:false` (help) | not listed as a card (`apps/help/app.json`) but `/help` loads | assert no card named Features & help |
| UI-016 | Tools P2 | Partner not installed (all-jao, faces, photobooth) | card absent, direct `/app/all-jao` gives plain message not blank | env without partner; goto and text check |
| UI-017 | Modules P1 | Open Modules tab with a fake board (qc `fake_serial`) | card shows, buttons send commands and `fake_serial.wire` records them (CLAUDE rule 5) | use QC harness `F.start_hub()` + wire assert |
| UI-018 | Modules P2 | Rename a module to 300 chars / emoji / `<img src=x onerror=...>` | stored as text, drawn as text, 400 plain words if too long | PW fill + dialog listener; `/api/modules` read-back |
| UI-019 | Firmware P1 | Open Firmware tab, start flash without choosing a file | confirm dialog (`flash_confirm.js`) blocks; no POST sent | `page.on('request')` assert none to flash route |
| UI-020 | Firmware P1 | Choose a 0-byte / wrong-extension file and flash | refused with words; hub still answers `/api/whoami` after | `setInputFiles` buffer, follow-up request |
| UI-021 | Firmware P2 | POST firmware body with Content-Length 3 GB, body empty | 413-style refusal, connection closed, hub alive (main.py L1835-1850) | raw socket send header only; then GET `/` |
| UI-022 | Network P1 | Open Network tab | hubs list, QR painted (`paintQr`), no console error (`network.js` L276-278) | assert canvas/img non-blank pixel count |
| UI-023 | Network P2 | Other hub name = `<script>alert(1)</script>` via stubbed `/api/hubs` | drawn as text; no dialog event (check_studio_escape, A24-8) | `page.route('**/api/hubs')`, `page.on('dialog')` fail |
| UI-024 | Network P2 | Pairing flow with wrong code x5 | plain error each time, no lockout crash, hub alive (`pairing.js`) | repeated fill/click |
| UI-025 | Settings P1 | Change a setting, reload | value persisted server-side (`settings.js` L18; `/api/settings`) | fill, reload, assert value |
| UI-026 | Settings P1 | Change setting in tab A, reload tab B | B shows new value (no stale cache) | two `context.newPage()` |
| UI-027 | Settings P2 | Transfer settings export then import malformed JSON | plain 400 words, settings unchanged (check_settings_transfer) | setInputFiles bad JSON |
| UI-028 | Problem reports P1 | Open tab, submit empty report | refused or sends nothing; button not stuck disabled (`complaints.js` L167) | click, assert enabled after 2 s |
| UI-029 | Problem reports P1 | Submit with 5 MB text, emoji, RTL, `<b>` | either capped with message or stored; list renders text not markup | fill huge string, reload, `innerHTML` has no `<b>` |
| UI-030 | Problem reports P2 | Double-click Send | exactly one POST (check network count) | `page.on('request')` filter POST, `dblclick` |
| UI-031 | Login P1 | Hit a login-gated POST while logged out (e.g. `/api/save`) | 401 and page shows login prompt, then action resumes (check_studio_login_resume) | no cookie context, click Save |
| UI-032 | Login P1 | Wrong password, then right | plain "wrong" words, no password in URL or console | `page.on('console')`, assert URL |
| UI-033 | Login P2 | Login then Back button then Forward | still logged in, no re-prompt loop | goBack/goForward |
| UI-034 | Login P1 | Submit login form with 10k-char password and `' OR 1=1--` | 400/401 words, hub alive | fill + `/api/whoami` |
| UI-035 | Login P1 | Open `/studio` and `/app/gacha` in a fresh context | pages load read-only; write controls ask for login (check_page_login, check_faces_login) | new context, click write control, expect login dialog |
| UI-036 | Theme P1 | On every page set `mice_theme=daylight`, reload | `<html data-theme="daylight">`; computed body background luminance > 0.6 | evaluate `getComputedStyle`, luminance fn |
| UI-037 | Theme P1 | Same with `midnight` and `indigo` | background luminance < 0.3; text contrast ratio >= 4.5 on body and primary button | evaluate contrast; or axe-core `color-contrast` |
| UI-038 | Theme P2 | Set bogus theme id `mice_theme=zzz` | page still readable (falls back to default tokens), no error (`mice.js` L26-28) | init script, pageerror, screenshot diff vs default |
| UI-039 | Theme P2 | Change theme in tab A, observe tab B without reload | B updates via `storage` event (`mice.js` L30-36) | two pages same context, `waitForFunction` |
| UI-040 | Theme P2 | Studio: pick theme in Studio, open Hub | same theme applied; 3D canvas background matches (check_studio_theme) | localStorage shared; screenshot canvas corner pixel |
| UI-041 | Theme P2 | Light theme, open every dialog/notice/toast | no white-on-white text | trigger notice; contrast check on `.notice` |
| UI-042 | Theme P2 | `prefers-color-scheme: dark` emulation with no stored theme | default theme applies, no flash of wrong theme (grep shows no prefers-color-scheme use, so expected: ignored) document actual | `browser.newContext({colorScheme:'dark'})`, assert data-theme absent |
| UI-043 | Theme P2 | Private mode / localStorage throws | pages still load, theme just not saved (`mice.js` L55 try/catch) | `addInitScript` override `Storage.prototype.setItem` to throw |
| UI-044 | Lang P1 | For lang in th,en,zh,ja set `mice.lang`, reload each of 17 surfaces | `<html lang>` or picker value matches; no console error; picker option selected (`mice-lang.js` L80-90) | param loop; `select.lang-pick select` value |
| UI-045 | Lang P1 | Switch language with the picker on Home | page reloads once, tab stays (hubTab survives, `mice-lang.js` L27 comment) | click selectOption, `waitForNavigation`, assert tab |
| UI-046 | Lang P1 | th default for a fresh browser | first visit shows Thai (DEFAULT="th") | fresh context, text contains Thai range regex |
| UI-047 | Lang P1 | Fetch `/lang/index.json`, then each `/lang/<code>.json` | 200, `name`, >50 strings; `/lang/..%2Fmain.json` refused (QC: check_language) | `request.get` loop |
| UI-048 | Lang P2 | Count visible text nodes still English (not in the th/zh/ja maps) per page | list reported, threshold e.g. <15% on Home; regression snapshot | evaluate TreeWalker on text nodes, compare vs `lang/*.json` keys |
| UI-049 | Lang P2 | Switch to zh then ja on Studio mid-edit with unsaved keys | beforeunload prompt or draft restore offered after reload (timeline.js L684, draft restore notice) | add keys, change picker, accept/dismiss dialog |
| UI-050 | Lang P2 | Longest language (de-style long th/ja strings) at 390px | no horizontal overflow, no clipped buttons | `scrollWidth<=clientWidth`, bounding boxes inside viewport |
| UI-051 | Lang P2 | `mice.lang=xx` (unlisted) | falls back to Thai/English, no crash | init script |
| UI-052 | Lang P2 | Help in 4 languages: `shared/web/lang/help/*.json` | same section ids exist in each; search finds a term in each language | load `/help`, compare anchor ids |
| UI-053 | Lang P2 | Fonts: ja/zh glyphs on Chrome 75 headless | no tofu (check glyph width not equal missing-glyph box) | canvas measureText compare vs `.notdef`; manual screenshot |
| UI-054 | Mobile P1 | Viewport 390x844, touch, load each of 17 surfaces | `document.documentElement.scrollWidth <= 390`; no element wider than viewport | param loop + evaluate widest element |
| UI-055 | Mobile P1 | Home tabs row on 390px | row scrolls horizontally, active tab scrolled into view (`tabs.js` L16) | click last tab, assert `getBoundingClientRect` inside |
| UI-056 | Mobile P1 | Tap targets (`pointer:coarse`) on all buttons | min 40x40 px (`mice.css` L188, L278) | `hasTouch`; evaluate size for `button, a, input` |
| UI-057 | Mobile P1 | Studio at 390px | toolbar buttons reachable, none hidden under 3D (check_studio_phone_buttons) | PW mobile device + click each toolbar button |
| UI-058 | Mobile P2 | Rotate 390x844 -> 844x390 | layout reflows; no lost state in Studio | `setViewportSize`, assert keys unchanged |
| UI-059 | Mobile P2 | Soft keyboard simulation: focus input, shrink viewport height to 300 | focused field remains visible (`scrollIntoView`) | `setViewportSize`, `isIntersectingViewport` |
| UI-060 | Mobile P2 | Pinch zoom disabled? check `<meta viewport>` | no `user-scalable=no` (a11y) | `page.locator('meta[name=viewport]')` content |
| UI-061 | Mobile P2 | Voice page at 390px: mic button, transcript area | usable, no overlap with header | screenshot + bounding box overlap |
| UI-062 | Mobile P2 | Gacha page 390px with 6 machines | cards stack, tab row scrolls | stub `/api/gacha` |
| UI-063 | Legacy P1 | Run `qc/checks/check_old_browser.py` list on all 11 PAGES + 8 SCRIPTS | no `?.`/`??` in inline or shared scripts | existing check; extend PAGES with new pages |
| UI-064 | Legacy P1 | Chromium with `Element.prototype.replaceChildren`, `Promise.allSettled`, `Array.prototype.flat`, `Object.fromEntries`, `String.prototype.replaceAll`, `at()` deleted via `addInitScript`; load each page | page still boots (polyfills in `mice-ui.js`), no pageerror | extend BROWSER script in check_old_browser |
| UI-065 | Legacy P1 | Send UA `Chrome/75.0.3770.100 Android` to `/app/voice` | served `index.legacy.html` (`hub_legacy.pick`, main.py L2198) | `userAgent` context option; assert response contains legacy marker |
| UI-066 | Legacy P1 | Chrome 75 UA to `/studio` | legacy `app.legacy.js` used, not `app.js`; Studio boots | route listener on script URLs |
| UI-067 | Legacy P1 | Simulate startup syntax error by injecting bad script before app | plain-words banner shows (`mice-ui.js` L59) | `addInitScript` throw SyntaxError via `eval` / bad `<script>` |
| UI-068 | Legacy P2 | Remove `CSS.supports`, `IntersectionObserver`, `ResizeObserver`, `fetch` AbortController | Home and Help still load | init script deletes |
| UI-069 | Legacy P2 | No CSS grid gap / `inset` / `aspect-ratio` support (cannot delete; grep CSS) | scan CSS for properties unsupported in 75 and list; manual check on real VM | grep `aspect-ratio|inset:|gap:` in flex; compare against caniuse data file |
| UI-070 | Legacy P2 | No WebGL: launch with `--disable-gpu --disable-3d-apis` | Studio shows note instead of 3D, rest works (`scene.js` L4-15) | launch args; assert `noWebGL` note and Save button works |
| UI-071 | Legacy P2 | TV (`/app/tv`) at 1280x720 with D-pad keys only | every control focusable and reachable by Tab/Arrow; visible focus ring | `keyboard.press` sequence; `document.activeElement` log |
| UI-072 | Help P1 | Open `/help`, type "pose" in `#q` | results filtered, matching section highlighted (`help/parts/search.js`) | fill, count visible sections |
| UI-073 | Help P1 | Every sidebar link and by-task link | target anchor exists, scrolls to it (`bytask.html`, help_map.json) | collect `a[href^="#"]`, assert `getElementById` |
| UI-074 | Help P1 | From every hub tab click the contextual Help link | lands on its section (`HELP_SECTION` map, `tabs.js` L24+); tab without one lands on top | click `#helpLink`, assert `location.hash` |
| UI-075 | Help P1 | Help parity: every Studio/hub control id has help text (Rule 11) | QC docs check green; spot-check new features text appears | existing check_docs; PW search for control names |
| UI-076 | Help P2 | Search "<script>alert(1)</script>", 10k chars, emoji, RTL string | no dialog, no hang >1 s, "nothing found" words | fill + `page.on('dialog')`; time `waitFor` |
| UI-077 | Help P2 | Search empty after typing then clearing | full list returns | fill then clear |
| UI-078 | Help P2 | Help offline (context.setOffline(true) after load) | search still works (offline reference per `apps/help/app.json` blurb) | `setOffline`, repeat UI-072 |
| UI-079 | Help P2 | Help page at 390px and in light theme | sidebar collapses; contrast ok | mobile ctx + theme init |
| UI-080 | Help P2 | Print stylesheet (`emulateMedia print`) | no cut-off sections | `page.pdf` page count > 0, text present |
| UI-081 | Studio load P1 | Open `/studio` fresh | no console error; 3D canvas non-blank; head status says "nothing to save yet" (`save_state.js`) | pixel sample of canvas; `#stat` text |
| UI-082 | Studio save P1 | Add 3 keyframes, name "t1", Save | `/api/save` 200 `replaced:false`; status "saved"; both json and yaml exist (`hub_api_studio.py` L216-228) | click `#saveBtn`, read `/api/list` |
| UI-083 | Studio save P1 | Save again same name | response `replaced:true` and UI says "replaced t1.json" (L225 comment) | assert notice text |
| UI-084 | Studio 2 tabs P1 | Tabs A and B load same project "dup", A edits+saves, B edits other key+saves | last write wins on disk, but B warns it replaced something; no corrupt JSON (write_atomic); `/api/load` parses | two pages; read file json; assert `replaced:true` shown in B |
| UI-085 | Studio 2 tabs P1 | Two tabs save the SAME NAME concurrently (`Promise.all` of two POST via `page.evaluate`) | both 200, final file valid JSON, no `.tmp` leftovers, backup kept (`write_atomic` keep_backup, main.py L410) | parallel `fetch`, `/api/list` no stray tmp |
| UI-086 | Studio 2 tabs P2 | B opens project while A mid-save | B loads either old or new complete file, never partial | loop 50x, JSON.parse each |
| UI-087 | Studio 2 tabs P2 | Two tabs, delete sequence in A while B has it open then B saves | B save recreates or warns; no 500 (`/api/seqdelete` L170) | sequence of API calls |
| UI-088 | Studio names P1 | Save with name `../evil`, `a/b`, `.hidden`, 81 chars, emoji, empty, `CON`, trailing dots | rejected 400 in plain words except allowed unicode/Thai (PC_NAME regex main.py L390); nothing written outside PROJECTS | `/api/save` posts; directory listing unchanged |
| UI-089 | Studio names P2 | Thai name "ท่าเต้น1" | accepted, listed, reload works | save+list |
| UI-090 | Studio undo P1 | Add key, move key, delete key, Undo x3 | state returns step by step; Undo disabled at start (`timeline_undo.js`, `#undoBtn`) | evaluate `keys.length`; `#undoBtn:disabled` |
| UI-091 | Studio undo P1 | Undo then new edit then Redo | Redo disabled (future cleared, `changed()` L27) | click sequence |
| UI-092 | Studio undo P1 | Ctrl+Z / Ctrl+Shift+Z / Ctrl+Y while typing in a text input | does NOT undo timeline while a field is focused (check key handler `timeline_undo.js` L61) | focus `#projName`, press Ctrl+Z, assert keys unchanged |
| UI-093 | Studio undo P2 | 70 edits then Undo 70 times | stops at MAX 60 steps, no error (L11) | loop |
| UI-094 | Studio undo P2 | Drag a key rapidly (coalesce < 700 ms) | one Undo step reverts the whole drag | mouse move steps; count undo presses |
| UI-095 | Studio undo P2 | Load a file after edits | undo history reset (`reset()`) so Undo cannot resurrect old file | load, assert `#undoBtn:disabled` |
| UI-096 | Studio unsaved P1 | Edit, then `page.close({runBeforeUnload:true})` | beforeunload fires when dirty; not when clean or setting off (timeline.js L684) | `page.on('dialog')` beforeunload type |
| UI-097 | Studio draft P1 | Edit, kill tab without saving, reopen | draft restore notice with Yes/No (`project_library.js`, notice actions) | close page; new page; click `#draftRestoreBtn` |
| UI-098 | Studio reload mid-save P1 | Throttle `/api/save` to 3 s, reload at 1 s | file either old or complete new; draft still restorable (no data loss; check_no_data_loss) | route delay; reload; read file |
| UI-099 | Studio save offline P1 | `context.setOffline(true)`, click Save | plain-words failure, status stays "not saved", draft kept; saving again after online works | setOffline toggle |
| UI-100 | Studio save fail P1 | Stub `/api/save` -> 500 and -> 409 | message in words; `savedSig` not updated (still dirty) | route fulfil; `#stat` text |
| UI-101 | Studio double submit P1 | Double-click Save | one file write, no "replaced" false positive from own first save | count POST `/api/save`; replaced flag false/true sequence |
| UI-102 | Studio rapid clicks P2 | Click Add Key 200 times fast | keys count 200 (or capped with message), UI responsive (< 2 s) | `click({clickCount})` loop, `performance.now` |
| UI-103 | Studio music P1 | Add music file to timeline via input, check waveform/track appears (`sequence_audio.js`) | asset signature set; `sequenceAudio.signature()` non-empty; status "not saved" | `setInputFiles` small wav fixture; evaluate |
| UI-104 | Studio music P1 | Save with music, reload, reopen | music restored from IndexedDB (`nong_project_audio`, L21-26) and plays/duration same | `indexedDB.databases()`; compare `asset.sha256` |
| UI-105 | Studio music P1 | Reopen project on another browser profile (no IndexedDB) | "pick the .nong.json again" notice, Save refused until ready (`readyForSave`, L10-12) | new context; click Save; assert notice text and no POST |
| UI-106 | Studio music P2 | Music offset change then undo | offset restored or documented as not undoable | edit `offsetMs`; check |
| UI-107 | Studio music P2 | Music file: 0 bytes, 500 MB (generated), `.txt` renamed `.mp3`, 8 h silence | plain refusal or progress; no tab freeze > 5 s | `setInputFiles` buffers; watchdog |
| UI-108 | Studio music P2 | Music on a keyframe (`play:` cue, `vol:`) with robot offline | track list says unavailable in words (`music_on_a_keyframe.js` L8-12 `musicNote`) | stub robot list fail |
| UI-109 | Studio music P2 | Preview music then press Stop and tab hidden | audio stops (no ghost playback) | evaluate `media.paused` |
| UI-110 | Studio video P1 | Moves from a video: pick small mp4 via `#vidFile` | frames decoded, subjects list fills (`#vidSubject`), no console error (`video.html` L21) | `setInputFiles` 2 s fixture mp4; wait select options |
| UI-111 | Studio video P1 | Paste link into `#vidLink`, click Fetch with stubbed `/api/video/fetch` (start -> status progress -> done) | progress shown, completes, then `/api/video/file` used (`hub_api_studio.py` L336-380) | route state machine |
| UI-112 | Studio video P1 | Link = `file:///etc/passwd`, `javascript:alert(1)`, `http://127.0.0.1:8642/api/...`, empty | refused in words (`links().start` returns why); no local file read | POST direct and via UI; assert error text |
| UI-113 | Studio video P1 | Fetch id from before hub restart | 404 "hub was restarted?" shown as plain message (L347) | GET `/api/video/fetch?id=zzz` |
| UI-114 | Studio video P2 | Cancel fetch mid-way | POST `{cancel:id}` sent; UI returns to idle | click Cancel; request assert |
| UI-115 | Studio video P2 | Upload via `/api/video/put` body > limit or `Content-Length` 0 / negative | 413/400, connection closed, hub alive (L349-356) | raw http; follow-up GET |
| UI-116 | Studio video P2 | Video with no person / 1 frame / corrupt header | message "no one found" style words, no infinite spinner (timeout < 60 s) | fixtures; waitFor text |
| UI-117 | Studio video P2 | Reload during video analysis | no leftover temp, page returns to idle; hub alive | reload; `/api/video/fetch` 404 or idle |
| UI-118 | Studio 3D P1 | Orbit with mouse drag, wheel zoom, double-click reset | camera changes; canvas pixel hash changes; no error | mouse events; `toDataURL` hash compare |
| UI-119 | Studio 3D P1 | Slider for each joint moves robot model; limit clamps | `RIG` angle within min/max; model matrix changes (`sliders.js`) | set slider value, evaluate joint angle |
| UI-120 | Studio 3D P2 | Resize window 1280 -> 390 -> 1280 | canvas resizes, aspect right, no stretching | `setViewportSize`, compare canvas width/height vs client |
| UI-121 | Studio 3D P2 | Upload bad STL / URDF (`/api/model/upload`, `urdf_import.js`) | extension rule enforced (`UPLOAD_EXT`), plain refusal, previous model kept | `setInputFiles` bad ext and bad content |
| UI-122 | Studio 3D P2 | Switch rig preset, then "Use the CAD's sizes", then Reset | `/api/rigpresets` list used; Reset returns to default (rigdefault L247) | select options; evaluate `RIG` |
| UI-123 | Studio 3D P2 | Context lost: `gl.getExtension('WEBGL_lose_context').loseContext()` | page says so / recovers; Save still works | evaluate lose/restore |
| UI-124 | Studio 3D P2 | Pose collisions: drag arm into body | collision highlighted / blocked (`collisions.js`, `checked_motion.js`) | set angles via evaluate; read collision state |
| UI-125 | Studio sim P1 | With sim enabled (`config/nong_sim.json`), play a saved sequence | sim robot follows keys (lagged), finishes; Stop halts (tools/nong_sim/play.py) | needs MuJoCo; skip if not installed; run `tools/nong_sim` CLI and compare to Studio keys |
| UI-126 | Studio sim P1 | Dummy robot panel (`dummySimBox`, `robot.html` L97) shows when no robot | rows draw; commands go to dummy not serial | assert `fake_serial.wire` empty, dummy rows changed |
| UI-127 | Studio sim P2 | Sim timing vs board clock: 10 s sequence | sim duration within 5% of Studio's computed duration (`board_clock.py`) | python test calling play module, compare |
| UI-128 | Studio sim P2 | Run 3 sims at once ("any number of Nongs") | all finish, no cross-talk in joint states | python, 3 worlds |
| UI-129 | Studio sim P2 | Sim not installed | Studio hides/greys sim option with words, no error | uninstall mujoco in venv; load page |
| UI-130 | Studio safety P1 | Play with robot link while `/api/play` stub returns 500 | UI stops, shows words, no stuck "playing" (`checked_motion.js` one owner) | route fail; assert Stop button state |
| UI-131 | Studio safety P2 | Press Play twice quickly | one run, second ignored or queued | count `/api/play` POSTs |
| UI-132 | Studio keys P2 | Number fields: type `-1`, `1e9`, `NaN`, `0.0000001`, emoji, 500 chars in time/angle | clamped or refused, `keys` has no NaN (JSON round trip) | fill; evaluate `JSON.stringify(keys)` no `null` numbers |
| UI-133 | Studio XSS P1 | Sequence name / key note / music file name `"><img src=x onerror=alert(1)>` | rendered as text everywhere (list, status, export line) (check_studio_escape) | fill, `page.on('dialog')` fail, check `innerHTML` |
| UI-134 | Studio export P2 | Export YAML with name containing spaces and Thai | file name sanitized, content parses | download event; parse |
| UI-135 | Studio back P2 | Navigate Studio -> Hub -> Back | Studio restores state or draft notice; no blank 3D | goBack; canvas pixel check |
| UI-136 | Voice P1 | Open `/app/voice` | page loads, config fetched (`/api/voice/config`), start/stop buttons enabled per state (`apps/voice/app.js`) | stub `/api/voice/*`; assert buttons |
| UI-137 | Voice P1 | Type question in ask box, submit | POST `/api/voice/ask` body has question; answer shown as text | route capture; assert text |
| UI-138 | Voice P1 | Ask with 100k chars / emoji / RTL Arabic / `<svg onload=alert(1)>` / null byte | answer or plain refusal; no dialog; hub alive (`apps/voice` answerer) | fill; dialog guard; `/api/whoami` after |
| UI-139 | Voice P1 | Double-click Ask and Enter-key repeat | one request in flight, or second cancels first | count requests |
| UI-140 | Voice P1 | Start then Stop in <200 ms x10 | state ends consistent with server `/api/voice` status | click loop; GET status |
| UI-141 | Voice P2 | Mic permission denied (`context.grantPermissions([])`) | plain words how to allow; no crash (`getUserMedia` rejects) | permissions empty; assert message |
| UI-142 | Voice P2 | Add FAQ answer, reload | persisted (`/api/voice/faq`), `wholeQuestion` switch kept (app-voice.md) | POST/GET |
| UI-143 | Voice P2 | Select language th/en/zh/ja in Voice | request carries language; unsure-language fallback unaffected (`stt.fallback`) | capture request body |
| UI-144 | Voice P2 | Offline during ask | words "no connection", Ask re-enabled | setOffline |
| UI-145 | Voice P2 | Characters/profile create with name "default" | refused ("Default is kept safe" 409 pattern hub_api_studio L96) | POST profiles |
| UI-146 | Voice P2 | Play TTS then navigate away | audio stops (one player, check_voice_one_player) | evaluate `audio.paused` after goto |
| UI-147 | Faces P1 | Open `/app/faces` (partner present) | state polled (`/api/faces/state`), no spin loop >1 req/s | request rate count over 5 s |
| UI-148 | Faces P1 | Edit rules greeting on/off, save | POST `/api/faces/rules` needs login; keys starting `_` round-trip (app-faces.md) | assert `_note` key retained after save |
| UI-149 | Faces P2 | Rules with 10k-char greeting, emoji, `{name}` template injection `{__class__}` | stored as text; spoken text sanitized | POST; read back |
| UI-150 | Faces P2 | Partner server offline | page says offline in words; no hang; hub stays responsive (`partners_here` no health probes) | stub partner down; timing of `/api/faces/state` < 1 s |
| UI-151 | Faces P2 | Photo test upload (not a photo / 40 MB) | refusal in words (`tools/face_photo_test.py` paths) | `setInputFiles` |
| UI-152 | TV P1 | Open `/app/tv`, play list loads (`/api/list`, `/api/seqsteps`) | entries listed; Play posts `/api/play` (tv/index.html L592-656) | route capture |
| UI-153 | TV P1 | Press Play then Stop | `/api/play/stop` called, UI idle | request assert |
| UI-154 | TV P2 | Sequence name with Thai/emoji/quotes in list | play param URL-encoded, plays right file | stub list, check request URL |
| UI-155 | TV P2 | `/api/list` empty / 500 | empty-state words | route |
| UI-156 | TV P2 | Remote-style keys: Enter/Arrow/Back (keyCode 4) | navigates, Back does not exit page unexpectedly | `keyboard.press`; assert URL |
| UI-157 | Gacha P1 | Open `/app/gacha`; each tab in `TABS` (app-gacha.md) | each card has data-tab and shows only on its tab (check_gacha_sheet) | click tabs; compare card counts |
| UI-158 | Gacha P1 | Dispense on machine (`/api/gacha/dispense`) button | one POST, button disabled during request, result shown | route delay; count |
| UI-159 | Gacha P1 | Double-click Dispense / hold Enter | exactly one prize deducted (stub counts) | `dblclick`; server counter |
| UI-160 | Gacha P1 | Add machine with name `<img onerror>` / 300 chars / duplicate name | text-safe; duplicate refused in words | POST `/api/gacha/machine` |
| UI-161 | Gacha P1 | Edit rules JSON invalid / huge / `sheet_write_url` missing (save merges, app-gacha.md) | refused words or merged; existing rules kept | POST `/api/gacha/rules` |
| UI-162 | Gacha P2 | Sheet script secret endpoint without login | 401 (login-only) (app-gacha.md) | no-cookie `request.get` |
| UI-163 | Gacha P2 | Status poll while partner servers offline | returns < 1 s (no live probes, app-gacha.md) | time `/api/gacha` |
| UI-164 | Gacha P2 | Prize log with 10k rows | paginates or renders < 2 s | stub `/api/gacha/log` |
| UI-165 | Gacha P2 | Webhook URL `javascript:` / internal IP | refused or warned | POST config |
| UI-166 | Other apps P2 | `/app/camera` with no ESP32 | placeholder words, no broken image icon loop | stub stream 404 |
| UI-167 | Other apps P2 | `/app/photobooth` and `/app/all-jao` launch buttons double-click | one process started (partner_launch) | count `/api/...start` |
| UI-168 | RGB P2 | `/rgb.html` choose mode with WiFi vs USB target, send | `/api/dev/cmd?dev=..&c=` url-encoded; unusual chars safe (main.py L473 in rgb) | route capture; `c` with `&`, `#`, emoji |
| UI-169 | Newcomer P1 | Fresh profile (no localStorage), open `/`, follow only on-screen words to: see a board, open Studio, make 2 keys, save, play | completes without Help or console; each step has a visible clickable cue | scripted by role/text only (no ids); fail if any step requires technical term from `qc/data/designer_words.json` |
| UI-170 | Newcomer P1 | Same walk in en, then th, zh, ja | every step label translated; no raw keys like `studio.save` | regex for `\w+\.\w+` snake keys in visible text |
| UI-171 | Newcomer P1 | Designer-first: scan every page's visible text for banned words | none outside technical-switch (CLAUDE.md, `designer_words.json`) | load json; walk text nodes where not inside `.tech` hidden; (QC: check_designer_first) |
| UI-172 | Newcomer P2 | Technical switch on then off | technical detail (ids, ports) appears/disappears and state persists on reload | toggle; assert text visibility |
| UI-173 | Newcomer P2 | Walk-through at 390px on a phone: connect board, open Voice, ask one question | completes with touch only | mobile ctx |
| UI-174 | Newcomer P2 | Click "Help" from first page seen; return with Back | lands on right section and Back returns to same tab | `goBack`, assert `hubTab` |
| UI-175 | Newcomer P2 | Everything clickable that is settable: scan inputs lacking a visible label | 0 inputs without label/aria-label (Studio `projName` has aria-label, header.html L14) | evaluate query of unlabeled form controls |
| UI-176 | Mischief XSS P1 | Put payload set (`<script>alert(1)</script>`, `"><svg/onload=alert(1)>`, `javascript:alert(1)`, `{{7*7}}`, `${7*7}`, `'-alert(1)-'`) in every text input on every page, submit, reload | no dialog event, text echoed literally | generic form filler over `input,textarea`; dialog guard; compare saved vs literal |
| UI-177 | Mischief XSS P1 | URL params and hash: `/?tab=<script>`, `/#<img src=x onerror=alert(1)>`, `/help?q=<svg onload>` | no execution; invalid hash ignored (tabs.js L88-96 only matches existing tab) | goto each; dialog guard |
| UI-178 | Mischief XSS P1 | Stored XSS via `/api/modules` rename and board self-reported name via stub | drawn as text (check_studio_escape; extend to Home, Network) | stub endpoints with payloads, scan `innerHTML` for unescaped `<img` |
| UI-179 | Mischief big text P1 | 1 MB text into each text input/textarea | no freeze > 3 s, server answers 4xx plain words if too long, hub alive | `fill` large string; timing; `/api/whoami` |
| UI-180 | Mischief big text P2 | 5 MB POST bodies to every JSON route (`/api/save`, `/api/settings`, ...) | 413 or 400, never 500 (check_odd_input extends) | crawl routes from `docs/` route list; send big body |
| UI-181 | Mischief unicode P2 | Emoji ZWJ sequences, combining marks (Zalgo), Thai stacked vowels, 0-width chars, NUL, lone surrogates in names | stored/displayed intact or refused plain; no `UnicodeEncodeError` 500 | fill; check status codes |
| UI-182 | Mischief RTL P2 | Arabic / Hebrew names and bidi override U+202E in file name | list stays readable, layout not mirrored; `dir=auto` or isolate; no overlap | screenshot compare; bounding box of neighbours |
| UI-183 | Mischief rapid P2 | Mash every button on each page (random clicks 500x with `page.mouse`) | no pageerror, no unhandled rejection, hub alive (monkey test) | seeded random clicker; `pageerror` listener; end `/api/whoami` |
| UI-184 | Mischief rapid P2 | Hold Enter/Space on focused primary buttons 3 s | no repeated destructive action (delete, flash, dispense) | `keyboard.down('Enter')` repeat |
| UI-185 | Mischief double submit P1 | Double-click every POST-causing button listed from page scan | one effective POST each, or idempotent | wrap `fetch` counter via `addInitScript` |
| UI-186 | Mischief offline P1 | After loading each page, `setOffline(true)`, click every button, then back online | words not stack traces; page recovers without reload | `setOffline`; no console `TypeError`; assert recover polling |
| UI-187 | Mischief offline P2 | Load page while offline (cached) | browser error is browser's; after online reload works | context offline goto |
| UI-188 | Mischief hub dies P1 | Kill hub process mid-use (QC `F.start_hub()` then stop) | every page shows "hub not reachable" words, polling backs off (no 100 req/s), recovers when hub returns | harness stop/start; count requests |
| UI-189 | Mischief slow net P2 | CDP throttle Slow 3G, load each page | spinners/skeleton, no blank > 10 s, Studio still draws | `CDPSession Network.emulateNetworkConditions` |
| UI-190 | Mischief back button P1 | Studio: edit, press browser Back to hub | beforeunload prompt for dirty; after Forward state not silently lost (draft) | `goBack` with dialog handler |
| UI-191 | Mischief back button P2 | Open a dialog (Firmware confirm), press Back | dialog closes or page leaves; no stuck overlay | `goBack`; `.modal:visible` count |
| UI-192 | Mischief reload mid-action P1 | Reload during: firmware flash, project save, video fetch, Dispense, Play | hub-side state consistent; page afterward shows true state, not "playing" forever | start action, `reload`, poll status |
| UI-193 | Mischief tabs P2 | Open `/` in 5 tabs, mutate settings in each | no cross-tab corruption, last write wins, each tab refreshes within one poll | multi pages same context |
| UI-194 | Mischief storage P2 | Clear localStorage/IndexedDB while Studio open, then Save | save works (server side), music/draft warnings in words | `evaluate localStorage.clear(); indexedDB.deleteDatabase` |
| UI-195 | Mischief storage P2 | localStorage quota full (fill 5 MB) | draft write failure handled, notice, no crash (`save_state`) | fill in init script |
| UI-196 | Mischief clock P2 | `page.clock` set to 2038 / 1970 / DST jump | timers (heartbeats, status poll) still run, timestamps readable | Playwright `clock.install` |
| UI-197 | Mischief resize P2 | Rapid viewport resize 100x between 320 and 2560 | no layout thrash errors; Studio canvas ok | loop `setViewportSize` |
| UI-198 | Mischief zoom P2 | CSS zoom 200% and 50% (`page.evaluate document.body.style.zoom`) / device scale factor 3 | no overlap of primary controls | screenshot and bounding-box checks |
| UI-199 | Mischief keyboard P2 | Tab through each page; Esc in every dialog | all dialogs close with Esc, focus returns, no keyboard trap | `keyboard.press('Tab')` x N; `Escape` |
| UI-200 | Mischief clipboard P2 | Paste 1 MB / HTML clipboard into text fields | plain text only inserted; no HTML | `clipboard.writeText` + Ctrl+V |
| UI-201 | Mischief drag-drop P2 | Drop a folder / .exe / 100 files on Studio video, music, model inputs | first valid file taken or refusal in words | `dispatchEvent('drop')` with DataTransfer |
| UI-202 | A11y P2 | Run axe-core on all pages in dark + light, th + en | no "critical" violations (labels, contrast, names) | `@axe-core/playwright` |
| UI-203 | A11y P2 | Status line is `aria-live` polite, not read every tick (`save_state.js` L2-4 comment) | no text mutation when unchanged over 5 s | `MutationObserver` count on `#stat` |
| UI-204 | Perf P2 | Cold load of Home, Studio, Voice | Home DOMContentLoaded < 1.5 s, Studio < 4 s on localhost, JS heap < 150 MB after 60 s idle | `performance.timing`; CDP heap |
| UI-205 | Perf P2 | Leave Studio 3D idle 5 min | CPU low when tab hidden (`visibilitychange` pause render loop) / no memory growth > 20% | CDP `Performance.getMetrics` |
| UI-206 | Security P1 | Cross-origin POST to hub from `evil.example` page (CORS / CSRF) with cookie | rejected (no `Access-Control-Allow-Origin: *` on gated routes; Origin check) | second server on :9999 with fetch to :8642; assert blocked/401 |
| UI-207 | Security P1 | Request with `Host: evil.com` / DNS rebinding | refused or harmless (main.py Handler) verify | raw http headers |
| UI-208 | Security P1 | Path traversal on static: `/shared/web/..%2f..%2fmain.py`, `/lang/..%2Fmain.json` | 400/403/404 | `request.get` list |
| UI-209 | Security P2 | NEVER_GATED routes: POST 101 MB body unauthenticated | rejected at 100 MB cap (main.py L1846) | stream body; expect 413 |
| UI-210 | Security P2 | Session cookie flags | HttpOnly, SameSite set; not readable from `document.cookie` | `context.cookies()`; evaluate |
