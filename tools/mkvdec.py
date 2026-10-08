"""Generator of the Z80 video decoder handlers (docs/format.md): sapi/gen/vdec.asm.

Every opcode of tools/vfmt.py has its own handler at the address (page << 8) | opcode, so dispatching is
   ld a,(bc) / inc bc / ld l,a / ld h,HI(vjt) / ld h,(hl) / jp (hl)       (35 T)
with vjt[op] = page of the handler. Registers in the decoder: DE = address of the left byte of the track's
interval in the previous row, BC = stream pointer, HL and A scratch. Handlers are placed into the pages from
VDEC_BASE up, wherever the bytes are free.

The cost of every opcode (T-states at 4 MHz without waits, number of video memory reads and writes) is in
COST and is used by the encoder (tools/vcodec.py).

Usage: python tools/mkvdec.py      (writes sapi/gen/vdec.asm)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vfmt  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VJT = 0x1000             # jump table page (high bytes of the handlers)
VDEC_BASE = 0x1100       # first page of handlers
VDEC_END = 0x3800        # handlers must end below

# instruction: (text, bytes, T, video reads, video writes)
I = {
    'ld a,(bc)': (1, 7), 'inc bc': (1, 6), 'ld l,a': (1, 4), 'ld h,a': (1, 4), 'ld h,(hl)': (1, 7),
    'jp (hl)': (1, 4), 'add hl,de': (1, 11), 'ex de,hl': (1, 4), 'ld a,(de)': (1, 7), 'ld (de),a': (1, 7),
    'ld h,d': (1, 4), 'ld l,e': (1, 4), 'inc hl': (1, 6), 'ld a,(hl)': (1, 7), 'ld (hl),a': (1, 7),
    'cpl': (1, 4), 'ld e,a': (1, 4), 'ld d,a': (1, 4), 'ret': (1, 10), 'push bc': (1, 11),
    'pop bc': (1, 10), 'ld b,a': (1, 4),
}
VREAD = {'ld a,(de)', 'ld a,(hl)'}
VWRITE = {'ld (de),a', 'ld (hl),a'}


class Code:
    def __init__(self):
        self.lines = []
        self.size = 0
        self.t = 0
        self.r = 0
        self.w = 0

    def op(self, text, size=None, t=None, vram=True):
        if size is None:
            size, t = I[text]
        self.lines.append('\t' + text)
        self.size += size
        self.t += t
        if vram and text in VREAD:
            self.r += 1
        if vram and text in VWRITE:
            self.w += 1

    def ld_hl(self, v):
        self.op(f'ld hl,{v & 0xFFFF:05X}h', 3, 10)

    def xor_n(self, v):
        if v == 0xFF:
            self.op('cpl')
        else:
            self.op(f'xor {v:03X}h', 2, 7)

    def dispatch(self):
        self.op('ld a,(bc)', vram=False)
        self.op('inc bc')
        self.op('ld l,a')
        self.op('ld h,HI_VJT', 2, 7)
        self.op('ld h,(hl)', vram=False)
        self.op('jp (hl)')


def step(c, d):
    c.ld_hl(vfmt.ROW + d)
    c.op('add hl,de')
    c.op('ex de,hl')


def handler(op):
    k = op[0]
    c = Code()
    if k == 'S':
        _, d, a, b = op
        step(c, d)
        c.op('ld a,(de)')
        c.xor_n(vfmt.pix_mask(a, b))
        c.op('ld (de),a')
    elif k == 'M':
        _, d, a, b, m = op
        step(c, d)
        c.op('ld a,(de)')
        c.xor_n(vfmt.pix_mask(a, 3))
        c.op('ld (de),a')
        c.op('ld h,d')
        c.op('ld l,e')
        for _ in range(m):
            c.op('inc hl')
            c.op('ld a,(hl)')
            c.op('cpl')
            c.op('ld (hl),a')
        c.op('inc hl')
        c.op('ld a,(hl)')
        c.xor_n(vfmt.pix_mask(0, b))
        c.op('ld (hl),a')
    elif k == 'MX':
        _, d, a, b = op
        step(c, d)
        c.op('ld a,(de)')
        c.xor_n(vfmt.pix_mask(a, 3))
        c.op('ld (de),a')
        c.op('ld a,(bc)', vram=False)          # m (3..255), loop with B
        c.op('inc bc')
        c.op('push bc')
        c.op('ld b,a')
        c.op('ld h,d')
        c.op('ld l,e')
        lab = f'.vmx{d + 1}{a}{b}'
        c.lines.append(lab + ':')
        c.op('inc hl')
        c.op('ld a,(hl)')
        c.op('cpl')
        c.op('ld (hl),a')
        c.op(f'djnz {lab}', 2, 13)             # counted once; the rest in MX_MID
        c.op('pop bc')
        c.op('inc hl')
        c.op('ld a,(hl)')
        c.xor_n(vfmt.pix_mask(0, b))
        c.op('ld (hl),a')
    elif k == 'TRACKA':
        c.op('ld a,(bc)', vram=False)
        c.op('inc bc')
        c.op('ld e,a')
        c.op('ld a,(bc)', vram=False)
        c.op('inc bc')
        c.op('ld d,a')
        c.op('ld (vtstart),de', 4, 20)
    elif k == 'TRACKR':
        c.op('ld hl,(vtstart)', 3, 16)
        c.op('ld a,(bc)', vram=False)
        c.op('inc bc')
        c.op('add a,l', 1, 4)
        c.op('ld l,a')
        c.op('adc a,h', 1, 4)
        c.op('sub l', 1, 4)
        c.op('ld h,a')
        c.op('ld (vtstart),hl', 3, 16)
        c.op('ex de,hl')
    elif k == 'CLR':
        c.op('jp vclr', 3, 10)                 # sapi/video.asm; cost in the encoder
        return c
    elif k == 'END':
        c.op('ret')
        return c
    c.dispatch()
    return c


# cost of one middle byte in the MX loop (inc hl, ld a,(hl), cpl, ld (hl),a, djnz): T, reads, writes
MX_MID = (6 + 7 + 4 + 7 + 13, 1, 1)     # the last djnz is 5 T shorter


def build():
    handlers = [handler(op) for op in vfmt.OPS]
    used = bytearray(VDEC_END - VDEC_BASE)
    place = []
    for opc, h in enumerate(handlers):
        page = VDEC_BASE >> 8
        while True:
            a = (page << 8) | opc
            lo, hi = a - VDEC_BASE, a - VDEC_BASE + h.size
            if hi > len(used):
                sys.exit(f'handlers do not fit below {VDEC_END:04X}h')
            if not any(used[lo:hi]):
                used[lo:hi] = b'\x01' * h.size
                place.append(a)
                break
            page += 1
    return handlers, place


COST = None


def costs():
    """Per opcode (T, reads, writes)."""
    global COST
    if COST is None:
        COST = [(h.t, h.r, h.w) for h in (handler(op) for op in vfmt.OPS)]
    return COST


def main():
    handlers, place = build()
    out = ['; Generated by tools/mkvdec.py from tools/vfmt.py - do not edit.',
           '; Video decoder handlers: one per opcode at (page << 8) | opcode (docs/format.md).', '',
           f'HI_VJT\tequ {VJT >> 8:03X}h', '']
    out.append(f'\torg {VJT:05X}h')
    out.append('vjt:')
    for i in range(0, 256, 16):
        row = [(place[j] >> 8) if j < len(place) else 0 for j in range(i, i + 16)]
        out.append('\tdb ' + ','.join(f'{v:03X}h' for v in row))
    for opc in sorted(range(len(handlers)), key=lambda j: place[j]):
        h = handlers[opc]
        out.append('')
        out.append(f'\torg {place[opc]:05X}h')
        out.append(f'vop_{opc:02X}:\t\t\t; {vfmt.OPS[opc]} {h.t} T, {h.r} R, {h.w} W')
        out += h.lines
    end = max(p + h.size for p, h in zip(place, handlers))
    out.append('')
    out.append(f'VDEC_TOP\tequ {end:05X}h')
    os.makedirs(os.path.join(ROOT, 'sapi', 'gen'), exist_ok=True)
    path = os.path.join(ROOT, 'sapi', 'gen', 'vdec.asm')
    open(path, 'w', newline='\n').write('\n'.join(out) + '\n')
    print(f'{path}: {len(handlers)} handlers, {VJT:04X}h..{end:04X}h '
          f'({sum(h.size for h in handlers)} B of code)')


if __name__ == '__main__':
    main()
