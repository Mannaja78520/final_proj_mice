"""Run many firmware SIM cases (docs/test_cases/firmware_cases.md, mark SIM) on QEMU.

    python tools/sim_sweep.py [--env mice_nong] [--out docs/test_cases/sim_sweep.json]

One boot per group. Every case prints PASS/FAIL with the reply it saw, so a
failure can be read without rerunning. Tested against an emulator, not a board.
Case ids match firmware_cases.md. Needs `tools/qemu_esp32.py install` and a
`pio run -e <env>` build.
"""
import json
import random
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "qc" / "lib"))
import qemu_board as Q  # noqa: E402

RESULTS = []


def case(cid, ok, label, seen=""):
    RESULTS.append({"id": cid, "ok": bool(ok), "label": label, "seen": str(seen)[:160]})
    print(("%s %s %s | %s" % ("PASS" if ok else "FAIL", cid, label, str(seen)[:100])).encode("ascii", "replace").decode(), flush=True)


def drain(b, wait=1.0):
    """Let late replies (to garbage lines) arrive and drop them, so the next cmd reads its own."""
    time.sleep(wait)
    b._pump()


def has(s, *words):
    s = s.lower()
    return any(w.lower() in s for w in words)


def router_cases(b):
    """FW-069..079: the command router on a nong build, over USB serial."""
    t0 = time.time()
    r = b.cmd("INFO")
    case("FW-001", '"id":7' in r.replace(" ", "") or " 7" in r, "INFO shows seeded id 7", r)
    r = b.cmd("PERF?")
    keys = ("loop", "heap", "stack", "lock")
    case("FW-012", all(k in r for k in keys), "PERF? has loop/heap/stack/lock", r)
    r = b.cmd("   ")
    case("FW-069", has(r, "err", "empty") or r == "", "blank line: ERR or silent, board alive", r)
    r = b.cmd("PING")
    case("FW-069b", has(r, "pong"), "PING after blank line", r)
    r = b.cmd(" ".join(["PING"] * 17))
    case("FW-070", has(r, "too many", "err"), "17 words refused", r)
    r = b.cmd("XYZZY")
    case("FW-071", has(r, "unknown", "err"), "unknown command", r)
    r = b.cmd("A" * 10000, timeout=20)
    case("FW-072a", has(r, "err", "unknown"), "10 KB line answered with one ERR", r[:60])
    time.sleep(1.5)
    b._pump()
    r = b.cmd("PING")
    case("FW-072", has(r, "pong"), "alive after 10 KB line", r)
    r = b.cmd('SET WIFI "abc')
    case("FW-073", has(r, "err", "usage", "ok") and not has(r, "panic"), "unmatched quote: clean reply", r)
    r1, r2 = b.cmd("ping"), b.cmd("Ping")
    case("FW-074", has(r1, "pong") and has(r2, "pong"), "case-insensitive verbs", (r1, r2))
    bad = []
    for v in ("0", "248", "-3", "abc", "1.5", "255"):
        r = b.cmd("SET ID " + v)
        if not has(r, "1-247", "err"):
            bad.append((v, r))
    case("FW-075", not bad, "SET ID bad values refused", bad)
    bad = []
    for n in ("", "x" * 40, 'a"b'):
        r = b.cmd("SET NAME " + n)
        if not r:
            bad.append((n, "silent"))
    case("FW-076", not bad, "SET NAME odd values answered", bad)
    r1, r2 = b.cmd("SET MESH banana"), b.cmd("SET RELAY banana")
    case("FW-077", has(r1, "usage", "err") and has(r2, "usage", "err"), "SET MESH/RELAY bad word", (r1, r2))
    r = b.cmd("SET WIFI")
    case("FW-016", has(r, "ssid", "err"), "SET WIFI no args", r)
    bad = []
    for p in ("short", "x" * 64, "has space1"):
        r = b.cmd("SET APPASS " + p)
        if not has(r, "8-63", "err"):
            bad.append((p, r))
    case("FW-017", not bad, "APPASS length/space rules", bad)
    r = b.cmd("SET TYPE lift")
    case("FW-007", has(r, "unknown type", "err"), "SET TYPE lift on nong build", r)
    r = b.cmd("REACH")
    case("FW-021", not has(r, "panic") and r != "", "REACH on no-radio build answers", r)
    # FW-078/079: every verb in HELP, no args, then silly args
    h = b.cmd("HELP", timeout=15).split("(HELP")[0]
    skip = {"REBOOT", "FWBEGIN", "FWDATA", "FWEND", "FWABORT", "OTA", "FBEGIN", "FDATA", "FEND", "FDEL", "AUTH", "USER", "SET", "GROUP", "APPASS", "PEERPASS", "WIFI", "PEERS", "FILES"}
    verbs = [w for w in h.split() if w not in skip]
    verbs = sorted(set(verbs))
    b.cmd("SET ID 7")
    dead = []
    for v in verbs:
        if not b.cmd(v, timeout=6):
            dead.append(v)
    for v in ("PEERS", "FILES"):          # JSON arrays start with "[": cmd() reads that as a log line
        mark = len(b.log)
        b.write(v)
        b.wait_for("[", 5, since=mark)
        case("FW-078 " + v, "[" in b.log[mark:] and "Guru" not in b.log[mark:], v + " answers a JSON array and does not panic", b.log[mark:mark + 60])
    case("FW-078", not dead and verbs, "%d verbs with no args each answer" % len(verbs), dead or verbs[:12])
    dead = []
    for v in verbs:
        for a in ("nan", "99999999999", "-5", "inf"):
            if not b.cmd("%s %s %s" % (v, a, a), timeout=4):
                dead.append((v, a))
    drain(b, 3.0)
    b.cmd("STOP")
    drain(b)
    r = b.cmd("PING")
    case("FW-079", has(r, "pong") and "Guru" not in b.log, "fuzz args (nan, huge, negative, inf) on every verb: no panic, board alive", "unanswered=%s | %s" % (dead[:6], r))
    for ln in ("POSE nan 1", "POSE 1 inf", "POSE 1 -1"):
        pass
    r = b.cmd("FWBEGIN")
    case("FW-082", has(r, "err", "md5"), "FWBEGIN without md5", r)
    r = b.cmd("FWBEGIN 100 zzzz")
    case("FW-083", has(r, "32 hex", "err"), "FWBEGIN bad md5", r)
    r = b.cmd("FWBEGIN 0 " + "a" * 32)
    case("FW-084a", has(r, "err"), "FWBEGIN size 0", r)
    r = b.cmd("FWBEGIN 4294967295 " + "a" * 32)
    case("FW-084b", has(r, "err", "room"), "FWBEGIN size 0xFFFFFFFF", r)
    r = b.cmd("FWBEGIN 99999999 " + "a" * 32)
    case("FW-099", has(r, "err", "room"), "FWBEGIN over slot size", r)
    r = b.cmd("FWDATA 0 3 AAAA")
    case("FW-086a", has(r, "err", "no update"), "FWDATA without FWBEGIN", r)
    r = b.cmd("FWEND")
    case("FW-086b", has(r, "err", "no update"), "FWEND without FWBEGIN", r)
    b.cmd("FWBEGIN 300 " + "a" * 32)
    r = b.cmd("FWEND")
    case("FW-087", has(r, "only", "err"), "FWEND short of promised", r)
    b.cmd("FWBEGIN 300 " + "a" * 32)
    r = b.cmd("FWBEGIN 300 " + "b" * 32)
    case("FW-091", has(r, "ok", "begin") and not has(r, "panic"), "second FWBEGIN restarts cleanly", r)
    r = b.cmd("FWEND")
    r = b.cmd("PING")
    case("FW-091b", has(r, "pong"), "alive after aborted updates", r)
    # FW-157 many writes
    ok = True
    seen = ""
    for i in range(300):
        seen = b.cmd("SET NAME n%d" % i, timeout=5)
        if not seen:
            ok = False
            break
    case("FW-157", ok, "300 SET NAME writes, all answered", seen)
    b.cmd("SET NAME keepme")
    b.reboot()
    r = b.cmd("INFO")
    case("FW-153", "keepme" in r, "name survives reboot", r)
    r = b.cmd("PERF?")
    case("FW-009", has(r, "reboot", "sw", "software"), "reset reason after REBOOT", r)
    r = b.cmd("SET TYPE blank")
    b.reboot()
    r = b.cmd("INFO")
    case("FW-008", "blank" in r, "SET TYPE blank persists", r)
    b.cmd("SET TYPE nong")
    b.reboot()
    print("router group %.0fs" % (time.time() - t0))


def lines_cases(b):
    """FW-050..057, 172 on a board, over its USB line (the router sees the same bytes)."""
    b.write("PING" * 1500)
    drain(b)
    drain(b, 2.0)
    r = b.cmd("PING")
    case("FW-172", has(r, "pong"), "6000 bytes without newline, then PING", r)
    for name, raw in (("FW-053a", b"\r\n"), ("FW-053b", b"PING\r\n"), ("FW-053c", b"\r\r\r")):
        b.sock.sendall(raw)
        time.sleep(0.3)
        b._pump()
    r = b.cmd("PING")
    case("FW-053", has(r, "pong"), "CR / CRLF / empty lines", r)
    rnd = random.Random(7)
    b.sock.sendall(bytes(rnd.randrange(256) for _ in range(2000)) + b"\n")
    drain(b)
    r = b.cmd("PING")
    case("FW-052", has(r, "pong"), "2000 random bytes then PING", r)
    b.sock.sendall(b"PI\xff\xfeNG\n")
    time.sleep(0.3)
    r = b.cmd("PING")
    case("FW-054", has(r, "pong"), "0xFF bytes in command", r)
    t0 = time.time()
    n = 0
    for i in range(100):
        if has(b.cmd("PING", timeout=3), "pong"):
            n += 1
    case("FW-067", n == 100, "100 PINGs back to back, all answered (%.1fs)" % (time.time() - t0), n)
    drain(b)
    r = b.cmd("PERF?")
    case("FW-171", "stack" in r, "stack high-water readable after fuzz", r)


def gacha_cases():
    nvs = ROOT / "qc" / "data" / "qemu_nvs_gacha_wifi_off.bin"
    with Q.QemuBoard("mice_gacha", nvs=nvs) as b:
        case("FW-132a", has(b.cmd("GSTOCK 0"), "stock=0"), "stock 0", "")
        r = b.cmd("GDISPENSE")
        case("FW-132", has(r, "empty", "err"), "GDISPENSE with stock 0 refused", r)
        for v in ("-3", "abc", "99999999", "1.5"):
            r = b.cmd("GSTOCK " + v)
            case("FW-133 " + v, r != "" and not has(r, "panic"), "GSTOCK " + v, r)
        b.cmd("GSTOCK 4")
        r = b.cmd("GDISPENSE")
        r2 = b.cmd("GDISPENSE")
        case("FW-136", has(r2, "busy", "err"), "second GDISPENSE while turning", (r, r2))
        r = b.cmd("STOP")
        case("FW-137", r != "", "STOP mid-dispense answered", r)
        r = b.cmd("G?")
        case("FW-137b", '"state":"idle"' in r.replace(" ", ""), "state idle after STOP", r)
        b.cmd("GSTOCK 3")
        b.reboot()
        r = b.cmd("G?")
        case("FW-134", "stock" in r and "3" in r, "stock after reboot", r)


def main():
    env = "mice_nong"
    for i, a in enumerate(sys.argv):
        if a == "--env":
            env = sys.argv[i + 1]
    t = time.time()
    with Q.QemuBoard(env) as b:
        router_cases(b)
        lines_cases(b)
    if (ROOT / "firmware" / ".pio" / "build" / "mice_gacha").is_dir():
        gacha_cases()
    bad = [r for r in RESULTS if not r["ok"]]
    out = ROOT / "docs" / "test_cases" / "sim_sweep.json"
    out.write_text(json.dumps(RESULTS, indent=1))
    print("\n%d cases, %d failed, %.0fs" % (len(RESULTS), len(bad), time.time() - t))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
