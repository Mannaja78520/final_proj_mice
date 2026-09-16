"""One binary per module type — and the other type is ABSENT, not hidden.

A board runs one module type, but for a long time every board carried every
type: a nong flashed the lift's motor code and the lift's web cards, a lift
flashed the nong's servo code and joint sliders. Only a JavaScript capability
check kept the wrong controls off the screen — and that check has already
broken once (`isNong` was used and never defined), which is how the RIGHT
controls disappeared. The mirror of that bug shows the WRONG ones, on a board
whose "joint sliders" drive nothing.

So this check does not ask whether the page hides the other type. It builds the
real per-type binaries and looks INSIDE them for the other type's markup. If a
lift binary contains `id="jointRows"`, the split has regressed no matter what
the page says at runtime.

Slow: it compiles. Skipped by --quick, run before flashing.
"""
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import qc as F

AREA = "firmware"
TITLE = "each module type builds its own binary, without the others"
SLOW = True

PIO = Path(os.environ.get("USERPROFILE", "")) / ".platformio/penv/Scripts/pio.exe"

# env -> (module types it carries, markup that must NOT be in it)
#
# The markers are MARKUP (`id="..."`, a card heading), never a bare word: the
# shared script legitimately mentions `liftCard` in showCard(), and a check
# that failed on that would be measuring the wrong thing.
ENVS = {
    "mice_nong": (["nong"], ['id="liftCard"', "RGB Strip", 'id="camCard"']),
    "mice_lift": (["lift"], ['id="jointRows"', "Nong Arms", 'id="camCard"']),
    # the camera is a different BOARD (esp32cam), which is the strongest form
    # of "costs the other modules nothing" — it cannot even share their binary
    "mice_cam": (["cam"], ['id="jointRows"', 'id="liftCard"', "RGB Strip"]),
}
LEGACY = "mice_module_firmware"     # every type in one binary, kept for now
FLASH_CEILING = 90.0


def _run(args, cwd, timeout=900):
    r = subprocess.run(args, cwd=str(cwd), capture_output=True, text=True,
                       timeout=timeout)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def _inputs_key():
    """One hash over everything a firmware build reads."""
    import hashlib
    h = hashlib.sha256()
    roots = [F.FIRMWARE, F.CODE / "config", F.CODE / "shared" / "web"]
    skip = {".pio", "patches", "__pycache__", ".vscode"}
    for root in roots:
        for f in sorted(root.rglob("*")):
            rel = f.relative_to(root)
            if not f.is_file() or skip & set(rel.parts) or f.name in ("promt.md", "PATCHES.md"):
                continue
            h.update(rel.as_posix().encode())
            h.update(f.read_bytes())
    return h.hexdigest()


def _cached(cache, key):
    import json
    try:
        got = json.loads(cache.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if got.get("key") != key:
        return None
    if not all((F.FIRMWARE / ".pio" / "build" / e / "firmware.bin").is_file()
               for e in list(ENVS) + [LEGACY]) or LEGACY not in got.get("out", {}):
        return None
    return {e: (0, got["out"].get(e, "")) for e in list(ENVS) + [LEGACY]}


def _store(cache, key, built):
    import json
    try:
        cache.write_text(json.dumps({"key": key, "out": {e: o for e, (_c, o) in built.items()}}),
                         encoding="utf-8")
    except OSError:
        pass


def run(t):
    # ---- 1. the generator splits the page, with no board involved ----
    # Fast, and it is where a broken marker shows up first.
    import tempfile
    tmp = Path(tempfile.mkdtemp(prefix="qc_gen_"))
    gen = F.FIRMWARE / "tools" / "gen_tables.py"
    pages = {}
    for types, name in ((["nong"], "nong"), (["lift"], "lift"), ([], "none")):
        code, out = _run([sys.executable, str(gen),
                          "--types", ",".join(types) or "none",
                          "--out", str(tmp / name)], F.FIRMWARE, timeout=120)
        if not t.ok(code == 0, "gen_tables writes a %s-only tree" % name, out[-200:]):
            return
        pages[name] = (tmp / name / "web" / "ModuleUI.h").read_text(
            encoding="utf-8", errors="replace")

    t.ok('id="jointRows"' in pages["nong"], "the nong page has the joint sliders")
    t.ok('id="jointRows"' not in pages["lift"],
         "the LIFT page does not contain the joint sliders",
         "a marker region is missing or misplaced in src/web/WebUI.h")
    t.ok('id="liftCard"' in pages["lift"], "the lift page has the lift controls")
    t.ok('id="liftCard"' not in pages["nong"],
         "the NONG page does not contain the lift controls")
    for name in ("nong", "lift", "none"):
        # a marker that survives into the output means the generator stopped
        # recognising it — the page would then show '#type nong' to a user
        body = re.search(r'R"rawliteral\((.*)\)rawliteral"', pages[name], re.S)
        t.ok(body and "#type" not in body.group(1) and "#end" not in body.group(1),
             "no build markers are left in the %s page" % name)

    # the command table must lose the other type's commands too: HELP may not
    # advertise a command whose handler is not in this binary
    lift_cmds = (tmp / "lift" / "core" / "CommandHelp.h").read_text(
        encoding="utf-8", errors="replace")
    t.ok('"nong"' not in lift_cmds,
         "the lift's command table carries no nong commands")
    nong_cmds = (tmp / "nong" / "core" / "CommandHelp.h").read_text(
        encoding="utf-8", errors="replace")
    t.ok('"lift"' not in nong_cmds,
         "the nong's command table carries no lift commands")

    # ---- 2. the real binaries -----------------------------------------
    if not PIO.is_file():
        t.give_up("PlatformIO not found at %s — install it or skip this check" % PIO)

    ini = (F.FIRMWARE / "platformio.ini").read_text(encoding="utf-8", errors="replace")
    for env in list(ENVS) + [LEGACY]:
        t.contains(ini, "[env:%s]" % env, "platformio.ini defines %s" % env)

    sizes = {}
    # ALL FOUR AT ONCE. Each environment writes its own .pio/build/<env>, so
    # they never touch each other's output - and building them in a for loop
    # was 107 of the suite's 836 seconds, on a machine with 24 threads. The
    # compiler itself is single-threaded per file; four compilers are not.
    import concurrent.futures as _cf
    t0 = time.time()
    # REUSE A GOOD BUILD WHEN NOTHING IT READS CHANGED (2026-09-17: 136 s of
    # every gate, almost always for identical firmware). The key hashes every
    # input - firmware sources, the registries and the shared stylesheet
    # compiled into it; one changed byte builds again. The checks below still
    # run on the real binaries either way.
    key = _inputs_key()
    # A reused build is only honest if any source change moves the key.
    probe = F.FIRMWARE / "src" / "_qc_key_probe.h"
    try:
        probe.write_bytes(b"// qc: proves a source edit changes the build key\n")
        t.ok(_inputs_key() != key, "a changed firmware file forces a real build",
             "the cache would reuse binaries that no longer match the source")
    finally:
        probe.unlink(missing_ok=True)
    cache = F.FIRMWARE / ".pio" / "qc_build_cache.json"
    built = _cached(cache, key)
    if built is None:
        with _cf.ThreadPoolExecutor(max_workers=len(ENVS) + 1) as pool:
            built = dict(zip(list(ENVS) + [LEGACY], pool.map(
                lambda e: _run([str(PIO), "run", "-e", e], F.FIRMWARE), list(ENVS) + [LEGACY])))
        if all(code == 0 for code, _o in built.values()):
            _store(cache, key, built)
        print("      (%d environments built in %.0fs, together)"
              % (len(ENVS), time.time() - t0))
    else:
        print("      (firmware inputs unchanged - reused the last good build)")

    for env, (types, absent) in ENVS.items():
        code, out = built[env]
        if not t.ok(code == 0, "%s compiles" % env, _first_error(out)):
            continue

        m = re.search(r"Flash:\s*\[[^\]]*\]\s*([\d.]+)%", out)
        if t.ok(m, "%s reports flash usage" % env):
            sizes[env] = float(m.group(1))
            t.under(sizes[env], FLASH_CEILING, "%s leaves room to grow" % env, "%")
            print("      (%s flash %.1f%%)" % (env, sizes[env]))

        # The point of the whole exercise: look in the actual image.
        binf = F.FIRMWARE / ".pio" / "build" / env / "firmware.bin"
        if t.ok(binf.is_file(), "%s produced a binary" % env):
            blob = binf.read_bytes()
            for marker in absent:
                t.ok(marker.encode() not in blob,
                     "%s does not contain %s" % (env, marker),
                     "the other module type's page is still in this binary")
            # ...and its own controls really are there, or the absence above
            # would pass on an empty page
            own = {"nong": 'id="jointRows"', "lift": 'id="liftCard"',
                   "cam": 'id="camCard"'}[types[0]]
            t.ok(own.encode() in blob, "%s does contain its own controls" % env)

    # ---- 3. the split must actually save something --------------------
    # It is the reason this exists: 74.9% of flash on every board, with a
    # camera type still to come.
    # built in the same parallel pool above, and reused with it
    code, out = built[LEGACY]
    m = re.search(r"Flash:\s*\[[^\]]*\]\s*([\d.]+)%", out)
    if t.ok(code == 0 and m, "the all-types build still compiles (%s)" % LEGACY,
            _first_error(out)):
        allt = float(m.group(1))
        print("      (all types flash %.1f%%)" % allt)
        for env in sizes:
            t.ok(sizes[env] < allt - 1.0,
                 "%s is smaller than the all-types build" % env,
                 "%s %.1f%% vs %.1f%% — the split saved nothing"
                 % (env, sizes[env], allt))


def _first_error(out):
    for line in out.splitlines():
        low = line.lower()
        if "error:" in low or "fatal" in low or line.startswith("*** "):
            return line.strip()[:300]
    tail = [l for l in out.strip().splitlines() if l.strip()][-3:]
    return " / ".join(x.strip()[:120] for x in tail)
