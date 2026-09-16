# A23-1 module site — Gemini's screens + flow spec

The page a module board serves about itself (`firmware/src/web/WebUI.h`).
No board is on the bench, so this ships as a spec; after the judgement the
winner's design is applied to WebUI.h. Features are the incumbent's
inventory — nothing added, nothing dropped.

## The idea in one sentence

A board's site reads like the hub's four tabs shrunk to one board: the
same one-word states (Fine / Lost / Stale / Check / Failed), the same
row-plus-next-action language, so the whole toolchain speaks one dialect.

## Screens (one page, four groups mirroring the hub tabs)

1. **Show** — the board right now: name as the headline, ONE WORD state
   beside it (Fine / Stale / Check…), and a `.next` line saying what to
   do ("check its power", "log in to change settings"). Technical detail
   (ip, fw, id) behind the technical switch.
2. **Drive** — Joints/Axes rows (name · slider · number) grouped like the
   Rig tab groups boards; STOP pinned above them. Camera/Speaker/RGB
   appear here only for boards that have them, generated per type.
3. **Maintain** — Moves & sequences list with five states; Zero position
   with an honest confirm sentence; firmware self-report.
4. **Config 🔒** — login first; name, WiFi credentials, hardware pins
   table. Saves say what they restart.

## Flows

- **Opening**: `?dev=…&name=…`; greet by NAME. State word derives from
  real answers only — never invented motion data.
- **Failure**: red banner, failures only; routine progress on the row it
  belongs to (same contract as the hub).
- **Grouped lists**: every group header names WHERE things live
  ("on the card", "in the board"), matching the hub's On WiFi /
  On cables here / On other PCs pattern.

## Why a designer moves faster

One vocabulary everywhere: learn "state word + next action" once at the
hub and every board page is already legible. New per-type features are a
new group under Drive, not a new layout.
