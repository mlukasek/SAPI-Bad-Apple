"""Bad Apple!! - our arrangement for the YM3812 (OPL2) of MPH-1V.

Song: Bad Apple!! (Touhou Gensokyo ~ Lotus Land Story, ZUN), the version of Alstroemeria Records feat. nomico that
plays in the video. The melody, the chords and the form were transcribed from the audio of the video
(tools/transcribe.py); the arrangement - the parts, the instruments (tools/opl_patches.py), the intro, the riffs,
the breakdown and the ending - is our own, written for 6 FM voices and the rhythm mode of the OPL2.

Key D# minor (the last chorus in E minor), 138 BPM, 125 bars; a step is a 16th, bar b starts at step 16 b.
Channels: 0 lead (the voice of the song), 1 bass, 2 echo / second voice, 3+4 pads / stabs / gated chords,
5 arpeggio / bells; drums in the rhythm mode (BD, SD, HH, TOM, CYM).
Form (bars): intro 0-7, riff 8-15, verse 16-31, chorus 32-47, quiet chorus 48-63, riff 64-71, verse 72-87,
chorus 88-103, chorus in E minor 104-119, outro 120-124.
"""
import opl_patches as P

PC = {'c': 0, 'c#': 1, 'd': 2, 'd#': 3, 'e': 4, 'f': 5, 'f#': 6, 'g': 7, 'g#': 8, 'a': 9, 'a#': 10, 'b': 11}


def key(name):
    """'d#4' -> 63 (C4 = 60)."""
    return 12 * (int(name[-1]) + 1) + PC[name[:-1]]


def melody(text):
    """Notes of a line: 'd#4/2 f4/2 r/4 ...' (length in 16ths, r = rest, '|' checks a bar of 16).
    -> [(step, length, key)] from step 0."""
    out, step, bar = [], 0, 0
    for tok in text.split():
        if tok == '|':
            bar += 16
            if step != bar:
                raise ValueError(f'bar ends at {step}, expected {bar}: {text}')
            continue
        name, ln = tok.split('/')
        if name != 'r':
            out.append((step, int(ln), key(name)))
        step += int(ln)
    return out


# ---- the song: melody (transcribed), D# minor

V1 = 'd#4/2 f4/2 f#4/2 g#4/2 a#4/4 d#5/2 c#5/2 |'
V2 = 'a#4/4 d#4/4 a#4/2 g#4/2 f#4/2 f4/2 |'
V3 = 'd#4/2 f4/2 f#4/2 g#4/2 a#4/4 g#4/2 f#4/2 |'
V4 = 'f4/2 d#4/1 c#4/1 f4/2 f#4/2 f4/2 d#4/2 d4/2 f4/2 |'
V8A = 'f#4/8 g#4/4 r/4 |'
V8B = 'f#4/8 g#4/4 d4/4 |'
VERSE = ' '.join([V1, V2, V3, V4, V1, V2, V3, V8A, V1, V2, V3, V4, V1, V2, V3, V8B])

CA = 'c#5/2 d#5/2 a#4/2 g#4/2 a#4/4 g#4/2 a#4/2 |'
CB = 'c#5/2 d#5/2 c#5/2 g#4/8 a#4/2 |'
CC = 'g#4/2 f#4/2 f4/2 c#4/2 d#4/8 |'
CD = 'f4/2 f#4/2 g#4/2 a#4/8 c#5/2 |'
CE = 'c#5/2 d#5/2 a#4/2 g#4/2 a#4/2 c#5/2 d#5/2 f5/2 |'
CF = 'f#5/2 f5/2 d#5/2 c#5/2 a#4/4 g#4/2 a#4/2 |'
CG = 'd#5/12 r/4 |'
CHORUS = ' '.join([CA, CB, CC, CD, CA, CA, CC, CD, CA, CA, CC, CD, CA, CE, CF, CG])
CHORUS_END = ' '.join([CA, CB, CC, CD, CA, CA, CC, CD, CA, CA, CC, CD, CA, CE, CF, 'r/16 |'])   # + the last note

# our riff hook (bells), in the 3-3-2 rhythm of the riff
HOOK = ('a#4/3 d#5/3 f5/2 f#5/3 f5/3 d#5/2 | c#5/3 a#4/3 g#4/2 a#4/8 | '
        'a#4/3 d#5/3 f5/2 f#5/3 g#5/3 a#5/2 | g#5/3 f#5/3 f5/2 d#5/4 r/4 |')
# intro twinkle (bells): two bars, D# minor add 9
TWINKLE = 'd#6/3 a#5/3 f#5/2 c#6/3 a#5/3 f5/2 | a#5/3 f#5/3 d#5/2 f5/3 c#5/3 a#4/2 |'

# chords: (bass pitch class, chord tones)
CH = {
    'D#m': (3, (3, 6, 10)), 'D#m/A#': (10, (3, 6, 10)), 'Bmaj7': (11, (11, 3, 6, 10)), 'C#': (1, (1, 5, 8)),
    'C#s2': (1, (1, 3, 8)), 'Dm': (2, (2, 5, 9)), 'A#7/D': (2, (10, 2, 5, 8)), 'G#7': (8, (8, 3, 6)),
    'G#6': (8, (8, 3, 5)), 'F#s2': (6, (6, 8, 1)), 'D#5/D': (2, (3, 10)), 'D#/G': (7, (7, 10, 3)),
    'Esus4': (4 - 1, (4 - 1, 9 - 1, 11 - 1)),         # the outro is transposed up like the last chorus
}
RIFF_CH = [['D#m'], ['D#m', 'G#7'], ['D#m'], ['D#m', 'F#s2']] * 2
VERSE_CH = [['D#m'], ['D#m'], ['Bmaj7'], ['C#', 'Dm'], ['D#m'], ['D#m', 'G#6'], ['Bmaj7'], ['C#', 'D#5/D'],
            ['D#m'], ['D#m'], ['D#m/A#', 'Bmaj7'], ['C#', 'Dm'], ['D#m'], ['D#m'], ['Bmaj7'], ['C#', 'Dm']]
CHORUS_CH = [['Bmaj7'], ['C#s2'], ['D#m'], ['D#m']] * 3 + [['Bmaj7'], ['C#s2'], ['D#m'], ['D#m', 'D#m', 'G#7', 'D#/G']]
QUIET_CH = CHORUS_CH[:12] + [['Bmaj7'], ['C#s2'], ['D#m'], ['C#s2', 'G#7']]

FORM = [('intro', 0, 8), ('riff', 8, 8), ('verse', 16, 16), ('chorus', 32, 16), ('quiet', 48, 16), ('riff', 64, 8),
        ('verse', 72, 16), ('chorus', 88, 16), ('chorusE', 104, 16), ('outro', 120, 5)]


def chart():
    """{bar: [(step, length, chord name, transpose)]}"""
    out = {}
    for name, b0, n in FORM:
        rows = {'intro': [['D#m']] * 8, 'riff': RIFF_CH, 'verse': VERSE_CH, 'chorus': CHORUS_CH,
                'quiet': QUIET_CH, 'chorusE': CHORUS_CH, 'outro': [['Esus4']] * 5}[name]
        tr = 1 if name in ('chorusE', 'outro') else 0
        for i in range(n):
            row = rows[i % len(rows)]
            if name in ('chorusE', 'outro') and i == n - 1 and len(row) > 1:
                row = row[:1]                       # the end of the song: no walk down
            ln = 16 // len(row)
            out[b0 + i] = [(16 * (b0 + i) + j * ln, ln, c, tr) for j, c in enumerate(row)]
    return out


CHART = chart()


def chord_at(step):
    for s, ln, c, tr in CHART.get(int(step) // 16, ()):
        if s <= step < s + ln:
            bass, tones = CH[c]
            return (bass + tr) % 12, tuple((t + tr) % 12 for t in tones)
    raise KeyError(step)


def tones_in(pcs, lo, hi):
    return [k for k in range(lo, hi + 1) if k % 12 in pcs]


# ---- part writers

class Parts:
    def __init__(self, song):
        self.s = song
        self.prev_voices = None

    def line(self, ch, step0, text, patch, att=0.0, tr=0, vib=4, legato=False, gate=None, echo=None):
        """A melody line at step0; vib: notes of 6 steps and more get vibrato after `vib` steps.
        echo: (channel, delay, att, patch) repeats the line later and quieter."""
        notes = [(step0 + s, ln, k + tr) for s, ln, k in melody(text)]
        for s, ln, k in notes:
            self.s.note(ch, s, ln, k, att, patch, legato=legato, vib=vib if ln >= 6 else None,
                        gate=None if gate is None else min(ln, gate))
        if echo:
            ech, dly, eatt, epatch = echo
            for s, ln, k in notes:
                self.s.note(ech, s + dly, ln, k, att + eatt, epatch)
        return notes

    def second(self, ch, notes, patch, att):
        """A second voice under a line: the nearest chord tone 3-9 semitones below each note."""
        for s, ln, k in notes:
            bass, tones = chord_at(s)
            cand = [t for t in tones_in(tones, k - 9, k - 3)]
            h = max(cand) if cand else k - 4
            self.s.note(ch, s, ln, h, att, patch, vib=4 if ln >= 6 else None)

    def voices(self, tones, n, lo, hi, all_tones=None):
        """Two chord tones 3-9 semitones apart near the previous voicing (smooth movement); when the tones
        cannot make such a pair, from all_tones."""
        best = None
        prev = self.prev_voices or [(lo + hi) // 2 + 2 * i for i in range(n)]
        for pcs in (tones, all_tones or tones):
            cand = tones_in(pcs, lo, hi)
            for i in range(len(cand)):
                for j in range(i + 1, len(cand)):
                    pair = (cand[i], cand[j])
                    if pair[0] % 12 == pair[1] % 12 or pair[1] - pair[0] > 9 or pair[1] - pair[0] < 3:
                        continue
                    cost = sum(abs(a - b) for a, b in zip(pair, sorted(prev)))
                    if best is None or cost < best[0]:
                        best = (cost, pair)
            if best:
                break
        self.prev_voices = list(best[1])
        return best[1]

    def chords(self, b0, n, patch, att, rhythm=None, gate=None, chans=(3, 4), lo=56, hi=72, skip_bass=True):
        """Two chord voices on channels 3 and 4: held (rhythm None) or a rhythm of steps in a bar."""
        for b in range(b0, b0 + n):
            for s, ln, c, tr in CHART[b]:
                bass, tones = chord_at(s)
                use = [t for t in tones if t != bass] if skip_bass and len(tones) > 2 else list(tones)
                pair = self.voices(use, 2, lo, hi, tones)
                if rhythm is None:
                    for ch, k in zip(chans, pair):
                        self.s.note(ch, s, ln, k, att, patch, gate=ln - 0.25)
                else:
                    for r in rhythm:
                        if s <= 16 * b + r < s + ln:
                            for ch, k in zip(chans, pair):
                                self.s.note(ch, 16 * b + r, 1, k, att, patch, gate=gate)

    def bass(self, b0, n, patch, att, style):
        """Bass from the chord roots: 'oct8' (8ths low/high), 'off8' (offbeat 8ths), 'quarter', 'long'."""
        for b in range(b0, b0 + n):
            for s, ln, c, tr in CHART[b]:
                root = chord_at(s)[0]
                low = 34 + (root - 34) % 12          # A#1..A2
                for st in range(s, s + ln):
                    r = st - 16 * b
                    if style == 'oct8' and r % 2 == 0:
                        self.s.note(1, st, 2, low + (12 if r % 4 == 2 else 0), att + (0 if r % 4 == 0 else 1.5),
                                    patch, gate=1.5)
                    elif style == 'off8' and r % 4 == 2:
                        self.s.note(1, st, 2, low + 12, att, patch, gate=1.5)
                    elif style == 'quarter' and r % 4 == 0:
                        self.s.note(1, st, 4, low, att, patch, gate=3)
                    elif style == 'long' and st == s:
                        self.s.note(1, st, ln, low, att, patch)

    def arp(self, b0, n, patch, att, every=1, lo=63, span=15):
        """Rising arpeggio of the chord tones, a note every `every` steps."""
        for b in range(b0, b0 + n):
            for s, ln, c, tr in CHART[b]:
                bass, tones = chord_at(s)
                ks = tones_in(tones, lo, lo + span)
                for i, st in enumerate(range(s, s + ln, every)):
                    self.s.note(5, st, every, ks[i % len(ks)], att, patch)

    def drums(self, b0, n, pattern):
        """pattern: {instrument: (16 chars, att)}; x = hit, X = accent (-3 dB), o = soft (+5 dB)."""
        for b in range(b0, b0 + n):
            for inst, (pat, att) in pattern.items():
                for i, c in enumerate(pat):
                    if c in 'xXo':
                        self.s.hit(16 * b + i, inst, att + {'x': 0, 'X': -3, 'o': 5}[c])


# drum patterns
FOUR = 'x...x...x...x...'
TWO_FOUR = '....x.......x...'
OFF8 = '..x...x...x...x.'
FILL_SD = '........x.x.xxxx'
ROLL16 = 'xxxxxxxxxxxxxxxx'


def arrange(song):
    p = Parts(song)
    s = song
    lead_echo = (2, 3, 12.0, P.SHADOW)

    # ---- intro (0-7): bells and their echo over a swelling pad, then kick, bass, snare build
    for b in (0, 2, 4, 6):
        p.line(5, 16 * b, TWINKLE, P.BELL, att=7.0, vib=None, echo=(2, 3, 10.0, P.BELL))
    s.ramp('level', 5, 0, 64, 9, 0)
    s.ramp('level', 2, 0, 64, 9, 0)
    s.note(3, 0, 128, key('f#4'), 9.0, P.PAD, vib=8, gate=120)
    s.note(4, 0, 128, key('a#4'), 9.0, P.PAD, vib=8, gate=120)
    s.ramp('level', 3, 0, 64, 24, 0)
    s.ramp('level', 4, 0, 64, 24, 0)
    s.note(1, 64, 32, key('d#1'), 4.0, P.SUB)
    for st in range(96, 128, 2):
        s.note(1, st, 2, key('d#2') if st % 4 else key('d#1'), 3.0, P.BASS, gate=1.5)
    s.ramp('bright', 1, 96, 128, 18, 0)
    p.drums(2, 2, {'HH': (OFF8, 16)})
    p.drums(4, 2, {'BD': (FOUR, 2), 'HH': (OFF8, 12)})
    p.drums(6, 1, {'BD': (FOUR, 0), 'SD': (TWO_FOUR, 6), 'HH': (OFF8, 10)})
    p.drums(7, 1, {'BD': (FOUR, 0), 'SD': ('x.x.x.x.xxxxxxxx', 4), 'HH': (OFF8, 10)})
    s.ramp('level', 'drums', 112, 128, 6, 0)

    def riff(b0):
        p.chords(b0, 8, P.GATE, 8.0, rhythm=(0, 3, 6, 8, 11, 14), gate=0.6, lo=58, hi=72)
        p.arp(b0, 8, P.PLUCK, 11.0)
        s.ramp('bright', 5, 16 * b0, 16 * b0 + 64, 6, 0)
        p.bass(b0, 8, P.BASS, 2.0, 'oct8')
        p.line(0, 16 * (b0 + 4), HOOK, P.BELL, att=3.0, vib=None, echo=(2, 3, 11.0, P.BELL))
        p.drums(b0, 7, {'BD': (FOUR, 0), 'SD': (TWO_FOUR, 3), 'HH': (TWO_FOUR, 7), 'OH': (OFF8, 8)})
        p.drums(b0, 7, {'HH': ('.o.o.o.o.o.o.o.o', 11)})
        p.drums(b0 + 7, 1, {'BD': (FOUR, 0), 'SD': ('....x...x.x.xxxx', 3), 'HH': (OFF8, 9)})
        s.hit(16 * b0, 'CYM', 2.0)

    def verse(b0, second_voice):
        notes = p.line(0, 16 * b0, VERSE, P.LEAD, att=1.5, vib=3)
        s.ramp('bright', 0, 16 * b0, 16 * b0, 2, 2)
        for st, ln, k in notes:
            if st < 16 * (b0 + 8) or not second_voice:
                s.note(2, st + 3, ln, k, 12.0, P.SHADOW)
        if second_voice:
            p.second(2, [n for n in notes if n[0] >= 16 * (b0 + 8)], P.SHADOW, 7.0)
        p.chords(b0, 8, P.STAB, 8.0, rhythm=(2, 6, 10, 14), gate=1, lo=58, hi=72)
        p.chords(b0 + 8, 8, P.STAB, 7.0, rhythm=(2, 6, 10, 14), gate=1, lo=58, hi=72)
        if second_voice:
            p.arp(b0, 16, P.PLUCK, 12.0)
            p.bass(b0, 16, P.BASS, 2.0, 'oct8')
        else:
            p.arp(b0 + 8, 8, P.PLUCK, 12.0, every=2)
            p.bass(b0, 8, P.SUB, 2.0, 'quarter')
            p.bass(b0 + 8, 8, P.BASS, 2.0, 'oct8')
        s.ramp('bright', 5, 16 * b0, 16 * b0, 4, 4)
        p.drums(b0, 7, {'BD': (FOUR, 0), 'SD': (TWO_FOUR, 4), 'HH': (OFF8, 9)})
        p.drums(b0 + 7, 1, {'BD': (FOUR, 0), 'SD': ('....x.......xxxx', 4), 'HH': (OFF8, 9)})
        p.drums(b0 + 8, 7, {'BD': (FOUR, 0), 'SD': (TWO_FOUR, 3), 'HH': ('.o.o.o.o.o.o.o.o', 12), 'OH': (OFF8, 9)})
        p.drums(b0 + 15, 1, {'BD': (FOUR, 0), 'SD': ('....x...x.x.xxxx', 3), 'HH': (OFF8, 9)})
        s.hit(16 * (b0 + 8), 'CYM', 4.0)

    def chorus(b0, text, tr=0, quiet=False):
        if quiet:
            # 48-55: bells sing, pads and sub bass, soft hats; 56-63: the voice returns, everything builds
            notes = [(16 * b0 + st, ln, k) for st, ln, k in melody(text)]
            for st, ln, k in notes:
                if st < 16 * (b0 + 8):
                    s.note(0, st, ln, k, 2.0, P.BELL)
                    s.note(2, st + 3, ln, k, 12.0, P.BELL)
                else:
                    s.note(0, st, ln, k, 1.5, P.LEAD, vib=3 if ln >= 6 else None)
                    s.note(2, st + 3, ln, k, 12.0, P.SHADOW)
            p.chords(b0, 16, P.PAD, 7.0, lo=56, hi=70)
            p.bass(b0, 8, P.SUB, 2.0, 'long')
            p.bass(b0 + 8, 4, P.SUB, 2.0, 'quarter')
            p.bass(b0 + 12, 4, P.BASS, 2.0, 'oct8')
            p.arp(b0 + 8, 8, P.PLUCK, 10.0)
            s.ramp('bright', 5, 16 * (b0 + 8), 16 * (b0 + 16), 20, 0)
            s.ramp('level', 5, 16 * (b0 + 8), 16 * (b0 + 16), 10, 0)
            s.ramp('level', 5, 16 * (b0 + 16), 16 * (b0 + 16), 0, 0)
            p.drums(b0, 8, {'HH': (OFF8, 12)})
            s.hit(16 * b0, 'CYM', 8.0)
            p.drums(b0 + 8, 4, {'BD': (FOUR, 3), 'HH': (OFF8, 10)})
            p.drums(b0 + 12, 2, {'BD': (FOUR, 0), 'SD': (TWO_FOUR, 4), 'HH': ('.o.o.o.o.o.o.o.o', 11),
                                 'OH': (OFF8, 9)})
            p.drums(b0 + 14, 1, {'BD': (FOUR, 0), 'SD': ('x.x.x.x.x.x.x.x.', 5), 'OH': (OFF8, 9)})
            p.drums(b0 + 15, 1, {'BD': (FOUR, 0), 'SD': (ROLL16, 2)})
            s.ramp('level', 'drums', 16 * (b0 + 14), 16 * (b0 + 16), 4, 0)
            s.ramp('level', 'drums', 16 * (b0 + 16), 16 * (b0 + 16), 0, 0)
            return
        notes = p.line(0, 16 * b0, text, P.LEAD, att=1.5, tr=tr, vib=3)
        s.ramp('bright', 0, 16 * b0, 16 * b0, -2, -2)
        p.second(2, notes, P.SHADOW, 6.0)
        p.chords(b0, 16, P.PAD, 6.0, lo=56, hi=70)
        p.arp(b0, 16, P.PLUCK, 10.0)
        s.ramp('bright', 5, 16 * b0, 16 * b0, 0, 0)
        p.bass(b0, 16, P.BASS, 1.5, 'oct8')
        full = {'BD': (FOUR, 0), 'SD': (TWO_FOUR, 3), 'HH': ('.o.o.o.o.o.o.o.o', 11), 'OH': (OFF8, 8)}
        p.drums(b0, 15, full)
        for b in (b0, b0 + 8) if not tr else (b0, b0 + 4, b0 + 8, b0 + 12):
            s.hit(16 * b, 'CYM', 2.0)

    # ---- the form
    riff(8)
    verse(16, second_voice=False)
    chorus(32, CHORUS)
    # chorus end (47): toms down into the quiet chorus
    p.drums(47, 1, {'BD': ('x...x...x.......', 0), 'SD': (TWO_FOUR[:12] + '....', 3), 'OH': (OFF8[:12], 8)})
    for i, tk in enumerate((67, 64, 60, 57, 55, 52)):
        s.hit(16 * 47 + 10 + i, 'TOM', 3.0, tk)
    chorus(48, CHORUS, quiet=True)
    riff(64)
    verse(72, second_voice=True)
    chorus(88, CHORUS)
    # 103: the turn to E minor: snare roll and toms
    p.drums(103, 1, {'BD': (FOUR, 0), 'SD': ('x.x.x.x.xxxxxxxx', 2)})
    for i, tk in enumerate((60, 62, 64, 67)):
        s.hit(16 * 103 + 12 + i, 'TOM', 2.0, tk)
    s.ramp('level', 'drums', 16 * 103, 16 * 104, 5, 0)
    s.ramp('level', 'drums', 16 * 104, 16 * 104, 0, 0)
    chorus(104, CHORUS_END, tr=1)
    s.ramp('bright', 0, 16 * 104, 16 * 104, -3, -3)

    # ---- outro (120-124): E minor, Esus4 held; the voice holds its last note (the fifth), the bells of the
    # intro come back and fade
    s.note(0, 16 * 119, 32, key('b4'), 1.5, P.LEAD, vib=3)
    s.ramp('level', 0, 16 * 120, 16 * 122, 0, 30)
    for b in (120, 122):
        p.line(5, 16 * b, TWINKLE, P.BELL, att=6.0, tr=1, vib=None, echo=(2, 3, 10.0, P.BELL))
    s.note(5, 16 * 124, 16, key('e6'), 6.0, P.BELL)
    s.note(3, 16 * 120, 80, key('e4'), 6.0, P.PAD, vib=8)
    s.note(4, 16 * 120, 80, key('a4'), 6.0, P.PAD, vib=8)
    s.note(1, 16 * 120, 64, key('e1'), 3.0, P.SUB)
    for ch in (1, 3, 4):
        s.ramp('level', ch, 16 * 120, 16 * 125, 0, 30)
    for ch in (2, 5):
        s.ramp('level', ch, 16 * 120, 16 * 125, 0, 18)
    s.hit(16 * 120, 'CYM', 0.0)
    s.hit(16 * 120, 'BD', 0.0)
    p.drums(120, 2, {'HH': (OFF8, 12)})
    s.ramp('level', 'drums', 16 * 120, 16 * 122, 0, 12)
