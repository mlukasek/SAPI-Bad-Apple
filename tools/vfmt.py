"""Track format of the video (docs/format.md): the opcode table shared by the encoder (tools/vcodec.py) and the
generator of the Z80 decoder (tools/mkvdec.py).

A frame is a list of row clears (CLR) and then a list of tracks. A track is a vertical chain of XOR intervals,
one per row, on the CPU page of CGA-1V. Decoder state: DE = address of the left byte of the interval in the
previous row of the track. Each row is one opcode (MX has an extra byte):
  - step: DE += 80 + d (d = -1, 0, 1: the left byte moves by d bytes),
  - S: XOR one byte with a mask of pixels a..b of the byte (a <= b),
  - M: XOR the left byte with pixels a..3, m full bytes (complement), the right byte with pixels 0..b,
  - MX: the same for m = 3..62 middle bytes, but the middle is filled with a colour (00h or FFh): the encoder
    only uses it where the middle of the old picture is one colour. Extra byte: 2 * (62 - m) + (1 if FFh), the
    entry into the unrolled fill (sapi/video.asm vfill).
A track starts with TRACKA + 2 B (DE of the row above its first row) or TRACKR + 1 B (DE = DE of the previous
track start + the byte). CLR + 2 B address + 1 B rows + 1 B colour fills rows of 64 B (stride 80). END ends the
frame. Masks are in CGA mode (2 bits per pixel, white = both bits): pixel p of a byte = bits 7-p and 3-p.
"""

ROW = 80                 # bytes per line of CGA-1V
STEP_D = (-1, 0, 1)
MULTI_M = (0, 1, 2)      # M codes; m >= 3 is MX + byte


def pix_mask(a, b):
    """Byte mask of pixels a..b (0 = left)."""
    n = 0
    for p in range(a, b + 1):
        n |= 1 << (3 - p)
    return (n << 4) | n


# opcode table: list of (kind, params); index = opcode
OPS = []
for d in STEP_D:
    for a in range(4):
        for b in range(a, 4):
            OPS.append(('S', d, a, b))                 # 30 codes
for d in STEP_D:
    for a in range(4):
        for b in range(4):
            for m in MULTI_M:
                OPS.append(('M', d, a, b, m))          # 144 codes
for d in STEP_D:
    for a in range(4):
        for b in range(4):
            OPS.append(('MX', d, a, b))                # 48 codes, then 1 B: 2 * (62 - m) + colour
OPS.append(('TRACKA',))                                # then 2 B: DE (little endian)
OPS.append(('TRACKR',))                                # then 1 B: DE = track start + byte
OPS.append(('CLR',))                                   # then 2 B address, 1 B rows, 1 B colour
OPS.append(('END',))
assert len(OPS) <= 256, len(OPS)

CODE = {op: i for i, op in enumerate(OPS)}
OP_TRACKA = CODE[('TRACKA',)]
OP_TRACKR = CODE[('TRACKR',)]
OP_CLR = CODE[('CLR',)]
OP_END = CODE[('END',)]


FILL_MAX = 62


def code_for(d, s, e1, fill=0):
    """Opcode bytes for one row: d = byte step of the left byte (-1..1), interval pixels s..e1; fill = new
    value of the middle bytes (0 or 0xFF) for MX."""
    a, b = s & 3, e1 & 3
    m = (e1 >> 2) - (s >> 2) - 1
    if m < 0:
        return bytes([CODE[('S', d, a, b)]])
    if m in MULTI_M:
        return bytes([CODE[('M', d, a, b, m)]])
    assert m <= FILL_MAX
    return bytes([CODE[('MX', d, a, b)], 2 * (FILL_MAX - m) + (1 if fill else 0)])


def mx_m(extra):
    return FILL_MAX - (extra >> 1)


def body_end(buf, pos):
    """Position after the END of the frame body at buf[pos:]."""
    extra = {'TRACKA': 2, 'TRACKR': 1, 'MX': 1, 'CLR': 4}
    while True:
        k = OPS[buf[pos]][0]
        pos += 1
        if k == 'END':
            return pos
        pos += extra.get(k, 0)
