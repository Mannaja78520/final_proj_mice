"""Adding a thing must cost ONE edit in ONE place.

The project grew by adding functions one at a time, and each addition ended up
touching three to five files — a hub button here, a route there, a duplicate
table in the firmware and another in Studio that could drift apart unnoticed.
The registries exist to end that.

So this check does not merely read the registry code: it **adds a thing and
proves it works**, then removes it. If adding a web app ever needs a second
edit again, this fails.
"""
import json
import shutil
import sys
from pathlib import Path

import qc as F

AREA = "registries"
TITLE = "adding a thing costs one file"
SLOW = False

sys.path.insert(0, str(F.CODE / "tools"))
import registry  # noqa: E402


def run(t):
    # ---- the loader has to be forgiving of hand-written files ---------
    # A registry nobody can comfortably edit defeats the point.
    src = '{\n  // a comment\n  "a": 1, // trailing note\n  "b": [1, 2,],\n}\n'
    try:
        got = json.loads(registry.strip_jsonc(src))
        t.eq(got, {"a": 1, "b": [1, 2]},
             "registry files may carry // comments and trailing commas")
    except Exception as e:
        t.ok(False, "registry files may carry // comments and trailing commas", e)
    # ...but a // inside a string is part of the data, not a comment
    keep = json.loads(registry.strip_jsonc('{"u": "http://x/y"}'))
    t.eq(keep, {"u": "http://x/y"}, "a URL in a string survives comment stripping")

    # ---- a broken file must name itself, not raise from deep inside ---
    bad = F.QC / "_bad_registry.json"
    bad.write_text('{"a": 1,,}', encoding="utf-8")
    try:
        registry.load(bad)
        t.ok(False, "a malformed registry is reported clearly")
    except registry.RegistryError as e:
        t.contains(str(e), "_bad_registry", "a malformed registry names the file")
    except Exception as e:
        t.ok(False, "a malformed registry raises RegistryError", repr(e))
    finally:
        bad.unlink(missing_ok=True)

    # ---- the real apps are registered and reachable --------------------
    base, main = F.start_hub()
    s, b = F.get(base + "/api/apps")
    t.eq(s, 200, "the hub lists its apps")
    listed = json.loads(b).get("apps", [])
    by_id = {a["id"]: a for a in listed}
    for want in ("studio", "help"):
        t.ok(want in by_id, "%s is registered" % want, sorted(by_id))
    for a in listed:
        s, _ = F.get(base + a["path"])
        t.eq(s, 200, "%s actually serves at %s" % (a["name"], a["path"]))

    # ---- THE TEST: add an app, with no code change ---------------------
    tmp = F.CODE / "apps" / "_qc_tmp_app"
    try:
        tmp.mkdir(parents=True, exist_ok=True)
        (tmp / "app.json").write_text(
            '{\n  // added by QC, removed again below\n'
            '  "name": "QC temp app",\n  "blurb": "one file, no code change",\n'
            '  "icon": "\\ud83e\\uddea",\n  "order": 999\n}\n', encoding="utf-8")
        (tmp / "index.html").write_text("<!doctype html><title>qc</title>ok",
                                        encoding="utf-8")
        s, b = F.get(base + "/api/apps")
        got = {a["id"]: a for a in json.loads(b).get("apps", [])}
        if t.ok("_qc_tmp_app" in got,
                "a NEW app appears just by dropping its folder in", sorted(got)):
            s, body = F.get(base + got["_qc_tmp_app"]["path"])
            t.eq(s, 200, "and the hub serves it with no route added")
            t.contains(body, "ok", "serving its own entry file")
            t.eq(got["_qc_tmp_app"]["name"], "QC temp app",
                 "using the name from its manifest")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # and it is gone again once the folder is
    s, b = F.get(base + "/api/apps")
    t.ok("_qc_tmp_app" not in {a["id"] for a in json.loads(b).get("apps", [])},
         "removing the folder removes the app")

    # ---- an app may not serve files outside its own folder -------------
    s, _ = F.get(base + "/app/studio/../../../main_python/main.py")
    t.ok(s >= 400, "an app cannot escape its folder", "path traversal returned %s" % s)

    # ---- servo presets: ONE table, three consumers ---------------------
    # Firmware and Studio each used to keep their own copy, which could drift
    # apart with nothing to notice. Now: JSON -> generated header (build time)
    # and JSON -> hub -> Studio (runtime).
    presets = registry.servos()
    t.ok(len(presets) >= 5, "the shared servo table has the presets (%d)" % len(presets))
    s, b = F.get(base + "/api/servos")
    served = json.loads(b).get("servos", {}) if s == 200 else {}
    t.eq(sorted(served), sorted(presets), "the hub serves exactly that table")

    hdr = F.generated("modules/nong/ServoPresets.h")
    if t.ok(hdr.is_file(), "the firmware header was generated"):
        h = hdr.read_text(encoding="utf-8", errors="replace")
        for name in sorted(presets):
            t.contains(h, '"%s"' % name, "the firmware table has %s" % name)
        t.contains(h, "GENERATED", "the header says it is generated, not hand-edited")

    nong = (F.FIRMWARE / "src/modules/nong/NongModule.cpp").read_text(
        encoding="utf-8", errors="replace")
    t.contains(nong, "findServoPreset",
               "the SERVO command looks presets up in that table")
    t.ok('t == "mg90s"' not in nong,
         "the old hardcoded servo if-chain is gone",
         "a second copy of the presets still lives in NongModule.cpp")

    app = (F.STUDIO_WEB / "app.js").read_text(encoding="utf-8", errors="replace")
    t.contains(app, "/api/servos", "Studio loads the shared table")

    # every preset must be usable: a servo with max <= min would drive nothing
    for name, sp in presets.items():
        t.ok(sp.get("max", 0) > sp.get("min", 0) and sp.get("range", 0) > 0
             and sp.get("dps", 0) > 0, "preset %s is usable" % name, sp)

    # ---- commands: declared once, and it must match reality BOTH ways --
    import re
    decl = registry.commands()
    t.ok(len(decl) >= 40, "commands are declared (%d)" % len(decl))

    # Where each scope's handlers live. The module scopes come from the module
    # registry, so adding a type does not need this list edited — which was the
    # point of having the registry at all.
    src = {"core": (F.FIRMWARE / "src/core/CommandRouter.cpp")}
    for ty, mod in registry.modules().items():
        src[ty] = F.FIRMWARE / "src" / mod["header"].replace(".h", ".cpp")
    handlers = {k: set(re.findall(r'cmd == "([A-Z][A-Z0-9?]*)"',
                                 p.read_text(encoding="utf-8", errors="replace")))
                for k, p in src.items()}

    # A declared command with no handler would be advertised by HELP and then
    # answer "unknown cmd" — worse than not listing it.
    for c in decl:
        name, scope = c["name"], c["scope"]
        t.ok(name in handlers[scope],
             "%s (%s) has a handler" % (name, scope),
             "declared in commands.json but no handler in %s" % src[scope].name)

    # ...and a handler nobody declared is invisible: absent from HELP, absent
    # from the docs, and nothing notices it was added.
    declared = {(c["name"], c["scope"]) for c in decl}
    for scope, names in handlers.items():
        for name in sorted(names):
            t.ok((name, scope) in declared,
                 "%s (%s) is declared" % (name, scope),
                 "handled in %s but missing from commands.json" % src[scope].name)

    # every command must be in the reference too
    cmds_md = (F.FIRMWARE / "COMMANDS.md").read_text(encoding="utf-8", errors="replace")
    for c in decl:
        t.contains(cmds_md, c["name"], "COMMANDS.md documents %s" % c["name"])

    # the firmware answers HELP from that table, not a hand-typed string
    router = src["core"].read_text(encoding="utf-8", errors="replace")
    t.contains(router, "commandHelp(", "the board's HELP reads the generated table")

    # ---- capabilities: the board says what it can do -------------------
    # The module site used to switch on the module TYPE, so a third type would
    # have shown nothing until the page was taught about it.
    t.contains(router, 'doc["caps"]', "status reports what the board can do")
    t.contains(router, "addCapabilities", "and asks the module for its own")
    mod_h = (F.FIRMWARE / "src/modules/Module.h").read_text(encoding="utf-8", errors="replace")
    t.contains(mod_h, "addCapabilities",
               "every module type can declare capabilities")
    for f, cap in (("src/modules/lift/LiftModule.cpp", "rgb"),
                   ("src/modules/lift/LiftModule.cpp", "audio"),
                   ("src/modules/nong/NongModule.cpp", "joints"),
                   ("src/modules/nong/NongModule.cpp", "servos")):
        body = (F.FIRMWARE / f).read_text(encoding="utf-8", errors="replace")
        t.contains(body, '"%s"' % cap, "%s declares %s" % (Path(f).name, cap))

    web = (F.FIRMWARE / "src/web/WebUI.h").read_text(encoding="utf-8", errors="replace")
    t.contains(web, "st.caps", "the module site reads those capabilities")
    # Every card must be shown BY CAPABILITY. Banning one spelling of a type
    # check is not enough — the first version of this check passed while a
    # hardcoded `st.type==='lift'` sat on the RGB card, because it only looked
    # for the old variable name.
    # (The master page is still the all-types one; the per-type BUILD removes
    # the other type's cards from the binary — see check_build_split.py. Both
    # rules hold at once, and this one still matters because the hub serves
    # this master page for a module reached over USB.)
    for card, cap in (("liftCard", "motion"), ("nongCard", "joints"),
                      ("rgbCard", "rgb"), ("audCard", "audio")):
        m = re.search(r"showCard\('%s'\s*,\s*([^)]+)\)" % card, web)
        if t.ok(m, "%s decides its own visibility" % card):
            expr = m.group(1)
            t.ok("has(" in expr and "st.type" not in expr,
                 "%s is shown by capability, not module type" % card,
                 "reads: %s" % expr.strip()[:80])
    # an old board sends no caps, and must still work
    t.contains(web, "caps.length?", "an old board without caps still renders")
    hdr2 = F.generated("core/CommandHelp.h")
    if t.ok(hdr2.is_file(), "the command table header was generated"):
        h = hdr2.read_text(encoding="utf-8", errors="replace")
        t.contains(h, "GENERATED", "it says it is generated, not hand-edited")
        for c in decl[:5]:
            t.contains(h, '"%s"' % c["name"], "the table carries %s" % c["name"])
