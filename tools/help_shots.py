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


class ShotCatalog:
    def __init__(self, root):
        self.root = root

    def recipes(self):
        for recipe in sorted(self.root.glob("apps/*/help/shots.json")):
            yield recipe.parent.parent.name, recipe
        yield "hub", self.root / "main_python/web/help/shots.json"


class HelpShooter:
    def __init__(self, browser, base, out=None):
        self.browser = browser
        self.base = base
        self.out = out

    def capture(self, shot, lang, mode):
        with self.browser.new_context(viewport=shot.get("viewport", VIEWPORT), color_scheme=mode,
                                      service_workers="block") as context:
            login = context.request.post(self.base + "/api/login",
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
            self.demo_routes(context, shot.get("responses", {}))
            page = context.new_page()
            page.set_default_timeout(8000)
            response = page.goto(self.base + shot["url"], wait_until="domcontentloaded")
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

    def demo_routes(self, context, responses):
        def permitted(route):
            req = route.request
            url = urlsplit(req.url)
            if req.method != "GET" or not req.url.startswith(self.base + "/"):
                return route.abort()
            fixture = responses.get(url.path)
            if isinstance(fixture, dict) and "$qr" in fixture:
                sys.path.insert(0, str(ROOT / "main_python"))
                import qr
                return route.fulfill(content_type="image/svg+xml", body=qr.svg(fixture["$qr"]))
            if fixture is not None:
                return route.fulfill(json=fixture)
            return route.continue_()
        context.route("**/*", permitted)

    def run(self, catalog, apps, only):
        failures = []
        for app, recipe in catalog.recipes():
            if apps and app not in apps:
                continue
            shots = json.loads(recipe.read_text(encoding="utf-8"))
            folder = self.out / app if self.out else recipe.parent / "img"
            folder.mkdir(parents=True, exist_ok=True)
            for name, shot in shots.items():
                if only and name not in only:
                    continue
                variants = {}
                failed = False
                for lang in LANGS:
                    for mode in THEMES:
                        key = f"{lang}-{mode}-{name}"
                        try:
                            variants[key] = self.capture(shot, lang, mode)
                        except (Error, RuntimeError) as exc:
                            failures.append(f"{app}/{key}: {str(exc).splitlines()[0]}")
                            print(failures[-1], flush=True)
                            failed = True
                            break
                    if failed:
                        break
                if len(variants) == len(LANGS) * len(THEMES):
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
    args = p.parse_args()
    base = args.base.rstrip("/")
    url = urlsplit(base)
    if url.scheme != "http" or url.hostname not in {"127.0.0.1", "localhost"} or url.path:
        p.error("--base needs a loopback demo Hub URL")
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel="msedge", args=["--use-gl=angle", "--use-angle=swiftshader",
                                                            "--enable-unsafe-swiftshader"])
        try:
            return 0 if HelpShooter(browser, base, args.out).run(ShotCatalog(ROOT), args.app, args.only) else 1
        finally:
            browser.close()


if __name__ == "__main__":
    sys.exit(main())
