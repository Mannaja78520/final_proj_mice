# What the prize machines would like from the friend's apps (A47-4)

Our side is built and works without any of this (tested with pretend machines).
Each item makes a link better; none is required.

## The games (All-Jao-Games)

1. **When a player wins, ask for a prize**: `POST http://<hub>:8642/api/gacha/dispense`
   with JSON `{"item": "<kind>", "person": "<name or @face>", "app": "all-jao"}`.
   From the same PC no login is needed (JSON, no browser headers). Show the
   answer's `message` on the game screen: it says which machine to go to,
   including when the first machine is empty.
2. **Which prize for which result**: a list from the game (game, result → kind),
   or let us keep that list in `config/gacha.json`. Tell us the game names and results.
3. **Optional**: a webhook address of yours to hear `gacha.dispensed`,
   `gacha.out` (a kind ran out everywhere), so the game can stop offering it.

## Face_Regonize

1. **Who is in front of camera X right now** (already asked 2026-10-09:
   `GET /api/node/{id}/present`). We use it for `person: "@face"`; today we
   fall back to our own camera look or the recent arrivals.
2. **A group or tag per person** (e.g. `vip`, `staff`) in the person record, so
   a rule can say "every vip gets 3" without listing names. We would read it
   from the person list the same way we read names.
3. **The same name spelling everywhere**: rules match the name exactly as your
   app reports it (case does not matter).
4. **Your Google Sheet layout**: if your app pulls people from a sheet, tell us
   the tab/column names so the prize rules sheet can sit beside it with the same
   habits (ours: tabs `items` and `people`, see docs/gacha/README.md).
