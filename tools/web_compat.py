"""Old-browser support for the built pages (user 2026-11-20).

An Android TV with Chrome 75 (VirtualBox test) could not start Studio or Home:
the pages used `?.`, `??` and friends that only Chrome 80+ parses. The sources
stay modern and easy to read; the BUILT script is lowered here, and only when
it needs it (a script that already parses as ES2019, which Chrome 75 runs, is
left byte for byte). Target = `oldest_browser` in tools/web_build.json, data.

Needs node and `npm install` in tools/ (esbuild + acorn, pinned in
tools/package.json, build-time only, never shipped). Without them the script
is left as it is and a warning is printed; check_old_browser fails on a
built file that still has new syntax, so it cannot slip through unseen.
"""
import shutil
import subprocess
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
# Chrome 75 = ES2019 plus dynamic import(). acorn parses ES2020 (which has
# import()), then any `?.` / `??` found in the tree means "needs lowering".
_PARSE = ("const a=require(%r);let s='';process.stdin.on('data',d=>s+=d).on('end',()=>{"
          "let t;try{t=a.parse(s,{ecmaVersion:2020,sourceType:'script',allowHashBang:true});}"
          "catch(e){process.exit(1)}"
          "const bad=n=>{if(!n||typeof n!=='object')return false;"
          "if(n.type==='ChainExpression'||(n.type==='LogicalExpression'&&n.operator==='??'))return true;"
          "for(const k in n){const v=n[k];if(Array.isArray(v)){for(const c of v)if(bad(c))return true}"
          "else if(v&&typeof v.type==='string'&&bad(v))return true}return false};"
          "process.exit(bad(t)?1:0)});" % str(TOOLS / "node_modules" / "acorn"))
_warned = False


def _ready(node):
    if (TOOLS / "node_modules" / "esbuild").exists():
        return True
    npm = shutil.which("npm")
    if npm:
        subprocess.run([npm, "install", "--no-audit", "--no-fund", "--prefix", str(TOOLS)],
                       capture_output=True, text=True, timeout=300)
    return (TOOLS / "node_modules" / "esbuild").exists()


def parses_for_old(source, node):
    r = subprocess.run([node, "-e", _PARSE], input=source, text=True, encoding="utf-8", capture_output=True)
    return r.returncode == 0


def lower(source, target="chrome70"):
    """The script, lowered when it needs it; unchanged when it does not or when no toolchain."""
    global _warned
    node = shutil.which("node")
    if not node or not _ready(node):
        if not _warned:
            print("WARNING: node/esbuild missing - scripts are not lowered for old TV browsers "
                  "(run npm install in tools/)", file=sys.stderr, flush=True)
            _warned = True
        return source
    if parses_for_old(source, node):
        return source
    r = subprocess.run([node, str(TOOLS / "downlevel.js"), target], input=source, text=True,
                       encoding="utf-8", capture_output=True)
    if r.returncode:
        raise ValueError("lowering for old browsers failed: " + r.stderr[:300])
    return r.stdout
