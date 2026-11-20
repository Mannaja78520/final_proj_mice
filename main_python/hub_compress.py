"""Smaller pages for slow devices: gzip + "unchanged" answers, server-side.

Asked 2026-11-20: customers may open the hub on a low-spec Android TV, so the
work belongs on the server, not the browser. Measured that day: every page,
script and style left the hub as plain text with `Cache-Control: no-store`
(Studio's app.js 653 KB, the Home page 181 KB, Voice 186 KB; gzip is about
a third of that), and a page was re-sent whole on every open.

Two things, both done once in Handler.send_bytes:
  * gzip, when the browser says it accepts it and the body is text >= 1 KB.
    The squeezed copy is kept by content hash, so a 650 KB script is
    compressed once, not on every request.
  * for pages, scripts and styles an ETag and `no-cache`: the browser keeps a
    copy but must ask first, and gets a 304 with no body when nothing
    changed. Never a stale page after a hub update (the reason `no-store` was
    chosen), because "ask first" is every time. JSON from /api stays no-store.
"""
import gzip
import hashlib
from collections import OrderedDict

# Text a browser reads. Images and STL are already dense or not text.
SQUEEZE = ("text/", "application/json", "application/javascript", "image/svg+xml")
# What may be kept and re-validated (pages, scripts, styles, pictures: Help
# is 780 KB of screenshots); everything else is live data.
STATIC = ("text/html", "text/css", "text/javascript", "image/png", "image/jpeg", "image/gif")
MIN_BYTES = 1024
KEEP = 24            # squeezed copies kept; ~50 pages and scripts exist


class Squeezer:
    def __init__(self, keep=KEEP):
        self._keep = keep
        self._copies = OrderedDict()      # digest -> gzip bytes

    @staticmethod
    def wants_gzip(accept_encoding):
        return "gzip" in (accept_encoding or "").lower()

    @staticmethod
    def can_squeeze(ctype, size):
        return size >= MIN_BYTES and ctype.startswith(SQUEEZE)

    @staticmethod
    def is_static(ctype):
        return ctype.startswith(STATIC)

    @staticmethod
    def digest(data):
        return hashlib.blake2b(data, digest_size=12).hexdigest()

    def squeeze(self, data, digest):
        got = self._copies.get(digest)
        if got is None:
            got = gzip.compress(data, 6, mtime=0)
            self._copies[digest] = got
            while len(self._copies) > self._keep:
                self._copies.popitem(last=False)
        else:
            self._copies.move_to_end(digest)
        return got


SQUEEZER = Squeezer()
