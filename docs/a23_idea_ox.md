# A23-1 — ox-alpha's IDEA note (read this first)

**The hub is a workbench, not an app with menus.** Show night has three
questions, in order: *what is running* (Tonight), *what do I set up*
(Set up), *what broke* (When something goes wrong). The page is one long
bench in that order — no tabs to learn, nothing is ever more than a
scroll away. Sheets handle the jobs you open and close (flash wizard,
pairing, settings); real routes stay real URLs.

**Every card is the same skeleton.** Title · state line · body · actions,
with the five states written ONCE on the skeleton — so loading, empty,
error, stale and ready look and read the same everywhere. A designer adds
a feature by adding a card, never by designing a screen.

**Words carry state, colour only backs them up.** "last answered 40s ago
— check its power", not a yellow dot. Sliders speak ("dim ↔ bright").
Failures are the only thing allowed in the red banner; everything else
lives on the card it belongs to.

**Scope call, stated plainly:** Studio ships as the working engine under
`/o/studio/` with this version's shell (way home, wording) — re-deriving
a 209 KB editor's IA without a bench to test it against risked the one
surface people make their living in. The module site is a screens+flow
spec for the same reason (no board hosts it).

Files: `web_ox/hub.html`, `ox.css`, `ox.js`, `rgb.html`, `help.html`,
`studio/`.
