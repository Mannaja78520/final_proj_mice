"""Build web assets from checked, ordered sources without modifying templates."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys


def _read(path):
    return path.read_text(encoding='utf-8').replace('\r\n', '\n')


def _inside(root, name):
    path = (root / name).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError('Build path leaves its tree: ' + name)
    return path


def build(tree):
    tree = Path(tree).resolve()
    manifest = json.loads(_read(tree / 'tools/web_build.json'))
    outputs = {}
    scripts = []
    for spec in manifest['inline_apps']:
        app = _inside(tree, spec)
        template = _read(app / 'index.template.html')
        for filename, tag, replacement in (
            ('style.css', '<link rel="stylesheet" href="style.css">', '<style>\n%s\n</style>'),
            ('app.js', '<script src="app.js"></script>', '<script>\n%s\n</script>'),
        ):
            source = _read(app / filename).strip()
            if template.count(tag) != 1:
                raise ValueError(f'{app}/index.template.html: expected exactly one {tag}')
            template = template.replace(tag, replacement % source)
            if filename.endswith('.js'):
                scripts.append((str(app / filename), source))
        outputs[app / 'index.html'] = template
    studio = manifest['studio']
    app = _inside(tree, studio['path'])
    parts = studio['parts']
    actual = {p.name for p in (app / 'app_parts').glob('*.js')}
    if len(parts) != len(set(parts)) or set(parts) != actual:
        raise ValueError('Studio part manifest mismatch; missing=' + str(sorted(set(parts) - actual))
                         + ', unlisted=' + str(sorted(actual - set(parts))))
    source = '\n'.join(_read(_inside(app / 'app_parts', name)).rstrip() for name in parts) + '\n'
    outputs[app / 'app.js'] = source
    scripts.append((str(app / 'app.js'), source))
    node = shutil.which('node')
    if node:
        for name, source in scripts:
            check = subprocess.run([node, '--check'], input=source, text=True,
                                   encoding='utf-8', capture_output=True)
            if check.returncode:
                raise ValueError(name + ': JavaScript syntax check failed\n' + check.stderr)
    # Validate everything before writing any output. Identical builds keep mtimes.
    changed = []
    for path, source in outputs.items():
        data = source.encode('utf-8')
        if not path.exists() or path.read_bytes() != data:
            path.write_bytes(data)
            changed.append(path.relative_to(tree).as_posix())
    return changed


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('tree', nargs='?', type=Path, default=Path(__file__).resolve().parent.parent)
    args = parser.parse_args(argv)
    try:
        changed = build(args.tree)
    except (OSError, ValueError, KeyError) as exc:
        print('WEB BUILD FAILED: ' + str(exc), file=sys.stderr)
        return 1
    print('Web build ready: %d output(s) updated' % len(changed), flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
