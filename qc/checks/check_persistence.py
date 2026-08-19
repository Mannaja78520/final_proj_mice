"""Everything the user can save must come back exactly as it went in.

`/api/list` was the only storage endpoint QC touched, and it only proved the
hub answers — not that a project keeps its rig, or that a sequence survives a
round trip through the SD card. Losing an afternoon's tuning to a save that
silently dropped a field is the failure this guards against.

Round trips, not status codes.
"""
import json
import urllib.parse

import fake_serial
import fake_wifi
import qc as F

AREA = "persistence"
TITLE = "saving gives back exactly what went in"
SLOW = False


def run(t):
    fake_serial.reset()
    fake_wifi.reset()
    wifi_ip = fake_wifi.start()
    base, main = F.start_hub()

    # ---- projects: rig, meshes and timeline together -------------------
    project = {
        "keys": [{"pose": [90] * 10, "t": 1000, "hold": 250},
                 {"pose": [25, 155] + [90] * 8, "t": 800, "hold": 0, "dps": 45}],
        "rig": {"gearPinion": [14] * 10, "gearGear": [19] * 10,
                "servoRange": [180] * 10, "min": [25] * 10, "max": [155] * 10,
                "tilt": [[0, 0, -55]] * 10},
        "speedDps": 137, "maxDps": 400, "loop": True,
        "meshes": {"torso": {"file": "torso.stl", "scale": 1.5}},
    }
    name = "_qc_roundtrip"
    s, b = _post(base, "/api/save", {"name": name, "project": project})
    t.eq(s, 200, "a project saves")
    saved = json.loads(b)
    t.ok(saved.get("ok"), "the save reports success", b[:120])

    s, b = F.get("%s/api/list?kind=projects" % base)
    t.contains(b, name, "it appears in the project list")

    s, b = F.get("%s/api/load?name=%s.json" % (base, name))
    t.eq(s, 200, "and loads back")
    back = json.loads(b)
    # the parts a user would be furious to lose
    t.eq(back.get("rig", {}).get("gearPinion"), [14] * 10,
         "the tuned gear survives the round trip")
    t.eq(back.get("rig", {}).get("tilt"), [[0, 0, -55]] * 10,
         "the joint axis tilts survive")
    t.eq(back.get("speedDps"), 137, "the sequence speed survives")
    t.eq(len(back.get("keys", [])), 2, "every keyframe survives")
    t.eq(back["keys"][1].get("dps"), 45, "a per-move speed override survives")
    t.eq(back["keys"][0].get("hold"), 250, "a hold survives")
    t.eq(back.get("meshes", {}).get("torso", {}).get("scale"), 1.5,
         "the model settings survive")

    # ---- sequences: export, then read back ----------------------------
    yaml = ("name: qc_seq\nloop: false\nnext: after.yaml\nsteps:\n"
            "  - speed: 150\n"
            '  - pose: "90 90 90 90 90 90 90 90 90 90 T 900"\n'
            "  - wait: 400\n"
            "  - speed: 30\n"
            '  - pose: "25 155 90 90 90 90 90 90 90 90 T 3200"\n')
    s, b = _post(base, "/api/export", {"name": "_qc_seq", "yaml": yaml})
    t.eq(s, 200, "a sequence exports")
    s, b = F.get("%s/api/loadseq?name=_qc_seq.yaml" % base)
    t.eq(s, 200, "and reads back")
    t.eq(b, yaml, "byte for byte — no step, speed or chain lost")

    # ---- the robot's SD card, on a cable AND on WiFi -------------------
    # These are different code paths: FBEGIN/FDATA/FEND over a cable, the
    # module's HTTP file API over WiFi. Only the cable one was ever tested.
    body = b"name: uploaded\nsteps:\n  - pose: \"90 90 90 90 90 90 90 90 90 90 T 500\"\n"
    dev = "wifi:%s" % wifi_ip
    s, b = _post_raw(base, "/api/dev/upload?dev=%s&dir=/moves&name=qc_up.yaml"
                     % urllib.parse.quote(dev), body)
    t.eq(s, 200, "WiFi: a sequence uploads to the card")
    s, b = F.get("%s/api/dev/download?dev=%s&path=%s"
                 % (base, urllib.parse.quote(dev),
                    urllib.parse.quote("/moves/qc_up.yaml")))
    t.eq(b.encode(), body, "WiFi: and comes back byte for byte")
    s, b = F.get("%s/api/dev/delete?dev=%s&path=%s"
                 % (base, urllib.parse.quote(dev),
                    urllib.parse.quote("/moves/qc_up.yaml")))
    t.ok("qc_up.yaml" not in fake_wifi.MODULE.files, "WiFi: and deletes")

    # ---- the rig default the user bakes in ----------------------------
    # This endpoint OVERWRITES the shipped rig — the file holding the real
    # robot's measured geometry. An earlier version of this check wrote a
    # 3-field dummy over it and destroyed the user's tuning; only the promote
    # gate refusing kept it out of the working tree. Back it up and put it back.
    rig_file = F.STUDIO / "rig_default.json"
    saved_rig = rig_file.read_bytes() if rig_file.is_file() else None
    try:
        rig = {"min": [25] * 10, "max": [155] * 10, "gearPinion": [14] * 10}
        s, b = _post(base, "/api/rigdefault", {"rig": rig})
        t.eq(s, 200, "the factory-default rig saves")
        s, b = F.get(base + "/rig_default.js")
        t.contains(b, "NONG_RIG_DEFAULT", "and is served to a fresh browser")
        t.contains(b, '"gearPinion"', "carrying the tuned values")
    finally:
        if saved_rig is not None:
            rig_file.write_bytes(saved_rig)
        elif rig_file.is_file():
            rig_file.unlink()
    # and the real one is back, untouched
    if saved_rig is not None:
        t.eq(rig_file.read_bytes(), saved_rig,
             "the real tuned rig is restored, not left overwritten")

    # ---- names that must be refused -----------------------------------
    # A save endpoint that accepts a path is a way out of the folder.
    for bad in ("../evil.json", "..\\evil.json", "a/b.json", ""):
        s, b = _post(base, "/api/save", {"name": bad, "project": {}})
        t.ok(s >= 400, "a project named %r is refused" % bad,
             "returned %s — a name with a path escapes the folder" % s)
    for bad in ("../x.stl", "shell.exe", "notes.txt"):
        s, b = _post_raw(base, "/api/model/upload?name=" + urllib.parse.quote(bad), b"x")
        t.ok(s >= 400, "a model named %r is refused" % bad)

    _cleanup(name)


def _post(base, path, obj):
    return _post_raw(base, path, json.dumps(obj).encode())


def _post_raw(base, path, body):
    # Through F.post, not a hand-rolled request: the hub now needs a login for
    # anything that writes, and F.post is what carries the session. A check
    # that built its own request silently lost the cookie and got a 401 that
    # looked like the save being broken.
    try:
        return F.post(base + path, body, timeout=20)
    except Exception as e:  # noqa: BLE001
        return 0, repr(e)


def _cleanup(name):
    for p in ((F.STUDIO / "projects" / (name + ".json")),
              (F.STUDIO / "sequences" / "_qc_seq.yaml")):
        try:
            p.unlink()
        except OSError:
            pass
