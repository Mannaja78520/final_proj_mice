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
what is the page's own between them.

## The parts

* **`Mice.Api.get(path)` / `.post(path, body)`** — every call to the hub. Never
  throws; returns `{ok, data, status, needLogin, says, tech}`. `says` is for the
  person, `tech` for the technical switch. No bare `fetch`, no empty `catch`.
* **`new Mice.Status("stat")`** — one status line, five states:
  `.loading() .empty() .error() .stale() .warn() .ready()`, each `(words, tech)`.
  `.from(answer, "saved")` words an Api answer.
* **`new Mice.Partner(id, {status})`** — an outside program from
  `config/partners.json`: `.load()`, `.check()` (the HUB asks it), `.ensure()`
  (start if silent), `.open(which, button)`. A new outside program is an entry
  in that file and a page with one `new Mice.Partner(...)`.
* **`Mice.here(url)`** — a `127.0.0.1` link made to work from a phone.

## Rules the checks hold

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
| Home | `main_python/web/hub.html` | stage 2 |
| Studio | `nong/main_python_set_nong/web/` (`app_parts/*.js` → `app.js`) | stage 3 |
| Board site, RGB | `firmware/src/web/WebUI.h`, `main_python/web/rgb.html` | stage 4 |
| Help | `main_python/web/help.html` | stage 5 |
