#!/usr/bin/env python3
"""Render a markdown file to a page that keeps itself current.

    python tools/livedoc.py NEXT_SESSION.md
    python tools/livedoc.py docs/DIARY.md --out docs/DIARY.html
    python tools/livedoc.py --refresh          re-render every page made before

The generalisation of what docs/PLAN.html does, asked for 2026-08-19: *make it
like this for another plan too*.

TWO RULES THAT KEEP IT HONEST
-----------------------------
1. **The markdown is the only source.** The HTML is generated and must never be
   edited - otherwise one document exists twice and the copies drift. Every
   page says so, in the page.
2. **The page updates while it is open.** It is opened from `file:///E:/...`,
   and a file:// page may not fetch() a file beside it: the browser gives it a
   null origin and blocks the read. It MAY load a script. So the content is
   published as `<name>.doc.js`, the page pulls it in on a timer, and redraws
   when the stamp moves. Re-running this tool is all it takes.

The markdown subset is deliberately small - headings, lists, task boxes, code,
quotes, rules, bold, inline code and links. Anything else is shown as written
rather than mangled, and `--strict` lists what it did not understand, because a
renderer that quietly drops a line is worse than one that admits it.
"""
import argparse
import html
import json
import re
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVERY_MS = 4000                      # how often the open page re-reads the state


def inline(s: str) -> str:
    """Bold, inline code and links. Escaped first, so nothing can inject."""
    s = html.escape(s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", r'<a href="\2">\1</a>', s)
    return s


def render(md: str):
    """Markdown subset -> (html, done, total). Returns the task-box counts too."""
    out, lines = [], md.splitlines()
    i, in_code, in_list, done, total, odd = 0, False, None, 0, 0, []
    while i < len(lines):
        ln = lines[i]
        if ln.strip().startswith("```"):
            if in_code:
                out.append("</code></pre>")
            else:
                out.append("<pre><code>")
            in_code = not in_code
            i += 1
            continue
        if in_code:
            out.append(html.escape(ln))
            i += 1
            continue
        if in_list and not re.match(r"\s*([-*]|\d+\.)\s", ln):
            out.append("</%s>" % in_list)
            in_list = None
        if not ln.strip():
            i += 1
            continue
        m = re.match(r"(#{1,4})\s+(.*)", ln)
        if m:
            lvl = len(m.group(1))
            out.append("<h%d>%s</h%d>" % (lvl, inline(m.group(2)), lvl))
            i += 1
            continue
        if re.match(r"\s*(---+|\*\*\*+)\s*$", ln):
            out.append("<hr>")
            i += 1
            continue
        if ln.lstrip().startswith(">"):
            out.append("<blockquote>%s</blockquote>"
                       % inline(ln.lstrip()[1:].strip()))
            i += 1
            continue
        m = re.match(r"\s*([-*]|\d+\.)\s+(.*)", ln)
        if m:
            want = "ol" if m.group(1)[0].isdigit() else "ul"
            if in_list != want:
                if in_list:
                    out.append("</%s>" % in_list)
                out.append("<%s>" % want)
                in_list = want
            body = m.group(2)
            box = re.match(r"\[([ xX])\]\s+(.*)", body)
            if box:
                total += 1
                hit = box.group(1).lower() == "x"
                done += hit
                out.append('<li class="task %s">%s%s</li>'
                           % ("on" if hit else "off",
                              "\u2713 " if hit else "\u25a2 ", inline(box.group(2))))
            else:
                out.append("<li>%s</li>" % inline(body))
            i += 1
            continue
        if ln.startswith("|"):
            # Tables earn real markup: the first document tried had one on line
            # 7, and a row-per-code-block loses the columns, which are the only
            # reason anyone writes a table.
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append(lines[i])
                i += 1
            cells = [[c.strip() for c in r.strip().strip("|").split("|")]
                     for r in rows]
            sep = len(cells) > 1 and all(set(c) <= set("-: ") and "-" in c
                                         for c in cells[1])
            out.append("<table>")
            for n, row in enumerate(cells):
                if sep and n == 1:
                    continue                      # the |---| alignment line
                tag = "th" if (sep and n == 0) else "td"
                out.append("<tr>" + "".join("<%s>%s</%s>" % (tag, inline(c), tag)
                                            for c in row) + "</tr>")
            out.append("</table>")
            continue
        out.append("<p>%s</p>" % inline(ln))
        i += 1
    if in_code:
        out.append("</code></pre>")
        odd.append("a code fence was never closed")
    if in_list:
        out.append("</%s>" % in_list)
    return "\n".join(out), done, total, odd


SHELL = """<title>%(title)s</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
body{background:#12141a;color:#e8eaf0;font-family:system-ui,"Segoe UI",sans-serif;
     font-size:15px;line-height:1.6;margin:0;padding:24px}
main{max-width:820px;margin:0 auto}
h1{font-size:22px} h2{font-size:16px;color:#7cc4ff;text-transform:uppercase;
   letter-spacing:.06em;margin-top:24px}
h3,h4{font-size:15px;margin-top:16px}
p{margin:8px 0} ul,ol{margin:8px 0 8px 22px}
code{background:#1b1e27;border-radius:6px;padding:1px 5px;
     font-family:ui-monospace,Consolas,monospace;font-size:13px}
pre{background:#1b1e27;border-radius:10px;padding:12px;overflow-x:auto}
pre code{background:none;padding:0}
blockquote{border-left:3px solid #3a3f4d;margin:8px 0;padding-left:12px;color:#aab}
hr{border:0;border-top:1px solid #2a2e3a;margin:20px 0}
a{color:#7cc4ff}
table{border-collapse:collapse;margin:10px 0;display:block;overflow-x:auto}
th,td{border:1px solid #2a2e3a;padding:6px 10px;text-align:left;vertical-align:top}
th{color:#7cc4ff;font-size:13px}
li.task{list-style:none;margin-left:-18px}
li.task.on{color:#8ee6a0} li.task.off{color:#c9cddb}
.head{display:flex;gap:12px;align-items:baseline;flex-wrap:wrap;
      border-bottom:1px solid #2a2e3a;padding-bottom:10px;margin-bottom:14px}
.bar{height:8px;background:#1b1e27;border-radius:99px;overflow:hidden;
     flex:1 1 160px;min-width:120px}
.bar i{display:block;height:100%%;background:#8ee6a0;width:0}
.mini{color:#8d93a6;font-size:12px}
.warn{color:#e0b34d}
</style>
<main>
  <div class="head">
    <strong>%(title)s</strong>
    <span class="bar" id="bar" hidden><i id="barfill"></i></span>
    <span class="mini" id="count"></span>
    <span class="mini" id="stamp">…</span>
  </div>
  <div class="mini warn">Generated from <code>%(src)s</code> by
    <code>tools/livedoc.py</code> — edit the markdown, never this page.</div>
  <div id="doc">loading…</div>
</main>
<script src="%(state)s"></script>
<script>
// The page redraws itself when the stamp moves. A file:// page cannot fetch a
// file beside it, but it CAN load a script - so the state is a script, and
// re-loading it is how this stays current with nothing to press.
var seen = null;
function paint(){
  var s = window.LIVEDOC;
  if (!s || s.stamp === seen) return;
  seen = s.stamp;
  document.getElementById('doc').innerHTML = s.html;
  document.getElementById('stamp').textContent = 'updated ' + s.stamp;
  var bar = document.getElementById('bar');
  if (s.total > 0){
    bar.hidden = false;
    document.getElementById('barfill').style.width =
      Math.round(100 * s.done / s.total) + '%%';
    document.getElementById('count').textContent = s.done + ' of ' + s.total + ' done';
  } else { bar.hidden = true; document.getElementById('count').textContent = ''; }
}
paint();
setInterval(function(){
  var el = document.createElement('script');
  el.src = '%(state)s?t=' + Date.now();
  el.onload = function(){ paint(); el.remove(); };
  document.head.appendChild(el);
}, %(every)d);
</script>
"""


def build(src: Path, out: Path = None):
    md = src.read_text(encoding="utf-8", errors="replace")
    body, done, total, odd = render(md)
    out = out or src.with_suffix(".html")
    state = out.name.replace(".html", "") + ".doc.js"
    (out.parent / state).write_bytes(
        ("window.LIVEDOC=" + json.dumps({
            "stamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "html": body, "done": done, "total": total}) + ";\n").encode("utf-8"))
    out.write_bytes((SHELL % {
        "title": html.escape(src.stem.replace("_", " ").title()),
        "src": html.escape(str(src.relative_to(ROOT)) if src.is_relative_to(ROOT)
                           else src.name),
        "state": state, "every": EVERY_MS}).encode("utf-8"))
    return out, done, total, odd


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file", nargs="?", help="the markdown file")
    ap.add_argument("--out", help="where to write the page")
    ap.add_argument("--refresh", action="store_true",
                    help="re-render every page this tool has made before")
    ap.add_argument("--strict", action="store_true",
                    help="list what the renderer did not understand")
    a = ap.parse_args(argv)

    targets = []
    if a.refresh:
        # A page is one of ours when its state file sits beside it.
        for js in sorted(ROOT.rglob("*.doc.js")):
            md = js.with_name(js.name[:-7] + ".md")
            if md.is_file():
                targets.append((md, js.with_name(js.name[:-7] + ".html")))
        if not targets:
            print("nothing to refresh - render one first")
            return 1
    elif a.file:
        src = Path(a.file)
        if not src.is_absolute():
            src = ROOT / a.file
        if not src.is_file():
            raise SystemExit("no such file: %s" % a.file)
        targets.append((src, Path(a.out) if a.out else None))
    else:
        ap.error("give a markdown file, or --refresh")

    for src, out in targets:
        page, done, total, odd = build(src, out)
        note = ("  %d/%d done" % (done, total)) if total else ""
        print("%s -> %s%s" % (src.name, page.name, note))
        if odd and a.strict:
            for o in odd:
                print("   not understood: " + o)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
