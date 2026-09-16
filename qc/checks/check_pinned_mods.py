"""The modules you actually use sit at the top, and the row says which is which.

A venue rig has four modules that matter and a shelf of spares that do not, and
the spares are usually the larger number. Scrolling past them to reach the same
four boards, every single time, is the problem. So a module can be pinned, and
pinned modules are drawn first.

Three properties, and each one is a thing that would quietly go wrong:

  * **pinned by board id.** A name is user-settable (`SET NAME`, the module
    site) and an address changes the moment a board moves between a cable and
    the WiFi, or the router hands out a new lease. Pinning by either would drop
    the pin off the board it was pinned to, and look like the feature simply
    forgetting;
  * **pinning costs a REPAINT, never a scan.** A network sweep takes seconds
    and poles every board at the venue. Paying that to reorder a list would
    make the pin feel broken, and would hit the rig for no reason;
  * **the repaint re-applies the filter.** The search hides rows with
    `display:none`, so redrawing the list without re-filtering would silently
    un-hide everything the person had just filtered away.

And one long-standing bug fixed on the way, which is really the same feature by
another route - knowing which board is which at a glance. `mice.css` has styled
`.mod.t-nong`, `.t-lift` and `.t-cam` since the design system landed, and
NOTHING ever added those classes: `modRow` only ever set `mod`. Every board has
been showing the default grey, and the type colour on the row's left edge had
never once worked. Found by grepping for who sets them - only the stylesheet
mentioned them at all.
"""
import re

import qc as F

AREA = "hub"
TITLE = "pinned modules are listed first, and a row shows its type colour"


def _fn(src, name):
    """One function's body, so an assertion cannot pass on a different one."""
    i = src.find("function " + name + "(")
    if i < 0:
        return ""
    j = src.find("\nfunction ", i + 10)
    return src[i:j if j > 0 else len(src)]


def run(t):
    hub = (F.HUB / "web" / "hub.html").read_text(encoding="utf-8")
    css = (F.CODE / "shared" / "web" / "mice.css").read_text(encoding="utf-8")

    # ---- pinned by ID, not by name or address ------------------------
    for fn in ("pinnedIds", "isPinned", "togglePin", "pinnedFirst"):
        t.ok(_fn(hub, fn), "%s exists" % fn)
    toggle = _fn(hub, "togglePin")
    t.contains(toggle, "pinnedMods",
               "the pins are stored under their own key")
    row = _fn(hub, "modRow")
    t.contains(row, "togglePin(m.id)",
               "the pin control pins by the board's id")
    t.ok("togglePin(m.name" not in row and "togglePin(dev" not in row,
         "and never by its name or its address",
         "a name is user-settable and an address changes when the board moves "
         "between a cable and the WiFi - either would drop the pin off the "
         "board it was pinned to, which reads as the feature forgetting")

    # ---- pinned really come first ------------------------------------
    first = _fn(hub, "pinnedFirst")
    t.contains(first, "concat",
               "pinned modules are put ahead of the rest")
    i_yes = first.find("yes.concat(no)")
    t.ok(i_yes > 0, "in that order, not the other way round",
         "concat(yes) on the unpinned list would put the spares first, which "
         "is the current behaviour with extra steps")
    t.contains(_fn(hub, "repaintMods"), "pinnedFirst",
               "and the list is drawn through it")

    # ---- a pin does NOT cost a network sweep -------------------------
    t.contains(row, "repaintMods()",
               "clicking the pin repaints")
    t.ok("scan(true)" not in row.split("pin.onclick")[-1][:400],
         "and does NOT rescan the network",
         "a sweep takes seconds and pokes every board at the venue; paying "
         "that to reorder a list makes the pin feel broken")

    # ---- the repaint keeps the filter applied ------------------------
    rep = _fn(hub, "repaintMods")
    t.contains(rep, "filterMods()",
               "a repaint re-applies the search filter")
    i_draw = rep.find("forEach")
    # the LAST call, not the first: there is now an early-return path that
    # settles the filter before any row exists, and matching that one would
    # assert the opposite of what this is about.
    i_filt = rep.rfind("filterMods()")
    t.ok(0 < i_draw < i_filt,
         "after the rows are drawn, not before",
         "filtering before the rows exist filters nothing, and the person's "
         "search silently un-hides every module they had just filtered away")

    # ---- the toggle says which state it is in, in words --------------
    t.contains(row, "aria-pressed",
               "the pin reports its state to a screen reader")
    t.ok("Pinned — click to unpin" in row or "Pinned" in row,
         "and says in words whether it is pinned",
         "a filled star against an outlined one is not a difference everyone "
         "can see; this page never uses shape or colour alone")

    # ---- the type colour finally reaches the row ---------------------
    # It was styled and never applied: modRow set only `mod`, so every board
    # showed the default grey.
    for ty in ("nong", "lift", "cam"):
        t.contains(css, ".mod.t-%s" % ty, "mice.css styles a %s row" % ty)
    t.contains(row, "'t-'+tyClass",
               "and modRow really adds that class")
    m = re.search(r"tyClass\s*=\s*String\(m\.type\|\|''\)\.replace\(([^)]*)\)", row)
    t.ok(m, "the type is sanitised before it becomes a class name",
         "it comes off the wire from a board, and classList.add throws on a "
         "string containing a space - which would take the whole row down")
    if m:
        t.contains(m.group(1), "a-z0-9",
                   "down to characters that are safe in a class name")

    # ---- LATE still beats TYPE ---------------------------------------
    # Found by a model review 2026-08-20, and it was a regression this change
    # caused. `.mod.late` sets the border-left SHORTHAND (colour included) and
    # the type rules set only the colour, at the same specificity - so the one
    # written later wins, and the type rules are written later. A board that
    # may have dropped off the rig would have shown its cheerful type colour
    # instead of the warning one. Harmless only while nothing added the t-
    # classes; the moment modRow started adding them it became real.
    i_late = css.find(".mod.late{")
    i_type = css.find(".mod.t-nong")
    t.ok(0 < i_late < i_type,
         "the type rules are written after .mod.late, so they must exclude it")
    for ty in ("nong", "lift", "cam"):
        t.contains(css, ".mod.t-%s:not(.late){" % ty,
                   "a late %s row keeps the warning colour" % ty)
    t.contains(css, ".mod.late{opacity",
               "and late still dims the row as well as colouring it")

    # ---- the empty list does not leave a contradiction on screen -----
    t.contains(rep, "filterMods(); return;",
               "an empty list still settles the filter before returning")
    t.ok(rep.find("filterMods(); return;") < rep.find("el.innerHTML=''"),
         "which happens on the early path, not only at the end",
         "otherwise #modFindNone keeps saying '3 of 5 hidden by the filter' "
         "beside a message saying none were found at all")

    # ---- a pin survives the next scan failing ------------------------
    t.contains(rep, "modsHtml = el.innerHTML",
               "a repaint refreshes the last-good markup")
    t.ok("modsAt =" not in rep,
         "but does NOT touch modsAt",
         "modsAt records when the DATA was fetched; a repaint learns nothing "
         "new about the rig, and moving it would let stale rows claim to be "
         "fresh - the one thing the stale banner exists to prevent")

    # ---- the pin has somewhere to be, and can be hit on a phone ------
    t.contains(css, ".pin{", "the pin is styled")
    t.contains(css, ".pin.on{", "and looks different when it is on")
    coarse = css[css.find("@media (pointer:coarse){.pin"):][:120]
    t.ok("44px" in coarse,
         "with a full-size touch target on a phone",
         "it sits beside the module name, which is exactly where a thumb "
         "lands by accident")
