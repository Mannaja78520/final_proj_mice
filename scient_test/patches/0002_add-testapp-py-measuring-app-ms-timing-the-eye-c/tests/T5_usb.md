# T5 — USB serial transport (tested on its own)

This file tests **the USB cable path**, not the modules. Run it **once per
module** — once with the nong board, once with the lift board.

Why separate from T3 (RS485) and T4 (WiFi): USB is point-to-point, powered, and
**shares the port with the boot log**. Its independent variables — cable
quality and length, USB-UART driver, the `[…]` log-line ambiguity, Web Serial
in the browser — exist nowhere else. It is also the **reference transport**:
the module tests T1 and T2 are run over USB precisely because it has the fewest
confounds, so its own numbers need to be established first.

Source of truth: `code/firmware/src/main.cpp` (the serial loop),
`code/firmware/COMMANDS.md` §3, `code/firmware/tools/usb-console.html`.

> **All of it is app work.** `python ../tools/bench.py usb --port COM5 --cmd
> PING -n 50` covers USB-01, 02, 03 and 10. USB-04's line-filter experiment is
> already built into both tools — `bench.is_log_line()` implements the correct
> "skip only a real log tag" rule, so comparing its behaviour against the naive
> rule is the test. Only the physical rows need you: swapping cables, unplugging
> mid-run, opening two programs on one port.

---

## What the firmware does on USB

```
115200 baud, newline-terminated ASCII, same command language as every channel
line NOT starting with '#'  ->  router.handle(line)          local command
line starting with '#'      ->  rs485.bridge(line, &router)  forwarded to the RS485 bus
replies from the bus ('@…') are printed on USB as they arrive (onBusLine)
the boot log shares the port:  [boot] …  [wifi] …  [sd] …
```

The trap every host app hits, from `COMMANDS.md`:

> ignore log lines, but match them precisely as a bracket **tag** (`[wifi] …`),
> **not** just any line starting with `[`. Some replies are JSON **arrays**
> that also start with `[` (`PIN VALID` → `[{…}]`, `FILES` → `["…"]`).

USB-04 tests exactly that, because getting it wrong makes pin config look
broken over USB while working fine over WiFi.

---

## Variables

### Independent variables

| # | Independent Variable | How to set it | Range used |
|---|---|---|---|
| 1 | **Cable length / quality** | swap cables | 0.3 m good, 1 m good, 3 m cheap, 5 m + hub |
| 2 | **USB-UART bridge** | the board's chip / adapter | CP2102, CH340, FTDI (whatever is on hand) |
| 3 | **Command rate** | commands per second from the host | 1, 10, 50, 100, 200 /s |
| 4 | **Line-filter rule in the host app** | how the host skips boot log | "skip any line starting with `[`" vs "skip only `[tag] `" |
| 5 | **Command case** | as typed | `POSE …` vs `pose …` |
| 6 | **Bridging** | direct vs through the bus | plain `PING` vs `#<id> PING` vs `#* PING` |
| 7 | **`FDATA` chunk size** | base64 chunk in the file transfer | 40, 80, 120, 200, 400 bytes |
| 8 | **Host** | which program drives the port | `pio device monitor`, `tools/usb-console.html` (Web Serial), Nong Studio, `bench.py` |
| 9 | **Timing of the first command** | how soon after power-on | 0.5 s, 1 s, 2 s, 5 s |
| 10 | **Module activity** | idle vs moving during the traffic | idle, sequence running |

### Dependent variables

| DV | Unit | How it is read |
|---|---|---|
| Round-trip latency | ms | `tools/bench.py usb` — min / mean / p95 / max |
| Command success rate | % | same tool |
| Dropped / garbled lines | count | replies that don't parse |
| Boot-to-first-reply | s | power on, send `PING` every 100 ms, time the first `PONG` |
| Log/JSON misparse | pass/fail | does the host's filter eat `PIN VALID` / `FILES` replies? |
| File transfer throughput | KB/s | `FBEGIN`/`FDATA`/`FEND` of a known file, timed |
| File integrity | pass/fail | md5 after `FREAD` back |
| Bridged reply delay | ms | time from `#<id> CMD` to the `@<id>` line appearing |
| Reply string | text | verbatim |

### Control variables

| CV | Fixed at |
|---|---|
| Baud | 115200 8N1 — the firmware's fixed rate, never changed |
| Host PC | one machine, one OS, one driver version (note all three) |
| Port | one COM port; close every other program using it (a second monitor steals the bytes) |
| Command | `PING` for latency rows |
| WiFi | `SET WIFI OFF` on the module — no radio task competing for CPU |
| RS485 | disconnected, except in USB-06 (bridging) where it is the point |
| Module state | idle, `HOME`d, except IV #10 |
| Module type under test | one per series — nong, then lift |
| Sample size | 50 commands per run, 3 runs per IV value |

---

## Tests

### USB-01 — baseline latency, and the reference number for T1/T2

| ID | IV setting | Command / action | Measure (DV) | Expected | Pass if |
|---|---|---|---|---|---|
| USB-01a | idle module, 0.3 m cable | `python ../tools/bench.py usb --port COM5 --cmd PING -n 50` | min/mean/p95/max ms, success % | 100 %; a few ms — the firmware answers inside one `loop()` | 100 %, p95 <30 ms |
| USB-01b | `INFO` instead of `PING` | `--cmd INFO -n 50` | same | longer reply, slightly higher latency | 100 % |
| USB-01c | module moving | start a sequence, repeat 01a | same | `loop()` is also driving servos/motor | 100 %, note the p95 rise |
| USB-01d | reference | compare 01a with WIFI-01a and RS485-01a | mean ms on each | USB is the lowest — hence it is the transport used in T1 and T2 | report all three |

USB-01d is the row that **justifies the control variable choice** in the module
tests. Fill it in before running T1 and T2.

### USB-02 — cable and adapter

| ID | IV setting | Command / action | Measure (DV) | Expected | Pass if |
|---|---|---|---|---|---|
| USB-02a | 0.3 m good cable | bench.py ×50 | success %, garbled lines | 100 % | 100 % |
| USB-02b | 1 m good cable | same | same | 100 % | 100 % |
| USB-02c | 3 m cheap cable | same | same | where cheap cables start dropping bytes | record |
| USB-02d | 5 m + unpowered hub | same | same, plus: does the board brown out? | a hub also limits current — the ESP32 may reset | record |
| USB-02e | different UART chip | swap board/adapter (CH340 vs CP2102) | latency, success % | driver buffering differs measurably | report the difference |

### USB-03 — command rate

| ID | IV setting | Command / action | Measure (DV) | Expected | Pass if |
|---|---|---|---|---|---|
| USB-03a | 1 /s | bench.py `--rate 1 -n 50` | success %, p95 | 100 % | 100 % |
| USB-03b | 10 /s | `--rate 10` | same | 100 % | 100 % |
| USB-03c | 50 /s | `--rate 50` | same | 100 % | ≥99 % |
| USB-03d | 100 /s | `--rate 100` | same | at 115200 that's ~1.2 KB/s of `PING` — still light | ≥99 % |
| USB-03e | 200 /s | `--rate 200` | same, plus dropped | the serial RX is drained once per `loop()`; find the ceiling | report the saturation rate |
| USB-03f | 200 /s while moving | repeat 03e with a sequence running | success % | `loop()` is busier — a lower ceiling | report both ceilings |

Compare the USB ceiling (USB-03e) with the RS485 ceiling (RS485-05e) and the
WiFi ceiling (WIFI-05d). Three different numbers for the same firmware — that
comparison is the point of splitting these files.

### USB-04 — the boot-log / JSON-array trap

IV: the host's line-filter rule. This is a **host-side** experiment run over
USB, and it reproduces a bug that has actually happened in this project.

| ID | IV setting | Command / action | Measure (DV) | Expected | Pass if |
|---|---|---|---|---|---|
| USB-04a | filter = "skip any line starting with `[`" | send `PIN VALID`, parse with that rule | is the reply seen? | **reply is eaten** — it is `[{…}]` | reproduces the bug |
| USB-04b | same filter | send `FILES /moves` | is the reply seen? | eaten — reply is `["…"]` | reproduces |
| USB-04c | filter = "skip only `[tag] ` / `[  1234][I]`" | repeat 04a and 04b | replies seen? | both parse correctly | both parse |
| USB-04d | no filter at all | reboot the module, then send `PING` immediately | what the host receives | boot log lines mixed with `PONG` | document the noise |
| USB-04e | same command over WiFi | `GET /api/cmd?c=PIN VALID` | reply | always clean — no log on that channel | clean |

USB-04e is the control: it proves the problem is the **transport's shared
port**, not the command.

### USB-05 — command case sensitivity

IV: the case you type. A standing control variable in every other file; this
test is where it gets measured instead of assumed.

| ID | IV setting | Command / action | Measure (DV) | Expected | Pass if |
|---|---|---|---|---|---|
| USB-05a | core command, upper | `PING` | reply | `PONG …` | works |
| USB-05b | core command, lower | `ping` | reply | `PONG …` — the router uppercases its own copy | works |
| USB-05c | module command, upper | `POSE?` (nong) / `STAGE?` (lift) | reply | the value | works |
| USB-05d | module command, lower | `pose?` / `stage?` | reply | **`ERR unknown cmd: POSE?`** — `argv[0]` reaches the module in its original case | reproduces |
| USB-05e | mixed | `Pose?` | reply | same `ERR` | reproduces |

Result to record: **module commands are case-sensitive, core commands are
not.** That is why "UPPERCASE always" is a control variable everywhere else —
without it, a lowercase typo in a timing test looks like a firmware failure.

### USB-06 — bridging onto the RS485 bus through USB

CV: RS485 connected for this test only, ≥2 modules on the bus.

| ID | IV setting | Command / action | Measure (DV) | Expected | Pass if |
|---|---|---|---|---|---|
| USB-06a | direct | `PING` | reply, ms | answered locally | fastest |
| USB-06b | addressed to **this** module | `#<own id> PING` | reply | answered directly: `@<id> PONG …`, never touches the wire | correct |
| USB-06c | addressed to another module | `#3 PING` | immediate reply, then the `@3` line, and the delay between them | `-> sent, module 3's reply appears when it answers`, then `@3 PONG …` | `@3` arrives <200 ms |
| USB-06d | broadcast | `#* PING` | all `@<id>` lines, and the last one's delay | staggered by id×20 ms | all modules answer |
| USB-06e | bad frame | `#3` / `#` / `# PING` | reply | `ERR bad frame (use #<id> CMD or #* CMD)` | exact |
| USB-06f | reach a module with no USB and no WiFi | `SET WIFI OFF` on module 3, unplug its USB, then `#3 GOTO 1` from module 1's USB | does module 3 move? | **yes** — one cable reaches the whole fleet | it moves |

USB-06f is the claim in README/COMMANDS.md ("one link to one module reaches
everything"). This row turns it into a measured result.

### USB-07 — file transfer chunk size

CV: one 4 KB YAML file, module idle.

| ID | IV setting | Command / action | Measure (DV) | Expected | Pass if |
|---|---|---|---|---|---|
| USB-07a | 40-byte chunks | `FBEGIN`/`FDATA`×N/`FEND` | seconds, KB/s, integrity | slowest — most round trips | md5 match |
| USB-07b | 80-byte chunks | same | same | faster | md5 match |
| USB-07c | 120-byte chunks | same | same | the documented RS485-safe size | md5 match |
| USB-07d | 200-byte chunks | same | same | **USB has no 250-char frame limit for the host→module direction the way the bus does — but the firmware's 192-byte decode buffer does** (`uint8_t buf[192]` in `FDATA`) | expect failure ≥256 b64 chars; document |
| USB-07e | 400-byte chunks | same | same | fails | document the error |
| USB-07f | read back | `FREAD <file> <off> 120` in a loop | KB/s, integrity | 120 is the hard cap in the firmware | md5 match |

USB-07d/e find the **real** maximum chunk on USB, which is not the same as the
RS485 maximum. Recording both stops the next person guessing.

### USB-08 — boot timing

IV: how soon after power-on the first command is sent. `SET WIFI OFF` makes
this the fastest case; repeat with WiFi `on` to see the difference.

| ID | IV setting | Command / action | Measure (DV) | Expected | Pass if |
|---|---|---|---|---|---|
| USB-08a | 0.5 s after power-on | send `PING` at 0.5 s | reply? | probably too early | record |
| USB-08b | 1 s | same at 1 s | reply? | COMMANDS.md claims USB/RS485 respond ~1 s after power-on | replies |
| USB-08c | 2 s | same | reply? | yes | replies |
| USB-08d | with WiFi `on` and the AP absent | `SET WIFI ON`, AP off, repeat 08b | reply at 1 s? | boot is **non-blocking** — USB must answer even while WiFi is failing for 15 s | replies at 1 s |
| USB-08e | boot-to-first-reply | poll `PING` every 100 ms from power-on | the exact ms | the definitive number for both WiFi modes | report both |

USB-08d tests the non-blocking-boot design claim directly: WiFi failing must
not delay USB.

### USB-09 — host program comparison

IV: which program drives the port. Same 50 `PING`s each.

| ID | IV setting | Command / action | Measure (DV) | Expected | Pass if |
|---|---|---|---|---|---|
| USB-09a | `bench.py` (pyserial) | as USB-01a | mean/p95 ms | the reference | — |
| USB-09b | `tools/usb-console.html` (Web Serial, Chrome/Edge) | connect, send `PING` ×50 from the console | mean ms (browser devtools timing) | comparable; Web Serial adds a little | within 2× of 09a |
| USB-09c | Nong Studio, USB transport, `live` mode | drag a slider, watch the arm | pose lag ms, dropped commands | live posing must feel immediate | lag <150 ms |
| USB-09d | `pio device monitor` | type commands by hand | replies readable? | boot log interleaved, but usable | usable |
| USB-09e | two programs at once | open the monitor **and** bench.py on the same port | what happens | port is exclusive: one fails to open, or bytes are split | document the failure mode |

USB-09e is worth doing once: "the port was already open" is otherwise diagnosed
as a broken module.

### USB-10 — soak

| ID | IV setting | Command / action | Measure (DV) | Expected | Pass if |
|---|---|---|---|---|---|
| USB-10a | 1 /s for 60 min, idle | bench.py `--rate 1 -n 3600` | success %, any reset | stable | 100 %, no reset |
| USB-10b | 10 /s for 60 min, sequence looping | same with a looping `/moves` sequence | success %, drift in the sequence timing, resets | the show-length test | ≥99.9 %, no reset |
| USB-10c | unplug / replug mid-run | pull the cable, plug it back | does the module keep running? does the host recover? | the module is unaffected; the host must reopen the port | module unaffected |

---

## Run this file twice

| Series | Device under test | Everything else |
|---|---|---|
| T5-NONG | the nong board | — |
| T5-LIFT | the lift board | — |

Record both in [`../results/usb_results.csv`](../results/usb_results.csv); the
`module` column separates them.
