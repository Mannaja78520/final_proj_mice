"""Adding a theme is one block in one file, and no theme is unreadable.

Asked for on 2026-08-19: a file to change only the theme or the colours, so a
new one can be added later without reading anything else. That promise is only
worth something if it is checked, because it breaks silently - someone adds a
picker entry by hand, and from then on every new theme needs two edits and the
second one gets forgotten.

So this check ADDS A THEME. It writes a block into shared/web/themes.css that
nothing else in the project has ever heard of, drives the real hub page in a
browser, and expects it in the picker with its own name. If the list is being
repeated anywhere, the new theme does not appear and this fails.

The other half is that colour must not cost readability, which is exactly what
happens when a palette is chosen to look cheerful:

  * body text at least 7:1 on its background, and on cards;
  * muted text at least 4.5:1 - it is a demotion, not a disappearance;
  * the accent at least 4.5:1, because links are text;
  * ok / warn / err far enough APART to be told from each other and from the
    accent. Measured as a colour distance (CIE76), not as a contrast ratio:
    two colours can have identical brightness and be blue and red, and the
    first version of this asked the wrong question and called the shipped
    palette broken.
"""
import itertools
import math
import re

import browser
import fake_serial
import qc as F

AREA = "design"
TITLE = "themes are one block each, and all of them stay readable"
SLOW = True

# The floors. Written here rather than in the stylesheet so a theme cannot
# quietly lower the bar it is measured against.
MIN_TEXT = 7.0          # body text, on bg and on card
MIN_MUTED = 4.5         # the demoted caption
MIN_ACCENT = 4.5        # links are text
MIN_STATE = 3.0         # ok / warn / err against their background
MIN_APART = 25.0        # CIE76 distance between state colours and the accent


def _rgb(h):
    h = h.strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]


def _lin(c):
    return [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]


def _lum(h):
    r, g, b = _lin(_rgb(h))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    la, lb = _lum(a), _lum(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def _lab(h):
    r, g, b = _lin(_rgb(h))
    x = (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047
    y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    z = (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883

    def f(v):
        return v ** (1.0 / 3) if v > 0.008856 else (7.787 * v + 16.0 / 116)

    fx, fy, fz = f(x), f(y), f(z)
    return (116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz))


def apart(a, b):
    """CIE76 distance - how different two colours LOOK, which is the question."""
    return math.sqrt(sum((p - q) ** 2 for p, q in zip(_lab(a), _lab(b))))


def themes_in(css):
    """Every theme block, as {name: {token: colour}}."""
    out = {}
    for m in re.finditer(r':root(?:\[data-theme="([\w-]+)"\])?\s*\{(.*?)\}', css, re.S):
        name = m.group(1) or "midnight"
        body = m.group(2)
        vals = dict(re.findall(r"(--[\w-]+)\s*:\s*(#[0-9a-fA-F]{3,8})", body))
        if "--bg" in vals and "--txt" in vals:
            out.setdefault(name, {}).update(vals)
    return out


DRIVER = """
<style>html,body{margin:0}#f{width:1100px;height:900px;border:0}</style>
<iframe id="f" src="/"></iframe>
<script>
function done(s){ qcMark("TH " + s); qcMark("done"); }
setTimeout(async function(){
  try{
    var w = document.getElementById('f').contentWindow;
    var d = document.getElementById('f').contentDocument;
    if (!w.miceTheme) return done("missing=miceTheme");

    var found = w.miceTheme.list().map(function(t){ return t.id; }).join(",");
    var box = d.getElementById('themePick');
    var sel = box ? box.querySelector('select') : null;
    var opts = sel ? [].slice.call(sel.options).map(function(o){ return o.value; }).join(",")
                   : "none";
    var names = sel ? [].slice.call(sel.options).map(function(o){
                        return o.textContent; }).join(",").replace(/[^A-Za-z,]/g, "")
                    : "none";

    // Actually wear one, and see whether the paint changed.
    var before = getComputedStyle(d.body).backgroundColor;
    w.miceTheme.set('daylight');
    await new Promise(function(r){ setTimeout(r, 300); });
    var after = getComputedStyle(d.body).backgroundColor;
    var attr = d.documentElement.getAttribute('data-theme') || 'none';
    var saved = w.localStorage.getItem('mice_theme') || 'none';
    w.miceTheme.set('');

    done(["found=" + found, "opts=" + opts, "names=" + names,
          "changed=" + (before !== after ? "yes" : "no"),
          "attr=" + attr, "saved=" + saved].join(" "));
  } catch (e) { done("ERR=" + String(e).replace(/[^A-Za-z0-9=]+/g, "_").slice(0,50)); }
}, 5000);
</script>
"""


def run(t):
    css_file = F.CODE / "shared" / "web" / "themes.css"
    if not t.ok(css_file.is_file(), "shared/web/themes.css is where colour lives",
                "one file to change a theme, asked for 2026-08-19"):
        return
    css = css_file.read_text(encoding="utf-8")
    found = themes_in(css)

    t.ok(len(found) >= 3, "there are themes to choose between",
         "found %r" % sorted(found))
    t.ok("midnight" in found, "the dark one is still there",
         "dark is the default because a bright screen spills light into the "
         "show area")

    # ---- every theme stays readable --------------------------------
    for name, v in sorted(found.items()):
        def near(tok, floor, what, against="--bg"):
            if tok not in v or against not in v:
                t.ok(False, "%s: %s is defined" % (name, tok),
                     "a theme that omits one inherits it and looks almost right")
                return
            r = contrast(v[tok], v[against])
            t.ok(r >= floor, "%s: %s reads on %s (%.1f:1)" % (name, what, against, r),
                 "%.2f:1 against a floor of %.1f - %s on %s"
                 % (r, floor, v[tok], v[against]))

        near("--txt", MIN_TEXT, "body text")
        near("--txt", MIN_TEXT, "body text", "--card")
        near("--mut", MIN_MUTED, "the quiet caption")
        near("--acc", MIN_ACCENT, "the accent")
        for tok in ("--ok", "--warn", "--err"):
            near(tok, MIN_STATE, tok.strip("-"))

        # ...and the state colours cannot be confused with one another.
        keys = [k for k in ("--acc", "--ok", "--warn", "--err") if k in v]
        worst, pair = 999.0, ("", "")
        for a, b in itertools.combinations(keys, 2):
            d = apart(v[a], v[b])
            if d < worst:
                worst, pair = d, (a, b)
        t.ok(worst >= MIN_APART,
             "%s: state colours are told apart (%s vs %s)" % (name, pair[0], pair[1]),
             "colour distance %.1f, floor %.1f - a warning that looks like the "
             "accent is decoration, not a warning" % (worst, MIN_APART))

        # Decoration must not wear a state colour. --ty-lift was byte for byte
        # --ok in every theme, so a lift board's row edge was the colour that
        # means "fine" - and the same green then meant two things, which is the
        # one thing colour is bad at. The model panel found this; it is here so
        # it cannot come back.
        states = {k: v[k] for k in ("--ok", "--warn", "--err") if k in v}
        for tok in ("--ty-nong", "--ty-lift", "--ty-cam", "--ty-other"):
            if tok not in v:
                continue
            same = [k for k, val in states.items()
                    if val.lower() == v[tok].lower()]
            t.ok(not same, "%s: %s is not a state colour" % (name, tok),
                 "it is exactly %s, so a board type and a state are painted "
                 "the same" % (", ".join(same) or "-"))

    # ---- no theme name is written into the code ---------------------
    js = (F.CODE / "shared" / "web" / "mice.js").read_text(encoding="utf-8")
    code = re.sub(r"//[^" + chr(10) + "]*", "", js)
    named = [n for n in found if n != "midnight" and n in code]
    t.ok(not named, "the switcher names no theme in its code",
         "%r appear in mice.js, so those themes are special and the others "
         "are not" % named)
    t.ok("midnight" not in code,
         "not even the default one",
         "the default is the first block in the file; naming it means renaming "
         "that block silently preselects nothing")

    # ---- adding one is ONE block -----------------------------------
    if not browser.available():
        t.give_up("headless Edge not found - install Edge or run --quick")
    keep = css
    probe = css + """
:root[data-theme="qcprobe"]{
  --theme-name:"QC Probe";
  --theme-note:"added by the QC suite, and removed again";
  --bg:#0a0a0a; --card:#141414; --sunk:#050505; --line:#333333;
  --txt:#f5f5f5; --mut:#a8a8a8;
  --acc:#7fd1ff; --on-acc:#04121a; --btn:#222222;
  --ok:#5fdca0; --warn:#ffc061; --err:#ff8080;
  --ty-nong:#ffd166; --ty-lift:#5fdca0; --ty-cam:#c0a0ff; --ty-other:#a8a8a8;
  color-scheme:dark;
}
"""
    try:
        css_file.write_text(probe, encoding="utf-8", newline="")
        fake_serial.reset()
        base, _main = F.start_hub()
        browser.raw_page(DRIVER, base, seconds=30)
    finally:
        css_file.write_text(keep, encoding="utf-8", newline="")

    got = {}
    for m in fake_serial.qc_marks:
        if m.startswith("TH "):
            for part in m[3:].split(" "):
                k, _, val = part.partition("=")
                got[k] = val
    if not t.ok(got, "the page reported back",
                "%r" % (fake_serial.qc_marks[-3:],)):
        return

    t.contains(got.get("found", ""), "qcprobe",
               "a theme added to the file is DISCOVERED, not listed anywhere")
    t.contains(got.get("opts", ""), "qcprobe",
               "and it reaches the picker with no other edit")
    t.contains(got.get("names", ""), "QCProbe",
               "under the name the block gives itself")
    t.eq(got.get("changed"), "yes", "choosing a theme repaints the page")
    t.eq(got.get("attr"), "daylight",
         "by setting data-theme on the root, so the page background changes too")
    t.eq(got.get("saved"), "daylight",
         "and the choice is remembered for next time")
