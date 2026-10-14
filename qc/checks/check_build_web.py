"""Web source edits reach served output; missing parts and bad syntax stop builds."""
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile

AREA = 'tools'
TITLE = 'web builds repeat from templates and reject incomplete source'


def run(t):
    tree = Path(__file__).resolve().parents[2]
    spec = importlib.util.spec_from_file_location('web_builder_check', tree / 'tools/build_web.py')
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    with tempfile.TemporaryDirectory(prefix='mice-build-web-') as tmp:
        root = Path(tmp)
        (root / 'tools').mkdir()
        app = root / 'app'
        app.mkdir()
        studio = root / 'studio'
        (studio / 'app_parts').mkdir(parents=True)
        (root / 'tools/web_build.json').write_text(json.dumps({
            'inline_apps': ['app'], 'studio': {'path': 'studio', 'parts': ['state.js', 'boot.js']}
        }))
        (app / 'index.template.html').write_bytes(b'<link rel="stylesheet" href="style.css">\n<script src="app.js"></script>')
        (app / 'style.css').write_bytes(b'body{color:red}')
        (app / 'app.js').write_bytes(b'const example = 1;')
        (studio / 'app_parts/state.js').write_bytes(b'let ready = true;')
        (studio / 'app_parts/boot.js').write_bytes(b'if (!ready) throw new Error();')
        builder.build(root)
        output = app / 'index.html'
        template = (app / 'index.template.html').read_bytes()
        mtime = output.stat().st_mtime_ns
        t.eq(builder.build(root), [], 'identical build updates no output')
        t.eq(output.stat().st_mtime_ns, mtime, 'identical build preserves output mtime')
        (app / 'app.js').write_bytes(b'const example = 2;')
        builder.build(root)
        t.contains(output.read_text(), 'example = 2', 'second build uses edited JS, not stale inline content')
        t.eq((app / 'index.template.html').read_bytes(), template, 'source template stays intact')
        before = output.read_bytes()
        (studio / 'app_parts/boot.js').unlink()
        try:
            builder.build(root)
            rejected = False
        except ValueError:
            rejected = True
        t.ok(rejected, 'missing required Studio part fails the build')
        t.eq(output.read_bytes(), before, 'failed build leaves previous outputs intact')
        (studio / 'app_parts/boot.js').write_bytes(b'let this.broken = true;')
        if shutil.which('node'):
            try:
                builder.build(root)
                rejected = False
            except ValueError:
                rejected = True
            t.ok(rejected, 'invalid JavaScript fails before browser launch')
        (studio / 'app_parts/extra.js').write_bytes(b'')
        try:
            builder.build(root)
            rejected = False
        except ValueError:
            rejected = True
        t.ok(rejected, 'unlisted source cannot silently disappear from bundle')
        (studio / 'app_parts/extra.js').unlink()
        (studio / 'app_parts/boot.js').write_bytes(b'if (!ready) throw new Error();')
        _pages(t, builder, root)


def _pages(t, builder, root):
    """A page cut into parts (Home, A41-3): every part placed once, in order."""
    home = root / 'home'
    (home / 'parts').mkdir(parents=True)
    manifest = json.loads((root / 'tools/web_build.json').read_text())
    manifest['pages'] = [{'path': 'home', 'out': 'out.html', 'js': ['a.js', 'b.js']}]
    (root / 'tools/web_build.json').write_text(json.dumps(manifest))
    (home / 'index.template.html').write_bytes(
        b'<link rel="stylesheet" href="style.css">\n<!-- part: top.html -->\n'
        b'<script src="app.js"></script>\n')
    (home / 'style.css').write_bytes(b'b{color:red}')
    (home / 'parts/top.html').write_bytes(b'<h1>top</h1>\n')
    (home / 'parts/a.js').write_bytes(b'var first = 1;\n')
    (home / 'parts/b.js').write_bytes(b'var second = first + 1;\n')
    builder.build(root)
    out = (root / 'out.html').read_text()
    t.ok('<h1>top</h1>' in out and '<!-- part:' not in out,
         'a page part lands where the template places it', out)
    t.ok(out.find('var first') < out.find('var second') and 'b{color:red}' in out,
         'script parts join in the listed order, the stylesheet inlined', out)

    def refused():
        try:
            builder.build(root)
            return False
        except ValueError:
            return True
    (home / 'parts/stray.js').write_bytes(b'var lost = 1;\n')
    t.ok(refused(), 'a script part nobody listed fails the build')
    (home / 'parts/stray.js').unlink()
    (home / 'parts/side.html').write_bytes(b'<p>side</p>\n')
    t.ok(refused(), 'an html part the template never places fails the build')
