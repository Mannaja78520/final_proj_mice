"""The pin drawing matches the board in front of you, whichever board it is.

Settled in the plan: keep BOTH pinout images, chosen by condition. The 38-pin
WROOM reference is right for a nong or a lift and simply wrong for an ESP32-CAM,
whose GPIOs are nearly all spoken for by the sensor - somebody wiring a servo to
GPIO 26 because the picture showed it free would be wiring it onto the SCCB data
line, and the camera would stop answering with nothing to explain why.

The camera half is DRAWN rather than shipped, from
`firmware/config/cam_boards.json` - the same file `gen_tables.py` compiles into
CamBoards.h. That is the property this check exists for: one source. A picture
has to be found for every board somebody might buy, and a picture can be wrong
about the wiring; a diagram rendered from the numbers the firmware compiled
cannot be, and it arrives free with every board added to the registry. The user
asked for exactly that on 2026-08-19: *make it compatable with many board
sometime when i buy the new one maybe i don't know which hardware i got*.
"""
import json
import urllib.request
from pathlib import Path

import qc as F

AREA = "hub"
TITLE = "each board gets its own pin diagram, drawn from the firmware's own data"


def run(t):
    import sys
    sys.path.insert(0, str(F.HUB))
    sys.path.insert(0, str(F.CODE / "tools"))
    import main      # noqa: PLC0415 - the module under test
    import registry  # noqa: PLC0415

    boards = main.cam_boards()
    t.ok(len(boards) >= 5, "the hub knows every camera board the firmware does",
         "found %s" % sorted(boards))

    # ---- ONE source: the json IS the firmware's table ----------------
    # The C++ used to hold the list. If it ever holds one again, the picture and
    # the wiring can disagree, and the picture is what somebody wires to.
    cpp = (F.FIRMWARE / "src" / "modules" / "cam" /
           "CamModule.cpp").read_text(encoding="utf-8")
    t.ok("CAM_BOARDS[] = {" not in cpp,
         "the board table does not live in the C++ any more",
         "a second copy of a pin map is a second chance for the diagram to lie")
    t.contains(cpp, "CamBoards.h", "it includes the generated one instead")

    gen = F.FIRMWARE / "generated" / "modules" / "cam" / "CamBoards.h"
    if not t.ok(gen.is_file(), "and the generator really wrote it", str(gen)):
        return
    head = gen.read_text(encoding="utf-8")
    order = [k for k, _lbl in main.CAM_SIGNALS]
    for name, b in boards.items():
        row = [l for l in head.splitlines() if '"%s"' % name in l]
        if not t.ok(row, "%s is in the generated table" % name):
            continue
        # The numbers between the name and the closing brace, in order. Parsed
        # properly because the first version of this produced an empty list on
        # both sides and compared nothing - the sabotage tool caught it by
        # changing a pin in the json and watching this pass.
        inside = row[0][row[0].index("{") + 1:row[0].rindex("}")]
        nums = [int(x) for x in inside.split(",")[1:] if x.strip()]
        # The camera signals, then the two LED pins the board carries.
        t.eq(len(nums), len(order) + 2,
             "%s has every pin plus its LEDs in the header" % name)
        t.eq(nums[:len(order)], [b["pins"][k] for k in order],
             "%s has the same pins in the header as in the json" % name)
        ex = b.get("extra") or {}
        t.eq(nums[len(order):],
             [int(ex.get("flash", -1)), int(ex.get("led", -1))],
             "%s carries its own flash and status LED pins" % name)

    # That equality can never FAIL - QC regenerates the header before it runs,
    # so the two always agree. Shown by the sabotage tool: a pin was changed in
    # the json and the check passed. What is worth holding is the generator's
    # own refusals, since a board entered wrongly is a camera that initialises
    # and returns noise.
    import subprocess  # noqa: PLC0415
    import tempfile    # noqa: PLC0415
    import shutil      # noqa: PLC0415
    box = Path(tempfile.mkdtemp(prefix="qc_camgen_"))
    try:
        bad = json.loads(registry.strip_jsonc(
            main.CAM_BOARDS_JSON.read_text(encoding="utf-8")))
        first = sorted(bad["boards"])[0]
        # The message has to NAME the problem, not merely fail. Removing the
        # missing-pin guard still refused the file - with a KeyError, which
        # tells whoever added the board nothing about which pin they forgot.
        for what, breakit, says in (
                ("a missing pin",
                 lambda d: d["boards"][first]["pins"].pop("pclk"), "pclk"),
                ("a GPIO that does not exist",
                 lambda d: d["boards"][first]["pins"].update({"xclk": 99}),
                 "xclk")):
            d = json.loads(registry.strip_jsonc(
                main.CAM_BOARDS_JSON.read_text(encoding="utf-8")))
            breakit(d)
            tmp = box / "cam_boards.json"
            tmp.write_text(json.dumps(d), encoding="utf-8")
            r = subprocess.run(
                [sys.executable, "-c",
                 "import sys;sys.path.insert(0,%r);import gen_tables as g;"
                 "from pathlib import Path;g.CAM_BOARDS_JSON=Path(%r);"
                 "g.gen_cam_boards(Path(%r), ('cam',))"
                 % (str(F.FIRMWARE / "tools"), str(tmp), str(box))],
                capture_output=True, text=True, timeout=90)
            out = (r.stdout or "") + (r.stderr or "")
            t.ok(r.returncode != 0, "the generator refuses %s" % what,
                 "it accepted it and wrote a table - the firmware would compile "
                 "and the camera would return noise")
            t.ok(says in out and "Traceback" not in out,
                 "and says which pin, for %s" % what,
                 "a crash names the pin too, in a stack trace nobody adding a "
                 "board should have to read. The whole message was: %s"
                 % out.strip()[-200:])
    finally:
        shutil.rmtree(box, ignore_errors=True)

    # ---- the drawing is real, and honest about what is missing -------
    for name in boards:
        svg = main.cam_pinout_svg(name)
        if not t.ok(svg and svg.startswith("<svg"), "%s has a diagram" % name):
            continue
        t.ok(len(svg) < 20000, "%s's diagram is small enough to embed" % name,
             "it is %d bytes; the point of drawing it was that the board's own "
             "page cannot carry a big one" % len(svg))
        for key, _label in main.CAM_SIGNALS:
            gpio = boards[name]["pins"][key]
            if gpio >= 0:
                t.contains(svg, "GPIO %d" % gpio,
                           "%s shows %s on GPIO %d" % (name, key.upper(), gpio))
                break

    eye = main.cam_pinout_svg("esp-eye")
    t.contains(eye, "not wired",
               "a pin the board does not wire is SHOWN as not wired")
    t.ok(main.cam_pinout_svg("nope") is None,
         "a board nobody has heard of gets no invented diagram")

    # ---- served, and the right one ----------------------------------
    base, _m = F.start_hub()
    got = _bytes(base + "/pinout.svg?board=ai-thinker")
    t.ok(got.startswith(b"<svg"), "the hub serves a drawn diagram per board")
    plain = _bytes(base + "/pinout.svg")
    t.ok(plain != got and len(plain) > 5000,
         "and the WROOM reference is still there, unchanged",
         "the general drawing is a real reference of a real part; nothing "
         "generates that, so it stays a file")

    # ---- who decides: the hub, not the page -------------------------
    # A camera that cannot say which board it is gets the commonest clone AND a
    # warning. A diagram presented as certain when it is a guess is worse than
    # no diagram, because somebody wires to it.
    pick = main.pinout_for("wifi:203.0.113.9")     # nothing answers there
    t.ok(pick["url"].startswith("/pinout.svg"),
         "an unreachable board still gets an answer, not an error")
    if pick.get("board"):
        t.ok(pick["sure"] is False,
             "and a guessed board says it was guessed",
             "sure=%r with why=%r" % (pick.get("sure"), pick.get("why")))
        t.contains(pick["why"], "guess",
                   "in words the person reading it will understand")

    # DRIVEN, not read. The words `kind != "cam"` appear twice in that
    # function, so asserting on the source passed while the decision itself was
    # removed - the sabotage tool caught that too.
    nong = ""
    for m in main.modules_here():
        if (m.get("type") or "").lower() != "cam":
            for r in m.get("routes", []):
                nong = nong or r.get("dev") or ""
    if t.ok(nong, "there is a non-camera module to ask about",
            "QC's fake module should be on the list"):
        # It must not ASK an arm which camera board it is. Falling through to
        # the camera branch happens to return the same URL, so the answer alone
        # proves nothing - the sabotage tool showed exactly that. What is real
        # is the round trip: a CAM command sent to a nong is an error printed on
        # the module and a wait for nothing.
        asked = []
        real_cmd = main.dev_cmd
        main.dev_cmd = lambda dev, c: asked.append((dev, c)) or ""
        try:
            pick = main.pinout_for(nong)
        finally:
            main.dev_cmd = real_cmd
        t.eq(pick["url"], "/pinout.svg",
             "a board that is not a camera gets the WROOM reference")
        t.eq(pick["board"], "",
             "with no camera board attached to it")
        t.eq(asked, [],
             "and is never asked a camera question to find that out")

    src = (F.HUB / "main.py").read_text(encoding="utf-8")
    i = src.find("def pinout_for")
    body = src[i:i + 1800]
    t.contains(body, "board=",
               "and a camera is asked which board it actually is")

    # ---- and the page asks rather than assuming ---------------------
    t.contains(src, "/api/pinout?dev=",
               "the module page asks the hub which diagram to show")
    j = src.find("/api/pinout?dev=")
    shim = src[j - 400:j + 900]
    t.contains(shim, "p.sure===false",
               "and shows the warning when the hub says it guessed")
    t.ok("'/pinout.svg'" not in shim,
         "the page no longer hardcodes one diagram for every board",
         "that is how a camera ended up being shown a WROOM pinout")


def _bytes(url):
    with urllib.request.urlopen(url, timeout=10) as r:
        return r.read()
