"""Measurements of the soundtrack for the transcription of the arrangement (stdlib only, tools/audio.py).

The audio of the video on the grid of the song (138 BPM, bar 0 at OFFSET s), per 16th: the harmonic salience of
the semitones E3..E6 in the center of the stereo (mid minus 1.2 x side, whitened: the voice), in the side and
in the mix; per 8th the salience of the bass E1..A3; per 16th the chroma. Cached in work/sal.json (~1 min).

  python tools/transcribe.py roll MODE LO HI BARS [LEN]   heat map (piano roll) of the average of bars
  python tools/transcribe.py melody MODE LO HI BARS [LEN] [cost]   most likely line (Viterbi) through it
  python tools/transcribe.py chords B0 B1                 chord and bass per half bar
MODE center | side | mix | bass; BARS: start bars of the repeats to average, '+' separated, a ':T' suffix
transposes that repeat down by T semitones (the last chorus is one up), e.g. 32+88+104:1.
"""
import array
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import audio  # noqa: E402

SRC = os.path.join(ROOT, 'orig', 'Touhou - Bad Apple_003.avi')
CACHE = os.path.join(ROOT, 'work', 'sal.json')
RATE = 11025
OFFSET = 1.39                       # s of the audio at bar 0
STEP = 60.0 / 138 / 4               # a 16th
NBARS = 125
MEL_LO, BASS_LO = 48, 26            # lowest keys of the salience rows
NAMES = 'C C# D D# E F F# G G# A A# B'.split()


def name(key):
    return f'{NAMES[key % 12]}{key // 12 - 1}'


def features():
    if os.path.exists(CACHE):
        with open(CACHE) as f:
            return json.load(f)
    L, R = audio.decode(SRC, RATE, 2)
    M = array.array('f', ((x + y) * 0.5 for x, y in zip(L, R)))
    S = array.array('f', ((x - y) * 0.5 for x, y in zip(L, R)))
    sp2, sp4 = audio.Spectrum(2048), audio.Spectrum(4096)
    mel = audio.Salience(2048, RATE, MEL_LO, 88, harmonics=5, decay=0.7)
    bas = audio.Salience(4096, RATE, BASS_LO, 57, harmonics=4, decay=0.7)
    out = {'center': [], 'side': [], 'mix': [], 'bass': [], 'chroma': []}
    for s in range(NBARS * 16):
        t0 = int(OFFSET * RATE + (s + 0.5) * STEP * RATE)
        mm, ms = sp2.mags(M, t0 - 1024), sp2.mags(S, t0 - 1024)
        c = [max(0.0, x - 1.2 * y) for x, y in zip(mm, ms)]
        out['center'].append([round(v, 2) for v in mel(audio.whiten(c), compress=False)])
        out['side'].append([round(v, 2) for v in mel(audio.whiten(ms), compress=False)])
        out['mix'].append([round(v, 2) for v in mel(audio.whiten(mm), compress=False)])
        out['chroma'].append([round(v, 3) for v in audio.chroma(audio.whiten(mm), 2048, RATE, 60, 1500)])
        if s % 2 == 0:
            m4 = sp4.mags(M, t0 - 2048 + int(STEP * RATE / 2))
            out['bass'].append([round(v, 2) for v in bas(audio.whiten(m4), compress=False)])
        if s % 400 == 0:
            print(f'  step {s}/{NBARS * 16}', file=sys.stderr)
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    with open(CACHE, 'w') as f:
        json.dump(out, f)
    return out


def repeats(spec):
    return [(int(x.split(':')[0]), int(x.split(':')[1]) if ':' in x else 0) for x in spec.split('+')]


def grid(d, mode, lo, hi, inst, length):
    """Columns (per 16th, per 8th for the bass) of the summed salience of keys lo..hi over the repeats."""
    base, per = (BASS_LO, 8) if mode == 'bass' else (MEL_LO, 16)
    g = d[mode]
    cols = []
    for s in range(length * per):
        v = [0.0] * (hi - lo + 1)
        for b0, tr in inst:
            row = g[b0 * per + s]
            for i in range(hi - lo + 1):
                j = lo + i + tr - base
                if 0 <= j < len(row):
                    v[i] += row[j]
        cols.append(v)
    return cols, per


def roll(d, mode, lo, hi, inst, length):
    cols, per = grid(d, mode, lo, hi, inst, length)
    w = 32 // per
    for b in range(length):
        part = cols[b * per:(b + 1) * per]
        mx = max(max(c) for c in part) or 1
        print(f'--- bar +{b} of {inst}')
        for i in range(hi - lo, -1, -1):
            print(f'{name(lo + i):>4} |' + ''.join(' .:-=+*#%@'[min(9, int(10 * c[i] / mx))] * w for c in part) + '|')


def melody(d, mode, lo, hi, inst, length, change=0.25, jump=0.03):
    cols, per = grid(d, mode, lo, hi, inst, length)
    cols = [[x / (max(c) or 1) for x in c] for c in cols]
    n = hi - lo + 1
    score, back = cols[0][:], []
    for c in cols[1:]:
        ns, bk = [], []
        for j in range(n):
            bi = max(range(n), key=lambda i: score[i] - (0 if i == j else change + jump * abs(i - j)))
            ns.append(score[bi] - (0 if bi == j else change + jump * abs(bi - j)) + c[j])
            bk.append(bi)
        score, back = ns, back + [bk]
    j = max(range(n), key=lambda i: score[i])
    path = [j]
    for bk in reversed(back):
        j = bk[j]
        path.append(j)
    path.reverse()
    for b in range(length):
        seg = path[b * per:(b + 1) * per]
        print(f'+{b:2}: ' + ' '.join(f'{name(lo + p) if s == 0 or seg[s - 1] != p else "-":>4}'
                                     for s, p in enumerate(seg)))


def chords(d, b0, b1):
    kinds = {'': (0, 4, 7), 'm': (0, 3, 7), '7': (0, 4, 7, 10), 'm7': (0, 3, 7, 10), 'sus4': (0, 5, 7)}

    def norm(v):
        m = sum(v) / 12
        v = [x - m for x in v]
        s = math.sqrt(sum(x * x for x in v)) or 1
        return [x / s for x in v]
    tmpl = []
    for r in range(12):
        for k, iv in kinds.items():
            v = [0.0] * 12
            for i in iv:
                v[(r + i) % 12] = 1.0
            tmpl.append((NAMES[r] + k, r, norm(v)))
    for b in range(b0, b1 + 1):
        out = []
        for h in range(2):
            c = [sum(d['chroma'][s][i] for s in range(b * 16 + h * 8, b * 16 + h * 8 + 8)) for i in range(12)]
            bp = [0.0] * 12
            for s in range(b * 8 + h * 4, b * 8 + h * 4 + 4):
                for i, v in enumerate(d['bass'][s]):
                    bp[(BASS_LO + i) % 12] += v
            bass = max(range(12), key=lambda i: bp[i])
            cn = norm(c)
            sc = sorted(((sum(x * y for x, y in zip(cn, t)) + (0.15 if r == bass else 0), nm)
                         for nm, r, t in tmpl), reverse=True)
            out.append(f'{sc[0][1]:>6} ({sc[0][0]:.2f}) {sc[1][1]:>6}  bass {NAMES[bass]:<2}')
        print(f'{b:3}: ' + ' | '.join(out))


def main():
    a = sys.argv[1:]
    if not a:
        print(__doc__)
        return
    d = features()
    if a[0] in ('roll', 'melody'):
        mode, lo, hi, inst = a[1], int(a[2]), int(a[3]), repeats(a[4])
        length = int(a[5]) if len(a) > 5 else 1
        if a[0] == 'roll':
            roll(d, mode, lo, hi, inst, length)
        else:
            melody(d, mode, lo, hi, inst, length, *(float(x) for x in a[6:8]))
    elif a[0] == 'chords':
        chords(d, int(a[1]), int(a[2]))


if __name__ == '__main__':
    main()
