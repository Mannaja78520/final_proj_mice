"""Two uploads at once must not rewrite each other's destination.

The upload handler kept its destination in MEMBERS (`uploadDest_` /
`uploadTmp_`). A second upload's first chunk overwrote them while the first
upload was still streaming, so the first request's final chunk then renamed or
deleted the SECOND request's target — one designer's file arriving under
another's name. Now the destination is worked out from each request's own
query (`dir`) and its own `filename` argument on every chunk, so concurrent
uploads carry their paths with them.
"""
import qc as F

AREA = "firmware"
TITLE = "each upload carries its own destination, no shared members"


def run(t):
    h = (F.FIRMWARE / "src" / "core" / "WebPortal.h").read_text(encoding="utf-8")
    for gone in ("uploadDest_", "uploadTmp_"):
        t.ok(gone not in h, "no %s member in WebPortal.h" % gone)

    src = (F.FIRMWARE / "src" / "core" / "WebPortal.cpp").read_text(encoding="utf-8")
    t.ok("uploadDest_" not in src and "uploadTmp_" not in src,
         "and none anywhere in WebPortal.cpp")

    up = src[src.find('server_.on("/api/upload"'):]
    up = up[:up.find("\n    server_.on(")]          # until the next route
    # the destination comes from THIS request's own data, every chunk
    t.contains(up, 'req->hasParam("dir")',
               "the dir is read off the request itself")
    t.contains(up, "const String dest = dir + \"/\" + filename;",
               "the destination is a per-request local")
    t.contains(up, "SD.rename(tmp.c_str(), dest.c_str())",
               "the final rename aims at the same local it opened")
