# A23-1 — the shared brief both versions answer

Two complete front-end designs of the Mice hub are built from THIS brief:
one by Gemini Pro, one by ox-alpha. The user judges which wins.
Fair-comparison rule (user, 2026-08-24): both answer the same brief, full
UX + UI — flows, interaction design, information architecture, wording, all
five states — not visual skinning alone. Only the backend stays fixed.

## What is being designed

Five human surfaces. The descriptions below are the FEATURE INVENTORY —
what every surface must keep reachable — NOT a prescription of structure:
both designers may reorganise tabs, flows and wording freely, as long as
a designer can still reach every feature.

1. **Hub** (`hub.html`) — the control centre. Login gate first. Today:
   Home (one row per module, connection state + what to do next),
   Modules (per-type detail, flash over USB/OTA/network, pairing cards),
   Network (scan, two-hub link, WiFi credentials), Tools (RGB strip test,
   voice say/health, complaints/reports screen with translations,
   settings/users, self-update).
2. **Module site** (`firmware/src/web/WebUI.h`) — the page a module board
   serves about itself: identity, joint sliders over USB, moves, config.
   One code base, generated per module type from registries. It cannot be
   hosted side by side (it lives on a board, and no board is on the
   bench), so BOTH designers deliver it as screens + a written flow spec;
   the winner's design is applied to WebUI.h after the judgement.
3. **Nong Studio** (`nong/main_python_set_nong/web/`) — pose & sequence
   editor: 10-joint 3D robot, sliders, timeline keyframes, YAML sequences
   to SD, projects, limits push/pull, settings bundle, keyboard shortcuts.
4. **RGB** (`rgb.html`) — strip colour / effect / brightness.
5. **Help** (`help.html`) — features & help, plain words, offline.

Feature truth lives in `main_python/web/help.html`, the registries
(`tools/registry.py` reading config/*.jsonc) and
`qc/data/designer_words.json` (banned words) — enumerate from there, do
not guess. The API surface is fixed (user, 2026-08-24: *only the backend
stays fixed*): every route `main.py` already answers (~63 `/api/*` +
static). No new endpoints except two additive static mounts:

    /g/…  →  main_python/web_gemini/   (Gemini Pro's version)
    /o/…  →  main_python/web_ox/       (ox-alpha's version)

The incumbent `web/` belongs to NEITHER competitor — it is the baseline
both are judged against. Both versions stay reachable so the user can
compare three ways side by side; the winner is copied over `web/` in a
follow-up task after the judgement. Judgement is the USER'S alone
(settled 2026-08-23): panels find defects before and after; they never
score or pick a winner.

## Rules both versions obey (checked by QC)

* One design system: every page links `/mice.css` + `/themes.css`; colours
  only through tokens; no `:root` blocks in pages. A version MAY ADD new
  tokens — one entry in the shared token file, one block per theme in
  themes.css — what it may never do is copy a colour into its own page.
  A version MAY add its own layout stylesheet built from the tokens
  (Studio's `style.css` is the pattern).
* Designer-first: anything settable is clickable; plain words on the
  surface, technical detail (ids, ports, status codes) behind the
  technical switch; banned words live in DATA at
  `qc/data/designer_words.json` — read it before writing wording.
* All five states everywhere: loading, empty, error, stale, ready.
* Nothing scrolls sideways at any width from 360 px up; `pointer:coarse`
  targets everywhere; verified at 360 / 768 / 1440. Studio's primary
  target stays the desktop, but it must still not break on a phone.
* notice()/banner discipline: failures only; routine progress stays on
  the card's own status line; refusals ("connect first") count as
  failures and DO banner.
* No CDN at runtime; three.js r147 UMD stays vendored in Studio.
* LF endings; no hardcoded lists — new tables go in DATA/registries.
* Dark is the permanent default; every theme in themes.css stays readable.

## Deliverables

Per version: hub, RGB, help and Studio as working pages under the
version's mount; the module site as screens + a written flow spec; plus
a half-page note stating the IDEA — what the information architecture is,
what the flows look like, why a designer moves faster in it. The note is
part of what the user reads when judging.

## Process

This is not a blind contest — the settled division of labour holds:
Gemini designs the visible surfaces, Claude builds and verifies the
logic, several models review. Fairness comes from the SAME brief and the
same QC, not from blinding.

1. Panel brainstorm attacks this brief BEFORE any UI code. (done twice;
   real findings folded back into this file)
2. Gemini Pro designs its full version from this brief (Pro, and wait).
3. ox-alpha designs the other version from the same brief.
4. Both versions: quick suite green, panel review after, land under
   `/g/` and `/o/` with the incumbent untouched at `/`.
