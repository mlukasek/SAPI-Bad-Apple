"""Music of Bad Apple!! for the YM3812 of MPH-1V: the arrangement (music/badapple.py) -> stream of register writes.

The arrangement is our own, written for the OPL2 (6 melodic channels and the rhythm mode). music/badapple.py puts
notes, drum hits and automation into a Song; this player turns them into register writes per tick: key on/off,
frequencies (detune, glides, legato without a new attack), levels (velocity, fades, brightness of the modulator),
delayed vibrato, the falling pitch of the bass drum, instrument changes ahead of the notes.

Time: a step is a 16th of the song (138 BPM), bar 0 begins OFFSET s after the first VBI (the audio of the video,
tools/transcribe.py). A tick is one VBI of 59.94 Hz at the nominal speed; the player in sapi/music.asm releases the
ticks by the 82C54 and slows them down when the picture is late (docs/format.md).

Stream (docs/format.md): register writes as pairs (register, value); FFh = the next tick; FEh = end. Writes before
the first FFh are the setup. The interrupt (1300.7 Hz) writes at most one pair per call, so writes never need the
delays of the YM3812.

Outputs: build/music.bin (the stream, for tools/mkdat.py --music), build/badapple.vgm (VGM 1.51 with the times of
the writes, for listening in a VGM player).
Usage: python tools/mkmusic.py [--out build/music.bin] [--vgm build/badapple.vgm]
"""
import argparse
import importlib.util
import math
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import opl_patches as P  # noqa: E402

SCORE = os.path.join(ROOT, 'music', 'badapple.py')
BPM = 138.0
OFFSET = 1.39                       # s from the first VBI to bar 0 (the grid of the original, tools/transcribe.py)
STEP = 60.0 / BPM / 4               # s per 16th
TICK_HZ = 60000 / 1001              # VBI of CGA-1V
ISR_HZ = 55930.4 / 43               # interrupt of the 82C54
YM_CLOCK = 3579545
YM_RATE = YM_CLOCK / 72
WAIT = 0xFF
END = 0xFE

MOD_SLOT = (0x00, 0x01, 0x02, 0x08, 0x09, 0x0A, 0x10, 0x11, 0x12)   # register offset of the modulator of a channel
SLOT = {'BD': 0x13, 'SD': 0x14, 'HH': 0x11, 'OH': 0x11, 'TOM': 0x12, 'CYM': 0x15}    # BD: its carrier
BIT = {'BD': 0x10, 'SD': 0x08, 'TOM': 0x04, 'CYM': 0x02, 'HH': 0x01, 'OH': 0x01}
DRUM_OP = {'SD': P.SD, 'HH': P.HH, 'OH': P.OH, 'TOM': P.TOM, 'CYM': P.CYM}
BD_BASE = 0x20 | 0x40               # rhythm mode, deep vibrato (14 cent)
RHYTHM_KEYS = {6: 35, 7: 67, 8: 60}     # pitch of the rhythm channels (BD sweeps from above, TOM changes ch 8)
BD_SWEEP = (47, 41, 37)             # BD pitch in the first ticks of a hit, then RHYTHM_KEYS[6]
PATCH_AHEAD = 24                    # ticks: an instrument change is written this early when the channel is free


def tick_of(step):
    return round((OFFSET + step * STEP) * TICK_HZ)


def ym_freq(key):
    """(block, F-number) of a (fractional) MIDI key, the finest block that fits."""
    f = 440.0 * 2 ** ((key - 69) / 12)
    for block in range(8):
        fn = round(f * (1 << (20 - block)) / YM_RATE)
        if fn < 1024:
            return block, fn
    return 7, 1023


def tl_of(o, att_db):
    return max(0, min(63, o['tl'] + round(att_db / 0.75)))


def reg20(o, vib=None):
    return o['am'] << 7 | (o['vib'] if vib is None else vib) << 6 | o['egt'] << 5 | o['ksr'] << 4 | o['mult']


def op_static(slot, o):
    """Registers of an operator except 20h (vibrato) and 40h (level), which the player drives."""
    return [(0x60 + slot, o['ar'] << 4 | o['dr']), (0x80 + slot, o['sl'] << 4 | o['rr']), (0xE0 + slot, o['ws'])]


class Song:
    """What music/badapple.py fills: notes of channels 0-5, drum hits, automation; times in steps (16ths)."""

    def __init__(self):
        self.notes = {c: [] for c in range(6)}
        self.hits = []
        self.auto = {}

    def note(self, ch, step, length, key, att=0.0, patch=None, legato=False, glide=0, vib=None, gate=None):
        """A note: length in steps to the next possible note, gate = steps until key off (default length);
        legato: no new attack when the previous note still sounds (glide: ticks of the pitch slide);
        vib: steps after which the vibrato starts (None: never; the patch's own VIB bits stay)."""
        self.notes[ch].append(dict(s0=step, s1=step + (length if gate is None else gate), key=key, att=att,
                                   patch=patch, legato=legato, glide=glide, vib=vib))

    def hit(self, step, inst, att=0.0, key=None):
        """A drum: BD, SD, HH (closed), OH (open hat), CYM, TOM (key = its pitch)."""
        self.hits.append((step, inst, att, key))

    def ramp(self, kind, ch, s0, s1, v0, v1):
        """Automation (dB, from step s0 to s1, then held): kind 'level' (attenuation of the channel, ch 'drums' for
        all drums) or 'bright' (attenuation of the modulator: darker)."""
        self.auto.setdefault((kind, ch), []).append((s0, s1, v0, v1))

    def value(self, kind, ch, step):
        v = 0.0
        for s0, s1, v0, v1 in sorted(self.auto.get((kind, ch), ())):
            if step < s0:
                break
            v = v1 if step >= s1 or s1 == s0 else v0 + (v1 - v0) * (step - s0) / (s1 - s0)
        return v


def step_of(tick):
    return (tick / TICK_HZ - OFFSET) / STEP


class Regs:
    """Shadow of the registers: only changes are written (forced writes for key on/off and drums)."""
    def __init__(self):
        self.v = {}

    def set(self, out, r, val, force=False):
        if force or self.v.get(r) != val:
            out.append((r, val))
            self.v[r] = val


def compile_song(song):
    """-> (setup writes, list of ticks with their writes)."""
    # channel timelines: on/off ticks
    plan = {}
    for c, lst in song.notes.items():
        lst = sorted(lst, key=lambda n: n['s0'])
        prev = None
        for n in lst:
            n['k0'] = tick_of(n['s0'])
            n['k1'] = max(n['k0'] + 1, tick_of(n['s1']))
            if n['patch'] is None:
                n['patch'] = prev['patch'] if prev else None
            if n['patch'] is None:
                raise ValueError(f'channel {c}: first note without an instrument')
            if prev is not None:
                if prev['k1'] > n['k0']:
                    prev['k1'] = n['k0']
                n['tie'] = n['legato'] and prev['k1'] == n['k0'] and prev['patch'] is n['patch']
            else:
                n['tie'] = False
            prev = n
        # a note followed right by the next one ends a tick early: its key off is not in the burst of the attacks
        for a, b in zip(lst, lst[1:]):
            if not b['tie'] and a['k1'] == b['k0'] and a['k1'] - a['k0'] > 2:
                a['k1'] -= 1
        plan[c] = lst
    hits = {}
    for step, inst, att, key in song.hits:
        k = tick_of(step)
        cur = hits.setdefault(k, {}).get(inst)
        if cur is None or att < cur[0]:
            hits[k][inst] = (att, key)

    regs = Regs()
    setup = []
    regs.set(setup, 0x01, 0x20, True)          # waveform select on
    regs.set(setup, 0x08, 0x00, True)
    regs.set(setup, 0xBD, 0x00, True)
    for ch in range(9):
        regs.set(setup, 0xB0 + ch, 0x00, True)
    cur_patch = {}

    def patch_writes(out, c, p):
        m = MOD_SLOT[c]
        for r, v in op_static(m, p['mod']) + op_static(m + 3, p['car']):
            regs.set(out, r, v)
        regs.set(out, 0xC0 + c, p['fb'] << 1 | p['cnt'])
        cur_patch[c] = p

    for c, lst in plan.items():
        if lst:
            patch_writes(setup, c, lst[0]['patch'])
    m = MOD_SLOT[6]
    for r, v in op_static(m, P.BD['mod']) + op_static(m + 3, P.BD['car']):
        regs.set(setup, r, v, True)
    regs.set(setup, 0x20 + m, reg20(P.BD['mod']), True)
    regs.set(setup, 0x23 + m, reg20(P.BD['car']), True)
    regs.set(setup, 0x40 + m, P.BD['mod']['ksl'] << 6 | P.BD['mod']['tl'], True)
    regs.set(setup, 0xC6, P.BD['fb'] << 1 | P.BD['cnt'], True)
    for ins in ('SD', 'HH', 'TOM', 'CYM'):
        o = DRUM_OP[ins]
        for r, v in op_static(SLOT[ins], o):
            regs.set(setup, r, v, True)
        regs.set(setup, 0x20 + SLOT[ins], reg20(o), True)
    for ch, key in RHYTHM_KEYS.items():
        block, fn = ym_freq(key)
        regs.set(setup, 0xA0 + ch, fn & 0xFF, True)
        regs.set(setup, 0xB0 + ch, block << 2 | fn >> 8, True)
    regs.set(setup, 0xBD, BD_BASE, True)

    # events per tick
    on_at, off_at, pre_at = {}, {}, {}
    for c, lst in plan.items():
        last_off = 0
        last_patch = cur_patch.get(c)
        for i, n in enumerate(lst):
            if not n['tie']:
                on_at.setdefault(n['k0'], []).append((c, n))
            nxt = lst[i + 1] if i + 1 < len(lst) else None
            if not (nxt and nxt['tie']):
                off_at.setdefault(n['k1'], []).append(c)
            if n['patch'] is not last_patch:
                pk = max(last_off + 1, n['k0'] - PATCH_AHEAD) if last_off < n['k0'] else n['k0']
                pre_at.setdefault(min(pk, n['k0']), []).append((c, n['patch']))
                last_patch = n['patch']
            last_off = n['k1']
    idx = {c: 0 for c in plan}      # channel -> index of its current note
    keyed = {}                      # channel -> True while key on
    hh_var = 'HH'
    bd_sweep = []
    last = max([n['k1'] for lst in plan.values() for n in lst] + list(hits)) + 60
    ticks = []
    for k in range(last + 1):
        step = step_of(k)
        offs, pre, lv, fr, ons, drum = [], [], [], [], [], []
        for c in off_at.get(k, ()):
            regs.set(offs, 0xB0 + c, regs.v.get(0xB0 + c, 0) & 0x1F, True)
            keyed[c] = False
        for c, p in pre_at.get(k, ()):
            patch_writes(pre, c, p)
        starting = {c: n for c, n in on_at.get(k, ())}
        for c, lst in plan.items():
            # the note of the channel at this tick: the last one started (sounding or in its release)
            i = idx[c]
            while i + 1 < len(lst) and lst[i + 1]['k0'] <= k:
                i += 1
            idx[c] = i
            if not lst or lst[i]['k0'] > k:
                continue
            cand = lst[i]
            p = cand['patch']
            if c in starting and keyed.get(c):            # still on: retrigger
                regs.set(offs, 0xB0 + c, regs.v[0xB0 + c] & 0x1F, True)
            # levels: note + channel automation; brightness on the modulator
            att = cand['att'] + song.value('level', c, step)
            bright = song.value('bright', c, step)
            mslot = MOD_SLOT[c]
            car_tl = tl_of(p['car'], att)
            mod_tl = tl_of(p['mod'], bright + (att if p['cnt'] else 0))
            regs.set(lv, 0x43 + mslot, p['car']['ksl'] << 6 | car_tl)
            regs.set(lv, 0x40 + mslot, p['mod']['ksl'] << 6 | mod_tl)
            vib_on = cand['vib'] is not None and k >= tick_of(cand['s0'] + cand['vib']) and k < cand['k1']
            regs.set(lv, 0x20 + mslot, reg20(p['mod'], 1 if vib_on else None))
            regs.set(lv, 0x23 + mslot, reg20(p['car'], 1 if vib_on else None))
            # pitch
            key = cand['key'] + p['tr']
            if cand['tie'] and cand['glide'] and k < cand['k0'] + cand['glide']:
                prev = lst[i - 1]
                a = (k - cand['k0'] + 1) / (cand['glide'] + 1)
                key = prev['key'] + p['tr'] + (cand['key'] - prev['key']) * a
            block, fn = ym_freq(key)
            regs.set(fr, 0xA0 + c, fn & 0xFF)
            if c in starting:
                regs.set(ons, 0xB0 + c, 0x20 | block << 2 | fn >> 8, True)
                keyed[c] = True
            else:
                regs.set(fr, 0xB0 + c, (0x20 if keyed.get(c) else 0) | block << 2 | fn >> 8)
        # drums (written before the melodic attacks of the tick: the beat on time)
        dprep = []
        dlev = song.value('level', 'drums', step)
        h = hits.get(k, {})
        bits = 0
        for ins, (att, key) in h.items():
            bits |= BIT[ins]
            a = att + dlev
            if ins == 'BD':
                regs.set(dprep, 0x40 + SLOT['BD'], P.BD['car']['ksl'] << 6 | tl_of(P.BD['car'], a))
                bd_sweep = list(BD_SWEEP)
                continue
            o = DRUM_OP[ins]
            slot = SLOT[ins]
            if ins in ('HH', 'OH') and ins != hh_var:
                for r, v in op_static(slot, o):
                    regs.set(dprep, r, v)
                hh_var = ins
            regs.set(dprep, 0x40 + slot, o['ksl'] << 6 | tl_of(o, a))
            if ins == 'TOM' and key is not None:
                block, fn = ym_freq(key)
                regs.set(dprep, 0xA8, fn & 0xFF)
                regs.set(dprep, 0xB8, block << 2 | fn >> 8)
        bkey = bd_sweep.pop(0) if bd_sweep else RHYTHM_KEYS[6]
        block, fn = ym_freq(bkey)
        regs.set(dprep, 0xA6, fn & 0xFF)
        regs.set(dprep, 0xB6, block << 2 | fn >> 8)
        cur = regs.v.get(0xBD, BD_BASE)
        if cur & bits:                                  # retrigger: the bit must go 0 first
            regs.set(drum, 0xBD, cur & ~bits & 0xFF, True)
        regs.set(drum, 0xBD, BD_BASE | bits)
        ticks.append(offs + pre + dprep + drum + lv + fr + ons)
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
    """Times of the writes as the interrupt makes them at the nominal speed: [(time s, reg, val)], and the worst lag
    in ticks. Tick k starts at k / TICK_HZ (tick 0 with the first interrupt after the setup)."""
    out = []
    p = 0
    while stream[p] < END:                  # setup: mus_init writes it before the interrupt runs
        out.append((0.0, stream[p], stream[p + 1]))
        p += 2
    tick = -1
    tick_start = 0.0
    worst = 0.0
    i = 0
    while stream[p] != END:
        t = (i + isr_phase) / ISR_HZ
        i += 1
        due = int(t * TICK_HZ)              # ticks released so far - 1
        n = 0
        while n < per_isr and stream[p] != END:
            if stream[p] == WAIT:
                if tick >= due:
                    break
                tick += 1
                tick_start = tick / TICK_HZ
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


def load_score(path=SCORE):
    spec = importlib.util.spec_from_file_location('score', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    song = Song()
    mod.arrange(song)
    return song


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--score', default=SCORE)
    ap.add_argument('--out', default=os.path.join(ROOT, 'build', 'music.bin'))
    ap.add_argument('--vgm', default=os.path.join(ROOT, 'build', 'badapple.vgm'))
    a = ap.parse_args()
    song = load_score(a.score)
    setup, ticks = compile_song(song)
    st = stream_of(setup, ticks)
    writes, worst = simulate(st)
    n = [len(t) for t in ticks]
    srt = sorted(n)
    print(f'music: {len(ticks)} ticks ({len(ticks) / TICK_HZ:.1f} s), {len(st)} B, setup {len(setup)} writes, '
          f'{sum(len(v) for v in song.notes.values())} notes, {len(song.hits)} drum hits')
    print(f'  writes/tick: mean {sum(n) / len(n):.2f} p99 {srt[len(n) * 99 // 100]} max {srt[-1]}; '
          f'worst lag {worst:.2f} ticks')
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    open(a.out, 'wb').write(st)
    if a.vgm:
        write_vgm(a.vgm, writes)
        print(f'  {a.out}, {a.vgm}')


if __name__ == '__main__':
    main()
