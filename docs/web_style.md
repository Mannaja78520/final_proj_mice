# Building a web page — read this one file first

Asked 2026-10-14 (A41-1): every page the same, easy to change, fewer tokens.
A page is **assembled from shared parts**, never written from scratch. Read
this file, then only the page you change. Do not open other pages to copy from.

## The three shared files (`shared/web/`)

| file | what | who loads it |
|---|---|---|
| `themes.css` + `mice.css` | colours (one block per theme), then shape, type and components. Served together as `/mice.css`. | every page, the board's site too (compiled into flash) |
| `mice.js` | theme picker, login (`miceLogin`), technical switch (`miceAdv`), link state (`miceLink`) | every page, the board's site too |
| `mice-ui.js` | the page parts as classes: `Mice.Api`, `Mice.Status`, `Mice.TopBar`, `Mice.Partner` | hub pages only (not in flash: mice_nong is near its OTA slot) |

A new colour is a token in `themes.css`. A component used on three or more
pages goes in `mice.css`; a one-off stays in its page.

## A hub page, whole

```html
<!doctype html>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Thing — Mice</title>
<link rel="stylesheet" href="/mice.css">
<script src="/mice.js"></script>
<script src="/mice-ui.js"></script>
<body class="page">
<header class="topbar">
  <h1>🧩 Thing</h1>
  <span class="statline" id="stat">checking…</span>
  <button onclick="...">its own button</button>
  <span class="sub">one line saying what this is for</span>
</header>
<div class="card"> ... </div>
```

`body.page` is the frame (one column, the hub's width). `Mice.TopBar` mounts by
itself: it puts **← Hub** first and **Show technical details** last. Write only
what is the page's own between them. `data-home="none"` drops the way back
(Home itself).

## A big page is cut into parts (Home)

Home is `main_python/web/home/`, never `hub.html` (that file is BUILT):

* `index.template.html` — the map: head, the tab row, and one
  `<!-- part: x.html -->` line per area.
* `parts/<area>.html` + `parts/<area>.js` — one area each (home, tools,
  modules, firmware, network, settings, complaints; top = the head and login
  card; dialogs; login, accounts, pairing...). Read only the area you change.
* `style.css` — what is Home's own.
* The `.js` parts run in the order listed in `tools/web_build.json` — they share
  one script, so a function in one part is visible to all.
* A tab draws itself with `onTab('<tab>', fn)` next to `fn`, in its own part.
* Then `python tools/build_web.py`. A part not placed or listed fails the build.

A new area is a new part file plus one line (template or `web_build.json`).

## The parts

* **`Mice.Api.get(path)` / `.post(path, body)`** — every call to the hub. Never
  throws; returns `{ok, data, status, needLogin, says, tech}`. `says` is for the
  person, `tech` for the technical switch. No bare `fetch`, no empty `catch`.
  Default timeout 8 s; pass `{timeout: ms}` for a slow one. (Home's login,
  accounts and pairing use it; its scans and flashing still call `fetch`,
  which mocks in QC replace - move them when you next change them.)
* **`new Mice.Status("stat")`** — one status line, five states:
  `.loading() .empty() .error() .stale() .warn() .ready()`, each `(words, tech)`.
  `.from(answer, "saved")` words an Api answer.
* **`new Mice.Partner(id, {status})`** — an outside program from
  `config/partners.json`: `.load()`, `.check()` (the HUB asks it), `.ensure()`
  (start if silent), `.open(which, button)`. A new outside program is an entry
  in that file and a page with one `new Mice.Partner(...)`.
* **`Mice.here(url)`** — a `127.0.0.1` link made to work from a phone.

## Rules the checks hold

* One login place per screen. A page with its own login form marks it
  `data-login-here`; a gated card (`data-needs-login`) then shows one line
  pointing at it instead of a second login card (`check_page_login`).
* Plain words on the surface. Addresses, ports, paths, commands, ids and status
  codes go in `tech` or a `.tech` element (`check_designer_first`).
* The browser never asks `127.0.0.1` / `localhost` itself — on a phone that is
  the phone. Ask the hub (`check_page_frame`).
* Every page fits 360–1920 px with no sideways scroll (`check_responsive`).
* No raw colours; tokens only (`check_design_system`, `check_css_tokens`).

## Pages and where they stand (the stage plan in docs/PLAN.html, A41)

| page | file | shared head |
|---|---|---|
| Camera, Voice | `apps/<id>/index.template.html` + `app.js` + `style.css`, built by `tools/build_web.py` | yes |
| Reconize, Photobooth, All-Jao | `apps/<id>/index.html` | yes |
| Home | `main_python/web/home/` (template + `parts/`) → `hub.html`, built by `tools/build_web.py` | yes (A41-3) |
| Studio | `nong/main_python_set_nong/web/` (`app_parts/*.js` → `app.js`) | stage 3 |
| Board site, RGB | `firmware/src/web/WebUI.h`, `main_python/web/rgb.html` | stage 4 |
| Help | `main_python/web/help.html` | stage 5 |
