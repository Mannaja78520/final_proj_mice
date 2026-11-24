"""Capture Help screenshots from a local, isolated Hub running demo data.

Use tools/visual/serve_hub.py, then run this with its URL. Requires Playwright,
Edge and Pillow. Review each result before committing assets to the public repo.
"""
import argparse
from io import BytesIO
import json
import os
from pathlib import Path
import sys
from urllib.parse import urlsplit

from PIL import Image
from playwright.sync_api import Error, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
LANGS = ("th", "en", "zh", "ja")
THEMES = {"light": "daylight", "dark": "midnight"}
VIEWPORT = {"width": 1440, "height": 900}


def loopback_origin(value):
    url = urlsplit(value)
    if (url.scheme != "http" or url.hostname not in {"127.0.0.1", "localhost"}
            or url.username or url.password or url.path or url.query or url.fragment):
        raise ValueError("expected an HTTP loopback origin")
    return value


class ShotCatalog:
    def __init__(self, root):
        self.root = root

    def recipes(self):
        for recipe in sorted(self.root.glob("apps/*/help/shots.json")):
            yield recipe.parent.parent.name, recipe
        yield "hub", self.root / "main_python/web/help/shots.json"


class HelpShooter:
    def __init__(self, browser, base, out=None, native=None, states=None):
        self.browser = browser
        self.base = base
        self.out = out
        self.native = native or {}
        self.states = states or {}

    def capture(self, shot, lang, mode, app):
        direct = shot.get("direct", False)
        base = self.native.get(app) if direct else self.base
        if not base:
            raise RuntimeError(f"Set --native {app}=URL for its isolated demo app")
        options = {}
        if direct and app in self.states and not shot.get("anonymous"):
            options["storage_state"] = self.states[app]
        with self.browser.new_context(viewport=shot.get("viewport", VIEWPORT), color_scheme=mode,
                                      service_workers="block", **options) as context:
            if not direct:
                login = context.request.post(base + "/api/login",
                                             data={"password": os.environ.get("HUB_PW", "qc-test-password")})
                if not login.ok:
                    raise RuntimeError("Demo Hub login failed")
            context.add_init_script(
                f"localStorage.setItem('mice.lang', {json.dumps(lang)});"
                f"localStorage.setItem('mice_theme', {json.dumps(THEMES[mode])});"
                "document.addEventListener('DOMContentLoaded', () => {"
                "const style = document.createElement('style');"
                "style.textContent = '*,*::before,*::after{transition:none!important;animation:none!important}';"
                "document.head.append(style); });"
            )
            self.demo_routes(context, base, shot.get("responses", {}), direct)
            page = context.new_page()
            page.set_default_timeout(8000)
            response = self.go(page, base, shot["url"])
            if not response or not response.ok:
                raise RuntimeError(f"Could not open {shot['url']}")
            if not shot.get("native"):
                page.wait_for_function("(m) => document.documentElement.dataset.mode === m", arg=mode)
                page.locator("#miceLang").wait_for(state="attached")
                if lang != "en":
                    page.wait_for_function("window.MiceLang && MiceLang.say('Log in') !== 'Log in'")
            for step in shot.get("steps", []):
                if "click" in step:
                    page.locator(step["click"]).click()
                if "fill" in step:
                    field = step["fill"]
                    value = os.environ[field["env"]] if "env" in field else field["value"]
                    page.locator(field["selector"]).fill(value)
                if "goto" in step:
                    self.go(page, base, step["goto"])
                if "eval" in step:
                    page.evaluate(step["eval"])
                if "wait" in step:
                    page.locator(step["wait"]).first.wait_for()
            if "ready" in shot:
                page.locator(shot["ready"]).first.wait_for()
            page.evaluate("document.fonts.ready.then(() => true)")
            # Shared language packs and the first asynchronous UI read finish
            # after the language picker appears. Avoid racing translated labels.
            page.wait_for_timeout(650)
            kwargs = {"animations": "disabled", "timeout": 10000}
            if "clip" in shot:
                png = page.locator(shot["clip"]).screenshot(**kwargs)
            else:
                png = page.screenshot(**kwargs)
        with Image.open(BytesIO(png)) as image:
            out = BytesIO()
            image.convert("RGB").save(out, "WEBP", quality=88, method=4)
        return out.getvalue()

    @staticmethod
    def go(page, base, path):
        if not path.startswith("/") or path.startswith("//") or "\\" in path:
            raise RuntimeError("Screenshot routes must stay on the demo origin")
        return page.goto(base + path, wait_until="domcontentloaded")

    def demo_routes(self, context, base, responses, direct):
        def permitted(route):
            req = route.request
            url = urlsplit(req.url)
            if not req.url.startswith(base + "/") or (not direct and req.method != "GET"):
                return route.abort()
            fixture = responses.get(url.path)
            if isinstance(fixture, dict) and "$qr" in fixture:
                sys.path.insert(0, str(ROOT / "main_python"))
                import qr
                return route.fulfill(content_type="image/svg+xml", body=qr.svg(fixture["$qr"]))
            if fixture is not None and req.method == "GET":
                return route.fulfill(json=fixture)
            return route.continue_()
        context.route("**/*", permitted)

    def run(self, catalog, apps, only, mode=None):
        failures = []
        for app, recipe in catalog.recipes():
            if apps and app not in apps:
                continue
            shots = json.loads(recipe.read_text(encoding="utf-8"))
            manifest = recipe.parent / "help.json"
            meta = json.loads(manifest.read_text(encoding="utf-8")) if manifest.is_file() else {}
            folder = self.out / app if self.out else recipe.parent / "img"
            folder.mkdir(parents=True, exist_ok=True)
            for name, shot in shots.items():
                if only and name not in only:
                    continue
                pairs = [(lang, theme) for lang in LANGS for theme in THEMES if mode in (None, theme)]
                if shot.get("fixed"):
                    lang, default = meta["nativeVariant"].split("-")
                    theme = mode or default
                    pairs = [(lang, theme)] if theme in shot.get("modes", [default]) else []
                if not pairs:
                    continue
                variants = {}
                for lang, theme in pairs:
                    key = f"{lang}-{theme}-{name}"
                    try:
                        variants[key] = self.capture(shot, lang, theme, app)
                    except (Error, RuntimeError, KeyError) as exc:
                        failures.append(f"{app}/{key}: {str(exc).splitlines()[0]}")
                        print(failures[-1], flush=True)
                        break
                if len(variants) == len(pairs):
                    for key, blob in variants.items():
                        (folder / (key + ".webp")).write_bytes(blob)
                    print(f"{app}/{name}: {len(variants)} WebP files", flush=True)
        return not failures


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--base", required=True, help="local demo Hub URL")
    p.add_argument("--app", action="append", help="app id or hub (repeatable)")
    p.add_argument("--only", action="append", help="shot name (repeatable)")
    p.add_argument("--out", type=Path, help="capture outside shipping folders for review")
    p.add_argument("--native", action="append", default=[], metavar="APP=URL",
                   help="isolated native demo app origin. Its normal UI actions can write demo data")
    p.add_argument("--state", action="append", default=[], metavar="APP=JSON",
                   help="private Playwright storage state from the isolated demo instance")
    p.add_argument("--fake-camera", action="store_true", help="use Edge's synthetic camera input")
    p.add_argument("--mode", choices=THEMES, help="capture only this mode; select it in the demo app first")
    args = p.parse_args()
    try:
        base = loopback_origin(args.base.rstrip("/"))
        native = {app: loopback_origin(url.rstrip("/"))
                  for app, url in (pair.split("=", 1) for pair in args.native)}
        states = dict(pair.split("=", 1) for pair in args.state)
    except ValueError as exc:
        p.error(str(exc))
    flags = ["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"]
    if args.fake_camera:
        flags.extend(["--use-fake-device-for-media-stream", "--use-fake-ui-for-media-stream"])
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel="msedge", args=flags)
        try:
            shooter = HelpShooter(browser, base, args.out, native, states)
            return 0 if shooter.run(ShotCatalog(ROOT), args.app, args.only, args.mode) else 1
        finally:
            browser.close()


if __name__ == "__main__":
    sys.exit(main())
