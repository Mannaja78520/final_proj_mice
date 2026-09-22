"""Camera boards: which board, and its pinout drawn as SVG.

Moved out of main.py on 2026-09-23 (A26-93). Nothing here changed in
behaviour. main.py imports these names back and calls bind() with itself;
names that live there, and names QC swaps on main, are read late as _hub.
"""
import json

_hub = None           # the main module, set by bind()


def bind(hub):
    global _hub
    _hub = hub


def esc(text):
    """Text that is safe inside SVG/XML. The labels come from a data file, and
    a data file is edited by people - an unescaped & or < there would produce a
    diagram the browser refuses to render at all."""
    return (str(text).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def cam_boards():
    """Every camera board, from the file the FIRMWARE is built from.

    Not a copy. `firmware/config/cam_boards.json` becomes CamBoards.h at build
    time and is read here at run time, so a diagram cannot disagree with the
    wiring the board is actually using - which is the whole risk with a picture.
    Asked for on 2026-08-19: *make it compatable with many board sometime when i
    buy the new one maybe i don't know which hardware i got*.
    """
    try:
        import registry
        return json.loads(registry.strip_jsonc(
            _hub.CAM_BOARDS_JSON.read_text(encoding="utf-8"))).get("boards", {})
    except Exception as e:                                   # noqa: BLE001
        print("[hub] camera boards unavailable:", e)
        return {}


# The order signals are drawn in: the bus first, then the eight data lines,
# then the timing. It matches how the board is actually read rather than the
# order the struct happens to store them in.
CAM_SIGNALS = [
    ("pwdn", "power down"), ("reset", "reset"), ("xclk", "clock out"),
    ("siod", "SCCB data"), ("sioc", "SCCB clock"),
    ("y9", "data 7"), ("y8", "data 6"), ("y7", "data 5"), ("y6", "data 4"),
    ("y5", "data 3"), ("y4", "data 2"), ("y3", "data 1"), ("y2", "data 0"),
    ("vsync", "frame sync"), ("href", "line valid"), ("pclk", "pixel clock"),
]


def cam_pinout_svg(name):
    """A pin diagram for ONE camera board, drawn from its entry.

    Drawn rather than shipped, for two reasons that are not about elegance:
    a picture has to be found for every board someone might buy, and a picture
    can be wrong - this cannot, because it is rendered from the same numbers the
    firmware compiles. It is also about 3 KB rather than 133 KB, which matters
    because the WROOM reference is too big to come off board flash at all.

    Colours come from the stylesheet, not from literals, so it follows whichever
    theme the page is using - including the light one, where a diagram drawn in
    pale grey on white would be unreadable.
    """
    b = cam_boards().get(name)
    if not b:
        return None
    pins = b.get("pins", {})
    rows, y = [], 78
    for key, label in CAM_SIGNALS:
        gpio = pins.get(key)
        if gpio is None:
            continue
        # A signal the board does not wire is SHOWN, greyed, saying "not wired".
        # Leaving it out would make two boards look identical when the
        # difference is exactly the missing pin - an ESP-EYE has no power-down
        # line, and a reader has to be able to see that.
        wired = gpio >= 0
        rows.append(
            '<text x="14" y="%d" class="sig">%s</text>'
            '<text x="150" y="%d" class="%s">%s</text>'
            '<text x="205" y="%d" class="lbl">%s</text>'
            % (y, key.upper(), y, "gpio" if wired else "off",
               ("GPIO %d" % gpio) if wired else "not wired", y, label))
        y += 21

    extra = b.get("extra") or {}
    if extra:
        y += 8
        rows.append('<text x="14" y="%d" class="head">also on this board</text>' % y)
        y += 20
        for key, gpio in sorted(extra.items()):
            rows.append('<text x="14" y="%d" class="sig">%s</text>'
                        '<text x="150" y="%d" class="gpio">GPIO %d</text>'
                        % (y, key.upper(), y, gpio))
            y += 21

    height = y + 16
    return ("""<svg xmlns="http://www.w3.org/2000/svg" width="380" height="%d"
     viewBox="0 0 380 %d" role="img" aria-label="%s pin map">
  <style>
    /* The page's own tokens: this is embedded in a page that has a theme, and
       a diagram that ignores it is a foreign object on the screen. The
       fallbacks are for the file opened on its own, with no page around it. */
    .bg   { fill: var(--sunk, #0d1117); stroke: var(--line, #2a3442); }
    text  { font-family: ui-monospace, Consolas, monospace; font-size: 12px; }
    .head { fill: var(--acc, #4da3ff); font-weight: 600; font-size: 13px; }
    .sub  { fill: var(--mut, #8b98a8); font-size: 11px; }
    .sig  { fill: var(--txt, #e6edf3); }
    .gpio { fill: var(--ok, #3ecf8e); }
    .off  { fill: var(--mut, #8b98a8); font-style: italic; }
    .lbl  { fill: var(--mut, #8b98a8); }
  </style>
  <rect class="bg" x="1" y="1" width="378" height="%d" rx="10" stroke-width="1"/>
  <text x="14" y="28" class="head">%s</text>
  <text x="14" y="46" class="sub">%s</text>
  <text x="14" y="62" class="sub">drawn from firmware/config/cam_boards.json</text>
  %s
</svg>
""" % (height, height, esc(b.get("label", name)), height - 2,
       esc(b.get("label", name)), esc(b.get("note", "")), chr(10) + "  ".join(rows)))
