# A23-1 — Gemini's IDEA note (read this first)

**Four fixed destinations: Show · Rig · Maintenance · Config.** Show is
the live run and holds STOP, pinned boards and active problems. Rig is
where you build the set — every board grouped by where it lives (On WiFi /
On cables here / On other PCs). Maintenance is the careful, machine-
changing work (flash wizard, linking two PCs) done before a show, not
during it. Config is set-once (people, colours, QR, reports, updates).

**One word per board, then what to do next.** Every row leads with
Fine / Lost / Stale / Check / Failed and backs it with a `.next` sentence
("last answered 40s ago — check its power"). A shelf of boards reads in a
glance; colour only repeats what the word already said.

**The flash wizard is seven honest steps**: pick image → pick board
(including boards on other PCs' cables, password asked when the image
must travel) → confirm with route + cost in sentences ("about a minute;
the cable is busy until it finishes; the board keeps its id") → progress
that says its route and admits when it stalls.

**Scope call, stated plainly:** Studio ships as the working engine under
`/g/studio/` with this version's shell (way back to Show, wording); the
module site is a screens+flow spec because no board hosts it.

Files: `web_gemini/hub.html`, `g.css`, `g.js`, `rgb.html`, `help.html`,
`studio/`.
