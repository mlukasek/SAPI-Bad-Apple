"""Music of Bad Apple!! for the YM3812 of MPH-1V: MIDI -> arrangement -> stream of register writes (stdlib only).

Source: a MIDI transcription of the Alstroemeria Records version (orig/midi/, not in the repo). Its time 0 is at
MIDI_OFFSET s of the audio of the video (tools/msync.py). The arrangement: OPL2 rhythm mode (BD, SD, HH, TOM, CYM)
and 6 melodic voices (vocal, bass, square lead, arpeggio, guitar 2x), instruments in tools/opl_patches.py.

Stream (docs/format.md): register writes as pairs (register, value); FFh = wait for the next VBI (one per tick of
59.94 Hz, the first VBI plays tick 0); FEh = end. Writes before the first FFh are the setup. The interrupt
(sapi/music.asm, 1300.7 Hz) writes at most one pair per call, so writes never need the delays of the YM3812.

Outputs: build/music.bin (the stream, for tools/mkdat.py --music), build/badapple.vgm (VGM 1.51 with the exact
times of the writes, for listening in a VGM player).
Usage: python tools/mkmusic.py [--midi FILE] [--out build/music.bin] [--vgm build/badapple.vgm]
"""
import argparse
import math
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import midi  # noqa: E402
import opl_patches as P  # noqa: E402

MIDI_FILE = os.path.join(ROOT, 'orig', 'midi', 'handhule90-full.mid')
MIDI_OFFSET = 1.39                  # s of the video audio at MIDI time 0 (tools/msync.py)
TICK_HZ = 60000 / 1001              # VBI of CGA-1V
ISR_HZ = 55930.4 / 43               # interrupt of the 82C54
YM_CLOCK = 3579545
YM_RATE = YM_CLOCK / 72
WAIT = 0xFF
END = 0xFE

MOD_SLOT = (0x00, 0x01, 0x02, 0x08, 0x09, 0x0A, 0x10, 0x11, 0x12)   # register offset of the modulator of a channel
SLOT_BD = (0x10, 0x13)
SLOT_HH, SLOT_SD, SLOT_TOM, SLOT_CYM = 0x11, 0x14, 0x12, 0x15
BD_BASE = 0x20 | 0x40               # rhythm mode, deep vibrato (14 cent)
BIT = {'BD': 0x10, 'SD': 0x08, 'TOM': 0x04, 'CYM': 0x02, 'HH': 0x01}

# melodic parts: MIDI tracks -> channels. pick: which notes of a chord are kept (lowest / highest first).
PARTS = [
    dict(name='vocal', tracks=(6,), patch=P.VOCAL, chans=(0,), pick='top', att=0.0),
    dict(name='bass', tracks=(9,), patch=P.BASS, chans=(1,), pick='bottom', att=1.5, min_key=35),
    dict(name='square', tracks=(5,), patch=P.SQUARE, chans=(2,), pick='top', att=7.0),
    dict(name='arp', tracks=(8,), patch=P.ARP, chans=(3,), pick='top', att=6.0),
    dict(name='guitar', tracks=(7,), patch=P.GUITAR, chans=(4, 5), pick='bottom', att=6.0),
]
# drums: GM key -> (instrument, variant, attenuation dB, TOM key)
DRUMS = {
    35: ('BD', None, 0, None), 36: ('BD', None, 0, None),
    38: ('SD', None, 0, None), 39: ('SD', None, 1.5, None), 40: ('SD', None, 0, None),
    42: ('HH', 'closed', 6, None), 69: ('HH', 'closed', 10, None), 82: ('HH', 'closed', 12, None),
    46: ('HH', 'open', 6, None),
    49: ('CYM', None, 3, None),
    60: ('TOM', None, 6, 67), 61: ('TOM', None, 6, 62), 63: ('TOM', None, 5, 60), 64: ('TOM', None, 5, 55),
}
DRUM_SLOT = {'SD': SLOT_SD, 'HH': SLOT_HH, 'TOM': SLOT_TOM, 'CYM': SLOT_CYM}
DRUM_OP = {('SD', None): P.SD, ('HH', 'closed'): P.HH, ('HH', 'open'): P.HH_OPEN, ('TOM', None): P.TOM,
           ('CYM', None): P.CYM}
RHYTHM_KEYS = {6: 35, 7: 67, 8: 60}     # pitch of the rhythm channels (ch 8 changes with TOM)


def ym_freq(key):
    """(block, F-number) of a MIDI key, the finest block that fits."""
    f = 440.0 * 2 ** ((key - 69) / 12)
    for block in range(8):
        fn = round(f * (1 << (20 - block)) / YM_RATE)
        if fn < 1024:
            return block, fn
    return 7, 1023


def op_regs(slot, o, tl=None):
    """(register, value) of an operator at a slot offset."""
    return [(0x20 + slot, o['am'] << 7 | o['vib'] << 6 | o['egt'] << 5 | o['ksr'] << 4 | o['mult']),
            (0x40 + slot, o['ksl'] << 6 | (o['tl'] if tl is None else tl)),
            (0x60 + slot, o['ar'] << 4 | o['dr']),
            (0x80 + slot, o['sl'] << 4 | o['rr']),
            (0xE0 + slot, o['ws'])]


def patch_regs(ch, p):
    m = MOD_SLOT[ch]
    return op_regs(m, p['mod']) + op_regs(m + 3, p['car']) + [(0xC0 + ch, p['fb'] << 1 | p['cnt'])]


def tl_of(o, att_db):
    return max(0, min(63, o['tl'] + round(att_db / 0.75)))


def vel_db(vel):
    return 40 * math.log10(127 / max(1, vel)) * 0.5


def tick_of(t):
    return round((t + MIDI_OFFSET) * TICK_HZ)


def melodic_notes(song, part):
    """{channel: [(k0, k1, key, vel)]} of a part: chords cut to the channels, notes cut by the next one."""
    notes = [n for n in song.notes if n.track in part['tracks']]
    groups = {}
    for n in notes:
        groups.setdefault(tick_of(n.t0), []).append(n)
    out = {c: [] for c in part['chans']}
    for k0 in sorted(groups):
        g = sorted(groups[k0], key=lambda n: n.key, reverse=part['pick'] == 'top')
        seen, sel = set(), []
        for n in g:
            if n.key not in seen:
                seen.add(n.key)
                sel.append(n)
        sel = sel[:len(part['chans'])]
        sel.sort(key=lambda n: n.key)
        for c, n in zip(part['chans'], sel):
            key = n.key
            while key < part.get('min_key', 0):
                key += 12
            out[c].append([k0, max(k0 + 1, tick_of(n.t1)), key, n.vel])
    for c, lst in out.items():
        for a, b in zip(lst, lst[1:]):
            a[1] = min(a[1], b[0])
    return out


def drum_hits(song):
    """{tick: {instrument: (vel_db, variant, tom key)}} (the loudest hit of an instrument in a tick)."""
    hits = {}
    for n in song.notes:
        if n.ch != 9 or n.key not in DRUMS:
            continue
        ins, var, att, tom = DRUMS[n.key]
        a = att + vel_db(n.vel)
        k = tick_of(n.t0)
        cur = hits.setdefault(k, {}).get(ins)
        if cur is None or a < cur[0]:
            hits[k][ins] = (a, var, tom)
    return hits


class Regs:
    """Shadow of the registers: only changes are written (forced writes for key on/off)."""
    def __init__(self):
        self.v = {}

    def set(self, out, r, val, force=False):
        if force or self.v.get(r) != val:
            out.append((r, val))
            self.v[r] = val


def arrange(song):
    """-> list of ticks, each a list of (register, value); and the setup writes."""
    regs = Regs()
    setup = []
    regs.set(setup, 0x01, 0x20, True)          # waveform select on
    regs.set(setup, 0x08, 0x00, True)
    regs.set(setup, 0xBD, 0x00, True)
    for ch in range(9):
        regs.set(setup, 0xB0 + ch, 0x00, True)
    for part in PARTS:
        for ch in part['chans']:
            for r, v in patch_regs(ch, part['patch']):
                regs.set(setup, r, v, True)
    for r, v in patch_regs(6, P.BD):
        regs.set(setup, r, v, True)
    for (ins, var), o in DRUM_OP.items():
        if var != 'open':
            for r, v in op_regs(DRUM_SLOT[ins], o):
                regs.set(setup, r, v, True)
    for ch, key in RHYTHM_KEYS.items():
        block, fn = ym_freq(key)
        regs.set(setup, 0xA0 + ch, fn & 0xFF, True)
        regs.set(setup, 0xB0 + ch, block << 2 | fn >> 8, True)
    regs.set(setup, 0xBD, BD_BASE, True)

    chans = {}
    patch_of = {}
    for part in PARTS:
        for c, lst in melodic_notes(song, part).items():
            chans[c] = lst
            patch_of[c] = (part['patch'], part['att'])
    starts, ends = {}, {}
    for c, lst in chans.items():
        for k0, k1, key, vel in lst:
            starts.setdefault(k0, []).append((c, key, vel))
            ends.setdefault(k1, []).append(c)
    hits = drum_hits(song)
    last = max(list(ends) + list(hits)) + 30
    ticks = []
    for k in range(last + 1):
        offs, levels, freqs, ons = [], [], [], []
        starting = {c for c, _, _ in starts.get(k, ())}
        for c in ends.get(k, ()):
            regs.set(offs, 0xB0 + c, regs.v.get(0xB0 + c, 0) & 0x1F, True)
        for c, key, vel in starts.get(k, ()):
            p, att = patch_of[c]
            if regs.v.get(0xB0 + c, 0) & 0x20:            # still on (legato): retrigger
                regs.set(offs, 0xB0 + c, regs.v[0xB0 + c] & 0x1F, True)
            regs.set(levels, 0x43 + MOD_SLOT[c], p['car']['ksl'] << 6 | tl_of(p['car'], att + vel_db(vel)))
            block, fn = ym_freq(key)
            regs.set(freqs, 0xA0 + c, fn & 0xFF)
            regs.set(ons, 0xB0 + c, 0x20 | block << 2 | fn >> 8, True)
        del starting
        # drums
        h = hits.get(k, {})
        bits = 0
        for ins, (a, var, tom) in h.items():
            bits |= BIT[ins]
            if ins == 'BD':
                regs.set(levels, 0x40 + SLOT_BD[1], P.BD['car']['ksl'] << 6 | tl_of(P.BD['car'], a))
                continue
            o = DRUM_OP[(ins, var)]
            slot = DRUM_SLOT[ins]
            for r, v in op_regs(slot, o, tl_of(o, a))[1:4]:
                regs.set(levels, r, v)
            if tom is not None:
                block, fn = ym_freq(tom)
                regs.set(freqs, 0xA8, fn & 0xFF)
                regs.set(freqs, 0xB8, block << 2 | fn >> 8)
        drum = []
        cur = regs.v.get(0xBD, BD_BASE)
        if cur & bits:                                  # retrigger: the bit must go 0 first
            regs.set(drum, 0xBD, cur & ~bits & 0xFF, True)
        regs.set(drum, 0xBD, BD_BASE | bits)
        ticks.append(offs + levels + freqs + ons + drum)
    # silence at the end
    tail = []
    for ch in range(9):
        regs.set(tail, 0xB0 + ch, regs.v.get(0xB0 + ch, 0) & 0x1F)
    regs.set(tail, 0xBD, BD_BASE)
    ticks.append(tail)
    return setup, ticks


def stream_of(setup, ticks):
    out = bytearray()
    for r, v in setup:
        out += bytes((r, v))
    for t in ticks:
        out.append(WAIT)
        for r, v in t:
            out += bytes((r, v))
    out.append(END)
    return out


def simulate(stream, per_isr=1, isr_phase=0.5):
    """Times of the writes as the interrupt makes them: [(time s, reg, val)], and the worst lag in ticks.
    VBI k (k = 0, 1, ...) is at (k + 1) / TICK_HZ; the stream's tick k starts at it."""
    out = []
    p = 0
    while stream[p] < END:                  # setup: mus_init writes it before the interrupt runs
        out.append((0.0, stream[p], stream[p + 1]))
        p += 2
    vbis = 0
    tick = -1
    tick_start = 0.0
    worst = 0.0
    i = 0
    while stream[p] != END:
        t = (i + isr_phase) / ISR_HZ
        i += 1
        while (vbis + 1) / TICK_HZ <= t:
            vbis += 1
        n = 0
        while n < per_isr and stream[p] != END:
            if stream[p] == WAIT:
                if tick + 1 >= vbis:
                    break
                tick += 1
                tick_start = (tick + 1) / TICK_HZ
                p += 1
                continue
            out.append((t, stream[p], stream[p + 1]))
            worst = max(worst, (t - tick_start) * TICK_HZ)
            p += 2
            n += 1
    return out, worst


def write_vgm(path, writes, title='Bad Apple!! (SAPI-1 MPH-1V arrangement)'):
    body = bytearray()
    now = 0
    for t, r, v in writes:
        s = round(t * 44100)
        while s > now:
            d = min(65535, s - now)
            body += bytes((0x61,)) + struct.pack('<H', d)
            now += d
        body += bytes((0x5A, r, v))
    end = now + 2 * 44100
    while end > now:
        d = min(65535, end - now)
        body += bytes((0x61,)) + struct.pack('<H', d)
        now += d
    body.append(0x66)
    hdr = bytearray(0x100)
    hdr[0:4] = b'Vgm '
    struct.pack_into('<I', hdr, 0x08, 0x151)
    struct.pack_into('<I', hdr, 0x18, now)
    struct.pack_into('<I', hdr, 0x24, 60)
    struct.pack_into('<I', hdr, 0x34, 0x100 - 0x34)
    struct.pack_into('<I', hdr, 0x50, YM_CLOCK)
    data = hdr + body
    struct.pack_into('<I', data, 0x04, len(data) - 4)
    open(path, 'wb').write(data)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--midi', default=MIDI_FILE)
    ap.add_argument('--out', default=os.path.join(ROOT, 'build', 'music.bin'))
    ap.add_argument('--vgm', default=os.path.join(ROOT, 'build', 'badapple.vgm'))
    a = ap.parse_args()
    song = midi.load(a.midi)
    setup, ticks = arrange(song)
    st = stream_of(setup, ticks)
    writes, worst = simulate(st)
    n = [len(t) for t in ticks]
    srt = sorted(n)
    print(f'music: {len(ticks)} ticks ({len(ticks) / TICK_HZ:.1f} s), {len(st)} B, setup {len(setup)} writes')
    print(f'  writes/tick: mean {sum(n) / len(n):.2f} p99 {srt[len(n) * 99 // 100]} max {srt[-1]}; '
          f'worst lag {worst:.2f} ticks')
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    open(a.out, 'wb').write(st)
    if a.vgm:
        write_vgm(a.vgm, writes)
        print(f'  {a.out}, {a.vgm}')


if __name__ == '__main__':
    main()
