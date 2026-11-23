"""Theme packs install like extensions, and a pack that is hard to read is refused (2026-11-23).

User 2026-11-23: themes like VS Code extensions - install a pack, press Use - with a cute
"Cloudy" and a second pretty one, and pictures that follow dark/light. The text stays WCAG AA
in every pack, built in or installed, so the gate is in theme_packs.py itself and this
proves it: break the contrast floor, the traversal guard or the SVG guard and a line fails.
"""
import io
import json
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

import qc as F

AREA = "hub"
TITLE = "theme packs: built-ins are readable, install/remove work, unsafe or unreadable packs are refused"

GOOD = {"id": "qcpack", "name": "QC Pack", "mode": "light", "note": "test",
        "colors": {"bg": "#ffffff", "card": "#fafafa", "sunk": "#eeeeee", "line": "#cccccc",
                   "txt": "#111111", "mut": "#555555", "acc": "#0b3d91", "on-acc": "#ffffff",
                   "btn": "#eeeeee", "ok": "#146c43", "warn": "#8a4b00", "err": "#a01c2c"}}


def pack(cfg, extra=None):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("theme.json", json.dumps(cfg))
        for k, v in (extra or {}).items():
            z.writestr(k, v)
    return buf.getvalue()


def refused(T, data):
    try:
        T.install(data)
    except Exception as e:                                  # noqa: BLE001
        return str(e)
    return ""


def run(t):
    sys.path.insert(0, str(F.HUB))
    import theme_packs as TP

    box = Path(tempfile.mkdtemp(prefix="qc_themes_"))
    try:
        T = TP.ThemePacks(F.CODE / "shared" / "web" / "themes", box)
        ids = {c["id"]: c for c in T.all()}
        for need, mode in (("cloudy", "light"), ("cream", "light"), ("aurora", "dark")):
            t.ok(need in ids and ids[need]["mode"] == mode, "built-in pack %s (%s) is there" % (need, mode),
                 sorted(ids))
        # A folder in themes/ that fails its own rules would silently vanish from the list.
        folders = sorted(p.name for p in (F.CODE / "shared" / "web" / "themes").iterdir() if p.is_dir())
        t.ok(sorted(ids) == folders, "every built-in pack folder passes validation", (sorted(ids), folders))
        css = T.css()
        t.ok(':root[data-theme="cloudy"]' in css and '--theme-mode:"dark"' in css,
             "packs become CSS blocks that declare light/dark", css[:80])

        T2 = TP.ThemePacks(box / "none", box / "user")
        t.eq(refused(T2, pack(GOOD)), "", "a readable pack installs")
        t.ok([c["id"] for c in T2.all()] == ["qcpack"], "the installed pack is listed", T2.all())
        low = json.loads(json.dumps(GOOD)); low["id"] = "faint"; low["colors"]["txt"] = "#999999"
        why = refused(T2, pack(low))
        t.ok("readable" in why and "faint" not in [c["id"] for c in T2.all()],
             "grey-on-white text is refused with its ratio", why)
        for bad_id in ("Bad Id", "../x", "midnight"):
            c = json.loads(json.dumps(GOOD)); c["id"] = bad_id
            t.ok(refused(T2, pack(c)) != "", "id %r is refused" % bad_id)
        c = json.loads(json.dumps(GOOD)); c["id"] = "withsvg"; c["art"] = "a.svg"
        t.ok("active content" in refused(T2, pack(c, {"a.svg": "<svg><script>x</script></svg>"})),
             "an SVG with a script is refused")
        t.eq(refused(T2, pack(c, {"a.svg": "<svg xmlns='http://www.w3.org/2000/svg'/>"})), "", "a clean SVG is accepted")
        t.ok(T2.file("withsvg", "a.svg") is not None and T2.file("withsvg", "theme.json") is None,
             "only pictures a pack names are served", "")
        c["mode"] = "purple"
        t.ok(refused(T2, pack(c)) != "", "mode must be light or dark")
        T2.remove("qcpack")
        t.ok("qcpack" not in [x["id"] for x in T2.all()], "an installed pack can be removed", "")
        try:
            T.remove("cloudy"); gone = False
        except TP.ThemePackError:
            gone = True
        t.ok(gone and "cloudy" in {c["id"] for c in T.all()}, "a built-in pack cannot be removed", "")
    finally:
        shutil.rmtree(box, ignore_errors=True)
