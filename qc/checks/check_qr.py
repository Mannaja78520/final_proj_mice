"""The hub can draw a QR of its own address, and the QR is a real one.

A wrong QR looks exactly like a right one, so none of this is eyeballed.

Three independent things are asserted, and the point is that they are
independent — a single mistake cannot satisfy all three:

  * the picture is READ BACK. The mask is recovered from the format area, the
    same zig-zag is walked, the parity is stripped, and the URL has to come out
    the other end. This catches encoding, placement and masking together.
  * the parity is checked by SYNDROMES. A valid Reed-Solomon codeword answers
    zero for every syndrome, and computing them is different arithmetic from
    the generator polynomial that produced the parity — so agreement is not one
    bug agreeing with itself.
  * the fixed patterns are checked against the standard's own description:
    three finders, alternating timing, the dark module, a format string that
    is one of the eight legal ones, and the zig-zag covering every free cell
    exactly once.

What this cannot prove is that a phone in a dark room scans it. Nothing on a
PC can. That is a bench test, like the rest of the [hw] work.
"""
import sys
from pathlib import Path

import qc as F

AREA = "hub"
TITLE = "the hub draws a QR of its own address"

sys.path.insert(0, str(F.HUB))
import qr  # noqa: E402  (the module under test lives with the hub)


def _read_format(m):
    """Which mask the picture says it used, read from the format area."""
    bits = "".join(str(m[8][i]) for i in range(6))
    bits += str(m[8][7]) + str(m[8][8]) + str(m[7][8])
    bits += "".join(str(m[14 - i][8]) for i in range(9, 15))
    return qr.FORMAT_L.index(bits) if bits in qr.FORMAT_L else -1


def _decode(m, version):
    """The text back out of the picture, the long way round."""
    mask = _read_format(m)
    if mask < 0:
        return None, -1
    rule = qr.MASKS[mask]
    free = qr.free_cells(version)
    order = qr.zigzag(len(m), free)
    bits = "".join(str(m[r][c] ^ (1 if rule(r, c) else 0)) for r, c in order)
    words = [int(bits[i:i + 8], 2) for i in range(0, len(bits) - 7, 8)]

    # Un-interleave: the data codewords come first, one per block in turn.
    _side, total, ec, blocks = qr._VERSIONS[version]      # noqa: SLF001
    per, extra = total // blocks, total % blocks
    sizes = [per + (1 if b >= blocks - extra else 0) for b in range(blocks)]
    chunks = [[] for _ in range(blocks)]
    at = 0
    for i in range(max(sizes)):
        for b in range(blocks):
            if i < sizes[b]:
                chunks[b].append(words[at])
                at += 1
    data = [w for c in chunks for w in c]

    raw = "".join(format(w, "08b") for w in data)
    if raw[:4] != "0100":                                  # byte mode
        return None, mask
    n = int(raw[4:12], 2)
    body = raw[12:12 + n * 8]
    out = bytes(int(body[i:i + 8], 2) for i in range(0, len(body), 8))
    return out.decode("utf-8", "replace"), mask


def _syndromes_zero(text, version):
    """Every block of the codeword answers zero. If not, the parity is wrong."""
    _side, total, ec, blocks = qr._VERSIONS[version]       # noqa: SLF001
    words = qr.codewords(text, version)
    per, extra = total // blocks, total % blocks
    sizes = [per + (1 if b >= blocks - extra else 0) for b in range(blocks)]
    # rebuild each block: its data (interleaved) then its parity (interleaved)
    data = [[] for _ in range(blocks)]
    at = 0
    for i in range(max(sizes)):
        for b in range(blocks):
            if i < sizes[b]:
                data[b].append(words[at])
                at += 1
    par = [[] for _ in range(blocks)]
    for _i in range(ec):
        for b in range(blocks):
            par[b].append(words[at])
            at += 1
    bad = []
    for b in range(blocks):
        block = data[b] + par[b]
        for s in range(ec):
            acc = 0
            for byte in block:                    # Horner, in GF(256)
                acc = qr.mul(acc, qr.exp(s)) ^ byte
            if acc:
                bad.append((b, s, acc))
    return bad



def _bch_format(level_bits, mask):
    """The format string the standard says, computed rather than remembered.

    Five data bits (error level, then mask), ten BCH parity bits over
    10100110111, the whole thing XORed with 101010000010010.
    """
    v = (level_bits << 3) | mask
    rem = v << 10
    for i in range(4, -1, -1):
        if rem & (1 << (i + 10)):
            rem ^= 0b10100110111 << i
    return format(((v << 10) | rem) ^ 0b101010000010010, "015b")


def run(t):
    url = "http://192.168.1.20:9203/"

    # ---- 1. it comes back out ---------------------------------------
    v = qr.fit(url)
    m = qr.matrix(url)
    t.eq(len(m), qr._VERSIONS[v][0], "the picture is the size its version says")  # noqa: SLF001
    got, mask = _decode(m, v)
    t.ok(mask >= 0, "the format area names one of the eight legal masks",
         "read %d — a reader gives up before it looks at the data" % mask)
    t.eq(got, url, "the URL reads back out of the picture")

    # a longer one, to cross a version boundary and use two blocks
    long_url = "http://192.168.137.1:9203/studio/?rig=nong-85&from=the-hub-on-this-pc"
    v2 = qr.fit(long_url)
    t.ok(v2 > v, "a longer address picks a bigger version",
         "%d bytes chose version %d" % (len(long_url), v2))
    back, _mask2 = _decode(qr.matrix(long_url), v2)
    t.eq(back, long_url, "and that one reads back too")

    # ---- 2. the parity is right, checked another way ----------------
    for text in (url, long_url):
        bad = _syndromes_zero(text, qr.fit(text))
        t.ok(not bad, "the error correction is valid for %d bytes" % len(text),
             "non-zero syndromes: %r — a reader would refuse or misread" % bad[:4])

    # ---- 3. the fixed patterns are where the standard says ----------
    side = len(m)
    for name, (r0, c0) in (("top left", (0, 0)), ("top right", (0, side - 7)),
                           ("bottom left", (side - 7, 0))):
        ring = all(m[r0][c0 + i] == 1 for i in range(7)) and \
            all(m[r0 + 6][c0 + i] == 1 for i in range(7)) and \
            m[r0 + 3][c0 + 3] == 1 and m[r0 + 1][c0 + 1] == 0
        t.ok(ring, "the %s finder pattern is there" % name,
             "a reader finds the code by these three and nothing else")
    timing = all(m[6][i] == (1 if i % 2 == 0 else 0) for i in range(8, side - 8))
    t.ok(timing, "the timing row alternates, so a reader can measure the grid")
    t.eq(m[side - 8][8], 1, "the always-dark module is dark")

    # ---- 4. the data path covers every free cell, once --------------
    free = qr.free_cells(v)
    order = qr.zigzag(side, free)
    t.eq(len(order), len(set(order)), "no cell is written twice")
    t.eq(len(order), sum(sum(1 for x in row if x) for row in free),
         "and every free cell is written")
    t.ok(all(c != 6 for _r, c in order),
         "the timing column is stepped over, not written through")

    # ---- 5. the hub serves it ---------------------------------------
    base, main = F.start_hub()
    code, body = F.get(base + "/api/qr")
    t.eq(code, 200, "GET /api/qr answers")
    t.contains(body, "<svg", "with an SVG, so it stays sharp on any screen")
    t.contains(body, "http://", "carrying a URL")
    t.contains(body, str(main.PORT), "the address of THIS hub, port and all")
    t.ok("<rect" in body and body.count("<rect") > 50,
         "and the code is actually drawn",
         "%d rectangles — an empty SVG is a QR nobody can scan" % body.count("<rect"))

    # It must not need a login: the QR is how a phone GETS to the login. Asked
    # with NO cookie at all - qc.get and qc.raw_get both carry the QC session,
    # so asking with them proves nothing about the gate, which is exactly the
    # mistake the first version of this made: putting /api/qr behind the login
    # did not fail this check.
    import http.client
    c = http.client.HTTPConnection(base.split("//", 1)[1], timeout=10)
    try:
        c.request("GET", "/api/qr")
        anon = c.getresponse()
        code, body = anon.status, anon.read(400)
    finally:
        c.close()
    t.eq(code, 200, "and a phone that has never logged in can still fetch it")
    t.contains(body.decode("utf-8", "replace"), "<svg",
               "getting the picture, not a login page")

    # ---- 6. the tables are not taken on trust -----------------------
    # A table copied wrong produces a QR that looks perfect and scans as
    # nothing, and no other assertion here would notice.
    wrong = [(m, qr.FORMAT_L[m]) for m in range(8)
             if qr.FORMAT_L[m] != _bch_format(0b01, m)]
    t.ok(not wrong, "every format string matches the BCH code it must be",
         "computed from the standard's generator: %r" % wrong)

    # And the capacity table has to agree with the PICTURE: whatever the fixed
    # patterns leave free, in bytes, is exactly the codewords for that version.
    off = []
    for ver, (side, data, ec, blocks) in sorted(qr._VERSIONS.items()):   # noqa: SLF001
        cells = sum(sum(1 for x in row if x) for row in qr.free_cells(ver))
        if cells // 8 != data + blocks * ec:
            off.append((ver, cells // 8, data + blocks * ec))
    t.ok(not off, "and every version holds exactly what its table claims",
         "version, room in the picture, what the table says: %r" % off)

