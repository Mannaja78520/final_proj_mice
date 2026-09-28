"""The real robot's size is something you PICK, not something you type.

Asked 2026-09-18 (A26-72): *the forward invert kinematric i will send the step
file later is the full part and my real robot edit in nong studio too make it
preset i will select to use later*.

The STEP file was measured by A30-1/A30-2 into nong_analysis.json: upper arm
128.70 mm, forearm 167.64 mm, shoulder 87.7 mm out from the centre line. Those
numbers now live in ONE place - config/rig_presets.json - and reach Studio
three ways that must not drift:

  * the hub serves them at /api/rigpresets (open, it is a catalogue);
  * Studio fetches them and offers them in the rig panel;
  * Studio carries the measured one as a fallback for opening it with no hub.

What this guards: a preset whose reach does not match its own arm lengths (a
typo nobody would see), a preset that quietly changes the servo settings, and
the fallback drifting away from the file.
"""
import json
import re

import qc as F

AREA = "studio"
TITLE = "the measured robot is a body you can pick in Studio"

NEEDED = ("shoulderX", "shoulderY", "upperLenL", "upperLenR", "foreLenL",
          "foreLenR", "torsoW", "torsoH", "torsoD", "shrugPivot")


def run(t):
    raw = (F.CODE / "config" / "rig_presets.json").read_text(encoding="utf-8")
    data = json.loads(raw)
    presets = data.get("presets") or []
    t.ok(len(presets) >= 2, "there are bodies to pick from (%d)" % len(presets),
         "at least the measured robot and the Studio default")

    ids = [p.get("id") for p in presets]
    t.ok(len(set(ids)) == len(ids), "every body has its own id", ids)
    measured = next((p for p in presets if p.get("id") == "nong_step_2026_09"), None)
    if not t.ok(measured, "the robot measured from the STEP file is one of them",
                ids):
        return

    for p in presets:
        dims = p.get("dims") or {}
        missing = [k for k in NEEDED if k not in dims]
        t.ok(not missing, "%s sets every size the rig has" % p.get("id"),
             "missing: %s - Studio would keep yesterday's number" % missing)
        # The reach is the arm, written down: a typo in a link length shows up
        # here instead of on the robot.
        reach = dims.get("upperLenL", 0) + dims.get("foreLenL", 0)
        t.ok(abs(reach - (p.get("reach_mm") or 0)) < 0.5,
             "%s says the reach its own arm gives (%.2f mm)" % (p.get("id"), reach),
             "reach_mm says %s" % p.get("reach_mm"))
        t.ok((p.get("source") or "").strip(),
             "%s says where its numbers come from" % p.get("id"),
             "a size with no source is a guess nobody can check")

    # ---- measured against the model it came from ------------------------
    d = measured["dims"]
    t.ok(abs(d["upperLenL"] - 128.70) < 0.05 and abs(d["foreLenL"] - 167.64) < 0.05,
         "the measured body carries the STEP file's arm (128.70 / 167.64 mm)",
         "got %s / %s" % (d["upperLenL"], d["foreLenL"]))
    t.ok(d["upperLenL"] == d["upperLenR"] and d["foreLenL"] == d["foreLenR"],
         "and both arms are the same length, as built", d)

    # ---- the hub serves it, without a login -----------------------------
    src = F.hub_src()
    t.ok('"/api/rigpresets"' in src, "the hub serves the list")
    t.ok("rig_presets()" in src, "from the registry, not a second copy in the hub")
    auth = (F.HUB / "hub_auth.py").read_text(encoding="utf-8")
    t.ok('"/api/rigpresets"' in auth.split("OPEN = ", 1)[-1],
         "and reading the catalogue needs no login",
         "it changes nothing; gating it would only stop a page drawing its list")

    # ---- Studio offers it, and its fallback matches the file -------------
    app = (F.STUDIO_WEB / "app.js").read_text(encoding="utf-8", errors="replace")
    t.ok('fetch("/api/rigpresets")' in app, "Studio asks the hub for the list")
    t.ok("function applyRigPreset" in app and "RIG.dims[k] = +v" in app,
         "picking one sets the sizes")
    for word in ("zero", "min", "max", "gear"):
        t.ok(("RIG.%s[" % word) not in app.split("function applyRigPreset", 1)[-1]
             .split("\n}", 1)[0],
             "and it does not touch RIG.%s" % word,
             "a body preset must not rewrite what the fitted servos need")
    # ---- A31-17: the servos come from the STEP too, but only when asked ----
    # *load all from my step*. The shrug is a 4-bar; tools/step_preset.py
    # measures it, and the old hand guess (1:4.5, sent to the board as 1:4
    # because GEAR keeps whole teeth) was 1.9x the real ratio.
    sv = measured.get("servos") or {}
    t.ok(len(sv) == 10, "the measured body names a servo for all 10 joints",
         sorted(sv))
    whole = [n for n, s in sv.items()
             if not all(isinstance(g, int) and g >= 1 for g in s.get("gear", [1, 1]))]
    t.ok(not whole, "every gear is whole teeth, as the board stores it", whole)
    link = measured.get("shrug_linkage") or {}
    shr = sv.get("SHRUG", {})
    g = shr.get("gear") or [1, 1]
    t.ok(link.get("ratio") and abs(g[1] / g[0] - link["ratio"]) < 0.01,
         "the SHRUG gear is the 4-bar's measured ratio (%s)" % link.get("ratio"),
         "gear %s" % g)
    rng = link.get("range_deg", 0)
    t.ok(shr.get("min") == 90 - rng and shr.get("max") == 90 + rng,
         "and its limits are the +-%s deg the linkage was measured over" % rng, shr)
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("step_preset", F.CODE / "tools" / "step_preset.py")
        sp = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(sp)
        fs = measured["from_step"]
        folder = sp.ROOT / fs["dir"]
        if (folder / fs["robot"]).is_file():
            full = sp.parts(folder, fs["robot"])
            up = [1.0 if i == fs.get("up_axis", 1) else 0.0 for i in range(3)]
            again = sp.shrug(folder, fs["shrug"], full, up)
            t.ok(abs(again["ratio"] - link.get("ratio", 0)) < 0.005,
                 "re-measuring the STEP file gives the same ratio (%.3f)" % again["ratio"],
                 "the preset says %s - run python tools/step_preset.py --write" % link.get("ratio"))
    except Exception as e:  # noqa: BLE001 - the tool crashing is the finding
        t.ok(False, "tools/step_preset.py reads the STEP file", repr(e)[:200])
    body = app.split("function applyRigPreset", 1)[-1].split("\n}", 1)[0]
    # the call must BE the statement the confirm guards, not merely come after it
    t.ok(re.search(r"if \(p\.servos && confirm\((?:[^;]|\n)*?\)\)\s*\n\s*servos = "
                   r"applyPresetServos\(p\);", body) is not None
         and body.count("applyPresetServos(") == 1,
         "picking the body only sets its servos after the person says yes",
         "the servos rewrite what the fitted robot needs - never silently")

    # inside the fallback LIST, not the built-in default rig above it
    fallback = app.split("let RIG_PRESETS", 1)[-1].split("async function", 1)[0]
    m = re.search(r"upperLenL:\s*([\d.]+),\s*upperLenR:\s*([\d.]+)", fallback)
    t.ok(m and abs(float(m.group(1)) - d["upperLenL"]) < 0.05,
         "the no-hub fallback carries the same arm as the file",
         "fallback %s vs file %s" % (m.group(1) if m else "none", d["upperLenL"]))
