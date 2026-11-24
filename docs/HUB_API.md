# Hub API (generated, do not edit)

Made by `python tools/api_index.py`. The hub also serves this list at
`GET /api`. Base: `http://<hub>:8642`. Anything that moves, flashes or
deletes needs a login cookie (`POST /api/login`). Errors are always
`{"ok": false, "error": "<plain words>"}`; a 401 adds `"need_login": true`.

## Start here (checked against the running hub)

- Log in: `curl -c cookie -X POST http://127.0.0.1:8642/api/login -d '{"password":"..."}'`
- What is connected: `curl http://127.0.0.1:8642/api/modules` (reading needs no login)
- Cables on this PC: `curl http://127.0.0.1:8642/api/ports`
- Send a board command: `curl -b cookie 'http://127.0.0.1:8642/api/usb/cmd?port=COM3&c=STATUS'`
- Show progress of a play: `curl http://127.0.0.1:8642/api/play`
- Pages the hub offers: `curl http://127.0.0.1:8642/api/apps`

A `-` in the table means the code has no comment for that URL yet.

| Method | Path | What | Query values | Defined in |
|---|---|---|---|---|
| GET | `/api/access` | - | - | hub_api_apps.py |
| GET | `/api/ai-status` | - | - | hub_api_apps.py |
| GET | `/api/all-jao/start` | - | - | hub_api_apps.py |
| GET | `/api/allmods` | every module on every PC, this one included scan_hubs() already finds the other hubs on this subnet (it is wha | force | main.py |
| GET | `/api/app` | - | - | hub_api_support.py |
| GET | `/api/app/version` | - | - | hub_api_support.py |
| GET | `/api/apps` | - | - | hub_api_apps.py |
| GET | `/api/cameras` | - | face | hub_api_cameras.py |
| GET | `/api/cameras/add` | - | - | hub_api_cameras.py |
| GET | `/api/cameras/kinds` | - | - | hub_api_cameras.py |
| GET | `/api/cameras/remove` | - | - | hub_api_cameras.py |
| GET | `/api/diag` | - | - | hub_api_support.py |
| POST | `/api/export` | - | - | main.py |
| GET | `/api/extensions` | - | - | hub_api_extensions.py |
| GET | `/api/extensions/add` | - | - | hub_api_extensions.py |
| GET | `/api/extensions/check` | - | - | hub_api_extensions.py |
| GET | `/api/extensions/pick` | - | - | hub_api_extensions.py |
| GET | `/api/extensions/remove` | - | - | hub_api_extensions.py |
| GET | `/api/extensions/restore` | - | - | hub_api_extensions.py |
| GET | `/api/extensions/update` | - | - | hub_api_extensions.py |
| GET | `/api/faces/start` | - | only | hub_api_faces.py |
| GET | `/api/faces/state` | - | - | hub_api_faces.py |
| GET | `/api/flash` | - | - | hub_api_flash.py |
| POST | `/api/flash` | - | port, type | hub_api_flash.py |
| GET | `/api/flash/at` | flashing a board over its own cable (see Flasher) GET  /api/flash/images   what this PC could flash, and what  | ip | hub_api_flash.py |
| POST | `/api/flash/bus` | and the same job again over the COMMAND channel, which is the only one an RS485 board has — see Flash.start_bu | dev, type | hub_api_flash.py |
| GET | `/api/flash/images` | - | - | hub_api_flash.py |
| POST | `/api/flash/remote` | flashing from ANOTHER PC (see remote_payload) The image arrives over the network and esptool runs HERE, becaus | - | hub_api_flash.py |
| POST | `/api/flash/send` | ...and the other half: | - | hub_api_flash.py |
| GET | `/api/gacha` | - | - | hub_api_gacha.py |
| GET | `/api/gacha/can` | - | - | hub_api_gacha.py |
| GET | `/api/gacha/config` | - | - | hub_api_gacha.py |
| GET | `/api/gacha/event` | - | - | hub_api_gacha.py |
| GET | `/api/gacha/game` | - | - | hub_api_gacha.py |
| GET | `/api/gacha/keys` | - | - | hub_api_gacha.py |
| GET | `/api/gacha/load` | - | - | hub_api_gacha.py |
| GET | `/api/gacha/log` | - | csv, limit | hub_api_gacha.py |
| GET | `/api/gacha/machine` | - | - | hub_api_gacha.py |
| GET | `/api/gacha/rules` | - | - | hub_api_gacha.py |
| GET | `/api/gacha/rules/pull` | - | - | hub_api_gacha.py |
| GET | `/api/gacha/rules/push` | - | - | hub_api_gacha.py |
| GET | `/api/gacha/sheet` | - | - | hub_api_gacha.py |
| GET | `/api/gacha/sheet/read` | - | tab | hub_api_gacha.py |
| GET | `/api/gacha/sheet/script` | - | - | hub_api_gacha.py |
| GET | `/api/gacha/sheet/write` | - | - | hub_api_gacha.py |
| GET | `/api/gacha/stats` | - | - | hub_api_gacha.py |
| GET | `/api/gacha/stock` | - | game, source | hub_api_gacha.py |
| GET | `/api/gacha/voice` | - | - | hub_api_gacha.py |
| GET | `/api/gestures` | - | - | hub_api_studio.py |
| GET | `/api/help/apps` | - | - | hub_api_help.py |
| GET | `/api/hubs` | - | force | hub_api_studio.py |
| GET | `/api/list` | studio: | deep, kind | hub_api_studio.py |
| GET | `/api/load` | - | name | hub_api_studio.py |
| GET | `/api/loadseq` | - | name | hub_api_studio.py |
| GET | `/api/logout` | - | - | main.py |
| GET | `/api/mine` | - | - | main.py |
| POST | `/api/model/upload` | - | name | hub_api_studio.py |
| GET | `/api/modules` | - | force | main.py |
| GET | `/api/modules/all` | - | force | main.py |
| POST | `/api/ota` | the same job, over WiFi: | ip, password, type, user | hub_api_flash.py |
| POST | `/api/pair/claim` | - | - | main.py |
| POST | `/api/pair/link` | - | - | main.py |
| POST | `/api/pair/start` | - | - | main.py |
| GET | `/api/pair/status` | pairing: | - | main.py |
| POST | `/api/pair/stop` | - | - | main.py |
| GET | `/api/partners` | - | - | hub_api_apps.py |
| GET | `/api/partners/health` | - | id | hub_api_apps.py |
| GET | `/api/partners/start` | - | id | hub_api_apps.py |
| GET | `/api/partners/version` | - | id | hub_api_apps.py |
| GET | `/api/peers` | - | app, cap | hub_api_peers.py |
| GET | `/api/pinout` | - | dev | main.py |
| GET | `/api/play` | - | - | hub_api_play.py |
| POST | `/api/play` | - | - | hub_api_play.py |
| POST | `/api/play/beat` | - | - | hub_api_play.py |
| GET | `/api/play/home` | the hub as the show clock (see ShowPlayer) POST /api/play   {dev, steps:[{pose[10], t, hold}], loop, name, fro | - | hub_api_play.py |
| GET | `/api/play/stop` | - | - | hub_api_play.py |
| GET | `/api/ports` | - | - | main.py |
| GET | `/api/qr` | the way a phone gets here Printed addresses do not survive a venue: | text | main.py |
| GET | `/api/questions` | - | csv, day | hub_api_gacha.py |
| GET | `/api/questions/topics` | - | - | hub_api_gacha.py |
| GET | `/api/quit` | - | - | hub_api_apps.py |
| POST | `/api/report` | - | - | hub_api_support.py |
| GET | `/api/reports` | - | - | hub_api_support.py |
| POST | `/api/reports` | - | - | hub_api_support.py |
| POST | `/api/rigcad` | - | - | hub_api_studio.py |
| POST | `/api/rigdefault` | - | - | hub_api_studio.py |
| GET | `/api/rigpresets` | - | - | hub_api_studio.py |
| POST | `/api/robot/upload` | - | - | main.py |
| POST | `/api/save` | - | - | hub_api_studio.py |
| GET | `/api/scan` | - | force | main.py |
| GET | `/api/scanusb` | - | force, full, port | main.py |
| GET | `/api/selfupdate` | - | - | hub_api_support.py |
| POST | `/api/seqdelete` | - | - | hub_api_studio.py |
| GET | `/api/seqsteps` | - | name | hub_api_studio.py |
| GET | `/api/servos` | - | - | main.py |
| GET | `/api/settings` | - | - | hub_api_studio.py |
| POST | `/api/settings` | - | - | hub_api_studio.py |
| GET | `/api/settings/peer` | - | host | hub_api_studio.py |
| GET | `/api/show` | - | name | hub_api_play.py |
| GET | `/api/show/delete` | - | - | hub_api_play.py |
| GET | `/api/show/save` | - | - | hub_api_play.py |
| GET | `/api/show/steps` | GET is "the saved show called X"; POST (below) is the draft being edited. | name | hub_api_play.py |
| GET | `/api/show/yaml` | - | - | hub_api_play.py |
| GET | `/api/shows` | shows: | - | hub_api_play.py |
| GET | `/api/speak` | - | - | hub_api_speak.py |
| POST | `/api/speak/stop` | - | - | hub_api_speak.py |
| GET | `/api/speakers` | - | - | hub_api_speak.py |
| POST | `/api/stopall` | - | - | hub_api_play.py |
| GET | `/api/stream` | - | - | hub_api_play.py |
| POST | `/api/stream/feed` | - | session | hub_api_play.py |
| POST | `/api/stream/start` | live audio to a module's speaker (A24-32) POST /api/stream/start  {dev|ip, port, rate, file} -> {session, ...} | - | hub_api_play.py |
| POST | `/api/stream/stop` | - | session | hub_api_play.py |
| POST | `/api/stream/voice` | - | - | hub_api_play.py |
| GET | `/api/themes` | - | - | hub_api_themes.py |
| GET | `/api/themes/images` | - | id | hub_api_themes.py |
| GET | `/api/themes/install` | - | - | hub_api_themes.py |
| GET | `/api/themes/remove` | - | - | hub_api_themes.py |
| POST | `/api/upload/cancel` | - | - | main.py |
| GET | `/api/upload/progress` | the background upload: | - | main.py |
| GET | `/api/usb/close` | - | port | main.py |
| GET | `/api/usb/cmd` | USB command proxy: | c, id, port | main.py |
| GET | `/api/users` | - | - | main.py |
| GET | `/api/version` | - | - | main.py |
| GET | `/api/video/fetch` | - | id | hub_api_studio.py |
| POST | `/api/video/fetch` | - | - | hub_api_studio.py |
| GET | `/api/video/file` | - | id, kind | hub_api_studio.py |
| GET | `/api/video/lan` | - | - | hub_api_studio.py |
| POST | `/api/video/put` | - | name | hub_api_studio.py |
| POST | `/api/video/sound` | - | - | hub_api_studio.py |
| GET | `/api/voice` | - | - | hub_api_apps.py |
| GET | `/api/voice/ask` | - | - | main.py |
| GET | `/api/voice/helper` | - | - | hub_api_apps.py |
| POST | `/api/voice/start` | - | - | hub_api_apps.py |
| POST | `/api/voice/stop` | - | - | hub_api_apps.py |
| GET | `/api/whoami` | - | - | main.py |
