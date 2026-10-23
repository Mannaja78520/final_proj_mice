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
| `apps/gacha/sheet_script.gs` | the sheet's Apps Script: lets the hub read and write the sheet (copy it from the page, it carries the hub's secret) |
| `main_python/gacha_sheet.py` | the ways to the sheet: link (read only), script, service account |
| `docs/gacha/form_sample.gs` | sample Google Form that adds people rows |

## Rules (one Google Sheet, two tabs)

**items**: `event, item, total, per_person, note`. `total` = how many of that
kind in the event, `per_person` = times one person may get it, 0 = no limit.

**people**: `event, person, item, times, special, note`. `person` is the name
as Face_Regonize knows it. `item` `*` = any kind. `times` overrides
`per_person` for that person. `special` = yes marks a special guest: a request
for them with no kind gets the kind on their row.

An empty `event` applies to every event. Column order does not matter, the
header names do.

## The sheet: paste its link, read and write it (A47-15)

Prize machines ▸ **Google Sheet** tab. Paste the sheet's own address. How the hub
gets in is `rules.sheet_way` (config/gacha.json), one class each in gacha_sheet.py:

| way | reads | writes | one-time setup |
|---|---|---|---|
| `link` | yes | no | Share ▸ Anyone with the link (Viewer) |
| `script` | yes (private sheet too) | yes | **Copy the script** on the page, paste in Extensions ▸ Apps Script, Deploy ▸ Web app (Execute as Me, Anyone), paste the Web app URL as Script address |
| `service` | yes | yes | a service account key in `.local/gacha/google_service.json` (never git), share the sheet with its e-mail as Editor; needs `pip install cryptography` |
| `auto` | the first that is set up: script, service, link |

The script refuses anything without the hub's secret (`.local/gacha/sheet_secret.txt`,
made on first use), so its address alone writes nothing. On the page: **Take / Send the
rules**, edit any tab as a table (**Edit a tab of the sheet**), **Every saved rule goes to
the sheet too** (`sheet_auto_push`), **Each prize is a new row** (`sheet_log`, tab `log`).
Tab names: `sheet_tabs {items, people, log}`. Routes: `GET /api/gacha/sheet`,
`GET /api/gacha/sheet/read?tab=`, `POST /api/gacha/sheet/write {tab, rows}`,
`GET /api/gacha/sheet/script` (all login). The older published-CSV links
(`sheet_items_csv`, `sheet_people_csv`) still work when no link is set.
A Google Form can feed the people tab: `docs/gacha/form_sample.gs` makes the form and
adds each answer as a row (same headers), so the hub reads it on the next pull.

A kind may name substitutes: `items.<kind>.instead: ["sticker"]` (page: Kinds ▸ When it
runs out, give instead). When the kind is out on every machine, the first substitute the
person may still have is given, from a machine in the asked machine's `near` list first;
the answer carries `instead_of` and says so (`messages.instead`).

## For other apps (Voice, the friend's game, Face_Regonize)

All JSON, to the hub (`http://<hub>:8642`). A program on the hub PC needs no
login (JSON body, no browser headers); from another PC, log in first
(`POST /api/login`) and send the cookie.

```
POST /api/gacha/dispense {"item": "keychain", "person": "Somchai", "app": "game", "machine": "g1", "wait": false}
  -> {"ok": true, "machine": "g2", "label": "...", "place": "...", "moved": true,
      "seq": 7, "stock": 4, "message": "ตู้ 1 หมดแล้ว เชิญรับ...ที่ตู้ 2 ..."}
  -> {"ok": false, "reason": "person limit reached" | "event closed" | "item used up for this event"
                            | "out everywhere" | "no machine" | "no item" | "busy", "message": "..."}
POST /api/gacha/can      {"item": "keychain", "person": "Somchai"} -> {"ok", "reason", "limit", "had", "special"}
GET  /api/gacha          machines with live stock, kinds, event
```
`person: "@face"` = whoever the face app sees nearest right now. `force: true`
(admin's extra, still counted) needs a logged-in person. Leave out `machine`
for "any machine of that kind"; when it is empty the next machine of the same
kind is used (its `near` list first) and `message` says where to go.

### Another PC, a form, a button somewhere else: app keys (A47-7)

Make a key on the page (**Other PCs and forms ▸ Make a key**, shown once; kept in
`.local/gacha/keys.json`, never in git). Send it as the header `X-Mice-Key` or
`?key=` on the address. A key works on `dispense`, `can` and `game` only: the
limits still apply, `force` is refused, settings are refused.

```
curl -X POST http://<hub>:8642/api/gacha/dispense -H "Content-Type: application/json" \
     -H "X-Mice-Key: <key>" -d '{"item": "keychain", "person": "Somchai", "app": "form"}'
```
```js
// Google Apps Script (a Form's "on submit" trigger)
function onFormSubmit(e) {
  UrlFetchApp.fetch("http://<hub>:8642/api/gacha/dispense?key=<key>", {method: "post",
    contentType: "application/json",
    payload: JSON.stringify({item: e.namedValues["kind"][0], person: e.namedValues["name"][0], app: "form"})});
}
```
(Apps Script runs on Google's servers: the hub must be reachable from the internet
for that one; on the venue WiFi use a program on a PC instead.)

### Games: a win gives a prize (A47-6)

```
POST /api/gacha/game {"game": "quiz", "result": "5", "person": "Somchai", "ref": "<unique id of this win>"}
  -> the dispense answer, or {"ok": false, "reason": "no prize for this result"} (not an error)
```
`config/gacha.json` `"games"`: `[{game, result (pattern), item, machine?, person?}]`, first
fit wins; the page edits it. The same `ref` twice gives once. The friend's All-Jao
Games call this without any change on their side: the hub serves their folder at
`/play/all-jao/` and adds `apps/all-jao/link.js`, which watches what
`config/partners.json` `all-jao.play.watch` names (their localStorage win lists, the
memory game's status text). Allowed for a hub page in this PC's browser (Origin =
this hub), a program on this PC, a key, or a login.

### Webhooks (config `webhooks.<kind>`: list of addresses)

Each gets `POST` JSON with `type` = `gacha.dispensed` (fell; `result` done),
`gacha.jam` (stuck), `gacha.empty` (a machine ran out), `gacha.out` (a kind
ran out on every machine), `gacha.low` (few balls left), `gacha.refused`.
The other fields are the log row: `machine, item, person, app, seq, stock,
result, reason, message, event, time`.

## The board itself

`firmware/COMMANDS.md` ▸ gacha module: `GDISPENSE`, `G?`, `GSTOCK`, `GEVENT`,
`GCFG`... over HTTP `/api/cmd` or RS485 `#<id> ...`.
