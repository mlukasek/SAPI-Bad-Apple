"""Fit the timing of a MIDI to the audio of the video: t_audio = scale * t_midi + offset.

The audio of orig/Touhou - Bad Apple_003.avi is decoded by ffmpeg (mono 8 kHz), its onset envelope (rectified
rise of the log energy in 10 ms bins) is correlated with the onsets of the MIDI notes (drums weigh most).
Usage: python tools/msync.py [MIDI] [--tracks 2,9]
"""
import argparse
import math
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import midi  # noqa: E402

AUDIO = os.path.join(ROOT, 'orig', 'Touhou - Bad Apple_003.avi')
RATE = 8000
BIN = 0.01


def audio_envelope(path=AUDIO):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-vn', '-ac', '1', '-ar', str(RATE), '-f', 's16le',
                          '-'], capture_output=True, check=True).stdout
    import array
    a = array.array('h')
    a.frombytes(raw[:len(raw) // 2 * 2])
    n = int(RATE * BIN)
    loge = []
    for i in range(0, len(a) - n, n):
        e = sum(x * x for x in a[i:i + n]) / n
        loge.append(math.log10(e + 1.0))
    env = [0.0] + [max(0.0, loge[i] - loge[i - 1]) for i in range(1, len(loge))]
    return env


def midi_onsets(song, tracks=None):
    w = {}
    for n in song.notes:
        if tracks and n.track not in tracks:
            continue
        wt = 1.0 if n.ch == 9 and n.key in (35, 36, 38, 39, 40) else 0.3
        w[n.t0] = w.get(n.t0, 0) + wt
    return sorted(w.items())


def score(env, ons, scale, off):
    s = 0.0
    for t, wt in ons:
        i = int(round((scale * t + off) / BIN))
        if 0 <= i < len(env):
            s += wt * max(env[i - 1:i + 2] or [0])
    return s


def fit(env, ons, scales, offs):
    best = (-1, 0, 0)
    for sc in scales:
        for off in offs:
            v = score(env, ons, sc, off)
            if v > best[0]:
                best = (v, sc, off)
    return best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('midi', nargs='?', default=os.path.join(ROOT, 'orig', 'midi', 'handhule90-full.mid'))
    ap.add_argument('--tracks')
    a = ap.parse_args()
    song = midi.load(a.midi)
    tr = {int(x) for x in a.tracks.split(',')} if a.tracks else None
    env = audio_envelope()
    ons = midi_onsets(song, tr)
    print(f'audio {len(env) * BIN:.2f} s, onsets {len(ons)}')
    # coarse: offset in 20 ms steps, scale around 1
    v, sc, off = fit(env, ons, [1 + k * 0.001 for k in range(-5, 6)], [k * 0.02 for k in range(-250, 501)])
    print(f'coarse: score {v:.1f} scale {sc:.4f} offset {off:.3f}')
    v, sc, off = fit(env, ons, [sc + k * 0.0001 for k in range(-10, 11)], [off + k * 0.005 for k in range(-8, 9)])
    print(f'fine:   score {v:.1f} scale {sc:.5f} offset {off:.3f}')
    base = score(env, ons, sc, off + 0.217)          # half a beat away: the contrast of the fit
    print(f'contrast against half a beat off: {v / max(base, 1e-9):.2f}x')
    # local check per 16 bars: the best offset of each part with the global scale
    bar = 4 * 60 / 138
    for b0 in range(0, 128, 16):
        part = [(t, w) for t, w in ons if b0 * bar <= t < (b0 + 16) * bar]
        if len(part) < 10:
            continue
        lv, _, lo = fit(env, part, [sc], [off + k * 0.005 for k in range(-20, 21)])
        print(f'  bars {b0:3}-{b0 + 15:3}: offset {lo:.3f} ({(lo - off) * 1000:+.0f} ms)')


if __name__ == '__main__':
    main()
