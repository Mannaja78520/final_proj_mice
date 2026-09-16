# A23-1 module site — ox-alpha's screens + flow spec

The page a module board serves about itself (`firmware/src/web/WebUI.h`).
No board is on the bench, so this ships as a spec; after the judgement the
winner's design is applied to WebUI.h. Features are the incumbent's
inventory — nothing added, nothing dropped.

## The idea in one sentence

A board's site is ONE CARD PER CONCERN on the same workbench skeleton as
the hub: title line, state line, body, actions — so a designer who learned
the hub already knows how to read a board.

## Screens (all one page, sections in reach order)

1. **Who this is** — name, type badge with the type-coloured edge, id.
   State line speaks: "answering · firmware 1.4" or, stale,
   "last answered 40s ago — check its power". Technical switch reveals ip,
   fw hash. Actions: back to the hub that opened it.
2. **Joints** (nong) / **Axes** (lift) — one row per joint: name, slider,
   number. Loading dims rows; a joint that refuses says so on its own row.
   STOP button pinned at the card top, red, always reachable.
3. **Moves & sequences** — list from SD with the five states exactly as
   the hub's flash wizard: loading / empty ("card has no moves yet") /
   error ("could not read the card") / stale (keeps last good list, says
   old) / ready. Run and Stop beside the list.
4. **Zero position** — "set THIS pose as home" with a confirm sentence:
   what it overwrites and why 90°/joint matters.
5. **Speaker & camera & RGB** — only the cards this board actually has
   (generated per type from the registries). Same anatomy; camera shows
   its frame in the state slot when live.
6. **Setup 🔒** — login first (refusals banner). Name, WiFi credentials,
   pins table behind the technical switch. Save buttons say what a save
   restarts.

## Flows

- **Opening**: hub hands over `?dev=…&name=…`; the site greets by NAME,
  never by port. Login gate appears only when an action needs it.
- **Failure anywhere**: notice() = fail banner only, per the shared
  wording contract; polling never writes it.
- **Every settable thing clickable**: no value requires typing a URL or
  editing a file; pins/wifi stay visible but read-only until Setup.

## Why a designer moves faster

One skeleton + five states written once means each new concern is "one
more card", not a new screen design. The type edge and the word+colour
states are the same ones as the hub, so training happens once.
