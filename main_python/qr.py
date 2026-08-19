"""A QR code, from nothing but the standard library.

WHY THIS EXISTS
---------------
The hub prints its address to a console nobody at a venue is looking at. The
way people actually get a phone onto a rig is by pointing it at a screen, so
the hub has to be able to draw the one thing a phone camera understands.

Nothing may be installed for it. The hub is stdlib-only on purpose — it is
copied to a laptop at a venue and run — so `pip install qrcode` is not an
option, and neither is fetching an image from an API on a network that has no
way out. That leaves writing the encoder, which is about two hundred lines and
entirely specified.

WHAT IT DOES, AND WHAT IT DOES NOT
----------------------------------
Byte mode, error-correction level L, versions 1 to 6 — up to 134 characters,
where a hub URL is about 26. That is everything `http://192.168.1.20:9203/`
needs and nothing more, because every extra version is another table to be
wrong in.

The pieces, in the order the standard builds them:

    _bits        the text becomes bits: mode, length, data, terminator, padding
    _rs_parity   Reed-Solomon parity over GF(256) — the part that survives damage
    zigzag       the codewords are laid in a zig-zag around the fixed patterns
    MASKS        eight candidate patterns, scored, and the least bad one wins

VERIFYING IT
------------
A wrong QR still looks like a QR, so qc/checks/check_qr.py does not eyeball it.
It reads the matrix BACK — undoes the mask, walks the same zig-zag, strips the
parity and recovers the string — and it checks the parity independently by
computing syndromes, which a valid Reed-Solomon codeword answers with zero.
Syndromes are different arithmetic from the generator polynomial that produced
the parity, so the two agreeing is not one bug agreeing with itself.
"""

# ---- GF(256), the field Reed-Solomon works in -------------------------
# x^8 + x^4 + x^3 + x^2 + 1, the polynomial QR uses. Built once, at import.
_EXP = [0] * 512
_LOG = [0] * 256
_x = 1
for _i in range(255):
    _EXP[_i] = _x
    _LOG[_x] = _i
    _x <<= 1
    if _x & 0x100:
        _x ^= 0x11D
for _i in range(255, 512):
    _EXP[_i] = _EXP[_i - 255]


def mul(a, b):
    """Multiply in GF(256). Public: the check computes syndromes with it."""
    if a == 0 or b == 0:
        return 0
    return _EXP[_LOG[a] + _LOG[b]]


def exp(i):
    """The generator raised to i, in GF(256)."""
    return _EXP[i % 255]


# ---- the tables, for versions 1..6 at error level L -------------------
# Data rather than formulas: they are lookup tables in the standard too, and a
# wrong formula here would produce a QR that scans as gibberish rather than one
# that fails loudly.
#   version: (modules per side, data codewords, EC codewords per block, blocks)
_VERSIONS = {
    1: (21, 19, 7, 1),
    2: (25, 34, 10, 1),
    3: (29, 55, 15, 1),
    4: (33, 80, 20, 1),
    5: (37, 108, 26, 1),
    6: (41, 136, 18, 2),
}
# Where the alignment patterns go, per version (centres, on both axes).
_ALIGN = {1: [], 2: [6, 18], 3: [6, 22], 4: [6, 26], 5: [6, 30], 6: [6, 34]}


def _poly_mul(a, b):
    out = [0] * (len(a) + len(b) - 1)
    for i, av in enumerate(a):
        for j, bv in enumerate(b):
            out[i + j] ^= mul(av, bv)
    return out


def _rs_generator(n):
    """The generator polynomial for n parity bytes."""
    g = [1]
    for i in range(n):
        g = _poly_mul(g, [1, _EXP[i]])
    return g


def _rs_parity(data, n):
    """n Reed-Solomon parity bytes for these data bytes."""
    gen = _rs_generator(n)
    rem = list(data) + [0] * n
    for i in range(len(data)):
        coef = rem[i]
        if coef:
            for j, g in enumerate(gen):
                rem[i + j] ^= mul(g, coef)
    return rem[len(data):]


# ---- bits ------------------------------------------------------------
def _bits(text, version):
    """The text as a bit string: mode, length, bytes, terminator, padding."""
    data = text.encode("utf-8")
    _side, total, _ec, _blocks = _VERSIONS[version]
    if len(data) + 2 > total:
        raise ValueError("%d bytes will not fit a version %d QR"
                         % (len(data), version))
    # 0100 = byte mode. The length field is 8 bits for versions 1 to 9.
    out = "0100" + format(len(data), "08b")
    out += "".join(format(b, "08b") for b in data)
    out += "0000"                                   # terminator
    out = out[:total * 8]
    out += "0" * (-len(out) % 8)                    # up to a whole byte
    pad = ["11101100", "00010001"]                  # the standard's filler
    i = 0
    while len(out) < total * 8:
        out += pad[i % 2]
        i += 1
    return out


def codewords(text, version):
    """Data + parity, interleaved per block the way the standard requires.

    Public because the check reads them back out of the picture and compares.
    """
    _side, total, ec, blocks = _VERSIONS[version]
    raw = _bits(text, version)
    data = [int(raw[i:i + 8], 2) for i in range(0, len(raw), 8)]
    per, extra = total // blocks, total % blocks
    chunks, at = [], 0
    for b in range(blocks):
        n = per + (1 if b >= blocks - extra else 0)
        chunks.append(data[at:at + n])
        at += n
    parity = [_rs_parity(c, ec) for c in chunks]
    out = []
    for i in range(max(len(c) for c in chunks)):
        for c in chunks:
            if i < len(c):
                out.append(c[i])
    for i in range(ec):
        for block in parity:
            out.append(block[i])
    return out


# ---- the picture -----------------------------------------------------
def _blank(side):
    return [[None] * side for _ in range(side)]


def _finder(m, r, c):
    """One 7x7 corner marker, with its separator."""
    for dr in range(-1, 8):
        for dc in range(-1, 8):
            rr, cc = r + dr, c + dc
            if not (0 <= rr < len(m) and 0 <= cc < len(m)):
                continue
            inside = 0 <= dr < 7 and 0 <= dc < 7
            ring = inside and (dr in (0, 6) or dc in (0, 6)
                               or (2 <= dr <= 4 and 2 <= dc <= 4))
            m[rr][cc] = 1 if ring else 0


def _fixed(m, version):
    """Everything whose position is decided by the standard, not by the data."""
    side = len(m)
    _finder(m, 0, 0)
    _finder(m, 0, side - 7)
    _finder(m, side - 7, 0)
    for i in range(8, side - 8):                    # timing patterns
        bit = 1 if i % 2 == 0 else 0
        m[6][i] = bit
        m[i][6] = bit
    for r in _ALIGN[version]:                       # alignment patterns
        for c in _ALIGN[version]:
            if (r < 9 and c < 9) or (r < 9 and c > side - 10) \
               or (r > side - 10 and c < 9):
                continue                            # never on a finder
            for dr in range(-2, 3):
                for dc in range(-2, 3):
                    m[r + dr][c + dc] = 1 if (abs(dr) == 2 or abs(dc) == 2
                                              or (dr == 0 and dc == 0)) else 0
    m[side - 8][8] = 1                              # the always-dark module
    for i in range(9):                              # reserve the format area
        if m[8][i] is None:
            m[8][i] = 0
        if m[i][8] is None:
            m[i][8] = 0
    for i in range(8):
        if m[8][side - 1 - i] is None:
            m[8][side - 1 - i] = 0
        if m[side - 1 - i][8] is None:
            m[side - 1 - i][8] = 0
    return m


def free_cells(version):
    """Which cells the data may use: everything the fixed patterns left."""
    side = _VERSIONS[version][0]
    fixed = _fixed(_blank(side), version)
    return [[fixed[r][c] is None for c in range(side)] for r in range(side)]


def zigzag(side, free):
    """The order the standard fills cells in: up and down in pairs of columns.

    Public because the check walks the same path to read a QR back — and it
    also reads the picture with a decoder written the other way round, so the
    two are not one mistake agreeing with itself.
    """
    order = []
    col = side - 1
    upward = True
    while col > 0:
        if col == 6:                                # the timing column is skipped
            col -= 1
        rows = range(side - 1, -1, -1) if upward else range(side)
        for r in rows:
            for c in (col, col - 1):
                if free[r][c]:
                    order.append((r, c))
        col -= 2
        upward = not upward
    return order


MASKS = [
    lambda r, c: (r + c) % 2 == 0,
    lambda r, c: r % 2 == 0,
    lambda r, c: c % 3 == 0,
    lambda r, c: (r + c) % 3 == 0,
    lambda r, c: (r // 2 + c // 3) % 2 == 0,
    lambda r, c: (r * c) % 2 + (r * c) % 3 == 0,
    lambda r, c: ((r * c) % 2 + (r * c) % 3) % 2 == 0,
    lambda r, c: ((r + c) % 2 + (r * c) % 3) % 2 == 0,
]

# Format information for level L, masks 0..7: 15 bits each, BCH-protected and
# XOR'd with 101010000010010 as the standard says. A table, because getting the
# BCH wrong produces a code no reader will even attempt to read.
FORMAT_L = ["111011111000100", "111001011110011", "111110110101010",
            "111100010011101", "110011000101111", "110001100011000",
            "110110001000001", "110100101110110"]


def _penalty(m):
    """How bad a masked pattern is. Lower is better; the rules are the spec's."""
    side = len(m)
    score = 0
    for line in list(m) + [list(col) for col in zip(*m)]:
        run, last = 0, None
        for v in line:
            if v == last:
                run += 1
            else:
                if run >= 5:
                    score += 3 + (run - 5)
                run, last = 1, v
        if run >= 5:
            score += 3 + (run - 5)
    for r in range(side - 1):                       # 2x2 blocks of one colour
        for c in range(side - 1):
            if m[r][c] == m[r][c + 1] == m[r + 1][c] == m[r + 1][c + 1]:
                score += 3
    dark = sum(sum(row) for row in m)
    score += 10 * (abs(dark * 100 // (side * side) - 50) // 5)
    return score


def fit(text):
    """The smallest version this text fits in."""
    n = len(text.encode("utf-8"))
    for v in sorted(_VERSIONS):
        if n + 2 <= _VERSIONS[v][1]:
            return v
    raise ValueError("%d bytes is more than this encoder handles" % n)


def _write_format(m, mask):
    side = len(m)
    bits = FORMAT_L[mask]
    for i in range(6):                              # top-left, along the row
        m[8][i] = int(bits[i])
    m[8][7] = int(bits[6])
    m[8][8] = int(bits[7])
    m[7][8] = int(bits[8])
    for i in range(9, 15):                          # top-left, up the column
        m[14 - i][8] = int(bits[i])
    for i in range(8):                              # the second copy
        m[side - 1 - i][8] = int(bits[i])
    for i in range(8, 15):
        m[8][side - 15 + i] = int(bits[i])
    m[side - 8][8] = 1                              # dark module, again


def matrix(text, version=None):
    """The finished QR as rows of 0 and 1. 1 is a dark module."""
    version = version or fit(text)
    side = _VERSIONS[version][0]
    free = free_cells(version)
    order = zigzag(side, free)
    bits = "".join(format(b, "08b") for b in codewords(text, version))
    bits += "0" * (len(order) - len(bits))          # remainder bits are 0

    base = _fixed(_blank(side), version)
    for (r, c), bit in zip(order, bits):
        base[r][c] = int(bit)

    best, best_score = None, None
    for mask, rule in enumerate(MASKS):
        cand = [row[:] for row in base]
        for r, c in order:
            if rule(r, c):
                cand[r][c] ^= 1
        _write_format(cand, mask)
        s = _penalty(cand)
        if best_score is None or s < best_score:
            best, best_score = cand, s
    return best


def svg(text, quiet=4, scale=6):
    """The QR as an SVG string — no image library, and it stays sharp anywhere.

    A quiet zone is not decoration: a reader needs the clear border to find the
    code at all, and four modules is what the standard asks for.
    """
    m = matrix(text)
    side = len(m)
    total = (side + quiet * 2) * scale
    safe = (text.replace("&", "&amp;").replace("<", "&lt;").replace('"', "&quot;"))
    out = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" '
           'viewBox="0 0 %d %d" shape-rendering="crispEdges" role="img" '
           'aria-label="QR code for %s">' % (total, total, total, total, safe),
           '<rect width="100%" height="100%" fill="#fff"/>']
    for r in range(side):
        for c in range(side):
            if m[r][c]:
                out.append('<rect x="%d" y="%d" width="%d" height="%d" fill="#000"/>'
                           % ((c + quiet) * scale, (r + quiet) * scale, scale, scale))
    out.append("</svg>")
    return "".join(out)
