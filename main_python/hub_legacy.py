"""Old browsers get the lowered copy of a page's script (user 2026-11-20).

An Android TV with Chrome 75 could not start Studio or Voice: their scripts use
`?.` and `??` (Chrome 80+). tools/build_web.py writes a lowered sibling
(`app.legacy.js`, `index.legacy.html`) next to those files; the hub hands it
to a browser whose User-Agent says Chrome older than OLDEST_MODERN, and the
normal file to everyone else. The decision is on the server, the TV's browser
does no work; no sibling file means the normal file.
"""
import re

OLDEST_MODERN = 80          # Chrome 80 parses ?. and ??


def is_old(user_agent):
    m = re.search(r"Chrome/(\d+)", user_agent or "")
    return bool(m) and int(m.group(1)) < OLDEST_MODERN


def pick(path, user_agent):
    """`path` (a pathlib.Path), or its .legacy sibling for an old browser."""
    if is_old(user_agent):
        sibling = path.with_name(path.stem + ".legacy" + path.suffix)
        if sibling.is_file():
            return sibling
    return path
