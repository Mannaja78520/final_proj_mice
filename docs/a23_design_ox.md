# ox-alpha's version — design spec

Answer to `docs/a23_brief.md`. Same features, same APIs, same token
system. The idea in one line: **the hub is a workbench, so the page is a
workbench — one card per job, laid out in the order a show night uses
them, everything else a sheet over it.**

## Information architecture

No tabs. `hub.html` is ONE page with three zones top to bottom, each zone
a heading plus cards, with a slim sticky section nav that appears only
after login:

1. **Tonight** — the doing zone. One card per module the scan can see,
   biggest card = the module you last acted on. Each module card shows:
   who it is (name, type badge), where it is (cable or WiFi, plain
   words), what it is doing now, and the two or three actions that type
   of show actually needs (nong: play/stop a sequence, relax, zero;
   lift: up/down/stop; cam: snap/watch). Anything rarer lives behind
   "More…" which opens the module's own sheet.
2. **Set up** — getting ready. Cards: put new software on a board
   (flash), introduce a new module to the rig (pairing), link a second
   PC, name and find this hub (QR + mDNS).
3. **When something goes wrong** — complaints/reports, the help page
   link, voice health, self-update.

RGB test, voice try-it and other tools become sheets opened FROM the
module card they belong to (the nong card offers "try the speaker"),
not destinations somebody has to know exist. Help stays a real page —
it is documentation, offline. Studio stays its own app, reached from the
module card ("edit poses").

Separate routes stay real URLs (`/o/rgb`, `/o/help`) because bookmarks
and QC need them; the sheets are progressive enhancement, not the only
way in.

## The card pattern (one skeleton, five states)

Every card on every surface is the same HTML pattern with four slots —
title, state line, body, actions — and five state classes:

* `loading` — state line says what is being fetched, body dims, actions
  disabled but visible (no layout jump);
* `empty` — one plain sentence saying what would appear here and the
  button that makes it happen ("Nothing here yet — scan the network");
* `error` — the state line becomes the failure in visitor words, the
  action slot offers exactly one retry;
* `stale` — data older than its refresh promise: a thin amber edge and
  "last seen 2 min ago", nothing else changes;
* `ready` — normal.

The red banner keeps its batch-5 contract: failures only, refusals
included, routine progress never leaves the card's own state line.

## Flows

* **Connect → act**: plugging a cable or powering a board moves its card
  from empty to ready by itself (scan already runs); the designer never
  presses refresh first. If login is missing, EVERY action button opens
  the login sheet instead of erroring.
* **Flash** stays a wizard of three steps maximum — pick the board, pick
  the software, watch it go — each step one screen, back always safe,
  and the confirmation names the board, the software and this PC.
* **Failure recovery**: every error card's retry is joined by a "what
  does this mean?" toggle that shows the technical detail (port, id,
  status code) — hidden until asked, per the designer-first rule.
* **Zero-cost wording**: labels are sentences ("Put new software on a
  board"), values are answers ("on cable 7", "last seen just now"),
  never field names.

## Tokens added (one entry each, themes.css owns colour)

* `--warn-edge` — the stale card edge, already implied by --warn;
* `--card-gap` — the one grid gap every zone shares (shape, mice.css);
* `--tap` — minimum coarse-pointer target (shape, mice.css).
Nothing else; the existing twelve colour tokens carry the palette.

## Per-surface notes

* **Module site**: same card pattern; identity card, live control cards
  generated per module type from the registry; config behind "More…".
  Delivered as screens + flow spec per the brief (no board needed).
* **Studio**: keeps its desktop-first three-pane body (robot / sliders /
  timeline — that layout earns its place), but adopts the card pattern
  for its side panels, the same five states on every list (projects,
  sequences, ports), and sentence labels. Timeline keys get a plain-words
  status line under the canvas instead of console-style output.
* **RGB**: one card — big colour pad, effect picker as thumbnail chips,
  brightness as a slider with the value spoken in words at the ends
  ("dim" … "full").
* **Help**: unchanged structure (it was rebuilt in batch 5), re-skinned
  onto the card pattern so its sections match the hub's zones.
