"""Names that came off the network are drawn as TEXT, never as markup.

A24-8, from the standing question of what a hostile board — or a hostile
laptop on the venue WiFi — could write into a page Studio renders. Two
places fed straight-off-the-network strings into innerHTML: the hubs
dropdown drew the other PC's self-reported name, and the export status line
echoed back a file name built from a name typed into a form. Not exploitable
from this PC alone, but Studio runs next to strangers' phones, and one
renamed machine should not be able to script whoever picks it from a list.

The safe pattern already existed in this same file - scanModules, loadPorts,
refreshProjects and refreshSeqs all build their <option>s with textContent -
so holding every picker to the pattern is consistency, not invention.
"""
import qc as F

AREA = "studio"
TITLE = "network-fed names reach Studio's page as text, not as markup"
SLOW = False


def _block(src, start):
    """From `start` to the next blank-line-bounded top-level definition."""
    i = src.find(start)
    if i < 0:
        return ""
    rest = src[i:]
    j = rest.find("\nasync function ", len(start))
    k = rest.find("\nfunction ", len(start))
    ends = [e for e in (j, k) if e > 0]
    return rest[:min(ends)] if ends else rest


def run(t):
    js = (F.STUDIO_WEB / "app.js").read_text(encoding="utf-8")

    # ---- the hubs dropdown: the other PC names itself -----------------
    hubs = _block(js, "async function findHubs()")
    t.ok("createElement" in hubs and "o.textContent = h.ip" in hubs,
         "hub rows are built as elements carrying text")
    dirty = [ln.strip() for ln in hubs.splitlines()
             if ".innerHTML" in ln and any(c in ln for c in "+`")]
    t.ok("hubs.map(" not in hubs and not dirty,
         "and nothing in the picker is assembled as an HTML string",
         "the old .map(h => '<option ...' + h.ip + ...) put the far PC's "
         "self-reported name straight into markup - a renamed laptop on the "
         "venue WiFi could write HTML, and script whoever picked it: %r"
         % (dirty[:2] or ["hubs.map survived"],))

    # ---- the export status echoes a typed name ------------------------
    i = js.find("$(`tlStat`).textContent")
    if i < 0:
        i = js.find('$("tlStat").textContent')
    t.ok(i > 0, "the saved-sequence status line is written as text")
    t.ok("$(`tlStat`).innerHTML" not in js and '$("tlStat").innerHTML' not in js,
         "and never through innerHTML again",
         "the file name it prints is echoed from this very form; through "
         "markup a name containing <img onerror=...> executed in the editor")

    # ---- every other network-fed picker keeps the pattern -------------
    for fn in ("async function scanModules()",
               "async function loadPorts(",
               "async function refreshProjects()"):
        b = _block(js, fn)
        t.ok(bool(b) and "textContent" in b,
             "%s still builds its options as text" % fn.split("(")[0].replace(
                 "async ", ""),
             "this is the pattern the two fixed pickers were made to follow; "
             "losing it here is how the next picker drifts back to strings")
