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

## Studio is cut the same way (A41-4)

`nong/main_python_set_nong/web/`, never `index.html` or `app.js` (both BUILT):

* `index.template.html` — the map: one `<!-- part: x.html -->` line per area.
* `html_parts/<area>.html` — header, view (3D + view buttons), login, pose,
  sequence, robot, shows, setup, timeline. A side-panel card belongs to the
  part of the tab it shows on (`data-stab`).
* `app_parts/*.js` — the script, one job per file, in `web_build.json`'s
  `studio.parts` order (they share one script).
* `style.css` — Studio's own; it stays a file (Studio is a full-window tool,
  `body.app`, not the `body.page` column).
* Studio has ONE name box and ONE Save, both in the head. The timeline row is
  only what you do to the timeline; the saved-file list and "Then run" live
  in the Sequence tab. A new timeline button is a toolbar button: it must not
  make the row wrap at 1280 px (`check_studio_layout` measures the 3D view).
* Its head status line (`save_state.js`) says saved / not saved; save, load
  and timing detail still go to the timeline's own line, failures to
  `notice()` (seen on every tab).

## Help is cut the same way (A41-6)

`main_python/web/help/`, never `help.html` (BUILT, listed in `web_build.json`):

* `index.template.html` — the shared head, the sidebar and the ORDER of the
  sections: by what the reader is doing (use it, build and set up, when
  something is wrong), not by where the code runs.
* `parts/<section>.html` — one `<section id=...>` each; `parts/search.js` the
  search box and the sidebar highlight; `style.css` the document type scale
  (Help is a document, so it keeps its own wider two-column frame, not
  `body.page`).
* A new section is a part file, one `<!-- part: -->` line, one sidebar link
  and one link in `bytask.html` (`check_help_links` fails an orphan).
* Code paths in a section's `.where` label carry `tech`.

## The board's own site (A41-5)

`firmware/src/web/WebUI.h` is served from the board's flash, and also whole by
the hub at `/mod?dev=...`. mice-ui.js does not fit in flash, so its head is
the same markup written out: `<header class="topbar">`, then `#hubBack`
(`class="topbar-home"`, "← Hub", hidden until showHubLink knows where the hub
is), the name, `#hnow` (what it is doing, in words), its own button, the
`topbar-adv` switch last, and the badges in a `.sub` line under it. Keep it
small: every byte is in mice_nong's OTA slot. Its own frame (wider grid of
cards) stays; it is not `body.page`.

A page about one module names it with ONE address: `?dev=wifi:<ip>` or
`?dev=usb:<port>[:<bus id>]`, and sends commands to `/api/dev/cmd?dev=`
(the light strip page `rgb.html` too; its old `?ip=` / `?port=&id=` still
open). A read the person may do logged out must not come back 401: a
command `"query": true` in `firmware/config/commands.json` is free through the
hub as on the board (`hub_auth.free_read`). Anything else refused is said in
words (`refusal()` on the board site) and asked again after a login, not on
every status push.

## The parts

* **`Mice.Api.get(path)` / `.post(path, body)`** — every call to the hub. Never
  throws; returns `{ok, data, status, needLogin, says, tech}`. `says` is for the
  person, `tech` for the technical switch. No bare `fetch`, no empty `catch`.
  Default timeout 8 s; pass `{timeout: ms}` for a slow one. (Home's login,
  accounts and pairing use it, and Studio's project save, load and list; the
  rest of both still call `fetch`, which mocks in QC replace - move a call
  when you next change it.)
* **`new Mice.Status("stat")`** — one status line, five states:
  `.loading() .empty() .error() .stale() .warn() .ready()`, each `(words, tech)`.
  `.from(answer, "saved")` words an Api answer.
* **`new Mice.Partner(id, {status})`** — an outside program from
  `config/partners.json`: `.load()`, `.check()` (the HUB asks it), `.ensure()`
  (start if silent), `.open(which, button)`. A new outside program is an entry
  in that file and a page with one `new Mice.Partner(...)`.
* **`new Mice.Tabs("tabs", [{id, label, icon, load}])`** — a page in sections, one
  shown at a time (the friend's Reconize layout, user 2026-10-23). Markup
  `<div class="tabbed"><nav id="tabs"></nav><div> cards with data-tab="id" </div></div>`;
  the list sits beside the content on a wide screen and above it on a phone,
  the open section is kept in the address (`#id`), `load` runs when it opens.
  Every app page with more than one job uses it (`check_mice_tabs`).
* **`Mice.here(url)`** — a `127.0.0.1` link made to work from a phone.

## Rules the checks hold

* One login place per screen. A page with its own login form marks it
  `data-login-here`; a gated card (`data-needs-login`) then shows one line
  pointing at it instead of a second login card (`check_page_login`).
* Plain words on the surface. Addresses, ports, paths, commands, ids and status
  codes go in `tech` or a `.tech` element (`check_designer_first`).
* The browser never asks `127.0.0.1` / `localhost` itself — on a phone that is
  the phone. Ask the hub (`check_page_frame`).
* Every page fits 360–1920 px with no sideways scroll (`check_responsive`;
  the plan is held at phone widths only).
* No raw colours; tokens only (`check_design_system`, `check_css_tokens`).

## Pages and where they stand (the stage plan in docs/PLAN.html, A41)

| page | file | shared head |
|---|---|---|
| Camera, Voice | `apps/<id>/index.template.html` + `app.js` + `style.css`, built by `tools/build_web.py` | yes |
| Reconize, Photobooth, All-Jao | `apps/<id>/index.html` | yes |
| Home | `main_python/web/home/` (template + `parts/`) → `hub.html`, built by `tools/build_web.py` | yes (A41-3) |
| Studio | `nong/main_python_set_nong/web/` (`index.template.html` + `html_parts/` → `index.html`, `app_parts/*.js` → `app.js`) | yes (A41-4) |
| Board site | `firmware/src/web/WebUI.h` (master; `gen_tables.py` cuts one per module type) | yes, written out (A41-5) |
| Light strip (RGB) | `main_python/web/rgb.html` | yes (A41-5) |
| Help | `main_python/web/help/` (template + `parts/`) → `help.html`, built by `tools/build_web.py` | yes (A41-6) |
| Plan | `docs/PLAN.html` (hand-written top, STATE from `tools/plan.py`) | no: a reference document; a wide table goes in `<div class="wrap">` |
