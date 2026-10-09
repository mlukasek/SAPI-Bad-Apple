"""Bad Apple!! - our arrangement for the YM3812 (OPL2) of MPH-1V.

Song: Bad Apple!! (Touhou Gensokyo ~ Lotus Land Story, ZUN), the version of Alstroemeria Records feat. nomico that
plays in the video. The melody, the chords, the form and the plan of the arrangement (what plays where: the drum
intro, the quiet chorus without the kick, the stop in bar 63, the last chorus without drums) were transcribed and
measured from the audio of the video (tools/transcribe.py, docs/rozhodnuti.md); the parts and the sounds are our
own, written for 6 FM voices and the rhythm mode of the OPL2 (tools/opl_patches.py).

Key D# minor (the last chorus in E minor), 138 BPM, 125 bars; a step is a 16th, bar b starts at step 16 b.
Channels: 0 lead (the voice of the song), 1 bass, 2 echo / second voice / gated chord, 3+4(+5) pads,
5 arpeggio; drums in the rhythm mode (BD, SD, HH as closed and open hat and crash, TOM).
Form (bars): drum intro 0-7, riff 8-15, verse 16-31, chorus 32-47, quiet chorus 48-62, stop 63, riff 64-71,
verse 72-87, chorus 88-103, chorus in E minor without drums 104-119, outro 120-124.
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

# chords: (bass pitch class, chord tones)
CH = {
    'D#m': (3, (3, 6, 10)), 'D#m/A#': (10, (3, 6, 10)), 'Bmaj7': (11, (11, 3, 6, 10)), 'C#': (1, (1, 5, 8)),
    'C#s2': (1, (1, 3, 8)), 'Dm': (2, (2, 5, 9)), 'A#7/D': (2, (10, 2, 5, 8)), 'G#7': (8, (8, 3, 6)),
    'G#6': (8, (8, 3, 5)), 'F#s2': (6, (6, 8, 1)), 'D#5/D': (2, (3, 10)), 'D#5': (3, (3, 10)), 'F#x': (6, (6, 8, 3)), 'D#/G': (7, (7, 10, 3)),
    'Esus4': (4 - 1, (4 - 1, 9 - 1, 11 - 1)),         # the outro is transposed up like the last chorus
}
RIFF_CH = [['D#5'], ['D#5', 'G#7'], ['D#5'], ['D#5', 'F#x']] * 2      # power chords, as in the original
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
            self.s.note(ch, s, ln, h + DETUNE.get(ch, 0.0), att, patch, vib=4 if ln >= 6 else None)

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
                if len(chans) == 3:                     # the third voice: the root above the pair
                    root = chord_at(s)[0]
                    pair = pair + (min(k for k in range(pair[1] + 1, pair[1] + 13) if k % 12 == root),)
                if rhythm is None:
                    for ch, k in zip(chans, pair):
                        self.s.note(ch, s, ln, k + DETUNE.get(ch, 0.0), att, patch, gate=ln - 0.25)
                else:
                    for r in rhythm:
                        if s <= 16 * b + r < s + ln:
                            for ch, k in zip(chans, pair):
                                self.s.note(ch, 16 * b + r, 1, k + DETUNE.get(ch, 0.0), att, patch, gate=gate)

    def bass(self, b0, n, patch, att, style):
        """Bass from the chord roots: 'oct8' (8ths low/high), 'pump' (8ths, offbeats strong), 'quarter',
        'long'."""
        for b in range(b0, b0 + n):
            for s, ln, c, tr in CHART[b]:
                root = chord_at(s)[0]
                low = 34 + (root - 34) % 12          # A#1..A2
                for st in range(s, s + ln):
                    r = st - 16 * b
                    if style == 'oct8' and r % 2 == 0:
                        self.s.note(1, st, 2, low + (12 if r % 4 == 2 else 0), att + (0 if r % 4 == 0 else 1.5),
                                    patch, gate=1.5)
                    elif style == 'pump' and r % 2 == 0:
                        # 8ths on the root, the offbeats strong (the kick has the beat)
                        self.s.note(1, st, 2, low, att + (4.5 if r % 4 == 0 else 0), patch, gate=1.5)
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

    def tails(self, s0, s1, spec):
        """Noise tails of the drums hit in steps s0..s1 (the reverb and the wash of the original):
        spec {instrument: (channels, patch, att over the hit, softest att)}; the tail follows soft hits but not the
        accents (they come with the kick: its noise would cover it); a tail lasts until the next one on its channel and ends
        two steps before s1 (the channel is free to switch its instrument)."""
        for step, inst, att, key in sorted(h for h in self.s.hits if s0 <= h[0] < s1):
            if inst in spec:
                chans, patch, extra, loudest = spec[inst]
                for ch in chans:
                    self.s.note(ch, step, min(16, s1 - 2 - step), P.NOISE_KEY, max(att + extra, loudest) - MIX[ch],
                                patch)

    def snare_body(self, s0, s1, chans, att):
        """The body of each snare hit in steps s0..s1 on melodic channels: a note sliding down SNARE_BODY (on two
        channels a little apart: louder and wider)."""
        hi, lo, glide = SNARE_BODY
        for step, inst, hatt, key in sorted(h for h in self.s.hits if s0 <= h[0] < s1 and h[1] == 'SD'):
            ln = min(2, s1 - step)
            for i, ch in enumerate(chans):
                a, d = hatt + att - MIX[ch], 0.15 * i
                self.s.note(ch, step, 0.2, hi + d, a, P.BODY)
                self.s.note(ch, step + 0.2, ln - 0.2, lo + d, a, P.BODY, legato=True, glide=glide)

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
EIGHTS = 'x.x.x.x.x.x.x.x.'


# mix (dB of attenuation per channel): the original has most of its energy in the kick and the bass, the voice
# and the synths lie lower (measured per section, docs/rozhodnuti.md)
MIX = {0: 4.0, 1: 0.0, 2: 4.0, 3: 6.0, 4: 6.0, 5: 5.0, 'drums': 0.0}
# detune of the accompanying voices against each other (semitones): the beating thickens the sound like the
# chorus of the synths of the original (the pure FM tones measured too clean)
DETUNE = {2: 0.10, 3: -0.08, 4: 0.08, 5: 0.04}
# the riff line per half bar (transcribed): D#, then into G#7 and F# at the end of the odd bars
RIFF_A = [key(n) for n in 'd#2 d#2 d#2 d#3 d#3 d#3 c#3 d#3'.split()]
RIFF_G = [key(n) for n in 'd#2 d#2 d#3 f#3 g#2 g#2 f#3 g#2'.split()]
RIFF_F = [key(n) for n in 'g#2 g#2 f#2 g#2 f#2 f#2 d#3 f#3'.split()]
RIFF_DETUNE = {0: 0.12, 2: -0.12}                # the two guitars against the bass
RIFF_GTR = 0.0                                  # dB of the guitars under the bass
RIFF_SUB = 2.0                                  # dB of the deep bass (a sine on the line: the body of the bass)
# noise tails of the drums in the intro: {instrument: (channels, patch, dB under the hit)}
# The original (work/introdecay.py): the snare falls 12 dB in 55 ms and then rings out (-24 dB at 0.2 s): its
# tail starts ~12 dB under it; the hats fade like a burst of noise (-9 dB at 70 ms, -24 dB at 180 ms) where the
# rhythm HH is gone in 25 ms: their tail is ~3 dB under them and masks their tonal peaks.
# The author found the first version too noisy at the kick: the tails are 3 dB softer and the accents of the
# hats (on the beats, with the kick) do not raise them.
INTRO_TAILS = {'SD': ((3,), P.NZ_SNARE, 17.0, 0.0), 'HH': ((4,), P.NZ_HAT, 11.0, 22.0),
               'OH': ((4,), P.NZ_HAT, 9.0, 0.0), 'CR': ((5,), P.NZ_CRASH, -2.0, 0.0)}
SNARE_BODY = (55, 38, 9)                        # the body of the snare slides G3 -> D2 in 9 ticks
SHAKER = 'o.x.o.x.o.x.o.x.'                  # soft hats for air in the parts without the beat


def arrange(song):
    p = Parts(song)
    s = song
    s.mix.update(MIX)

    # ---- intro (0-7): the drums alone, as in the original: kick on the beats, snare on 2 and 4, the hats
    # on the 8ths, a crash at the start, a snare run at the end of every other bar; bar 7 rises to the riff
    for b in range(7):
        p.drums(b, 1, {'BD': (FOUR, 0), 'SD': (TWO_FOUR if b % 2 else '....x.......xxxx', 3),
                       'HH': ('X.x.X.x.X.x.X.x.', 11)})
    s.hit(0, 'CR', 9.0)                     # the crash of the rhythm HH rings (1-5 kHz partials): soft, its noise
    for b in (2, 4, 6):                     # tail carries it
        s.hit(16 * b, 'CR', 14.0)
    p.drums(7, 1, {'BD': (FOUR, 0), 'SD': ('....x...x.x.x.x.', 3)})
    for i in range(8):
        s.hit(16 * 7 + 8 + i, 'OH', 14.0 - 1.5 * i)        # a rising wash of hats into the riff
    # the drums of the original ring out (reverb, a wash of the hats between the hits): noise tails on the free
    # melodic channels
    p.tails(0, 16 * 8, INTRO_TAILS)
    p.snare_body(0, 16 * 8 - 2, (0, 1), 0.0)

    def riff(b0):
        # the riff of the original: a driving 16th line of distorted basses (D#2 D#2 D#2 D#3 D#3 D#3 C#3 D#3,
        # through G# and F# at the end of the odd bars), the bass in the middle and two guitars doubled around
        # it (measured: the same line in the center and the sides, a saw-like spectrum to 4 kHz), a sine under
        # the bass for its body (ch 5); the power chord held quietly under it, full beat
        for b in range(b0, b0 + 8):
            line = RIFF_A + (RIFF_A if b % 2 == 0 else RIFF_G if b % 4 == 1 else RIFF_F)
            for i, k in enumerate(line):
                acc = 0.0 if i % 8 in (3, 7) else 1.0            # the syncopes push
                s.note(1, 16 * b + i, 1, k, att=acc, patch=P.DRIVE)
                if b < b0 + 7 or i < 14:                  # the guitars and the sine stop before the verse
                    s.note(5, 16 * b + i, 1, k, att=acc - MIX[5] + RIFF_SUB, patch=P.DEEP)
                    for ch in (0, 2):
                        s.note(ch, 16 * b + i, 1, k + RIFF_DETUNE[ch], att=acc + RIFF_GTR, patch=P.GRIT)
        p.chords(b0, 8, P.PAD, 11.0, chans=(4,), lo=60, hi=72, skip_bass=False)
        p.drums(b0, 7, {'BD': (FOUR, 0), 'SD': (TWO_FOUR, 3), 'HH': (EIGHTS, 9), 'OH': (OFF8, 7)})
        p.drums(b0 + 7, 1, {'BD': (FOUR, 0), 'SD': ('....x...x.x.xxxx', 3), 'HH': (OFF8, 9)})
        p.snare_body(16 * b0, 16 * (b0 + 8) - 2, (3,), 0.0)
        s.hit(16 * b0, 'CR', 1.0)

    def verse(b0, second_voice):
        # the voice with its echo (in the second verse a second voice in the second half); held strings
        notes = p.line(0, 16 * b0, VERSE, P.LEAD, att=1.5, vib=3)
        s.ramp('bright', 0, 16 * b0, 16 * b0, 2, 2)
        for st, ln, k in notes:
            if st < 16 * (b0 + 8) or not second_voice:
                s.note(2, st + 3, ln, k + DETUNE[2], 12.0, P.SHADOW)
        if second_voice:
            p.second(2, [n for n in notes if n[0] >= 16 * (b0 + 8)], P.SHADOW, 7.0)
        p.chords(b0, 16, P.PAD, 8.0, chans=(3, 4, 5), lo=56, hi=70)
        p.bass(b0, 16, P.BASS, 2.0, 'pump')
        p.drums(b0, 7, {'BD': (FOUR, 0), 'SD': (TWO_FOUR, 4), 'HH': ('o.x.o.x.o.x.o.x.', 7)})
        p.drums(b0 + 7, 1, {'BD': (FOUR, 0), 'SD': ('....x.......xxxx', 4), 'HH': (OFF8, 8)})
        p.drums(b0 + 8, 7, {'BD': (FOUR, 0), 'SD': (TWO_FOUR, 3), 'HH': ('.o.o.o.o.o.o.o.o', 9), 'OH': (OFF8, 6)})
        p.drums(b0 + 15, 1, {'BD': (FOUR, 0), 'SD': ('....x...x.x.xxxx', 3), 'HH': (OFF8, 8)})
        s.hit(16 * (b0 + 8), 'CR', 4.0)

    def chorus(b0, text, tr=0, drums=True):
        notes = p.line(0, 16 * b0, text, P.LEAD, att=1.5, tr=tr, vib=3)
        s.ramp('bright', 0, 16 * b0, 16 * b0, -2, -2)
        p.second(2, notes, P.SHADOW, 6.0)
        p.chords(b0, 16, P.PAD, 6.0, lo=56 if drums else 62, hi=70 if drums else 76)
        if drums:
            p.arp(b0, 16, P.PLUCK, 11.0)
            p.bass(b0, 16, P.BASS, 1.5, 'pump')
            p.drums(b0, 15, {'BD': (FOUR, 0), 'SD': (TWO_FOUR, 3), 'HH': ('.o.o.o.o.o.o.o.o', 8), 'OH': (OFF8, 6)})
            for b in (b0, b0 + 8):
                s.hit(16 * b, 'CR', 2.0)
        else:
            # the last chorus: no drums, the arpeggio in 8ths like a piano, the bass pulses, then holds
            p.arp(b0, 16, P.PLUCK, 9.0, every=2)
            p.drums(b0, 16, {'HH': (SHAKER, 13)})
            p.bass(b0, 8, P.BASS, 3.0, 'pump')
            p.bass(b0 + 8, 8, P.SUB, 2.0, 'long')

    def quiet(b0):
        # 48-62: the voice softly over the strings, no kick, a clap on beat 3; 63: the stop
        stop = 16 * (b0 + 15) + 8
        for st, ln, k in melody(CHORUS):
            st += 16 * b0
            if st < stop:
                ln = min(ln, stop - st)
                s.note(0, st, ln, k, 3.0, P.LEAD, vib=3 if ln >= 6 else None)
                s.note(2, st + 3, ln, k + DETUNE[2], 13.0, P.SHADOW)
        s.ramp('bright', 0, 16 * b0, 16 * b0, 3, 3)
        p.chords(b0, 15, P.PAD, 6.0, chans=(3, 4, 5), lo=62, hi=76)
        p.bass(b0, 15, P.SUB, 2.0, 'long')
        p.drums(b0, 15, {'SD': ('........x.......', 7), 'HH': (SHAKER, 11)})
        # bar 63: two snare hits and the big stop on beat 3, then silence until the riff
        b = b0 + 15
        s.hit(16 * b + 2, 'SD', 5.0)
        s.hit(16 * b + 4, 'SD', 3.0)
        for inst in ('BD', 'SD', 'CR'):
            s.hit(stop, inst, 0.0)
        bass, tones = chord_at(stop)
        for ch, k in zip((3, 4, 5), tones_in(tones, 60, 72)):
            s.note(ch, stop, 8, k, 4.0, P.GATE, gate=2)
        s.note(1, stop, 8, 34 + (bass - 34) % 12, 0.0, P.BASS, gate=2)

    # ---- the form
    riff(8)
    verse(16, second_voice=False)
    chorus(32, CHORUS)
    p.drums(47, 1, {'BD': ('x...x...x.......', 0), 'SD': (TWO_FOUR[:12] + '....', 3), 'OH': (OFF8[:12], 8)})
    for i, tk in enumerate((67, 64, 60, 57)):
        s.hit(16 * 47 + 12 + i, 'TOM', 3.0, tk)
    quiet(48)
    riff(64)
    verse(72, second_voice=True)
    chorus(88, CHORUS)
    p.drums(103, 1, {'BD': (FOUR, 0), 'SD': ('....x...x.x.xxxx', 3), 'HH': (OFF8, 8)})
    chorus(104, CHORUS_END, tr=1, drums=False)
    s.ramp('bright', 0, 16 * 104, 16 * 104, -3, -3)

    # ---- outro (120-124): Esus4 held and fading, the voice holds its last note (the fifth)
    s.note(0, 16 * 119, 32, key('b4'), 1.5, P.LEAD, vib=3)
    s.ramp('level', 0, 16 * 120, 16 * 122, 0, 30)
    s.note(3, 16 * 120, 80, key('e5') + DETUNE[3], 8.0, P.PAD, vib=8)
    s.note(4, 16 * 120, 80, key('a5') + DETUNE[4], 8.0, P.PAD, vib=8)
    s.note(5, 16 * 120, 80, key('e4') + DETUNE[5], 9.0, P.PAD, vib=8)
    for ch in (3, 4, 5):
        s.ramp('level', ch, 16 * 120, 16 * 125, 0, 30)
