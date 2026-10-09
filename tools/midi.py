"""Standard MIDI File reader (stdlib only) for the music arrangement (tools/mkmusic.py).

load(path) -> Song: tracks of events with absolute ticks, the tempo map and notes paired (on, off) with times in
seconds. Command line: python tools/midi.py FILE  prints a summary of the tracks.
"""
import struct
import sys
from collections import namedtuple

Note = namedtuple('Note', 'track ch key vel t0 t1 tick0 tick1')   # t0, t1 in seconds
Event = namedtuple('Event', 'tick track kind data')               # kind: 'on', 'off', 'prog', 'cc', 'bend', meta


class Song:
    def __init__(self):
        self.division = 480
        self.tracks = []          # list of (name, [Event])
        self.tempos = []          # (tick, us per quarter)
        self.timesig = []         # (tick, num, den)
        self.notes = []
        self.events = []          # all non-note channel events (prog, cc, bend), merged

    def seconds(self, tick):
        """Time of an absolute tick by the tempo map."""
        t = 0.0
        last_tick, us = 0, 500000
        for tt, u in self.tempos:
            if tt >= tick:
                break
            t += (tt - last_tick) * us / 1e6 / self.division
            last_tick, us = tt, u
        return t + (tick - last_tick) * us / 1e6 / self.division


def _varlen(b, p):
    n = 0
    while True:
        c = b[p]
        p += 1
        n = (n << 7) | (c & 0x7F)
        if not c & 0x80:
            return n, p


def load(path):
    b = open(path, 'rb').read()
    s = Song()
    assert b[:4] == b'MThd', 'not a MIDI file'
    hl, fmt, ntr, div = struct.unpack('>IHHH', b[4:14])
    assert not div & 0x8000, 'SMPTE time not supported'
    s.division = div
    p = 8 + hl
    for ti in range(ntr):
        while b[p:p + 4] != b'MTrk':           # skip unknown chunks
            p += 8 + struct.unpack('>I', b[p + 4:p + 8])[0]
        ln = struct.unpack('>I', b[p + 4:p + 8])[0]
        q, end = p + 8, p + 8 + ln
        p = end
        tick, run, name, ev = 0, 0, '', []
        while q < end:
            dt, q = _varlen(b, q)
            tick += dt
            st = b[q]
            if st & 0x80:
                q += 1
            else:
                st = run
            if st == 0xFF:
                typ = b[q]
                n, q = _varlen(b, q + 1)
                data = b[q:q + n]
                q += n
                if typ == 0x51:
                    s.tempos.append((tick, int.from_bytes(data, 'big')))
                elif typ == 0x58:
                    s.timesig.append((tick, data[0], 1 << data[1]))
                elif typ == 0x03 and not name:
                    name = data.decode('latin-1')
                elif typ == 0x2F:
                    break
                continue
            if st in (0xF0, 0xF7):
                n, q = _varlen(b, q)
                q += n
                continue
            run = st
            hi, ch = st & 0xF0, st & 0x0F
            if hi in (0xC0, 0xD0):
                d = (b[q],)
                q += 1
            else:
                d = (b[q], b[q + 1])
                q += 2
            if hi == 0x90 and d[1]:
                ev.append(Event(tick, ti, 'on', (ch, d[0], d[1])))
            elif hi in (0x80, 0x90):
                ev.append(Event(tick, ti, 'off', (ch, d[0])))
            elif hi == 0xC0:
                ev.append(Event(tick, ti, 'prog', (ch, d[0])))
            elif hi == 0xB0:
                ev.append(Event(tick, ti, 'cc', (ch, d[0], d[1])))
            elif hi == 0xE0:
                ev.append(Event(tick, ti, 'bend', (ch, (d[0] | d[1] << 7) - 8192)))
        s.tracks.append((name, ev))
    s.tempos.sort()
    # pair notes (offs before ons at the same tick, first in first out per channel and key)
    open_ = {}
    for name, ev in s.tracks:
        for e in sorted(ev, key=lambda e: (e.tick, e.kind != 'off')):
            if e.kind == 'on':
                open_.setdefault((e.track, e.data[0], e.data[1]), []).append((e.tick, e.data[2]))
            elif e.kind == 'off':
                lst = open_.get((e.track, e.data[0], e.data[1]))
                if lst:
                    t0, vel = lst.pop(0)
                    s.notes.append(Note(e.track, e.data[0], e.data[1], vel, s.seconds(t0), s.seconds(e.tick),
                                        t0, e.tick))
            else:
                s.events.append(e)
    s.notes.sort(key=lambda n: (n.t0, n.key))
    s.events.sort(key=lambda e: e.tick)
    return s


NAMES = 'C C# D D# E F F# G G# A A# B'.split()


def key_name(k):
    return f'{NAMES[k % 12]}{k // 12 - 1}'


def summary(s):
    print(f'division {s.division}, tempos {len(s.tempos)}: ' +
          ', '.join(f'{t}:{60e6 / u:.2f}' for t, u in s.tempos[:8]) + (' ...' if len(s.tempos) > 8 else ''))
    print('time signatures:', s.timesig[:4])
    end = max((n.t1 for n in s.notes), default=0)
    print(f'notes {len(s.notes)}, length {end:.1f} s')
    for ti, (name, ev) in enumerate(s.tracks):
        ns = [n for n in s.notes if n.track == ti]
        if not ns and not ev:
            continue
        chs = sorted({n.ch for n in ns})
        progs = sorted({e.data for e in ev if e.kind == 'prog'})
        poly = 0
        if ns:
            pts = sorted([(n.t0, 1) for n in ns] + [(n.t1, -1) for n in ns])
            c = 0
            for _, d in pts:
                c += d
                poly = max(poly, c)
        rng = f'{key_name(min(n.key for n in ns))}..{key_name(max(n.key for n in ns))}' if ns else ''
        t = f'{ns[0].t0:.1f}-{max(n.t1 for n in ns):.1f}s' if ns else ''
        print(f'  {ti:2} {name[:28]:28} ch {chs} prog {progs} notes {len(ns):5} poly {poly:2} {rng:10} {t}')


if __name__ == '__main__':
    for f in sys.argv[1:]:
        print('==', f)
        summary(load(f))
