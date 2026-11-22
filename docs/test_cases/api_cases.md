# API / hub test cases (brainstorm, verified against code 2026-11-22)

Target: hub on `localhost:8642` plus fake serial (`qc/lib/fake_serial.py`), `fake_wifi.py`, `fake_friend.py`, `bus_sim.py`. Nothing here is tested on real hardware. P1 = safety, data loss, security, hub down; P2 = correctness and polish. Code cites are `file:line` under `main_python/` unless noted. Rows marked as flags are suspected gaps found by reading code, to be confirmed by running.

| ID | area | steps | expected | how to automate |
|---|---|---|---|---|
| API-001 (P1) | Input | POST /api/save with body missing fields (`{}`), then `[]`, then `null` | 400 JSON {ok:false,error} in plain words, no 500/traceback; file list unchanged | requests.post json=; assert status<500 and body['ok'] is False |
| API-002 (P1) | Input | POST /api/save name `../../config/hub_auth` and `..\..\x`, `%2e%2e/`, absolute `C:\x` | rejected by safe_name (SAFE_NAME `^[A-Za-z0-9._ -]{1,80}$`, no leading dot; main.py:383,400); nothing written outside data dir | post, then compare file tree snapshot (os.walk hash) before/after |
| API-003 (P1) | Input | GET /api/load?name=../hub_auth.json and name=.hidden | 400; no file contents returned | assert 'salt' not in r.text |
| API-004 (P2) | Input | GET /api/load?name= (empty), name=<81 chars>, name=with NUL `%00` | 400 each, not 500 | param loop |
| API-005 (P2) | Input | Save a sequence named with unicode (Thai `สวัสดี`, emoji, NFC vs NFD é) | SAFE_NAME rejects with plain message (not crash); documented in HUB_API; no half-written file | post utf-8 json; check list unchanged |
| API-006 (P2) | Input | POST /api/save with wrong types: steps as string, pose with 9 or 11 values, t negative, hold NaN/1e999 | 400 per case, show list unaffected | parametrized json; Python json emits NaN |
| API-007 (P1) | Input | POST body 200 MB to /api/save (NEVER_GATED route, no login) | 413 "too big" (main.py:1850; cap 100 MB for NEVER_GATED); connection closed, hub still answers next GET | stream generator body; then GET /api/version |
| API-008 (P1) | Input | Content-Length lies: header 2 GB, send 10 bytes; and header 10, send 1 MB | no RAM blowup, hub alive; 413 or 400 within timeout | raw socket via socket.send |
| API-009 (P2) | Input | Content-Length negative, non-numeric (`abc`) on every POST route | no 500 stack; max(0,int()) crash on `abc` is ValueError (main.py:1841) - expect clean 400 | raw socket sweep over POST routes in api_index.json |
| API-010 (P2) | Input | Invalid JSON (`{`), wrong Content-Type (form-urlencoded) on each POST route | 400 plain error; comment main.py:2399 says JSON only | iterate api_index.json POST entries |
| API-011 (P2) | Input | Query string with repeated keys, `?name=a&name=b`, 10 KB query, invalid %-escape `%zz` | first value used or 400; no 500 | requests params list |
| API-012 (P2) | Input | Unknown path /api/nope, /api/../etc/passwd, //api//modules, trailing slash /api/modules/ | 404 JSON {ok:false}; no file read | loop statuses |
| API-013 (P2) | Input | HTTP methods: PUT/DELETE/OPTIONS/HEAD on /api/modules | 405/501 or clean error, no hang | requests.request |
| API-014 (P1) | Input | GET /api/logout and other state-changing GET routes (extensions/add, show/save, show/delete, gacha/load, usb/cmd) from cross-site Referer/Origin | state change via GET is CSRF-able; assert the hub's JSON-only/Origin rule (main.py:2399) rejects or login cookie SameSite=Lax limits it; document | requests with Origin: http://evil |
| API-015 (P2) | Input | Static pages path traversal: GET /hub.html/../../main.py, /%2e%2e/config/hub_auth.json, backslash variants | 404; never serves config or .py | requests with raw urls (urllib3 no-normalise) |
| API-016 (P2) | Input | Huge unicode filename in /api/video/put?name= and /api/model/upload?name= | 400 by safe_name; no temp file left | post then os.listdir temp dir |
| API-017 (P2) | Input | /api/speak with text 1 MB, text of only whitespace, text with control chars/RTL marks | empty -> "nothing to say" (hub_speak.py:259); big text bounded or rejected, queue not wedged | get/post, then GET /api/speak status |
| API-018 (P2) | Input | /api/usb/cmd with c= containing newline/CR (`STATUS%0AFLASH`), 4 KB, and non-ASCII | newline injection blocked: only one wire line reaches fake serial | fake_serial.wire assert single line |
| API-019 (P1) | Input | /api/usb/cmd?port=COM99 (absent), port=../x, port empty | 404/400 plain error, no port opened; no thread leak | requests + fake_serial open-count |
| API-020 (P2) | Input | /api/qr?text= 10 KB, empty, unicode | bounded response or 400 | requests, assert len(body)<1MB |
| API-021 (P2) | Input | /api/gacha/log?limit=-1, limit=abc, limit=999999999 | hub_api_gacha.py:252 does int() on raw value: abc must be 400 not 500 | param loop; flag if 500 |
| API-022 (P2) | Input | /api/questions?day=garbage&csv=1 | clean error, valid CSV header otherwise | requests |
| API-023 (P2) | Input | /api/list?kind=nonsense&deep=1 | empty list or 400, no 500 | requests |
| API-024 (P2) | Input | /api/settings POST: 5 MB, empty, non-object, unknown keys, key with dots (`a.b`) | 413 for oversize (hub_api_resources.py:60); unknown keys ignored or rejected; file still valid JSON after | post then json.load config file |
| API-025 (P2) | Input | POST /api/settings with valid JSON that breaks invariants (port=-1, port=99999, route_latency negative) | rejected; hub restarts clean with stored value | post, restart harness, check boot |
| API-026 (P1) | Concurrency | Two clients POST /api/save same name 50x each in parallel with different content | file always parses as one writer's whole content (atomic write main.py:411, per-writer temp name 427); no .tmp leftovers | threading.Thread pool, final json.load + glob *.tmp |
| API-027 (P1) | Concurrency | Concurrent save + delete (/api/seqdelete) same name | either order ends consistent: file exists whole or absent; no 500 | thread pool with barrier |
| API-028 (P2) | Concurrency | Two clients save different names simultaneously, 200 total | all 200 listed in /api/list | pool, set compare |
| API-029 (P2) | Concurrency | Concurrent /api/settings POST x2 (different keys) | last-writer-wins at worst, no corrupted JSON, no lost keys unless racing same key | pool + json.load |
| API-030 (P1) | Concurrency | 100 parallel GET /api/modules?force=1 while a show plays | hub stays responsive (<2 s for /api/play), show timing not delayed beyond tolerance | pool; record show beat timestamps in fake_serial.wire |
| API-031 (P2) | Concurrency | 50 parallel /api/usb/cmd to ONE port | per-port lock serialises (hub-usb header); every wire line intact, replies matched to requests, none interleaved | fake_serial.wire line-by-line regex |
| API-032 (P2) | Concurrency | Parallel /api/upload/progress + /api/upload/cancel during upload | cancel stops upload; progress final state cancelled, temp removed | thread + poll |
| API-033 (P2) | Concurrency | Parallel logins from 20 clients with correct password | all get distinct tokens, no corruption of hub_auth.json | pool, then json.load store |
| API-034 (P2) | Concurrency | ThreadingHTTPServer slow-loris: open 200 sockets sending 1 byte/s headers | other clients still served (thread-per-request); document limit | raw sockets |
| API-035 (P1) | Auth | Call every gated route (api_index.json POST + moves/flash/delete) with no cookie | 401 with need_login:true as HUB_API.md claims; nothing reaches fake_serial.wire | iterate index, assert 401 and wire empty |
| API-036 (P1) | Auth | Read routes (/api/modules, /api/ports, /api/play, /api/apps) with no cookie | 200 (doc says reading needs no login) | requests |
| API-037 (P1) | Auth | POST /api/login wrong password | 401 plain error; counts toward lock (hub_auth.py:333 _MAX_TRIES=5) | requests |
| API-038 (P1) | Auth | Brute force: 5 wrong then correct password immediately | locked for _LOCK_SECONDS=60 even with right password; message names wait; unlock after 60 s (patch via monkeypatch of _LOCK_SECONDS in test hub) | loop, then time.sleep or short-lock env |
| API-039 (P1) | Auth | Brute force from two source IPs / spoofed X-Forwarded-For header | lock keyed on real peer (who in hub_auth.py:808), XFF cannot reset counter | requests with header, 6 tries |
| API-040 (P2) | Auth | Lockout on user A does not lock user B; successful login resets counter (hub_auth.py:847) | B logs in; A count cleared after success | sequence test |
| API-041 (P1) | Auth | Login with no body, `{}`, password as number/list/null, 10 MB password | 400/401, no 500; oversize 413 (NEVER_GATED cap) | param loop |
| API-042 (P2) | Auth | Password limits: 7 chars, 33 chars, containing space, unicode (PASS_MIN..PASS_MAX 32, no spaces; hub_auth.py:517) | change-password rejects with message; login with such password simply fails | requests |
| API-043 (P2) | Auth | Username rules: 21 chars, empty, `../x`, unicode, case variants Admin vs admin | add_user rejects (NAME_MAX=20, valid_name); duplicate by case decided and documented | requests with admin cookie |
| API-044 (P2) | Auth | Add 17th account (MAX_USERS=16) | error "this hub already has 16 accounts" (hub_auth.py:633) | loop add_user |
| API-045 (P1) | Auth | Remove the only super_admin account | refused "everyone would be locked out" (hub_auth.py:647) | requests |
| API-046 (P1) | Auth | Default password admin123 on fresh store: forced change (must_change); all gated routes blocked until changed? | must_change flag returned in /api/whoami; behaviour matches docs | fresh hub_auth.json fixture |
| API-047 (P1) | Auth | Token expiry: idle 12 h (_IDLE_SECONDS) | after idle limit cookie rejected 401 need_login; activity refreshes window | monkeypatch time.time/monotonic in in-process hub or set short idle via test store |
| API-048 (P2) | Auth | Forged cookie: random 32 hex, truncated, other user's token after logout, token after password change | 401 each; change_password keeps only keep_token (hub_auth.py:601) | requests with cookie |
| API-049 (P1) | Auth | Logout then replay old cookie | 401; Set-Cookie Max-Age=0 sent (main.py:2591) | requests Session |
| API-050 (P2) | Auth | Cookie flags: HttpOnly, SameSite=Lax present; Secure absent on http (LAN) | inspect Set-Cookie header | requests |
| API-051 (P2) | Auth | NEVER_GATED routes (/api/play/stop, /api/stopall, /api/speak/stop, /api/stream/stop) without login | 200 and actually stop; fake_serial.wire shows stop pose / STREAM OFF | requests then wire assert |
| API-052 (P1) | Auth | Surprise: NEVER_GATED includes /api/save, /api/export, /api/model/upload, /api/rigdefault (hub_auth.py:202-207): anonymous overwrite of rig default | test records behaviour; P1 decision: expect either gated or documented as Studio-open; HUB_API.md says writes need login | post without cookie, diff files |
| API-053 (P2) | Auth | Per-app key header X-Mice-Key and ?key= (hub_api_gacha.py:197) wrong/empty/very long | 401 for wrong; key in URL not echoed in logs | requests, grep hub log |
| API-054 (P2) | Auth | Pair flow: /api/pair/start, claim with wrong code, claim twice, stop mid-way, link to unreachable host | wrong code rejected and rate-limited; second claim fails; stop clears code (hub_pair.py) | two hub instances on ports 8642/8643 via fake_friend |
| API-055 (P2) | Auth | page_access.json: page requiring login accessed with/without cookie (hub_auth.py:243 page_here_ok) | gated page returns login redirect or 401, public page 200 | iterate config/page_access.json |
| API-056 (P2) | Auth | Board login sync (config/board_logins.json) after password change | boards get new credential on wire; old rejected | fake_serial.wire assert, check_board_login_sync |
| API-057 (P2) | Auth | Export/import accounts (hub_auth.py:662,676): clash on first attempt reports, changes nothing; replace=True | exact skip/clash lists; role escalation via import impossible for non-super | requests with user cookie |
| API-058 (P1) | Auth | Normal user (role user) calls super-only routes (add/remove user, import) | 403 not 401 | requests with user cookie |
| API-059 (P1) | Startup | Fresh PC: empty config/ dir, no hub_auth.json | hub starts, creates store with generated password, writes plain file (hub_auth.py:436,469), logs where | tmp cwd copy of tree minus config; subprocess main.py; poll /api/version |
| API-060 (P1) | Startup | Config files missing one at a time (settings.json, speakers.json, route_latency.json, page_access.json) | defaults used, no crash, /api/diag lists problem | loop delete each, boot, GET /api/diag |
| API-061 (P1) | Startup | Config file corrupt (truncated JSON, BOM, UTF-16, zero bytes) | hub boots with defaults, corrupt file preserved/renamed not overwritten | write bad bytes, boot, check file |
| API-062 (P1) | Startup | Data dirs missing (sequences, shows, reports, gacha data_dir) | created on demand; /api/list returns empty not 500; first save works | rm -rf dirs then post |
| API-063 (P1) | Startup | Port 8642 busy (another listener) | clear message and non-zero exit or fall back; no silent hang; /api/quit of old hub not invoked unauthenticated | socket.bind 8642 then run main.py, assert exit code/message |
| API-064 (P2) | Startup | Port 80 (short name) unavailable/permission denied | hub still serves on 8642 (hub.md says 8642 plus 80) | run as non-root on Linux, GET :8642 |
| API-065 (P1) | Startup | Read-only data dir / config dir | save returns plain error (not 500); hub keeps serving reads; login still works in memory | chmod -w tmp tree; post /api/save |
| API-066 (P2) | Startup | Disk full simulation on save (ENOSPC via tmpfs size 1 MB) | atomic write leaves old file intact, error reported | mount tmpfs / use small loop; post big |
| API-067 (P2) | Startup | Windows path case: ?name=Seq vs seq, config path with different drive-letter case, spaces in install path | same file on NTFS; two names differing only by case do not both exist | run on Windows runner; list after saving both |
| API-068 (P2) | Startup | Install path with non-ASCII user folder (C:\Users\สมชาย\) | hub boots, reads config, writes reports | Windows CI or Wine; boot and save |
| API-069 (P1) | Startup | Two hubs started on same PC | second detects and exits cleanly; first data untouched | subprocess x2 |
| API-070 (P2) | Startup | Kill -9 mid-save, restart | no corrupt json; leftover *.tmp ignored/cleaned | subprocess, os.kill, reboot, json.load |
| API-071 (P2) | Startup | GET /api/quit without login (hub_api_apps.py) | must need login or be loopback only; test from non-loopback address | bind test client to LAN IP; assert 401 and hub alive |
| API-072 (P2) | Startup | Graceful shutdown: SIGINT/SIGTERM and /api/quit while show playing and upload running | arm stop sent (wire), ports closed, audio stopped, exit<5 s | subprocess + fake_serial.wire |
| API-073 (P2) | Startup | Restart storm: restart hub 20x in 60 s | each boot answers /api/version <10 s, no leaked ports/threads, no stale lock files | loop subprocess |
| API-074 (P2) | Startup | Boot with no network adapter / only loopback; with IPv6 only | hub reachable on 127.0.0.1; lan_ip() falls back to 127.0.0.1 (main.py:524) and QR doesn't crash | unshare -n on Linux |
| API-075 (P2) | Startup | Clock jump backwards/forwards (NTP) during session | sessions valid, lockout uses monotonic (hub_auth.py:837) not wall clock | libfaketime |
| API-076 (P2) | Startup | PyInstaller exe vs source: GET /hub.html, /help.html, /app.js exist and non-empty (CLAUDE.md warns bare-script build ships no pages) | all 200 with size>1KB | run dist exe, requests |
| API-077 (P1) | Docs | For every row of HUB_API.md, hit the path with the listed method | no 404/405; GET-only rows reject POST sanely; accuracy of Method column | parse markdown table, loop |
| API-078 (P1) | Docs | Reverse: GET /api JSON paths vs HUB_API.md vs api_index.json | same set both directions; no route in code (grep 'path ==' in hub_api_*.py) missing from index | diff sets; AST/grep for routes |
| API-079 (P1) | Docs | Doc says every error is {"ok":false,"error":...}: sweep all routes with bad input | body always JSON with both keys; Content-Type application/json | iterate, assert schema |
| API-080 (P1) | Docs | Doc says 401 adds need_login:true: all gated routes | key present and true on every 401 | iterate |
| API-081 (P2) | Docs | "Start here" curls copy-pasted verbatim (login, modules, ports, usb/cmd, play, apps) | each returns documented shape; note doc says GET /api/usb/cmd with cookie works | parse code fences, run with requests |
| API-082 (P2) | Docs | State-changing routes documented as GET (show/save, show/delete, extensions/add and remove, gacha/load and sheet/write, logout, quit): confirm actual verb accepted, and that POST also works or is rejected as documented|doc table is source of truth for integrators|requests both verbs |
| API-083 (P2) | Docs | Query values column (force, port, type, dev, id...) vs what handler reads | every listed param changes behaviour; unlisted required params flagged | grep q.get( in handlers, compare |
| API-084 (P2) | Docs | Rows with "-" in What column (about 70%) count | metric only; fail if new route lacks docstring (docs gap) | count in script |
| API-085 (P2) | Docs | /api/gacha/* docstring at hub_api_gacha.py:22 lists stock/load body fields|load accepts machine,count,items,mode exactly; mode other than set or add rejected|post variants |
| API-086 (P2) | Docs | Docs generated: rerun tools/api_index.py and diff HUB_API.md | no diff (stale doc detection) | subprocess + git diff --exit-code |
| API-087 (P2) | Docs | Doc mentions short name and port 80: GET http://127.0.0.1:80/api/version equals :8642 | identical body | requests |
| API-088 (P1) | Boards | Register 255 fake boards ids 1..255 on the bus sim (qc/lib/bus_sim.py) | MAX_ID is 247 (bus_ids.py:21): ids 248-255 rejected/ignored with message; census lists exactly 247; /api/modules latency <3 s | bus_sim populate, GET /api/modules |
| API-089 (P1) | Boards | Two boards with the same id on one bus | census flags duplicate; fix() gives all but one a free id via CHIPS (bus_ids.py:97-118); wire shows reassign command | bus_sim dup ids, call hub bus fix route, assert chip->newid map |
| API-090 (P1) | Boards | All 247 ids taken and a duplicate appears | fix() has no free id (next(...) None, bus_ids.py:118): clean error, no exception/infinite loop | bus_sim full + dup |
| API-091 (P2) | Boards | Duplicate chip ids with colliding salts (identical chip bytes) | reports unresolvable, hub not hung | bus_sim chip clash |
| API-092 (P2) | Boards | Reconnect storm: board drops and rejoins 100x/min on bus and WiFi | /api/modules shows a board once (modules_here merge), no duplicate entries, no memory growth, show unaffected | fake_wifi toggle loop; assert list length stable |
| API-093 (P1) | Boards | USB cable unplug mid-command (fake_serial raises OSError) | per-port lock released, port marked gone, next call reopens; no deadlock | fake_serial fault injection, then new cmd |
| API-094 (P2) | Boards | Port flaps COM3 present/absent every 200 ms during /api/scanusb | scan returns, no zombie probe threads; probe skips in-use port (hub-usb header) | fake_serial toggle + thread count via /api/diag |
| API-095 (P2) | Boards | Same board reachable by USB, RS485, WiFi: dev=auto:<key> picks fastest, then drop fastest | route fails over, failHoldSec behaviour (hub-net header), one entry in /api/modules | fake_serial + fake_wifi latency knobs |
| API-096 (P2) | Boards | Route flapping: faster route wins only by margin with several samples | no thrash between routes under noisy latency | route_latency unit + fake delays |
| API-097 (P2) | Boards | dev strings invalid: `wifi:`, `usb:COM3:999`, `hub:x/y`, `auto:nokey` | 400/404 plain error; no hang waiting on 5 s timeout x N | requests /api/dev/status |
| API-098 (P2) | Boards | Forwarded command hub:<ip>/<dev> to unreachable peer | bounded timeout (two hops, main.py:937 comment), clear error | fake_friend down |
| API-099 (P2) | Boards | RS485 census with 0 boards, 1 board, 247 boards, noisy line (garbage bytes) | census returns in bounded time; garbage ignored; timing recorded | bus_sim noise injection |
| API-100 (P2) | Boards | Chip salts: 3 boards with same chip prefix | CHIPS lo hi s splits lanes, finds all (bus_ids.py:63) | bus_sim |
| API-101 (P2) | Boards | Mesh/wifi topology: 30 boards across 2 hubs, hub A scans hub B (/api/allmods?force=1, /api/hubs) | each board once with hub label; hub going down removes its boards after timeout | fake_friend x2 |
| API-102 (P2) | Boards | Two hubs list each other in a loop (A sees B sees A) via /api/allmods | no infinite recursion; boards not duplicated | fake_friend mutual |
| API-103 (P2) | Boards | Subnet scan with 254 addresses and all dead | scan completes within documented seconds, doesn't block /api/modules (main.py:597 comment) | fake_wifi black-hole; time GETs concurrently |
| API-104 (P2) | Boards | Board replies late (after timeout) then next command sent | late reply not attributed to new command (stale-line guard) | fake_serial delayed reply + wire/reply assert |
| API-105 (P2) | Boards | Board returns malformed/huge reply (1 MB, no newline, binary) | reader bounded, port recovers | fake_serial inject |
| API-106 (P2) | Boards | Flash POST /api/flash during active show and during other flash on same port | rejected 409/busy; probe skips flashing port (_flash_ports) | two posts, wire |
| API-107 (P2) | Boards | /api/flash/bus with dev not on bus, type unknown | 400 plain error; nothing on wire | post |
| API-108 (P2) | Boards | /api/flash/send and /api/flash/remote with truncated image, wrong chip type, oversize | image rejected before esptool runs | post bytes; assert no subprocess started |
| API-109 (P2) | Boards | /api/ota with wrong password, unreachable ip, ip=127.0.0.1 or hub itself | bounded failure, no credentials in error text or logs | fake_wifi; grep response/log |
| API-110 (P1) | Show | POST /api/play with 10 steps then GET /api/play/stop at random time | stop reaches wire within 200 ms; progress state idle; no later poses sent | fake_serial.wire timestamps |
| API-111 (P1) | Show | Start second POST /api/play while first running | first stopped or second rejected; never two clocks driving same arm (one player per hub, hub-show header) | post x2, wire interleave check |
| API-112 (P1) | Show | Show with MAX_MISSES consecutive no-reply poses | show ends and song stops (check_show_misses); one lost reply does not end it | fake_serial drop N replies |
| API-113 (P2) | Show | Watcher heartbeat: page asks to be watched then silent 4 s | arm stops (hub-show header A26-46) | post play watch=1, sleep 5, assert stop on wire |
| API-114 (P2) | Show | /api/play with loop and 0-length hold, huge hold (1e9), negative t | validated or clamped; no busy loop pegging CPU | post; psutil cpu sample |
| API-115 (P2) | Show | /api/stopall during play, speech, stream and flash simultaneously | every subsystem stops: poses, TTS silence(), STREAM OFF on wire | compose; assert states idle |
| API-116 (P2) | Show | show/save with name collision across two clients, then show/delete while playing | play continues from in-memory copy or stops cleanly | threads |
| API-117 (P2) | Show | /api/stream/start then feed with wrong session, after stop, 100 MB | rejected; session freed; no leak of sockets | post/fake_wifi |
| API-118 (P1) | Sound | Submit 20 /api/speak jobs quickly (queueMax 8, hub_speak.py:289) | extras report skipped "too many things are waiting"; no unbounded growth; order preserved | loop GET/POST speak, read status queue |
| API-119 (P1) | Sound | Two speak jobs to the same speaker with whenBusy=queue | play sequentially, never overlapping: STREAM ON of job2 after STREAM OFF of job1 on wire | fake_serial/fake_wifi wire order |
| API-120 (P1) | Sound | whenBusy=skip while busy | job state skipped with why, nothing on wire | post, status |
| API-121 (P1) | Sound | take=true while another speaks and an arm moves | silence() then STREAM OFFs waited (3 s) before new STREAM ON; show stopped (hub_speak.py:279-286) | wire order assert |
| API-122 (P1) | Sound | Stuck state: TTS engine hangs (monkeypatch _make to sleep 60 s) | job fails/timeout; queue worker not wedged; next job runs; /api/speak/stop clears | inject sleep; post job2 |
| API-123 (P2) | Sound | maxAgeSeconds expiry: job waits longer than max age | state skipped "too old", no voice made (_gone) | post with maxAgeSeconds=1 behind long job |
| API-124 (P2) | Sound | maxAgeSeconds="abc", -5, 0 | abc -> error "must be a number" (hub_speak.py:268); negative handled | post |
| API-125 (P2) | Sound | whenBusy invalid value | error text per hub_speak.py:263 | post |
| API-126 (P2) | Sound | Speaker unreachable mid-play (fake_wifi cut) | job fails, queue continues, no infinite retry | fake_wifi drop |
| API-127 (P2) | Sound | Speak to unknown `to` speaker and to speaker config with missing entry | clear error; default speaker used only when `to` empty | post |
| API-128 (P2) | Sound | speak/stop while idle, twice in a row, during "making" state | idempotent 200; making job cancelled before playing (_cancelled) | post loop |
| API-129 (P2) | Sound | Speaker config POST/save with invalid JSON, empty list, duplicate names (save_speakers, hub_speak.py:87) | rejected; old config kept | post, read file |
| API-130 (P2) | Sound | Voice helper start/stop/start rapid (/api/voice/start,stop) | single helper process; no zombie; state matches | post x10; psutil children |
| API-131 (P2) | Sound | /api/voice/ask without helper, with partner server down (hub_api_gacha.py:145 5.05 s stall noted) | returns within bound; no freeze of other routes | time concurrent GET /api/modules |
| API-132 (P2) | Sound | /api/video/sound and /api/stream/voice with unsupported codec, 0-byte, 500 MB | rejected, no temp leak | post bytes |
| API-133 (P2) | Sound | Speech language mixing (Thai + English + digits), SSML-ish `<` chars | speaks or errors; no crash; text not executed as markup | post, status |
| API-134 (P1) | Freeze | Hub watchdog: block one handler (partner service blackhole) and issue 50 other GETs | ThreadingHTTPServer keeps serving; /api/play answer <1 s | fake blackhole port; time GETs |
| API-135 (P2) | Freeze | Memory/thread/fd growth over 10 min of mixed requests (soak, 20 rps) | RSS growth <20%, thread count flat, fds flat | soak script + psutil |
| API-136 (P2) | Freeze | /api/stream (MJPEG) clients: open 20, disconnect abruptly | frame buffer freed (main.py:2055 take() reclaim), no thread leak | raw sockets, close, thread count |
| API-137 (P2) | Freeze | Cam route /api/faces/state when face service down | returns within timeout with ok:false | stop partner mock |
| API-138 (P1) | Gacha | Load stock count=0 then dispense | "refused_box_empty" message (gacha_stock.py:30); no wire turn; log row result refused | post load, call gacha/game dispense, wire empty |
| API-139 (P1) | Gacha | Dispense asked machine empty, another of same type has stock | uses other machine and reports asked_machine vs machine (gacha.py:8, 561); wire only to second | fake_serial two machines |
| API-140 (P1) | Gacha | All machines of kind empty | reason "out everywhere"; webhook empty fired (gacha.py:593) | fake webhook receiver |
| API-141 (P1) | Gacha | Two clients dispense the last ball simultaneously | exactly one succeeds; stock never negative; one log row each | thread pool, stock_view |
| API-142 (P1) | Gacha | POST /api/gacha/load without login | 401 "log in to put stock in" (hub_api_gacha.py:298) | requests |
| API-143 (P2) | Gacha | Load with count negative, float, string, huge (2^63), items with unknown kind, mode=bogus | 400 each; stock unchanged (MODES normal or random only)|param loop; stock_view before/after |
| API-144 (P2) | Gacha | mode set vs add semantics: set 5 then add 3 then set 1 | stock 5, 8, 1 | post, stock |
| API-145 (P2) | Gacha | Machine reports stock=-1/unparsable reply (gacha.py:573) | stock treated unknown; not empty; no crash | fake_serial odd reply |
| API-146 (P2) | Gacha | stock None machine (does not count) never empty; FORCE skips count but does not make empty box give (gacha.py:544) | force on empty counted box refused | post force=1 |
| API-147 (P2) | Gacha | Event total cap: kind stock 10 but event total left 2 | available capped to 2 (gacha_stock.py stock_view docstring); third draw refused | configure event, draw x3 |
| API-148 (P2) | Gacha | Per-source rules: `{game:quiz:true,"*":false}` ; source closed, source item not allowed | refused_source_closed / refused_source_item messages; play_only mode gives nothing real | post rules, dispense with source |
| API-149 (P2) | Gacha | Draw odds: stock 9/1 over 1000 draws on mode=random | empirical share within 3 sigma of odds in stock_view | loop, chi-square |
| API-150 (P2) | Gacha | Low stock threshold (low_stock=2): hook fires once at crossing, not every dispense | hook_log has one entry | dispense to 2, then to 1 |
| API-151 (P2) | Gacha | Jam reply from machine (fake_serial JAM) | webhook jam, stock not decremented, state recovers on next good call | fake_serial inject |
| API-152 (P2) | Gacha | gacha/rules/push and pull with remote offline, with malformed remote | 502 with error (hub_api_gacha.py:367,384), local rules untouched | fake_friend bad |
| API-153 (P2) | Gacha | gacha/sheet/write and sheet/read with bad tab name, 10k rows, formula-injection cells (`=cmd...`) | bounded; written as text not formula|post; inspect output |
| API-154 (P2) | Gacha | gacha/log CSV with commas/quotes/newlines/unicode in names | valid CSV roundtrip via csv.reader | post names, parse |
| API-155 (P2) | Gacha | Log file growth: 100k dispenses | log rotation or bounded memory; /api/gacha/log limit honoured | loop dispense with fake machine |
| API-156 (P2) | Gacha | Thai messages configurable via messages config: invalid placeholder `{nope}` | no KeyError 500; fallback message | post config |
| API-157 (P2) | Misc | /api/reports and /api/report POST with 10 MB, HTML/script in text, path-like name | stored as text; listing escapes; capped (hub_api_support.py:74 optional cap) | post then GET, assert no raw <script> |
| API-158 (P2) | Misc | /api/selfupdate and /api/app/version with no network | bounded failure message, no partial file replaced | block network; call |
| API-159 (P2) | Misc | /api/extensions/add with git/zip URL path traversal, zip-slip archive, restore without backup | rejected; files stay inside extensions dir | craft zip with ../, post |
| API-160 (P2) | Misc | /api/partners/start with unknown id, id with shell metachar `a;rm -rf` | 400; no subprocess spawn | post; watch process list |
| API-161 (P2) | Misc | /api/robot/upload and /api/model/upload with wrong extension, zip bomb, 0 bytes | rejected; temp cleaned | post bytes |
| API-162 (P2) | Misc | /api/rigcad POST bad CAD file / huge mesh | 400 or bounded time (<30 s) | post file |
| API-163 (P2) | Misc | /api/settings/peer?host= SSRF: host=169.254.169.254, localhost, file://, host with port/path | only valid hub hosts; no arbitrary GET proxy | post host variants; assert no outbound to canary server |
| API-164 (P2) | Misc | /api/video/fetch with URL file:// or internal IP or yt-dlp option injection (`--exec`) | rejected | post urls, canary |
