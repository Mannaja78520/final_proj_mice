# Prize machines (gachapon) — A47

One hub app (**Prize machines**, `/app/gacha/`) drives any number of gacha
boards (firmware type `gacha`, `pio run -e mice_gacha`). The board counts,
turns and refuses; the hub decides which machine, who may have one, and logs.

| file | what |
|---|---|
| `config/gacha.json` | machines, kinds, event, sheet links, webhooks, words (edited from the page) |
| `.local/gacha/rules.json` | the rules in use (people's names: never in git) |
| `.local/gacha/dispense_log.csv` | one row per prize, refusal, landing or jam |
| `.local/gacha/events.jsonl` | everything: settings, rules, board commands, webhook results |
| `main_python/gacha.py` | the brain; `main_python/hub_api_gacha.py` the routes |
| `docs/gacha/*.sample.csv` | sample rules = the Google Sheet layout |
| `docs/gacha/apps_script.gs` | optional write-back to the sheet |

## Rules (one Google Sheet, two tabs)

**items**: `event, item, total, per_person, note`. `total` = how many of that
kind in the event, `per_person` = times one person may get it, 0 = no limit.

**people**: `event, person, item, times, special, note`. `person` is the name
as Face_Regonize knows it. `item` `*` = any kind. `times` overrides
`per_person` for that person. `special` = yes marks a special guest: a request
for them with no kind gets the kind on their row.

An empty `event` applies to every event. Column order does not matter, the
header names do. Pull: in the sheet, File ▸ Share ▸ Publish to web ▸ choose the
tab ▸ CSV, paste each link on the page, press **Take them from the sheet**.
A Google Form can feed either tab later (form responses → a sheet with the same headers).

## For other apps (Voice, the friend's game, Face_Regonize)

All JSON, to the hub (`http://<hub>:8642`). A program on the hub PC needs no
login (JSON body, no browser headers); from another PC, log in first
(`POST /api/login`) and send the cookie.

```
POST /api/gacha/dispense {"item": "keychain", "person": "Somchai", "app": "game", "machine": "g1", "wait": false}
  -> {"ok": true, "machine": "g2", "label": "...", "place": "...", "moved": true,
      "seq": 7, "stock": 4, "message": "ตู้ 1 หมดแล้ว เชิญรับ...ที่ตู้ 2 ..."}
  -> {"ok": false, "reason": "person limit reached" | "event closed" | "item used up for this event"
                            | "out everywhere" | "no machine" | "no item", "message": "..."}
POST /api/gacha/can      {"item": "keychain", "person": "Somchai"} -> {"ok", "reason", "limit", "had", "special"}
GET  /api/gacha          machines with live stock, kinds, event
```
`person: "@face"` = whoever the face app sees nearest right now. `force: true`
(admin's extra, still counted) needs a logged-in person. Leave out `machine`
for "any machine of that kind"; when it is empty the next machine of the same
kind is used (its `near` list first) and `message` says where to go.

### Webhooks (config `webhooks.<kind>`: list of addresses)

Each gets `POST` JSON with `type` = `gacha.dispensed` (fell; `result` done),
`gacha.jam` (stuck), `gacha.empty` (a machine ran out), `gacha.out` (a kind
ran out on every machine), `gacha.low` (few balls left), `gacha.refused`.
The other fields are the log row: `machine, item, person, app, seq, stock,
result, reason, message, event, time`.

## The board itself

`firmware/COMMANDS.md` ▸ gacha module: `GDISPENSE`, `G?`, `GSTOCK`, `GEVENT`,
`GCFG`... over HTTP `/api/cmd` or RS485 `#<id> ...`.
