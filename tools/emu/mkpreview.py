"""Listening files from an emulator recording of the demo (tools/emu/run_demo.py --to-end --wav W):
build/badapple_opl.wav (the music from the start of the video), build/sync.wav (left the audio of the video,
right ours) and build/preview_opl.mp4 (the original video with our music). The recording is aligned by its
beats: roughly by the first sound (bar 0 of the arrangement, tools/mkmusic.py OFFSET s of the video), then to the
quarter notes of bars 8-120 (the strongest rises of the sound).

Usage: python tools/emu/mkpreview.py [work/demo_full.wav]
"""
import array
import math
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import mkmusic  # noqa: E402

VIDEO = os.path.join(ROOT, 'orig', 'Touhou - Bad Apple_003.avi')
B = os.path.join(ROOT, 'build')


def samples(path):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-vn', '-ac', '1', '-ar', '8000', '-f', 's16le', '-'],
                         capture_output=True, check=True).stdout
    a = array.array('h')
    a.frombytes(raw[:len(raw) // 2 * 2])
    return a


def align(path, thr=300):
    """s of the recording at video time 0."""
    a = samples(path)
    rough = next(i for i, x in enumerate(a) if abs(x) > thr) / 8000 - mkmusic.OFFSET
    n = 40                                              # 5 ms
    e = [math.log10(sum(x * x for x in a[i:i + n]) / n + 1.0) for i in range(0, len(a) - n, n)]
    rise = [0.0] + [max(0.0, e[i] - e[i - 1]) for i in range(1, len(e))]
    beat = 4 * mkmusic.STEP
    best = None
    for k in range(-40, 41):
        sh = rough + k * 0.005
        sc = sum(rise[i] for q in range(32, 480) if 0 <= (i := round((sh + mkmusic.OFFSET + q * beat) / 0.005))
                 < len(rise))
        if best is None or sc > best[0]:
            best = (sc, sh)
    return best[1]


def ff(*args):
    subprocess.run(['ffmpeg', '-v', 'error', '-y'] + list(args), check=True)


def main():
    rec = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'work', 'demo_full.wav')
    shift = align(rec)
    print(f'video time 0 is {shift:.3f} s of the recording')
    ours = os.path.join(B, 'badapple_opl.wav')
    ff('-i', rec, '-af', f'atrim=start={shift:.4f},asetpts=PTS-STARTPTS,aresample=44100,volume=1.6', ours)
    ff('-i', VIDEO, '-i', ours, '-filter_complex',
       '[0:a]aresample=44100,pan=mono|c0=0.5*c0+0.5*c1,volume=0.6,aformat=sample_fmts=fltp:channel_layouts=mono[l];'
       '[1:a]aformat=sample_fmts=fltp:channel_layouts=mono[r];[l][r]amerge=inputs=2[a]',
       '-map', '[a]', '-t', '220', os.path.join(B, 'sync.wav'))
    ff('-i', VIDEO, '-i', ours, '-map', '0:v', '-map', '1:a', '-c:v', 'libx264', '-crf', '23', '-preset', 'veryfast',
       '-c:a', 'aac', '-b:a', '192k', '-shortest', os.path.join(B, 'preview_opl.mp4'))
    print('build/badapple_opl.wav, build/sync.wav, build/preview_opl.mp4')


if __name__ == '__main__':
    main()
