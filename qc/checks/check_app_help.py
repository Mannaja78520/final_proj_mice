"""Installed app Help follows the Tools list, and shipped screenshots are complete."""
import json
from pathlib import Path
import re
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from urllib.request import urlopen

import qc as F

AREA = "hub"
TITLE = "App Help follows installation and ships every language and screenshot"
SLOW = False


def shots_in(path):
    return set(re.findall(r'\bdata-shot="([a-z0-9_-]+)"', path.read_text(encoding="utf-8")))


def full_catalog(t, folder, shots, langs, native=None):
    recipes = json.loads((folder / "shots.json").read_text(encoding="utf-8"))
    t.eq(set(recipes), shots, f"{folder.name}: each used view has a capture recipe")
    missing = []
    for shot in sorted(shots):
        recipe = recipes.get(shot, {})
        variants = [f"{lang}-{mode}" for lang in langs for mode in ("light", "dark")]
        if recipe.get("fixed"):
            if not native:
                missing.append(f"{shot}: nativeVariant")
                continue
            lang, default = native.split("-")
            variants = [f"{lang}-{mode}" for mode in recipe.get("modes", [default])]
        for variant in variants:
            img = folder / "img" / f"{variant}-{shot}.webp"
            if not img.is_file() or img.read_bytes()[:12][8:12] != b"WEBP":
                missing.append(img.name)
    t.eq(missing, [], f"{folder.name}: every required WebP variant is present")


def sources(t, app_help, registry):
    by_app = {}
    for app in registry.apps():
        folder = app["manifest_dir"] / "help"
        if not folder.is_dir():
            continue
        anchor = app.get("help") or app["id"]
        meta = app_help.AppHelp.read(folder, anchor)
        if not t.ok(meta is not None, f"{app['id']}: manifest and four language files", folder.name):
            continue
        refs = {}
        for lang in app_help.LANGS:
            path = folder / (lang + ".html")
            body = path.read_text(encoding="utf-8")
            t.eq(re.findall(r'<section id="([^"]+)"', body), [anchor],
                 f"{app['id']}: {lang} fragment preserves the Help anchor")
            t.ok(not re.search(r'<img\b[^>]*\bsrc=', body), f"{app['id']}: {lang} uses recipe images",
                 "Replace fixed image URLs with data-shot")
            refs[lang] = shots_in(path)
        t.ok(bool(refs["th"]) and all(shots == refs["th"] for shots in refs.values()),
             f"{app['id']}: every language illustrates the same steps", refs)
        by_app[app["id"]] = refs["th"]
        full_catalog(t, folder, refs["th"], app_help.LANGS, meta.get("nativeVariant"))
    t.ok(len(by_app) >= 8, "the eight initial app guides are covered", sorted(by_app))

    # A Hub gallery picture may reuse an installed app's own screenshot.
    hub = F.CODE / "main_python/web/help"
    sources = (hub / "parts/hub.html", hub / "parts/bytask.html")
    refs = set()
    for path in sources:
        body = path.read_text(encoding="utf-8")
        t.ok("/docs/shots/" not in body and "/img/help/" not in body,
             f"{path.name}: illustrated steps use new captures", "Found an old static picture")
        app_refs = set()
        for shot, app in re.findall(r'data-shot="([^"]+)"\s+data-shot-app="([^"]+)"', body):
            t.ok(shot in by_app.get(app, set()), f"{path.name}: {app}/{shot} exists", shot)
            app_refs.add(shot)
        refs.update(shots_in(path) - app_refs)
    full_catalog(t, hub, refs, app_help.LANGS)


def app_ids(base):
    status, data = F.get(base + "/api/help/apps")
    assert status == 200, data
    return {a["id"]: a for a in json.loads(data)["apps"]}


def install_round_trip(t, base, langs):
    app_id = "qc-help-example"
    url = base + "/api/help/apps/" + app_id + "/"
    with TemporaryDirectory(prefix="mice-app-help-") as tmp:
        folder = Path(tmp)
        meta = {key: dict.fromkeys(langs, words) for key, words in
                (("title", "Example Guide"), ("summary", "Install and remove this guide"))}
        meta.update(group="use", order=99, nativeVariant="en-light")
        (folder / "web").mkdir()
        (folder / "web/index.html").write_text("<h1>Example</h1>", encoding="utf-8")
        (folder / "mice-app.json").write_text(json.dumps(
            {"id": app_id, "name": "Example", "root": "web", "help": "example-guide"}), encoding="utf-8")
        help_dir = folder / "help"
        help_dir.mkdir()
        (help_dir / "help.json").write_text(json.dumps(meta), encoding="utf-8")
        for lang in langs:
            (help_dir / (lang + ".html")).write_text(
                '<section id="example-guide"><h2>' + lang + '</h2></section>', encoding="utf-8")
        image_dir = help_dir / "img"
        image_dir.mkdir()
        image = next((F.CODE / "apps/voice/help/img").glob("en-light-*.webp")).read_bytes()
        (image_dir / "en-light-demo.webp").write_bytes(image)
        dark = next((F.CODE / "apps/voice/help/img").glob("en-dark-*.webp")).read_bytes()
        (image_dir / "en-dark-paired.webp").write_bytes(dark)
        (image_dir / "en-light-paired.webp").write_bytes(image)

        t.ok(app_id not in app_ids(base), "uninstalled extension does not contribute a guide", app_id)
        result = F.post(base + "/api/extensions/add", json.dumps({"folder": str(folder)}).encode())
        try:
            t.eq(result[0], 200, "Tools Add app accepts the test extension")
            app = app_ids(base).get(app_id, {})
            t.eq(app.get("anchor"), "example-guide", "installed extension keeps its declared anchor")
            t.eq(app.get("title"), meta["title"], "localized titles are read from extension manifest")
            with urlopen(url + "img/ja-dark-demo.webp", timeout=10) as response:
                t.eq(response.read() == image, True, "native picture serves in other Help variants")
            with urlopen(url + "img/ja-dark-paired.webp", timeout=10) as response:
                t.eq(response.read() == dark, True, "native picture prefers the requested theme when available")
            for lang in langs:
                status, html = F.get(url + lang + ".html")
                t.eq(status, 200, f"{lang} fragment is served from the extension's manifest folder")
                t.contains(html, f"<h2>{lang}</h2>", f"the {lang} fragment matches the requested language")
            t.eq(F.get(url + "%2e%2e/mice-app.json")[0], 404, "Help asset route refuses paths outside Help")
        finally:
            result = F.post(base + "/api/extensions/remove", json.dumps({"id": app_id}).encode())
        t.eq(result[0], 200, "Tools Remove app accepts the test extension")
        t.ok(app_id not in app_ids(base), "removed extension disappears from the Help list", app_id)
        t.eq(F.get(url + "en.html")[0], 404, "removed extension's Help URL no longer serves its text")


def served_images(t, base):
    examples = (
        ("/hubweb/help/img/", F.CODE / "main_python/web/help/img"),
        ("/api/help/apps/voice/img/", F.CODE / "apps/voice/help/img"),
    )
    for prefix, folder in examples:
        sample = next(iter(sorted(folder.glob("*.webp"))))
        with urlopen(base + prefix + sample.name, timeout=10) as response:
            t.eq(response.headers.get_content_type(), "image/webp", f"{prefix} serves the WebP media type")
            t.eq(response.read() == sample.read_bytes(), True, f"{prefix} serves the checked-in bytes")


def reconize_package(t, app_help):
    original = F.CODE / "apps/faces/help"
    package = F.CODE / "docs/friend/reconize_help_package/help"

    def contents(folder):
        return {path.relative_to(folder): path.read_bytes()
                for path in folder.rglob("*") if path.is_file()}

    t.eq(contents(package) == contents(original), True,
         "Reconize drop-in Help matches the installed fallback byte for byte")
    jao = F.CODE / "docs/friend/all_jao_help_package/help"
    t.eq(contents(jao) == contents(F.CODE / "apps/all-jao/help"), True,
         "All-Jao drop-in Help matches the installed fallback byte for byte")
    partner = {"folder": str(package.parent)}
    hub = SimpleNamespace(
        read_partners=lambda: {"partners": {"reconize": partner}},
        hub_apps=lambda **_: [{"id": "faces", "needs": "reconize", "help": "faces",
                               "manifest_dir": original.parent}],
    )
    catalog = app_help.AppHelp(hub)
    t.eq(catalog.available()["faces"][0], package, "Hub prefers the partner's drop-in Help")
    partner.clear()
    t.eq(catalog.available()["faces"][0], original, "Hub keeps the fallback when partner has no folder")


def run(t):
    sys.path.insert(0, str(F.CODE / "main_python"))
    sys.path.insert(0, str(F.CODE / "tools"))
    import hub_api_help
    import registry

    sources(t, hub_api_help, registry)
    reconize_package(t, hub_api_help)
    base, _ = F.start_hub()
    _, raw = F.get(base + "/api/apps")
    shown = {a["id"] for a in json.loads(raw)["apps"]}
    guides = app_ids(base)
    t.ok({"studio", "voice"} <= guides.keys() <= shown,
         "Hub Help shows the installed apps with guides", sorted(guides))
    served_images(t, base)
    install_round_trip(t, base, hub_api_help.LANGS)
